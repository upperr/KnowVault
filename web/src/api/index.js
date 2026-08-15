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

// ==================== 系统状态 ====================

// 获取系统状态 - 使用 RAGFlow 标准 API
export const getStatus = async () => {
  // 获取所有知识库来计算统计信息
  const datasetsResponse = await api.get('/v1/datasets')
  const datasets = datasetsResponse.data?.data || []
  
  let totalFiles = 0
  let totalChunks = 0
  const fileList = []
  
  // 遍历所有知识库获取文档统计
  for (const dataset of datasets) {
    const docsResponse = await api.get(`/v1/datasets/${dataset.id}/documents`, {
      params: { page: 1, page_size: 100 }
    })
    const docs = docsResponse.data?.data?.docs || []
    totalFiles += docs.length
    docs.forEach(doc => {
      totalChunks += doc.chunk_num || 0
      fileList.push({
        name: doc.name,
        id: doc.id,
        chunk_num: doc.chunk_num,
        status: doc.status
      })
    })
  }
  
  return {
    data: {
      knowledge_base: {
        total_files: totalFiles,
        total_chunks: totalChunks,
        file_list: fileList
      }
    }
  }
}

// ==================== 文档管理 ====================

// 同步文档 - 保留自定义实现（RAGFlow 无文件夹同步功能）
export const syncDocuments = async (docDir = '') => {
  console.log('[API] 开始同步文档，目录:', docDir)
  try {
    const response = await api.post('/v1/files/sync', { doc_dir: docDir })
    console.log('[API] 同步响应:', response)
    console.log('[API] 同步响应.data:', response.data)
    return response.data
  } catch (error) {
    console.error('[API] 同步请求失败:', error)
    throw error
  }
}

// 上传 ZIP 文件 - 已使用 RAGFlow API
export const uploadZipFile = async (datasetId, file) => {
  const formData = new FormData()
  formData.append('file', file)
  return api.post(`/v1/datasets/${datasetId}/documents/upload_zip`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

// 获取知识库统计 - 使用 RAGFlow 标准 API
export const getKnowledgeStats = async (datasetId) => {
  const response = await api.get(`/v1/datasets/${datasetId}/documents`, {
    params: { page: 1, page_size: 100 }
  })
  const docs = response.data?.data?.docs || []
  return {
    data: {
      knowledge_base: {
        total_files: docs.length,
        total_chunks: docs.reduce((sum, doc) => sum + (doc.chunk_num || 0), 0),
        file_list: docs.map(doc => ({
          name: doc.name,
          id: doc.id,
          chunk_num: doc.chunk_num,
          status: doc.status
        }))
      }
    }
  }
}

// 获取知识库列表 - 已使用 RAGFlow API
export const getDatasets = async () => {
  const response = await api.get('/v1/datasets')
  return response
}

// 获取知识库文档列表 - 已使用 RAGFlow API
export const getDatasetDocuments = (datasetId) => 
  api.get(`/v1/datasets/${datasetId}/documents`, {
    params: { page: 1, page_size: 100 }
  })

// 清空知识库（删除所有文档） - 已使用 RAGFlow API
export const clearKnowledge = (datasetId) => 
  api.delete(`/v1/datasets/${datasetId}/documents`, {
    data: { delete_all: true }
  })

// 删除单个文件 - 已使用 RAGFlow API
export const removeFile = (datasetId, documentId) => 
  api.delete(`/v1/datasets/${datasetId}/documents`, {
    data: { ids: [documentId] }
  })

// 上传单个文件 - 使用 RAGFlow 标准 API
export const uploadFile = async (datasetId, file) => {
  const formData = new FormData()
  formData.append('file', file)
  return api.post(`/v1/datasets/${datasetId}/documents`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

// 导出 DOCX - 保留自定义实现（RAGFlow 无导出功能）
export const exportDocx = (content, title, filename) => 
  api.post('/files/export/docx', { content, title, filename }, {
    responseType: 'blob'
  })

// ==================== 智能问答 ====================

// 流式问答 - 使用 RAGFlow 标准 API /api/v1/chat/completions
export const askQuestionStream = async (question, useHistory = true, chatId = null, llmId = null, datasetIds = null) => {
  const requestBody = {
    messages: [
      { role: 'user', content: question }
    ],
    stream: true
  }
  
  // 如果指定了 llm_id，添加到请求体
  if (llmId) {
    requestBody.llm_id = llmId
  }
  
  // 如果指定了 dataset_ids（知识库 ID 列表），添加到请求体
  if (datasetIds && Array.isArray(datasetIds) && datasetIds.length > 0) {
    requestBody.dataset_ids = datasetIds
  }
  
  const url = chatId 
    ? `/api/v1/chats/${chatId}/completions`
    : '/api/v1/chat/completions'
  
  const response = await fetch(url, {
    method: 'POST',
    headers: { 
      'Content-Type': 'application/json',
    },
    credentials: 'include',  // 发送 cookie 用于认证
    body: JSON.stringify(requestBody)
  })
  
  return response
}

// ==================== 文档创作 ====================

// 使用 RAGFlow 标准 API /api/v1/document_creation/stream
export const createDocument = (data) => api.post('/v1/document_creation', data)

export const createDocumentStream = (requirement, title = null, originalText = null, datasetIds = null) => {
  const body = { requirement }
  if (title) body.title = title
  if (originalText) body.original_text = originalText
  if (datasetIds) body.dataset_ids = datasetIds
  
  return fetch('/api/v1/document_creation/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(body)
  })
}

// ==================== 文档优化 ====================

// 使用 RAGFlow 标准 API /api/v1/document_optimization/stream
export const optimizeDocumentStream = (content, instruction) => {
  return fetch('/api/v1/document_optimization/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ content, instruction })
  })
}

// ==================== 记忆管理 ====================

// 后端记忆类型定义
// RAW(原始对话), SEMANTIC(语义知识), EPISODIC(事件知识), PROCEDURAL(程序知识)
// 短期记忆 = RAW 类型，长期记忆 = SEMANTIC/EPISODIC/PROCEDURAL 类型

// 创建记忆 - 使用 RAGFlow 标准 API /api/v1/memories
export const createMemory = async (memoryInfo) => {
  const response = await api.post('/v1/memories', memoryInfo)
  return response.data
}

// 获取记忆统计 - 使用 RAGFlow 标准 API /api/v1/memories
export const getMemoryStats = async () => {
  const response = await api.get('/v1/memories')
  // 响应拦截器已返回 response.data，所以 response 直接是 {message: true, data: {...}}
  // response.data = { memory_list: [...], total_count: N }
  const memoryList = response.data?.memory_list || []
  
  console.log('[Memory API] 获取到的记忆列表:', memoryList)
  
  // 为每个记忆获取消息数量
  const memoriesWithCount = await Promise.all(
    memoryList.map(async (m) => {
      try {
        // 调用 /memories/{id} 获取消息列表
        const msgResponse = await api.get(`/v1/memories/${m.id}`, {
          params: { page: 1, page_size: 1 }
        })
        const messageCount = msgResponse.data?.messages?.total_count || 0
        console.log(`[Memory API] 记忆 ${m.id} 的消息数量:`, messageCount)
        return {
          id: m.id,
          name: m.name,
          type: m.memory_type,  // 数组，如 ["raw", "semantic"]
          message_count: messageCount
        }
      } catch (error) {
        console.error(`[Memory API] 获取记忆 ${m.id} 的消息数量失败:`, error)
        return {
          id: m.id,
          name: m.name,
          type: m.memory_type,
          message_count: 0
        }
      }
    })
  )
  
  console.log('[Memory API] 最终返回的记忆数据:', memoriesWithCount)
  
  return {
    data: {
      total_memories: memoriesWithCount.length,
      memories: memoriesWithCount
    }
  }
}

// 清空记忆 - 使用 RAGFlow 标准 API /api/v1/memories/{id}
export const clearMemory = async (type) => {
  // 先获取所有记忆
  const response = await api.get('/v1/memories')
  const memoryList = response.data?.memory_list || []
  
  // 根据类型删除记忆
  // 短期记忆：包含 raw 类型
  // 长期记忆：包含 semantic/episodic/procedural 类型
  const deletePromises = memoryList
    .filter(m => {
      if (type === 'all') return true
      if (type === 'short') return m.memory_type?.includes('raw')
      if (type === 'long') return m.memory_type?.some(t => ['semantic', 'episodic', 'procedural'].includes(t))
      return false
    })
    .map(m => api.delete(`/v1/memories/${m.id}`))
  
  await Promise.all(deletePromises)
  return { data: { success: true } }
}

// 刷新记忆偏好 - 使用 RAGFlow 标准 API /api/v1/memories/{id}
export const refreshMemoryPrefs = async (memoryId) => {
  if (!memoryId) {
    // 如果没有指定 memoryId，获取第一个记忆
    const response = await api.get('/v1/memories')
    const memoryList = response.data?.memory_list || []
    if (memoryList.length === 0) {
      throw new Error('没有找到记忆')
    }
    memoryId = memoryList[0].id
  }
  
  // 更新记忆配置（刷新）
  return api.put(`/v1/memories/${memoryId}`, {
    // 可以添加需要更新的配置参数
  })
}

// ==================== 模型管理 ====================

// 获取可用模型列表
export const getModels = () => api.get('/v1/models')

// 获取默认模型
export const getDefaultModel = async () => {
  try {
    const response = await api.get('/v1/models/default')
    return response.data?.data || null
  } catch (error) {
    console.error('获取默认模型失败:', error)
    return null
  }
}

// 获取提供商列表
export const getProviders = (available = false) => api.get('/v1/providers', {
  params: { available: available.toString() }
})

// 添加模型提供商
export const addModelProvider = (providerName, apiKey, baseUrl = null) => {
  // RAGFlow 需要两步：
  // 1. 先添加 provider
  // 2. 再添加 instance（带 API Key 和 Base URL）
  
  const data = {
    provider_name: providerName
  }
  
  return api.put('/v1/providers', data)
}

// 添加模型实例（带 API Key）
export const addModelInstance = (providerName, apiKey, baseUrl = null) => {
  const data = {}
  
  if (apiKey) {
    data.api_key = apiKey
  }
  
  if (baseUrl) {
    data.base_url = baseUrl
  }
  
  return api.post(`/v1/providers/${providerName}/instances`, data)
}

// 设置默认模型
export const setDefaultModel = (modelId) => {
  return api.patch('/v1/models/default', { model_id: modelId })
}

export default api
