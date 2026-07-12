<template>
  <div class="settings-container">
    <el-row :gutter="20">
      <!-- 系统配置 -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <el-icon><Setting /></el-icon>
              <span>系统配置</span>
            </div>
          </template>
          
          <el-form label-width="120px" label-position="left">
            <el-form-item label="API 服务地址">
              <el-input v-model="config.openaiBaseUrl" placeholder="http://localhost:8000/v1" />
              <div class="form-tip">OpenAI 兼容 API 地址（vLLM/Ollama/LM Studio）</div>
            </el-form-item>
            
            <el-form-item label="API Key">
              <el-input
                v-model="config.apiKey"
                type="password"
                show-password
                placeholder="sk-no-key-required"
              />
            </el-form-item>
            
            <el-form-item label="嵌入模型">
              <el-select v-model="config.embeddingModel" style="width: 100%">
                <el-option label="BAAI/bge-large-zh-v1.5 (推荐)" value="BAAI/bge-large-zh-v1.5" />
                <el-option label="text-embedding-3-small" value="text-embedding-3-small" />
                <el-option label="text-embedding-3-large" value="text-embedding-3-large" />
              </el-select>
              <div class="form-tip">用于文档向量化的嵌入模型</div>
            </el-form-item>
            
            <el-form-item label="LLM 模型">
              <el-select v-model="config.llmModel" style="width: 100%">
                <el-option label="qwen2.5:7b" value="qwen2.5:7b" />
                <el-option label="qwen2.5:14b" value="qwen2.5:14b" />
                <el-option label="llama3:8b" value="llama3:8b" />
                <el-option label="Qwen/Qwen2.5-7B-Instruct" value="Qwen/Qwen2.5-7B-Instruct" />
              </el-select>
              <div class="form-tip">用于问答和创作的 LLM 模型</div>
            </el-form-item>
            
            <el-form-item label="向量维度">
              <el-input-number
                v-model="config.vectorDimension"
                :min="128"
                :max="4096"
                :step="128"
              />
              <div class="form-tip">根据嵌入模型调整：bge-large-zh=1024, embedding-3-small=1536</div>
            </el-form-item>
          </el-form>
        </el-card>
        
        <!-- 数据库配置 -->
        <el-card style="margin-top: 20px">
          <template #header>
            <div class="card-header">
              <el-icon><Connection /></el-icon>
              <span>数据库配置</span>
            </div>
          </template>
          
          <el-form label-width="100px" label-position="left">
            <el-form-item label="主机">
              <el-input v-model="config.postgresHost" placeholder="localhost" />
            </el-form-item>
            <el-form-item label="端口">
              <el-input-number v-model="config.postgresPort" :min="1" :max="65535" />
            </el-form-item>
            <el-form-item label="数据库">
              <el-input v-model="config.postgresDb" placeholder="rag_knowledge" />
            </el-form-item>
            <el-form-item label="用户">
              <el-input v-model="config.postgresUser" placeholder="postgres" />
            </el-form-item>
            <el-form-item label="密码">
              <el-input
                v-model="config.postgresPassword"
                type="password"
                show-password
                placeholder="postgres"
              />
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
      
      <!-- 右侧：系统信息 -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <el-icon><Monitor /></el-icon>
              <span>系统信息</span>
            </div>
          </template>
          
          <el-descriptions :column="1" border>
            <el-descriptions-item label="系统版本">
              RAG 知识库系统 v1.0.0
            </el-descriptions-item>
            <el-descriptions-item label="后端框架">
              FastAPI + PostgreSQL + pgvector
            </el-descriptions-item>
            <el-descriptions-item label="前端框架">
              Vue 3 + Element Plus
            </el-descriptions-item>
            <el-descriptions-item label="向量存储">
              PostgreSQL 16 + pgvector
            </el-descriptions-item>
            <el-descriptions-item label="部署方式">
              本地部署，数据完全私有
            </el-descriptions-item>
          </el-descriptions>
        </el-card>
        
        <el-card style="margin-top: 20px">
          <template #header>
            <div class="card-header">
              <el-icon><Document /></el-icon>
              <span>快速链接</span>
            </div>
          </template>
          
          <div class="links-section">
            <el-button text @click="openLink('https://hermes-agent.nousresearch.com/docs')">
              <el-icon><Link /></el-icon>
              Hermes Agent 文档
            </el-button>
            <br />
            <el-button text @click="openLink('https://github.com/pgvector/pgvector')">
              <el-icon><Link /></el-icon>
              pgvector GitHub
            </el-button>
            <br />
            <el-button text @click="openLink('https://vitejs.dev/')">
              <el-icon><Link /></el-icon>
              Vite 文档
            </el-button>
            <br />
            <el-button text @click="openLink('https://element-plus.org/')">
              <el-icon><Link /></el-icon>
              Element Plus 文档
            </el-button>
          </div>
        </el-card>
        
        <el-card style="margin-top: 20px">
          <template #header>
            <div class="card-header">
              <el-icon><InfoFilled /></el-icon>
              <span>关于</span>
            </div>
          </template>
          
          <div class="about-section">
            <p>
              <strong>RAG 知识库系统</strong> 是一款面向企业和个人的本地私有文档智能问答与辅助创作工具。
            </p>
            <br />
            <p>核心功能：</p>
            <ul>
              <li>📁 本地多格式文档读取与知识库构建</li>
              <li>🔍 私有文档精准智能问答</li>
              <li>✍️ 基于本地素材的智能文档创作</li>
            </ul>
            <br />
            <p>
              <el-tag type="success">数据安全</el-tag>
              <el-tag type="primary">本地部署</el-tag>
              <el-tag type="warning">隐私保护</el-tag>
            </p>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { reactive } from 'vue'
import { ElMessage } from 'element-plus'

const config = reactive({
  openaiBaseUrl: 'http://localhost:8000/v1',
  apiKey: 'sk-no-key-required',
  embeddingModel: 'BAAI/bge-large-zh-v1.5',
  llmModel: 'qwen2.5:7b',
  vectorDimension: 1024,
  postgresHost: 'localhost',
  postgresPort: 5432,
  postgresDb: 'rag_knowledge',
  postgresUser: 'postgres',
  postgresPassword: 'postgres'
})

const openLink = (url) => {
  window.open(url, '_blank')
}

// 保存配置（实际项目中需要调用后端 API）
const saveConfig = () => {
  ElMessage.info('配置保存功能开发中...')
}
</script>

<style scoped>
.settings-container {
  max-width: 1400px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: bold;
}

.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 5px;
}

.links-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
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
