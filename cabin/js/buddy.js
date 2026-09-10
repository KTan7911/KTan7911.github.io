/* ==========================================================
   小屋 · 陪伴树苗 🌱
   ----------------------------------------------------------
   它会根据你的记录状态变化，但永远不催你。
   有记录 → 高兴；没记录 → 安静待着；久了 → 打个盹。
   ========================================================== */

const BUDDY = (() => {

  /* 计算活跃度统计 */
  function stats(entries){
    const days = new Set();
    let roar = 0, joy = 0, calm = 0, think = 0, luck = 0;

    entries.forEach(e => {
      const d = new Date(e.created_at);
      if (!isNaN(d)) days.add(dayKey(d));
      switch (e.mood) {
        case 'roar':  roar++;  break;
        case 'joy':   joy++;   break;
        case 'calm':  calm++;  break;
        case 'think': think++; break;
        case 'luck':  luck++;  break;
      }
    });

    const total = entries.length;
    const activeDays = days.size;
    const streak = calcStreak(days);

    // 最近一条的心情
    const last = entries.length ? entries[entries.length - 1] : null;
    const lastMood = last ? last.mood : null;

    // 距离上次记录多少天
    let gapDays = 0;
    if (last) {
      const lastD = new Date(last.created_at);
      const today = new Date();
      lastD.setHours(0,0,0,0); today.setHours(0,0,0,0);
      gapDays = Math.round((today - lastD) / 86400000);
    }

    // 今天是否记录过
    const todayKey = dayKey(new Date());
    const todayCount = entries.filter(e => dayKey(new Date(e.created_at)) === todayKey).length;

    return { total, activeDays, streak, roar, joy, calm, think, luck,
             lastMood, gapDays, todayCount };
  }

  function dayKey(d){
    return d.getFullYear() + '-' +
           String(d.getMonth()+1).padStart(2,'0') + '-' +
           String(d.getDate()).padStart(2,'0');
  }

  function calcStreak(days){
    let n = 0;
    const d = new Date();
    if (!days.has(dayKey(d))) d.setDate(d.getDate() - 1);   // 今天还没记 → 从昨天算
    while (days.has(dayKey(d))) { n++; d.setDate(d.getDate() - 1); }
    return n;
  }

  /* 树苗的形象与台词 */
  const FACES = {
    sleepy:  { art: '🌱', label: '打盹中',  tone: 'quiet' },
    idle:    { art: '🌿', label: '安静陪着', tone: 'quiet' },
    happy:   { art: '🌿', label: '精神不错', tone: 'warm'  },
    glad:    { art: '🌳', label: '长高啦',   tone: 'warm'  },
    bloom:   { art: '🌸', label: '开花了',   tone: 'warm'  },
    crown:   { art: '👑', label: '闪闪发光', tone: 'glow'  },
    worried: { art: '🥀', label: '有点蔫',   tone: 'soft'  },
    cheer:   { art: '🎉', label: '跟着开心', tone: 'warm'  },
    miss:    { art: '💤', label: '想你了',   tone: 'soft'  }
  };

  /* 根据统计决定树苗状态 */
  function face(s){
    // 很久没来了
    if (s.gapDays >= 7)             return FACES.miss;
    if (s.gapDays >= 3)             return FACES.sleepy;
    // 连续打卡里程碑
    if (s.streak >= 30)             return FACES.crown;
    if (s.streak >= 7)              return FACES.bloom;
    if (s.streak >= 3)              return FACES.glad;
    // 今天的心情
    if (s.todayCount > 0) {
      if (s.lastMood === 'joy' || s.lastMood === 'luck') return FACES.cheer;
      if (s.lastMood === 'roar')  return FACES.idle;
      return FACES.happy;
    }
    // 没记录但也没断
    return FACES.idle;
  }

  /* 台词 —— 永远温柔，不催不责备 */
  function speech(s, f){
    if (s.total === 0) return '欢迎回来，我会慢慢长大 🌱';

    if (s.gapDays >= 7)  return '好久不见…我一直在等你，不着急';
    if (s.gapDays >= 3)  return '我打了个盹，你回来就好';
    if (s.streak >= 30)  return `连续 ${s.streak} 天，你真的很认真在照顾自己`;
    if (s.streak >= 7)   return `连续 ${s.streak} 天了，我快长成小树啦`;
    if (s.streak >= 3)   return `连续 ${s.streak} 天，陪你一起长高 🌿`;
    if (s.todayCount > 0) {
      if (s.lastMood === 'joy' || s.lastMood === 'luck') return '看你开心，我也跟着高兴 ✨';
      if (s.lastMood === 'roar')  return '说出来就好，我听着呢';
      if (s.lastMood === 'calm')  return '平静的时候也很好';
      return '你在想事情呀，慢慢来';
    }
    return '今天想说点什么吗？不说也没关系';
  }

  /* 渲染到顶部 */
  function render(container, s){
    const f = face(s);
    container.className = 'buddy t-' + f.tone;
    container.innerHTML = `
      <div class="buddy-art">${f.art}</div>
      <div class="buddy-txt">
        <div class="buddy-speech">${speech(s, f)}</div>
        ${s.total > 0 ? `<div class="buddy-meta">${s.total} 条记录 · 连续 ${s.streak} 天</div>` : ''}
      </div>`;
    // 触发一次动画
    container.classList.remove('pop');
    void container.offsetWidth;
    container.classList.add('pop');
  }

  return { stats, render, face, dayKey, calcStreak };
})();
