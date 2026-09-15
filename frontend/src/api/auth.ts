import request from './request'
export const login = (data: any) => request.post('/auth/login', data)
export const getMe = () => request.get('/auth/me')