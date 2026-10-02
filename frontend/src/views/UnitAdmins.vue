<template>
  <div class="page-container">
    <div class="section-title">单位管理员账号</div>

    <el-card>
      <div class="toolbar">
        <el-alert
          type="info"
          :closable="false"
          style="flex: 1"
          title="单位管理员由超级管理员创建，负责管理本单位的人员信息、名单导入、统计报表等。一个单位可设置多个管理员。"
        />
        <el-button type="primary" @click="openCreate">
          <el-icon><Plus /></el-icon>创建管理员
        </el-button>
      </div>

      <el-table :data="list" v-loading="loading" border stripe style="margin-top: 16px">
        <el-table-column type="index" label="序号" width="60" align="center" />
        <el-table-column prop="username" label="用户名" width="160" />
        <el-table-column prop="unit_name" label="管理单位" width="160" />
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">
              {{ row.is_active ? '启用' : '已停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="openResetPwd(row)">重置密码</el-button>
            <el-button
              size="small"
              :type="row.is_active ? 'warning' : 'success'"
              @click="toggleStatus(row)"
            >
              {{ row.is_active ? '停用' : '启用' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 创建管理员对话框 -->
    <el-dialog v-model="createVisible" title="创建单位管理员" width="460px">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="90px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" placeholder="登录用户名" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" placeholder="至少6位" show-password />
        </el-form-item>
        <el-form-item label="管理单位" prop="unit_id">
          <el-select v-model="form.unit_id" placeholder="选择单位" style="width: 100%">
            <el-option v-for="u in units" :key="u.id" :label="u.name" :value="u.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitCreate">创建</el-button>
      </template>
    </el-dialog>

    <!-- 重置密码对话框 -->
    <el-dialog v-model="resetVisible" title="重置密码" width="400px">
      <el-form label-width="80px">
        <el-form-item label="账号">
          <el-input :model-value="resetTarget?.username" disabled />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input v-model="newPwd" type="password" placeholder="至少6位" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="resetVisible = false">取消</el-button>
        <el-button type="primary" @click="submitReset">确认重置</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/api'

const list = ref([])
const units = ref([])
const loading = ref(false)
const createVisible = ref(false)
const saving = ref(false)
const formRef = ref()
const form = reactive({ username: '', password: '', unit_id: null })
const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '至少6位', trigger: 'blur' },
  ],
  unit_id: [{ required: true, message: '请选择单位', trigger: 'change' }],
}

const resetVisible = ref(false)
const resetTarget = ref(null)
const newPwd = ref('')

const loadData = async () => {
  loading.value = true
  try {
    list.value = await api.get('/auth/unit-admins')
  } finally {
    loading.value = false
  }
}

const loadUnits = async () => {
  units.value = await api.get('/units')
}

const formatTime = (t) => {
  if (!t) return ''
  return new Date(t).toLocaleString('zh-CN')
}

const openCreate = () => {
  form.username = ''
  form.password = ''
  form.unit_id = null
  createVisible.value = true
}

const submitCreate = async () => {
  await formRef.value.validate()
  saving.value = true
  try {
    await api.post('/auth/unit-admins', { ...form })
    ElMessage.success('创建成功')
    createVisible.value = false
    loadData()
  } finally {
    saving.value = false
  }
}

const openResetPwd = (row) => {
  resetTarget.value = row
  newPwd.value = ''
  resetVisible.value = true
}

const submitReset = async () => {
  if (!newPwd.value || newPwd.value.length < 6) {
    ElMessage.warning('密码至少6位')
    return
  }
  await api.put(`/auth/unit-admins/${resetTarget.value.id}/reset-password`, null, {
    params: { new_password: newPwd.value },
  })
  ElMessage.success('密码已重置')
  resetVisible.value = false
}

const toggleStatus = async (row) => {
  const action = row.is_active ? '停用' : '启用'
  try {
    await ElMessageBox.confirm(`确定要${action}账号 "${row.username}" 吗？`, '确认', { type: 'warning' })
    await api.put(`/auth/unit-admins/${row.id}/toggle`)
    ElMessage.success(`已${action}`)
    loadData()
  } catch (e) {
    // 取消
  }
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
  gap: 12px;
}
</style>
