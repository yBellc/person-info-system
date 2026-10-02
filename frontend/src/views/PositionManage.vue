<template>
  <div class="page-container">
    <div class="section-title">岗位管理</div>

    <el-card>
      <!-- 搜索栏 -->
      <div class="toolbar">
        <el-input
          v-model="searchName"
          placeholder="按岗位名称搜索"
          clearable
          style="width: 220px"
          @keyup.enter="currentPage = 1"
        />
        <el-select
          v-model="filterCategory"
          placeholder="按类别筛选"
          clearable
          style="width: 180px"
          @change="currentPage = 1"
        >
          <el-option
            v-for="opt in categoryOptions"
            :key="opt"
            :label="opt"
            :value="opt"
          />
        </el-select>
        <el-button type="primary" @click="openCreate">
          <el-icon><Plus /></el-icon>新增岗位
        </el-button>
        <el-button @click="loadData">
          <el-icon><Refresh /></el-icon>刷新
        </el-button>
      </div>

      <!-- 列表 -->
      <el-table :data="pagedList" v-loading="loading" border stripe style="margin-top: 16px">
        <el-table-column type="index" label="序号" width="60" align="center" :index="indexFrom" />
        <el-table-column prop="name" label="岗位名称" min-width="160" />
        <el-table-column prop="code" label="编码" width="140" />
        <el-table-column label="类别" width="140" align="center">
          <template #default="{ row }">
            <el-tag :type="categoryTagType(row.category)" size="small">
              {{ row.category || '—' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="是否领导岗" width="110" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_leadership ? 'danger' : 'info'" size="small">
              {{ row.is_leadership ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
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

      <!-- 分页 -->
      <div class="pager">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50]"
          :total="filteredList.length"
          layout="total, sizes, prev, pager, next, jumper"
          background
        />
      </div>
    </el-card>

    <!-- 新增/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="editing.id ? '编辑岗位' : '新增岗位'"
      width="520px"
      @closed="resetForm"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="岗位名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入岗位名称" />
        </el-form-item>
        <el-form-item label="编码" prop="code">
          <el-input v-model="form.code" placeholder="请输入岗位编码" />
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
        <el-form-item label="是否领导岗" prop="is_leadership">
          <el-switch v-model="form.is_leadership" />
        </el-form-item>
        <el-form-item label="状态" prop="is_active">
          <el-switch v-model="form.is_active" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="3"
            placeholder="请输入岗位描述（选填）"
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
import { positionApi } from '@/api'

// 岗位类别选项
const categoryOptions = ['管理岗', '专业技术岗', '工勤技能岗']

// 类别对应标签颜色
const categoryTagType = (category) => {
  switch (category) {
    case '管理岗':
      return 'primary'
    case '专业技术岗':
      return 'success'
    case '工勤技能岗':
      return 'warning'
    default:
      return 'info'
  }
}

const list = ref([])
const loading = ref(false)

// 搜索与筛选
const searchName = ref('')
const filterCategory = ref('')

// 分页
const currentPage = ref(1)
const pageSize = ref(10)

// 过滤后的列表（按名称 + 类别）
const filteredList = computed(() => {
  const kw = searchName.value.trim().toLowerCase()
  const cat = filterCategory.value
  return list.value.filter((item) => {
    const matchName = !kw || String(item.name || '').toLowerCase().includes(kw)
    const matchCat = !cat || item.category === cat
    return matchName && matchCat
  })
})

// 当前页数据
const pagedList = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return filteredList.value.slice(start, start + pageSize.value)
})

// 分页序号续接
const indexFrom = (index) => (currentPage.value - 1) * pageSize.value + index + 1

// 对话框
const dialogVisible = ref(false)
const saving = ref(false)
const formRef = ref(null)
const editing = reactive({ id: null })
const form = reactive({
  name: '',
  code: '',
  category: '',
  is_leadership: false,
  is_active: true,
  description: '',
})
const rules = {
  name: [{ required: true, message: '请输入岗位名称', trigger: 'blur' }],
  code: [{ required: true, message: '请输入岗位编码', trigger: 'blur' }],
  category: [{ required: true, message: '请选择岗位类别', trigger: 'change' }],
}

const loadData = async () => {
  loading.value = true
  try {
    const res = await positionApi.list()
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
  form.is_leadership = false
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
  form.is_leadership = !!row.is_leadership
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
      is_leadership: form.is_leadership,
      is_active: form.is_active,
      description: form.description || null,
    }
    if (editing.id) {
      await positionApi.update(editing.id, payload)
      ElMessage.success('修改成功')
    } else {
      await positionApi.create(payload)
      ElMessage.success('新增成功')
    }
    dialogVisible.value = false
    loadData()
  } finally {
    saving.value = false
  }
}

const onDelete = (row) => {
  ElMessageBox.confirm(`确定删除岗位「${row.name}」吗？此操作不可恢复。`, '删除确认', {
    type: 'warning',
    confirmButtonText: '确定删除',
    cancelButtonText: '取消',
  })
    .then(async () => {
      await positionApi.delete(row.id)
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
.pager {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
