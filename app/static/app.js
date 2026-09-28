const chat = document.querySelector('#chat');
const form = document.querySelector('#chatForm');
const input = document.querySelector('#message');
const send = document.querySelector('#send');
let sessionId = localStorage.getItem('ops_session_id');
const originalChat = chat;

const escapeHtml = value => String(value).replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));

function evidenceLabel(item) {
  if (item.type === 'document') return `<b>文档</b> · ${escapeHtml(item.source)}`;
  if (item.type === 'log') return `<b>日志</b> · ${escapeHtml(item.timestamp)}<br>${escapeHtml(item.quote)}`;
  return `<b>指标</b> · ${escapeHtml(item.field)} = ${escapeHtml(item.value)}`;
}

function reportHtml(answer) {
  const evidence = answer.evidence.slice(0, 6).map(x => `<div class="chip">${evidenceLabel(x)}</div>`).join('');
  const steps = answer.steps.map(x => `<li>${escapeHtml(x)}</li>`).join('');
  const commands = answer.commands.map(x => `<div class="command"><span>${escapeHtml(x)}</span><button class="copy" data-command="${escapeHtml(x)}">复制</button></div>`).join('');
  return `<div class="report"><div class="report-head"><small>AGENT 分析完成</small><h3>${escapeHtml(answer.findings[0])}</h3></div><div class="report-grid"><div class="section"><h4>关键证据</h4><div class="evidence">${evidence}</div></div><div class="section"><h4>建议排查步骤</h4><ol>${steps}</ol></div><div class="section commands"><h4>安全命令建议 · 仅生成不执行</h4>${commands}</div></div></div>`;
}

function showPanel(title, html) {
  chat.innerHTML = `<div class="report"><div class="report-head"><small>功能模块</small><h3>${title}</h3></div><div class="section panel-content">${html}</div></div>`;
}

async function loadSessions() {
  const box = document.querySelector('#sessions');
  try { const data = await fetch('/sessions').then(r => r.json()); box.innerHTML = data.items.length ? data.items.map(x => `<div data-session="${x.session_id}">${escapeHtml(x.title)}</div>`).join('') : '<small>暂无历史会话</small>'; }
  catch (_) { box.innerHTML = '<small>历史会话加载失败</small>'; }
}

async function loadView(view) {
  if (view === 'analysis') { location.reload(); return; }
  if (view === 'knowledge') {
    showPanel('知识库检索', '<form id="searchForm" class="inline-form"><input id="searchQuery" placeholder="输入关键词，例如：连接池超时"><button>检索</button></form><div id="searchResults"><p>输入关键词检索文档证据。</p></div>');
    document.querySelector('#searchForm').onsubmit = async e => { e.preventDefault(); const q = document.querySelector('#searchQuery').value; const data = await fetch(`/knowledge/search?q=${encodeURIComponent(q)}`).then(r => r.json()); document.querySelector('#searchResults').innerHTML = data.items.map(x => `<div class="chip"><b>${escapeHtml(x.source)}</b><br>${escapeHtml(x.content.slice(0, 240))}</div>`).join('') || '<p>没有找到相关文档。</p>'; };
  } else {
    const data = await fetch('/observability').then(r => r.json()); showPanel('日志与指标', `<div class="chip">服务：${escapeHtml(data.metrics.service)} · 错误率：${data.metrics.error_rate} · p95：${data.metrics.p95_latency_ms}ms · 连接池：${data.metrics.db_pool_in_use}/${data.metrics.db_pool_size}</div>${data.logs.map(x => `<div class="chip"><b>${escapeHtml(x.timestamp)}</b><br>${escapeHtml(x.message)}</div>`).join('')}`);
  }
}

async function ask(message) {
  document.querySelector('#welcome')?.remove();
  const turn = document.createElement('div');
  turn.className = 'turn';
  turn.innerHTML = `<div class="user-row"><div class="user-bubble">${escapeHtml(message)}</div></div><div class="loading">正在检索知识库并分析证据<span class="dots"><span>.</span><span>.</span><span>.</span></span></div>`;
  chat.appendChild(turn); chat.scrollTop = chat.scrollHeight;
  send.disabled = true;
  try {
    const controller = new AbortController(); const timeout = setTimeout(() => controller.abort(), 65000);
    const response = await fetch('/chat', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({message, session_id:sessionId}), signal:controller.signal}); clearTimeout(timeout);
    if (!response.ok) throw new Error(`请求失败（${response.status}）`);
    const data = await response.json();
    sessionId = data.session_id; localStorage.setItem('ops_session_id', sessionId);
    turn.querySelector('.loading').outerHTML = reportHtml(data.answer); loadSessions();
  } catch (error) {
    const text = error.name === 'AbortError' ? '模型响应超时' : (error.message || '网络请求失败');
    turn.querySelector('.loading').innerHTML = `${escapeHtml(text)}，请确认后端服务正在运行。 <button class="retry">重试</button>`;
  } finally { send.disabled = false; chat.scrollTop = chat.scrollHeight; }
}

form.addEventListener('submit', event => { event.preventDefault(); const message=input.value.trim(); if(!message)return; input.value=''; ask(message); });
input.addEventListener('keydown', event => { if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();form.requestSubmit();} });
document.querySelectorAll('.examples button').forEach(button => button.addEventListener('click', () => ask(button.textContent)));
document.querySelector('#newChat').addEventListener('click', () => { localStorage.removeItem('ops_session_id'); sessionId=null; location.reload(); });
document.querySelectorAll('.nav-item').forEach(item => item.addEventListener('click', () => { document.querySelectorAll('.nav-item').forEach(x => x.classList.remove('active')); item.classList.add('active'); loadView(item.dataset.view); }));
document.querySelector('#sessions').addEventListener('click', async event => { const id = event.target.dataset.session; if (!id) return; sessionId = id; localStorage.setItem('ops_session_id', id); const data = await fetch(`/sessions/${id}`).then(r => r.json()); location.reload(); });
fetch('/health').then(response => response.json()).then(data => { document.querySelector('#mode').textContent = data.model === 'enabled' ? '模型模式' : '离线模式'; }).catch(() => { document.querySelector('#mode').textContent = '服务未连接'; });
document.querySelector('#upload').addEventListener('change', async event => {
  const file = event.target.files[0]; if (!file) return;
  const body = new FormData(); body.append('file', file);
  try { const response = await fetch('/documents', {method:'POST', body}); const data = await response.json(); if (!response.ok) throw new Error(data.detail || '上传失败'); alert(`${data.filename} 已加入知识库`); }
  catch (error) { alert(error.message); }
  event.target.value = '';
});
document.addEventListener('click', event => { if(event.target.classList.contains('copy')){navigator.clipboard.writeText(event.target.dataset.command);event.target.textContent='已复制';setTimeout(()=>event.target.textContent='复制',1200);} if(event.target.classList.contains('retry')){const bubble=event.target.closest('.turn')?.querySelector('.user-bubble');if(bubble)ask(bubble.textContent);} });
async function restoreSession() {
  if (!sessionId) return;
  try { const data = await fetch(`/sessions/${sessionId}`).then(r => r.json()); if (!data.items.length) return; document.querySelector('#welcome')?.remove(); data.items.forEach(item => { const turn = document.createElement('div'); turn.className='turn'; turn.innerHTML = item.role === 'user' ? `<div class="user-row"><div class="user-bubble">${escapeHtml(item.content)}</div></div>` : `<div class="report"><div class="report-head"><small>历史分析结果</small><h3>${escapeHtml(item.content)}</h3></div></div>`; chat.appendChild(turn); }); } catch (_) {}
}
loadSessions(); restoreSession();
