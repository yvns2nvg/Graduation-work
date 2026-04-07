/* ========================================
   SNEAKER AI — FRONTEND APPLICATION
   API Base: http://localhost:8000
   ======================================== */

const API_BASE = 'http://localhost:8000';

// ===== STATE =====
let state = {
  token: localStorage.getItem('sneaker_token') || null,
  user: null,
  currentGeneration: null,
  pollTimer: null,
  ws: null,
  threeScene: null,
};

// ===== INIT =====
document.addEventListener('DOMContentLoaded', async () => {
  // Prompt textarea character counter
  const ta = document.getElementById('promptInput');
  if (ta) {
    ta.addEventListener('input', () => {
      document.getElementById('charCount').textContent = ta.value.length;
    });
  }

  // Restore session
  if (state.token) {
    try {
      await fetchMe();
      showPage('generate');
    } catch {
      logout();
    }
  }
});

// ===================================
// API HELPERS
// ===================================
async function apiFetch(path, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...options.headers };
  if (state.token) headers['Authorization'] = `Bearer ${state.token}`;

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (res.status === 401) {
    logout();
    throw new Error('인증이 만료되었습니다. 다시 로그인해주세요.');
  }

  return res;
}

// ===================================
// AUTH
// ===================================
async function fetchMe() {
  const res = await apiFetch('/api/auth/me');
  if (!res.ok) throw new Error('Not authenticated');
  state.user = await res.json();
  updateNavForUser();
}

async function login() {
  const email = document.getElementById('loginEmail').value.trim();
  const password = document.getElementById('loginPassword').value;
  const errEl = document.getElementById('loginError');

  if (!email || !password) {
    showFormError(errEl, '이메일과 비밀번호를 입력해주세요.');
    return;
  }

  setButtonLoading('formLogin', true);

  try {
    const res = await apiFetch('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });

    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      showFormError(errEl, data.detail || '이메일 또는 비밀번호가 올바르지 않습니다.');
      return;
    }

    const data = await res.json();
    state.token = data.access_token;
    localStorage.setItem('sneaker_token', state.token);

    await fetchMe();
    closeModal();
    showPage('generate');
    showToast('환영합니다! 🎉', 'success');
  } catch (e) {
    showFormError(errEl, e.message || '로그인 중 오류가 발생했습니다.');
  } finally {
    setButtonLoading('formLogin', false);
  }
}

async function register() {
  const nickname = document.getElementById('regNickname').value.trim();
  const email = document.getElementById('regEmail').value.trim();
  const password = document.getElementById('regPassword').value;
  const errEl = document.getElementById('registerError');

  if (!email || !password) {
    showFormError(errEl, '이메일과 비밀번호를 입력해주세요.');
    return;
  }

  if (password.length < 6) {
    showFormError(errEl, '비밀번호는 6자 이상이어야 합니다.');
    return;
  }

  setButtonLoading('formRegister', true);

  try {
    const body = { email, password };
    if (nickname) body.nickname = nickname;

    const res = await apiFetch('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify(body),
    });

    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      showFormError(errEl, data.detail || '회원가입 중 오류가 발생했습니다.');
      return;
    }

    // Auto-login after register
    const loginRes = await apiFetch('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });

    if (loginRes.ok) {
      const loginData = await loginRes.json();
      state.token = loginData.access_token;
      localStorage.setItem('sneaker_token', state.token);
      await fetchMe();
      closeModal();
      showPage('generate');
      showToast('계정이 생성되었습니다! 🚀', 'success');
    }
  } catch (e) {
    showFormError(errEl, e.message || '회원가입 중 오류가 발생했습니다.');
  } finally {
    setButtonLoading('formRegister', false);
  }
}

function logout() {
  state.token = null;
  state.user = null;
  localStorage.removeItem('sneaker_token');
  if (state.ws) { state.ws.close(); state.ws = null; }
  if (state.pollTimer) { clearInterval(state.pollTimer); state.pollTimer = null; }
  updateNavForGuest();
  showPage('landing');
  showToast('로그아웃 되었습니다.');
}

// ===================================
// GENERATION
// ===================================
async function generateImage() {
  const prompt = document.getElementById('promptInput').value.trim();
  if (!prompt) {
    showToast('프롬프트를 입력해주세요.', 'error');
    return;
  }

  if (!state.token) {
    openAuthModal('login');
    return;
  }

  const btn = document.getElementById('generateBtn');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner" style="width:18px;height:18px;border-width:2px"></span> 생성 중...';

  try {
    const res = await apiFetch('/api/text-to-3d/generate', {
      method: 'POST',
      body: JSON.stringify({ prompt_text: prompt }),
    });

    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      showToast(data.detail || '생성 요청 실패', 'error');
      resetGenerateBtn();
      return;
    }

    const data = await res.json();
    state.currentGeneration = data;

    // Show progress panel
    document.getElementById('resultEmpty').classList.add('hidden');
    document.getElementById('result3D').classList.add('hidden');
    document.getElementById('resultProgress').classList.remove('hidden');
    document.getElementById('errorWrap').classList.add('hidden');
    document.getElementById('imagePreviewWrap').classList.add('hidden');

    updatePipelineStatus(data.status);
    connectWebSocket(data.id);
    startPolling(data.id);
  } catch (e) {
    showToast(e.message || '오류가 발생했습니다.', 'error');
    resetGenerateBtn();
  }
}

async function checkStatus(generationId) {
  try {
    const res = await apiFetch(`/api/text-to-3d/${generationId}/status`);
    if (!res.ok) return;
    const data = await res.json();
    handleStatusUpdate(data);
  } catch (e) {
    console.error('Status check error:', e);
  }
}

function handleStatusUpdate(data) {
  state.currentGeneration = { ...state.currentGeneration, ...data };
  updatePipelineStatus(data.status);

  const badge = document.getElementById('statusBadge');
  badge.textContent = statusLabel(data.status);
  badge.className = `status-badge ${data.status}`;

  // Progress percentages per status
  const progressMap = { pending: 5, generating: 35, image_done: 60, converting: 80, done: 100, failed: 0 };
  document.getElementById('progressBar').style.width = `${progressMap[data.status] || 0}%`;

  if (data.status === 'image_done') {
    document.getElementById('progressTitle').textContent = '이미지가 생성되었어요!';
    if (data.image_url) {
      showImagePreview(data.image_url, data.id);
    }
    // Show convert button
    document.getElementById('convertBtn').style.display = 'block';
    document.getElementById('convertBtn').dataset.id = data.id;
    stopPolling();
  }

  if (data.status === 'converting') {
    document.getElementById('progressTitle').textContent = '3D 모델 변환 중...';
    document.getElementById('convertBtn').style.display = 'none';
  }

  if (data.status === 'done') {
    stopPolling();
    if (state.ws) { state.ws.close(); state.ws = null; }
    show3DResult(data);
  }

  if (data.status === 'failed') {
    stopPolling();
    if (state.ws) { state.ws.close(); state.ws = null; }
    showGenerationError('생성에 실패했습니다. 다시 시도해주세요.');
  }
}

function showImagePreview(imageUrl, genId) {
  const wrap = document.getElementById('imagePreviewWrap');
  const img = document.getElementById('generatedImage');
  // Try to use the image endpoint
  img.src = `${API_BASE}/api/text-to-3d/${genId}/image`;
  img.onerror = () => { img.src = imageUrl; };
  wrap.classList.remove('hidden');
}

async function convert3D() {
  const genId = state.currentGeneration?.id;
  if (!genId) return;

  const btn = document.getElementById('convertBtn');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner" style="width:18px;height:18px;border-width:2px"></span> 변환 시작 중...';

  try {
    const res = await apiFetch(`/api/text-to-3d/${genId}/convert-3d`, {
      method: 'POST',
      body: JSON.stringify({}),
    });

    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      showToast(data.detail || '3D 변환 요청 실패', 'error');
      btn.disabled = false;
      btn.innerHTML = '<span class="btn-icon">🧊</span> 3D 모델로 변환하기';
      return;
    }

    document.getElementById('progressTitle').textContent = '3D 모델 변환 중...';
    btn.style.display = 'none';
    startPolling(genId);
  } catch (e) {
    showToast(e.message, 'error');
    btn.disabled = false;
    btn.innerHTML = '<span class="btn-icon">🧊</span> 3D 모델로 변환하기';
  }
}

async function show3DResult(data) {
  document.getElementById('resultProgress').classList.add('hidden');

  const container = document.getElementById('result3D');
  container.classList.remove('hidden');

  // Set prompt tag
  const promptTag = document.getElementById('resultPromptTag');
  promptTag.textContent = `"${state.currentGeneration?.prompt_text || ''}"`;

  // Download button
  document.getElementById('downloadBtn').dataset.id = data.id;

  // Load 3D model
  await load3DModel(data.id);

  resetGenerateBtn();
  showToast('3D 모델이 완성되었습니다! 🎉', 'success');
}

async function load3DModel(generationId) {
  const container = document.getElementById('threeContainer');
  const canvas = document.getElementById('threeCanvas');

  // Dynamically load Three.js if not present
  if (typeof THREE === 'undefined') {
    await loadScript('https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.min.js');
    await loadScript('https://cdn.jsdelivr.net/npm/three@0.160.0/examples/js/loaders/GLTFLoader.js');
    await loadScript('https://cdn.jsdelivr.net/npm/three@0.160.0/examples/js/controls/OrbitControls.js');
  }

  // Clean up previous scene
  if (state.threeScene) {
    state.threeScene.dispose && state.threeScene.dispose();
  }

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x1E1B4B);

  const camera = new THREE.PerspectiveCamera(60, container.clientWidth / container.clientHeight, 0.01, 1000);
  camera.position.set(0, 0.5, 2);

  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
  renderer.setSize(container.clientWidth, container.clientHeight);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.outputEncoding = THREE.sRGBEncoding;

  // Lights
  const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
  scene.add(ambientLight);

  const dirLight = new THREE.DirectionalLight(0xffffff, 1.2);
  dirLight.position.set(2, 4, 3);
  scene.add(dirLight);

  const pointLight = new THREE.PointLight(0x7C3AED, 0.8, 10);
  pointLight.position.set(-2, 2, -2);
  scene.add(pointLight);

  // Controls
  const controls = new THREE.OrbitControls(camera, canvas);
  controls.enableDamping = true;
  controls.dampingFactor = 0.05;
  controls.autoRotate = true;
  controls.autoRotateSpeed = 1.5;

  // Load GLB model via API
  const modelUrl = `${API_BASE}/api/text-to-3d/${generationId}/3d-model`;
  const loader = new THREE.GLTFLoader();

  loader.load(
    modelUrl,
    (gltf) => {
      const model = gltf.scene;

      // Center model
      const box = new THREE.Box3().setFromObject(model);
      const center = box.getCenter(new THREE.Vector3());
      const size = box.getSize(new THREE.Vector3());
      const maxDim = Math.max(size.x, size.y, size.z);
      const scale = 1.5 / maxDim;
      model.scale.setScalar(scale);
      model.position.sub(center.multiplyScalar(scale));

      scene.add(model);
    },
    undefined,
    (error) => {
      console.error('GLB load error:', error);
      // Show placeholder cube if model loading fails
      const geo = new THREE.BoxGeometry(0.8, 0.8, 0.8);
      const mat = new THREE.MeshStandardMaterial({ color: 0x7C3AED, roughness: 0.3, metalness: 0.6 });
      scene.add(new THREE.Mesh(geo, mat));
    }
  );

  // Animation loop
  let animId;
  function animate() {
    animId = requestAnimationFrame(animate);
    controls.update();
    renderer.render(scene, camera);
  }
  animate();

  // Handle resize
  const resizeObs = new ResizeObserver(() => {
    camera.aspect = container.clientWidth / container.clientHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(container.clientWidth, container.clientHeight);
  });
  resizeObs.observe(container);

  state.threeScene = { dispose: () => { cancelAnimationFrame(animId); resizeObs.disconnect(); renderer.dispose(); } };
}

async function downloadModel() {
  const genId = document.getElementById('downloadBtn').dataset.id;
  if (!genId) return;

  showToast('다운로드를 시작합니다...', 'success');

  try {
    const res = await apiFetch(`/api/text-to-3d/${genId}/download`);
    if (!res.ok) {
      showToast('다운로드 실패', 'error');
      return;
    }

    const blob = await res.blob();
    const contentDisposition = res.headers.get('content-disposition') || '';
    const fileNameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
    const fileName = fileNameMatch ? fileNameMatch[1].replace(/['"]/g, '') : `model_${genId}.glb`;

    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = fileName;
    a.click();
    URL.revokeObjectURL(url);
  } catch (e) {
    showToast(e.message || '다운로드 중 오류', 'error');
  }
}

function resetGeneration() {
  state.currentGeneration = null;
  stopPolling();
  if (state.ws) { state.ws.close(); state.ws = null; }
  if (state.threeScene) { state.threeScene.dispose && state.threeScene.dispose(); state.threeScene = null; }

  document.getElementById('resultEmpty').classList.remove('hidden');
  document.getElementById('resultProgress').classList.add('hidden');
  document.getElementById('result3D').classList.add('hidden');
  document.getElementById('promptInput').value = '';
  document.getElementById('charCount').textContent = '0';

  resetGenerateBtn();
}

// ===================================
// WEBSOCKET
// ===================================
function connectWebSocket(generationId) {
  if (!state.user) return;
  if (state.ws) { state.ws.close(); }

  const wsUrl = `${API_BASE.replace('http', 'ws')}/ws/${state.user.id}`;
  const ws = new WebSocket(wsUrl);

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data.generation_id === generationId || data.id === generationId) {
        handleStatusUpdate(data);
      }
    } catch (e) {
      console.error('WS parse error:', e);
    }
  };

  ws.onerror = () => { console.warn('WebSocket error, falling back to polling'); };
  ws.onclose = () => { state.ws = null; };

  state.ws = ws;
}

// ===================================
// POLLING (fallback)
// ===================================
function startPolling(generationId) {
  stopPolling();
  state.pollTimer = setInterval(() => checkStatus(generationId), 3000);
}

function stopPolling() {
  if (state.pollTimer) {
    clearInterval(state.pollTimer);
    state.pollTimer = null;
  }
}

// ===================================
// HISTORY
// ===================================
async function loadHistory() {
  const grid = document.getElementById('historyGrid');
  const loading = document.getElementById('historyLoading');
  const empty = document.getElementById('historyEmpty');

  grid.innerHTML = '';
  loading.classList.remove('hidden');
  empty.classList.add('hidden');

  try {
    const res = await apiFetch('/api/text-to-3d/history');
    if (!res.ok) { showToast('히스토리를 불러올 수 없습니다.', 'error'); return; }

    const data = await res.json();
    loading.classList.add('hidden');

    if (!data.generations || data.generations.length === 0) {
      empty.classList.remove('hidden');
      return;
    }

    data.generations.forEach(gen => {
      grid.appendChild(createHistoryCard(gen));
    });
  } catch (e) {
    loading.classList.add('hidden');
    showToast(e.message || '오류가 발생했습니다.', 'error');
  }
}

function createHistoryCard(gen) {
  const card = document.createElement('div');
  card.className = 'history-card';

  const date = new Date(gen.created_at).toLocaleDateString('ko-KR', {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  });

  card.innerHTML = `
    <div class="history-card-img">
      ${gen.image_url
        ? `<img src="${API_BASE}/api/text-to-3d/${gen.id}/image" alt="생성 이미지" onerror="this.parentElement.innerHTML='👟'" />`
        : '👟'
      }
    </div>
    <div class="history-card-body">
      <div class="history-card-prompt">${escapeHtml(gen.prompt_text)}</div>
      <div class="history-card-meta">
        <span class="history-status ${gen.status}">${statusLabel(gen.status)}</span>
        <span class="history-date">${date}</span>
      </div>
    </div>
    <div class="history-card-actions">
      ${gen.status === 'done'
        ? `<button class="btn btn-primary" onclick="downloadFromHistory(${gen.id})">⬇️ 다운로드</button>`
        : gen.status === 'image_done'
        ? `<button class="btn btn-secondary" onclick="resumeConvert(${gen.id})">🧊 3D 변환</button>`
        : ''
      }
      <button class="btn btn-ghost" onclick="deleteGeneration(${gen.id}, this)">🗑️</button>
    </div>
  `;
  return card;
}

async function downloadFromHistory(generationId) {
  document.getElementById('downloadBtn').dataset.id = generationId;
  await downloadModel();
}

async function resumeConvert(generationId) {
  const res = await apiFetch(`/api/text-to-3d/${generationId}/convert-3d`, {
    method: 'POST',
    body: JSON.stringify({}),
  });
  if (res.ok) {
    showToast('3D 변환을 시작합니다!', 'success');
    showPage('generate');
    // Load the existing generation into generate page
    state.currentGeneration = { id: generationId };
    document.getElementById('resultEmpty').classList.add('hidden');
    document.getElementById('resultProgress').classList.remove('hidden');
    startPolling(generationId);
  } else {
    showToast('변환 요청 실패', 'error');
  }
}

async function deleteGeneration(generationId, btnEl) {
  if (!confirm('이 항목을 삭제하시겠습니까?')) return;

  const res = await apiFetch(`/api/text-to-3d/${generationId}`, { method: 'DELETE' });
  if (res.ok || res.status === 204) {
    btnEl.closest('.history-card').remove();
    showToast('삭제되었습니다.', 'success');

    // Show empty state if no cards left
    if (document.getElementById('historyGrid').children.length === 0) {
      document.getElementById('historyEmpty').classList.remove('hidden');
    }
  } else {
    showToast('삭제 실패', 'error');
  }
}

// ===================================
// PIPELINE STATUS UI
// ===================================
const STATUS_ORDER = ['pending', 'generating', 'image_done', 'converting', 'done'];

function updatePipelineStatus(status) {
  const currentIdx = STATUS_ORDER.indexOf(status);

  STATUS_ORDER.forEach((s, i) => {
    const el = document.getElementById(`step-${s}`);
    if (!el) return;

    el.classList.remove('active', 'completed');

    if (i < currentIdx) el.classList.add('completed');
    else if (i === currentIdx && status !== 'failed') el.classList.add('active');
  });
}

// ===================================
// NAVIGATION
// ===================================
function showPage(pageId) {
  document.querySelectorAll('.page').forEach(p => p.classList.add('hidden'));
  document.getElementById(`page-${pageId}`)?.classList.remove('hidden');

  if (pageId === 'history') {
    loadHistory();
  }

  if (pageId === 'generate' && !state.currentGeneration) {
    resetGeneration();
  }
}

function updateNavForUser() {
  document.getElementById('navAuth').classList.add('hidden');
  document.getElementById('navUser').classList.remove('hidden');
  document.getElementById('navGenerate').classList.remove('hidden');
  document.getElementById('navHistory').classList.remove('hidden');

  const nickname = state.user?.nickname || state.user?.email?.split('@')[0] || '사용자';
  document.getElementById('userNickname').textContent = `👋 ${nickname}`;
}

function updateNavForGuest() {
  document.getElementById('navAuth').classList.remove('hidden');
  document.getElementById('navUser').classList.add('hidden');
  document.getElementById('navGenerate').classList.add('hidden');
  document.getElementById('navHistory').classList.add('hidden');
}

// ===================================
// MODAL
// ===================================
function openAuthModal(form = 'login') {
  document.getElementById('modalBackdrop').classList.remove('hidden');
  document.getElementById('authModal').classList.remove('hidden');
  switchForm(form);
}

function closeModal() {
  document.getElementById('modalBackdrop').classList.add('hidden');
  document.getElementById('authModal').classList.add('hidden');
}

function switchForm(form) {
  document.getElementById('formLogin').classList.toggle('hidden', form !== 'login');
  document.getElementById('formRegister').classList.toggle('hidden', form !== 'register');
  document.getElementById('loginError').classList.add('hidden');
  document.getElementById('registerError').classList.add('hidden');
}

// ===================================
// UI HELPERS
// ===================================
function showToast(msg, type = '') {
  const toast = document.getElementById('toast');
  toast.textContent = msg;
  toast.className = `toast ${type}`;

  setTimeout(() => toast.classList.add('show'), 10);
  setTimeout(() => toast.classList.remove('show'), 3000);
}

function showFormError(el, msg) {
  el.textContent = msg;
  el.classList.remove('hidden');
}

function setButtonLoading(formId, loading) {
  const form = document.getElementById(formId);
  const btn = form?.querySelector('.btn-primary');
  if (!btn) return;

  if (loading) {
    btn.disabled = true;
    btn.dataset.original = btn.textContent;
    btn.innerHTML = '<span class="spinner" style="width:18px;height:18px;border-width:2px"></span> 처리 중...';
  } else {
    btn.disabled = false;
    btn.textContent = btn.dataset.original || btn.textContent;
  }
}

function resetGenerateBtn() {
  const btn = document.getElementById('generateBtn');
  btn.disabled = false;
  btn.innerHTML = '<span class="btn-icon">✨</span> 이미지 생성하기';
}

function showGenerationError(msg) {
  document.getElementById('errorWrap').classList.remove('hidden');
  document.getElementById('errorMsg').textContent = msg;
  resetGenerateBtn();
}

function setPrompt(text) {
  const ta = document.getElementById('promptInput');
  if (ta) {
    ta.value = text;
    document.getElementById('charCount').textContent = text.length;
    ta.focus();
  }
}

function exampleClick(el) {
  openAuthModal('register');
}

function statusLabel(status) {
  const labels = {
    pending: '대기 중',
    generating: '생성 중',
    image_done: '이미지 완성',
    converting: '3D 변환 중',
    done: '완성',
    failed: '실패',
  };
  return labels[status] || status;
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.appendChild(document.createTextNode(str));
  return div.innerHTML;
}

function loadScript(src) {
  return new Promise((resolve, reject) => {
    const s = document.createElement('script');
    s.src = src;
    s.onload = resolve;
    s.onerror = reject;
    document.head.appendChild(s);
  });
}

// Enter key handlers
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') closeModal();
});

document.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && document.activeElement?.id === 'loginPassword') login();
  if (e.key === 'Enter' && document.activeElement?.id === 'regPassword') register();
  if (e.key === 'Enter' && e.ctrlKey && document.activeElement?.id === 'promptInput') generateImage();
});
