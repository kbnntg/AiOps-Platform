import request from './request'

export const getTopology = (namespace?: string) =>
  request.get('/topology', { params: namespace ? { namespace } : {} })