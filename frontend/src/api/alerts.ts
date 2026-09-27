import request from './request'

/**
 * 查询告警历史
 * @param limit  条数上限（后端限制 1~500）
 * @param status 可选：'OPEN' | 'RESOLVED'（后端早已支持，此前前端未使用）
 * @param silent 静默请求，失败不弹全局提示（用于轮询 / 自动刷新）
 */
export const getAlerts = (limit = 100, status?: string, silent = false) =>
  request.get('/alerts', {
    params: status ? { limit, status } : { limit },
    silent,
  })

export const resolveAlert = (alertId: number) =>
  request.post('/alerts/resolve', { alert_id: alertId })

export const markFalsePositive = (alertId: number) =>
  request.post(`/alerts/${alertId}/false-positive`)

export const getAuditLogs = (limit = 100, silent = false) =>
  request.get('/audit', { params: { limit }, silent })

export const getAlertMetrics = (silent = false) =>
  request.get('/alerts/metrics', { silent })
