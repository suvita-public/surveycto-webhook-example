"""
Webhook HTTP route.

SurveyCTO is configured to POST submission JSON to the path in appconfig.ini
(default /webhook/surveycto). This module only wires the URL to webhook_service;
all parsing logic lives in app/services/webhook_service.py.
"""

from fastapi import APIRouter, Request

from app.config.config_loader import dict_configs, logger
from app.services import webhook_service
from app.utils.exception_handler import handle_exceptions

router = APIRouter()

# Path comes from [webhook] path in appconfig.ini so you can change it without editing code.
_webhook_path = dict_configs.get("webhook", {}).get("path", "/webhook/surveycto")


@router.post(_webhook_path, tags=["Webhook"])
@handle_exceptions  # logs errors and returns JSON 500 for unexpected failures
async def surveycto_webhook(request: Request):
    logger.info("SurveyCTO webhook endpoint called")
    return await webhook_service.handle_surveycto_webhook(request)
