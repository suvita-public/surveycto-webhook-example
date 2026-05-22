# Example SurveyCTO webhook payloads

SurveyCTO POSTs a JSON body to your webhook when a form is submitted. These files show realistic shapes you can use for local testing.

## Files

| File | Use when |
|------|----------|
| `sample_submission.json` | Default config: `attachment_repeat_group = attachments`, `attachment_field = file` |
| `sample_submission_register_photos.json` | Form uses `register_photos_group` / `register_pic` (common for photo registers) |

## Important: attachments are not sent as files

The webhook JSON contains **metadata only** — mainly each uploaded file’s `filename`. Your server builds a URL to download or view the file on SurveyCTO, for example:

`https://your-server.surveycto.com/view/submission-attachment/photo-1.jpg?uuid=uuid%3A<submission-uuid>`

The actual image bytes are fetched from that URL (or via SurveyCTO APIs), not from the webhook body.

## Field mapping (config → JSON)

In `app/config/appconfig.ini`:

```ini
attachment_repeat_group = attachments    # key in JSON for the repeat group list
attachment_field = file                  # key inside each repeat item for the file object
```

For `sample_submission_register_photos.json` use:

```ini
attachment_repeat_group = register_photos_group
attachment_field = register_pic
```

## Test locally

```bash
# From project root — load JSON and call the handler (see scripts/manual_webhook_test.py)
python scripts/manual_webhook_test.py

# Or POST with curl (server must be running)
curl -X POST http://localhost:8000/webhook/surveycto \
  -H "Content-Type: application/json" \
  -d @examples/sample_submission.json
```

## Required fields for this example handler

| Field | Purpose |
|-------|---------|
| `KEY` | Unique submission id (`uuid:...`) |
| `username` | Enumerator account |
| `SubmissionDate` | ISO timestamp from SurveyCTO |
| `formdef_id` | Form version id |
| `survey_signature` | Must equal `{username}_{SubmissionDate}_{formdef_id}` |
| Your repeat group | List of items, each with a file field containing `filename` |

Other fields (`district`, `member_name`, etc.) are ignored by the example handler but are often present in real payloads — keep them in your own `process_submission()` logic if you need them.
