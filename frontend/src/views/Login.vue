<template>
  <div class="login-container">
    <canvas ref="canvasRef" class="particle-canvas"></canvas>
    <div class="mouse-glow" :style="{ left: mouseX + 'px', top: mouseY + 'px' }"></div>

    <div class="login-card">
      <div class="logo-area">
        <div class="logo-icon">AI</div>
        <h1>AIOps 智能运维平台</h1>
        <p class="subtitle">Kubernetes 集群监控与管理</p>
      </div>

      <el-form :model="form" @submit.prevent="handleLogin" class="login-form">
        <el-form-item>
          <el-input v-model="form.username" placeholder="用户名" size="large" clearable>
            <template #prefix><el-icon><User /></el-icon></template>
          </el-input>
        </el-form-item>
        <el-form-item>
          <el-input v-model="form.password" type="password" placeholder="密码" size="large"
                    show-password @keyup.enter="handleLogin">
            <template #prefix><el-icon><Lock /></el-icon></template>
          </el-input>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" size="large" style="width:100%" :loading="loading"
                     @click="handleLogin">
            登 录
          </el-button>
        </el-form-item>
      </el-form>

      <div class="footer-text">© 2026 AIOps Platform · Powered by Kubernetes</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { login } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const loading = ref(false)
const form = ref({ username: '', password: '' })
const canvasRef = ref<HTMLCanvasElement>()
const mouseX = ref(0)
const mouseY = ref(0)

let animationId = 0
let particles: any[] = []
let ctx: CanvasRenderingContext2D | null = null

function initCanvas() {
  const canvas = canvasRef.value
  if (!canvas) return
  ctx = canvas.getContext('2d')
  canvas.width = window.innerWidth
  canvas.height = window.innerHeight

  particles = []
  const count = Math.floor((canvas.width * canvas.height) / 12000)
  for (let i = 0; i < count; i++) {
    particles.push({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      vx: (Math.random() - 0.5) * 0.5,
      vy: (Math.random() - 0.5) * 0.5,
      r: Math.random() * 2 + 1,
    })
  }
  animate()
}

function animate() {
  if (!ctx || !canvasRef.value) return
  const { width, height } = canvasRef.value
  ctx.clearRect(0, 0, width, height)

  // 绘制连线
  for (let i = 0; i < particles.length; i++) {
    for (let j = i + 1; j < particles.length; j++) {
      const dx = particles[i].x - particles[j].x
      const dy = particles[i].y - particles[j].y
      const dist = Math.sqrt(dx * dx + dy * dy)
      if (dist < 150) {
        ctx.strokeStyle = `rgba(255, 255, 255, ${0.15 * (1 - dist / 150)})`
        ctx.lineWidth = 0.5
        ctx.beginPath()
        ctx.moveTo(particles[i].x, particles[i].y)
        ctx.lineTo(particles[j].x, particles[j].y)
        ctx.stroke()
      }
    }
  }

  // 绘制粒子
  particles.forEach(p => {
    p.x += p.vx
    p.y += p.vy
    if (p.x < 0 || p.x > width) p.vx *= -1
    if (p.y < 0 || p.y > height) p.vy *= -1

    ctx!.beginPath()
    ctx!.arc(p.x, p.y, p.r, 0, Math.PI * 2)
    ctx!.fillStyle = 'rgba(255, 255, 255, 0.6)'
    ctx!.fill()
  })

  animationId = requestAnimationFrame(animate)
}

function onMouseMove(e: MouseEvent) {
  mouseX.value = e.clientX
  mouseY.value = e.clientY
}

function onResize() { initCanvas() }

onMounted(() => {
  initCanvas()
  window.addEventListener('mousemove', onMouseMove)
  window.addEventListener('resize', onResize)
})

onUnmounted(() => {
  cancelAnimationFrame(animationId)
  window.removeEventListener('mousemove', onMouseMove)
  window.removeEventListener('resize', onResize)
})

async function handleLogin() {
  if (!form.value.username || !form.value.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  loading.value = true
  try {
    const data: any = await login(form.value)
    authStore.setAuth(data.token, data.username, data.role)
    ElMessage.success('登录成功')
    router.push('/dashboard')
  } catch (e) {} finally { loading.value = false }
}
</script>

<style scoped>
.login-container {
  position: relative;
  height: 100vh;
  overflow: hidden;
  background: linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #4c1d95 100%);
  display: flex;
  align-items: center;
  justify-content: center;
}

.particle-canvas {
  position: absolute;
  inset: 0;
  z-index: 1;
}

.mouse-glow {
  position: fixed;
  width: 400px;
  height: 400px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(139, 92, 246, 0.25) 0%, transparent 70%);
  transform: translate(-50%, -50%);
  pointer-events: none;
  z-index: 2;
  transition: left 0.15s ease-out, top 0.15s ease-out;
}

.login-card {
  position: relative;
  z-index: 3;
  width: 420px;
  padding: 48px 40px;
  background: rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-radius: 20px;
  border: 1px solid rgba(255, 255, 255, 0.15);
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  animation: cardIn 0.6s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes cardIn {
  from { opacity: 0; transform: translateY(30px) scale(0.96); }
  to   { opacity: 1; transform: translateY(0) scale(1); }
}

.logo-area { text-align: center; margin-bottom: 32px; }

.logo-icon {
  width: 64px;
  height: 64px;
  margin: 0 auto 16px;
  background: linear-gradient(135deg, #6366f1, #a855f7);
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 24px;
  font-weight: bold;
  box-shadow: 0 8px 24px rgba(99, 102, 241, 0.4);
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { box-shadow: 0 8px 24px rgba(99, 102, 241, 0.4); }
  50%      { box-shadow: 0 8px 36px rgba(168, 85, 247, 0.6); }
}

.logo-area h1 {
  margin: 0 0 8px;
  font-size: 22px;
  color: #fff;
  font-weight: 600;
  letter-spacing: 1px;
}
.subtitle {
  margin: 0;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.5);
  letter-spacing: 0.5px;
}

.login-form :deep(.el-input__wrapper) {
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 10px;
  box-shadow: none;
}
.login-form :deep(.el-input__wrapper:hover) {
  border-color: rgba(139, 92, 246, 0.5);
}
.login-form :deep(.el-input__wrapper.is-focus) {
  border-color: #8b5cf6;
  box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.15);
}
.login-form :deep(.el-input__inner) {
  color: #fff;
}
.login-form :deep(.el-input__inner::placeholder) {
  color: rgba(255, 255, 255, 0.4);
}
.login-form :deep(.el-input__prefix) {
  color: rgba(255, 255, 255, 0.6);
}
.login-form :deep(.el-button--primary) {
  height: 46px;
  font-size: 15px;
  letter-spacing: 4px;
  border-radius: 10px;
  background: linear-gradient(135deg, #6366f1, #a855f7) !important;
}

.footer-text {
  margin-top: 24px;
  text-align: center;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.35);
}
</style>