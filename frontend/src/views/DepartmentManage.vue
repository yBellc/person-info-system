<template>
  <div class="page-container">
    <div class="section-title">部门管理</div>

    <el-card>
      <div class="toolbar">
        <el-input
          v-model="keyword"
          placeholder="按名称 / 编码搜索"
          clearable
          style="width: 260px"
          :prefix-icon="Search"
        />
        <div class="toolbar-right">
          <el-button @click="loadData">
            <el-icon><Refresh /></el-icon>刷新
          </el-button>
          <el-button type="primary" @click="openCreate">
            <el-icon><Plus /></el-icon>新增部门
          </el-button>
        </div>
      </div>

      <el-table
        :data="filteredTree"
        v-loading="loading"
        row-key="id"
        :tree-props="{ children: 'children', hasChildren: 'hasChildren' }"
        default-expand-all
        border
        stripe
        style="margin-top: 16px"
      >
        <template #empty><el-empty description="暂无部门数据" :image-size="80" /></template>
        <el-table-column prop="name" label="名称" min-width="200" />
        <el-table-column prop="code" label="编码" width="140" />
        <el-table-column prop="level" label="层级" width="80" align="center" />
        <el-table-column label="负责人" width="140">
          <template #default="{ row }">
            {{ row.manager_id ? row.manager_id : '—' }}
          </template>
        </el-table-column>
        <el-table-column prop="sort" label="排序" width="80" align="center" />
        <el-table-column label="状态" width="90" align="center">
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
      :title="editing.id ? '编辑部门' : '新增部门'"
      width="520px"
      @closed="resetForm"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入部门名称" />
        </el-form-item>
        <el-form-item label="编码" prop="code">
          <el-input v-model="form.code" placeholder="请输入部门编码" />
        </el-form-item>
        <el-form-item label="父部门" prop="parent_id">
          <el-tree-select
            v-model="form.parent_id"
            :data="parentTreeData"
            :props="{ label: 'name', children: 'children' }"
            node-key="id"
            placeholder="顶级部门可不选"
            check-strictly
            clearable
            :render-after-expand="false"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="负责人" prop="manager_id">
          <el-input
            v-model="form.manager_id"
            placeholder="请输入负责人ID（暂时手动填写）"
          />
        </el-form-item>
        <el-form-item label="层级" prop="level">
          <el-input-number v-model="form.level" :min="1" :max="99" controls-position="right" />
        </el-form-item>
        <el-form-item label="排序" prop="sort">
          <el-input-number v-model="form.sort" :min="0" :max="9999" controls-position="right" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="2"
            placeholder="请输入部门描述（选填）"
          />
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
import { Plus, Refresh, Search } from '@element-plus/icons-vue'
import { departmentApi } from '@/api'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

const treeData = ref([])
const loading = ref(false)
const keyword = ref('')

const dialogVisible = ref(false)
const saving = ref(false)
const formRef = ref(null)
const editing = reactive({ id: null })
const form = reactive({
  name: '',
  code: '',
  parent_id: null,
  manager_id: '',
  level: 1,
  sort: 0,
  description: '',
  is_active: true,
})
const rules = {
  name: [{ required: true, message: '请输入部门名称', trigger: 'blur' }],
}

// 关键字过滤树：保留命中节点及其祖先
const filteredTree = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  if (!kw) return treeData.value
  const walk = (nodes) => {
    const result = []
    for (const n of nodes) {
      const children = n.children ? walk(n.children) : []
      const match =
        (n.name && String(n.name).toLowerCase().includes(kw)) ||
        (n.code && String(n.code).toLowerCase().includes(kw))
      if (match || children.length) {
        result.push({ ...n, children })
      }
    }
    return result
  }
  return walk(treeData.value)
})

// 父部门树选项：编辑时排除自身及其子孙，避免循环引用
const parentTreeData = computed(() => {
  if (!editing.id) return treeData.value
  const removeSelf = (nodes) => {
    const result = []
    for (const n of nodes) {
      if (n.id === editing.id) continue
      const children = n.children ? removeSelf(n.children) : undefined
      result.push(children ? { ...n, children } : { ...n })
    }
    return result
  }
  return removeSelf(treeData.value)
})

const loadData = async () => {
  loading.value = true
  try {
    const unitId = auth.user?.unit_id
    treeData.value = await departmentApi.tree(unitId)
  } finally {
    loading.value = false
  }
}

const resetForm = () => {
  editing.id = null
  form.name = ''
  form.code = ''
  form.parent_id = null
  form.manager_id = ''
  form.level = 1
  form.sort = 0
  form.description = ''
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
  form.name = row.name ?? ''
  form.code = row.code ?? ''
  form.parent_id = row.parent_id ?? null
  form.manager_id = row.manager_id ?? ''
  form.level = row.level ?? 1
  form.sort = row.sort ?? 0
  form.description = row.description ?? ''
  form.is_active = !!row.is_active
  dialogVisible.value = true
}

const onSave = async () => {
  await formRef.value?.validate?.()
  saving.value = true
  try {
    const payload = {
      name: form.name,
      code: form.code || null,
      parent_id: form.parent_id || null,
      manager_id: form.manager_id ? Number(form.manager_id) : null,
      level: form.level,
      sort: form.sort,
      description: form.description || null,
      is_active: form.is_active,
    }
    if (editing.id) {
      await departmentApi.update(editing.id, payload)
      ElMessage.success('修改成功')
    } else {
      await departmentApi.create(payload)
      ElMessage.success('新增成功')
    }
    dialogVisible.value = false
    loadData()
  } finally {
    saving.value = false
  }
}

const onDelete = (row) => {
  ElMessageBox.confirm(
    `确定删除部门「${row.name}」吗？删除后该部门将不再可用。`,
    '删除确认',
    {
      type: 'warning',
      confirmButtonText: '确定删除',
      cancelButtonText: '取消',
    }
  )
    .then(async () => {
      await departmentApi.delete(row.id)
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
  justify-content: space-between;
  gap: 12px;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}
</style>
