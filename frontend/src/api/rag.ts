import request from './request'

// 查看知识库状态
export const getRagStatus = () => request.get('/rag/status')

// 触发索引（把数据库的历史告警同步到知识库）
export const triggerIndex = () => request.post('/rag/index')

// 手动检索（调试用）
export const searchRag = (query: string, topK = 5, resource?: string) =>
  request.post('/rag/search', null, {
    params: { query, top_k: topK, ...(resource ? { resource } : {}) },
  })

// 清空知识库
export const clearRag = () => request.post('/rag/clear')