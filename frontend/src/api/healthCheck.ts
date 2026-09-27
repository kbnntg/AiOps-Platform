import request from './request'

export const runHealthCheck = (namespace?: string) =>
  request.get('/health-check', { params: namespace ? { namespace } : {} })