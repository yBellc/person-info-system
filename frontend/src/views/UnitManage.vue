<template>
  <div class="page-container">
    <div class="section-title">单位管理</div>

    <el-card>
      <div class="toolbar">
        <el-button type="primary" @click="openCreate">
          <el-icon><Plus /></el-icon>新增单位
        </el-button>
        <el-button @click="loadData">
          <el-icon><Refresh /></el-icon>刷新
        </el-button>
      </div>

      <el-table :data="list" v-loading="loading" border stripe style="margin-top: 16px">
        <template #empty><el-empty description="暂无单位数据" :image-size="80" /></template>
        <el-table-column type="index" label="序号" width="60" align="center" />
        <el-table-column prop="name" label="名称" min-width="160" />
        <el-table-column prop="code" label="编码" width="140" />
        <el-table-column label="父单位" width="160">
          <template #default="{ row }">
            {{ parentName(row.parent_id) || '—' }}
          </template>
        </el-table-column>
        <el-table-column label="是否启用" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
              {{ row.is_active ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="onDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新增/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="editing.id ? '编辑单位' : '新增单位'"
      width="480px"
      @closed="resetForm"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入单位名称" />
        </el-form-item>
        <el-form-item label="编码" prop="code">
          <el-input v-model="form.code" placeholder="请输入单位编码" />
        </el-form-item>
        <el-form-item label="父单位" prop="parent_id">
          <el-select
            v-model="form.parent_id"
            placeholder="顶级单位可不选"
            clearable
            style="width: 100%"
          >
            <el-option
              v-for="u in parentOptions"
              :key="u.id"
              :label="u.name"
              :value="u.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="是否启用" prop="is_active">
          <el-switch v-model="form.is_active" />
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
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh } from '@element-plus/icons-vue'
import api from '@/api'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

const list = ref([])
const loading = ref(false)

const dialogVisible = ref(false)
const saving = ref(false)
const formRef = ref(null)
const editing = reactive({ id: null })
const form = reactive({
  name: '',
  code: '',
  parent_id: null,
  is_active: true,
})
const rules = {
  name: [{ required: true, message: '请输入单位名称', trigger: 'blur' }],
  code: [{ required: true, message: '请输入单位编码', trigger: 'blur' }],
}

const parentOptions = computed(() => list.value.filter((u) => u.id !== editing.id))

const parentName = (pid) => {
  const u = list.value.find((x) => x.id === pid)
  return u ? u.name : ''
}

const formatTime = (t) => {
  if (!t) return ''
  return String(t).replace('T', ' ').slice(0, 19)
}

const loadData = async () => {
  loading.value = true
  try {
    list.value = await api.get('/units')
  } finally {
    loading.value = false
  }
}

const resetForm = () => {
  editing.id = null
  form.name = ''
  form.code = ''
  form.parent_id = null
  form.is_active = true
  formRef.value?.clearValidate?.()
}

const openCreate = () => {
  resetForm()
  dialogVisible.value = true
}

const openEdit = (row) => {
  resetForm()
  editing.id = row.id
  form.name = row.name
  form.code = row.code
  form.parent_id = row.parent_id ?? null
  form.is_active = !!row.is_active
  dialogVisible.value = true
}

const onSave = async () => {
  await formRef.value?.validate?.()
  saving.value = true
  try {
    const payload = {
      name: form.name,
      code: form.code,
      parent_id: form.parent_id || null,
      is_active: form.is_active,
    }
    if (editing.id) {
      await api.put(`/units/${editing.id}`, payload)
      ElMessage.success('修改成功')
    } else {
      await api.post('/units', payload)
      ElMessage.success('新增成功')
    }
    dialogVisible.value = false
    loadData()
  } finally {
    saving.value = false
  }
}

const onDelete = (row) => {
  ElMessageBox.confirm(`确定删除单位「${row.name}」吗？此操作不可恢复。`, '删除确认', {
    type: 'warning',
    confirmButtonText: '确定删除',
    cancelButtonText: '取消',
  })
    .then(async () => {
      await api.delete(`/units/${row.id}`)
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
</style>
