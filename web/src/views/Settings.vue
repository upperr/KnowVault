<template>
  <div class="settings-container">
    <el-row :gutter="20">
      <!-- LLM 模型配置 -->
      <el-col :span="24">
        <el-card>
          <template #header>
            <div class="card-header">
              <el-icon><Setting /></el-icon>
              <span>LLM 模型配置</span>
              <el-button 
                type="primary" 
                size="small"
                @click="loadModels"
                :loading="loadingModels"
              >
                <el-icon><Refresh /></el-icon>
                刷新模型列表
              </el-button>
            </div>
          </template>
          
          <el-alert
            title="配置说明"
            type="info"
            :closable="false"
            style="margin-bottom: 20px"
          >
            <p>在此配置 RAGFlow 系统的 LLM 模型。配置后需要刷新页面生效。</p>
            <p><strong>注意：</strong>此配置会保存到 RAGFlow 后端，所有用户共享。</p>
          </el-alert>
          
          <el-form label-width="140px" label-position="left">
            <el-form-item label="默认 LLM 模型">
              <el-select 
                v-model="selectedModelId" 
                placeholder="请选择模型"
                style="width: 100%"
                :disabled="models.length === 0"
              >
                <el-option
                  v-for="model in models"
                  :key="model.id"
                  :label="`${model.name} (${model.provider_name})`"
                  :value="model.id"
                >
                  <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span>{{ model.name }}</span>
                    <el-tag size="small" type="info">{{ model.provider_name }}</el-tag>
                  </div>
                </el-option>
              </el-select>
              <div class="form-tip">
                当前已加载 {{ models.length }} 个模型
                <span v-if="defaultModelId" style="margin-left: 10px; color: #67C23A">
                  ✓ 当前默认：{{ defaultModelName }}
                </span>
              </div>
            </el-form-item>
            
            <el-form-item label="添加新模型">
              <el-button type="primary" @click="showAddModelDialog = true">
                <el-icon><Plus /></el-icon>
                添加模型提供商
              </el-button>
              <div class="form-tip">添加新的 LLM 提供商（如 DashScope、OpenAI、Ollama 等）</div>
            </el-form-item>
          </el-form>
        </el-card>
        
        <!-- 模型列表 -->
        <el-card style="margin-top: 20px">
          <template #header>
            <div class="card-header">
              <el-icon><List /></el-icon>
              <span>已配置的模型</span>
            </div>
          </template>
          
          <el-table :data="models" style="width: 100%" v-loading="loadingModels">
            <el-table-column prop="name" label="模型名称" />
            <el-table-column prop="provider_name" label="提供商" width="150" />
            <el-table-column prop="model_type" label="类型" width="100">
              <template #default="{ row }">
                <el-tag size="small">{{ row.model_type || 'chat' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag size="small" :type="row.id === defaultModelId ? 'success' : 'info'">
                  {{ row.id === defaultModelId ? '默认' : '可用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="150">
              <template #default="{ row }">
                <el-button 
                  size="small" 
                  @click="setDefaultModelAction(row.id)"
                  :disabled="row.id === defaultModelId"
                >
                  设为默认
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      
      <!-- 数据库配置（保留原有功能） -->
      <el-col :span="24" style="margin-top: 20px">
        <el-card>
          <template #header>
            <div class="card-header">
              <el-icon><Connection /></el-icon>
              <span>数据库配置（只读）</span>
            </div>
          </template>
          
          <el-form label-width="100px" label-position="left">
            <el-form-item label="主机">
              <el-input v-model="config.postgresHost" disabled />
            </el-form-item>
            <el-form-item label="端口">
              <el-input-number v-model="config.postgresPort" disabled />
            </el-form-item>
            <el-form-item label="数据库">
              <el-input v-model="config.postgresDb" disabled />
            </el-form-item>
            <el-form-item label="用户">
              <el-input v-model="config.postgresUser" disabled />
            </el-form-item>
          </el-form>
          
          <el-alert
            title="数据库配置由 RAGFlow 后端管理，此处仅显示当前配置。"
            type="warning"
            :closable="false"
          />
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 添加模型对话框 -->
    <el-dialog
      v-model="showAddModelDialog"
      title="添加模型提供商"
      width="600px"
    >
      <el-alert
        title="配置说明"
        type="info"
        :closable="false"
        style="margin-bottom: 15px"
      >
        添加模型提供商后，系统会自动加载该提供商下的所有可用模型。
      </el-alert>
      
      <el-form label-width="120px" label-position="left">
        <el-form-item label="提供商" required>
          <el-select v-model="newModel.provider" placeholder="选择提供商" style="width: 100%">
            <el-option label="DashScope (阿里通义)" value="dashscope" />
            <el-option label="OpenAI" value="openai" />
            <el-option label="Ollama (本地)" value="ollama" />
            <el-option label="ZhipuAI (智谱)" value="zhipuai" />
            <el-option label="OpenAI-API-Compatible (vLLM/LM Studio)" value="OpenAI-API-Compatible" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="API Key" required>
          <el-input
            v-model="newModel.apiKey"
            type="password"
            show-password
            placeholder="输入 API Key"
          />
          <div class="form-tip">Ollama 等本地模型不需要 API Key，可留空</div>
        </el-form-item>
        
        <el-form-item label="Base URL">
          <el-input
            v-model="newModel.baseUrl"
            placeholder="http://localhost:11434"
          />
          <div class="form-tip">Ollama: http://localhost:11434，vLLM: http://host:port/v1，其他通常不需要填写</div>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="showAddModelDialog = false">取消</el-button>
        <el-button type="primary" @click="addModelProviderAction">添加</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getModels, getDefaultModel, addModelProvider, addModelInstance, setDefaultModel, getProviders } from '@/api'

const loadingModels = ref(false)
const showAddModelDialog = ref(false)
const selectedModelId = ref(null)
const defaultModelId = ref(null)
const models = ref([])

const config = reactive({
  postgresHost: 'localhost',
  postgresPort: 5432,
  postgresDb: 'rag_knowledge',
  postgresUser: 'postgres'
})

const newModel = reactive({
  provider: 'dashscope',
  apiKey: '',
  baseUrl: ''
})

const defaultModelName = computed(() => {
  const model = models.value.find(m => m.id === defaultModelId.value)
  return model ? model.name : ''
})

// 加载模型列表
const loadModels = async () => {
  loadingModels.value = true
  try {
    const response = await getModels()
    models.value = response.data?.data || response.data || []
    console.log('[Settings] 模型列表:', models.value)
    
    // 加载默认模型
    await loadDefaultModel()
  } catch (error) {
    console.error('加载模型失败:', error)
    ElMessage.error('加载模型列表失败：' + (error.message || '未知错误'))
  } finally {
    loadingModels.value = false
  }
}

// 加载默认模型
const loadDefaultModel = async () => {
  try {
    const defaultModel = await getDefaultModel()
    if (defaultModel) {
      defaultModelId.value = defaultModel.id
      selectedModelId.value = defaultModel.id
    }
  } catch (error) {
    console.error('加载默认模型失败:', error)
  }
}

// 设置默认模型
const setDefaultModelAction = async (modelId) => {
  try {
    await setDefaultModel(modelId)
    defaultModelId.value = modelId
    selectedModelId.value = modelId
    ElMessage.success('默认模型已更新')
  } catch (error) {
    console.error('设置默认模型失败:', error)
    ElMessage.error('设置失败：' + (error.response?.data?.message || error.message))
  }
}

// 添加模型提供商
const addModelProviderAction = async () => {
  if (!newModel.apiKey && newModel.provider !== 'ollama') {
    ElMessage.warning('请输入 API Key')
    return
  }
  
  try {
    // 步骤 1: 添加 provider
    await addModelProvider(newModel.provider, newModel.apiKey, newModel.baseUrl)
    
    // 步骤 2: 添加 instance（带 API Key 和 Base URL）
    if (newModel.apiKey || newModel.baseUrl) {
      await addModelInstance(newModel.provider, newModel.apiKey, newModel.baseUrl)
    }
    
    ElMessage.success('模型提供商添加成功，请刷新模型列表')
    showAddModelDialog.value = false
    newModel.apiKey = ''
    newModel.baseUrl = ''
    
    // 刷新模型列表
    await loadModels()
  } catch (error) {
    console.error('添加模型提供商失败:', error)
    ElMessage.error('添加失败：' + (error.response?.data?.message || error.message))
  }
}

onMounted(() => {
  loadModels()
})
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

.el-alert p {
  margin: 5px 0;
  font-size: 13px;
  line-height: 1.5;
}
</style>
