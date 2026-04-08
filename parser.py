import re
from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class Trade:
    symbol: str
    direction: str          # 多 / 空
    leverage: int
    margin_mode: str        # 全倉 / 逐倉
    realized_pnl: float     # 已實現盈虧（含手續費）
    close_pnl: float        # 平倉盈虧（不含手續費）
    entry_price: float
    exit_price: float
    open_volume: float      # 總開倉量 USDT
    close_volume: float     # 總平倉量 USDT
    open_time: str
    close_time: str

    # 衍生欄位
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
            # 跨日處理
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
    """移除逗號、空格後轉float"""
    return float(text.replace(",", "").strip())


def parse_trades(raw_text: str) -> list[Trade]:
    """
    解析用戶貼上的BingX倉位歷史文字
    支援多筆交易連續貼上
    """
    trades = []

    # 用「完全平倉」作為每筆交易的分隔點（行首匹配）
    blocks = re.split(r'\n(?=\S.*完全平倉)', raw_text.strip())
    blocks = [b.strip() for b in blocks if b.strip()]

    for block in blocks:
        try:
            trade = parse_single_trade(block)
            if trade:
                trades.append(trade)
        except Exception as e:
            print(f"[解析失敗] {e}\n區塊內容：\n{block[:100]}\n")

    return trades


def parse_single_trade(block: str) -> Optional[Trade]:
    """解析單筆交易區塊"""
    lines = [l.strip() for l in block.splitlines() if l.strip()]

    # --- 幣種 ---
    symbol_match = re.match(r'^(.+?)\s+完全平倉', lines[0].replace('\u200b', ''))
    if not symbol_match:
        return None
    symbol = symbol_match.group(1).strip()

    # --- 方向 / 倉位模式 / 槓桿 ---
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
                # 取label後面的數字部分
                value = line.replace(label, "").strip()
                value = re.sub(r'\(USDT\)', '', value).strip()
                # 只保留數字、小數點、負號、逗號
                value = re.sub(r'[^\d\.\-,]', '', value)
                return value if value else None
        return None

    realized_pnl = extract("已實現盈虧")
    close_pnl    = extract("平倉盈虧")
    entry_price  = extract("開倉均價")
    exit_price   = extract("平倉均價")
    open_volume  = extract("總開倉量")
    close_volume = extract("總平倉量")

    # 時間單獨處理（保留 / 和 :）
    open_time, close_time = None, None
    for line in lines:
        t_match = re.search(r'(\d{2}/\d{2}\s+\d{2}:\d{2})', line)
        if t_match:
            if "開倉" in line:
                open_time = t_match.group(1)
            elif "平倉" in line:
                close_time = t_match.group(1)

    # 必填欄位檢查
    required = [realized_pnl, close_pnl, entry_price, exit_price,
                open_volume, close_volume, open_time, close_time,
                direction, leverage]
    if any(v is None for v in required):
        missing = [name for name, val in zip(
            ["realized_pnl","close_pnl","entry_price","exit_price",
             "open_volume","close_volume","open_time","close_time",
             "direction","leverage"], required) if val is None]
        raise ValueError(f"缺少欄位：{missing}")

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


# ── 測試 ──────────────────────────────────────────────
if __name__ == "__main__":
    sample = """
GOLD(XAU) 完全平倉
空 全倉 500X
已實現盈虧 (USDT) -2.9823
平倉盈虧 (USDT) -2.0822
開倉均價 4,682.12
平倉均價 4,684.07
總開倉量 (USDT) 4999.56
總平倉量 (USDT) 5001.64
開倉時間 04/06 15:57
平倉時間 04/06 15:58
保證金變動記錄 詳情

GOLD(XAU) 完全平倉
空 全倉 500X
已實現盈虧 (USDT) -16.2643
平倉盈虧 (USDT) -13.5633
開倉均價 4,663.05
平倉均價 4,667.27
總開倉量 (USDT) 14999.17
總平倉量 (USDT) 15012.74
開倉時間 04/06 15:44
平倉時間 04/06 15:49
保證金變動記錄 詳情
"""

    trades = parse_trades(sample)
    print(f"解析到 {len(trades)} 筆交易\n")
    for i, t in enumerate(trades, 1):
        print(f"── 第{i}筆 ──")
        for k, v in t.to_dict().items():
            print(f"  {k}: {v}")
        print()
