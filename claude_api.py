import os
import re
import requests
from parser import parse_trades
from analyzer import analyze, build_prompt

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
API_URL = "https://api.anthropic.com/v1/messages"


def call_claude(prompt: str) -> str:
    if not ANTHROPIC_API_KEY:
        raise ValueError("請設定環境變數 ANTHROPIC_API_KEY")

    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    body = {
        "model": "claude-sonnet-4-6",
        "max_tokens": 1500,
        "messages": [{"role": "user", "content": prompt}],
    }

    response = requests.post(API_URL, headers=headers, json=body, timeout=30)

    if response.status_code != 200:
        raise RuntimeError(f"API錯誤 {response.status_code}: {response.text}")

    return response.json()["content"][0]["text"]


def extract_issues(ai_report: str) -> list[str]:
    issues = []
    match = re.search(r'【數據診斷】(.+?)(?=【|$)', ai_report, re.DOTALL)
    if match:
        block = match.group(1)
        for line in block.strip().splitlines():
            line = line.strip().lstrip("-•·").strip()
            if len(line) > 10:
                issues.append(line)
    return issues[:5]


def build_followup_prompt(trades, analysis: dict, last_issues: list[str]) -> str:
    base_prompt = build_prompt(trades, analysis)
    issues_text = "\n".join(f"- {issue}" for issue in last_issues)

    followup = f"""
━━━ 上次診斷的問題 ━━━
{issues_text}

━━━ 額外任務：改進追蹤 ━━━
在你的分析最後，加入【改進追蹤】區塊：
逐一對比上次的每個問題，用這次的數據判斷有沒有改善。
格式：

【改進追蹤】
- [問題摘要]：✅ 改善 / ❌ 未改善 / ⚠️ 部分改善
  → 說明（必須有數字佐證）

要直接、具體，不要客套。
"""
    return base_prompt + followup


def run_full_analysis(raw_text: str, last_issues: list = None) -> dict:
    trades = parse_trades(raw_text)
    if not trades:
        return {"error": "無法解析交易記錄"}

    stats = analyze(trades)

    if last_issues:
        prompt = build_followup_prompt(trades, stats, last_issues)
    else:
        prompt = build_prompt(trades, stats)

    ai_report = call_claude(prompt)
    issues = extract_issues(ai_report)

    return {
        "trades": [t.to_dict() for t in trades],
        "stats": stats,
        "ai_report": ai_report,
        "issues": issues,
        "is_followup": bool(last_issues),
    }
