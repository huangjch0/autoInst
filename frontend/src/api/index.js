import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 60000
})

api.interceptors.response.use(
  response => response.data,
  error => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

export const assetApi = {
  getAll: () => api.get('/assets/'),
  getOne: (id) => api.get(`/assets/${id}`),
  create: (data) => api.post('/assets/', data),
  update: (id, data) => api.put(`/assets/${id}`, data),
  delete: (id) => api.delete(`/assets/${id}`)
}

export const transactionApi = {
  getAll: (params) => api.get('/transactions/', { params }),
  create: (data) => api.post('/transactions/', data),
  update: (id, data) => api.put(`/transactions/${id}`, data),
  delete: (id) => api.delete(`/transactions/${id}`),
  getHoldings: () => api.get('/transactions/holdings/summary')
}

export const marketApi = {
  getQuote: (symbol) => api.get(`/market/quote/${symbol}`),
  getHistory: (symbol, params) => api.get(`/market/history/${symbol}`, { params }),
  fetchData: (symbol, params) => api.post(`/market/fetch/${symbol}`, null, { params }),
  fetchAll: () => api.post('/market/fetch-all'),
  search: (keyword) => api.get('/market/search', { params: { keyword } }),
  predict: (symbol, strategy = 'ensemble') => api.get(`/market/predict/${symbol}`, { params: { strategy } }),
  getPredictionStrategies: () => api.get('/market/predict-strategies'),
  getHistoryWithIndicators: (symbol, params) => api.get(`/market/history-with-indicators/${symbol}`, { params })
}

export const strategyApi = {
  getAll: (params) => api.get('/strategies/', { params }),
  getOne: (id) => api.get(`/strategies/${id}`),
  create: (data) => api.post('/strategies/', data),
  update: (id, data) => api.put(`/strategies/${id}`, data),
  delete: (id) => api.delete(`/strategies/${id}`),
  run: (id) => api.post(`/strategies/${id}/run`),
  getSignals: (params) => api.get('/strategies/list/signals', { params }),
  approveSignal: (id, data) => api.post(`/strategies/signals/${id}/approve`, data)
}

export const portfolioApi = {
  getSummary: () => api.get('/portfolio/summary'),
  getDistribution: () => api.get('/portfolio/chart/distribution'),
  getAll: () => api.get('/portfolio/'),
  create: (data) => api.post('/portfolio/', data)
}

export const accountApi = {
  getAll: () => api.get('/accounts/'),
  getOne: (id) => api.get(`/accounts/${id}`),
  create: (data) => api.post('/accounts/', data),
  update: (id, data) => api.put(`/accounts/${id}`, data),
  delete: (id) => api.delete(`/accounts/${id}`),
  getSummary: (id) => api.get(`/accounts/${id}/summary`),
  getTransactions: (id, params) => api.get(`/accounts/${id}/transactions`, { params }),
  getSnapshots: (id, params) => api.get(`/accounts/${id}/snapshots`, { params }),
  createSnapshot: (id) => api.post(`/accounts/${id}/snapshot-daily`)
}

export const backtestApi = {
  run: (data) => api.post('/backtest/run', data)
}

export const schedulerApi = {
  getStatus: () => api.get('/scheduler/status'),
  start: () => api.post('/scheduler/start'),
  stop: () => api.post('/scheduler/stop'),
  runNow: () => api.post('/scheduler/run-now'),
  config: (dailyTime, intervalMinutes, datasource) => api.post('/scheduler/config', null, { 
    params: { daily_time: dailyTime, interval_minutes: intervalMinutes, datasource } 
  })
}

export default api
