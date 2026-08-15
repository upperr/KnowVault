<template>
  <div class="optimize-container">
    <el-row :gutter="20">
      <!-- 左侧：上传文档 -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <el-icon><Upload /></el-icon>
              <span>上传文档</span>
            </div>
          </template>
          
          <!-- 拖拽上传区域 -->
          <div
            class="drop-zone"
            :class="{ 'is-dragging': isDragging }"
            @dragover.prevent="isDragging = true"
            @dragleave.prevent="isDragging = false"
            @dragenter.prevent="isDragging = true"
            @drop.prevent="handleDrop"
          >
            <div class="drop-zone-content">
              <div class="drop-icon">📄</div>
              <div class="drop-text">拖拽文件到此处，或点击选择文件</div>
              <div class="drop-hint">支持 PDF、Word、TXT 格式</div>
              <input
                type="file"
                ref="fileInputRef"
                accept=".pdf,.doc,.docx,.txt"
                style="display: none"
                @change="handleFileSelect"
              />
              <el-button type="primary" @click="selectFile">
                <el-icon><FolderOpened /></el-icon>
                选择文件
              </el-button>
            </div>
          </div>
          
          <!-- 文件信息 -->
          <div v-if="currentFile" class="file-info">
            <div class="file-info-content">
              <span class="file-icon">📄</span>
              <div class="file-details">
                <div class="file-name">{{ currentFile.name }}</div>
                <div class="file-size">{{ formatFileSize(currentFile.size) }}</div>
              </div>
              <el-button type="danger" size="small" @click="clearFile">
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
          </div>
          
          <!-- 修改要求 -->
          <el-form label-position="top" style="margin-top: 20px">
            <el-form-item label="修改要求">
              <el-input
                v-model="instruction"
                type="textarea"
                :rows="5"
                placeholder="请输入您的修改要求，例如：&#10;- 请对文档内容进行扩写，添加更多细节和案例&#10;- 请总结文档的核心要点，控制在 300 字以内&#10;- 请优化文档的表达方式，使语言更通俗易懂&#10;- 请整理文档结构，添加标题层级和列表&#10;- 保持专业术语，修正格式错误"
                @keydown="handleKeydown"
              />
            </el-form-item>
            <el-form-item>
              <el-button
                type="primary"
                :loading="optimizing || isParsing"
                :disabled="!currentFile || !instruction.trim() || isParsing"
                @click="startOptimize"
                style="width: 100%"
              >
                <el-icon><MagicStick /></el-icon>
                {{ isParsing ? '文档解析中...' : (optimizing ? '优化中...' : '开始优化') }}
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
      
      <!-- 右侧：优化结果 -->
      <el-col :span="12">
        <el-card class="result-card">
          <template #header>
            <div class="card-header">
              <el-icon><Document /></el-icon>
              <span>优化结果</span>
              <div style="display: flex; gap: 8px; margin-left: auto">
                <el-button
                  size="small"
                  :disabled="!optimizeResult"
                  @click="copyResult"
                >
                  <el-icon><CopyDocument /></el-icon>
                  复制
                </el-button>
                <el-button
                  size="small"
                  :disabled="!optimizeResult"
                  @click="exportToDocx"
                >
                  <el-icon><Download /></el-icon>
                  导出 DOCX
                </el-button>
              </div>
            </div>
          </template>
          
          <!-- 空状态 -->
          <div v-if="!optimizeResult && !optimizing" class="empty-state">
            <div class="empty-text">请上传文档并输入修改要求后点击「开始优化」</div>
          </div>
          
          <!-- 加载状态 -->
          <div v-if="optimizing" class="loading-state">
            <el-icon class="is-loading"><Loading /></el-icon>
            <span>正在优化中...</span>
          </div>
          
          <!-- 优化结果 -->
          <div
            v-if="optimizeResult"
            class="result-content"
            v-html="renderedResult"
          ></div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { uploadFile, exportDocx, optimizeDocumentStream } from '@/api'
import { renderMarkdown } from '@/utils/markdown'
import axios from 'axios'

const fileInputRef = ref(null)
const isDragging = ref(false)
const optimizing = ref(false)
const isParsing = ref(false)

const currentFile = ref(null)
const currentFileContent = ref('')
const instruction = ref('')
const optimizeResult = ref('')

const renderedResult = computed(() => {
  return renderMarkdown(optimizeResult.value)
})

const handleKeydown = (event) => {
  if (event.key === 'Enter') {
    if (event.shiftKey) {
      // Shift+Enter: 允许换行，不阻止默认行为
      return
    } else {
      // Enter: 开始优化，阻止换行
      event.preventDefault()
      if (!optimizing.value && currentFile.value && instruction.value.trim()) {
        startOptimize()
      }
    }
  }
}

// 选择文件
const selectFile = () => {
  fileInputRef.value?.click()
}

// 处理文件选择
const handleFileSelect = async (event) => {
  const files = event.target.files
  if (files.length > 0) {
    await processFile(files[0])
  }
}

// 处理拖拽
const handleDrop = async (event) => {
  isDragging.value = false
  const files = event.dataTransfer.files
  if (files.length > 0) {
    await processFile(files[0])
  }
}

// 处理文件
const processFile = async (file) => {
  const allowedExts = ['.pdf', '.doc', '.docx', '.txt']
  const ext = '.' + file.name.split('.').pop().toLowerCase()
  
  if (!allowedExts.includes(ext)) {
    ElMessage.error('不支持的文件格式')
    return
  }
  
  currentFile.value = file
  optimizeResult.value = ''
  
  // 上传文件
  isParsing.value = true
  try {
    const formData = new FormData()
    formData.append('file', file)
    
    const response = await axios.post('/api/v1/files/upload', formData)
    
    const data = response.data
    // 后端返回格式：{ code: 0, data: { status: 'success', content: '...' }, message: 'success' }
    const result = data.data || data
    if (result.status === 'success' || result.status === 'ok') {
      // content 可能是数组，取第一个元素
      currentFileContent.value = Array.isArray(result.content) ? result.content[0] : result.content
      ElMessage.success('文档解析完成')
    } else {
      ElMessage.error('文件解析失败：' + (result.detail || result.message || '未知错误'))
      currentFileContent.value = ''
    }
  } catch (error) {
    ElMessage.error('上传失败：' + error.message)
    currentFileContent.value = ''
  } finally {
    isParsing.value = false
  }
}

// 清除文件
const clearFile = () => {
  currentFile.value = null
  currentFileContent.value = ''
  optimizeResult.value = ''
  instruction.value = ''
  if (fileInputRef.value) {
    fileInputRef.value.value = ''
  }
}

// 格式化文件大小
const formatFileSize = (bytes) => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

// 开始优化
const startOptimize = async () => {
  if (isParsing.value) {
    ElMessage.warning('文档解析中，请稍后...')
    return
  }
  
  if (!currentFileContent.value) {
    ElMessage.warning('请先上传文档')
    return
  }
  
  if (!instruction.value.trim()) {
    ElMessage.warning('请输入修改要求')
    return
  }
  
  optimizing.value = true
  optimizeResult.value = ''
  
  try {
    const response = await optimizeDocumentStream(currentFileContent.value, instruction.value)
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop()
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6))
            
            if (data.type === 'content') {
              optimizeResult.value += data.content
            } else if (data.type === 'error') {
              ElMessage.error('优化失败：' + data.message)
              optimizing.value = false
              return
            } else if (data.type === 'done') {
              ElMessage.success('优化完成')
            }
          } catch (e) {
            console.error('Parse error:', e)
          }
        }
      }
    }
  } catch (error) {
    ElMessage.error('请求失败：' + error.message)
  } finally {
    optimizing.value = false
  }
}

// 复制结果
const copyResult = async () => {
  if (optimizeResult.value) {
    await navigator.clipboard.writeText(optimizeResult.value)
    ElMessage.success('已复制纯文本到剪贴板')
  }
}

// 导出 DOCX
const exportToDocx = async () => {
  if (!optimizeResult.value) {
    ElMessage.warning('没有可导出的内容')
    return
  }
  
  try {
    // 从 markdown 内容中提取第一个标题作为文件名
    const match = optimizeResult.value.match(/^# (.+)$/m)
    const title = match ? match[1].trim() : 'optimized_doc'
    const filename = title.replace(/[\\/:*?"<>|]/g, '_')
    
    const response = await exportDocx(optimizeResult.value, title, filename)
    
    // 下载文件
    const blob = new Blob([response], { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename + '.docx'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    
    ElMessage.success('导出成功')
  } catch (error) {
    ElMessage.error('导出失败：' + error.message)
  }
}

// 引入 axios（用于文件上传）

onMounted(() => {
  // 初始化
})

onUnmounted(() => {
  // 清理
})
</script>

<style scoped>
.optimize-container {
  max-width: 1400px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: bold;
}

.drop-zone {
  border: 2px dashed #dcdfe6;
  border-radius: 12px;
  padding: 32px;
  text-align: center;
  transition: all 0.3s;
  cursor: pointer;
}

.drop-zone.is-dragging {
  border-color: #409EFF;
  background-color: #f0f9ff;
}

.drop-zone-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.drop-icon {
  font-size: 48px;
  margin-bottom: 8px;
}

.drop-text {
  font-size: 14px;
  color: #606266;
}

.drop-hint {
  font-size: 12px;
  color: #909399;
}

.file-info {
  margin-top: 16px;
  padding: 12px;
  background: #f5f7fa;
  border-radius: 8px;
}

.file-info-content {
  display: flex;
  align-items: center;
  gap: 12px;
}

.file-icon {
  font-size: 24px;
}

.file-details {
  flex: 1;
}

.file-name {
  font-weight: 600;
  color: #303133;
}

.file-size {
  font-size: 12px;
  color: #909399;
}

.result-card {
  min-height: calc(100vh - 140px);
}

.empty-state {
  padding: 60px 20px;
  text-align: center;
  color: #909399;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  gap: 16px;
  color: #606266;
}

.loading-state .is-loading {
  font-size: 32px;
  color: #409EFF;
}

.result-content {
  padding: 20px 0;
  line-height: 1.8;
  color: #303133;
}

.result-content :deep(h1),
.result-content :deep(h2),
.result-content :deep(h3),
.result-content :deep(h4),
.result-content :deep(h5),
.result-content :deep(h6) {
  color: #303133;
  margin: 16px 0 8px;
}

.result-content :deep(pre) {
  background: #f5f7fa;
  padding: 12px;
  border-radius: 6px;
  overflow-x: auto;
  font-family: 'Courier New', Courier, monospace;
}

.result-content :deep(code) {
  background: #f5f7fa;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Courier New', Courier, monospace;
}

.result-content :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 16px 0;
}

.result-content :deep(th),
.result-content :deep(td) {
  border: 1px solid #dcdfe6;
  padding: 8px 12px;
  text-align: left;
}

.result-content :deep(th) {
  background: #f5f7fa;
  font-weight: 600;
}

.result-content :deep(ul),
.result-content :deep(ol) {
  padding-left: 20px;
}

.result-content :deep(blockquote) {
  border-left: 4px solid #409EFF;
  padding-left: 16px;
  margin: 16px 0;
  color: #606266;
  background: #f5f7fa;
  padding: 12px 16px;
}
</style>
