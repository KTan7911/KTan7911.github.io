/* ============================================
   个人网站交互脚本
   ============================================ */

// 页脚年份自动更新
document.getElementById("year").textContent = new Date().getFullYear();

// 移动端菜单开关
const menuToggle = document.getElementById("menuToggle");
const menu = document.getElementById("menu");

if (menuToggle && menu) {
  menuToggle.addEventListener("click", () => {
    menu.classList.toggle("open");
  });

  // 点击菜单项后自动收起菜单
  menu.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", () => {
      menu.classList.remove("open");
    });
  });
}

// 平滑滚动（配合 CSS scroll-behavior，此处理兼容性）
document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
  anchor.addEventListener("click", function (e) {
    const target = document.querySelector(this.getAttribute("href"));
    if (target) {
      e.preventDefault();
      target.scrollIntoView({ behavior: "smooth" });
    }
  });
});
