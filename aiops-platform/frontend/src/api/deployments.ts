import request from './request'
export const getDeployments = (namespace: string) => request.get('/deployments', { params: { namespace } })
export const scaleDeployment = (namespace: string, deployment: string, replicas: number) =>
  request.post('/deployments/scale', { namespace, deployment, replicas })