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

    @property
    def fee(self) -> float:
        return round(self.realized_pnl - self.close_pnl, 6)

    @property
    def holding_minutes(self) -> Optional[float]:
        fmts = ["%Y-%m-%d %H:%M:%S", "%m/%d %H:%M"]
        for fmt in fmts:
            try:
                t1 = datetime.strptime(self.open_time, fmt)
                t2 = datetime.strptime(self.close_time, fmt)
                diff = (t2 - t1).total_seconds() / 60
                if diff < 0:
                    diff += 24 * 60
                return round(diff, 1)
            except Exception:
                continue
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
    cleaned = re.sub(r'[^\d\.\-]', '', text.replace(',', ''))
    return float(cleaned)


# ── 自動偵測格式 ──────────────────────────────────────────

def parse_trades(raw_text: str) -> list[Trade]:
    if re.search(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', raw_text):
        return parse_trades_web(raw_text)
    return parse_trades_app(raw_text)


# ── 網頁版解析器（YYYY-MM-DD HH:MM:SS 格式）────────────────

def parse_trades_web(raw_text: str) -> list[Trade]:
    trades = []
    lines = [l.strip() for l in raw_text.strip().splitlines()]

    i = 0
    while i < len(lines):
        # 找到開倉時間行（YYYY-MM-DD HH:MM:SS）作為每筆的起點
        if not re.match(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$', lines[i]):
            i += 1
            continue

        # 蒐集這筆交易的所有行直到「完全平倉」或「強平」
        block_start = i
        block_lines = []
        while i < len(lines):
            block_lines.append(lines[i])
            if lines[i] in ('完全平倉', '強平'):
                i += 1
                break
            i += 1
        else:
            # 到達文字末尾但還沒遇到結束標記，嘗試解析
            pass

        try:
            trade = parse_single_trade_web(block_lines)
            if trade:
                trades.append(trade)
        except Exception as e:
            print(f"[網頁版解析失敗] {e}\n區塊：{block_lines[:3]}\n")

    return trades


def parse_single_trade_web(lines: list[str]) -> Optional[Trade]:
    # 必須至少有 open_time, close_time, symbol, direction, margin, leverage
    if len(lines) < 12:
        return None

    open_time  = lines[0]  # YYYY-MM-DD HH:MM:SS
    close_time = lines[1]
    symbol     = lines[2]
    direction  = lines[3]  # 多 / 空
    margin_mode = lines[4] # 全倉 / 逐倉

    lev_match = re.search(r'(\d+)X', lines[5])
    if not lev_match:
        return None
    leverage = int(lev_match.group(1))

    # 從第7行開始收集含 USDT 的數值行（跳過贈金券等雜訊）
    usdt_lines = []
    for line in lines[6:]:
        if line in ('檢視', '完全平倉', '強平'):
            continue
        if 'USDT' in line:
            usdt_lines.append(line)

    # 需要：開倉均價、平倉均價、總開倉量、總平倉量、已實現盈虧、平倉盈虧（共6個）
    if len(usdt_lines) < 6:
        return None

    entry_price  = parse_number(usdt_lines[0])
    exit_price   = parse_number(usdt_lines[1])
    open_volume  = parse_number(usdt_lines[2])
    close_volume = parse_number(usdt_lines[3])
    realized_pnl = parse_number(usdt_lines[4])
    close_pnl    = parse_number(usdt_lines[5])

    return Trade(
        symbol=symbol,
        direction=direction,
        leverage=leverage,
        margin_mode=margin_mode,
        realized_pnl=realized_pnl,
        close_pnl=close_pnl,
        entry_price=entry_price,
        exit_price=exit_price,
        open_volume=open_volume,
        close_volume=close_volume,
        open_time=open_time,
        close_time=close_time,
    )


# ── App版解析器（MM/DD HH:MM 格式）───────────────────────

def parse_trades_app(raw_text: str) -> list[Trade]:
    trades = []
    blocks = re.split(r'\n(?=\S.*完全平倉)', raw_text.strip())
    blocks = [b.strip() for b in blocks if b.strip()]

    for block in blocks:
        try:
            trade = parse_single_trade_app(block)
            if trade:
                trades.append(trade)
        except Exception as e:
            print(f"[App版解析失敗] {e}\n區塊：{block[:100]}\n")

    return trades


def parse_single_trade_app(block: str) -> Optional[Trade]:
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
        missing = [name for name, val in zip(
            ["realized_pnl", "close_pnl", "entry_price", "exit_price",
             "open_volume", "close_volume", "open_time", "close_time",
             "direction", "leverage"], required) if val is None]
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
    web_sample = """
2026-04-08 13:33:38
2026-04-08 13:38:16
GOLD(XAU)
多
全倉
500X
4,814.87USDT
4,811.14USDT
19,999.06USDT
19,983.55USDT
-19.1085USDT
-15.5101USDT
檢視
完全平倉

2026-04-08 14:00:00
2026-04-08 14:05:30
BTCUSDT
空
逐倉
100X
95,000.00USDT
94,800.00USDT
10,000.00USDT
10,021.00USDT
+18.5000USDT
+21.0000USDT
檢視
完全平倉
"""

    print("=== 網頁版格式測試 ===")
    trades = parse_trades(web_sample)
    print(f"解析到 {len(trades)} 筆交易\n")
    for i, t in enumerate(trades, 1):
        print(f"── 第{i}筆 ──")
        for k, v in t.to_dict().items():
            print(f"  {k}: {v}")
        print()
