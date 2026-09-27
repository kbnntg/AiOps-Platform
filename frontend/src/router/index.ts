import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', name: 'Login', component: () => import('@/views/Login.vue') },
    // 全屏大屏：脱离工作台布局，独立占满整个视口
    {
      path: '/screen',
      name: 'Screen',
      component: () => import('@/views/Screen.vue'),
      meta: { title: '全屏大屏' },
    },
    {
      path: '/',
      component: () => import('@/layout/MainLayout.vue'),
      redirect: '/dashboard',
      children: [
        { path: 'dashboard', name: 'Dashboard', component: () => import('@/views/Dashboard.vue'), meta: { title: '资源总览', icon: 'Odometer' } },
        { path: 'topology', name: 'Topology', component: () => import('@/views/Topology.vue'), meta: { title: '服务拓扑', icon: 'Share' } },
        { path: 'copilot', name: 'Copilot', component: () => import('@/views/Copilot.vue'), meta: { title: 'AI Copilot', icon: 'ChatDotRound' } },
        { path: 'pods', name: 'PodManage', component: () => import('@/views/PodManage.vue'), meta: { title: 'Pod 管理', icon: 'Box' } },
        { path: 'deployments', name: 'DeploymentManage', component: () => import('@/views/DeploymentManage.vue'), meta: { title: '副本管理', icon: 'Operation' } },
        { path: 'alerts', name: 'AlertHistory', component: () => import('@/views/AlertHistory.vue'), meta: { title: '告警历史', icon: 'Bell' } },
        { path: 'health-check', name: 'HealthCheck', component: () => import('@/views/HealthCheck.vue'), meta: { title: '集群巡检', icon: 'FirstAidKit' } },
        { path: 'rag', name: 'RagManage', component: () => import('@/views/RagManage.vue'), meta: { title: '知识库', icon: 'Collection' } },
        { path: 'audit', name: 'AuditLog', component: () => import('@/views/AuditLog.vue'), meta: { title: '审计日志', icon: 'Document' } },
      ],
    },
  ],
})

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  if (to.name !== 'Login' && !token) next({ name: 'Login' })
  else if (to.name === 'Login' && token) next({ name: 'Dashboard' })
  else next()
})

export default router