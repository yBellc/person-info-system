<template>
  <div class="page-container">
    <div class="section-title">待办事项</div>

    <el-card>
      <div class="toolbar">
        <el-radio-group v-model="statusFilter" @change="loadData">
          <el-radio-button label="all">全部</el-radio-button>
          <el-radio-button label="pending">待办</el-radio-button>
          <el-radio-button label="done">已完成</el-radio-button>
          <el-radio-button label="expired">已过期</el-radio-button>
        </el-radio-group>
        <el-button @click="loadData">
          <el-icon><Refresh /></el-icon>刷新
        </el-button>
        <el-button type="primary" @click="openCreate">
          <el-icon><Plus /></el-icon>新增待办
        </el-button>
      </div>

      <el-table :data="list" v-loading="loading" border stripe style="margin-top: 16px">
        <el-table-column type="index" label="序号" width="60" align="center" />
        <el-table-column label="标题" min-width="180">
          <template #default="{ row }">
            <span :class="{ 'todo-done-text': displayStatus(row) === 'done' }">{{ row.title }}</span>
          </template>
        </el-table-column>
        <el-table-column label="内容摘要" min-width="220">
          <template #default="{ row }">
            <span class="todo-summary">{{ row.content || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="分类" width="110" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.category" size="small" type="info">{{ row.category }}</el-tag>
            <span v-else>—</span>
          </template>
        </el-table-column>
        <el-table-column label="优先级" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="priorityType(row.priority)" size="small">{{ priorityLabel(row.priority) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="截止日期" width="120" align="center">
          <template #default="{ row }">{{ formatDate(row.due_date) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="statusType(displayStatus(row))" size="small">{{ statusLabel(displayStatus(row)) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="displayStatus(row) !== 'done'"
              size="small"
              type="success"
              @click="onComplete(row)"
            >完成</el-button>
            <el-button size="small" type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="onDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!loading && list.length === 0" description="暂无待办" />
    </el-card>

    <!-- 新增/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="editing.id ? '编辑待办' : '新增待办'"
      width="560px"
      @closed="resetForm"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="标题" prop="title">
          <el-input v-model="form.title" placeholder="请输入待办标题" />
        </el-form-item>
        <el-form-item label="分类" prop="category">
          <el-input v-model="form.category" placeholder="请输入分类（选填）" />
        </el-form-item>
        <el-form-item label="优先级" prop="priority">
          <el-select v-model="form.priority" placeholder="请选择优先级" style="width: 100%">
            <el-option label="普通" :value="0" />
            <el-option label="重要" :value="1" />
            <el-option label="紧急" :value="2" />
          </el-select>
        </el-form-item>
        <el-form-item label="截止日期" prop="due_date">
          <el-date-picker
            v-model="form.due_date"
            type="date"
            placeholder="请选择截止日期"
            value-format="YYYY-MM-DD"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="内容" prop="content">
          <el-input v-model="form.content" type="textarea" :rows="4" placeholder="请输入待办内容（选填）" />
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
import { todoApi } from '@/api'

const list = ref([])
const loading = ref(false)
const statusFilter = ref('all')

const dialogVisible = ref(false)
const saving = ref(false)
const formRef = ref(null)
const editing = reactive({ id: null })
const form = reactive({
  title: '',
  content: '',
  category: '',
  priority: 0,
  due_date: '',
})
const rules = {
  title: [{ required: true, message: '请输入待办标题', trigger: 'blur' }],
  priority: [{ required: true, message: '请选择优先级', trigger: 'change' }],
}

const priorityLabel = (p) => ({ 0: '普通', 1: '重要', 2: '紧急' }[p] ?? '普通')
const priorityType = (p) => ({ 0: 'info', 1: 'warning', 2: 'danger' }[p] ?? 'info')

const statusLabel = (s) => ({ pending: '待办', done: '已完成', expired: '已过期' }[s] || s)
const statusType = (s) => ({ pending: 'primary', done: 'success', expired: 'danger' }[s] || 'info')

const formatDate = (t) => (t ? String(t).replace('T', ' ').slice(0, 10) : '—')

// 计算展示状态：已完成 / 已过期 / 待办
const displayStatus = (row) => {
  if (row.status === 'done') return 'done'
  if (row.due_date) {
    const today = new Date()
    const due = new Date(row.due_date)
    due.setHours(23, 59, 59, 999)
    if (due < today) return 'expired'
  }
  return 'pending'
}

// 按优先级（紧急在前）和截止日期（早的在前）排序
const sortTodos = (arr) => {
  arr.sort((a, b) => {
    if (b.priority !== a.priority) return b.priority - a.priority
    const ad = a.due_date ? new Date(a.due_date).getTime() : Number.MAX_SAFE_INTEGER
    const bd = b.due_date ? new Date(b.due_date).getTime() : Number.MAX_SAFE_INTEGER
    return ad - bd
  })
}

const loadData = async () => {
  loading.value = true
  try {
    const res = await todoApi.list()
    let arr = Array.isArray(res) ? res : (res.items || res.data || [])
    if (statusFilter.value !== 'all') {
      arr = arr.filter((t) => displayStatus(t) === statusFilter.value)
    }
    sortTodos(arr)
    list.value = arr
  } finally {
    loading.value = false
  }
}

const resetForm = () => {
  editing.id = null
  form.title = ''
  form.content = ''
  form.category = ''
  form.priority = 0
  form.due_date = ''
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
  form.category = row.category || ''
  form.priority = row.priority ?? 0
  form.due_date = row.due_date ? String(row.due_date).slice(0, 10) : ''
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
      priority: form.priority,
      due_date: form.due_date || null,
    }
    if (editing.id) {
      await todoApi.update(editing.id, payload)
      ElMessage.success('修改成功')
    } else {
      await todoApi.create(payload)
      ElMessage.success('新增成功')
    }
    dialogVisible.value = false
    loadData()
  } finally {
    saving.value = false
  }
}

const onComplete = (row) => {
  ElMessageBox.confirm(`确定将待办「${row.title}」标记为已完成吗？`, '完成确认', {
    type: 'success',
    confirmButtonText: '确定完成',
    cancelButtonText: '取消',
  })
    .then(async () => {
      await todoApi.complete(row.id)
      ElMessage.success('已完成')
      loadData()
    })
    .catch(() => {})
}

const onDelete = (row) => {
  ElMessageBox.confirm(`确定删除待办「${row.title}」吗？此操作不可恢复。`, '删除确认', {
    type: 'warning',
    confirmButtonText: '确定删除',
    cancelButtonText: '取消',
  })
    .then(async () => {
      await todoApi.delete(row.id)
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
.todo-summary {
  color: #606266;
  font-size: 13px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.todo-done-text {
  text-decoration: line-through;
  color: #909399;
}
</style>
