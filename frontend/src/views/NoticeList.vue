<template>
  <div class="page-container">
    <div class="section-title">通知公告</div>

    <el-card>
      <div class="toolbar">
        <el-radio-group v-model="categoryFilter" @change="onFilterChange">
          <el-radio-button label="">全部</el-radio-button>
          <el-radio-button label="notice">通知</el-radio-button>
          <el-radio-button label="announcement">公告</el-radio-button>
          <el-radio-button label="news">新闻</el-radio-button>
        </el-radio-group>
        <el-button @click="loadData">
          <el-icon><Refresh /></el-icon>刷新
        </el-button>
        <el-button type="warning" @click="onReadAll" :loading="readingAll">全部已读</el-button>
        <el-button v-if="auth.isAdmin" type="primary" @click="openCreate">
          <el-icon><Plus /></el-icon>发布通知
        </el-button>
      </div>

      <el-table :data="list" v-loading="loading" border stripe style="margin-top: 16px">
        <el-table-column label="" width="40" align="center">
          <template #default="{ row }">
            <span v-if="!row.is_read" class="unread-dot" title="未读"></span>
          </template>
        </el-table-column>
        <el-table-column label="标题" min-width="260">
          <template #default="{ row }">
            <el-tag v-if="row.is_top" type="danger" size="small" effect="dark" style="margin-right: 6px">置顶</el-tag>
            <el-link type="primary" @click="openDetail(row)">{{ row.title }}</el-link>
          </template>
        </el-table-column>
        <el-table-column label="分类" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="categoryType(row.category)" size="small">{{ categoryLabel(row.category) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="发布人" width="120">
          <template #default="{ row }">{{ row.author_name || row.publisher || '—' }}</template>
        </el-table-column>
        <el-table-column label="发布时间" width="170">
          <template #default="{ row }">{{ formatTime(row.published_at || row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.is_read" type="info" size="small">已读</el-tag>
            <el-tag v-else type="danger" size="small">未读</el-tag>
          </template>
        </el-table-column>
        <el-table-column v-if="auth.isAdmin" label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="onDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!loading && list.length === 0" description="暂无通知" />

      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next, jumper"
        style="margin-top: 16px; justify-content: flex-end"
        @current-change="loadData"
      />
    </el-card>

    <!-- 详情抽屉 -->
    <el-drawer v-model="detailVisible" title="通知详情" size="520px">
      <div v-if="detail" class="notice-detail">
        <div class="detail-title">
          <el-tag v-if="detail.is_top" type="danger" size="small" effect="dark">置顶</el-tag>
          <span>{{ detail.title }}</span>
        </div>
        <div class="detail-meta">
          <el-tag :type="categoryType(detail.category)" size="small">{{ categoryLabel(detail.category) }}</el-tag>
          <span>发布人：{{ detail.author_name || detail.publisher || '—' }}</span>
          <span>发布时间：{{ formatTime(detail.published_at || detail.created_at) }}</span>
        </div>
        <el-divider />
        <div class="detail-content">{{ detail.content }}</div>
      </div>
    </el-drawer>

    <!-- 发布/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="editing.id ? '编辑通知' : '发布通知'"
      width="600px"
      @closed="resetForm"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="标题" prop="title">
          <el-input v-model="form.title" placeholder="请输入通知标题" />
        </el-form-item>
        <el-form-item label="分类" prop="category">
          <el-select v-model="form.category" placeholder="请选择分类" style="width: 100%">
            <el-option label="通知" value="notice" />
            <el-option label="公告" value="announcement" />
            <el-option label="新闻" value="news" />
          </el-select>
        </el-form-item>
        <el-form-item label="内容" prop="content">
          <el-input v-model="form.content" type="textarea" :rows="6" placeholder="请输入通知内容" />
        </el-form-item>
        <el-form-item label="是否置顶">
          <el-switch v-model="form.is_top" />
        </el-form-item>
        <el-form-item label="是否发布">
          <el-switch v-model="form.is_published" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="onSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh } from '@element-plus/icons-vue'
import { noticeApi } from '@/api'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

const list = ref([])
const loading = ref(false)
const categoryFilter = ref('')
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const readingAll = ref(false)

const detailVisible = ref(false)
const detail = ref(null)

const dialogVisible = ref(false)
const saving = ref(false)
const formRef = ref(null)
const editing = reactive({ id: null })
const form = reactive({
  title: '',
  content: '',
  category: 'notice',
  is_top: false,
  is_published: true,
})
const rules = {
  title: [{ required: true, message: '请输入通知标题', trigger: 'blur' }],
  category: [{ required: true, message: '请选择分类', trigger: 'change' }],
  content: [{ required: true, message: '请输入通知内容', trigger: 'blur' }],
}

const categoryLabel = (c) => ({ notice: '通知', announcement: '公告', news: '新闻' }[c] || c || '通知')
const categoryType = (c) => ({ notice: 'primary', announcement: 'warning', news: 'success' }[c] || 'info')

const formatTime = (t) => {
  if (!t) return ''
  return String(t).replace('T', ' ').slice(0, 19)
}

const loadData = async () => {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
    if (categoryFilter.value) params.category = categoryFilter.value
    const res = await noticeApi.list(params)
    if (Array.isArray(res)) {
      list.value = res
      total.value = res.length
    } else {
      list.value = res.items || res.data || []
      total.value = res.total ?? list.value.length
    }
    // 置顶排前
    list.value.sort((a, b) => (b.is_top ? 1 : 0) - (a.is_top ? 1 : 0))
  } finally {
    loading.value = false
  }
}

const onFilterChange = () => {
  page.value = 1
  loadData()
}

const openDetail = async (row) => {
  detail.value = row
  detailVisible.value = true
  if (!row.is_read) {
    try {
      await noticeApi.read(row.id)
      row.is_read = true
    } catch (e) {
      // 忽略标记已读失败
    }
  }
}

const onReadAll = async () => {
  readingAll.value = true
  try {
    await noticeApi.readAll()
    ElMessage.success('已全部标记为已读')
    loadData()
  } finally {
    readingAll.value = false
  }
}

const resetForm = () => {
  editing.id = null
  form.title = ''
  form.content = ''
  form.category = 'notice'
  form.is_top = false
  form.is_published = true
  formRef.value?.clearValidate?.()
}

const openCreate = () => {
  resetForm()
  dialogVisible.value = true
}

const openEdit = (row) => {
  resetForm()
  editing.id = row.id
  form.title = row.title
  form.content = row.content || ''
  form.category = row.category || 'notice'
  form.is_top = !!row.is_top
  form.is_published = !!row.is_published
  dialogVisible.value = true
}

const onSave = async () => {
  await formRef.value?.validate?.()
  saving.value = true
  try {
    const payload = {
      title: form.title,
      content: form.content,
      category: form.category,
      is_top: form.is_top,
      is_published: form.is_published,
    }
    if (editing.id) {
      await noticeApi.update(editing.id, payload)
      ElMessage.success('修改成功')
    } else {
      await noticeApi.create(payload)
      ElMessage.success('发布成功')
    }
    dialogVisible.value = false
    loadData()
  } finally {
    saving.value = false
  }
}

const onDelete = (row) => {
  ElMessageBox.confirm(`确定删除通知「${row.title}」吗？此操作不可恢复。`, '删除确认', {
    type: 'warning',
    confirmButtonText: '确定删除',
    cancelButtonText: '取消',
  })
    .then(async () => {
      await noticeApi.delete(row.id)
      ElMessage.success('删除成功')
      loadData()
    })
    .catch(() => {})
}

onMounted(loadData)
</script>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
}
.toolbar .el-radio-group {
  margin-right: auto;
}
.unread-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #f56c6c;
}
.notice-detail .detail-title {
  font-size: 20px;
  font-weight: 600;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
  color: #303133;
}
.detail-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  color: #909399;
  font-size: 13px;
  align-items: center;
}
.detail-content {
  white-space: pre-wrap;
  line-height: 1.8;
  color: #303133;
  font-size: 14px;
}
</style>
