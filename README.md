# surveycto-webhook-example

Runnable FastAPI reference for receiving SurveyCTO webhook POSTs when a form is submitted. It validates the submission, builds attachment URLs, and parses the result into a **pandas DataFrame** you can use in your own downstream code.

## Features

- FastAPI endpoint for SurveyCTO JSON webhook POSTs
- `survey_signature` validation (`{username}_{SubmissionDate}_{formdef_id}`)
- Configurable SurveyCTO attachment URL base and form field names
- One DataFrame row per attachment (`surveycto_key`, `username`, `formdef_id`, `submission_date`, `filename`, `attachment_url`)
- `process_submission()` hook for your custom logic
- INI-based config and structured logging
- Unit tests and a local replay script

## Prerequisites

- Python 3.11+
- SurveyCTO server with webhook support on your form

## Getting Started

### Installation

1. Clone the repository:

```bash
git clone https://github.com/suvita-public/surveycto-webhook-example.git
cd surveycto-webhook-example
```

2. Create a virtual environment and install dependencies:

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

3. Copy configuration templates:

```bash
copy app\config\appconfig.ini.example app\config\appconfig.ini
copy app\config\logconfig.ini.example app\config\logconfig.ini
```

4. Edit `app/config/appconfig.ini` with your webhook path and SurveyCTO server hostname.

### Configuration

`app/config/appconfig.ini` sections:

| Section | Keys | Purpose |
|---------|------|---------|
| `webhook` | `path`, `surveycto_attachment_base`, `attachment_repeat_group`, `attachment_field` | HTTP route, attachment URLs, and form field mapping |
| `logging` | `log_file_path` | Points to `logconfig.ini` |

### SurveyCTO setup

1. Deploy this app behind HTTPS (SurveyCTO requires a reachable URL).
2. In SurveyCTO server settings, configure a webhook to POST submission JSON to:

   `https://<your-host><path>`

   where `<path>` matches `[webhook] path` in `appconfig.ini` (default `/webhook/surveycto`).

3. Ensure your form calculates `survey_signature` the same way as this handler, or change validation in `app/services/webhook_service.py`.

4. Set `attachment_repeat_group` and `attachment_field` to the repeat group and file field names in your form design.

5. SurveyCTO expects a timely HTTP 200 response; keep processing efficient or move heavy work to a queue in production.

See [SurveyCTO documentation](https://docs.surveycto.com/) for webhook configuration details on your server version.

For a detailed guide on configuring the webhook in SurveyCTO (console screenshots, field options, troubleshooting), see [`SURVEYCTO-WEBHOOK-SETUP.md`](SURVEYCTO-WEBHOOK-SETUP.md).

## Usage

Start the API:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Health check:

```bash
curl http://localhost:8000/health
```

Run unit tests:

```bash
python -m pytest
```

Replay an example payload locally:

```bash
python scripts/manual_webhook_test.py
```

## Working with the DataFrame

After a successful webhook, the latest submission is available as a DataFrame:

```python
from app.services.webhook_service import get_latest_submission

df = get_latest_submission()
# df.to_csv("out.csv", index=False)
# df.to_sql("submissions", con=engine, if_exists="append")
```

To parse a payload without HTTP (tests, notebooks):

```python
from app.services.webhook_service import build_submission_dataframe

df = build_submission_dataframe(payload_dict)
```

Add your logic in `process_submission()` in `app/services/webhook_service.py`. It runs on every valid webhook.

## Payload contract

| Field | Description |
|-------|-------------|
| `KEY` | SurveyCTO submission UUID (e.g. `uuid:...`) |
| `username` | Collector username |
| `SubmissionDate` | ISO submission timestamp |
| `formdef_id` | Form definition id |
| `survey_signature` | Must equal `{username}_{SubmissionDate}_{formdef_id}` |
| `<attachment_repeat_group>` | List of groups, each containing `<attachment_field>` with a `filename` |

Default repeat group / field names are `attachments` / `file`.

**Example JSON files** (with notes): [`examples/README.md`](examples/README.md)

- [`examples/sample_submission.json`](examples/sample_submission.json) — default field names
- [`examples/sample_submission_register_photos.json`](examples/sample_submission_register_photos.json) — `register_photos_group` / `register_pic` style forms

## Adapting the example

- Implement `process_submission()` to save, sync, or queue data
- Rename `attachment_repeat_group` / `attachment_field` to match your form
- Replace `survey_signature` checks with HMAC or a SurveyCTO server secret if you use one
- Add authentication middleware on the webhook route for non-SurveyCTO callers
- Avoid logging full payloads in production (PII)

## Project structure

```
surveycto-webhook-example/
  LICENSE
  README.md
  SURVEYCTO-WEBHOOK-SETUP.md
  docs/
    images/   # SurveyCTO console screenshots (redacted)
  requirements.txt
  examples/
    sample_submission.json
    sample_submission_register_photos.json
  app/
    main.py
    api/routes_webhook.py
    services/webhook_service.py   # DataFrame + process_submission hook
    config/
    utils/exception_handler.py
  tests/
    test_webhook_service.py
  scripts/
    manual_webhook_test.py
```

## Contributing

1. Fork the repository
2. Create a branch (`git checkout -b feature/my-change`)
3. Commit your changes
4. Open a pull request against `main`

## License

MIT License. See LICENSE for details.
