from fastapi import FastAPI

from app.api.routes_webhook import router as webhook_router
from app.config.config_loader import dict_configs, logger

app = FastAPI(
    title="surveycto-webhook-example",
    description="Reference FastAPI app for receiving SurveyCTO webhook POSTs",
    version="1.0.0",
)

webhook_path = dict_configs.get("webhook", {}).get("path", "/webhook/surveycto")
app.include_router(webhook_router, tags=["Webhook"])


@app.get("/health")
async def health_check():
    return {"status": "ok"}


logger.info("surveycto-webhook-example started; webhook path=%s", webhook_path)
