/* ==========================================================
   小屋 · Supabase 轻量客户端
   ----------------------------------------------------------
   不依赖任何 CDN，纯 fetch 直连 Supabase REST + Auth。
   好处：离线可缓存、加载快、无第三方脚本风险。
   ========================================================== */

const SB = (() => {
  const U = CABIN_CONFIG.SUPABASE_URL.replace(/\/$/, '');
  const K = CABIN_CONFIG.SUPABASE_KEY;
  const SESSION_KEY = 'cabin_session';

  let session = null;
  try { session = JSON.parse(localStorage.getItem(SESSION_KEY) || 'null'); } catch(e) { session = null; }

  /* ---------- 会话管理 ---------- */
  function setSession(s) {
    session = s;
    if (s) localStorage.setItem(SESSION_KEY, JSON.stringify(s));
    else   localStorage.removeItem(SESSION_KEY);
  }
  function getSession() { return session; }
  function getToken()   { return session && session.access_token ? session.access_token : K; }
  function getUser()    { return session && session.user ? session.user : null; }
  function isLoggedIn() { return !!(session && session.access_token); }

  /* ---------- 请求头 ---------- */
  function headers(extra) {
    const h = {
      'apikey': K,
      'Authorization': 'Bearer ' + getToken(),
      'Content-Type': 'application/json'
    };
    return Object.assign(h, extra || {});
  }

  async function parse(res) {
    const text = await res.text();
    let data = null;
    try { data = text ? JSON.parse(text) : null; } catch(e) { data = text; }
    if (!res.ok) {
      const msg = (data && (data.msg || data.message || data.error_description || data.error)) || ('HTTP ' + res.status);
      const err = new Error(msg);
      err.status = res.status;
      err.data = data;
      throw err;
    }
    return data;
  }

  /* ---------- Auth ---------- */
  async function signUp(email, password) {
    const res = await fetch(U + '/auth/v1/signup', {
      method: 'POST',
      headers: { 'apikey': K, 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    const data = await parse(res);
    // 如果项目开了「无需邮箱确认」，signup 会直接返回 session
    if (data && data.access_token) setSession(data);
    return data;
  }

  async function signIn(email, password) {
    const res = await fetch(U + '/auth/v1/token?grant_type=password', {
      method: 'POST',
      headers: { 'apikey': K, 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    const data = await parse(res);
    if (data && data.access_token) setSession(data);
    return data;
  }

  async function signOut() {
    try {
      await fetch(U + '/auth/v1/logout', { method: 'POST', headers: headers() });
    } catch(e) { /* 忽略网络错误，本地照样登出 */ }
    setSession(null);
  }

  /* 用 refresh_token 续期 */
  async function refresh() {
    if (!session || !session.refresh_token) return null;
    try {
      const res = await fetch(U + '/auth/v1/token?grant_type=refresh_token', {
        method: 'POST',
        headers: { 'apikey': K, 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: session.refresh_token })
      });
      const data = await parse(res);
      if (data && data.access_token) { setSession(data); return data; }
      return null;
    } catch(e) {
      setSession(null);
      return null;
    }
  }

  /* ---------- Database (PostgREST) ---------- */
  async function db(table) {
    const base = U + '/rest/v1/' + table;
    const q = { select: null, filters: [], order: null, limit: null };

    const builder = {
      select(cols) { q.select = cols || '*'; return builder; },
      eq(col, val) { q.filters.push(col + '=eq.' + encodeURIComponent(val)); return builder; },
      order(col, opts) {
        const dir = (opts && opts.ascending === false) ? 'desc' : 'asc';
        q.order = col + '.' + dir;
        return builder;
      },
      limit(n) { q.limit = n; return builder; },

      async get() {
        const params = [];
        if (q.select) params.push('select=' + q.select);
        q.filters.forEach(f => params.push(f));
        if (q.order)  params.push('order=' + q.order);
        if (q.limit)  params.push('limit=' + q.limit);
        const url = base + (params.length ? '?' + params.join('&') : '');
        const res = await fetch(url, { headers: headers() });
        return parse(res);
      },

      async insert(rows) {
        const res = await fetch(base, {
          method: 'POST',
          headers: headers({ 'Prefer': 'return=representation' }),
          body: JSON.stringify(rows)
        });
        return parse(res);
      },

      async update(patch) {
        const params = q.filters.length ? '?' + q.filters.join('&') : '';
        const res = await fetch(base + params, {
          method: 'PATCH',
          headers: headers({ 'Prefer': 'return=representation' }),
          body: JSON.stringify(patch)
        });
        return parse(res);
      },

      async remove() {
        const params = q.filters.length ? '?' + q.filters.join('&') : '';
        const res = await fetch(base + params, {
          method: 'DELETE',
          headers: headers({ 'Prefer': 'return=representation' })
        });
        return parse(res);
      },

      async single() {
        const rows = await builder.get();
        return Array.isArray(rows) ? (rows[0] || null) : rows;
      }
    };
    return builder;
  }

  return {
    url: U,
    setSession, getSession, getToken, getUser, isLoggedIn,
    signUp, signIn, signOut, refresh,
    db
  };
})();
