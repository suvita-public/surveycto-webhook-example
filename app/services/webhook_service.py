"""
SurveyCTO webhook service — parse submission JSON into a pandas DataFrame.

WHAT SURVEYCTO SENDS
--------------------
When an enumerator submits a form, SurveyCTO can POST JSON to your URL. That JSON
includes normal form fields (text, selects, dates) plus metadata for any *file*
questions (photos, signatures, audio, PDFs, etc.).

File questions do NOT send the binary in the webhook. They send something like:

    "attachments": [
        { "file": { "filename": "photo-1.jpg", "type": "image/jpeg" } }
    ]

Your code reads `filename` and builds a view/download URL on the SurveyCTO server.

EXAMPLE PAYLOADS
----------------
See the project `examples/` folder:

  - examples/sample_submission.json
  - examples/sample_submission_register_photos.json  (repeat group + photo field names)

CONFIG (app/config/appconfig.ini)
---------------------------------
  attachment_repeat_group  — JSON key for the repeat group list (e.g. attachments)
  attachment_field         — JSON key inside each item for the file object (e.g. file)
  surveycto_attachment_base — URL prefix for building attachment_url

CUSTOMIZE
---------
Implement `process_submission()` below for your database, queue, email, etc.
"""

from datetime import datetime

import pandas as pd
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from app.config.config_loader import dict_configs, logger

# In-memory store for the most recent webhook only (fine for demos; use DB/Redis in production).
# One row per uploaded file in the submission.
latest_submission_df: pd.DataFrame | None = None


def _webhook_config() -> dict:
    """Read the [webhook] section from appconfig.ini."""
    return dict_configs.get("webhook", {})


def _attachment_base() -> str:
    """
    Base URL for SurveyCTO submission attachments on your server.

    Example: https://your-server.surveycto.com/view/submission-attachment
    """
    return _webhook_config().get(
        "surveycto_attachment_base",
        "https://your-server.surveycto.com/view/submission-attachment",
    ).rstrip("/")


def _build_attachment_url(surveycto_key: str, filename: str) -> str:
    """
    Build the URL SurveyCTO uses to view/download one uploaded file.

    surveycto_key: submission KEY from payload, usually "uuid:xxxxxxxx-..."
    filename:      value from the file field in the repeat group (e.g. photo-1.jpg)
    """
    # KEY arrives as "uuid:abc-123"; the attachment URL expects the uuid part only.
    uuid = surveycto_key.replace("uuid:", "")
    base = _attachment_base()
    # uuid is URL-encoded in the query string as uuid%3A<uuid>
    return f"{base}/{filename}?uuid=uuid%3A{uuid}"


def _validate_survey_signature(payload: dict) -> None:
    """
    Optional integrity check: form must set survey_signature to match this pattern.

    Many SurveyCTO forms use a calculate field:
        concat(${username}, "_", ${SubmissionDate}, "_", ${formdef_id})

    If it does not match, we reject the request (400) so random POSTs cannot fake submissions.
    """
    username = payload.get("username")
    submission_date = payload.get("SubmissionDate")
    formdef_id = payload.get("formdef_id")
    survey_signature = payload.get("survey_signature")

    expected_signature = f"{username}_{submission_date}_{formdef_id}"
    if survey_signature != expected_signature:
        logger.error(
            "Invalid survey_signature. Expected: %s, Got: %s",
            expected_signature,
            survey_signature,
        )
        raise HTTPException(status_code=400, detail="Invalid survey_signature")


def _extract_attachment_filenames(payload: dict) -> list[str]:
    """
    Collect every uploaded file's `filename` from the submission JSON.

    SurveyCTO repeat groups appear as a JSON array. Each element is one repeat instance.
    Inside each instance, the file question is an object with at least `filename` and often `type`.

    Example (default names) — see examples/sample_submission.json:

        "attachments": [
            { "file": { "filename": "photo-1.jpg", "type": "image/jpeg" } },
            { "file": { "filename": "photo-2.jpg", "type": "image/jpeg" } }
        ]

    Example (register-style names) — see examples/sample_submission_register_photos.json:

        "register_photos_group": [
            { "register_pic": { "filename": "capture-1.jpg", ... } }
        ]

    Map your form in appconfig.ini:
        attachment_repeat_group = register_photos_group
        attachment_field = register_pic
    """
    cfg = _webhook_config()
    group_name = cfg.get("attachment_repeat_group", "attachments")
    field_name = cfg.get("attachment_field", "file")

    # The repeat group key must exist on the payload; missing key => empty list => 400 later.
    group = payload.get(group_name, [])
    if not isinstance(group, list):
        return []

    filenames = []
    for item in group:
        if not isinstance(item, dict):
            continue

        # file question is usually a dict; some forms may store a plain string filename.
        file_info = item.get(field_name, {})
        if isinstance(file_info, dict):
            filename = file_info.get("filename")
        elif isinstance(file_info, str):
            filename = file_info
        else:
            filename = None

        if filename:
            filenames.append(filename)

    return filenames


def build_submission_dataframe(payload: dict) -> pd.DataFrame:
    """
    Turn a SurveyCTO submission dict into a pandas DataFrame (one row per uploaded file).

    Columns:
        surveycto_key   — payload KEY (submission uuid)
        username        — enumerator
        formdef_id      — form version
        submission_date — parsed SubmissionDate
        filename        — file name on SurveyCTO servers
        attachment_url  — full URL to view/download that file

    Use this from tests or notebooks without starting the HTTP server:

        import json
        from app.services.webhook_service import build_submission_dataframe
        with open("examples/sample_submission.json") as f:
            payload = json.load(f)
        df = build_submission_dataframe(payload)
    """
    surveycto_key = payload.get("KEY")
    username = payload.get("username")
    formdef_id = payload.get("formdef_id")
    submission_date_raw = payload.get("SubmissionDate")

    if not surveycto_key:
        raise HTTPException(status_code=400, detail="Missing KEY in submission payload")

    # Filenames from the repeat group configured in appconfig.ini.
    filenames = _extract_attachment_filenames(payload)
    if not filenames:
        # Same idea as "No images found in register_photos_group" — wrong config or empty submission.
        raise HTTPException(
            status_code=400,
            detail=(
                "No attachments found. Check attachment_repeat_group and "
                "attachment_field in appconfig.ini. See examples/sample_submission.json."
            ),
        )

    submission_dt = datetime.fromisoformat(submission_date_raw.replace("Z", "+00:00"))

    rows = []
    for filename in filenames:
        rows.append(
            {
                "surveycto_key": surveycto_key,
                "username": username,
                "formdef_id": formdef_id,
                "submission_date": submission_dt,
                "filename": filename,
                "attachment_url": _build_attachment_url(surveycto_key, filename),
            }
        )

    return pd.DataFrame(rows)


def get_latest_submission() -> pd.DataFrame | None:
    """Return the DataFrame from the last successful webhook, or None if none yet."""
    return latest_submission_df


def process_submission(submission_df: pd.DataFrame) -> None:
    """
    Hook: your business logic runs here after each valid webhook.

    The example only logs. Typical extensions:
      - submission_df.to_sql(...)
      - submission_df.to_parquet(...)
      - loop submission_df["attachment_url"] and download images
      - enqueue a background job with submission_df.to_dict("records")

    You can also read extra columns from the raw payload by extending build_submission_dataframe.
    """
    logger.info(
        "process_submission: %d row(s), keys=%s",
        len(submission_df),
        submission_df["surveycto_key"].iloc[0] if len(submission_df) else "n/a",
    )


async def handle_surveycto_webhook(request: Request):
    """
    HTTP entry point: SurveyCTO POSTs here when a form is submitted.

    Flow:
      1. Read JSON body
      2. Validate survey_signature (if your form provides it)
      3. Build DataFrame (one row per file in the repeat group)
      4. Store in latest_submission_df and call process_submission()
      5. Return 200 quickly (SurveyCTO expects a timely response)

    Example JSON: examples/sample_submission.json
    """
    global latest_submission_df

    logger.info("SurveyCTO webhook invoked. Headers: %s", str(request.headers))

    payload = await request.json()
    # Log keys only — full payload may contain PII; avoid logging entire body in production.
    logger.info("Received SurveyCTO payload keys: %s", list(payload.keys()))

    _validate_survey_signature(payload)

    submission_df = build_submission_dataframe(payload)
    latest_submission_df = submission_df

    logger.info("Built submission DataFrame with %d row(s)", len(submission_df))
    process_submission(submission_df)

    return JSONResponse(
        content={
            "response": "Success",
            "comment": "Submission parsed.",
            "row_count": len(submission_df),
            "surveycto_key": submission_df["surveycto_key"].iloc[0],
        }
    )
