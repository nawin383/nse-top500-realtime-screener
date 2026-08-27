"""Webhook management for alerts."""
from __future__ import annotations
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, HttpUrl, Field
from datetime import datetime
import httpx
import json
from pathlib import Path
from loguru import logger

router = APIRouter()

# Storage
webhooks_storage: Dict[str, "Webhook"] = {}
WEBHOOKS_FILE = Path("data/webhooks.json")


class Webhook(BaseModel):
    """Webhook configuration."""
    id: str
    url: HttpUrl
    name: str
    enabled: bool = True
    created_at: datetime = Field(default_factory=datetime.now)
    events: List[str] = ["alert"]  # alert, breakout, volume_spike, etc.
    headers: Dict[str, str] = {}
    retry_count: int = 3
    timeout_sec: int = 10


class CreateWebhookRequest(BaseModel):
    """Request to create webhook."""
    url: HttpUrl
    name: str = Field(..., min_length=1, max_length=100)
    events: List[str] = ["alert"]
    headers: Dict[str, str] = {}


class WebhookDelivery(BaseModel):
    """Webhook delivery record."""
    webhook_id: str
    event_type: str
    payload: Dict[str, Any]
    status: str  # success, failed, pending
    attempts: int = 0
    last_attempt: Optional[datetime] = None
    response_code: Optional[int] = None
    error: Optional[str] = None


def _load_webhooks():
    """Load webhooks from file."""
    global webhooks_storage
    if WEBHOOKS_FILE.exists():
        try:
            with open(WEBHOOKS_FILE, "r") as f:
                data = json.load(f)
                webhooks_storage = {k: Webhook(**v) for k, v in data.items()}
        except Exception:
            webhooks_storage = {}
    else:
        webhooks_storage = {}


def _save_webhooks():
    """Save webhooks to file."""
    WEBHOOKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(WEBHOOKS_FILE, "w") as f:
        json.dump(
            {k: v.model_dump(mode="json") for k, v in webhooks_storage.items()},
            f,
            indent=2,
            default=str
        )


async def trigger_webhook(webhook: Webhook, event_type: str, payload: Dict[str, Any]):
    """Send webhook HTTP request."""
    delivery = WebhookDelivery(
        webhook_id=webhook.id,
        event_type=event_type,
        payload=payload,
        status="pending"
    )

    for attempt in range(webhook.retry_count):
        try:
            async with httpx.AsyncClient(timeout=webhook.timeout_sec) as client:
                response = await client.post(
                    str(webhook.url),
                    json={
                        "event": event_type,
                        "data": payload,
                        "timestamp": datetime.now().isoformat(),
                        "webhook_id": webhook.id
                    },
                    headers=webhook.headers
                )

                delivery.attempts = attempt + 1
                delivery.last_attempt = datetime.now()
                delivery.response_code = response.status_code

                if 200 <= response.status_code < 300:
                    delivery.status = "success"
                    logger.info(f"Webhook {webhook.id} delivered successfully")
                    return delivery
                else:
                    delivery.error = f"HTTP {response.status_code}"

        except Exception as e:
            delivery.attempts = attempt + 1
            delivery.last_attempt = datetime.now()
            delivery.error = str(e)
            logger.warning(f"Webhook {webhook.id} delivery failed (attempt {attempt + 1}): {e}")

    delivery.status = "failed"
    return delivery


async def broadcast_webhook_event(event_type: str, payload: Dict[str, Any]):
    """Broadcast event to all matching webhooks."""
    for webhook in webhooks_storage.values():
        if webhook.enabled and event_type in webhook.events:
            await trigger_webhook(webhook, event_type, payload)


# Load on startup
_load_webhooks()


@router.get("/webhooks", response_model=List[Webhook])
async def list_webhooks():
    """List all webhooks."""
    return list(webhooks_storage.values())


@router.post("/webhooks", response_model=Webhook)
async def create_webhook(req: CreateWebhookRequest):
    """Create new webhook."""
    import uuid
    webhook_id = str(uuid.uuid4())

    webhook = Webhook(
        id=webhook_id,
        url=req.url,
        name=req.name,
        events=req.events,
        headers=req.headers
    )

    webhooks_storage[webhook_id] = webhook
    _save_webhooks()

    return webhook


@router.get("/webhooks/{webhook_id}", response_model=Webhook)
async def get_webhook(webhook_id: str):
    """Get specific webhook."""
    if webhook_id not in webhooks_storage:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return webhooks_storage[webhook_id]


@router.put("/webhooks/{webhook_id}/enabled")
async def toggle_webhook(webhook_id: str, enabled: bool):
    """Enable/disable webhook."""
    if webhook_id not in webhooks_storage:
        raise HTTPException(status_code=404, detail="Webhook not found")

    webhooks_storage[webhook_id].enabled = enabled
    _save_webhooks()

    return {"webhook_id": webhook_id, "enabled": enabled}


@router.delete("/webhooks/{webhook_id}")
async def delete_webhook(webhook_id: str):
    """Delete webhook."""
    if webhook_id not in webhooks_storage:
        raise HTTPException(status_code=404, detail="Webhook not found")

    del webhooks_storage[webhook_id]
    _save_webhooks()

    return {"status": "deleted", "webhook_id": webhook_id}


@router.post("/webhooks/{webhook_id}/test")
async def test_webhook(webhook_id: str, background_tasks: BackgroundTasks):
    """Test webhook by sending a test payload."""
    if webhook_id not in webhooks_storage:
        raise HTTPException(status_code=404, detail="Webhook not found")

    webhook = webhooks_storage[webhook_id]

    test_payload = {
        "test": True,
        "message": "This is a test webhook",
        "timestamp": datetime.now().isoformat()
    }

    # Trigger in background
    background_tasks.add_task(trigger_webhook, webhook, "test", test_payload)

    return {"status": "test_queued", "webhook_id": webhook_id}
