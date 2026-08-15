/* ============================================
   科幻启动页交互
   拖拽星网聚能 -> 亮点自动爆炸 -> 漫天星星闪烁
   ============================================ */

(function () {
  const splash = document.getElementById("splash");
  if (!splash) return;

  const canvas = document.getElementById("splashCanvas");
  const ctx = canvas.getContext("2d");
  const grid = splash.querySelector(".splash-grid");

  let W = 0, H = 0, DPR = 1;
  let rafId = null;
  let bursted = false;   // 是否已爆炸
  let burstAt = null;    // 爆炸中心点

  // 鼠标状态
  const mouse = { x: -9999, y: -9999, vx: 0, vy: 0, active: false };

  // 颜色主题
  const COLORS = ["#7df9ff", "#4f6ef7", "#b388ff", "#22d3ee", "#a78bfa", "#f0abfc"];

  // 粒子集合
  let particles = [];   // 星网粒子
  let stars = [];       // 漫天星星（爆炸后生成）

  /* ---------- 尺寸与初始化 ---------- */
  function resize() {
    DPR = Math.min(window.devicePixelRatio || 1, 2);
    W = splash.clientWidth;
    H = splash.clientHeight;
    canvas.width = W * DPR;
    canvas.height = H * DPR;
    canvas.style.width = W + "px";
    canvas.style.height = H + "px";
    ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
    initParticles();
  }

  function initParticles() {
    const count = Math.min(110, Math.max(45, Math.floor((W * H) / 16000)));
    particles = [];
    for (let i = 0; i < count; i++) {
      particles.push({
        x: Math.random() * W,
        y: Math.random() * H,
        vx: (Math.random() - 0.5) * 0.35,
        vy: (Math.random() - 0.5) * 0.35,
        r: Math.random() * 1.8 + 0.6,
        color: COLORS[Math.floor(Math.random() * COLORS.length)],
        alpha: Math.random() * 0.5 + 0.35,
        twinkle: Math.random() * Math.PI * 2,
      });
    }
  }

  /* ---------- 鼠标事件 ---------- */
  window.addEventListener("mousemove", (e) => {
    const rect = canvas.getBoundingClientRect();
    const nx = e.clientX - rect.left;
    const ny = e.clientY - rect.top;
    mouse.vx = (nx - mouse.x) * 0.45;
    mouse.vy = (ny - mouse.y) * 0.45;
    mouse.x = nx;
    mouse.y = ny;
    mouse.active = true;
  });

  splash.addEventListener("mouseleave", () => {
    mouse.active = false;
  });

  // 网格视差跟随鼠标
  window.addEventListener("mousemove", (e) => {
    if (!grid) return;
    const cx = e.clientX / window.innerWidth - 0.5;
    const cy = e.clientY / window.innerHeight - 0.5;
    grid.style.transform = `translate(${cx * -28}px, ${cy * -28}px)`;
  });

  /* ---------- 粒子更新（拖拽聚能核心） ---------- */
  function updateParticles() {
    const gatherR = 150; // 聚能吸引半径（缩小，避免鼠标一动就全吸走）
    for (const p of particles) {
      p.twinkle += 0.03;

      // 鼠标聚能：粒子被吸向鼠标，越近吸力越强 -> 慢慢聚成亮点
      if (mouse.active && !bursted) {
        const dx = mouse.x - p.x;
        const dy = mouse.y - p.y;
        const dist = Math.hypot(dx, dy);
        if (dist < gatherR && dist > 0.001) {
          const pull = 1 - dist / gatherR;
          p.vx += (dx / dist) * pull * 0.10;   // 慢速吸引
          p.vy += (dy / dist) * pull * 0.10;
          // 轻微跟随鼠标速度
          p.vx += mouse.vx * pull * 0.18;
          p.vy += mouse.vy * pull * 0.18;
        }
      }

      // 边界回弹
      if (p.x < 0) { p.x = 0; p.vx *= -0.7; }
      if (p.x > W) { p.x = W; p.vx *= -0.7; }
      if (p.y < 0) { p.y = 0; p.vy *= -0.7; }
      if (p.y > H) { p.y = H; p.vy *= -0.7; }

      p.x += p.vx;
      p.y += p.vy;
      p.vx *= 0.9;
      p.vy *= 0.9;
    }
  }

  /* ---------- 检测聚能完成 -> 自动爆炸 ---------- */
  function checkGather() {
    if (bursted || !mouse.active) return;
    // 统计距离鼠标 60px 内的粒子比例
    let near = 0;
    for (const p of particles) {
      if (Math.hypot(p.x - mouse.x, p.y - mouse.y) < 60) near++;
    }
    if (near / particles.length > 0.75) {
      burst(mouse.x, mouse.y);
    }
  }

  /* ---------- 爆炸：漫天星星（爆炸后保持闪烁，等待点击进入） ---------- */
  function burst(cx, cy) {
    if (bursted) return;
    bursted = true;
    burstAt = { x: cx, y: cy };
    splash.classList.add("bursting");

    // 粒子向外爆炸扩散
    for (const p of particles) {
      const ang = Math.random() * Math.PI * 2;
      const sp = Math.random() * 12 + 6;
      p.vx = Math.cos(ang) * sp;
      p.vy = Math.sin(ang) * sp;
      p.alpha *= 0.4;
    }

    // 生成漫天星星：有大有小、有远有近、随机、慢闪
    const starCount = Math.min(260, Math.max(140, Math.floor((W * H) / 5500)));
    stars = [];
    for (let i = 0; i < starCount; i++) {
      const ang = Math.random() * Math.PI * 2;
      const dist = Math.random() * Math.max(W, H) * 0.55;
      // 大小：近的大、远的小（对数分布让大小更丰富）
      const depth = Math.random(); // 0=远 1=近
      const r = 0.4 + Math.pow(depth, 1.8) * 2.6;
      stars.push({
        x: cx + Math.cos(ang) * dist,
        y: cy + Math.sin(ang) * dist,
        r: r,
        // 远星暗、近星亮
        alpha: 0.2 + depth * 0.7,
        // 远星慢闪、近星稍快，整体缓慢
        twinkleSpeed: 0.004 + depth * 0.016,
        twinkle: Math.random() * Math.PI * 2,
        color: Math.random() > 0.75
          ? "#f0abfc"
          : Math.random() > 0.5
            ? "#bcd6ff"
            : "#ffffff",
      });
    }

    // 提示文案切换为"点击进入"
    const hint = splash.querySelector(".splash-hint");
    if (hint) hint.textContent = "CLICK TO ENTER";
  }

  /* ---------- 鼠标按压：平滑进入网站 ---------- */
  let entered = false;
  function enterSite() {
    if (entered) return;
    entered = true;
    splash.classList.add("leaving");
    document.body.classList.remove("splash-lock");
    setTimeout(() => {
      cancelAnimationFrame(rafId);
      splash.remove();
      window.removeEventListener("resize", resize);
    }, 900);
  }

  // 鼠标按压（点击/触摸）进入
  splash.addEventListener("click", (e) => {
    if (!bursted) {
      burst(e.clientX, e.clientY); // 未聚能时点击：先引爆
    }
    enterSite();
  });

  /* ---------- 星星闪烁 ---------- */
  function updateStars() {
    for (const s of stars) {
      s.twinkle += s.twinkleSpeed;
    }
  }

  /* ---------- 绘制 ---------- */
  function draw() {
    ctx.clearRect(0, 0, W, H);

    // 漫天星星（爆炸后）
    for (const s of stars) {
      const a = s.alpha * (0.6 + 0.4 * Math.sin(s.twinkle));
      // 大星星带柔光（近），小星星锐利（远）
      if (s.r > 1.4) {
        ctx.beginPath();
        ctx.arc(s.x, s.y, s.r * 3.2, 0, Math.PI * 2);
        ctx.fillStyle = s.color;
        ctx.globalAlpha = a * 0.10;
        ctx.fill();
      }
      ctx.beginPath();
      ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
      ctx.fillStyle = s.color;
      ctx.globalAlpha = a;
      ctx.fill();

      // 十字光芒（较大的近星）
      if (s.r > 2.2) {
        ctx.globalAlpha = a * 0.55;
        ctx.fillRect(s.x - s.r * 3.4, s.y - 0.4, s.r * 6.8, 0.8);
        ctx.fillRect(s.x - 0.4, s.y - s.r * 3.4, 0.8, s.r * 6.8);
      }
    }

    // 星网连线（未爆炸时）
    if (!bursted) {
      const linkDist = 130;
      ctx.lineWidth = 0.7;
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const a = particles[i], b = particles[j];
          const d = Math.hypot(a.x - b.x, a.y - b.y);
          if (d < linkDist) {
            ctx.strokeStyle = `rgba(125, 249, 255, ${(1 - d / linkDist) * 0.22})`;
            ctx.beginPath();
            ctx.moveTo(a.x, a.y);
            ctx.lineTo(b.x, b.y);
            ctx.stroke();
          }
        }
      }
    }

    // 星网粒子（带发光）
    for (const p of particles) {
      const glow = 0.55 + 0.45 * Math.sin(p.twinkle);
      const a = p.alpha * (0.5 + 0.5 * glow);
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r * 3, 0, Math.PI * 2);
      ctx.fillStyle = p.color;
      ctx.globalAlpha = a * 0.12;
      ctx.fill();

      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = p.color;
      ctx.globalAlpha = a;
      ctx.fill();
    }

    // 聚能光晕：粒子聚集时鼠标处形成亮点
    if (!bursted && mouse.active) {
      let near = 0;
      for (const p of particles) {
        if (Math.hypot(p.x - mouse.x, p.y - mouse.y) < 90) near++;
      }
      const ratio = near / particles.length;
      if (ratio > 0.3) {
        const strength = Math.min(1, (ratio - 0.3) / 0.6);
        const size = 6 + ratio * 20;
        const grad = ctx.createRadialGradient(mouse.x, mouse.y, 0, mouse.x, mouse.y, size * 5);
        grad.addColorStop(0, `rgba(240, 252, 255, ${0.9 * strength})`);
        grad.addColorStop(0.15, `rgba(125, 249, 255, ${0.6 * strength})`);
        grad.addColorStop(0.5, `rgba(79, 110, 247, ${0.25 * strength})`);
        grad.addColorStop(1, "rgba(79, 110, 247, 0)");
        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.arc(mouse.x, mouse.y, size * 5, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    ctx.globalAlpha = 1;
  }

  /* ---------- 动画循环 ---------- */
  function loop() {
    updateParticles();
    checkGather();
    updateStars();
    draw();
    rafId = requestAnimationFrame(loop);
  }

  /* ---------- 启动 ---------- */
  resize();
  window.addEventListener("resize", resize);
  document.body.classList.add("splash-lock");
  loop();
})();
