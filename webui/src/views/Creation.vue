<template>
  <div class="creation-container">
    <el-row :gutter="20">
      <!-- 左侧：创作配置 -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <el-icon><Edit /></el-icon>
              <span>文档创作</span>
            </div>
          </template>
          
          <el-form
            ref="formRef"
            :model="form"
            label-width="100px"
            label-position="top"
          >
            <el-form-item label="创作类型" required>
              <el-select
                v-model="form.creation_type"
                placeholder="请选择创作类型"
                style="width: 100%"
              >
                <el-option label="📊 报告" value="report" />
                <el-option label="📝 总结" value="summary" />
                <el-option label="📋 方案" value="plan" />
                <el-option label="📓 笔记" value="notes" />
                <el-option label="📄 摘要" value="abstract" />
                <el-option label="✍️ 扩写" value="expand" />
                <el-option label="✂️ 缩写" value="condense" />
                <el-option label="🔄 改写" value="rewrite" />
                <el-option label="🗂️ 结构化整理" value="structure" />
                <el-option label="🎯 自定义" value="custom" />
              </el-select>
            </el-form-item>
            
            <el-form-item label="文档标题" required>
              <el-input
                v-model="form.title"
                placeholder="例如：2024 年项目总结报告"
                style="width: 100%"
              />
            </el-form-item>
            
            <el-form-item label="具体要求" required>
              <el-input
                v-model="form.requirement"
                type="textarea"
                :rows="4"
                placeholder="请描述您的具体需求，例如：重点突出项目成果、包含数据分析、字数控制在 3000 字左右..."
                style="width: 100%"
              />
            </el-form-item>
            
            <el-form-item
              v-if="['expand', 'condense', 'rewrite', 'structure'].includes(form.creation_type)"
              label="原文内容"
              required
            >
              <el-input
                v-model="form.original_text"
                type="textarea"
                :rows="6"
                placeholder="请输入需要处理的原文内容..."
                style="width: 100%"
              />
            </el-form-item>
            
            <el-form-item>
              <el-button
                type="primary"
                :loading="creating"
                @click="handleCreate"
                style="width: 100%"
                size="large"
              >
                <el-icon><DocumentAdd /></el-icon>
                {{ creating ? '创作中...' : '开始创作' }}
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
        
        <!-- 创作提示 -->
        <el-card style="margin-top: 20px">
          <template #header>
            <div class="card-header">
              <el-icon><Lightbulb /></el-icon>
              <span>创作说明</span>
            </div>
          </template>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="报告">
              生成结构化工作报告、项目报告等，包含概述、正文、结论
            </el-descriptions-item>
            <el-descriptions-item label="总结">
              提炼关键信息，生成工作总结、学习总结等
            </el-descriptions-item>
            <el-descriptions-item label="方案">
              生成实施方案、技术方案，包含背景、目标、计划等
            </el-descriptions-item>
            <el-descriptions-item label="扩写/缩写">
              基于原文进行内容扩展或精简
            </el-descriptions-item>
            <el-descriptions-item label="改写">
              保持核心意思，调整文风、语气、表达方式
            </el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
      
      <!-- 右侧：创作结果 -->
      <el-col :span="12">
        <el-card class="result-card">
          <template #header>
            <div class="card-header">
              <el-icon><Document /></el-icon>
              <span>创作结果</span>
              <div style="margin-left: auto; display: flex; gap: 10px">
                <el-button
                  :disabled="!result.content"
                  @click="handleCopy"
                >
                  <el-icon><CopyDocument /></el-icon>
                  复制
                </el-button>
                <el-button
                  :disabled="!result.content"
                  @click="handleExport"
                >
                  <el-icon><Download /></el-icon>
                  导出
                </el-button>
              </div>
            </div>
          </template>
          
          <!-- 空状态 -->
          <el-empty
            v-if="!result.content && !creating"
            description="请选择创作类型并填写要求，点击开始创作"
          />
          
          <!-- 加载状态 -->
          <el-skeleton
            v-if="creating"
            :rows="10"
            animated
          />
          
          <!-- 创作结果 -->
          <div v-if="result.content" class="result-content">
            <div class="result-meta">
              <el-tag type="success">{{ form.title }}</el-tag>
              <el-tag>{{ creationTypeLabels[form.creation_type] }}</el-tag>
            </div>
            <div class="result-text" v-html="formatContent(result.content)"></div>
            
            <!-- 参考来源 -->
            <el-divider />
            <div class="result-sources">
              <div class="sources-title">
                <el-icon><FolderOpened /></el-icon>
                参考文档
              </div>
              <el-tag
                v-for="(source, index) in result.sources"
                :key="index"
                style="margin-right: 10px; margin-bottom: 10px"
              >
                {{ source }}
              </el-tag>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { createDocument } from '@/api'

const formRef = ref(null)
const creating = ref(false)
const result = ref({ content: '', sources: [] })

const form = reactive({
  creation_type: 'report',
  title: '',
  requirement: '',
  original_text: '',
})

const creationTypeLabels = {
  report: '报告',
  summary: '总结',
  plan: '方案',
  notes: '笔记',
  abstract: '摘要',
  expand: '扩写',
  condense: '缩写',
  rewrite: '改写',
  structure: '结构化',
  custom: '自定义'
}

const handleCreate = async () => {
  // 验证必填项
  if (!form.title.trim()) {
    ElMessage.warning('请填写文档标题')
    return
  }
  if (!form.requirement.trim()) {
    ElMessage.warning('请填写具体要求')
    return
  }
  if (['expand', 'condense', 'rewrite', 'structure'].includes(form.creation_type) 
      && !form.original_text.trim()) {
    ElMessage.warning('请填写原文内容')
    return
  }
  
  creating.value = true
  result.value = { content: '', sources: [] }
  
  try {
    const data = await createDocument(form)
    result.value = data
    if (data.success) {
      ElMessage.success('创作完成')
    } else {
      ElMessage.warning(data.content || '创作失败')
    }
  } catch (error) {
    ElMessage.error('创作失败：' + error.message)
  } finally {
    creating.value = false
  }
}

const handleCopy = async () => {
  try {
    await navigator.clipboard.writeText(result.value.content)
    ElMessage.success('已复制到剪贴板')
  } catch (error) {
    ElMessage.error('复制失败')
  }
}

const handleExport = () => {
  const blob = new Blob([result.value.content], { type: 'text/markdown' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${form.title || '文档'}.md`
  a.click()
  URL.revokeObjectURL(url)
  ElMessage.success('导出成功')
}

const formatContent = (content) => {
  // 简单的 Markdown 格式化
  return content
    .replace(/^### (.*$)/gim, '<h3>$1</h3>')
    .replace(/^## (.*$)/gim, '<h2>$1</h2>')
    .replace(/^# (.*$)/gim, '<h1>$1</h1>')
    .replace(/\*\*(.*)\*\*/gim, '<b>$1</b>')
    .replace(/\*(.*)\*/gim, '<i>$1</i>')
    .replace(/\n/gim, '<br>')
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

.result-card {
  min-height: calc(100vh - 140px);
}

.result-content {
  padding: 10px 0;
}

.result-meta {
  margin-bottom: 20px;
  display: flex;
  gap: 10px;
}

.result-text {
  line-height: 2;
  color: #303133;
  font-size: 15px;
}

.result-text :deep(h1),
.result-text :deep(h2),
.result-text :deep(h3) {
  color: #303133;
  margin: 20px 0 10px;
}

.result-text :deep(b) {
  color: #409EFF;
}

.result-sources {
  padding-top: 10px;
}

.sources-title {
  display: flex;
  align-items: center;
  gap: 5px;
  color: #606266;
  font-weight: bold;
  margin-bottom: 15px;
}
</style>
