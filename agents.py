"""
TradeScope — 三個AI交易策略分析Agent

Agent 1 (研究Agent):  搜尋網路上能獲利的技術指標
Agent 2 (回測Agent):  對找到的指標執行程式化回測
Agent 3 (評估Agent):  判斷這些策略是否值得實際交易
"""

import anthropic

client = anthropic.Anthropic()
MODEL = "claude-opus-4-6"


# ─── 共用工具函式 ───────────────────────────────────────────────────────────


def _extract_text(content: list) -> str:
    """從 response content blocks 中提取純文字"""
    texts = []
    for block in content:
        if hasattr(block, "type") and block.type == "text":
            texts.append(block.text)
    return "\n".join(texts)


def _run_agent(
    system: str,
    user_prompt: str,
    tools: list = None,
    max_continuations: int = 8,
    on_progress=None,
) -> str:
    """
    執行單一 Agent，自動處理 server-side tool 的 pause_turn。

    on_progress: 可選的 callback(stage: str)，用來回報進度
    """
    messages = [{"role": "user", "content": user_prompt}]

    kwargs = {
        "model": MODEL,
        "max_tokens": 8192,
        "messages": messages,
        "thinking": {"type": "adaptive"},
    }
    if system:
        kwargs["system"] = system
    if tools:
        kwargs["tools"] = tools

    for i in range(max_continuations):
        if on_progress:
            on_progress(f"iteration_{i + 1}")

        response = client.messages.create(**kwargs)

        if response.stop_reason == "end_turn":
            return _extract_text(response.content)

        if response.stop_reason == "pause_turn":
            # server-side tool loop 達到上限，重新送出讓它繼續
            kwargs["messages"] = [
                messages[0],
                {"role": "assistant", "content": response.content},
            ]
            continue

        # 其他 stop_reason（如 max_tokens）直接取現有文字
        break

    return _extract_text(response.content)


# ─── Agent 1: 研究Agent ────────────────────────────────────────────────────


def agent_research_indicators(on_progress=None) -> str:
    """
    搜尋網路上有實際績效數據支撐的加密貨幣/期貨技術指標。
    使用 web_search 工具自動搜尋多個來源。
    """
    system = """你是一位專業的加密貨幣量化研究員，擅長從學術論文與交易社群中挖掘有效策略。

你的任務：
1. 搜尋近期有實際績效數據的技術指標或策略組合
2. 優先選擇有明確買賣訊號、經過回測驗證的指標
3. 涵蓋不同類型：趨勢、動量、均值回歸

輸出格式（必須是合法 JSON）：
{
  "indicators": [
    {
      "name": "指標名稱（英文）",
      "description": "一句話描述這個指標的核心邏輯",
      "buy_signal": "明確的買入觸發條件（可執行的規則）",
      "sell_signal": "明確的賣出/平倉觸發條件",
      "reported_win_rate": "文獻或社群報告的勝率（若無則填 '未知'）",
      "best_timeframe": "最適合的時間框架（如 1h / 4h / 1d）",
      "parameters": "關鍵參數設定（如 RSI 14, EMA 20/50）",
      "notes": "使用注意事項或已知限制"
    }
  ],
  "search_summary": "本次搜尋的簡短摘要（50字以內）"
}

嚴格輸出 JSON，不要在 JSON 前後加任何說明文字。"""

    tools = [
        {"type": "web_search_20260209", "name": "web_search"},
    ]

    prompt = """請執行以下搜尋，找出 3-5 個在加密貨幣/期貨市場有實際獲利記錄的技術指標：

1. 搜尋: "best crypto trading indicators 2024 backtest results win rate"
2. 搜尋: "bitcoin futures technical strategy backtest sharpe ratio"
3. 搜尋: "RSI MACD EMA crypto trading strategy performance 2023 2024"
4. 搜尋: "profitable momentum indicators cryptocurrency futures"

整合搜尋結果，挑選 3-5 個最有說服力的指標，輸出 JSON 格式。
只選有明確規則、可程式化回測的指標。"""

    return _run_agent(system, prompt, tools, on_progress=on_progress)


# ─── Agent 2: 回測Agent ────────────────────────────────────────────────────


def agent_backtest_indicators(indicators_json: str, on_progress=None) -> str:
    """
    對研究Agent找到的指標執行程式化回測。
    使用 code_execution 工具，以 Python 生成模擬 OHLCV 數據並計算績效指標。
    """
    system = """你是一位量化交易員，專長是用 Python 建立系統化回測框架。

你的任務：
1. 用 Python 生成 12 個月的模擬 BTC/USDT 日線 OHLCV 數據
   （價格範圍 25000-70000 USDT，包含真實波動特性：趨勢段、震盪段、急漲急跌）
2. 對每個指標實作買賣邏輯並執行回測
3. 計算標準績效指標

回測規則：
- 起始資金：10,000 USDT
- 每次入場：使用當前資金的 20%
- 不允許做空（只做多）
- 不考慮手續費（先測裸績效）

必須計算：
- 最終資產 / 總報酬率（%）
- 勝率（%）
- 最大回撤（%）
- 夏普比率（使用日收益率，無風險利率 = 0）
- 總交易次數
- 平均持倉天數

最後輸出合法 JSON：
{
  "backtest_results": [
    {
      "indicator_name": "...",
      "total_return_pct": 0.0,
      "win_rate_pct": 0.0,
      "max_drawdown_pct": 0.0,
      "sharpe_ratio": 0.0,
      "total_trades": 0,
      "avg_holding_days": 0.0
    }
  ],
  "data_description": "生成的模擬數據說明",
  "backtest_period": "回測期間",
  "code_notes": "代碼備注"
}

嚴格在 JSON 前後不要加說明文字。"""

    tools = [
        {"type": "code_execution_20260120", "name": "code_execution"},
    ]

    prompt = f"""以下是研究Agent找到的技術指標定義：

{indicators_json}

請執行 Python 代碼完成回測：

步驟 1：生成模擬數據
- 12 個月日線 OHLCV（約 365 天）
- 用 numpy 生成帶趨勢的隨機漫步，模擬 BTC 行為
- 確保數據有高低點、趨勢段和震盪段

步驟 2：對每個指標實作回測
- 用 pandas/numpy 計算指標值
- 實作買賣邏輯
- 追蹤每筆交易的入場/出場

步驟 3：計算績效
- 計算所有要求的指標
- 以 JSON 格式 print 輸出結果

請確保代碼可以完整運行，不要有 import error。
最後一步：print(json.dumps(results, ensure_ascii=False, indent=2))"""

    return _run_agent(system, prompt, tools, on_progress=on_progress)


# ─── Agent 3: 評估Agent ────────────────────────────────────────────────────


def agent_evaluate_strategy(research_result: str, backtest_result: str, on_progress=None) -> str:
    """
    綜合研究結果與回測數據，判斷策略是否值得用真實資金交易。
    這個 Agent 純靠推理，不需要工具。
    """
    system = """你是一位管理過億美元資產的量化基金風險管理師。
你的評估必須客觀、直接，不客套。

評估重點：
1. 回測數據是否可信（樣本量、過擬合風險）
2. 策略在不同市場環境下的穩健性
3. 實際執行的可行性（流動性、滑點、情緒管理）
4. 與 BTC Buy-and-Hold 的比較

用繁體中文回答，語氣直接，數字說話。"""

    prompt = f"""請評估以下交易策略的實際可行性：

━━━ 研究Agent的發現 ━━━
{research_result}

━━━ 回測Agent的結果 ━━━
{backtest_result}

請按以下格式輸出評估報告：

【綜合評分】
X / 10 分
（理由：一句話）

【最強策略】
哪個指標表現最好？用數字說明為什麼。

【優點分析】
1. [具體優點 + 數字]
2. [具體優點 + 數字]
3. [具體優點 + 數字]

【風險警告】
1. [具體風險 + 說明]
2. [具體風險 + 說明]
3. [具體風險 + 說明]

【回測可信度評估】
- 樣本量充足嗎？
- 有過擬合風險嗎？
- 模擬數據 vs 真實市場的差距？

【與 BTC Buy-and-Hold 比較】
過去 12 個月 BTC 約漲 X%，這些策略表現如何？

【最終結論】
值得用真實資金交易嗎？（必須明確回答「值得」或「不值得」，並說明原因）

【建議下一步】
如果要進一步驗證，最重要的 3 個步驟是什麼？"""

    return _run_agent(system, prompt, tools=None, on_progress=on_progress)


# ─── 完整流程 ──────────────────────────────────────────────────────────────


def run_agent_pipeline(on_progress=None) -> dict:
    """
    執行完整的三Agent流程：研究 → 回測 → 評估

    on_progress: 可選的 callback(stage: str, message: str)
    回傳 dict:
      {
        "research":   str,   # Agent 1 的輸出
        "backtest":   str,   # Agent 2 的輸出
        "evaluation": str,   # Agent 3 的輸出
        "error":      str | None
      }
    """
    results = {
        "research": None,
        "backtest": None,
        "evaluation": None,
        "error": None,
    }

    def _progress(stage, msg):
        if on_progress:
            on_progress(stage, msg)

    try:
        # Agent 1: 研究
        _progress("research", "Agent 1：正在搜尋網路上的獲利指標...")
        research_result = agent_research_indicators(
            on_progress=lambda s: _progress("research", f"Agent 1 {s}")
        )
        results["research"] = research_result
        _progress("research_done", "Agent 1 完成")

        # Agent 2: 回測
        _progress("backtest", "Agent 2：正在執行程式化回測...")
        backtest_result = agent_backtest_indicators(
            research_result,
            on_progress=lambda s: _progress("backtest", f"Agent 2 {s}"),
        )
        results["backtest"] = backtest_result
        _progress("backtest_done", "Agent 2 完成")

        # Agent 3: 評估
        _progress("evaluation", "Agent 3：正在評估策略可行性...")
        evaluation_result = agent_evaluate_strategy(
            research_result,
            backtest_result,
            on_progress=lambda s: _progress("evaluation", f"Agent 3 {s}"),
        )
        results["evaluation"] = evaluation_result
        _progress("evaluation_done", "Agent 3 完成")

    except Exception as e:
        results["error"] = str(e)

    return results
