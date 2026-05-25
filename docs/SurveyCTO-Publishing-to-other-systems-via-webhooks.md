# SurveyCTO — Publishing to other systems via webhooks

> **About this document**  
> This is an **expanded companion guide** based on SurveyCTO’s official page  
> [Publishing to other systems via webhooks](https://docs.surveycto.com/05-exporting-and-publishing-data/03-publishing-data-to-the-cloud/05.forms-to-webhooks.html).  
> It keeps the **same section order** as the official documentation and adds practical detail for people building a webhook receiver.  
> It is **not** official SurveyCTO documentation. For authoritative product behavior, use SurveyCTO’s docs and support.

**Screenshots** below are from a SurveyCTO server console. Personal account details (email, notification counts) have been **redacted** for publication.

---

## Overview

Webhooks allow web services to trigger actions, push data, or otherwise connect to other web services. Initially the exclusive domain of programmers who sought to use certain technologies and conventions to connect systems, webhooks are increasingly useful to non-programmers as well.

You can use webhooks to publish incoming SurveyCTO form data to a wide variety of outside systems, but typically you will need some technical expertise and/or instructions from the receiving system in order to successfully configure everything.

### What you need on your side

| Requirement | Why |
|-------------|-----|
| **HTTPS URL** | SurveyCTO must POST to your server over the public internet. |
| **HTTP POST handler** | Your app accepts JSON in the request body. |
| **Fast response (200 OK)** | Return success quickly; do slow work afterward (database, downloads, queues). |
| **Field mapping** | Your code must understand the field names you select in the SurveyCTO console. |

---

## Getting started (server console)

You can get started by going to your server console's **Export** tab, scrolling down to the **Advanced: publishing form and dataset data to the cloud** section, and clicking the **ON/OFF** toggle to **ON** if you haven't already enabled cloud publishing.

![Export tab — enable Advanced cloud publishing](images/01-export-cloud-publishing-on.png)

*Figure 1: **4. Export** → **Advanced: publishing form and dataset data to the cloud** → toggle **ON**.*

### Checklist before adding a webhook

- [ ] Cloud publishing is **ON**
- [ ] Your receiving app is deployed and reachable at an **HTTPS** URL
- [ ] You know which **form** should send data
- [ ] You know which **fields** (and file questions) the receiver needs

---

## Configure a webhook for a form

To configure any one of your forms to publish via webhooks, click on the **Configure** option for that form, and then click **Add Webhook** in the panel that appears.

![Form publishing options — Add Webhook](images/02-form-publishing-add-webhook.png)

*Figure 2: **Configure** on a form → **Form publishing options** → **+ Add Webhook**. (Other connections such as Google Sheets or Zapier may already exist on your server.)*

### Webhook URL

Enter the **full URL** SurveyCTO should POST to, for example:

```text
https://api.example.org/webhook/surveycto
```

The path (`/webhook/surveycto`) must match what your application expects. In this repository’s example app, the default path is set in `app/config/appconfig.ini` under `[webhook] path`.

### Name and fields to publish

You'll first need to choose a good **name** for your webhook connection, based on the system to which you're publishing and what you intend to publish.

After that, you'll need to select exactly which **form fields** to publish:

- For **encrypted forms**, only form fields that have been explicitly marked as **publishable** will be listed.
- There's a **Select all** button if you simply want to publish all listed fields.

**Important:** The JSON body contains **only the fields you select** (plus any optional extras described below). If your receiver expects a field, you must publish it in this step.

![New webhook connection — name, URL, and fields](images/03-new-webhook-connection.png)

*Figure 3: **New webhook connection** — connection name, **Webhook URL**, and checkboxes for each field to publish. Use **Select all** if you want every listed field. Scroll the list for more fields (`KEY`, `username`, `formdef_id`, form questions, etc.).*

---

## Other options

Finally, you have a few other options available when configuring the webhook.

### 1. Hyperlink to the full submission

You can choose whether or not to include a **hyperlink to the full submission** in SurveyCTO, in the data that publishes to the webhook.

- If you do include the hyperlink, and you happen to also be publishing a form field named `submission_url`, **choose a different name** for the hyperlink to avoid a naming conflict.

**Receiver tip:** Store this link if operators need to open the submission in SurveyCTO for review or correction.

In the console you set **JSON element name for hyperlink** (for example `submission_url`).

---

### 2. Extra summary field (optional)

You can include **one extra field**, if you wish, as a text summary of the submission (e.g., as its title or alert text, depending on the system to which you're publishing).

If you choose to include an extra field, you can choose its **name** and its **contents**. In its contents, you can use **`${fieldname}`** references to include data from the submission being published, just like in a form label.

**Official example:**

```text
Submission received from ${enumerator_name}, for household headed by ${hh_head}
```

(Note, however, that you can only reference **publishable** fields in encrypted forms.)

#### Example: `survey_signature` via “Include text summary” (used in this repo)

SurveyCTO can add an **extra JSON field** built from `${fieldname}` references. You choose the **JSON element name** and the **JSON text** in the webhook screen — this is **not** a built-in SurveyCTO system field name; you pick the name (here: `survey_signature`).

![Webhook options — hyperlink, text summary, embed binary](images/04-webhook-options-text-summary.png)

*Figure 4: Example settings aligned with [suvita-public/surveycto-webhook-example](https://github.com/suvita-public/surveycto-webhook-example):*

| Option | Example setting |
|--------|-----------------|
| Include hyperlink to submission details? | **Checked** — JSON element name: `submission_url` |
| Include text summary? | **Checked** — JSON element name: `survey_signature` |
| JSON text | `${username}_${SubmissionDate}_${formdef_id}` |
| Embed binary fields? | **Unchecked** (files publish as metadata/hyperlinks) |

SurveyCTO substitutes `${username}`, `${SubmissionDate}`, and `${formdef_id}` when the webhook fires. The published JSON can look like:

```json
"survey_signature": "collector@example.org_2025-07-01T15:07:53.416Z_example_form"
```

**What the example receiver checks** (`app/services/webhook_service.py`): it rebuilds `{username}_{SubmissionDate}_{formdef_id}` and compares it to `survey_signature`. If they do not match, the request is rejected with HTTP 400.

This is a **simple integrity check** for demos or low-risk workflows. It is **not** a substitute for proper authentication (API keys, HMAC, IP allow lists, etc.) on production systems.

**Also publish** `username`, `SubmissionDate`, `formdef_id`, and `KEY` in the field list (Figure 3) so your server can use them independently of the summary string.

**Alternative:** you can use the same pattern in a **calculate** field inside the form and publish that field instead of (or in addition to) the text summary — as long as the JSON key and value format match what your receiver expects.

- Sample payload: [`examples/sample_submission.json`](../examples/sample_submission.json)
- Validation: `app/services/webhook_service.py` → `_validate_survey_signature()`

---

### 3. Embed binary fields (file attachments)

You can choose to **embed the contents of binary fields** (files attached to submissions) in the data published to the webhook.

| Setting | What the webhook contains |
|---------|---------------------------|
| **Embed OFF** (typical default) | File fields publish as **metadata and/or hyperlinks** — for example `filename`, `type`, and links to view files on SurveyCTO — not the raw file bytes inside JSON. |
| **Embed ON** | File **contents** may be included in the payload (larger body, slower processing). |

**Encrypted forms:** you **can't** embed binary fields.

#### How this example repo handles files (embed OFF)

When binary embed is off, a repeat group with image questions often looks like:

```json
"attachments": [
  { "file": { "filename": "photo-1.jpg", "type": "image/jpeg" } },
  { "file": { "filename": "photo-2.jpg", "type": "image/jpeg" } }
]
```

Repeat group and file field **names come from your form** (`attachments` / `file` are only examples). Map them in `app/config/appconfig.ini`:

```ini
attachment_repeat_group = attachments
attachment_field = file
```

The example app builds a view/download URL per file using `surveycto_attachment_base` and the submission `KEY`. See `examples/README.md` and `examples/sample_submission_register_photos.json` for another naming pattern.

---

### 4. Publish existing data

You can check **Publish existing data** if you want to publish **existing** form submissions.

| Checkbox | Behavior |
|----------|----------|
| **Checked** | Past submissions are also sent to the webhook. |
| **Unchecked** | Only **new** submissions that arrive **after** you configure the webhook are published. |

Use **Publish existing data** for backfills; leave it unchecked when you only want to process new data going forward.

---

## Publishing

As submissions come in to the server, your selected fields will be automatically published to your chosen webhook — but there will be a **brief delay of up to ten minutes**.

### What to expect

- SurveyCTO sends an **HTTP POST** with **JSON** to your webhook URL.
- Delivery is **not instant**; wait up to **10 minutes** when testing.
- Your endpoint should return **HTTP 200** (or another success code your team agrees on) **quickly**.
- Log the submission **`KEY`** (and time received) so you can match delayed deliveries and avoid duplicate processing.

### Common metadata fields

Exact fields depend on your form and what you selected to publish. Receivers often rely on:

| Field | Typical meaning |
|-------|-----------------|
| `KEY` | Unique submission id (often `uuid:...`) |
| `username` | Collector / enumerator account |
| `SubmissionDate` | ISO timestamp of submission |
| `formdef_id` | Form version identifier |

Plus any form fields you selected (text, selects, repeats, files, and custom calculate fields such as `survey_signature`).

---

## What the receiver should implement

This section expands on behavior implied by the official page — useful when writing or reviewing webhook code.

### HTTP contract

```http
POST /webhook/surveycto HTTP/1.1
Host: your-server.example.org
Content-Type: application/json

{ ... JSON body ... }
```

Recommended response:

```http
HTTP/1.1 200 OK
Content-Type: application/json

{ "response": "Success" }
```

Keep the handler fast. Move heavy steps (SQL, image download, external APIs) to a background job.

### Minimal sample payload

See `examples/sample_submission.json` in this repository. Illustrative shape:

```json
{
  "SubmissionDate": "2025-07-01T15:07:53.416Z",
  "username": "collector@example.org",
  "formdef_id": "example_form",
  "KEY": "uuid:00000000-0000-0000-0000-000000000001",
  "survey_signature": "collector@example.org_2025-07-01T15:07:53.416Z_example_form",
  "attachments": [
    { "file": { "filename": "photo-1.jpg", "type": "image/jpeg" } }
  ]
}
```

`survey_signature` appears only if you added and published that calculate field in your form.

### Local testing (this repo)

```bash
# Parse example JSON without SurveyCTO
python scripts/manual_webhook_test.py

# Or POST while the server is running
uvicorn app.main:app --host 0.0.0.0 --port 8000
curl -X POST http://localhost:8000/webhook/surveycto \
  -H "Content-Type: application/json" \
  -d @examples/sample_submission.json
```

---

## Troubleshooting

| Symptom | Things to check |
|---------|------------------|
| No POST received | Cloud publishing **ON**; webhook on the **correct form**; URL is **HTTPS** and public; wait **10 minutes** |
| 400 from example app | `survey_signature` mismatch — text summary must be `${username}_${SubmissionDate}_${formdef_id}` (same as Figure 4) or disable validation in code |
| Missing form fields | Field not selected in webhook config; encrypted field not **publishable** |
| No files / only filenames | **Embed binary** is off — expected; use SurveyCTO URLs or APIs to fetch bytes |
| Wrong attachment structure | `attachment_repeat_group` / `attachment_field` in `appconfig.ini` must match **your** form JSON keys |
| Timeouts or errors on SurveyCTO side | Receiver too slow or returns 5xx — return **200** quickly and process async |

---

## Related resources

| Resource | Link |
|----------|------|
| Official SurveyCTO page | [Publishing to other systems via webhooks](https://docs.surveycto.com/05-exporting-and-publishing-data/03-publishing-data-to-the-cloud/05.forms-to-webhooks.html) |
| Cloud publishing overview | [Introduction to cloud publishing](https://docs.surveycto.com/05-exporting-and-publishing-data/03-publishing-data-to-the-cloud/) |
| This example (FastAPI) | [github.com/suvita-public/surveycto-webhook-example](https://github.com/suvita-public/surveycto-webhook-example) |
| Example payloads | [`examples/README.md`](../examples/README.md) |

---

## Sharing feedback with SurveyCTO

If you want SurveyCTO to update their official page, you can send them this document (or a PDF export) via the [SurveyCTO Support Center](https://www.surveycto.com/support/) and reference the official URL above. Clearly state which sections are **suggested additions** versus the existing official text.
