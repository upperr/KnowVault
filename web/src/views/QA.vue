<template>
  <div class="qa-container">
    <el-row :gutter="20">
      <!-- 左侧：问答区域 -->
      <el-col :span="16">
        <el-card class="chat-card">
          <template #header>
            <div class="card-header">
              <el-icon><ChatDotRound /></el-icon>
              <span>智能问答</span>
              <el-checkbox v-model="useHistory" style="margin-left: auto">
                使用对话历史
              </el-checkbox>
            </div>
          </template>
          
          <!-- 对话历史 -->
          <div class="chat-history" ref="chatHistoryRef">
            <div
              v-for="(msg, index) in chatHistory"
              :key="index"
              :class="['message', msg.role]"
            >
              <div class="message-avatar">
                <el-icon v-if="msg.role === 'user'"><User /></el-icon>
                <el-icon v-else><Avatar /></el-icon>
              </div>
              <div class="message-content">
                <div class="message-text" v-html="msg.content"></div>
                <div v-if="msg.sources && msg.sources.length" class="message-sources">
                  <div class="sources-title">
                    <el-icon><Document /></el-icon>
                    📚 参考来源
                  </div>
                  <ul class="message-sources-list">
                    <li v-for="(source, i) in msg.sources" :key="i">
                      📄 {{ source }}
                    </li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
          
          <!-- 输入区域 -->
          <div class="chat-input">
            <el-input
              v-model="question"
              type="textarea"
              :rows="3"
              placeholder="请输入您的问题，系统将基于本地文档内容回答..."
              :disabled="loading"
              @keydown="handleKeydown"
            />
            <div class="input-actions">
              <el-button @click="handleClearHistory" :disabled="loading">
                <el-icon><Delete /></el-icon>
                清空历史
              </el-button>
              <el-button
                type="primary"
                :loading="loading"
                @click="handleAsk"
              >
                <el-icon><ChatLineRound /></el-icon>
                {{ loading ? '思考中...' : '发送提问' }}
              </el-button>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <!-- 右侧：相关信息 -->
      <el-col :span="8">
        <!-- 检索片段 -->
        <el-card v-if="currentChunks.length" style="margin-bottom: 20px">
          <template #header>
            <div class="card-header">
              <el-icon><Search /></el-icon>
              <span>检索到的文档片段</span>
            </div>
          </template>
          <el-collapse accordion>
            <el-collapse-item
              v-for="(chunk, index) in currentChunks"
              :key="index"
              :title="`片段${index + 1} - ${chunk.file_name}`"
            >
              <div class="chunk-content">
                <div class="chunk-meta">
                  <el-tag size="small">相关度：{{ ((1 - chunk.distance) * 100).toFixed(1) }}%</el-tag>
                </div>
                <p class="chunk-text">{{ chunk.content }}</p>
              </div>
            </el-collapse-item>
          </el-collapse>
        </el-card>
        
        <!-- 问答提示 -->
        <el-card>
          <template #header>
            <div class="card-header">
              <el-icon><InfoFilled /></el-icon>
              <span>问答提示</span>
            </div>
          </template>
          <div class="tips-section">
            <h4>💡 提问建议</h4>
            <ul>
              <li>基于文档内容提问，系统会精准定位原文</li>
              <li>支持跨文档整合信息回答问题</li>
              <li>可以询问文档细节、数据、条款、要点</li>
              <li>支持总结归纳类问题</li>
              <li>按 Enter 快速发送，Shift+Enter 换行</li>
            </ul>
            
            <h4>🔒 隐私保护</h4>
            <ul>
              <li>所有数据本地处理，不对外上传</li>
              <li>文档内容存储在本地 PostgreSQL 数据库</li>
              <li>问答过程完全私密</li>
            </ul>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { askQuestionStream, getDefaultModel, getDatasets } from '@/api'
import { renderMarkdown, escapeHtml } from '@/utils/markdown'
import { useChatStore } from '@/stores/chat'

defineOptions({
  name: 'QA'
})

const chatStore = useChatStore()
const question = ref('')
const loading = ref(false)
const chatHistoryRef = ref(null)
const defaultLlmId = ref(null)  // 存储默认 LLM ID
const datasetIds = ref([])  // 存储知识库 ID 列表
const currentChunksMap = ref({})  // 存储 chunk ID 到文件名的映射

// 使用 store 的状态
const chatHistory = computed(() => chatStore.chatHistory)
const currentChunks = computed(() => chatStore.currentChunks)
const useHistory = computed({
  get: () => chatStore.useHistory,
  set: (value) => chatStore.setUseHistory(value)
})

// 将答案中的 [ID:n] 替换为文件名（使用占位符避免被转义）
const replaceCitationMarkers = (content, chunksMap) => {
  if (!content || !chunksMap || Object.keys(chunksMap).length === 0) {
    return content
  }
  
  return content.replace(/\[ID:(\d+)\]/g, (match, id) => {
    const fileName = chunksMap[id]
    if (fileName) {
      // 使用占位符格式，避免被 escapeHtml 转义
      return `%%CITATION${fileName}%%`
    }
    return match  // 如果找不到对应的文件名，保留原标记
  })
}

// 将占位符转换为 HTML 上标标签（在 renderMarkdown 之后调用）
const renderCitations = (html) => {
  return html.replace(/%%CITATION([^%]+)%%/g, (match, fileName) => {
    return `<sup style="color: #409EFF; cursor: pointer;" title="点击查看来源：${fileName}">[${fileName}]</sup>`
  })
}

// 获取默认 LLM 模型
const loadDefaultModel = async () => {
  try {
    const model = await getDefaultModel()
    if (model?.id) {
      defaultLlmId.value = model.id
    }
  } catch (error) {
    console.error('[QA] 获取默认模型失败:', error)
  }
}

// 获取知识库列表
const loadDatasets = async () => {
  try {
    const response = await getDatasets()
    const datasets = response.data || []
    const validDatasets = datasets.filter(ds => ds.chunk_count && ds.chunk_count > 0)
    datasetIds.value = validDatasets.map(ds => ds.id)
  } catch (error) {
    console.error('[QA] 获取知识库列表失败:', error)
  }
}

const scrollToBottom = async () => {
  await nextTick()
  if (chatHistoryRef.value) {
    chatHistoryRef.value.scrollTop = chatHistoryRef.value.scrollHeight
  }
}

const handleKeydown = (event) => {
  if (event.key === 'Enter') {
    if (event.shiftKey) {
      // Shift+Enter: 允许换行，不阻止默认行为
      return
    } else {
      // Enter: 发送消息，阻止换行
      event.preventDefault()
      handleAsk()
    }
  }
}

const handleAsk = async () => {
  if (!question.value.trim()) {
    ElMessage.warning('请输入问题')
    return
  }
  
  loading.value = true
  const userQuestion = question.value
  question.value = ''
  
  // 添加用户消息
  chatStore.addMessage({
    role: 'user',
    content: escapeHtml(userQuestion)
  })
  await scrollToBottom()
  
  // 创建助手消息容器（直接添加到 store）
  chatStore.addMessage({
    role: 'assistant',
    content: '<span class="typing-indicator">正在思考</span>',
    sources: []
  })
  await scrollToBottom()
  
let fullAnswer = ''
let sources = []
let buffer = ''  // 用于拼接被分割的数据包
// 获取助手消息的索引（最后一个）
const assistantIndex = chatStore.chatHistory.length - 1

try {
  const response = await askQuestionStream(userQuestion, useHistory.value, null, defaultLlmId.value, datasetIds.value)
  
  if (!response.ok) {
    const errorText = await response.text()
    console.error('[QA] 响应错误:', errorText)
    throw new Error(`HTTP ${response.status}: ${errorText}`)
  }
  
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    
    const chunk = decoder.decode(value)
    buffer += chunk
    
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''
    
    for (const line of lines) {
      if (!line.trim() || !line.startsWith('data:')) continue
      
      if (line.slice(5).trim() === '[DONE]') {
        break
      }
      
      try {
        const data = JSON.parse(line.slice(5).trim())
        
        // RAGFlow 格式：{ code, message, data: { answer, reference, ... } }
        if (data.code !== 0 && data.data?.answer) {
          // 错误情况
          chatStore.updateMessage(assistantIndex, { content: '⚠️ ' + escapeHtml(data.message || '未知错误') })
          ElMessage.warning(data.message || '回答出错')
          loading.value = false
          return
        }
        
        if (data.data?.answer) {
          // 累加答案内容
          const answerChunk = data.data.answer
          fullAnswer += answerChunk
          // 先替换引用标记，再渲染 Markdown，最后渲染引用 HTML
          const replacedContent = replaceCitationMarkers(fullAnswer, currentChunksMap.value)
          chatStore.updateMessage(assistantIndex, { content: renderCitations(renderMarkdown(replacedContent)) })
          await scrollToBottom()
        }
        
        // 处理引用来源
        if (data.data?.reference && Array.isArray(data.data.reference.chunks) && data.data.reference.chunks.length > 0) {
          const chunks = data.data.reference.chunks
          // 保存 chunk ID 到文件名的映射
          const chunksMap = {}
          chunks.forEach((chunk, index) => {
            const fileName = chunk.document_name || chunk.file_name || chunk.doc_name || `文档${index + 1}`
            chunksMap[String(index)] = fileName
            if (chunk.id) {
              chunksMap[String(chunk.id)] = fileName
            }
          })
          currentChunksMap.value = chunksMap
          
          // 从答案中提取实际被引用的 ID，只列出 LLM 实际使用的文档
          const citedIds = new Set()
          const citationRegex = /\[ID:(\d+)\]/g
          let match
          while ((match = citationRegex.exec(fullAnswer)) !== null) {
            citedIds.add(match[1])
          }
          
          // 只保留实际被引用的文档（去重）
          const seenDocs = new Set()
          sources = Array.from(citedIds)
            .map(id => chunksMap[String(id)])
            .filter(Boolean)
            .filter(doc => {
              if (seenDocs.has(doc)) return false
              seenDocs.add(doc)
              return true
            })
          
          if (sources.length > 0) {
            chatStore.updateMessage(assistantIndex, { sources: sources })
          }
          
          // 替换答案中的 [ID:n] 标记为文件名，并重新渲染
          if (fullAnswer) {
            const replacedContent = replaceCitationMarkers(fullAnswer, chunksMap)
            chatStore.updateMessage(assistantIndex, { content: renderCitations(renderMarkdown(replacedContent)) })
          }
        }
        
        // 检查是否是 final 消息
        if (data.data?.final === true) {
          break
        }
      } catch (e) {
        console.error('Parse error:', e, line)
      }
    }
  }
  
  // 完成
  ElMessage.success('回答完成')
  
  // 流式传输完成后，再次替换引用标记并更新来源列表（确保处理完整答案）
  if (fullAnswer && Object.keys(currentChunksMap.value).length > 0) {
    const replacedContent = replaceCitationMarkers(fullAnswer, currentChunksMap.value)
    chatStore.updateMessage(assistantIndex, { content: renderCitations(renderMarkdown(replacedContent)) })
    
    // 从完整答案中提取实际被引用的 ID，更新来源列表
    const citedIds = new Set()
    const citationRegex = /\[ID:(\d+)\]/g
    let match
    while ((match = citationRegex.exec(replacedContent)) !== null) {
      citedIds.add(match[1])
    }
    
    const seenDocs = new Set()
    const finalSources = Array.from(citedIds)
      .map(id => currentChunksMap.value[String(id)])
      .filter(Boolean)
      .filter(doc => {
        if (seenDocs.has(doc)) return false
        seenDocs.add(doc)
        return true
      })
    
    if (finalSources.length > 0) {
      chatStore.updateMessage(assistantIndex, { sources: finalSources })
    }
  }
} catch (error) {
    chatStore.updateMessage(assistantIndex, { content: '请求失败：' + escapeHtml(error.message) })
    ElMessage.error('请求失败')
  } finally {
    loading.value = false
  }
}

const handleClearHistory = () => {
  chatStore.clearHistory()
  ElMessage.success('对话历史已清空')
}

onMounted(() => {
  // 初始化欢迎消息（仅当历史为空时）
  chatStore.initWelcomeMessage()
  // 加载默认 LLM 模型
  loadDefaultModel()
  // 加载知识库列表
  loadDatasets()
})
</script>

<style scoped>
.qa-container {
  max-width: 1400px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: bold;
}

.chat-card {
  height: calc(100vh - 140px);
  display: flex;
  flex-direction: column;
}

.chat-history {
  flex: 1;
  overflow-y: auto;
  padding: 10px;
  min-height: 400px;
}

.message {
  display: flex;
  gap: 15px;
  margin-bottom: 20px;
  padding: 15px;
  border-radius: 10px;
}

.message.user {
  background-color: #e6f7ff;
}

.message.assistant {
  background-color: #f5f7fa;
}

.message-avatar {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background-color: #409EFF;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
}

.message-content {
  flex: 1;
  min-width: 0;
}

.message-text {
  line-height: 1.8;
  color: #303133;
}

.message-text :deep(h1),
.message-text :deep(h2),
.message-text :deep(h3),
.message-text :deep(h4),
.message-text :deep(h5),
.message-text :deep(h6) {
  color: #303133;
  margin: 12px 0 6px;
}

.message-text :deep(pre) {
  background: #f5f7fa;
  padding: 12px;
  border-radius: 6px;
  overflow-x: auto;
  font-family: 'Courier New', Courier, monospace;
}

.message-text :deep(code) {
  background: #f5f7fa;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Courier New', Courier, monospace;
}

.message-text :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 12px 0;
}

.message-text :deep(th),
.message-text :deep(td) {
  border: 1px solid #dcdfe6;
  padding: 8px 12px;
  text-align: left;
}

.message-text :deep(th) {
  background: #f5f7fa;
  font-weight: 600;
}

.message-text :deep(ul),
.message-text :deep(ol) {
  padding-left: 20px;
}

.message-text :deep(blockquote) {
  border-left: 4px solid #409EFF;
  padding-left: 16px;
  margin: 12px 0;
  color: #606266;
  background: #f5f7fa;
  padding: 12px 16px;
}

.message-sources {
  margin-top: 15px;
  padding-top: 10px;
  border-top: 1px solid #e4e7ed;
}

.sources-title {
  display: flex;
  align-items: center;
  gap: 5px;
  color: #606266;
  font-weight: bold;
  margin-bottom: 10px;
}

.message-sources-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.message-sources-list li {
  font-size: 13px;
  color: #909399;
  margin-bottom: 4px;
}

.typing-indicator {
  color: #909399;
  font-style: italic;
}

.chat-input {
  border-top: 1px solid #e4e7ed;
  padding-top: 15px;
}

.input-actions {
  display: flex;
  justify-content: space-between;
  margin-top: 10px;
}

.chunk-content {
  padding: 10px;
  background-color: #f5f7fa;
  border-radius: 5px;
}

.chunk-meta {
  margin-bottom: 10px;
}

.chunk-text {
  line-height: 1.6;
  color: #606266;
  font-size: 14px;
}

.tips-section h4 {
  color: #303133;
  margin: 15px 0 10px;
}

.tips-section ul {
  padding-left: 20px;
  color: #606266;
  line-height: 1.8;
}

.tips-section li {
  margin-bottom: 5px;
}
</style>
