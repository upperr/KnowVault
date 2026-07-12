import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
api.interceptors.request.use(
  config => config,
  error => Promise.reject(error)
)

// 响应拦截器
api.interceptors.response.use(
  response => response.data,
  error => {
    console.error('API 错误:', error)
    return Promise.reject(error)
  }
)

// 获取系统状态
export const getStatus = () => api.get('/status')

// 同步文档
export const syncDocuments = (docDir = '') => api.post('/sync', { doc_dir: docDir })

// 智能问答
export const askQuestion = (question, useHistory = true) => 
  api.post('/ask', { question, use_history: useHistory })

// 文档创作
export const createDocument = (data) => api.post('/create', data)

// 获取知识库统计
export const getKnowledgeStats = () => api.get('/status')

// 清空知识库
export const clearKnowledge = () => api.post('/clear')

// 删除文件
export const removeFile = (filePath) => api.post('/remove', { file_path: filePath })

export default api
