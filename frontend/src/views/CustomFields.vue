<template>
  <div class="page-container">
    <div class="section-title">自定义字段管理</div>

    <el-card>
      <div class="toolbar">
        <el-button type="primary" @click="openCreate">
          <el-icon><Plus /></el-icon>新增字段
        </el-button>
        <el-button @click="loadData">
          <el-icon><Refresh /></el-icon>刷新
        </el-button>
      </div>

      <el-table :data="list" v-loading="loading" border stripe style="margin-top: 16px">
        <el-table-column type="index" label="序号" width="60" align="center" />
        <el-table-column prop="field_key" label="字段Key" min-width="140" />
        <el-table-column prop="display_name" label="显示名" min-width="140" />
        <el-table-column label="类型" width="100" align="center">
          <template #default="{ row }">
            <el-tag size="small" type="info">{{ typeLabel(row.data_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="group_name" label="分组" width="120" align="center">
          <template #default="{ row }">{{ row.group_name || '—' }}</template>
        </el-table-column>
        <el-table-column prop="sort" label="排序" width="80" align="center" />
        <el-table-column label="必填" width="80" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.is_required" size="small" type="danger">必填</el-tag>
            <span v-else>—</span>
          </template>
        </el-table-column>
        <el-table-column label="启用" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
              {{ row.is_active ? '启用' : '停用' }}
            </el-tag>
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
      :title="editing.id ? '编辑字段' : '新增字段'"
      width="560px"
      @closed="resetForm"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="字段Key" prop="field_key">
          <el-input
            v-model="form.field_key"
            placeholder="英文标识，如 emergency_contact"
            :disabled="!!editing.id"
          />
        </el-form-item>
        <el-form-item label="显示名" prop="display_name">
          <el-input v-model="form.display_name" placeholder="中文显示名，如 紧急联系人" />
        </el-form-item>
        <el-form-item label="数据类型" prop="data_type">
          <el-select v-model="form.data_type" style="width: 100%">
            <el-option label="文本(text)" value="text" />
            <el-option label="数字(number)" value="number" />
            <el-option label="日期(date)" value="date" />
            <el-option label="下拉选择(select)" value="select" />
            <el-option label="多行文本(textarea)" value="textarea" />
          </el-select>
        </el-form-item>
        <el-form-item label="分组">
          <el-input v-model="form.group_name" placeholder="如 基本信息 / 联系方式" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="form.sort" :min="0" :max="9999" />
        </el-form-item>
        <el-form-item label="是否必填">
          <el-switch v-model="form.is_required" />
        </el-form-item>
        <el-form-item label="是否启用">
          <el-switch v-model="form.is_active" />
        </el-form-item>
        <el-form-item v-if="form.data_type === 'select'" label="选项">
          <div class="options-box">
            <div
              v-for="(opt, idx) in form.options"
              :key="idx"
              class="option-row"
            >
              <el-input
                v-model="form.options[idx]"
                placeholder="输入选项后回车添加"
                style="width: 320px"
                @keyup.enter="addOptionIfLast(idx)"
              />
              <el-button
                size="small"
                type="danger"
                link
                @click="removeOption(idx)"
              >
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
            <el-button size="small" type="primary" link @click="addOption">
              <el-icon><Plus /></el-icon>添加选项
            </el-button>
          </div>
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
import { Plus, Refresh, Delete } from '@element-plus/icons-vue'
import api from '@/api'

const list = ref([])
const loading = ref(false)

const dialogVisible = ref(false)
const saving = ref(false)
const formRef = ref(null)
const editing = reactive({ id: null })

const defaultForm = () => ({
  field_key: '',
  display_name: '',
  data_type: 'text',
  group_name: '',
  sort: 0,
  is_required: false,
  is_active: true,
  options: [],
})
const form = reactive(defaultForm())

const rules = {
  field_key: [
    { required: true, message: '请输入字段Key', trigger: 'blur' },
    { pattern: /^[a-zA-Z][a-zA-Z0-9_]*$/, message: '只能包含英文字母、数字和下划线，且以字母开头', trigger: 'blur' },
  ],
  display_name: [{ required: true, message: '请输入显示名', trigger: 'blur' }],
  data_type: [{ required: true, message: '请选择数据类型', trigger: 'change' }],
}

const typeLabel = (t) => {
  const m = { text: '文本', number: '数字', date: '日期', select: '下拉', textarea: '多行文本' }
  return m[t] || t || ''
}

const formatTime = (t) => (t ? String(t).replace('T', ' ').slice(0, 19) : '')

const loadData = async () => {
  loading.value = true
  try {
    list.value = await api.get('/custom-fields')
  } finally {
    loading.value = false
  }
}

const resetForm = () => {
  editing.id = null
  Object.assign(form, defaultForm())
  formRef.value?.clearValidate?.()
}

const openCreate = () => {
  resetForm()
  dialogVisible.value = true
}

const openEdit = (row) => {
  resetForm()
  editing.id = row.id
  Object.assign(form, {
    field_key: row.field_key,
    display_name: row.display_name,
    data_type: row.data_type,
    group_name: row.group_name || '',
    sort: row.sort ?? 0,
    is_required: !!row.is_required,
    is_active: !!row.is_active,
    options: Array.isArray(row.options) ? [...row.options] : [],
  })
  dialogVisible.value = true
}

const addOption = () => {
  form.options.push('')
}
const addOptionIfLast = (idx) => {
  if (idx === form.options.length - 1) addOption()
}
const removeOption = (idx) => {
  form.options.splice(idx, 1)
}

const onSave = async () => {
  await formRef.value?.validate?.()
  saving.value = true
  try {
    const payload = {
      field_key: form.field_key,
      display_name: form.display_name,
      data_type: form.data_type,
      group_name: form.group_name || null,
      sort: form.sort ?? 0,
      is_required: form.is_required,
      is_active: form.is_active,
      options: form.data_type === 'select' ? form.options.filter((o) => o && o.trim()) : null,
    }
    if (editing.id) {
      await api.put(`/custom-fields/${editing.id}`, payload)
      ElMessage.success('修改成功')
    } else {
      await api.post('/custom-fields', payload)
      ElMessage.success('新增成功')
    }
    dialogVisible.value = false
    loadData()
  } finally {
    saving.value = false
  }
}

const onDelete = (row) => {
  ElMessageBox.confirm(`确定删除字段「${row.display_name}」吗？已填写的数据可能受影响。`, '删除确认', {
    type: 'warning',
    confirmButtonText: '确定删除',
    cancelButtonText: '取消',
  })
    .then(async () => {
      await api.delete(`/custom-fields/${row.id}`)
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
.options-box {
  width: 100%;
}
.option-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
</style>
