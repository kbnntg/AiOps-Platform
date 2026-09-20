import request from './request'

export const getAlerts = (limit = 100) =>
  request.get('/alerts', { params: { limit } })

export const resolveAlert = (alertId: number) =>
  request.post('/alerts/resolve', { alert_id: alertId })

export const markFalsePositive = (alertId: number) =>
  request.post(`/alerts/${alertId}/false-positive`)

export const getAuditLogs = (limit = 100) =>
  request.get('/audit', { params: { limit } })

export const getAlertMetrics = () =>
  request.get('/alerts/metrics')