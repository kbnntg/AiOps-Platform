import request from './request'
export const getNamespaces = () => request.get('/metrics/namespaces')
export const getNodes = () => request.get('/metrics/nodes')
export const getCpu = (hour = 1) => request.get('/metrics/cpu', { params: { hour } })
export const getMemory = (hour = 1) => request.get('/metrics/memory', { params: { hour } })
export const getDisk = (hour = 1) => request.get('/metrics/disk', { params: { hour } })