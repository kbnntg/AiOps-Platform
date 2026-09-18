import request from './request'

export const getPods = (namespace: string) =>
  request.get('/pods', { params: { namespace } })

export const getPodLogs = (namespace: string, name: string, tail = 500) =>
  request.get(`/pods/${name}/logs`, { params: { namespace, tail_lines: tail } })

export const getPodEvents = (namespace: string, name: string) =>
  request.get(`/pods/${name}/event`, { params: { namespace } })

export const deletePod = (namespace: string, name: string) =>
  request.delete(`/pods/${name}`, { params: { namespace } })

export const analyzePodLogs = (namespace: string, name: string, tailLines = 500) =>
  request.post(`/pods/${name}/analyze`, null, {
    params: { namespace, tail_lines: tailLines },
  })

export const diagnosePod = (namespace: string, name: string) =>
  request.post(`/pods/${name}/diagnose`, null, {
    params: { namespace },
  })
