<template>
  <div class="page-container">
    <div class="section-title">管理员申请审批</div>

    <el-card>
      <div class="toolbar">
        <el-radio-group v-model="statusFilter" @change="loadData">
          <el-radio-button label="pending">待审批</el-radio-button>
          <el-radio-button label="approved">已批准</el-radio-button>
          <el-radio-button label="rejected">已驳回</el-radio-button>
          <el-radio-button label="all">全部</el-radio-button>
        </el-radio-group>
      </div>

      <el-table :data="list" v-loading="loading" border stripe style="margin-top: 16px">
        <el-table-column type="index" label="#" width="50" align="center" />
        <el-table-column prop="username" label="申请人" width="120" />
        <el-table-column prop="target_unit_name" label="申请管理单位" width="140" />
        <el-table-column prop="reason" label="申请理由" min-width="200" show-overflow-tooltip />
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="申请时间" width="170">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <template v-if="row.status === 'pending'">
              <el-button size="small" type="success" @click="openReview(row, 'approve')">批准</el-button>
              <el-button size="small" type="danger" @click="openReview(row, 'reject')">驳回</el-button>
            </template>
            <span v-else style="color: #909399; font-size: 12px">
              {{ row.review_note ? '意见：' + row.review_note : '—' }}
            </span>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!loading && list.length === 0" description="暂无申请" />
    </el-card>

    <!-- 审批对话框 -->
    <el-dialog v-model="reviewVisible" :title="reviewAction === 'approve' ? '批准申请' : '驳回申请'" width="440px">
      <el-descriptions :column="1" border size="small" style="margin-bottom: 16px">
        <el-descriptions-item label="申请人">{{ reviewTarget?.username }}</el-descriptions-item>
        <el-descriptions-item label="申请单位">{{ reviewTarget?.target_unit_name }}</el-descriptions-item>
        <el-descriptions-item label="申请理由">{{ reviewTarget?.reason || '—' }}</el-descriptions-item>
      </el-descriptions>
      <el-form>
        <el-form-item :label="reviewAction === 'approve' ? '批准意见' : '驳回原因'">
          <el-input v-model="reviewNote" type="textarea" :rows="3" placeholder="选填" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="reviewVisible = false">取消</el-button>
        <el-button :type="reviewAction === 'approve' ? 'success' : 'danger'" :loading="submitting" @click="submitReview">
          确认{{ reviewAction === 'approve' ? '批准' : '驳回' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/api'

const list = ref([])
const loading = ref(false)
const statusFilter = ref('pending')

const reviewVisible = ref(false)
const reviewTarget = ref(null)
const reviewAction = ref('approve')
const reviewNote = ref('')
const submitting = ref(false)

const loadData = async () => {
  loading.value = true
  try {
    list.value = await api.get('/auth/applications', { params: { status_filter: statusFilter.value } })
  } finally {
    loading.value = false
  }
}

const statusType = (s) => ({ pending: 'warning', approved: 'success', rejected: 'danger' }[s] || 'info')
const statusLabel = (s) => ({ pending: '待审批', approved: '已批准', rejected: '已驳回' }[s] || s)

const formatTime = (t) => t ? new Date(t).toLocaleString('zh-CN') : ''

const openReview = (row, action) => {
  reviewTarget.value = row
  reviewAction.value = action
  reviewNote.value = ''
  reviewVisible.value = true
}

const submitReview = async () => {
  submitting.value = true
  try {
    const url = `/auth/applications/${reviewTarget.value.id}/${reviewAction.value}`
    await api.put(url, { review_note: reviewNote.value })
    ElMessage.success(reviewAction.value === 'approve' ? '已批准，该用户已升级为单位管理员' : '已驳回')
    reviewVisible.value = false
    loadData()
  } finally {
    submitting.value = false
  }
}

onMounted(loadData)
</script>

<style scoped>
.toolbar {
  margin-bottom: 4px;
}
</style>
