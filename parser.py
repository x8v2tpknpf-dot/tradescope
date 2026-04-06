import re
from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class Trade:
    symbol: str
    direction: str
    leverage: int
    margin_mode: str
    realized_pnl: float
    close_pnl: float
    entry_price: float
    exit_price: float
    open_volume: float
    close_volume: float
    open_time: str
    close_time: str

    @property
    def fee(self) -> float:
        return round(self.realized_pnl - self.close_pnl, 6)

    @property
    def holding_minutes(self) -> Optional[float]:
        try:
            fmt = "%m/%d %H:%M"
            t1 = datetime.strptime(self.open_time, fmt)
            t2 = datetime.strptime(self.close_time, fmt)
            diff = (t2 - t1).total_seconds() / 60
            if diff < 0:
                diff += 24 * 60
            return round(diff, 1)
        except Exception:
            return None

    @property
    def is_win(self) -> bool:
        return self.close_pnl > 0

    @property
    def price_change_pct(self) -> float:
        return round((self.exit_price - self.entry_price) / self.entry_price * 100, 4)

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "direction": self.direction,
            "leverage": self.leverage,
            "margin_mode": self.margin_mode,
            "realized_pnl": self.realized_pnl,
            "close_pnl": self.close_pnl,
            "fee": self.fee,
            "entry_price": self.entry_price,
            "exit_price": self.exit_price,
            "open_volume": self.open_volume,
            "close_volume": self.close_volume,
            "open_time": self.open_time,
            "close_time": self.close_time,
            "holding_minutes": self.holding_minutes,
            "is_win": self.is_win,
            "price_change_pct": self.price_change_pct,
        }


def parse_number(text: str) -> float:
    return float(text.replace(",", "").strip())


def parse_trades(raw_text: str) -> list[Trade]:
    trades = []
    blocks = re.split(r'\n(?=\S.*完全平倉)', raw_text.strip())
    blocks = [b.strip() for b in blocks if b.strip()]
    for block in blocks:
        try:
            trade = parse_single_trade(block)
            if trade:
                trades.append(trade)
        except Exception as e:
            print(f"[解析失敗] {e}")
    return trades


def parse_single_trade(block: str) -> Optional[Trade]:
    lines = [l.strip() for l in block.splitlines() if l.strip()]

    symbol_match = re.match(r'^(.+?)\s+完全平倉', lines[0].replace('\u200b', ''))
    if not symbol_match:
        return None
    symbol = symbol_match.group(1).strip()

    direction, margin_mode, leverage = None, None, None
    for line in lines[:5]:
        dir_match = re.search(r'(做多|做空|多|空)', line)
        margin_match = re.search(r'(全倉|逐倉)', line)
        lev_match = re.search(r'(\d+)X', line)
        if dir_match:
            direction = dir_match.group(1)
        if margin_match:
            margin_mode = margin_match.group(1)
        if lev_match:
            leverage = int(lev_match.group(1))

    def extract(label: str) -> Optional[str]:
        for line in lines:
            if label in line:
                value = line.replace(label, "").strip()
                value = re.sub(r'\(USDT\)', '', value).strip()
                value = re.sub(r'[^\d\.\-,]', '', value)
                return value if value else None
        return None

    realized_pnl = extract("已實現盈虧")
    close_pnl    = extract("平倉盈虧")
    entry_price  = extract("開倉均價")
    exit_price   = extract("平倉均價")
    open_volume  = extract("總開倉量")
    close_volume = extract("總平倉量")

    open_time, close_time = None, None
    for line in lines:
        t_match = re.search(r'(\d{2}/\d{2}\s+\d{2}:\d{2})', line)
        if t_match:
            if "開倉" in line:
                open_time = t_match.group(1)
            elif "平倉" in line:
                close_time = t_match.group(1)

    required = [realized_pnl, close_pnl, entry_price, exit_price,
                open_volume, close_volume, open_time, close_time,
                direction, leverage]
    if any(v is None for v in required):
        return None

    return Trade(
        symbol=symbol,
        direction=direction,
        leverage=leverage,
        margin_mode=margin_mode or "未知",
        realized_pnl=parse_number(realized_pnl),
        close_pnl=parse_number(close_pnl),
        entry_price=parse_number(entry_price),
        exit_price=parse_number(exit_price),
        open_volume=parse_number(open_volume),
        close_volume=parse_number(close_volume),
        open_time=open_time,
        close_time=close_time,
    )
