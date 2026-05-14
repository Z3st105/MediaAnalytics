const API_BASE = 'http://127.0.0.1:8765/api';

// Debug log
const logs = [];
function debug(msg) {
  const ts = new Date().toLocaleTimeString();
  const entry = `[${ts}] ${msg}`;
  logs.push(entry);
  if (logs.length > 15) logs.shift();
  const el = document.getElementById('debugLog');
  if (el) el.textContent = logs.join('\n');
  console.log(entry);
}

document.addEventListener('DOMContentLoaded', () => {
  debug('popup.js loaded');

  // Bind events via addEventListener (MV3 CSP blocks inline onclick)
  document.getElementById('addBtn').addEventListener('click', addVideo);
  document.getElementById('urlInput').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') addVideo();
  });
  document.querySelector('.refresh-btn').addEventListener('click', loadVideos);

  debug('Events bound, loading videos...');
  loadVideos();
});

function showToast(message, type = 'success') {
  const toast = document.getElementById('toast');
  toast.textContent = message;
  toast.className = `toast toast-${type} show`;
  debug('Toast: ' + message);
  setTimeout(() => { toast.className = 'toast'; }, 2500);
}

async function loadVideos() {
  const listEl = document.getElementById('videoList');

  try {
    debug('GET /api/videos ...');
    const resp = await fetch(`${API_BASE}/videos`);
    debug('GET status: ' + resp.status);
    if (!resp.ok) throw new Error('API error ' + resp.status);
    const videos = await resp.json();
    debug('Videos count: ' + videos.length);

    if (videos.length === 0) {
      listEl.innerHTML = '<div class="empty-state">暂无视频，粘贴链接添加</div>';
      return;
    }

    listEl.innerHTML = videos.map(v => renderVideoCard(v)).join('');

    // Bind dynamic button events
    listEl.querySelectorAll('[data-action]').forEach(btn => {
      const action = btn.dataset.action;
      const id = parseInt(btn.dataset.id);
      if (action === 'delete') btn.addEventListener('click', () => deleteVideo(id));
      if (action === 'retry') btn.addEventListener('click', () => retryVideo(id));
      if (action === 'copy') btn.addEventListener('click', () => copyText(btn.dataset.target));
      if (action === 'paste') btn.addEventListener('click', () => pasteAnalysis(id));
    });
  } catch (e) {
    debug('GET ERROR: ' + e.message);
    listEl.innerHTML = '<div class="empty-state">无法连接后端服务<br><small>请确保 Python 后端已启动 (start.bat)</small></div>';
  }
}

function renderVideoCard(video) {
  const s = video.status.split(':')[0];
  const statusClass = `status-${s}`;
  const dotClass = `dot-${s}`;
  const fillClass = `fill-${s}`;
  const statusText = {
    'pending': '等待处理',
    'downloading': '正在下载音频...',
    'transcribing': '正在转录中...',
    'completed': '已完成',
  }[s] || video.status;

  const transcript = video.transcript || '';
  const analysis = video.ai_analysis || '';
  const isProcessing = s === 'downloading' || s === 'transcribing' || s === 'pending';

  const tLen = transcript.length;
  const aLen = analysis.length;
  const tPreview = transcript ? transcript.slice(0, 30) + (tLen > 30 ? '...' : '') : '';
  const aPreview = analysis ? analysis.slice(0, 30) + (aLen > 30 ? '...' : '') : '';

  return `
    <div class="video-card" id="card-${video.id}">
      <div class="video-card-header">
        <div class="status-bar ${statusClass}">
          <span class="status-dot ${dotClass}"></span>
          <span>${statusText}</span>
        </div>
        <div class="btn-group">
          ${s === 'error' ? `<button class="btn btn-retry" data-action="retry" data-id="${video.id}">重试</button>` : ''}
          <button class="btn btn-delete" data-action="delete" data-id="${video.id}">删除</button>
        </div>
      </div>
      ${isProcessing ? `<div class="progress-bar"><div class="progress-fill ${fillClass}"></div></div>` : ''}
      ${s === 'completed' || s === 'error' ? `<div class="progress-bar"><div class="progress-fill ${fillClass}"></div></div>` : ''}
      <div class="video-url">${video.url}</div>

      <div class="field-row">
        <span class="field-name">转录文案${tLen ? ` (${tLen}字)` : ''}</span>
        ${transcript ? `<button class="btn btn-copy" data-action="copy" data-target="transcript-${video.id}">复制</button>` : '<span class="field-pending">等待转录...</span>'}
      </div>
      ${tPreview ? `<div class="field-preview" id="transcript-${video.id}">${tPreview}</div>` : ''}

      <div class="field-row">
        <span class="field-name">AI 解析${aLen ? ` (${aLen}字)` : ''}</span>
        ${analysis ? `<button class="btn btn-copy" data-action="copy" data-target="analysis-${video.id}">复制</button>` : `<button class="btn btn-save" data-action="paste" data-id="${video.id}">粘贴</button>`}
      </div>
      ${aPreview ? `<div class="field-preview" id="analysis-${video.id}">${aPreview}</div>` : ''}
    </div>
  `;
}

async function addVideo() {
  const input = document.getElementById('urlInput');
  const btn = document.getElementById('addBtn');
  const url = input.value.trim();

  debug('addVideo() called, url=' + url);

  if (!url) {
    showToast('请输入链接', 'error');
    return;
  }

  btn.disabled = true;
  btn.textContent = '添加中...';

  try {
    debug('POST /api/videos ...');
    const resp = await fetch(`${API_BASE}/videos`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url })
    });

    debug('POST status: ' + resp.status);

    if (resp.status === 409) {
      showToast('该视频已存在', 'error');
    } else if (!resp.ok) {
      const err = await resp.json();
      debug('POST error: ' + JSON.stringify(err));
      showToast(err.detail || '添加失败', 'error');
    } else {
      const data = await resp.json();
      debug('POST success: ' + JSON.stringify(data));
      input.value = '';
      showToast('已添加，后台处理中...', 'success');
      loadVideos();
    }
  } catch (e) {
    debug('POST CATCH: ' + e.name + ': ' + e.message);
    showToast('无法连接后端: ' + e.message, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = '添加';
  }
}

async function deleteVideo(id) {
  if (!confirm('确定删除？')) return;
  try {
    debug('DELETE /api/videos/' + id);
    await fetch(`${API_BASE}/videos/${id}`, { method: 'DELETE' });
    showToast('已删除');
    loadVideos();
  } catch (e) {
    debug('DELETE ERROR: ' + e.message);
    showToast('删除失败', 'error');
  }
}

async function retryVideo(id) {
  showToast('正在重试...', 'success');
  try {
    const resp = await fetch(`${API_BASE}/videos/${id}`);
    const video = await resp.json();
    await fetch(`${API_BASE}/videos/${id}`, { method: 'DELETE' });
    await fetch(`${API_BASE}/videos`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: video.url })
    });
    loadVideos();
  } catch (e) {
    showToast('重试失败', 'error');
  }
}

function copyText(elementId) {
  const el = document.getElementById(elementId);
  const text = el.textContent;
  navigator.clipboard.writeText(text).then(() => {
    showToast('已复制到剪贴板');
  }).catch(() => {
    showToast('复制失败', 'error');
  });
}

async function pasteAnalysis(videoId) {
  try {
    const text = await navigator.clipboard.readText();
    if (!text) {
      showToast('剪贴板为空', 'error');
      return;
    }

    const resp = await fetch(`${API_BASE}/videos/${videoId}/analysis`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ video_id: videoId, analysis: text })
    });

    if (resp.ok) {
      showToast('AI 解析已保存');
      loadVideos();
    } else {
      showToast('保存失败', 'error');
    }
  } catch (e) {
    showToast('读取剪贴板失败', 'error');
  }
}

// Auto-refresh every 3 seconds
setInterval(loadVideos, 3000);
