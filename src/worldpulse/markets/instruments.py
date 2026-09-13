"""Hardcoded universe of ~18 tradable instruments tracked by WorldPulse."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Instrument:
    symbol: str
    display_name: str
    asset_class: str  # metal, energy, equity_index, volatility, sector_etf, fx, crypto


INSTRUMENTS: list[Instrument] = [
    Instrument("GC=F", "Gold", "metal"),
    Instrument("SI=F", "Silver", "metal"),
    Instrument("BZ=F", "Brent Crude", "energy"),
    Instrument("CL=F", "WTI Crude", "energy"),
    Instrument("NG=F", "Natural Gas", "energy"),
    Instrument("^GSPC", "S&P 500", "equity_index"),
    Instrument("^IXIC", "Nasdaq Composite", "equity_index"),
    Instrument("^VIX", "CBOE Volatility Index", "volatility"),
    Instrument("SOXX", "Semiconductor ETF", "sector_etf"),
    Instrument("XLE", "Energy Sector ETF", "sector_etf"),
    Instrument("DX-Y.NYB", "US Dollar Index", "fx"),
    Instrument("EURUSD=X", "EUR/USD", "fx"),
    Instrument("JPY=X", "USD/JPY", "fx"),
    Instrument("BTC-USD", "Bitcoin", "crypto"),
    Instrument("ETH-USD", "Ethereum", "crypto"),
    # +3 additional instruments from the spec's broader list
    Instrument("HG=F", "Copper", "metal"),
    Instrument("ITA", "Aerospace & Defense ETF", "sector_etf"),
    Instrument("TLT", "20+ Year Treasury Bond ETF", "bond_etf"),
    # India-focused instruments: added so events flagged with country focus
    # "IN" (see config.COUNTRY_FOCUS / EVENT_COUNTRY_FOCUS) map to relevant,
    # tradable local proxies instead of only global instruments.
    Instrument("^NSEI", "Nifty 50", "equity_index"),
    Instrument("^BSESN", "BSE Sensex", "equity_index"),
    Instrument("INR=X", "USD/INR", "fx"),
    Instrument("INDA", "iShares MSCI India ETF", "sector_etf"),
]

INSTRUMENTS_BY_SYMBOL: dict[str, Instrument] = {i.symbol: i for i in INSTRUMENTS}

# Per-asset-class base annualized volatility used to seed synthetic price
# generation, roughly calibrated to realistic historical levels.
ASSET_CLASS_ANNUAL_VOL: dict[str, float] = {
    "metal": 0.18,
    "energy": 0.35,
    "equity_index": 0.16,
    "volatility": 0.80,
    "sector_etf": 0.28,
    "fx": 0.09,
    "crypto": 0.65,
    "bond_etf": 0.10,
}


def all_symbols() -> list[str]:
    return [i.symbol for i in INSTRUMENTS]
