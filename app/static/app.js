const chat = document.querySelector('#chat');
const form = document.querySelector('#chatForm');
const input = document.querySelector('#message');
const send = document.querySelector('#send');
let sessionId = localStorage.getItem('ops_session_id');

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

async function ask(message) {
  document.querySelector('#welcome')?.remove();
  const turn = document.createElement('div');
  turn.className = 'turn';
  turn.innerHTML = `<div class="user-row"><div class="user-bubble">${escapeHtml(message)}</div></div><div class="loading">正在检索知识库并分析证据<span class="dots"><span>.</span><span>.</span><span>.</span></span></div>`;
  chat.appendChild(turn); chat.scrollTop = chat.scrollHeight;
  send.disabled = true;
  try {
    const response = await fetch('/chat', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({message, session_id:sessionId})});
    if (!response.ok) throw new Error(`请求失败（${response.status}）`);
    const data = await response.json();
    sessionId = data.session_id; localStorage.setItem('ops_session_id', sessionId);
    turn.querySelector('.loading').outerHTML = reportHtml(data.answer);
  } catch (error) {
    turn.querySelector('.loading').textContent = `${error.message}，请确认后端服务正在运行。`;
  } finally { send.disabled = false; chat.scrollTop = chat.scrollHeight; }
}

form.addEventListener('submit', event => { event.preventDefault(); const message=input.value.trim(); if(!message)return; input.value=''; ask(message); });
input.addEventListener('keydown', event => { if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();form.requestSubmit();} });
document.querySelectorAll('.examples button').forEach(button => button.addEventListener('click', () => ask(button.textContent)));
document.querySelector('#newChat').addEventListener('click', () => { localStorage.removeItem('ops_session_id'); sessionId=null; location.reload(); });
document.addEventListener('click', event => { if(event.target.classList.contains('copy')){navigator.clipboard.writeText(event.target.dataset.command);event.target.textContent='已复制';setTimeout(()=>event.target.textContent='复制',1200);} });
