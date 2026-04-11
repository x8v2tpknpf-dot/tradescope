import os
from flask import Flask, request, jsonify, render_template_string, session
from database import init_db, save_analysis, get_last_analysis, get_all_analyses
from auth import register, login
from claude_api import run_full_analysis
from agents import run_agent_pipeline

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev_secret_change_in_prod")

init_db()

HTML = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TradeScope — AI交易分析</title>
<link href="https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Noto+Sans+TC:wght@300;400;500;700&display=swap" rel="stylesheet">
<style>
  :root{--bg:#0a0a0f;--surface:#111118;--border:#1e1e2e;--accent:#00ff88;--accent2:#ff4466;--text:#e8e8f0;--muted:#5a5a7a;--mono:'Space Mono',monospace;--sans:'Noto Sans TC',sans-serif}
  *,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
  body{background:var(--bg);color:var(--text);font-family:var(--sans);font-weight:300;min-height:100vh;overflow-x:hidden}
  body::before{content:'';position:fixed;inset:0;background-image:linear-gradient(rgba(0,255,136,.03) 1px,transparent 1px),linear-gradient(90deg,rgba(0,255,136,.03) 1px,transparent 1px);background-size:40px 40px;pointer-events:none;z-index:0}
  .wrap{position:relative;z-index:1;max-width:900px;margin:0 auto;padding:0 24px 80px}
  header{padding:40px 0 36px;border-bottom:1px solid var(--border);margin-bottom:40px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:16px}
  .logo-area .logo{font-family:var(--mono);font-size:11px;letter-spacing:.2em;color:var(--accent);text-transform:uppercase;margin-bottom:8px}
  .logo-area h1{font-family:var(--mono);font-size:clamp(22px,4vw,34px);font-weight:700;letter-spacing:-.02em}
  .logo-area h1 span{color:var(--accent)}
  .auth-bar{display:flex;gap:8px;align-items:center}
  .auth-email{font-family:var(--mono);font-size:10px;color:var(--muted);letter-spacing:.08em}
  .btn-sm{font-family:var(--mono);font-size:10px;letter-spacing:.1em;text-transform:uppercase;padding:8px 16px;background:none;border:1px solid var(--border);color:var(--muted);cursor:pointer;transition:all .2s}
  .btn-sm:hover{border-color:var(--accent);color:var(--accent)}
  .btn-sm.primary{background:var(--accent);color:#000;border-color:var(--accent)}
  .btn-sm.primary:hover{opacity:.85}
  .modal-bg{display:none;position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:100;align-items:center;justify-content:center}
  .modal-bg.show{display:flex}
  .modal{background:var(--surface);border:1px solid var(--border);padding:36px;width:100%;max-width:400px}
  .modal-title{font-family:var(--mono);font-size:13px;letter-spacing:.1em;text-transform:uppercase;color:var(--accent);margin-bottom:24px}
  .field{margin-bottom:16px}
  .field label{font-family:var(--mono);font-size:9px;letter-spacing:.15em;color:var(--muted);text-transform:uppercase;display:block;margin-bottom:6px}
  .field input{width:100%;background:var(--bg);border:1px solid var(--border);color:var(--text);font-family:var(--mono);font-size:13px;padding:10px 14px;outline:none;transition:border-color .2s}
  .field input:focus{border-color:var(--accent)}
  .modal-actions{display:flex;gap:8px;margin-top:20px}
  .modal-error{font-family:var(--mono);font-size:11px;color:var(--accent2);margin-top:12px;display:none}
  .modal-error.show{display:block}
  .modal-switch{font-family:var(--mono);font-size:10px;color:var(--muted);margin-top:16px;cursor:pointer}
  .modal-switch span{color:var(--accent);text-decoration:underline}
  .stats-strip{display:flex;gap:2px;margin-bottom:36px}
  .stat-pill{flex:1;background:var(--surface);border:1px solid var(--border);padding:14px 16px;font-family:var(--mono);font-size:10px;letter-spacing:.1em;color:var(--muted);text-transform:uppercase}
  .stat-pill strong{display:block;font-size:20px;color:var(--accent);margin-bottom:4px;letter-spacing:-.02em}
  .label{font-family:var(--mono);font-size:10px;letter-spacing:.15em;color:var(--accent);text-transform:uppercase;margin-bottom:10px;display:flex;align-items:center;gap:8px}
  .label::before{content:'';display:inline-block;width:6px;height:6px;background:var(--accent);border-radius:50%}
  textarea{width:100%;height:200px;background:var(--surface);border:1px solid var(--border);color:var(--text);font-family:var(--mono);font-size:12px;line-height:1.7;padding:20px;resize:vertical;outline:none;transition:border-color .2s}
  textarea:focus{border-color:var(--accent)}
  textarea::placeholder{color:var(--muted)}
  .hint{margin-top:10px;font-size:12px;color:var(--muted)}
  .btn{display:inline-flex;align-items:center;gap:10px;margin-top:20px;padding:16px 36px;background:var(--accent);color:#000;font-family:var(--mono);font-size:12px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;border:none;cursor:pointer;transition:opacity .15s,transform .15s}
  .btn:hover{opacity:.85;transform:translateY(-1px)}
  .btn:disabled{opacity:.4;cursor:not-allowed;transform:none}
  .loading{display:none;align-items:center;gap:12px;margin-top:24px;font-family:var(--mono);font-size:12px;color:var(--accent);letter-spacing:.1em}
  .loading.show{display:flex}
  .spinner{width:16px;height:16px;border:2px solid var(--border);border-top-color:var(--accent);border-radius:50%;animation:spin .8s linear infinite}
  @keyframes spin{to{transform:rotate(360deg)}}
  #result{display:none;opacity:0;transform:translateY(16px);transition:opacity .4s,transform .4s}
  #result.show{display:block;opacity:1;transform:translateY(0)}
  .divider{border:none;border-top:1px solid var(--border);margin:36px 0}
  .kpi-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:2px;margin-bottom:28px}
  .kpi{background:var(--surface);border:1px solid var(--border);padding:18px}
  .kpi-label{font-family:var(--mono);font-size:9px;letter-spacing:.15em;color:var(--muted);text-transform:uppercase;margin-bottom:8px}
  .kpi-value{font-family:var(--mono);font-size:24px;font-weight:700;letter-spacing:-.02em}
  .kpi-value.pos{color:var(--accent)}.kpi-value.neg{color:var(--accent2)}.kpi-value.neu{color:var(--text)}
  .report-box{background:var(--surface);border:1px solid var(--border);border-left:3px solid var(--accent);padding:28px 32px;margin-bottom:16px}
  .report-header{font-family:var(--mono);font-size:10px;letter-spacing:.15em;color:var(--accent);text-transform:uppercase;margin-bottom:20px;display:flex;align-items:center;gap:10px}
  .report-header::after{content:'';flex:1;height:1px;background:var(--border)}
  .report-content{font-size:14px;line-height:1.9;white-space:pre-wrap;color:var(--text)}
  .followup-badge{display:inline-flex;align-items:center;gap:6px;font-family:var(--mono);font-size:9px;letter-spacing:.1em;text-transform:uppercase;background:rgba(0,255,136,.08);border:1px solid rgba(0,255,136,.2);color:var(--accent);padding:4px 10px;margin-bottom:16px}
  .history-section{margin-top:40px}
  .history-chart{background:var(--surface);border:1px solid var(--border);padding:24px;margin-top:12px}
  .chart-row{display:flex;align-items:center;gap:12px;margin-bottom:10px;font-family:var(--mono);font-size:11px}
  .chart-date{color:var(--muted);width:80px;flex-shrink:0}
  .chart-bar-wrap{flex:1;background:var(--bg);height:20px;position:relative}
  .chart-bar{height:100%;transition:width .6s ease}
  .chart-bar.pos{background:var(--accent)}.chart-bar.neg{background:var(--accent2)}
  .chart-val{width:70px;text-align:right;flex-shrink:0}
  .chart-val.pos{color:var(--accent)}.chart-val.neg{color:var(--accent2)}
  .error-box{background:rgba(255,68,102,.08);border:1px solid rgba(255,68,102,.3);padding:16px 20px;font-family:var(--mono);font-size:12px;color:var(--accent2);display:none;margin-top:16px}
  .error-box.show{display:block}
  .trades-toggle{font-family:var(--mono);font-size:10px;letter-spacing:.1em;color:var(--muted);text-transform:uppercase;background:none;border:1px solid var(--border);padding:8px 16px;cursor:pointer;margin-top:16px;transition:color .2s,border-color .2s}
  .trades-toggle:hover{color:var(--accent);border-color:var(--accent)}
  .trades-table{display:none;margin-top:12px;overflow-x:auto}
  .trades-table.show{display:block}
  table{width:100%;border-collapse:collapse;font-family:var(--mono);font-size:11px}
  th{text-align:left;padding:10px 12px;background:var(--surface);border-bottom:1px solid var(--border);color:var(--muted);letter-spacing:.08em;text-transform:uppercase;font-weight:400}
  td{padding:10px 12px;border-bottom:1px solid rgba(30,30,46,.5)}
  .win{color:var(--accent)}.loss{color:var(--accent2)}
  .agent-section{margin-top:48px}
  .agent-step{background:var(--surface);border:1px solid var(--border);margin-bottom:12px;overflow:hidden}
  .agent-step-header{display:flex;align-items:center;gap:12px;padding:16px 20px;border-bottom:1px solid transparent;font-family:var(--mono);font-size:10px;letter-spacing:.12em;text-transform:uppercase;cursor:pointer}
  .agent-step-header.has-content{border-bottom-color:var(--border)}
  .agent-step-num{width:24px;height:24px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;flex-shrink:0}
  .agent-step-num.research{background:rgba(0,255,136,.12);color:var(--accent);border:1px solid rgba(0,255,136,.3)}
  .agent-step-num.backtest{background:rgba(100,160,255,.12);color:#64a0ff;border:1px solid rgba(100,160,255,.3)}
  .agent-step-num.eval{background:rgba(255,200,0,.12);color:#ffc800;border:1px solid rgba(255,200,0,.3)}
  .agent-step-title{flex:1;color:var(--text)}
  .agent-step-status{font-size:9px;letter-spacing:.08em;color:var(--muted)}
  .agent-step-status.done{color:var(--accent)}
  .agent-step-body{padding:20px 24px;font-family:var(--mono);font-size:12px;line-height:1.8;white-space:pre-wrap;color:var(--text);display:none;max-height:440px;overflow-y:auto;border-top:1px solid var(--border)}
  .agent-step-body.show{display:block}
  .agent-btn{display:inline-flex;align-items:center;gap:10px;margin-top:20px;padding:14px 32px;background:transparent;color:var(--accent);font-family:var(--mono);font-size:11px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;border:1px solid var(--accent);cursor:pointer;transition:all .15s}
  .agent-btn:hover:not(:disabled){background:var(--accent);color:#000}
  .agent-btn:disabled{opacity:.4;cursor:not-allowed}
  .agent-loading{display:none;align-items:center;gap:10px;margin-top:16px;font-family:var(--mono);font-size:11px;color:var(--accent);letter-spacing:.08em}
  .agent-loading.show{display:flex}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div class="logo-area">
      <div class="logo">TradeScope v0.2</div>
      <h1>你的交易<span>真正</span>出了什麼問題</h1>
    </div>
    <div class="auth-bar" id="authBar">
      <button class="btn-sm primary" onclick="showModal('login')">登入</button>
      <button class="btn-sm" onclick="showModal('register')">註冊</button>
    </div>
  </header>

  <div class="modal-bg" id="authModal">
    <div class="modal">
      <div class="modal-title" id="modalTitle">登入</div>
      <div class="field"><label>Email</label><input type="email" id="authEmail" placeholder="you@example.com"></div>
      <div class="field"><label>密碼</label><input type="password" id="authPassword" placeholder="••••••"></div>
      <div class="modal-error" id="modalError"></div>
      <div class="modal-actions">
        <button class="btn-sm primary" id="modalSubmit" onclick="submitAuth()">登入</button>
        <button class="btn-sm" onclick="closeModal()">取消</button>
      </div>
      <div class="modal-switch" id="modalSwitch">還沒有帳號？<span onclick="switchMode()">立即註冊</span></div>
    </div>
  </div>

  <div class="stats-strip">
    <div class="stat-pill"><strong>82%</strong>散戶虧損</div>
    <div class="stat-pill"><strong>6個</strong>分析維度</div>
    <div class="stat-pill"><strong>追蹤</strong>每週進步</div>
  </div>

  <div class="label">貼上你的交易記錄</div>
  <textarea id="tradeInput" placeholder="從 BingX → U本位合約訂單 → 倉位歷史&#10;複製貼上文字到這裡（可以多筆）"></textarea>
  <p class="hint">✦ 只需要複製貼上，不需要整理格式 · 登入後可追蹤每週進步</p>
  <button class="btn" onclick="doAnalyze()">開始分析 →</button>
  <div class="loading" id="loading"><div class="spinner"></div>AI 正在診斷你的交易習慣...</div>
  <div class="error-box" id="errorBox"></div>

  <div id="result">
    <hr class="divider">
    <div id="followupBadge"></div>
    <div class="label">分析結果</div>
    <div class="kpi-grid" id="kpiGrid"></div>
    <div class="report-box">
      <div class="report-header">Claude AI 診斷報告</div>
      <div class="report-content" id="reportContent"></div>
    </div>
    <button class="trades-toggle" onclick="toggleTrades()">▸ 查看交易明細</button>
    <div class="trades-table" id="tradesTable"></div>
  </div>

  <div class="history-section" id="historySection" style="display:none">
    <hr class="divider">
    <div class="label">歷史盈虧追蹤</div>
    <div class="history-chart" id="historyChart"></div>
  </div>

  <div class="agent-section">
    <hr class="divider">
    <div class="label">AI 策略研究員 — 三Agent協作</div>
    <p class="hint">✦ Agent 1 搜尋獲利指標 → Agent 2 程式化回測 → Agent 3 評估是否值得交易</p>
    <button class="agent-btn" id="agentBtn" onclick="runAgentPipeline()">啟動三Agent分析 →</button>
    <div class="agent-loading" id="agentLoading">
      <div class="spinner"></div>
      <span id="agentStatus">Agent 正在執行，請稍候（約需 1-3 分鐘）...</span>
    </div>
    <div class="error-box" id="agentErrorBox"></div>

    <div id="agentResults" style="display:none;margin-top:24px">
      <div class="agent-step" onclick="toggleAgent('body1',this)">
        <div class="agent-step-header" id="header1">
          <div class="agent-step-num research">1</div>
          <div class="agent-step-title">研究Agent — 搜尋網路獲利指標</div>
          <div class="agent-step-status" id="status1">等待中</div>
        </div>
        <div class="agent-step-body" id="body1"></div>
      </div>
      <div class="agent-step" onclick="toggleAgent('body2',this)">
        <div class="agent-step-header" id="header2">
          <div class="agent-step-num backtest">2</div>
          <div class="agent-step-title">回測Agent — 程式化回測指標</div>
          <div class="agent-step-status" id="status2">等待中</div>
        </div>
        <div class="agent-step-body" id="body2"></div>
      </div>
      <div class="agent-step" onclick="toggleAgent('body3',this)">
        <div class="agent-step-header" id="header3">
          <div class="agent-step-num eval">3</div>
          <div class="agent-step-title">評估Agent — 判斷策略可行性</div>
          <div class="agent-step-status" id="status3">等待中</div>
        </div>
        <div class="agent-step-body" id="body3"></div>
      </div>
    </div>
  </div>
</div>

<script>
let currentUser = null;
let authMode = 'login';

async function init() {
  try {
    const res = await fetch('/me');
    const data = await res.json();
    if (data.user_id) { setLoggedIn(data); loadHistory(); }
  } catch(e) {}
}

function setLoggedIn(data) {
  currentUser = data;
  document.getElementById('authBar').innerHTML = `
    <span class="auth-email">${data.email}</span>
    <button class="btn-sm" onclick="doLogout()">登出</button>`;
}

function showModal(mode) {
  authMode = mode;
  document.getElementById('modalTitle').textContent = mode==='login'?'登入':'註冊';
  document.getElementById('modalSubmit').textContent = mode==='login'?'登入':'註冊';
  document.getElementById('modalSwitch').innerHTML = mode==='login'
    ? '還沒有帳號？<span onclick="switchMode()">立即註冊</span>'
    : '已有帳號？<span onclick="switchMode()">直接登入</span>';
  document.getElementById('modalError').classList.remove('show');
  document.getElementById('authEmail').value='';
  document.getElementById('authPassword').value='';
  document.getElementById('authModal').classList.add('show');
}

function closeModal(){ document.getElementById('authModal').classList.remove('show'); }
function switchMode(){ showModal(authMode==='login'?'register':'login'); }

async function submitAuth() {
  const email = document.getElementById('authEmail').value.trim();
  const password = document.getElementById('authPassword').value;
  const errEl = document.getElementById('modalError');
  const res = await fetch('/'+authMode, {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({email, password})
  });
  const data = await res.json();
  if (!data.ok) { errEl.textContent=data.error; errEl.classList.add('show'); return; }
  setLoggedIn(data); closeModal(); loadHistory();
}

async function doLogout() {
  await fetch('/logout', {method:'POST'});
  currentUser = null;
  document.getElementById('authBar').innerHTML = `
    <button class="btn-sm primary" onclick="showModal('login')">登入</button>
    <button class="btn-sm" onclick="showModal('register')">註冊</button>`;
  document.getElementById('historySection').style.display='none';
}

async function doAnalyze() {
  const raw = document.getElementById('tradeInput').value.trim();
  if (!raw) return;
  const btn = document.querySelector('.btn');
  const loading = document.getElementById('loading');
  const result = document.getElementById('result');
  const errorBox = document.getElementById('errorBox');
  btn.disabled=true; loading.classList.add('show');
  result.classList.remove('show'); errorBox.classList.remove('show');
  try {
    const res = await fetch('/analyze', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({text:raw})
    });
    const data = await res.json();
    if (data.error) { errorBox.textContent='⚠ '+data.error; errorBox.classList.add('show'); return; }
    renderResult(data);
    if (currentUser) loadHistory();
  } catch(e) {
    errorBox.textContent='⚠ 連線失敗'; errorBox.classList.add('show');
  } finally {
    btn.disabled=false; loading.classList.remove('show');
  }
}

function renderResult(data) {
  const s = data.stats.summary;
  document.getElementById('followupBadge').innerHTML = data.is_followup
    ? '<div class="followup-badge">🔄 改進追蹤模式 — 已對比上次診斷結果</div>' : '';
  const kpis = [
    {label:'勝率',value:s.win_rate+'%',cls:s.win_rate>=50?'pos':'neg'},
    {label:'盈虧比',value:'1:'+s.rr_ratio,cls:s.rr_ratio>=1.5?'pos':'neg'},
    {label:'總盈虧',value:(s.total_pnl>0?'+':'')+s.total_pnl.toFixed(2),cls:s.total_pnl>0?'pos':'neg'},
    {label:'手續費',value:s.total_fee.toFixed(2),cls:'neg'},
    {label:'交易筆數',value:s.total_trades,cls:'neu'},
    {label:'連虧加倉',value:data.stats.revenge_trading_count+'次',cls:data.stats.revenge_trading_count>0?'neg':'pos'},
  ];
  document.getElementById('kpiGrid').innerHTML = kpis.map(k=>
    `<div class="kpi"><div class="kpi-label">${k.label}</div><div class="kpi-value ${k.cls}">${k.value}</div></div>`
  ).join('');
  document.getElementById('reportContent').textContent = data.ai_report;
  const rows = data.trades.map(t=>
    `<tr><td>${t.open_time}</td><td>${t.symbol}</td><td>${t.direction}</td>
     <td>${t.leverage}X</td>
     <td class="${t.is_win?'win':'loss'}">${t.close_pnl>0?'+':''}${t.close_pnl.toFixed(4)}</td>
     <td>${t.holding_minutes}分</td></tr>`
  ).join('');
  document.getElementById('tradesTable').innerHTML = `
    <table><thead><tr><th>時間</th><th>幣種</th><th>方向</th><th>槓桿</th><th>盈虧</th><th>持倉</th></tr></thead>
    <tbody>${rows}</tbody></table>`;
  const resultEl = document.getElementById('result');
  resultEl.classList.add('show');
  resultEl.scrollIntoView({behavior:'smooth',block:'start'});
}

function toggleTrades() {
  const table = document.getElementById('tradesTable');
  const btn = document.querySelector('.trades-toggle');
  const isOpen = table.classList.toggle('show');
  btn.textContent = isOpen?'▾ 隱藏交易明細':'▸ 查看交易明細';
}

async function loadHistory() {
  try {
    const res = await fetch('/history');
    const data = await res.json();
    if (!data.analyses || data.analyses.length < 2) return;
    const section = document.getElementById('historySection');
    const chart = document.getElementById('historyChart');
    const maxAbs = Math.max(...data.analyses.map(a=>Math.abs(a.stats_json.summary.total_pnl)));
    chart.innerHTML = data.analyses.map(a=>{
      const pnl = a.stats_json.summary.total_pnl;
      const pct = maxAbs>0 ? Math.abs(pnl)/maxAbs*100 : 0;
      const isPos = pnl>=0;
      const date = a.created_at.slice(5,10);
      return `<div class="chart-row">
        <div class="chart-date">${date}</div>
        <div class="chart-bar-wrap"><div class="chart-bar ${isPos?'pos':'neg'}" style="width:${pct}%"></div></div>
        <div class="chart-val ${isPos?'pos':'neg'}">${isPos?'+':''}${pnl.toFixed(2)}</div>
      </div>`;
    }).join('');
    section.style.display='block';
  } catch(e) {}
}

function toggleAgent(bodyId, stepEl) {
  const body = document.getElementById(bodyId);
  if (!body.classList.contains('show') && !body.textContent.trim()) return;
  const header = stepEl.querySelector('.agent-step-header');
  body.classList.toggle('show');
  header.classList.toggle('has-content', body.classList.contains('show'));
}

async function runAgentPipeline() {
  const btn = document.getElementById('agentBtn');
  const loading = document.getElementById('agentLoading');
  const results = document.getElementById('agentResults');
  const errorBox = document.getElementById('agentErrorBox');

  btn.disabled = true;
  loading.classList.add('show');
  errorBox.classList.remove('show');
  results.style.display = 'none';

  ['1','2','3'].forEach(i => {
    document.getElementById('status'+i).textContent = '等待中';
    document.getElementById('status'+i).className = 'agent-step-status';
    document.getElementById('body'+i).classList.remove('show');
    document.getElementById('body'+i).textContent = '';
    document.getElementById('header'+i).classList.remove('has-content');
  });

  try {
    const res = await fetch('/api/agent-pipeline', {method:'POST',
      headers:{'Content-Type':'application/json'}});
    const data = await res.json();

    if (data.error) {
      errorBox.textContent = '⚠ ' + data.error;
      errorBox.classList.add('show');
      return;
    }

    results.style.display = 'block';

    if (data.research) {
      document.getElementById('status1').textContent = '✅ 完成';
      document.getElementById('status1').className = 'agent-step-status done';
      document.getElementById('body1').textContent = data.research;
      document.getElementById('body1').classList.add('show');
      document.getElementById('header1').classList.add('has-content');
    }
    if (data.backtest) {
      document.getElementById('status2').textContent = '✅ 完成';
      document.getElementById('status2').className = 'agent-step-status done';
      document.getElementById('body2').textContent = data.backtest;
      document.getElementById('body2').classList.add('show');
      document.getElementById('header2').classList.add('has-content');
    }
    if (data.evaluation) {
      document.getElementById('status3').textContent = '✅ 完成';
      document.getElementById('status3').className = 'agent-step-status done';
      document.getElementById('body3').textContent = data.evaluation;
      document.getElementById('body3').classList.add('show');
      document.getElementById('header3').classList.add('has-content');
      document.getElementById('agentResults').scrollIntoView({behavior:'smooth',block:'start'});
    }
  } catch(e) {
    errorBox.textContent = '⚠ 連線失敗：' + e.message;
    errorBox.classList.add('show');
  } finally {
    btn.disabled = false;
    loading.classList.remove('show');
  }
}

init();
</script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/me")
def me():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({})
    return jsonify({"user_id": user_id, "email": session.get("email")})

@app.route("/register", methods=["POST"])
def register_route():
    data = request.get_json()
    result = register(data.get("email",""), data.get("password",""))
    if result["ok"]:
        session["user_id"] = result["user_id"]
        session["email"] = result["email"]
    return jsonify(result)

@app.route("/login", methods=["POST"])
def login_route():
    data = request.get_json()
    result = login(data.get("email",""), data.get("password",""))
    if result["ok"]:
        session["user_id"] = result["user_id"]
        session["email"] = result["email"]
    return jsonify(result)

@app.route("/logout", methods=["POST"])
def logout_route():
    session.clear()
    return jsonify({"ok": True})

@app.route("/analyze", methods=["POST"])
def analyze_route():
    data = request.get_json()
    raw_text = data.get("text","").strip()
    if not raw_text:
        return jsonify({"error": "請貼上交易記錄"})
    try:
        user_id = session.get("user_id")
        last_issues = []
        if user_id:
            last = get_last_analysis(user_id)
            if last:
                last_issues = last.get("issues_json", [])
        result = run_full_analysis(raw_text, last_issues or None)
        if "error" in result:
            return jsonify(result)
        if user_id:
            save_analysis(
                user_id=user_id,
                trades=result["trades"],
                stats=result["stats"],
                ai_report=result["ai_report"],
                issues=result.get("issues", []),
            )
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/history")
def history_route():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"analyses": []})
    return jsonify({"analyses": get_all_analyses(user_id)})

@app.route("/api/agent-pipeline", methods=["POST"])
def agent_pipeline_route():
    """
    執行三個AI Agent的完整分析流程：
    Agent 1 搜尋指標 → Agent 2 回測 → Agent 3 評估
    """
    try:
        result = run_agent_pipeline()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"TradeScope 啟動中 → http://localhost:{port}")
    app.run(debug=False, host="0.0.0.0", port=port)
