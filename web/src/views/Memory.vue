<template>
  <div class="memory-container">
    <el-row :gutter="20">
      <!-- 记忆统计 -->
      <el-col :span="24">
        <el-card>
          <template #header>
            <div class="card-header">
              <el-icon><Collection /></el-icon>
              <span>记忆统计</span>
              <el-button type="primary" size="small" @click="loadMemoryStats" :loading="loading">
                <el-icon><Refresh /></el-icon>
                刷新
              </el-button>
            </div>
          </template>
          
          <el-row :gutter="20">
            <el-col :span="6">
              <div class="stat-item">
                <div class="stat-value primary">{{ memoryStats.shortTermSize || 0 }}</div>
                <div class="stat-label">短期记忆条目 (RAW)</div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="stat-item">
                <div class="stat-value success">{{ memoryStats.shortTermHits || 0 }}</div>
                <div class="stat-label">短期记忆消息数</div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="stat-item">
                <div class="stat-value warning">{{ memoryStats.longTermEntries || 0 }}</div>
                <div class="stat-label">长期记忆条目 (语义/事件/程序)</div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="stat-item">
                <div class="stat-value info">{{ memoryStats.longTermKeywords || 0 }}</div>
                <div class="stat-label">长期记忆消息数</div>
              </div>
            </el-col>
          </el-row>
        </el-card>
      </el-col>
      
      <!-- 记忆操作 -->
      <el-col :span="24">
        <el-card style="margin-top: 20px">
          <template #header>
            <div class="card-header">
              <el-icon><Operation /></el-icon>
              <span>记忆操作</span>
              <el-button type="primary" size="small" @click="showCreateDialog = true">
                <el-icon><Plus /></el-icon>
                创建记忆
              </el-button>
            </div>
          </template>
          
          <div class="operation-buttons">
            <el-button @click="handleClearMemory('short')" :loading="clearing">
              <el-icon><Delete /></el-icon>
              清空短期记忆
            </el-button>
            <el-button @click="handleClearMemory('long')" :loading="clearing">
              <el-icon><Delete /></el-icon>
              清空长期记忆
            </el-button>
            <el-button @click="handleRefreshPrefs" :loading="refreshing">
              <el-icon><Refresh /></el-icon>
              刷新偏好
            </el-button>
            <el-button type="danger" @click="handleClearMemory('all')" :loading="clearing">
              <el-icon><Delete /></el-icon>
              清空全部记忆
            </el-button>
          </div>
        </el-card>
      </el-col>
      
      <!-- 记忆说明 -->
      <el-col :span="24">
        <el-card style="margin-top: 20px">
          <template #header>
            <div class="card-header">
              <el-icon><InfoFilled /></el-icon>
              <span>记忆系统说明</span>
            </div>
          </template>
          
          <el-descriptions :column="2" border>
            <el-descriptions-item label="短期记忆 (RAW)">
              存储原始对话历史，保留完整的用户输入和 Agent 回复，用于后续检索和学习
            </el-descriptions-item>
            <el-descriptions-item label="长期记忆 (语义/事件/程序)">
              通过 LLM 从对话中提取结构化知识：
              <br/>• 语义知识：通用事实、定义、概念
              <br/>• 事件知识：具体经历、时间 bound 的事件
              <br/>• 程序知识：流程、方法、操作步骤
            </el-descriptions-item>
            <el-descriptions-item label="记忆消息数">
              每个记忆中存储的对话消息数量，反映记忆的使用频率
            </el-descriptions-item>
            <el-descriptions-item label="遗忘策略">
              当记忆容量达到上限时，按 FIFO(先进先出) 或 LRU(最近最少使用) 策略遗忘旧消息
            </el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 创建记忆对话框 -->
    <el-dialog v-model="showCreateDialog" title="创建记忆" width="500px" :close-on-click-modal="false">
      <el-form :model="createForm" label-width="100px" label-position="left">
        <el-form-item label="记忆名称" required>
          <el-input v-model="createForm.name" placeholder="请输入记忆名称" maxlength="50" show-word-limit />
        </el-form-item>
        
        <el-form-item label="记忆类型" required>
          <el-checkbox-group v-model="createForm.memory_type">
            <el-checkbox label="raw">原始对话 (RAW)</el-checkbox>
            <el-checkbox label="semantic">语义知识 (Semantic)</el-checkbox>
            <el-checkbox label="episodic">事件知识 (Episodic)</el-checkbox>
            <el-checkbox label="procedural">程序知识 (Procedural)</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        
        <el-form-item label="Embedding 模型" required>
          <el-select v-model="createForm.embd_id" placeholder="请选择 Embedding 模型" style="width: 100%">
            <el-option label="text-embedding-v3 (DashScope)" value="text-embedding-v3" />
            <el-option label="bge-large-zh-v1.5" value="bge-large-zh-v1.5" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="LLM 模型" required>
          <el-select v-model="createForm.llm_id" placeholder="请选择 LLM 模型" style="width: 100%">
            <el-option label="qwen-turbo (DashScope)" value="qwen-turbo" />
            <el-option label="qwen-plus (DashScope)" value="qwen-plus" />
            <el-option label="qwen-max (DashScope)" value="qwen-max" />
          </el-select>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="handleCreateMemory" :loading="creating">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getMemoryStats, clearMemory, refreshMemoryPrefs, createMemory } from '@/api'

const loading = ref(false)
const clearing = ref(false)
const refreshing = ref(false)
const creating = ref(false)
const showCreateDialog = ref(false)

const memoryStats = reactive({
  shortTermSize: 0,
  shortTermHits: 0,
  longTermEntries: 0,
  longTermKeywords: 0
})

const createForm = reactive({
  name: '',
  memory_type: ['raw'],
  embd_id: 'text-embedding-v3',
  llm_id: 'qwen-turbo'
})

const loadMemoryStats = async () => {
  loading.value = true
  try {
    const data = await getMemoryStats()
    // 后端返回格式：{ data: { total_memories, memories: [{ id, name, type: ['raw',...], message_count }] } }
    if (data?.data?.memories) {
      const memories = data.data.memories
      
      // 短期记忆：包含 raw 类型的记忆
      // 长期记忆：包含 semantic/episodic/procedural 类型的记忆
      const shortTermMemories = memories.filter(m => m.type?.includes('raw'))
      const longTermMemories = memories.filter(m => 
        m.type?.some(t => ['semantic', 'episodic', 'procedural'].includes(t))
      )
      
      memoryStats.shortTermSize = shortTermMemories.length
      memoryStats.shortTermHits = shortTermMemories.reduce((sum, m) => sum + (m.message_count || 0), 0)
      memoryStats.longTermEntries = longTermMemories.length
      memoryStats.longTermKeywords = longTermMemories.reduce((sum, m) => sum + (m.message_count || 0), 0)
    }
    ElMessage.success('记忆统计已更新')
  } catch (error) {
    ElMessage.error('加载失败：' + error.message)
  } finally {
    loading.value = false
  }
}

const handleCreateMemory = async () => {
  // 验证表单
  if (!createForm.name.trim()) {
    ElMessage.warning('请输入记忆名称')
    return
  }
  if (!createForm.memory_type || createForm.memory_type.length === 0) {
    ElMessage.warning('请至少选择一个记忆类型')
    return
  }
  
  creating.value = true
  try {
    await createMemory({
      name: createForm.name.trim(),
      memory_type: createForm.memory_type,
      embd_id: createForm.embd_id,
      llm_id: createForm.llm_id
    })
    ElMessage.success('创建成功')
    showCreateDialog.value = false
    // 重置表单
    createForm.name = ''
    createForm.memory_type = ['raw']
    createForm.embd_id = 'text-embedding-v3'
    createForm.llm_id = 'qwen-turbo'
    // 刷新统计
    await loadMemoryStats()
  } catch (error) {
    ElMessage.error('创建失败：' + error.message)
  } finally {
    creating.value = false
  }
}

const handleClearMemory = async (type) => {
  const typeNames = {
    short: '短期',
    long: '长期',
    all: '全部'
  }
  
  try {
    await ElMessageBox.confirm(`确定要清空${typeNames[type]}记忆吗？此操作不可恢复！`, '警告', {
      type: 'warning'
    })
    
    clearing.value = true
    await clearMemory(type)
    ElMessage.success('清空成功')
    await loadMemoryStats()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('清空失败：' + error.message)
    }
  } finally {
    clearing.value = false
  }
}

const handleRefreshPrefs = async () => {
  refreshing.value = true
  try {
    await refreshMemoryPrefs()
    ElMessage.success('刷新成功')
    await loadMemoryStats()
  } catch (error) {
    ElMessage.error('刷新失败：' + error.message)
  } finally {
    refreshing.value = false
  }
}

onMounted(() => {
  loadMemoryStats()
})
</script>

<style scoped>
.memory-container {
  max-width: 1400px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: bold;
}

.stat-item {
  text-align: center;
  padding: 20px;
  background: #f5f7fa;
  border-radius: 8px;
}

.stat-value {
  font-size: 36px;
  font-weight: bold;
  margin-bottom: 8px;
}

.stat-value.primary { color: #409EFF }
.stat-value.success { color: #67C23A }
.stat-value.warning { color: #E6A23C }
.stat-value.info { color: #909399 }

.stat-label {
  color: #606266;
  font-size: 14px;
}

.operation-buttons {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}
</style>
