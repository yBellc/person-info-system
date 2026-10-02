<template>
  <div class="page-container">
    <div class="section-title">职级管理</div>

    <el-card>
      <!-- 工具栏 -->
      <div class="toolbar">
        <el-button type="primary" @click="openCreate">
          <el-icon><Plus /></el-icon>新增职级
        </el-button>
        <el-button @click="loadData">
          <el-icon><Refresh /></el-icon>刷新
        </el-button>
        <span class="hint">列表按等级升序排列</span>
      </div>

      <!-- 列表 -->
      <el-table :data="sortedList" v-loading="loading" border stripe style="margin-top: 16px">
        <el-table-column type="index" label="序号" width="60" align="center" />
        <el-table-column prop="name" label="职级名称" min-width="160" />
        <el-table-column prop="code" label="编码" width="140" />
        <el-table-column label="类别" width="120" align="center">
          <template #default="{ row }">
            <el-tag :type="categoryTagType(row.category)" size="small">
              {{ row.category || '—' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="level" label="等级" width="100" align="center" sortable />
        <el-table-column label="状态" width="100" align="center">
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
      :title="editing.id ? '编辑职级' : '新增职级'"
      width="520px"
      @closed="resetForm"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="职级名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入职级名称" />
        </el-form-item>
        <el-form-item label="编码" prop="code">
          <el-input v-model="form.code" placeholder="请输入职级编码" />
        </el-form-item>
        <el-form-item label="类别" prop="category">
          <el-select v-model="form.category" placeholder="请选择类别" style="width: 100%">
            <el-option
              v-for="opt in categoryOptions"
              :key="opt"
              :label="opt"
              :value="opt"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="等级" prop="level">
          <el-input-number
            v-model="form.level"
            :min="1"
            :max="15"
            :step="1"
            controls-position="right"
            style="width: 160px"
          />
          <span class="hint" style="margin-left: 8px">取值范围 1-15</span>
        </el-form-item>
        <el-form-item label="状态" prop="is_active">
          <el-switch v-model="form.is_active" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="3"
            placeholder="请输入职级描述（选填）"
          />
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
import { rankApi } from '@/api'

// 职级类别选项
const categoryOptions = ['管理岗', '技术岗', '工勤岗']

// 类别对应标签颜色
const categoryTagType = (category) => {
  switch (category) {
    case '管理岗':
      return 'primary'
    case '技术岗':
      return 'success'
    case '工勤岗':
      return 'warning'
    default:
      return 'info'
  }
}

const list = ref([])
const loading = ref(false)

// 按 level 升序排列
const sortedList = computed(() => {
  return [...list.value].sort((a, b) => {
    const la = Number(a.level ?? 0)
    const lb = Number(b.level ?? 0)
    return la - lb
  })
})

// 对话框
const dialogVisible = ref(false)
const saving = ref(false)
const formRef = ref(null)
const editing = reactive({ id: null })
const form = reactive({
  name: '',
  code: '',
  category: '',
  level: 1,
  is_active: true,
  description: '',
})
const rules = {
  name: [{ required: true, message: '请输入职级名称', trigger: 'blur' }],
  code: [{ required: true, message: '请输入职级编码', trigger: 'blur' }],
  category: [{ required: true, message: '请选择职级类别', trigger: 'change' }],
  level: [
    { required: true, message: '请输入等级', trigger: 'blur' },
    {
      type: 'number',
      min: 1,
      max: 15,
      message: '等级范围 1-15',
      trigger: 'blur',
    },
  ],
}

const loadData = async () => {
  loading.value = true
  try {
    const res = await rankApi.list()
    list.value = Array.isArray(res) ? res : (res?.items ?? [])
  } finally {
    loading.value = false
  }
}

const resetForm = () => {
  editing.id = null
  form.name = ''
  form.code = ''
  form.category = ''
  form.level = 1
  form.is_active = true
  form.description = ''
  formRef.value?.clearValidate?.()
}

const openCreate = () => {
  resetForm()
  dialogVisible.value = true
}

const openEdit = (row) => {
  resetForm()
  editing.id = row.id
  form.name = row.name ?? ''
  form.code = row.code ?? ''
  form.category = row.category ?? ''
  form.level = Number(row.level ?? 1)
  form.is_active = !!row.is_active
  form.description = row.description ?? ''
  dialogVisible.value = true
}

const onSave = async () => {
  await formRef.value?.validate?.()
  saving.value = true
  try {
    const payload = {
      name: form.name,
      code: form.code,
      category: form.category,
      level: Number(form.level),
      is_active: form.is_active,
      description: form.description || null,
    }
    if (editing.id) {
      await rankApi.update(editing.id, payload)
      ElMessage.success('修改成功')
    } else {
      await rankApi.create(payload)
      ElMessage.success('新增成功')
    }
    dialogVisible.value = false
    loadData()
  } finally {
    saving.value = false
  }
}

const onDelete = (row) => {
  ElMessageBox.confirm(`确定删除职级「${row.name}」吗？此操作不可恢复。`, '删除确认', {
    type: 'warning',
    confirmButtonText: '确定删除',
    cancelButtonText: '取消',
  })
    .then(async () => {
      await rankApi.delete(row.id)
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
  flex-wrap: wrap;
}
.hint {
  color: #909399;
  font-size: 13px;
}
</style>
