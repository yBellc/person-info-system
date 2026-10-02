<template>
  <div class="backup-page">
    <el-card shadow="never" class="backup-card">
      <template #header>
        <div class="card-header">
          <span>数据库备份管理</span>
          <div>
            <el-button type="primary" :loading="creating" @click="handleCreate">
              <el-icon><Plus /></el-icon>&nbsp;立即备份
            </el-button>
            <el-button @click="loadBackups">
              <el-icon><Refresh /></el-icon>&nbsp;刷新
            </el-button>
          </div>
        </div>
      </template>

      <el-alert type="info" :closable="false" class="tip-alert">
        <template #title>
          <span>建议定期备份（至少每周一次），备份文件存储在服务器 backend/backups/ 目录。</span>
        </template>
      </el-alert>

      <el-table :data="backups" v-loading="loading" stripe style="width: 100%">
        <el-table-column prop="filename" label="文件名" min-width="250" />
        <el-table-column prop="size_mb" label="大小" width="100">
          <template #default="{ row }">{{ row.size_mb }} MB</template>
        </el-table-column>
        <el-table-column prop="created_at" label="备份时间" width="180" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleDownload(row.filename)">
              <el-icon><Download /></el-icon>&nbsp;下载
            </el-button>
            <el-button link type="danger" @click="handleDelete(row.filename)">
              <el-icon><Delete /></el-icon>&nbsp;删除
            </el-button>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无备份文件，点击「立即备份」创建第一个备份" />
        </template>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { systemApi } from '@/api'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const loading = ref(false)
const creating = ref(false)
const backups = ref([])

const loadBackups = async () => {
  loading.value = true
  try {
    const data = await systemApi.listBackups()
    backups.value = data.items
  } finally {
    loading.value = false
  }
}

const handleCreate = async () => {
  try {
    await ElMessageBox.confirm('确认立即创建数据库备份？备份期间系统可能短暂无响应。', '确认备份', {
      type: 'warning',
    })
    creating.value = true
    const data = await systemApi.createBackup()
    ElMessage.success(`备份成功：${data.filename} (${data.size_mb} MB)`)
    loadBackups()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('备份失败')
  } finally {
    creating.value = false
  }
}

const handleDownload = (filename) => {
  const token = auth.token
  const url = systemApi.downloadBackup(filename)
  const link = document.createElement('a')
  link.href = `${url}?token=${token}`
  link.download = filename
  // 通过 fetch 带 token 下载
  fetch(url, {
    headers: { Authorization: `Bearer ${token}` },
  })
    .then(res => res.blob())
    .then(blob => {
      const objUrl = URL.createObjectURL(blob)
      link.href = objUrl
      link.click()
      URL.revokeObjectURL(objUrl)
    })
    .catch(() => ElMessage.error('下载失败'))
}

const handleDelete = async (filename) => {
  try {
    await ElMessageBox.confirm(`确认删除备份文件 ${filename}？此操作不可恢复。`, '确认删除', {
      type: 'warning',
    })
    await systemApi.deleteBackup(filename)
    ElMessage.success('已删除')
    loadBackups()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除失败')
  }
}

onMounted(() => {
  loadBackups()
})
</script>

<style scoped>
.backup-page {
  padding: 16px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.tip-alert {
  margin-bottom: 16px;
}
</style>
