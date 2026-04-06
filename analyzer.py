from collections import defaultdict
from parser import Trade


def analyze(trades: list[Trade]) -> dict:
    if not trades:
        return {}

    total = len(trades)
    wins = [t for t in trades if t.is_win]
    losses = [t for t in trades if not t.is_win]

    win_rate = len(wins) / total * 100
    avg_win = sum(t.close_pnl for t in wins) / len(wins) if wins else 0
    avg_loss = sum(t.close_pnl for t in losses) / len(losses) if losses else 0
    rr_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 0
    total_pnl = sum(t.close_pnl for t in trades)
    total_fee = sum(t.fee for t in trades)
    total_realized = sum(t.realized_pnl for t in trades)

    best_trade = max(trades, key=lambda t: t.close_pnl)
    worst_trade = min(trades, key=lambda t: t.close_pnl)

    win_times = [t.holding_minutes for t in wins if t.holding_minutes is not None]
    loss_times = [t.holding_minutes for t in losses if t.holding_minutes is not None]
    avg_win_hold = sum(win_times) / len(win_times) if win_times else 0
    avg_loss_hold = sum(loss_times) / len(loss_times) if loss_times else 0

    hour_stats = defaultdict(lambda: {"wins": 0, "losses": 0, "pnl": 0.0})
    for t in trades:
        try:
            hour = int(t.open_time.split(" ")[1].split(":")[0])
            if t.is_win:
                hour_stats[hour]["wins"] += 1
            else:
                hour_stats[hour]["losses"] += 1
            hour_stats[hour]["pnl"] += t.close_pnl
        except Exception:
            pass

    hour_winrates = {}
    for h, s in hour_stats.items():
        total_h = s["wins"] + s["losses"]
        hour_winrates[h] = {
            "win_rate": round(s["wins"] / total_h * 100, 1) if total_h else 0,
            "trades": total_h,
            "pnl": round(s["pnl"], 4),
        }

    best_hour = max(hour_winrates, key=lambda h: hour_winrates[h]["win_rate"]) if hour_winrates else None
    worst_hour = min(hour_winrates, key=lambda h: hour_winrates[h]["win_rate"]) if hour_winrates else None

    symbol_stats = defaultdict(lambda: {"wins": 0, "losses": 0, "pnl": 0.0, "trades": 0})
    for t in trades:
        s = symbol_stats[t.symbol]
        s["trades"] += 1
        s["pnl"] += t.close_pnl
        if t.is_win:
            s["wins"] += 1
        else:
            s["losses"] += 1

    for sym in symbol_stats:
        s = symbol_stats[sym]
        total_s = s["wins"] + s["losses"]
        s["win_rate"] = round(s["wins"] / total_s * 100, 1) if total_s else 0
        s["pnl"] = round(s["pnl"], 4)

    worst_symbol = min(symbol_stats, key=lambda s: symbol_stats[s]["pnl"]) if symbol_stats else None
    best_symbol = max(symbol_stats, key=lambda s: symbol_stats[s]["pnl"]) if symbol_stats else None

    high_lev = [t for t in trades if t.leverage >= 100]
    low_lev = [t for t in trades if t.leverage < 100]
    high_lev_wr = len([t for t in high_lev if t.is_win]) / len(high_lev) * 100 if high_lev else None
    low_lev_wr = len([t for t in low_lev if t.is_win]) / len(low_lev) * 100 if low_lev else None

    revenge_count = 0
    for i in range(1, len(trades)):
        prev = trades[i - 1]
        curr = trades[i]
        if not prev.is_win and curr.open_volume > prev.open_volume * 1.5:
            revenge_count += 1

    return {
        "summary": {
            "total_trades": total,
            "win_rate": round(win_rate, 1),
            "total_pnl": round(total_pnl, 4),
            "total_fee": round(total_fee, 4),
            "total_realized": round(total_realized, 4),
            "avg_win": round(avg_win, 4),
            "avg_loss": round(avg_loss, 4),
            "rr_ratio": round(rr_ratio, 2),
        },
        "holding_time": {
            "avg_win_minutes": round(avg_win_hold, 1),
            "avg_loss_minutes": round(avg_loss_hold, 1),
        },
        "best_trade": best_trade.to_dict(),
        "worst_trade": worst_trade.to_dict(),
        "hour_analysis": hour_winrates,
        "best_hour": best_hour,
        "worst_hour": worst_hour,
        "symbol_analysis": dict(symbol_stats),
        "best_symbol": best_symbol,
        "worst_symbol": worst_symbol,
        "leverage": {
            "high_lev_trades": len(high_lev),
            "high_lev_win_rate": round(high_lev_wr, 1) if high_lev_wr is not None else None,
            "low_lev_trades": len(low_lev),
            "low_lev_win_rate": round(low_lev_wr, 1) if low_lev_wr is not None else None,
        },
        "revenge_trading_count": revenge_count,
    }


def build_prompt(trades: list[Trade], analysis: dict) -> str:
    s = analysis["summary"]
    h = analysis["holding_time"]
    lev = analysis["leverage"]

    trade_lines = []
    for t in trades:
        trade_lines.append(
            f"{t.open_time} | {t.symbol} | {'多' if '多' in t.direction else '空'} | "
            f"{t.leverage}X | 盈虧:{t.close_pnl:+.2f} | 持倉:{t.holding_minutes}分鐘"
        )

    hour_lines = []
    for h_key, hv in sorted(analysis["hour_analysis"].items()):
        hour_lines.append(f"  {h_key:02d}:00 → 勝率{hv['win_rate']}% ({hv['trades']}筆) PnL:{hv['pnl']:+.2f}")

    sym_lines = []
    for sym, sv in analysis["symbol_analysis"].items():
        sym_lines.append(f"  {sym} → 勝率{sv['win_rate']}% ({sv['trades']}筆) 總PnL:{sv['pnl']:+.2f}")

    return f"""你是一個專業的加密貨幣/期貨交易分析師，請根據以下真實交易數據分析這位交易者的問題。

━━━ 交易記錄 ━━━
{chr(10).join(trade_lines)}

━━━ 統計摘要 ━━━
總交易筆數：{s['total_trades']}
勝率：{s['win_rate']}%
平均獲利：{s['avg_win']:+.4f} USDT
平均虧損：{s['avg_loss']:+.4f} USDT
盈虧比：1:{s['rr_ratio']}
總盈虧（不含手續費）：{s['total_pnl']:+.4f} USDT
總手續費：{s['total_fee']:+.4f} USDT
最終實現盈虧：{s['total_realized']:+.4f} USDT

━━━ 持倉時間 ━━━
獲利單平均持倉：{h['avg_win_minutes']} 分鐘
虧損單平均持倉：{h['avg_loss_minutes']} 分鐘

━━━ 時段勝率 ━━━
{chr(10).join(hour_lines)}

━━━ 幣種表現 ━━━
{chr(10).join(sym_lines)}

━━━ 槓桿使用 ━━━
高槓桿(≥100X)：{lev['high_lev_trades']}筆，勝率{lev['high_lev_win_rate']}%
低槓桿(<100X)：{lev['low_lev_trades']}筆，勝率{lev['low_lev_win_rate']}%

━━━ 情緒交易偵測 ━━━
連虧後加倉次數：{analysis['revenge_trading_count']}次

━━━ 你的任務 ━━━
請用繁體中文，按以下格式回答：

【最大問題】
用一句話說出這位交易者最核心的問題。

【數據診斷】
列出3個有具體數字支撐的問題。

【具體建議】
給出3條可以馬上執行的建議，必須有數字，不要空話。

語氣直接，不要客套。數字說話。
"""
