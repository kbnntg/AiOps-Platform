<template>
  <div class="copilot-page">
    <!-- 左侧：工具列表 -->
    <div class="sidebar">
      <div class="sidebar-title">
        <el-icon><Tools /></el-icon>
        <span>可用工具</span>
      </div>
      <div class="tool-list">
        <div
          v-for="t in tools"
          :key="t.name"
          class="tool-item"
        >
          <div class="tool-name">{{ t.name }}</div>
          <div class="tool-desc">{{ truncate(t.description, 60) }}</div>
        </div>
      </div>
    </div>

    <!-- 右侧：对话区 -->
    <div class="chat-container">
      <!-- 消息列表 -->
      <div class="messages" ref="messagesRef">
        <!-- 欢迎语 -->
        <div v-if="messages.length === 0" class="welcome">
          <div class="welcome-icon">🤖</div>
          <h2>AI 运维助手</h2>
          <p>我可以帮你查询 K8s 集群的状态，比如：</p>
          <div class="suggestions">
            <div
              v-for="s in suggestions"
              :key="s"
              class="suggestion"
              @click="sendMessage(s)"
            >
              {{ s }}
            </div>
          </div>
        </div>

        <!-- 消息气泡 -->
        <div
          v-for="(msg, idx) in messages"
          :key="idx"
          class="message"
          :class="msg.role"
        >
          <div class="avatar">
            <span v-if="msg.role === 'user'">你</span>
            <span v-else>AI</span>
          </div>
          <div class="bubble">
            <!-- 工具调用展示 -->
            <div v-if="msg.toolCalls && msg.toolCalls.length > 0" class="tool-calls">
              <div
                v-for="(tc, i) in msg.toolCalls"
                :key="i"
                class="tool-call"
                :class="{ 'done': tc.status === 'done' }"
              >
                <el-icon v-if="tc.status === 'running'" class="spin"><Loading /></el-icon>
                <el-icon v-else><CircleCheck /></el-icon>
                <span class="tool-call-name">{{ tc.tool }}</span>
                <span class="tool-call-status">{{ tc.status === 'running' ? '调用中...' : '已完成' }}</span>
              </div>
            </div>

            <!-- 消息内容（Markdown 渲染） -->
            <div v-if="msg.content" class="content" v-html="renderMarkdown(msg.content)"></div>

            <!-- 流式加载动画 -->
            <div v-if="msg.loading && !msg.content" class="typing">
              <span></span><span></span><span></span>
            </div>
          </div>
        </div>
      </div>

      <!-- 输入框 -->
      <div class="input-area">
        <el-input
          v-model="input"
          type="textarea"
          :rows="2"
          placeholder="问我任何关于集群的问题...（Enter 发送，Shift+Enter 换行）"
          resize="none"
          @keydown.enter.exact.prevent="handleSend"
        />
        <el-button
          type="primary"
          :loading="loading"
          :disabled="!input.trim() || loading"
          @click="handleSend"
        >
          <el-icon v-if="!loading"><Promotion /></el-icon>
          <span v-if="!loading">发送</span>
          <span v-else>思考中</span>
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { streamChat, getCopilotTools } from '@/api/copilot'

interface Message {
  role: 'user' | 'assistant'
  content: string
  loading?: boolean
  toolCalls?: Array<{ tool: string; status: 'running' | 'done' }>
}

const messages = ref<Message[]>([])
const input = ref('')
const loading = ref(false)
const messagesRef = ref<HTMLDivElement>()
const tools = ref<any[]>([])

const suggestions = [
  '现在有哪些 Pod？',
  '最近有告警吗？',
  '集群有几个节点？',
  'nginx 这个 Deployment 有几个副本？',
]

// 加载工具列表
async function loadTools() {
  try {
    tools.value = await getCopilotTools()
  } catch (e) {
    console.error('加载工具列表失败', e)
  }
}

// 滚到底部
function scrollToBottom() {
  nextTick(() => {
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight
    }
  })
}

// 发送消息
async function handleSend() {
  const text = input.value.trim()
  if (!text || loading.value) return
  sendMessage(text)
}

async function sendMessage(text: string) {
  input.value = ''
  loading.value = true

  // 1. 添加用户消息
  messages.value.push({ role: 'user', content: text })

  // 2. 添加 AI 占位消息
  const aiMsg: Message = {
    role: 'assistant',
    content: '',
    loading: true,
    toolCalls: [],
  }
  messages.value.push(aiMsg)
  scrollToBottom()

  // 3. 准备历史（排除当前 AI 占位消息）
  const history = messages.value
    .slice(0, -1)   // 排除刚加的 AI 占位
    .filter((m) => m.content)   // 过滤掉空消息
    .map((m) => ({ role: m.role, content: m.content }))

  try {
    // 4. 消费 SSE 流
    for await (const event of streamChat(text, history)) {
      if (event.type === 'tool_start') {
        aiMsg.toolCalls!.push({ tool: event.tool, status: 'running' })
        scrollToBottom()
      } else if (event.type === 'tool_result') {
        // 把最后一个 running 改成 done
        const last = aiMsg.toolCalls!.findLast((t) => t.status === 'running')
        if (last) last.status = 'done'
        scrollToBottom()
      } else if (event.type === 'text') {
        aiMsg.content += event.content
        scrollToBottom()
      } else if (event.type === 'error') {
        aiMsg.content = `❌ ${event.content}`
      } else if (event.type === 'done') {
        aiMsg.loading = false
      }
    }
  } catch (e: any) {
    aiMsg.content = `❌ 请求失败: ${e.message}`
    ElMessage.error('对话失败')
  } finally {
    aiMsg.loading = false
    loading.value = false
    scrollToBottom()
  }
}

function truncate(s: string, n: number): string {
  return s.length > n ? s.slice(0, n) + '...' : s
}

// Markdown 渲染（简化版）
function renderMarkdown(text: string): string {
  if (!text) return ''
  return text
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/^### (.*$)/gm, '<h3>$1</h3>')
    .replace(/^## (.*$)/gm, '<h2>$1</h2>')
    .replace(/^# (.*$)/gm, '<h1>$1</h1>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/`(.*?)`/g, '<code>$1</code>')
    .replace(/^- (.*$)/gm, '<li>$1</li>')
    .replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>')
    .replace(/\n\n/g, '</p><p>')
    .replace(/\n/g, '<br/>')
}

onMounted(loadTools)
</script>

<style scoped>
.copilot-page {
  display: flex;
  height: calc(100vh - 112px);
  gap: 16px;
}

/* ========== 左侧工具列表 ========== */
.sidebar {
  width: 260px;
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06);
  overflow-y: auto;
  flex-shrink: 0;
}

.sidebar-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #f1f5f9;
}

.tool-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.tool-item {
  padding: 10px 12px;
  background: #f8fafc;
  border-radius: 8px;
  transition: all 0.2s;
  cursor: default;
}
.tool-item:hover {
  background: #eef2ff;
  transform: translateX(2px);
}

.tool-name {
  font-size: 13px;
  font-weight: 600;
  color: #6366f1;
  margin-bottom: 4px;
  font-family: Consolas, monospace;
}

.tool-desc {
  font-size: 11px;
  color: #64748b;
  line-height: 1.5;
}

/* ========== 右侧对话区 ========== */
.chat-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06);
  overflow: hidden;
}

.messages {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  background: #fafbfc;
}

/* 欢迎语 */
.welcome {
  text-align: center;
  padding: 60px 20px;
}
.welcome-icon {
  font-size: 64px;
  margin-bottom: 16px;
}
.welcome h2 {
  color: #1e293b;
  margin: 0 0 8px;
}
.welcome p {
  color: #64748b;
  margin: 0 0 24px;
}
.suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: center;
  max-width: 600px;
  margin: 0 auto;
}
.suggestion {
  padding: 8px 16px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 20px;
  cursor: pointer;
  font-size: 13px;
  color: #475569;
  transition: all 0.2s;
}
.suggestion:hover {
  border-color: #6366f1;
  color: #6366f1;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.15);
}

/* 消息气泡 */
.message {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  animation: fadeIn 0.3s ease;
}
.message.user {
  flex-direction: row-reverse;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
  flex-shrink: 0;
}
.message.user .avatar {
  background: linear-gradient(135deg, #6366f1, #818cf8);
  color: #fff;
}
.message.assistant .avatar {
  background: linear-gradient(135deg, #10b981, #34d399);
  color: #fff;
}

.bubble {
  max-width: 75%;
  padding: 12px 16px;
  border-radius: 12px;
  background: #fff;
  border: 1px solid #f1f5f9;
  line-height: 1.7;
  font-size: 14px;
  color: #1e293b;
  word-break: break-word;
}
.message.user .bubble {
  background: linear-gradient(135deg, #6366f1, #818cf8);
  color: #fff;
  border: none;
}

/* 工具调用 */
.tool-calls {
  margin-bottom: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.tool-call {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background: #f1f5f9;
  border-radius: 6px;
  font-size: 12px;
  color: #64748b;
}
.tool-call.done {
  background: #f0fdf4;
  color: #10b981;
}
.tool-call-name {
  font-family: Consolas, monospace;
  font-weight: 600;
}
.tool-call-status {
  margin-left: auto;
  opacity: 0.7;
}
.spin {
  animation: spin 1s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Markdown 内容 */
.content :deep(h1),
.content :deep(h2),
.content :deep(h3) {
  color: #4f46e5;
  margin: 16px 0 8px;
  border-left: 4px solid #6366f1;
  padding-left: 10px;
}
.content :deep(code) {
  background: rgba(99, 102, 241, 0.1);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: Consolas, monospace;
  font-size: 13px;
}
.content :deep(table) {
  border-collapse: collapse;
  margin: 12px 0;
  font-size: 13px;
}
.content :deep(th),
.content :deep(td) {
  border: 1px solid #e2e8f0;
  padding: 6px 12px;
}
.content :deep(th) {
  background: #f8fafc;
  font-weight: 600;
}

/* 加载动画 */
.typing {
  display: flex;
  gap: 4px;
  padding: 4px 0;
}
.typing span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #6366f1;
  animation: bounce 1.4s infinite;
}
.typing span:nth-child(2) { animation-delay: 0.2s; }
.typing span:nth-child(3) { animation-delay: 0.4s; }

@keyframes bounce {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
  30% { transform: translateY(-6px); opacity: 1; }
}

/* 输入区 */
.input-area {
  padding: 16px 20px;
  border-top: 1px solid #f1f5f9;
  display: flex;
  gap: 12px;
  align-items: flex-end;
}
.input-area :deep(.el-textarea__inner) {
  border-radius: 8px;
  font-family: inherit;
  font-size: 14px;
}
</style>
