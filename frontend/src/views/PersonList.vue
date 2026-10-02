<template>
  <div class="page-container">
    <div class="section-title">人员管理</div>

    <el-card>
      <!-- 搜索栏 -->
      <div class="toolbar">
        <el-input
          v-model="keyword"
          placeholder="搜索姓名/身份证号"
          style="width: 280px"
          clearable
          @keyup.enter="loadData"
          @clear="loadData"
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-select
          v-if="auth.isAdmin"
          v-model="unitFilter"
          placeholder="筛选单位"
          style="width: 180px; margin-left: 12px"
          clearable
          @change="loadData"
        >
          <el-option v-for="u in unitTreeOptions" :key="u.id" :label="u.displayName" :value="u.id" />
        </el-select>
        <el-button type="primary" @click="loadData" style="margin-left: 12px">
          <el-icon><Search /></el-icon>查询
        </el-button>
        <el-button type="success" @click="openCreate">
          <el-icon><Plus /></el-icon>新增人员
        </el-button>
      </div>

      <!-- 列表 -->
      <el-table :data="list" v-loading="loading" border stripe style="margin-top: 16px">
        <template #empty><el-empty description="暂无人员数据" :image-size="80" /></template>
        <el-table-column type="index" label="序号" width="60" align="center" />
        <el-table-column prop="name" label="姓名" width="80" />
        <el-table-column prop="gender" label="性别" width="60" align="center" />
        <el-table-column prop="age" label="年龄" width="60" align="center" />
        <el-table-column prop="id_card_masked" label="身份证号" width="200" />
        <el-table-column prop="unit_name" label="所在单位" width="120" v-if="auth.isSuperAdmin" />
        <el-table-column prop="department" label="部门" width="100" />
        <el-table-column prop="position" label="职务" width="100" />
        <el-table-column prop="education_level" label="学历" width="80" align="center" />
        <el-table-column prop="phone" label="联系电话" width="130" />
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="$router.push(`/persons/${row.id}`)">详情</el-button>
            <el-button size="small" type="primary" @click="openEdit(row)">编辑</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next, jumper"
        style="margin-top: 16px; justify-content: flex-end"
        @current-change="loadData"
      />
    </el-card>

    <!-- 新增/编辑对话框 -->
    <person-form-dialog
      v-model:visible="formVisible"
      :person="editingPerson"
      :units="units"
      @saved="onSaved"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/api'
import { useAuthStore } from '@/stores/auth'
import PersonFormDialog from '@/components/PersonFormDialog.vue'

const auth = useAuthStore()

const list = ref([])
const loading = ref(false)
const keyword = ref('')
const unitFilter = ref(null)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const units = ref([])

const formVisible = ref(false)
const editingPerson = ref(null)

const loadData = async () => {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
    if (keyword.value) params.keyword = keyword.value
    if (unitFilter.value) params.unit_id = unitFilter.value
    list.value = await api.get('/persons', { params })
    const c = await api.get('/persons/count')
    total.value = c.total
  } finally {
    loading.value = false
  }
}

// 层级化的单位选项（父单位在前，子单位缩进显示）
const unitTreeOptions = computed(() => {
  const list = units.value
  if (!list.length) return []
  const byParent = {}
  list.forEach((u) => {
    const pid = u.parent_id || 0
    if (!byParent[pid]) byParent[pid] = []
    byParent[pid].push(u)
  })
  const result = []
  const walk = (parentId, depth) => {
    const children = byParent[parentId] || []
    children.forEach((u) => {
      result.push({ ...u, displayName: (depth > 0 ? '┣ ' + '─'.repeat(depth * 2) + ' ' : '') + u.name })
      walk(u.id, depth + 1)
    })
  }
  walk(0, 0)
  return result
})

const loadUnits = async () => {
  if (auth.isSuperAdmin) {
    units.value = await api.get('/units')
  } else if (auth.isAdmin) {
    // 单位管理员也加载单位列表用于筛选下属单位
    units.value = await api.get('/units')
  }
}

const openCreate = () => {
  editingPerson.value = null
  formVisible.value = true
}
const openEdit = (row) => {
  editingPerson.value = row
  formVisible.value = true
}
const onSaved = () => {
  formVisible.value = false
  loadData()
  ElMessage.success('保存成功')
}

onMounted(() => {
  loadData()
  loadUnits()
})
</script>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
}
</style>
