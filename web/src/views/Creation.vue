<template>
  <div class="creation-container">
    <el-row :gutter="20">
      <!-- 左侧：创作要求 -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <el-icon><Edit /></el-icon>
              <span>文档创作</span>
            </div>
          </template>
          
          <div class="creation-form">
            <div class="input-group" style="margin-bottom: 16px">
              <label class="input-label">创作要求</label>
              <el-input
                v-model="requirement"
                type="textarea"
                :rows="6"
                placeholder="请描述您希望生成的文档类型、结构、内容要求等（例如：生成一份关于网络安全的技术报告，包含引言、正文、总结等章节）..."
                @keydown="handleKeydown"
              />
            </div>
            
            <el-button
              type="primary"
              :loading="creating"
              :disabled="!requirement.trim()"
              @click="startCreation"
              style="width: 100%"
              size="large"
            >
              <el-icon><DocumentAdd /></el-icon>
              {{ creating ? '创作中...' : '开始创作' }}
            </el-button>
          </div>
        </el-card>
        
        <!-- 创作说明 -->
        <el-card style="margin-top: 20px">
          <template #header>
            <div class="card-header">
              <el-icon><Lightbulb /></el-icon>
              <span>创作说明</span>
            </div>
          </template>
          <div class="tips-section">
            <p>系统将根据您的要求，基于本地文档库内容进行智能创作：</p>
            <ul>
              <li>📊 报告：生成结构化工作报告、项目报告等</li>
              <li>📝 总结：提炼关键信息，生成工作总结、学习总结</li>
              <li>📋 方案：生成实施方案、技术方案</li>
              <li>📓 笔记：整理学习笔记、会议记录</li>
              <li>📄 摘要：提取文档核心要点</li>
            </ul>
          </div>
        </el-card>
      </el-col>
      
      <!-- 右侧：创作结果 -->
      <el-col :span="12">
        <el-card class="result-card">
          <template #header>
            <div class="card-header">
              <el-icon><Document /></el-icon>
              <span>创作结果</span>
              <div style="display: flex; gap: 8px; margin-left: auto">
                <el-button
                  size="small"
                  :disabled="!creationResult"
                  @click="copyResult"
                >
                  <el-icon><CopyDocument /></el-icon>
                  复制
                </el-button>
                <el-button
                  size="small"
                  type="success"
                  :disabled="!creationResult"
                  @click="exportToDocx"
                >
                  <el-icon><Download /></el-icon>
                  导出 DOCX
                </el-button>
              </div>
            </div>
          </template>
          
          <!-- 空状态 -->
          <div v-if="!creationResult && !creating" class="empty-state">
            <div class="empty-text">请在左侧填写创作要求后点击「开始创作」</div>
          </div>
          
          <!-- 加载状态 -->
          <div v-if="creating" class="loading-state">
            <el-icon class="is-loading"><Loading /></el-icon>
            <span>正在创作中...</span>
          </div>
          
          <!-- 创作结果 -->
          <div
            v-if="creationResult"
            class="result-content"
            v-html="renderedResult"
          ></div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { createDocumentStream, exportDocx } from '@/api'
import { renderMarkdown } from '@/utils/markdown'

const requirement = ref('')
const creating = ref(false)
const creationResult = ref('')
const rawContent = ref('')

const renderedResult = computed(() => {
  return renderMarkdown(creationResult.value)
})

const handleKeydown = (event) => {
  if (event.key === 'Enter') {
    if (event.shiftKey) {
      // Shift+Enter: 允许换行，不阻止默认行为
      return
    } else {
      // Enter: 开始创作，阻止换行
      event.preventDefault()
      if (!creating.value && requirement.value.trim()) {
        startCreation()
      }
    }
  }
}

// 开始创作
const startCreation = async () => {
  if (!requirement.value.trim()) {
    ElMessage.warning('请输入创作要求')
    return
  }
  
  creating.value = true
  creationResult.value = ''
  rawContent.value = ''
  
  try {
    const response = await createDocumentStream(requirement.value)
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
              rawContent.value += data.content
              creationResult.value = rawContent.value
            } else if (data.type === 'done') {
              ElMessage.success('创作完成')
            } else if (data.type === 'error') {
              ElMessage.error('创作失败：' + data.message)
              creating.value = false
              return
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
    creating.value = false
  }
}

// 复制结果
const copyResult = async () => {
  if (rawContent.value) {
    await navigator.clipboard.writeText(rawContent.value)
    ElMessage.success('已复制纯文本到剪贴板')
  }
}

// 导出 DOCX
const exportToDocx = async () => {
  if (!rawContent.value) {
    ElMessage.warning('没有可导出的内容')
    return
  }
  
  try {
    // 从 markdown 内容中提取第一个标题作为文件名
    const match = rawContent.value.match(/^# (.+)$/m)
    const title = match ? match[1].trim() : '创作文档'
    const filename = title.replace(/[\\/:*?"<>|]/g, '_')
    
    const response = await exportDocx(rawContent.value, title, filename)
    
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
</script>

<style scoped>
.creation-container {
  max-width: 1400px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: bold;
}

.input-label {
  display: block;
  margin-bottom: 8px;
  color: #606266;
  font-size: 14px;
}

.tips-section {
  line-height: 1.8;
  color: #606266;
}

.tips-section ul {
  padding-left: 20px;
  margin-top: 8px;
}

.tips-section li {
  margin-bottom: 5px;
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
