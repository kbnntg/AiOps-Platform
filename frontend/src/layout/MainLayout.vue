<template>
  <el-container class="main-layout">
    <!-- 自定义背景图层（固定在内容下方） -->
    <AppBackground />

    <!-- 侧边栏 -->
    <el-aside :width="isCollapse ? '64px' : '220px'" class="sidebar">
      <div class="logo">
        <div class="logo-icon">AI</div>
        <transition name="fade">
          <span v-if="!isCollapse" class="logo-text">AIOps 平台</span>
        </transition>
      </div>
      <el-menu :default-active="$route.path" router :collapse="isCollapse"
               background-color="transparent"
               text-color="rgba(255,255,255,0.75)"
               active-text-color="#fff"
               class="side-menu">
        <el-menu-item v-for="item in menuItems" :key="item.path" :index="item.path">
          <el-icon><component :is="item.icon" /></el-icon>
          <template #title>
            <span>{{ item.title }}</span>
          </template>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <!-- 顶栏 -->
      <el-header class="header">
        <div class="header-left">
          <el-icon class="collapse-btn" @click="isCollapse = !isCollapse">
            <component :is="isCollapse ? 'Expand' : 'Fold'" />
          </el-icon>
          <span class="page-title">{{ $route.meta.title }}</span>
        </div>
        <div class="header-right">
          <el-tooltip content="更换背景" placement="bottom">
            <el-icon class="header-icon" @click="appearanceStore.openDrawer()"><Picture /></el-icon>
          </el-tooltip>
          <el-tooltip content="刷新" placement="bottom">
            <el-icon class="header-icon" @click="refreshPage"><Refresh /></el-icon>
          </el-tooltip>
          <el-dropdown @command="handleCommand">
            <span class="user-info">
              <el-avatar :size="32" class="avatar">
                {{ authStore.username?.charAt(0)?.toUpperCase() }}
              </el-avatar>
              <div class="user-detail" v-show="!isMobile">
                <div class="username">{{ authStore.username }}</div>
                <div class="user-role">{{ authStore.role === 'admin' ? '管理员' : '只读用户' }}</div>
              </div>
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="appearance">
                  <el-icon><Picture /></el-icon> 更换背景
                </el-dropdown-item>
                <el-dropdown-item command="profile">
                  <el-icon><User /></el-icon> 个人信息
                </el-dropdown-item>
                <el-dropdown-item divided command="logout">
                  <el-icon><SwitchButton /></el-icon> 退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-main class="main-content">
        <router-view v-slot="{ Component }">
          <transition name="page" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>

    <!-- 外观设置抽屉 -->
    <AppearanceSetting />
  </el-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useAppearanceStore } from '@/stores/appearance'
import { ElMessage } from 'element-plus'
import AppBackground from '@/components/AppBackground.vue'
import AppearanceSetting from '@/components/AppearanceSetting.vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const appearanceStore = useAppearanceStore()
const isCollapse = ref(false)
const isMobile = ref(window.innerWidth < 768)

const menuItems = computed(() => {
  const items = [
    { path: '/dashboard', title: '资源总览', icon: 'Odometer' },
    { path: '/topology', title: '服务拓扑', icon: 'Share' },
    { path: '/copilot', title: 'AI Copilot', icon: 'ChatDotRound' },
    { path: '/pods', title: 'Pod 管理', icon: 'Box' },
    { path: '/deployments', title: '副本管理', icon: 'Operation' },
    { path: '/alerts', title: '告警历史', icon: 'Bell' },
  ]
  if (authStore.role === 'admin') items.push({ path: '/audit', title: '审计日志', icon: 'Document' })
  return items
})

function refreshPage() {
  window.location.reload()
}

function handleCommand(cmd: string) {
  if (cmd === 'logout') {
    authStore.clearAuth()
    router.push('/login')
    ElMessage.success('已退出登录')
  } else if (cmd === 'appearance') {
    appearanceStore.openDrawer()
  } else if (cmd === 'profile') {
    ElMessage.info('个人信息功能开发中')
  }
}

// 工作面板挂载时载入当前用户的外观配置（不同用户互不影响）
onMounted(() => {
  appearanceStore.init(authStore.username)
})

// 离开工作面板（例如退出登录）时恢复默认外观，避免影响登录页
onBeforeUnmount(() => {
  appearanceStore.clearDocumentEffect()
})
</script>

<style scoped>
.main-layout { height: 100vh; }

/* ========== 侧边栏 ========== */
.sidebar {
  background: var(--sidebar-gradient);
  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
  box-shadow: 4px 0 24px rgba(30, 27, 75, 0.15);
}

.logo {
  height: 64px;
  display: flex;
  align-items: center;
  padding: 0 20px;
  gap: 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}
.logo-icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: linear-gradient(135deg, #6366f1, #a855f7);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-weight: bold;
  font-size: 14px;
  flex-shrink: 0;
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.4);
}
.logo-text {
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 0.5px;
  white-space: nowrap;
}

.side-menu {
  border-right: none !important;
  padding: 12px 8px;
}
.side-menu :deep(.el-menu-item) {
  height: 48px;
  border-radius: 10px;
  margin-bottom: 4px;
  transition: all 0.25s;
}
.side-menu :deep(.el-menu-item:hover) {
  background: rgba(139, 92, 246, 0.15) !important;
}
.side-menu :deep(.el-menu-item.is-active) {
  background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
  box-shadow: 0 4px 16px rgba(99, 102, 241, 0.4);
}

/* ========== 顶栏 ========== */
.header {
  height: 64px;
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  position: sticky;
  top: 0;
  z-index: 10;
}

.header-left { display: flex; align-items: center; gap: 16px; }
.collapse-btn {
  font-size: 20px;
  cursor: pointer;
  color: #64748b;
  transition: all 0.2s;
  padding: 8px;
  border-radius: 8px;
}
.collapse-btn:hover {
  color: var(--primary);
  background: rgba(99, 102, 241, 0.08);
}
.page-title {
  font-size: 16px;
  font-weight: 600;
  color: #1e293b;
}

.header-right { display: flex; align-items: center; gap: 16px; }
.header-icon {
  font-size: 18px;
  cursor: pointer;
  color: #64748b;
  transition: all 0.2s;
  padding: 8px;
  border-radius: 8px;
}
.header-icon:hover {
  color: var(--primary);
  background: rgba(99, 102, 241, 0.08);
}

.user-info {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  padding: 6px 12px 6px 6px;
  border-radius: 24px;
  transition: all 0.2s;
}
.user-info:hover { background: rgba(99, 102, 241, 0.08); }

.avatar {
  background: linear-gradient(135deg, #6366f1, #a855f7);
  color: #fff;
  font-weight: 600;
}

.user-detail { line-height: 1.3; }
.username { font-size: 13px; font-weight: 600; color: #1e293b; }
.user-role { font-size: 11px; color: #94a3b8; }

/* ========== 主内容区 ========== */
.main-content {
  background: #f8fafc;
  padding: 24px;
  overflow-y: auto;
}

/* ========== 过渡动画 ========== */
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

.page-enter-active, .page-leave-active {
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}
.page-enter-from { opacity: 0; transform: translateY(12px); }
.page-leave-to { opacity: 0; transform: translateY(-12px); }
</style>