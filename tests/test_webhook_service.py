import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.services import webhook_service

EXAMPLE_PAYLOAD = {
    "SubmissionDate": "2025-07-01T15:07:53.416Z",
    "username": "collector@example.org",
    "formdef_id": "example_form",
    "KEY": "uuid:00000000-0000-0000-0000-000000000001",
    "survey_signature": "collector@example.org_2025-07-01T15:07:53.416Z_example_form",
    "attachments": [
        {"file": {"filename": "photo-1.jpg", "type": "image/jpeg"}},
        {"file": {"filename": "photo-2.jpg", "type": "image/jpeg"}},
    ],
}

WEBHOOK_PATH = "/webhook/surveycto"


@pytest.fixture(autouse=True)
def reset_latest_submission():
    webhook_service.latest_submission_df = None
    yield
    webhook_service.latest_submission_df = None


def test_build_submission_dataframe_shape_and_columns():
    df = webhook_service.build_submission_dataframe(EXAMPLE_PAYLOAD)

    assert len(df) == 2
    assert list(df.columns) == [
        "surveycto_key",
        "username",
        "formdef_id",
        "submission_date",
        "filename",
        "attachment_url",
    ]
    assert df["surveycto_key"].nunique() == 1
    assert set(df["filename"]) == {"photo-1.jpg", "photo-2.jpg"}
    assert df["attachment_url"].str.contains("photo-1.jpg").any()
    assert df["attachment_url"].str.contains("uuid%3A").all()


def test_build_submission_dataframe_missing_key():
    payload = dict(EXAMPLE_PAYLOAD)
    del payload["KEY"]

    with pytest.raises(HTTPException) as exc:
        webhook_service.build_submission_dataframe(payload)

    assert exc.value.status_code == 400


def test_build_submission_dataframe_no_attachments():
    payload = dict(EXAMPLE_PAYLOAD)
    payload["attachments"] = []

    with pytest.raises(HTTPException) as exc:
        webhook_service.build_submission_dataframe(payload)

    assert exc.value.status_code == 400


def test_webhook_endpoint_success():
    client = TestClient(app)
    response = client.post(WEBHOOK_PATH, json=EXAMPLE_PAYLOAD)

    assert response.status_code == 200
    body = response.json()
    assert body["response"] == "Success"
    assert body["row_count"] == 2

    latest = webhook_service.get_latest_submission()
    assert latest is not None
    assert len(latest) == 2


def test_webhook_endpoint_invalid_signature():
    client = TestClient(app)
    bad_payload = dict(EXAMPLE_PAYLOAD)
    bad_payload["survey_signature"] = "invalid"

    response = client.post(WEBHOOK_PATH, json=bad_payload)

    assert response.status_code == 400
