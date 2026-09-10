/* ==========================================================
   小屋 · 设置 / 个人资料页
   ========================================================== */

const PROFILE = (() => {

  const AVATARS = [
    { k:'sprout', e:'🌱', n:'小树苗' },
    { k:'bear',   e:'🐻', n:'小熊'   },
    { k:'cat',    e:'🐱', n:'小猫'   },
    { k:'bunny',  e:'🐰', n:'小兔'   },
    { k:'cloud',  e:'☁️', n:'小云'   },
    { k:'pig',    e:'🐷', n:'小猪'   },
    { k:'fox',    e:'🦊', n:'小狐'   },
    { k:'panda',  e:'🐼', n:'熊猫'   }
  ];

  const HOBBY_PRESET = ['看书','电影','音乐','运动','游戏','美食','旅行','摄影','手作','追剧','咖啡','猫咪','狗狗','动漫'];

  let data = null;       // 当前资料
  let dirty = false;
  let curAvatar = 'sprout';

  async function load(){
    if (data) return data;
    try {
      const row = await SB.db('profiles').select('*').eq('user_id', SB.getUser().id).single();
      data = row || {};
    } catch(e) {
      data = {};
    }
    return data;
  }

  async function save(){
    const patch = {
      user_id: SB.getUser().id,
      nickname: $('#pfNick').value.trim(),
      avatar_kind: curAvatar,
      birthday: $('#pfBirth').value || null,
      gender: $('#pfGender').value || '',
      bio: $('#pfBio').value.trim(),
      hobbies: getHobbies(),
      updated_at: new Date().toISOString()
    };

    try {
      const existing = await SB.db('profiles').select('user_id').eq('user_id', patch.user_id).single();
      if (existing) {
        await SB.db('profiles').eq('user_id', patch.user_id).update(patch);
      } else {
        await SB.db('profiles').insert(patch);
      }
      data = Object.assign(data || {}, patch);
      toast('已保存 ✨');
      applyAvatar();
    } catch(e) {
      console.error(e);
      toast('保存失败：' + (e.message || '未知错误'));
    }
  }

  function getHobbies(){
    const out = [];
    $$('#pfHobbies .hchip').forEach(c => { if (c.classList.contains('on')) out.push(c.dataset.h); });
    return out;
  }

  function renderHobbies(){
    const cur = (data && data.hobbies) || [];
    const all = [...new Set([...HOBBY_PRESET, ...cur])];
    $('#pfHobbies').innerHTML = all.map(h =>
      `<button class="hchip ${cur.includes(h) ? 'on' : ''}" data-h="${h}">${h}</button>`
    ).join('');
    $$('#pfHobbies .hchip').forEach(c => {
      c.addEventListener('click', () => c.classList.toggle('on'));
    });
  }

  function renderAvatars(){
    $('#pfAvatars').innerHTML = AVATARS.map(a =>
      `<button class="avopt ${a.k === curAvatar ? 'on' : ''}" data-a="${a.k}" title="${a.n}">
         <span>${a.e}</span>
       </button>`
    ).join('');
    $$('#pfAvatars .avopt').forEach(b => {
      b.addEventListener('click', () => {
        curAvatar = b.dataset.a;
        $$('#pfAvatars .avopt').forEach(x => x.classList.remove('on'));
        b.classList.add('on');
      });
    });
  }

  /* 把头像应用到顶部 */
  function applyAvatar(){
    if (!data) return;
    const a = AVATARS.find(x => x.k === data.avatar_kind) || AVATARS[0];
    const el = $('#topAvatar');
    if (el) el.textContent = a.e;
    // 昵称
    const nick = (data.nickname || '').trim();
    if (nick) $('#topTitle').textContent = nick + '的小屋';
  }

  async function open(){
    await load();
    curAvatar = (data && data.avatar_kind) || 'sprout';

    $('#pfNick').value     = (data && data.nickname) || '';
    $('#pfBirth').value    = (data && data.birthday) || '';
    $('#pfGender').value   = (data && data.gender) || '';
    $('#pfBio').value      = (data && data.bio) || '';
    $('#pfEmail').textContent = (SB.getUser() || {}).email || '';

    renderAvatars();
    renderHobbies();
    renderStats();

    $('#profilepage').classList.remove('hidden');
  }

  function close(){ $('#profilepage').classList.add('hidden'); }

  /* 活跃度统计 */
  function renderStats(){
    const s = BUDDY.stats(window.__entries || []);
    const f = BUDDY.face(s);
    $('#pfBuddy').innerHTML = `<span class="pfb-art">${f.art}</span>`;
    $('#pfBuddyLabel').textContent = f.label;

    $('#pfStats').innerHTML = [
      { n: s.total,      l: '总记录' },
      { n: s.activeDays, l: '记录天数' },
      { n: s.streak,     l: '连续打卡' },
      { n: s.joy + s.luck, l: '开心时刻' },
      { n: s.roar,       l: '吐槽一下' },
      { n: s.think,      l: '思考时刻' }
    ].map(x => `<div class="pstat"><div class="pn">${x.n}</div><div class="pl">${x.l}</div></div>`).join('');
  }

  /* 修改密码 */
  async function changePassword(){
    const p1 = $('#pwNew').value;
    const p2 = $('#pwNew2').value;
    if (!p1 || p1.length < 6) return toast('新密码至少 6 位');
    if (p1 !== p2)            return toast('两次输入不一致');

    const btn = $('#pwSubmit');
    btn.disabled = true; btn.textContent = '正在修改…';
    try {
      const res = await fetch(SB.url + '/auth/v1/user', {
        method: 'PUT',
        headers: {
          'apikey': CABIN_CONFIG.SUPABASE_KEY,
          'Authorization': 'Bearer ' + SB.getToken(),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ password: p1 })
      });
      const txt = await res.text();
      if (!res.ok) {
        let m = txt;
        try { const j = JSON.parse(txt); m = j.msg || j.message || j.error_description || txt; } catch(e) {}
        throw new Error(m);
      }
      $('#pwNew').value = ''; $('#pwNew2').value = '';
      toast('密码已修改 ✅');
    } catch(e) {
      toast('修改失败：' + (e.message || '未知错误'));
    } finally {
      btn.disabled = false; btn.textContent = '修改密码';
    }
  }

  return { open, close, save, applyAvatar, changePassword, load };
})();
