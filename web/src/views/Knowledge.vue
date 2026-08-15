<template>
  <div class="knowledge-container">
    <el-row :gutter="20">
      <!-- 左侧：上传操作 -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <el-icon><FolderOpened /></el-icon>
              <span>文档上传</span>
            </div>
          </template>
          
          <div class="sync-section">
            <el-form label-position="top">
              <el-form-item label="选择压缩包文件">
                <el-upload
                  ref="uploadRef"
                  drag
                  :auto-upload="false"
                  :on-change="handleFileChange"
                  :on-remove="handleFileRemove"
                  :limit="1"
                  accept=".zip"
                  :disabled="uploading"
                  class="upload-area"
                >
                  <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
                  <div class="el-upload__text">
                    拖拽文件到此处或 <em>点击选择</em>
                  </div>
                  <template #tip>
                    <div class="el-upload__tip">
                      仅支持 zip 格式，最大 500MB
                    </div>
                  </template>
                </el-upload>
              </el-form-item>
              
              <el-form-item>
                <el-button
                  type="primary"
                  :loading="uploading"
                  :disabled="!selectedFile"
                  @click="handleUpload"
                  style="width: 100%"
                >
                  <el-icon><Upload /></el-icon>
                  {{ uploading ? '上传中...' : '开始上传' }}
                </el-button>
              </el-form-item>
            </el-form>
            
            <el-alert
              title="温馨提示"
              type="info"
              :closable="false"
              show-icon
            >
              <p>1. 将 PDF、Word、TXT 文档打包成 zip 压缩包</p>
              <p>2. 点击"开始上传"按钮构建知识库</p>
              <p>3. 系统会自动解压并解析文档，创建向量索引</p>
              <p>4. 支持重复上传，已存在文档会自动更新</p>
            </el-alert>
            
            <!-- 上传结果 -->
            <div v-if="uploadResult" class="sync-result">
              <el-descriptions :column="2" border>
                <el-descriptions-item label="新增文件">
                  <el-tag type="success">+{{ uploadResult.added }}</el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="更新文件">
                  <el-tag type="warning">~{{ uploadResult.updated }}</el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="失败文件">
                  <el-tag type="danger">{{ uploadResult.failed || 0 }}</el-tag>
                </el-descriptions-item>
              </el-descriptions>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <!-- 右侧：知识库统计 -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <el-icon><DataAnalysis /></el-icon>
              <span>知识库统计</span>
              <el-button
                type="danger"
                size="small"
                style="margin-left: auto"
                @click="handleClear"
              >
                <el-icon><Delete /></el-icon>
                清空知识库
              </el-button>
            </div>
          </template>
          
          <div class="stats-section">
            <div class="stat-item">
              <div class="stat-label">收录文件数</div>
              <div class="stat-value">{{ stats.total_files || 0 }}</div>
            </div>
            <div class="stat-item">
              <div class="stat-label">向量化文本块</div>
              <div class="stat-value">{{ stats.total_chunks || 0 }}</div>
            </div>
          </div>
          
          <el-divider />
          
          <div class="file-list-section">
            <div class="list-header">
              <h3>已收录文件</h3>
              <el-button size="small" @click="loadStats">
                <el-icon><Refresh /></el-icon>
                刷新
              </el-button>
            </div>
            <el-table :data="fileList" style="width: 100%" max-height="400">
              <el-table-column prop="file_name" label="文件名" show-overflow-tooltip />
              <el-table-column prop="chunk_num" label="文本块数" width="100" align="right" />
              <el-table-column label="操作" width="80" fixed="right">
                <template #default="{ row }">
                  <el-button
                    type="danger"
                    size="small"
                    @click="handleRemoveFile(row.file_name)"
                  >
                    删除
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Folder, FolderOpened, DataAnalysis, Refresh, Delete, Upload, UploadFilled } from '@element-plus/icons-vue'
import { uploadZipFile, getDatasets, getDatasetDocuments, clearKnowledge, removeFile } from '@/api'

const uploading = ref(false)
const selectedFile = ref(null)
const uploadResult = ref(null)
const stats = reactive({ total_files: 0, total_chunks: 0 })
const fileList = ref([])
const uploadRef = ref(null)
const refreshTimer = ref(null)
const isPolling = ref(false)

// 文件选择处理
const handleFileChange = (file) => {
  selectedFile.value = file.raw
}

// 文件移除处理
const handleFileRemove = () => {
  selectedFile.value = null
}

// 上传处理
const handleUpload = async () => {
  if (!selectedFile.value) {
    ElMessage.warning('请先选择文件')
    return
  }
  
  uploading.value = true
  try {
    // 获取知识库 ID
    const datasetsResponse = await getDatasets()
    const datasetsData = datasetsResponse.data || datasetsResponse
    const datasets = datasetsData.data || datasetsData || []
    if (datasets.length === 0) {
      ElMessage.error('未找到知识库')
      uploading.value = false
      return
    }
    const datasetId = datasets[0].id
    
    const response = await uploadZipFile(datasetId, selectedFile.value)
    console.log('[上传] 原始响应:', response)
    
    // 处理两种可能的响应格式：
    // 格式 1 (拦截器已提取): {status: "ok", upload_result: {...}}
    // 格式 2 (完整响应): {code: 0, message: "success", data: {status: "ok", upload_result: {...}}}
    const result = response.data && response.code !== undefined ? response.data : response
    console.log('[上传] 处理后的 result:', result)
    
    // 检查后端返回的状态
    if (result.status === 'error') {
      throw new Error(result.message || '上传失败')
    }
    
    if (!result.upload_result) {
      throw new Error('上传响应格式异常：' + JSON.stringify(result))
    }
    
    uploadResult.value = result.upload_result
    
    // 构建详细的上传完成提示
    const { added, updated, failed } = result.upload_result
    let summary = '上传完成！'
    const details = []
    if (added > 0) details.push(`新增 ${added} 个文件`)
    if (updated > 0) details.push(`更新 ${updated} 个文件`)
    if (failed > 0) details.push(`失败 ${failed} 个文件`)
    if (details.length > 0) {
      summary += '\n' + details.join(' | ')
    }
    
    // 如果有警告，显示警告信息
    if (result.status === 'warning') {
      ElMessage.warning({
        message: summary + '\n' + (result.warning || ''),
        duration: 8000,
        showClose: true
      })
    } else {
      // 成功
      ElMessage.success({
        message: summary,
        duration: 5000,
        showClose: true
      })
    }
    
    // 清空文件选择
    uploadRef.value?.clearFiles()
    selectedFile.value = null
    
    // 开始轮询检查文档处理状态
    startPolling(datasetId)
  } catch (error) {
    console.error('上传错误:', error)
    const errorMsg = error.response?.data?.detail || error.response?.data?.message || error.message
    ElMessage.error('上传失败：' + errorMsg)
  } finally {
    uploading.value = false
  }
}

const loadStats = async () => {
  try {
    // 1. 获取知识库列表
    const datasetsResponse = await getDatasets()
    console.log('[统计] 知识库列表响应:', datasetsResponse)
    const datasetsData = datasetsResponse.data || datasetsResponse
    const datasets = datasetsData.data || datasetsData || []
    
    if (datasets.length === 0) {
      console.log('[统计] 暂无知识库')
      return
    }
    
    // 使用第一个知识库
    const dataset = datasets[0]
    const datasetId = dataset.id
    console.log('[统计] 使用知识库:', dataset.name, datasetId)
    
    // 2. 获取该知识库的文档列表（包含 chunk_count）
    const response = await getDatasetDocuments(datasetId)
    console.log('[统计] 文档列表原始响应:', response)
    const data = response.data || response
    console.log('[统计] 文档列表处理后的 data:', data)
    
    // 处理多种可能的响应格式
    const docs = data.data?.docs || data.docs || (Array.isArray(data) ? data : [])
    console.log('[统计] 解析后的 docs:', docs)
    
    if (Array.isArray(docs)) {
      // 只统计已完成的文档 (run === 'DONE' 或 run === 3)
      const isDone = (doc) => {
        const status = doc.run ?? doc.status ?? ''
        return status === 'DONE' || status === 3 || status === '3'
      }
      
      const completedDocs = docs.filter(isDone)
      
      // 计算统计信息（只统计已完成的文档）
      const totalFiles = completedDocs.length
      const totalChunks = completedDocs.reduce((sum, doc) => {
        const chunkCount = doc.chunk_count ?? doc.chunk_num ?? 0
        return sum + chunkCount
      }, 0)
      
      stats.total_files = totalFiles
      stats.total_chunks = totalChunks
      
      // 构建文件列表（只展示已完成的文档）
      fileList.value = completedDocs.map(doc => {
        // 尝试多种字段名获取 chunk 数量
        const chunkNum = doc.chunk_count ?? doc.chunk_num ?? 0
        // 尝试多种字段名获取文件名，并处理可能的编码问题
        let fileName = doc.name || doc.file_name || ''
        
        return {
          id: doc.id,
          file_name: fileName,
          chunk_num: chunkNum,
          token_count: doc.token_count ?? doc.token_num ?? 0,
          status: doc.run || 'DONE'
        }
      })
      
      console.log('[统计] 更新后 - 文件数:', totalFiles, '文本块数:', totalChunks, '文件列表:', fileList.value.length)
    }
  } catch (error) {
    console.error('加载统计失败:', error)
  }
}

// 轮询检查文档处理状态
const startPolling = (datasetId) => {
  // 清除之前的轮询
  stopPolling()
  isPolling.value = true
  
  const poll = async () => {
    if (!isPolling.value) return
    
    try {
      const response = await getDatasetDocuments(datasetId)
      const data = response.data || response
      const docs = data.data?.docs || data.docs || (Array.isArray(data) ? data : [])
      
      if (Array.isArray(docs)) {
        // 检查是否有文档仍在处理中
        const hasProcessing = docs.some(doc => {
          const status = doc.run ?? doc.status ?? ''
          return status === 'RUNNING' || status === 'UNSTART' || status === 0 || status === 1 || status === '0' || status === '1'
        })
        
        if (hasProcessing) {
          // 仍有文档在处理中，继续轮询
          console.log('[轮询] 仍有文档在处理中，3 秒后重试...')
          refreshTimer.value = setTimeout(poll, 3000)
        } else {
          // 所有文档处理完成
          console.log('[轮询] 所有文档处理完成')
          ElMessage.success('文档处理完成！')
          await loadStats()
          stopPolling()
        }
      }
    } catch (error) {
      console.error('[轮询] 检查状态失败:', error)
      stopPolling()
    }
  }
  
  // 首次立即检查
  poll()
}

const stopPolling = () => {
  if (refreshTimer.value) {
    clearTimeout(refreshTimer.value)
    refreshTimer.value = null
  }
  isPolling.value = false
}

const handleClear = async () => {
  try {
    // 获取知识库 ID
    const datasetsResponse = await getDatasets()
    const datasetsData = datasetsResponse.data || datasetsResponse
    const datasets = datasetsData.data || datasetsData || []
    if (datasets.length === 0) {
      ElMessage.error('未找到知识库')
      return
    }
    const datasetId = datasets[0].id
    
    await ElMessageBox.confirm('确定要清空知识库吗？此操作不可恢复！', '警告', {
      type: 'warning'
    })
    const response = await clearKnowledge(datasetId)
    const result = response.data || response
    ElMessage.success(result.message || '知识库已清空')
    await loadStats()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('清空失败：' + (error.response?.data?.message || error.message))
    }
  }
}

const handleRemoveFile = async (file) => {
  try {
    await ElMessageBox.confirm('确定要删除该文件吗？', '确认', {
      type: 'warning'
    })
    
    // 获取知识库 ID
    const datasetsResponse = await getDatasets()
    const datasetsData = datasetsResponse.data || datasetsResponse
    const datasets = datasetsData.data || datasetsData || []
    if (datasets.length === 0) {
      ElMessage.error('未找到知识库')
      return
    }
    const datasetId = datasets[0].id
    
    const response = await removeFile(datasetId, file.id)
    const result = response.data || response
    ElMessage.success(result.message || '文件已删除')
    await loadStats()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败：' + (error.response?.data?.message || error.message))
    }
  }
}

onMounted(() => {
  loadStats()
})

onUnmounted(() => {
  stopPolling()
})
</script>

<style scoped>
.knowledge-container {
  max-width: 1400px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: bold;
}

.sync-section {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.sync-result {
  margin-top: 16px;
}

.stats-section {
  display: flex;
  justify-content: space-around;
  padding: 20px 0;
}

.stat-item {
  text-align: center;
}

.stat-label {
  color: #909399;
  font-size: 14px;
  margin-bottom: 10px;
}

.stat-value {
  font-size: 42px;
  font-weight: bold;
  color: #409EFF;
}

.file-list-section {
  margin-top: 10px;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.list-header h3 {
  margin: 0;
  color: #303133;
  font-size: 16px;
}

.upload-area {
  width: 100%;
}
</style>
