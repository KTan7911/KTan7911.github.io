/* ==========================================================
   小屋 · 主逻辑
   ========================================================== */

const $  = s => document.querySelector(s);
const $$ = s => [...document.querySelectorAll(s)];

function escapeHtml(s){
  return String(s == null ? '' : s).replace(/[&<>"']/g, c => (
    {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]
  ));
}
function nowHM(){
  const n = new Date();
  return String(n.getHours()).padStart(2,'0') + ':' + String(n.getMinutes()).padStart(2,'0');
}
function pad2(n){ return String(n).padStart(2,'0'); }

let toastTimer;
function toast(msg){
  const t = $('#toast');
  t.textContent = msg;
  t.classList.add('on');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove('on'), 1800);
}

/* ==========================================================
   启动流程：检查登录 → 显示登录页 or 主应用
   ========================================================== */
async function boot(){
  const bootEl = $('#boot');
  const authEl = $('#authpage');
  const appEl  = $('#app');

  // 有本地会话 → 试着续期，成功就直接进
  if (SB.isLoggedIn()) {
    let ok = true;
    try {
      const s = SB.getSession();
      const issued = s.expires_at ? s.expires_at * 1000 : 0;
      if (issued && Date.now() > issued - 60000) {
        const r = await SB.refresh();
        ok = !!r;
      }
    } catch(e) { ok = false; }

    if (ok) {
      bootEl.classList.add('hidden');
      appEl.classList.remove('hidden');
      await startApp();
      return;
    }
  }

  bootEl.classList.add('hidden');
  authEl.classList.remove('hidden');
}

/* ==========================================================
   登录 / 注册
   ========================================================== */
let authMode = 'login';

function setAuthMode(m){
  authMode = m;
  $$('.authtabs button').forEach(b => b.classList.toggle('on', b.dataset.m === m));
  $('#authSubmit').textContent = m === 'login' ? '进入小屋' : '创建账号';
  $('#authMsg').className = 'authmsg';
  $('#authMsg').textContent = '';
  $('#confirmRow').classList.toggle('hidden', m === 'login');
}

function authMsg(type, text){
  const el = $('#authMsg');
  el.className = 'authmsg ' + type;
  el.textContent = text;
}

async function doAuth(){
  const email = $('#emailInput').value.trim();
  const pwd   = $('#pwdInput').value;
  const btn   = $('#authSubmit');

  if (!email || !email.includes('@')) return authMsg('err', '请输入正确的邮箱地址');
  if (!pwd || pwd.length < 6)         return authMsg('err', '密码至少 6 位');

  if (authMode === 'register') {
    const pwd2 = $('#pwdInput2').value;
    if (pwd !== pwd2) return authMsg('err', '两次输入的密码不一致');

    const allow = CABIN_CONFIG.ALLOWED_EMAILS;
    if (allow && allow.length && !allow.includes(email.toLowerCase())) {
      return authMsg('err', '这个邮箱不在小屋的名单里 🌿');
    }
  }

  btn.disabled = true;
  btn.textContent = authMode === 'login' ? '正在进入…' : '正在创建…';

  try {
    if (authMode === 'login') {
      await SB.signIn(email, pwd);
      enterApp();
    } else {
      const data = await SB.signUp(email, pwd);
      if (data && data.access_token) {
        enterApp();
      } else {
        authMsg('ok', '账号已创建！如果没有自动进入，请切换到「登入」试一下');
        setAuthMode('login');
      }
    }
  } catch(err) {
    let m = err.message || '操作失败';
    if (/Invalid login credentials/i.test(m))       m = '邮箱或密码不对哦';
    if (/already registered|already been registered/i.test(m)) m = '这个邮箱已经注册过了，直接登入吧';
    if (/Email not confirmed/i.test(m))             m = '邮箱还没验证，或者后台的「Confirm email」没关';
    if (/Password should be at least/i.test(m))     m = '密码太短啦，至少 6 位';
    if (/rate limit|too many/i.test(m))             m = '尝试太频繁，稍等一下再试';
    authMsg('err', m);
  } finally {
    btn.disabled = false;
    btn.textContent = authMode === 'login' ? '进入小屋' : '创建账号';
  }
}

function enterApp(){
  $('#authpage').classList.add('hidden');
  $('#app').classList.remove('hidden');
  startApp();
}

async function logout(){
  if (!confirm('要退出小屋吗？')) return;
  await SB.signOut();
  location.reload();
}

/* ==========================================================
   主应用
   ========================================================== */
let entries = [];      // 全部记录
let curMood = 'roar';
let curTags = [];
let voiceMode = false;
let chatMode = 'cabin'; // cabin | pig（小猪为二期预留）

async function startApp(){
  const u = SB.getUser();
  if (u && u.email) {
    $('#topSub').textContent = u.email.split('@')[0] + ' 的小屋 🌿';
  }
  renderMoodStrip();
  await loadEntries();
  renderStream();
}

/* ---------- 心情胶囊 ---------- */
function renderMoodStrip(){
  const box = $('#moodstrip');
  box.innerHTML = CABIN_CONFIG.MOODS.map((m, i) =>
    `<button data-m="${m.key}" class="${i === 0 ? 'sel ' + m.cls : ''}">${m.emoji} ${m.name}</button>`
  ).join('');
  curMood = CABIN_CONFIG.MOODS[0].key;

  box.querySelectorAll('button').forEach(b => {
    b.addEventListener('click', () => {
      box.querySelectorAll('button').forEach(x => x.classList.remove('sel'));
      const m = CABIN_CONFIG.MOODS.find(x => x.key === b.dataset.m);
      b.classList.add('sel', m.cls);
      curMood = b.dataset.m;
    });
  });
}

function moodOf(key){
  return CABIN_CONFIG.MOODS.find(m => m.key === key) || CABIN_CONFIG.MOODS[0];
}

/* ---------- 读取记录 ---------- */
async function loadEntries(){
  try {
    const rows = await SB.db('entries').select('*').order('created_at', { ascending: true }).limit(500);
    entries = Array.isArray(rows) ? rows : [];
  } catch(err) {
    console.error('读取记录失败', err);
    entries = [];
    if (/relation|does not exist|404/i.test(err.message || '')) {
      toast('数据表还没建好，请先执行 SQL 建表');
    } else {
      toast('读取失败：' + err.message);
    }
  }
}

/* ---------- 渲染聊天流 ---------- */
let lastDayLabel = '';

function dayLabel(ts){
  const d = new Date(ts);
  const now = new Date();
  const dk = d.toDateString(), nk = now.toDateString();
  if (dk === nk) return '今天';
  const y = new Date(now); y.setDate(y.getDate() - 1);
  if (dk === y.toDateString()) return '昨天';
  const thisYear = d.getFullYear() === now.getFullYear();
  return thisYear
    ? `${d.getMonth()+1}月${d.getDate()}日`
    : `${d.getFullYear()}年${d.getMonth()+1}月${d.getDate()}日`;
}

function entryHTML(e){
  const m = moodOf(e.mood);
  let inner = '';
  let tailText;

  if (e.kind === 'voice') {
    const bars = Array.from({ length: 12 }).map(() =>
      `<i style="height:${6 + Math.floor(Math.random()*13)}px"></i>`).join('');
    inner = `<div class="bubble mine">
        <div class="vbubble">
          <button class="vplay" data-audio="${escapeHtml(e.audio_url || '')}">▶</button>
          <div class="vwave">${bars}</div>
          <span class="vtime">${escapeHtml(e.duration_text || '0:00')}</span>
        </div>
      </div>`;
    tailText = '语音已存';
  } else {
    inner = `<div class="bubble mine">${escapeHtml(e.text)}</div>`;
    tailText = '已收好';
  }

  const tags = (e.tags || []).map(t => `<span class="etag">#${escapeHtml(t)}</span>`).join('');

  return `<div class="mrow">
      <span class="moodtag ${m.cls}">${m.emoji} ${m.name}</span>
      ${inner}
      ${tags ? `<div class="etags">${tags}</div>` : ''}
    </div>
    <div class="tail me">${nowHMFrom(e.created_at)} · ${tailText}</div>`;
}

function nowHMFrom(ts){
  if (!ts) return nowHM();
  const d = new Date(ts);
  if (isNaN(d)) return nowHM();
  return pad2(d.getHours()) + ':' + pad2(d.getMinutes());
}

function renderStream(){
  const box = $('#stream');

  if (!entries.length) {
    box.innerHTML = `<div class="empty">
        <span class="big">🌱</span>
        这里还空空的<br>
        说点什么吧，只有你自己看得见
      </div>`;
    return;
  }

  let html = '';
  let lastDay = '';
  entries.forEach(e => {
    const day = dayLabel(e.created_at);
    if (day !== lastDay) {
      html += `<div class="daysep"><span>${day}</span></div>`;
      lastDay = day;
    }
    html += entryHTML(e);
  });
  box.innerHTML = html;
  box.scrollTop = box.scrollHeight;
  bindPlayButtons();
}

function appendEntry(e){
  const box = $('#stream');
  const em = box.querySelector('.empty');
  if (em) em.remove();

  const day = dayLabel(e.created_at);
  if (day !== lastDayLabel) {
    box.insertAdjacentHTML('beforeend', `<div class="daysep"><span>${day}</span></div>`);
    lastDayLabel = day;
  }
  box.insertAdjacentHTML('beforeend', entryHTML(e));
  box.scrollTop = box.scrollHeight;
  bindPlayButtons();
}

function bindPlayButtons(){
  $$('.vplay').forEach(b => {
    if (b._bound) return;
    b._bound = true;
    b.addEventListener('click', () => {
      const url = b.dataset.audio;
      if (!url) { toast('这条语音暂时听不了'); return; }
      const a = new Audio(url);
      b.textContent = '❚❚';
      a.play().catch(() => { toast('播放失败'); b.textContent = '▶'; });
      a.onended = () => { b.textContent = '▶'; };
    });
  });
}

/* ---------- 发送文字 ---------- */
async function sendText(){
  const input = $('#msgInput');
  const text = input.value.trim();
  if (!text) return;

  const payload = {
    kind: 'text',
    text,
    mood: curMood,
    tags: [...curTags]
  };

  input.value = '';
  input.style.height = 'auto';
  $('#sendBtn').disabled = true;

  await pushEntry(payload);
}

async function pushEntry(payload){
  try {
    const rows = await SB.db('entries').insert(payload);
    const row = Array.isArray(rows) ? rows[0] : rows;
    if (row) {
      entries.push(row);
      appendEntry(row);
    }
  } catch(err) {
    console.error(err);
    toast('没发出去：' + (err.message || '未知错误'));
    // 失败时把文字还回输入框，避免内容丢失
    if (payload.kind === 'text') {
      const input = $('#msgInput');
      input.value = payload.text;
      input.dispatchEvent(new Event('input'));
    }
  }
}

/* ==========================================================
   输入交互
   ========================================================== */
function initComposer(){
  const input  = $('#msgInput');
  const hold   = $('#holdTalk');
  const wrap   = $('#inputWrap');
  const toggle = $('#toggleKey');
  const send   = $('#sendBtn');

  /* 自适应高度 */
  input.addEventListener('input', () => {
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 110) + 'px';
    send.disabled = !input.value.trim();
  });
  input.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendText(); }
  });
  send.addEventListener('click', sendText);

  /* 切换 文字 / 语音 */
  toggle.addEventListener('click', () => {
    voiceMode = !voiceMode;
    if (voiceMode) {
      toggle.textContent = '⌨️';
      wrap.classList.add('hidden');
      hold.classList.remove('hidden');
      send.classList.add('hidden');
      input.blur();
    } else {
      toggle.textContent = '🎤';
      wrap.classList.remove('hidden');
      hold.classList.add('hidden');
      send.classList.remove('hidden');
      send.disabled = !input.value.trim();
      input.focus();
    }
  });

  /* 按住说话 */
  let holding = false, recSec = 0, recTimer = null;
  const banner = $('#recBanner'), bannerTxt = $('#recBannerTxt');

  function startRec(){
    if (holding) return;
    holding = true; recSec = 0;
    hold.classList.add('rec');
    hold.textContent = '松开 发送';
    banner.classList.add('on');
    bannerTxt.textContent = '正在听你说… 松手就发出去';
    recTimer = setInterval(() => {
      recSec++;
      bannerTxt.textContent =
        `正在听你说… ${pad2(Math.floor(recSec/60))}:${pad2(recSec%60)} · 松手就发出去`;
    }, 1000);
  }

  function endRec(cancel){
    if (!holding) return;
    holding = false;
    clearInterval(recTimer);
    hold.classList.remove('rec');
    hold.textContent = '按住 说话';
    banner.classList.remove('on');

    if (cancel) return;
    if (recSec < 1) { toast('说话时间太短啦'); return; }

    const dur = pad2(Math.floor(recSec/60)) + ':' + pad2(recSec%60);
    // 一期：先记录「语音条目」（音频上传为二期）
    pushEntry({
      kind: 'voice',
      text: '',
      mood: curMood,
      tags: [...curTags],
      duration_text: dur,
      duration_sec: recSec
    });
  }

  hold.addEventListener('mousedown', startRec);
  hold.addEventListener('touchstart', e => { e.preventDefault(); startRec(); }, { passive: false });
  document.addEventListener('mouseup', () => endRec(false));
  document.addEventListener('touchend', () => endRec(false));
  hold.addEventListener('mouseleave', () => { if (holding) endRec(true); });
}

/* ==========================================================
   顶部按钮 / Tab
   ========================================================== */
function initChrome(){
  $('#logoutBtn').addEventListener('click', logout);

  $('#openHole').addEventListener('click', () => openHole());
  $('#closeHole').addEventListener('click', () => $('#holepage').classList.add('hidden'));
}

/* ==========================================================
   树洞页
   ========================================================== */
let holeFilter = 'all';

function openHole(){
  const page = $('#holepage');
  page.classList.remove('hidden');
  renderHole();
}

function renderHole(){
  const box = $('#holeList');

  // 筛选条
  const filters = [{ k:'all', t:'全部' }].concat(
    CABIN_CONFIG.MOODS.map(m => ({ k: m.key, t: `${m.emoji} ${m.name}` }))
  );
  $('#holeFilters').innerHTML = filters.map(f =>
    `<button data-f="${f.k}" class="${f.k === holeFilter ? 'on' : ''}">${f.t}</button>`
  ).join('');
  $$('#holeFilters button').forEach(b => {
    b.addEventListener('click', () => { holeFilter = b.dataset.f; renderHole(); });
  });

  // 列表（倒序，最新在上）
  let list = entries.slice().reverse();
  if (holeFilter !== 'all') list = list.filter(e => e.mood === holeFilter);

  if (!list.length) {
    box.innerHTML = `<div class="empty"><span class="big">📜</span>还没有记录</div>`;
    return;
  }

  box.innerHTML = list.map(e => {
    const m = moodOf(e.mood);
    const tags = (e.tags || []).map(t => `<span class="ctag">#${escapeHtml(t)}</span>`).join('');
    const body = e.kind === 'voice'
      ? `<div class="vrow" style="display:flex;align-items:center;gap:11px;background:#fff5f7;border-radius:16px;padding:11px 15px">
           <button class="vplay" data-audio="${escapeHtml(e.audio_url || '')}"
             style="background:linear-gradient(135deg,#ff6b81,#ff9f68);color:#fff;width:34px;height:34px;border-radius:50%;display:grid;place-items:center;border:none;font-size:13px">▶</button>
           <div style="flex:1;font-size:12.5px;color:#b0a29d">🎤 语音 · ${escapeHtml(e.duration_text || '0:00')}</div>
         </div>`
      : `<div class="ctext">${escapeHtml(e.text)}</div>`;

    return `<div class="card">
        <div class="ch">
          <span class="badge ${m.cls}">${m.emoji} ${m.name}</span>
          <span class="ctime">${dayLabel(e.created_at)} ${nowHMFrom(e.created_at)}</span>
        </div>
        ${body}
        ${tags ? `<div class="ctags">${tags}</div>` : ''}
      </div>`;
  }).join('');

  bindPlayButtons();
}

/* ==========================================================
   启动
   ========================================================== */
document.addEventListener('DOMContentLoaded', () => {
  $('#authSubmit').addEventListener('click', doAuth);
  $$('.authtabs button').forEach(b => b.addEventListener('click', () => setAuthMode(b.dataset.m)));

  const pwd = $('#pwdInput');
  if (pwd) pwd.addEventListener('keydown', e => { if (e.key === 'Enter') doAuth(); });
  const pwd2 = $('#pwdInput2');
  if (pwd2) pwd2.addEventListener('keydown', e => { if (e.key === 'Enter') doAuth(); });

  initComposer();
  initChrome();
  setAuthMode('login');
  boot();
});
