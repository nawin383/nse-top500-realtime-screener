"""Watchlist management API endpoints."""
from __future__ import annotations
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from datetime import datetime
import json
from pathlib import Path

router = APIRouter()

# In-memory storage (consider Redis/DB for production)
watchlists_storage: dict = {}
WATCHLISTS_FILE = Path("data/watchlists.json")


class WatchlistItem(BaseModel):
    """Individual watchlist item."""
    symbol: str
    added_at: datetime = Field(default_factory=datetime.now)
    notes: Optional[str] = None
    alert_enabled: bool = False
    alert_price_above: Optional[float] = None
    alert_price_below: Optional[float] = None
    alert_volume_spike: bool = False


class Watchlist(BaseModel):
    """Watchlist model."""
    id: str
    name: str
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    stocks: List[WatchlistItem] = []
    color: Optional[str] = "#3b82f6"
    is_default: bool = False


class CreateWatchlistRequest(BaseModel):
    """Request to create watchlist."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    color: Optional[str] = "#3b82f6"


class AddStockRequest(BaseModel):
    """Request to add stock to watchlist."""
    symbol: str = Field(..., min_length=1)
    notes: Optional[str] = None
    alert_enabled: bool = False
    alert_price_above: Optional[float] = None
    alert_price_below: Optional[float] = None
    alert_volume_spike: bool = False


def _load_watchlists():
    """Load watchlists from file."""
    global watchlists_storage
    if WATCHLISTS_FILE.exists():
        try:
            with open(WATCHLISTS_FILE, "r") as f:
                data = json.load(f)
                watchlists_storage = {k: Watchlist(**v) for k, v in data.items()}
        except Exception:
            watchlists_storage = {}
    else:
        watchlists_storage = {}


def _save_watchlists():
    """Save watchlists to file."""
    WATCHLISTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(WATCHLISTS_FILE, "w") as f:
        json.dump(
            {k: v.model_dump(mode="json") for k, v in watchlists_storage.items()},
            f,
            indent=2,
            default=str
        )


# Load on startup
_load_watchlists()


@router.get("/watchlists", response_model=List[Watchlist])
async def list_watchlists():
    """List all watchlists."""
    return list(watchlists_storage.values())


@router.post("/watchlists", response_model=Watchlist)
async def create_watchlist(req: CreateWatchlistRequest):
    """Create new watchlist."""
    import uuid
    watchlist_id = str(uuid.uuid4())

    watchlist = Watchlist(
        id=watchlist_id,
        name=req.name,
        description=req.description,
        color=req.color
    )

    watchlists_storage[watchlist_id] = watchlist
    _save_watchlists()

    return watchlist


@router.get("/watchlists/{watchlist_id}", response_model=Watchlist)
async def get_watchlist(watchlist_id: str):
    """Get specific watchlist."""
    if watchlist_id not in watchlists_storage:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    return watchlists_storage[watchlist_id]


@router.put("/watchlists/{watchlist_id}", response_model=Watchlist)
async def update_watchlist(watchlist_id: str, req: CreateWatchlistRequest):
    """Update watchlist metadata."""
    if watchlist_id not in watchlists_storage:
        raise HTTPException(status_code=404, detail="Watchlist not found")

    watchlist = watchlists_storage[watchlist_id]
    watchlist.name = req.name
    watchlist.description = req.description
    watchlist.color = req.color
    watchlist.updated_at = datetime.now()

    _save_watchlists()
    return watchlist


@router.delete("/watchlists/{watchlist_id}")
async def delete_watchlist(watchlist_id: str):
    """Delete watchlist."""
    if watchlist_id not in watchlists_storage:
        raise HTTPException(status_code=404, detail="Watchlist not found")

    del watchlists_storage[watchlist_id]
    _save_watchlists()

    return {"status": "deleted", "watchlist_id": watchlist_id}


@router.post("/watchlists/{watchlist_id}/stocks", response_model=Watchlist)
async def add_stock_to_watchlist(watchlist_id: str, req: AddStockRequest):
    """Add stock to watchlist."""
    if watchlist_id not in watchlists_storage:
        raise HTTPException(status_code=404, detail="Watchlist not found")

    watchlist = watchlists_storage[watchlist_id]

    # Check if already exists
    if any(s.symbol == req.symbol.upper() for s in watchlist.stocks):
        raise HTTPException(status_code=400, detail="Stock already in watchlist")

    item = WatchlistItem(
        symbol=req.symbol.upper(),
        notes=req.notes,
        alert_enabled=req.alert_enabled,
        alert_price_above=req.alert_price_above,
        alert_price_below=req.alert_price_below,
        alert_volume_spike=req.alert_volume_spike
    )

    watchlist.stocks.append(item)
    watchlist.updated_at = datetime.now()

    _save_watchlists()
    return watchlist


@router.delete("/watchlists/{watchlist_id}/stocks/{symbol}")
async def remove_stock_from_watchlist(watchlist_id: str, symbol: str):
    """Remove stock from watchlist."""
    if watchlist_id not in watchlists_storage:
        raise HTTPException(status_code=404, detail="Watchlist not found")

    watchlist = watchlists_storage[watchlist_id]
    watchlist.stocks = [s for s in watchlist.stocks if s.symbol != symbol.upper()]
    watchlist.updated_at = datetime.now()

    _save_watchlists()
    return {"status": "removed", "symbol": symbol}


@router.put("/watchlists/{watchlist_id}/stocks/{symbol}", response_model=WatchlistItem)
async def update_watchlist_stock(watchlist_id: str, symbol: str, req: AddStockRequest):
    """Update stock settings in watchlist."""
    if watchlist_id not in watchlists_storage:
        raise HTTPException(status_code=404, detail="Watchlist not found")

    watchlist = watchlists_storage[watchlist_id]

    for item in watchlist.stocks:
        if item.symbol == symbol.upper():
            item.notes = req.notes
            item.alert_enabled = req.alert_enabled
            item.alert_price_above = req.alert_price_above
            item.alert_price_below = req.alert_price_below
            item.alert_volume_spike = req.alert_volume_spike
            watchlist.updated_at = datetime.now()
            _save_watchlists()
            return item

    raise HTTPException(status_code=404, detail="Stock not found in watchlist")
