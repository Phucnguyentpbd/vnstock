from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

import pandas as pd


@dataclass
class IndexSnapshot:
    symbol: str
    close: float
    change: float
    percent_change: float
    volume: float
    volume_vs_20d: float | None
    session_date: date | None


@dataclass
class MarketDigest:
    indices: list[IndexSnapshot]
    advancers: int
    decliners: int
    unchanged: int
    total_value: float
    total_volume: float
    foreign_net_volume: float
    foreign_net_value_est: float
    gainers: list[dict]
    losers: list[dict]
    liquidity: list[dict]
    session_date: date | None


def _date(value) -> date | None:
    if value is None:
        return None
    if isinstance(value, pd.Timestamp):
        return value.date()
    if isinstance(value, datetime):
        return value.date()
    try:
        return pd.to_datetime(value).date()
    except (TypeError, ValueError):
        return None


def _num(value) -> float:
    try:
        value = float(value)
        return 0.0 if pd.isna(value) else value
    except (TypeError, ValueError):
        return 0.0


class VnstockMarketCollector:
    def _facades(self):
        from vnstock import Market, Reference
        return Market(), Reference()

    def _index(self, market, symbol: str) -> IndexSnapshot | None:
        df = market.index(symbol).ohlcv(count=25)
        if df is None or len(df) < 2:
            return None
        data = df.copy()
        time_col = next((c for c in ("time", "date", "trading_date") if c in data.columns), None)
        if time_col:
            data = data.sort_values(time_col)
        latest, previous = data.iloc[-1], data.iloc[-2]
        close, prev_close = _num(latest.get("close")), _num(previous.get("close"))
        change = close - prev_close
        pct = change / prev_close * 100 if prev_close else 0.0
        volume = _num(latest.get("volume"))
        history = data.iloc[:-1].tail(20)
        avg = pd.to_numeric(history["volume"], errors="coerce").mean() if "volume" in history else float("nan")
        ratio = volume / float(avg) if pd.notna(avg) and avg else None
        return IndexSnapshot(symbol, close, change, pct, volume, ratio, _date(latest.get(time_col)) if time_col else None)

    def _hose_quotes(self, market, reference) -> pd.DataFrame:
        universe = reference.equity.list_by_group("HOSE")
        if universe is None or universe.empty:
            return pd.DataFrame()
        col = next((c for c in ("symbol", "ticker", "code") if c in universe.columns), None)
        if not col:
            return pd.DataFrame()
        symbols = universe[col].dropna().astype(str).str.upper().drop_duplicates().tolist()
        frames = []
        for start in range(0, len(symbols), 80):
            try:
                df = market.quote(symbols[start:start + 80], source="kbs")
            except Exception:
                continue
            if df is not None and not df.empty:
                frames.append(df)
        return pd.concat(frames, ignore_index=True).drop_duplicates("symbol", keep="last") if frames else pd.DataFrame()

    def collect(self) -> MarketDigest:
        market, reference = self._facades()
        indices = [x for symbol in ("VNINDEX", "VN30", "HNXINDEX", "UPCOMINDEX") if (x := self._index(market, symbol))]
        quotes = self._hose_quotes(market, reference)
        if quotes.empty:
            return MarketDigest(indices, 0, 0, 0, 0, 0, 0, 0, [], [], [], indices[0].session_date if indices else None)

        pct = pd.to_numeric(quotes.get("percent_change"), errors="coerce").fillna(0)
        total_value = pd.to_numeric(quotes.get("total_value"), errors="coerce").fillna(0)
        total_volume = pd.to_numeric(quotes.get("volume_accumulated"), errors="coerce").fillna(0)
        fb = pd.to_numeric(quotes.get("foreign_buy_volume"), errors="coerce").fillna(0)
        fs = pd.to_numeric(quotes.get("foreign_sell_volume"), errors="coerce").fillna(0)
        avg = pd.to_numeric(quotes.get("average_price"), errors="coerce").fillna(0)
        q = quotes.copy()
        q["percent_change"] = pct
        q["total_value"] = total_value
        q["foreign_net_volume"] = fb - fs

        cols = ["symbol", "percent_change", "close_price", "total_value", "foreign_net_volume"]
        gainers = q.sort_values("percent_change", ascending=False).head(5)[cols].to_dict("records")
        losers = q.sort_values("percent_change", ascending=True).head(5)[cols].to_dict("records")
        liquidity = q.sort_values("total_value", ascending=False).head(5)[cols].to_dict("records")
        session = next((i.session_date for i in indices if i.symbol == "VNINDEX"), None)
        return MarketDigest(
            indices=indices,
            advancers=int((pct > 0).sum()),
            decliners=int((pct < 0).sum()),
            unchanged=int((pct == 0).sum()),
            total_value=float(total_value.sum()),
            total_volume=float(total_volume.sum()),
            foreign_net_volume=float((fb - fs).sum()),
            foreign_net_value_est=float(((fb - fs) * avg).sum()),
            gainers=gainers,
            losers=losers,
            liquidity=liquidity,
            session_date=session,
        )
