<template>
  <div class="page-container">
    <div class="section-title">人员名单</div>

    <el-card>
      <el-alert
        type="info"
        :closable="false"
        show-icon
        style="margin-bottom: 16px"
        title="导入名单后，员工凭姓名+身份证号可自助注册，填写个人档案信息。"
      />

      <!-- 单位选择 -->
      <div class="toolbar">
        <span class="label">选择单位：</span>
        <el-select
          v-if="auth.isSuperAdmin"
          v-model="unitId"
          placeholder="请选择单位"
          style="width: 240px"
          @change="loadRoster"
        >
          <el-option v-for="u in units" :key="u.id" :label="u.name" :value="u.id" />
        </el-select>
        <span v-else class="readonly-unit">{{ currentUnitName || '本单位' }}</span>
        <el-button @click="loadRoster" style="margin-left: 12px">
          <el-icon><Refresh /></el-icon>刷新
        </el-button>
        <el-button type="success" :disabled="!unitId" @click="openImport">
          <el-icon><Upload /></el-icon>批量导入名单
        </el-button>
      </div>

      <!-- 名单列表 -->
      <el-table :data="list" v-loading="loading" border stripe style="margin-top: 16px">
        <el-table-column type="index" label="序号" width="60" align="center" />
        <el-table-column prop="name" label="姓名" width="120" />
        <el-table-column label="身份证号" min-width="200">
          <template #default="{ row }">
            {{ maskIdCard(row.id_card) }}
          </template>
        </el-table-column>
        <el-table-column label="是否已注册" width="120" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_registered ? 'success' : 'info'" size="small">
              {{ row.is_registered ? '已注册' : '未注册' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="danger" @click="onDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 批量导入对话框 -->
    <el-dialog
      v-model="importVisible"
      title="批量导入名单"
      width="640px"
      @closed="resetImport"
    >
      <el-alert
        type="warning"
        :closable="false"
        show-icon
        style="margin-bottom: 12px"
        title="请录入姓名和身份证号。重复或格式错误的身份证号可能影响员工注册。"
      />
      <div class="toolbar" style="margin-bottom: 8px">
        <el-button type="primary" size="small" @click="addRow">
          <el-icon><Plus /></el-icon>新增一行
        </el-button>
        <el-button size="small" @click="clearRows">清空</el-button>
        <span class="hint">共 {{ importRows.length }} 条</span>
      </div>
      <el-table :data="importRows" border stripe max-height="360">
        <el-table-column type="index" label="#" width="50" align="center" />
        <el-table-column label="姓名" min-width="120">
          <template #default="{ row }">
            <el-input v-model="row.name" placeholder="姓名" />
          </template>
        </el-table-column>
        <el-table-column label="身份证号" min-width="200">
          <template #default="{ row }">
            <el-input v-model="row.id_card" placeholder="身份证号" maxlength="18" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="90" align="center">
          <template #default="{ $index }">
            <el-button size="small" type="danger" link @click="removeRow($index)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="importVisible = false">取消</el-button>
        <el-button type="primary" :loading="importing" @click="onSaveImport">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh, Upload } from '@element-plus/icons-vue'
import api from '@/api'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

const list = ref([])
const loading = ref(false)
const units = ref([])

// 超管可选单位；单位管理员固定本单位
const unitId = ref(auth.isSuperAdmin ? null : auth.user?.unit_id || null)

const currentUnitName = computed(() => {
  const u = units.value.find((x) => x.id === unitId.value)
  return u ? u.name : ''
})

const importVisible = ref(false)
const importing = ref(false)
const importRows = ref([])

const maskIdCard = (id) => {
  if (!id) return ''
  const s = String(id)
  if (s.length <= 8) return s
  return s.slice(0, 4) + '********' + s.slice(-4)
}

const loadUnits = async () => {
  if (auth.isSuperAdmin) {
    units.value = await api.get('/units')
  }
}

const loadRoster = async () => {
  if (!unitId.value) {
    list.value = []
    return
  }
  loading.value = true
  try {
    list.value = await api.get(`/units/${unitId.value}/roster`)
  } finally {
    loading.value = false
  }
}

const openImport = () => {
  resetImport()
  importRows.value = [{ name: '', id_card: '' }]
  importVisible.value = true
}

const resetImport = () => {
  importRows.value = []
}

const addRow = () => {
  importRows.value.push({ name: '', id_card: '' })
}

const removeRow = (idx) => {
  importRows.value.splice(idx, 1)
}

const clearRows = () => {
  importRows.value = []
}

const onSaveImport = async () => {
  const items = importRows.value
    .map((r) => ({ name: (r.name || '').trim(), id_card: (r.id_card || '').trim() }))
    .filter((r) => r.name && r.id_card)
  if (items.length === 0) {
    ElMessage.warning('请至少录入一条有效的姓名+身份证号')
    return
  }
  // 基本校验
  const bad = items.find((r) => r.id_card.length < 15)
  if (bad) {
    ElMessage.warning(`「${bad.name}」的身份证号长度不正确`)
    return
  }
  importing.value = true
  try {
    const res = await api.post(`/units/${unitId.value}/roster`, { items })
    const msg = typeof res === 'object' && res !== null && 'imported' in res
      ? `成功导入 ${res.imported} 条`
      : '导入成功'
    ElMessage.success(msg)
    importVisible.value = false
    loadRoster()
  } finally {
    importing.value = false
  }
}

const onDelete = (row) => {
  ElMessageBox.confirm(`确定删除名单「${row.name}」吗？`, '删除确认', {
    type: 'warning',
    confirmButtonText: '确定删除',
    cancelButtonText: '取消',
  })
    .then(async () => {
      await api.delete(`/units/roster/${row.id}`)
      ElMessage.success('删除成功')
      loadRoster()
    })
    .catch(() => {})
}

onMounted(async () => {
  await loadUnits()
  if (!auth.isSuperAdmin || unitId.value) {
    await loadRoster()
  }
})
</script>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
}
.toolbar .label {
  color: #606266;
  font-size: 14px;
}
.readonly-unit {
  font-weight: 600;
  color: #303133;
}
.hint {
  margin-left: 8px;
  color: #909399;
  font-size: 13px;
}
</style>
