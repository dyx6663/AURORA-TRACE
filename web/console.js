const $ = (selector) => document.querySelector(selector);
const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const stateLabels = {IDLE:'IDLE', QUEUED:'QUEUED', UNDERSTAND:'UNDERSTAND', PLAN:'PLAN', EXECUTE:'EXECUTE', VERIFY:'VERIFY', COMPLETED:'COMPLETED', FAILED:'FAILED'};
const evidenceKeys = ['baseline_failure_captured','minimal_patch_recorded','regression_tests_passed','workspace_boundary_respected'];
let activeRun = null; let activeData = null; let projects = new Map(); let renderedEvents = 0; let lastDiff = ''; let replayTimer = null;

function setState(state) {
  const pill = $('#statePill'); const label = stateLabels[state] || state || 'IDLE';
  pill.textContent = label; pill.className = 'state-pill ' + (state === 'COMPLETED' ? 'done' : state === 'FAILED' ? 'failed' : state === 'IDLE' ? 'idle' : 'running');
  const order = ['UNDERSTAND','PLAN','EXECUTE','VERIFY']; const index = order.indexOf(state);
  document.querySelectorAll('#stateMap span').forEach((node, i) => node.classList.toggle('active', i <= index || state === 'COMPLETED'));
  $('#phaseLabel').textContent = label;
}

function eventCard(event) {
  const payload = event.payload || {}; const tags = [];
  if (event.phase) tags.push(`<span class="tag">${esc(event.phase.toUpperCase())}</span>`);
  if (event.tool) tags.push(`<span class="tag">${esc(event.tool)}</span>`);
  if (event.evidence_type) tags.push(`<span class="tag evidence">${esc(event.evidence_type)}</span>`);
  if (event.verification_status && event.verification_status !== 'pending') tags.push(`<span class="tag ${event.verification_status === 'passed' ? 'ok' : 'bad'}">${esc(event.verification_status.toUpperCase())}</span>`);
  if (event.parent_event_id) tags.push(`<span class="tag">parent #${event.parent_event_id}</span>`);
  const detail = event.detail || (payload.output ? payload.output : '');
  return `<article class="event-card ${esc(event.kind)}"><div class="event-top"><strong>#${event.id} · ${esc(event.title)}</strong><time>${esc(event.time || event.timestamp || '')}</time></div><p class="event-detail">${esc(detail)}</p><div class="event-meta">${tags.join('')}</div></article>`;
}

function renderEvents(events, reset = false) {
  if (reset) { renderedEvents = 0; $('#events').innerHTML = ''; }
  const fresh = events.slice(renderedEvents); if (!fresh.length) return;
  if (renderedEvents === 0) $('#events').innerHTML = '';
  $('#events').insertAdjacentHTML('beforeend', fresh.map(eventCard).join('')); renderedEvents = events.length;
  $('#events').scrollTop = $('#events').scrollHeight;
}

function renderDiff(diffs = []) {
  const raw = diffs.join('\n'); if (raw === lastDiff) return; lastDiff = raw;
  $('#diffMeta').textContent = raw ? `${diffs.length} DIFF${diffs.length > 1 ? 'S' : ''}` : 'NO CHANGES';
  if (!raw) { $('#diff').innerHTML = '<span class="muted">// 运行后显示真实文件变更</span>'; return; }
  $('#diff').innerHTML = raw.split('\n').map((line) => { const safe = esc(line); if (line.startsWith('+') && !line.startsWith('+++')) return `<span class="diff-add">${safe}</span>`; if (line.startsWith('-') && !line.startsWith('---')) return `<span class="diff-del">${safe}</span>`; return safe; }).join('');
}

function renderVerification(events = []) {
  const commandEvents = events.filter((event) => event.tool === 'run_command' && event.payload);
  const last = commandEvents[commandEvents.length - 1]; if (!last) return;
  const payload = last.payload; const ok = payload.ok === true;
  $('#verified').textContent = `${ok ? '✓ PASS' : '× FAIL'} · ${String(payload.phase || last.phase || 'COMMAND').toUpperCase()}`;
  $('#verified').className = 'verify-badge ' + (ok ? 'ok' : 'bad');
  $('#verifyBody').innerHTML = `<p class="${ok ? 'success' : 'failure'}">${ok ? '✓' : '×'} ${esc(payload.command || 'verification command')}</p><p>${esc(payload.output || payload.error || 'no output')}</p>`;
}

function renderContract(evidence = {}) {
  const nodes = document.querySelectorAll('#contract-list');
  document.querySelectorAll('#contract > div').forEach((node, i) => { const passed = Boolean(evidence[evidenceKeys[i]]); node.classList.toggle('checked', passed); node.querySelector('i').textContent = passed ? '✓' : '○'; });
}

function update(data) {
  activeData = data; const events = data.events || []; setState(data.state);
  renderEvents(events); renderDiff(data.diffs || []); renderVerification(events); renderContract(data.evidence || {});
  const decisions = events.filter((event) => event.kind === 'decision').length; const files = new Set(events.flatMap((event) => event.affected_files || [])); const score = data.trust_score || 0;
  $('#eventCount').textContent = `${events.length} EVENTS`; $('#runCaption').textContent = data.project?.name ? `${data.project.name} · ${data.task}` : (data.task || '当前运行'); $('#runIdCaption').textContent = `RUN ${data.id || activeRun || '————'}`;
  $('#progress').textContent = String(score).padStart(2,'0'); $('#contractScore').textContent = `${String(score).padStart(2,'0')} / 100`; $('#metricIter').textContent = String(decisions).padStart(2,'0'); $('#metricTools').textContent = String(decisions).padStart(2,'0'); $('#metricFiles').textContent = String(files.size).padStart(2,'0');
  $('#healthText').textContent = data.state === 'COMPLETED' ? '验收通过' : data.state === 'FAILED' ? '运行中断' : data.state === 'VERIFY' ? '等待证据闭合' : '正在执行';
  $('#healthSub').textContent = data.summary || (data.state === 'COMPLETED' ? '所有 Gate 均由真实事件支持' : '决策、工具和验证结果正在写入账本');
  $('#exportBtn').disabled = !activeRun; $('#replayBtn').disabled = !events.length;
  if (data.finished) { $('#runBtn').disabled = false; $('#runBtn').innerHTML = '<span>↻</span> 再次运行 <kbd>Ctrl ↵</kbd>'; loadHistory(); }
}

async function loadRun(runId) { const response = await fetch('/api/run/' + encodeURIComponent(runId), {cache:'no-store'}); if (!response.ok) throw new Error('无法读取运行记录'); activeRun = runId; renderedEvents = 0; lastDiff = ''; update(await response.json()); }
async function poll() { if (!activeRun) return; try { const response = await fetch('/api/run/' + encodeURIComponent(activeRun), {cache:'no-store'}); const data = await response.json(); if (!response.ok) throw new Error(data.error || '运行状态读取失败'); update(data); if (!data.finished) window.setTimeout(poll, 420); } catch (error) { showError(error.message); } }
function showError(message) { $('#healthText').textContent = '请求失败'; $('#healthSub').textContent = message; $('#runBtn').disabled = false; $('#runBtn').innerHTML = '<span>↻</span> 重试 <kbd>Ctrl ↵</kbd>'; }

function projectDescription(project) { const profile = project.profile || {}; return `${(profile.languages || ['Unknown']).join(' / ')} · ${profile.files ?? project.file_count ?? 0} files · ${(profile.suggested_tests || []).join(' / ')}`; }
async function loadProjects(selected = null) { const response = await fetch('/api/projects', {cache:'no-store'}); const data = await response.json(); projects = new Map(data.projects.map((project) => [project.id, project])); $('#project').innerHTML = data.projects.map((project) => `<option value="${esc(project.id)}">${esc(project.name)}${project.source === 'uploaded' ? ' · imported' : ''}</option>`).join(''); if (selected) $('#project').value = selected; updateProjectMeta(); }
function updateProjectMeta() { const project = projects.get($('#project').value); if (!project) return; $('#projectMeta').textContent = project.source === 'uploaded' ? `已导入 · ${projectDescription(project)}` : `内置示例 · ${projectDescription(project)}`; if (project.source === 'uploaded') { $('#mode').value = 'live'; $('#task').value = '请分析这个项目，定位并修复问题，运行可用测试，并给出可审计的修改证据。'; } }
async function loadHistory() { try { const response = await fetch('/api/runs', {cache:'no-store'}); const data = await response.json(); const list = data.runs || []; $('#history').innerHTML = list.length ? list.map((run) => `<div class="history-item ${run.run_id === activeRun ? 'active' : ''}" data-run="${esc(run.run_id)}"><div class="history-item-top"><b>${esc(run.task)}</b><span class="history-score">${String(run.trust_score).padStart(2,'0')}</span></div><small>${esc(run.run_id)} · ${esc(run.state)} · ${esc(run.mode)}</small></div>`).join('') : '<p class="empty-small">尚无已保存的运行记录</p>'; document.querySelectorAll('[data-run]').forEach((node) => node.addEventListener('click', () => loadRun(node.dataset.run).catch((error) => showError(error.message)))); } catch (error) { $('#history').innerHTML = `<p class="empty-small">历史读取失败：${esc(error.message)}</p>`; } }

function openReplay() { if (!activeData?.events?.length) return; $('#replayPanel').classList.remove('hidden'); $('#replayTrack').innerHTML = activeData.events.map((event) => `<div class="replay-step"><b>#${event.id} · ${esc((event.phase || event.kind || '').toUpperCase())}</b><span>${esc(event.title)}</span><small>${esc(event.tool || 'system')}</small></div>`).join(''); }
function playReplay() { const nodes = [...document.querySelectorAll('.replay-step')]; if (!nodes.length) return; window.clearInterval(replayTimer); let index = 0; $('#replayStatus').textContent = '正在按持久化事件顺序回放……'; replayTimer = window.setInterval(() => { nodes.forEach((node, i) => node.classList.toggle('active', i === index)); index += 1; if (index >= nodes.length) { window.clearInterval(replayTimer); $('#replayStatus').textContent = '回放完成 · read-only replay'; } }, 380); }

$('#project').addEventListener('change', updateProjectMeta); $('#refreshHistory').addEventListener('click', loadHistory); $('#historyBtn').addEventListener('click', () => $('#history').scrollIntoView({behavior:'smooth'})); $('#closeReplay').addEventListener('click', () => $('#replayPanel').classList.add('hidden')); $('#replayBtn').addEventListener('click', openReplay); $('#replayPlay').addEventListener('click', playReplay); $('#exportBtn').addEventListener('click', () => activeRun && window.open('/api/run/' + encodeURIComponent(activeRun) + '/export', '_blank')); $('#uploadBtn').addEventListener('click', () => $('#projectFile').click());
$('#projectFile').addEventListener('change', async (event) => { const file = event.target.files[0]; if (!file) return; $('#uploadBtn').disabled = true; $('#uploadBtn').textContent = '上传中'; try { const form = new FormData(); form.append('project', file); const response = await fetch('/api/projects/import', {method:'POST', body:form}); const data = await response.json(); if (!response.ok) throw new Error(data.error || '项目导入失败'); await loadProjects(data.project.id); } catch (error) { showError(error.message); } finally { $('#uploadBtn').disabled = false; $('#uploadBtn').textContent = '＋ ZIP'; event.target.value = ''; } });
$('#runBtn').addEventListener('click', async () => { if ($('#runBtn').disabled) return; $('#runBtn').disabled = true; $('#runBtn').innerHTML = '<span>◌</span> 正在执行 <kbd>RUN</kbd>'; $('#events').innerHTML = '<div class="empty-state"><span>◌</span><b>正在建立隔离副本</b><p>事件流即将开始。</p></div>'; renderedEvents = 0; lastDiff = ''; try { const response = await fetch('/api/run', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({task:$('#task').value, mode:$('#mode').value, project_id:$('#project').value})}); const data = await response.json(); if (!response.ok) throw new Error(data.error || '任务启动失败'); activeRun = data.run_id; await poll(); } catch (error) { showError(error.message); } });
document.addEventListener('keydown', (event) => { if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') $('#runBtn').click(); }); window.setInterval(() => { $('#clock').textContent = new Date().toLocaleTimeString('zh-CN', {hour12:false}); }, 1000); loadProjects().then(loadHistory).catch((error) => showError(error.message));
