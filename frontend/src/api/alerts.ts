import request from './request'
export const getAlerts = (limit = 100) => request.get('/alerts', { params: { limit } })
export const resolveAlert = (alter_id: number) => request.post('/alerts/resolve', { alter_id })
export const getAuditLogs = (limit = 100) => request.get('/audit', { params: { limit } })