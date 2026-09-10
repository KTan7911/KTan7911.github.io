/* ==========================================================
   小屋 · 配置文件
   ----------------------------------------------------------
   这里放的都是「可以公开」的信息（会被打进前端代码）。
   安全由 Supabase 的 RLS 策略保证，不靠藏 key。

   ⚠️ 千万不要把 service_role key 写在这里！
   ========================================================== */

const CABIN_CONFIG = {
  // Supabase 项目
  SUPABASE_URL: 'https://effceweqqmnsekpvkswq.supabase.co',
  SUPABASE_KEY: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVmZmNld2VxcW1uc2VrcHZrc3dxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODkwNDMyNTcsImV4cCI6MjEwNDYxOTI1N30.iJssRfdnfCjfrKnUBMCL1HWQCdd0dzwtCX697Z2ZFv4',

  // 产品信息
  APP_NAME: '小屋',
  APP_SLOGAN: '只有你自己看得见 🌿',

  // 心情定义（顺序即展示顺序）
  MOODS: [
    { key: 'roar',  emoji: '😤', name: '吐槽', cls: 'm-roar'  },
    { key: 'joy',   emoji: '😄', name: '开心', cls: 'm-joy'   },
    { key: 'calm',  emoji: '😌', name: '平静', cls: 'm-calm'  },
    { key: 'think', emoji: '🤔', name: '思考', cls: 'm-think' },
    { key: 'luck',  emoji: '✨', name: '小确幸', cls: 'm-luck' }
  ],

  // 话题标签
  TAGS: ['她', '工作', '生活', '家人', '自己', '小确幸', '烦恼', '未来'],

  // 允许注册的邮箱（白名单安全阀；为空数组 = 不限制）
  ALLOWED_EMAILS: [],

  // AI 对话（一期先留空，二期接 Edge Function）
  AI_ENDPOINT: ''
};
