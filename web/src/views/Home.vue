<template>
  <div class="home-container">
    <el-row :gutter="20">
      <!-- 欢迎卡片 -->
      <el-col :span="24">
        <el-card class="welcome-card">
          <div class="welcome-content">
            <h1>欢迎使用 KnowVault</h1>
            <p class="subtitle">本地私有文档智能问答与辅助创作工具</p>
            <div class="features">
              <el-tag type="success" effect="dark">📁 本地文档安全存储</el-tag>
              <el-tag type="primary" effect="dark">🔍 智能问答检索</el-tag>
              <el-tag type="warning" effect="dark">✍️ 文档辅助创作</el-tag>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 核心功能 -->
      <el-col :span="24">
        <el-card>
          <template #header>
            <div class="card-header">
              <el-icon><InfoFilled /></el-icon>
              <span>核心功能</span>
            </div>
          </template>
          <el-row :gutter="20">
            <el-col :span="8">
              <div class="feature-item">
                <div class="feature-icon">💬</div>
                <h3>智能问答</h3>
                <p>针对文件夹内全部文档内容进行问答交互，支持跨文件整合信息，精准定位原文依据，可解答文件细节、数据、条款、要点类问题。</p>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="feature-item">
                <div class="feature-icon">📝</div>
                <h3>文档创作</h3>
                <p>辅助撰写报告、总结、方案、笔记、摘要等内容，创作内容可调用本地文档中的数据、案例、条款、素材。</p>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="feature-item">
                <div class="feature-icon">✨</div>
                <h3>文档优化</h3>
                <p>对上传文档进行定制性优化，包括扩写、缩写、改写、结构化整理等，优化后文档贴合原文档表达风格。</p>
              </div>
            </el-col>
          </el-row>
        </el-card>
      </el-col>

      <!-- 统计卡片 -->
      <el-col :span="8">
        <el-card class="stat-card">
          <template #header>
            <div class="card-header">
              <el-icon><FolderOpened /></el-icon>
              <span>知识库文件</span>
            </div>
          </template>
          <div class="stat-number">{{ stats.total_files || 0 }}</div>
          <div class="stat-label">已收录文档</div>
        </el-card>
      </el-col>

      <el-col :span="8">
        <el-card class="stat-card">
          <template #header>
            <div class="card-header">
              <el-icon><Document /></el-icon>
              <span>文本块</span>
            </div>
          </template>
          <div class="stat-number">{{ stats.total_chunks || 0 }}</div>
          <div class="stat-label">向量化片段</div>
        </el-card>
      </el-col>

      <el-col :span="8">
        <el-card class="stat-card">
          <template #header>
            <div class="card-header">
              <el-icon><CircleCheck /></el-icon>
              <span>系统状态</span>
            </div>
          </template>
          <div class="stat-number">
            <el-tag type="success">正常运行</el-tag>
          </div>
          <div class="stat-label">PostgreSQL + pgvector</div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getStatus } from '@/api'

const router = useRouter()
const stats = ref({ total_files: 0, total_chunks: 0 })

const loadStats = async () => {
  try {
    const data = await getStatus()
    // 新 API 返回格式：{ data: { knowledge_base: {...} } }
    if (data?.data?.knowledge_base) {
      stats.value = data.data.knowledge_base
    }
  } catch (error) {
    console.error('加载统计失败:', error)
  }
}

onMounted(() => {
  loadStats()
})
</script>

<style scoped>
.home-container {
  max-width: 1400px;
  margin: 0 auto;
}

.welcome-card {
  margin-bottom: 20px;
}

.welcome-content {
  text-align: center;
  padding: 20px 0;
}

.welcome-content h1 {
  color: #303133;
  margin-bottom: 10px;
}

.subtitle {
  color: #909399;
  margin-bottom: 20px;
}

.features {
  display: flex;
  justify-content: center;
  gap: 15px;
}

.stat-card {
  text-align: center;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: bold;
}

.stat-number {
  font-size: 36px;
  font-weight: bold;
  color: #409EFF;
  margin: 20px 0;
}

.stat-label {
  color: #909399;
  font-size: 14px;
}

.feature-item {
  text-align: center;
  padding: 20px;
}

.feature-icon {
  font-size: 48px;
  margin-bottom: 15px;
}

.feature-item h3 {
  color: #303133;
  margin-bottom: 10px;
}

.feature-item p {
  color: #606266;
  line-height: 1.6;
}

.about-section {
  line-height: 1.8;
  color: #606266;
}

.about-section p {
  margin-bottom: 10px;
}

.about-section ul {
  padding-left: 20px;
}

.about-section li {
  margin-bottom: 5px;
}
</style>
