<template>
  <div class="knowledge-container">
    <el-row :gutter="20">
      <!-- 左侧：同步操作 -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <el-icon><FolderOpened /></el-icon>
              <span>文档同步</span>
            </div>
          </template>
          
          <div class="sync-section">
            <el-form label-position="top">
              <el-form-item label="文档目录路径">
                <el-input
                  v-model="docDir"
                  placeholder="默认：data/documents"
                  :disabled="syncing"
                >
                  <template #prepend>路径</template>
                </el-input>
              </el-form-item>
              
              <el-form-item>
                <el-button
                  type="primary"
                  :loading="syncing"
                  @click="handleSync"
                  style="width: 100%"
                >
                  <el-icon><Refresh /></el-icon>
                  {{ syncing ? '同步中...' : '开始同步' }}
                </el-button>
              </el-form-item>
            </el-form>
            
            <el-alert
              title="温馨提示"
              type="info"
              :closable="false"
              show-icon
            >
              <p>1. 将 PDF、Word、TXT 文档放入指定文件夹</p>
              <p>2. 点击"开始同步"按钮构建知识库</p>
              <p>3. 系统会自动解析文档并创建向量索引</p>
              <p>4. 支持增量更新，已处理文档不会重复解析</p>
            </el-alert>
          </div>
        </el-card>
        
        <!-- 同步结果 -->
        <el-card v-if="syncResult" style="margin-top: 20px">
          <template #header>
            <div class="card-header">
              <el-icon><CircleCheck /></el-icon>
              <span>同步结果</span>
            </div>
          </template>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="新增文件">
              <el-tag type="success">+{{ syncResult.added }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="删除文件">
              <el-tag type="danger">-{{ syncResult.deleted }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="更新文件">
              <el-tag type="warning">~{{ syncResult.updated }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="未变更">
              <el-tag>{{ syncResult.unchanged }}</el-tag>
            </el-descriptions-item>
          </el-descriptions>
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
            <h3>已收录文件</h3>
            <el-table :data="fileList" style="width: 100%" max-height="400">
              <el-table-column prop="file_name" label="文件名" show-overflow-tooltip />
              <el-table-column prop="file_path" label="路径" show-overflow-tooltip />
              <el-table-column label="操作" width="80">
                <template #default="{ row }">
                  <el-button
                    type="danger"
                    size="small"
                    @click="handleRemoveFile(row.file_path)"
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
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { syncDocuments, getKnowledgeStats, clearKnowledge, removeFile } from '@/api'

const docDir = ref('')
const syncing = ref(false)
const syncResult = ref(null)
const stats = ref({ total_files: 0, total_chunks: 0 })
const fileList = ref([])

const loadStats = async () => {
  try {
    const data = await getKnowledgeStats()
    if (data.knowledge_base) {
      stats.value = data.knowledge_base
      fileList.value = data.knowledge_base.file_list || []
    }
  } catch (error) {
    console.error('加载统计失败:', error)
  }
}

const handleSync = async () => {
  syncing.value = true
  try {
    const result = await syncDocuments(docDir.value)
    syncResult.value = result.sync_result
    ElMessage.success(result.message || '同步完成')
    await loadStats()
  } catch (error) {
    ElMessage.error('同步失败：' + (error.response?.data?.detail || error.message))
  } finally {
    syncing.value = false
  }
}

const handleClear = async () => {
  try {
    await ElMessageBox.confirm('确定要清空知识库吗？此操作不可恢复！', '警告', {
      type: 'warning'
    })
    await clearKnowledge()
    ElMessage.success('知识库已清空')
    await loadStats()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('清空失败：' + error.message)
    }
  }
}

const handleRemoveFile = async (filePath) => {
  try {
    await ElMessageBox.confirm('确定要删除该文件吗？', '确认', {
      type: 'warning'
    })
    await removeFile(filePath)
    ElMessage.success('文件已删除')
    await loadStats()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败：' + error.message)
    }
  }
}

onMounted(() => {
  loadStats()
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

.file-list-section h3 {
  margin-bottom: 15px;
  color: #303133;
}
</style>
