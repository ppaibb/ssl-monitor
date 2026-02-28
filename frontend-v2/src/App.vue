<template>
  <div class="app-wrapper">
    <div class="glow-orb glow-top"></div>
    <div class="glow-orb glow-bottom"></div>
    <router-view />
  </div>
</template>

<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'Helvetica Neue', Helvetica, Arial, sans-serif;
  background-color: var(--color-bg-1);
  transition: background-color 0.3s;
  min-height: 100vh;
  margin: 0;
}

.app-wrapper {
  position: relative;
  min-height: 100vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* 独立的柔和背景光晕，彻底避免 body pseudo-element 引起的事件穿透或层级问题 */
.glow-orb {
  position: absolute; /* 修改为 absolute，跟随全局滚动或相对容器 */
  border-radius: 50%;
  filter: blur(80px);
  z-index: 0;
  pointer-events: none;
}
.glow-top {
  top: -20vh;
  left: -10vw;
  width: 60vw;
  height: 60vh;
  background: radial-gradient(circle, rgba(22, 93, 255, 0.12) 0%, transparent 70%);
}
.glow-bottom {
  bottom: -20vh;
  right: -10vw;
  width: 50vw;
  height: 50vh;
  background: radial-gradient(circle, rgba(0, 180, 42, 0.08) 0%, transparent 70%);
}

/* 高级暗黑模式颜色微调 */
body[arco-theme='dark'] {
  --color-bg-1: #0a0d14;         /* 更深邃的背景色 */
  --color-bg-2: #141824;         /* 稍微提亮的卡片底色 */
  --color-border: rgba(255, 255, 255, 0.06); /* 更微弱的边框 */
  --color-border-2: rgba(255, 255, 255, 0.08);
}
body[arco-theme='dark'] .glow-top {
  background: radial-gradient(circle, rgba(22, 93, 255, 0.2) 0%, transparent 70%);
}
body[arco-theme='dark'] .glow-bottom {
  background: radial-gradient(circle, rgba(0, 180, 42, 0.1) 0%, transparent 70%);
}

/* 修改滚动条使其更加精致 */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}
::-webkit-scrollbar-thumb {
  background: var(--color-fill-3);
  border-radius: 4px;
}
::-webkit-scrollbar-thumb:hover {
  background: var(--color-fill-4);
}
::-webkit-scrollbar-track {
  background: transparent;
}
</style>
