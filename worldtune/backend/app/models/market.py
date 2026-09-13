"""Financial Pulse tables: `market_assets`, `market_prices`, `market_signals`.

`market_prices` is a plain OHLCV bar series keyed by (asset, timestamp) so the
trend engine can compute returns, momentum and volume z-scores with real
time-series maths rather than a stored "trend" string.

`market_signals` holds the *derived* per-asset snapshot (momentum, news
intensity, sentiment, volume z-score) that feeds the WorldTune score. It is
recomputed, never hand-authored.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Float, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, JSONColumn, UTCDateTime, utcnow


class MarketAssetORM(Base):
    __tablename__ = "market_assets"

    id: Mapped[str] = mapped_column(String, primary_key=True)   # e.g. "BTC", "NVDA"
    symbol: Mapped[str] = mapped_column(String, index=True)
    name: Mapped[str] = mapped_column(String, default="")
    asset_class: Mapped[str] = mapped_column(String, index=True)  # crypto|equity|etf
    sector: Mapped[str] = mapped_column(String, default="", index=True)
    provider_id: Mapped[str] = mapped_column(String, default="")  # e.g. coingecko "bitcoin"
    currency: Mapped[str] = mapped_column(String, default="USD")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, index=True)


class MarketPriceORM(Base):
    __tablename__ = "market_prices"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    asset_id: Mapped[str] = mapped_column(ForeignKey("market_assets.id"), index=True)
    timestamp: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    open: Mapped[float] = mapped_column(Float, default=0.0)
    high: Mapped[float] = mapped_column(Float, default=0.0)
    low: Mapped[float] = mapped_column(Float, default=0.0)
    close: Mapped[float] = mapped_column(Float, default=0.0)
    volume: Mapped[float] = mapped_column(Float, default=0.0)
    source: Mapped[str] = mapped_column(String, default="")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    __table_args__ = (
        UniqueConstraint("asset_id", "timestamp", name="uq_market_price_asset_ts"),
        Index("ix_market_prices_asset_ts", "asset_id", "timestamp"),
    )


class MarketSignalORM(Base):
    """Derived per-asset snapshot. Recomputed by the analytics pass."""

    __tablename__ = "market_signals"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    asset_id: Mapped[str] = mapped_column(ForeignKey("market_assets.id"), index=True)
    computed_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, index=True)
    price: Mapped[float] = mapped_column(Float, default=0.0)
    change_24h_pct: Mapped[float] = mapped_column(Float, default=0.0)
    change_7d_pct: Mapped[float] = mapped_column(Float, default=0.0)
    change_30d_pct: Mapped[float] = mapped_column(Float, default=0.0)
    momentum: Mapped[float] = mapped_column(Float, default=0.0)        # EWMA momentum, z-like
    acceleration: Mapped[float] = mapped_column(Float, default=0.0)    # 2nd derivative
    volume_zscore: Mapped[float] = mapped_column(Float, default=0.0)
    news_intensity: Mapped[float] = mapped_column(Float, default=0.0)  # normalized 0..1
    news_sentiment: Mapped[float] = mapped_column(Float, default=0.0)  # [-1, 1]
    extra: Mapped[dict] = mapped_column(JSONColumn, default=dict)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
