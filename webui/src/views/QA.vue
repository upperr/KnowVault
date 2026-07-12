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
                    参考来源
                  </div>
                  <el-tag
                    v-for="(source, i) in msg.sources"
                    :key="i"
                    size="small"
                    style="margin-right: 5px; margin-bottom: 5px"
                  >
                    {{ source }}
                  </el-tag>
                </div>
              </div>
            </div>
            
            <!-- 加载状态 -->
            <div v-if="loading" class="message assistant">
              <div class="message-avatar">
                <el-icon><Avatar /></el-icon>
              </div>
              <div class="message-content">
                <el-skeleton :rows="3" animated />
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
              @keydown.ctrl.enter="handleAsk"
              @keydown.meta.enter="handleAsk"
            />
            <div class="input-actions">
              <el-button @click="handleClearHistory">
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
              <li>使用 Ctrl+Enter 或 Cmd+Enter 快速发送</li>
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
import { ref, nextTick, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { askQuestion } from '@/api'

const question = ref('')
const useHistory = ref(true)
const loading = ref(false)
const chatHistory = ref([])
const currentChunks = ref([])
const chatHistoryRef = ref(null)

const scrollToBottom = async () => {
  await nextTick()
  if (chatHistoryRef.value) {
    chatHistoryRef.value.scrollTop = chatHistoryRef.value.scrollHeight
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
  chatHistory.value.push({
    role: 'user',
    content: userQuestion
  })
  await scrollToBottom()
  
  try {
    const result = await askQuestion(userQuestion, useHistory.value)
    
    // 添加助手消息
    chatHistory.value.push({
      role: 'assistant',
      content: result.answer,
      sources: result.sources
    })
    
    // 更新检索片段
    if (result.chunks) {
      currentChunks.value = result.chunks
    }
    
    await scrollToBottom()
  } catch (error) {
    ElMessage.error('问答失败：' + error.message)
    // 移除失败的用户消息
    chatHistory.value.pop()
  } finally {
    loading.value = false
  }
}

const handleClearHistory = () => {
  chatHistory.value = []
  currentChunks.value = []
  ElMessage.success('对话历史已清空')
}

onMounted(() => {
  // 添加欢迎消息
  chatHistory.value.push({
    role: 'assistant',
    content: '您好！我是本地文档智能问答助手。我可以基于您本地文件夹中的文档内容回答问题，支持跨文件整合信息、精准定位原文依据。请问有什么可以帮您？'
  })
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
  white-space: pre-wrap;
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
