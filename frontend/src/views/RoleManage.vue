<template>
  <div class="page-container role-manage">
    <div class="section-title">角色权限管理</div>

    <div class="role-layout">
      <!-- 左侧角色列表 -->
      <el-card class="role-list-card" shadow="never">
        <template #header>
          <div class="card-header">
            <span class="card-title">角色列表</span>
            <el-button type="primary" size="small" @click="openRoleCreate">
              <el-icon><Plus /></el-icon>新增角色
            </el-button>
          </div>
        </template>
        <el-table
          ref="roleTableRef"
          :data="roles"
          v-loading="rolesLoading"
          border
          stripe
          size="small"
          row-key="id"
          highlight-current-row
          max-height="640"
          @current-change="onRoleSelect"
        >
          <template #empty><el-empty description="暂无角色" :image-size="80" /></template>
          <el-table-column prop="name" label="角色名称" min-width="120" />
          <el-table-column prop="code" label="编码" width="140" />
          <el-table-column label="类型" width="70" align="center">
            <template #default="{ row }">
              <el-tag v-if="row.is_system" size="small" type="warning">内置</el-tag>
              <el-tag v-else size="small" type="info">自定义</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="70" align="center">
            <template #default="{ row }">
              <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
                {{ row.is_active ? '启用' : '停用' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="user_count" label="用户数" width="70" align="center" />
          <el-table-column label="操作" width="110" align="center" fixed="right">
            <template #default="{ row }">
              <el-button
                size="small"
                link
                type="primary"
                :disabled="row.is_system"
                @click.stop="openRoleEdit(row)"
              >编辑</el-button>
              <el-button
                size="small"
                link
                type="danger"
                :disabled="row.is_system"
                @click.stop="onRoleDelete(row)"
              >删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <!-- 右侧标签页 -->
      <el-card class="role-detail-card" shadow="never">
        <template #header>
          <div class="card-header">
            <span class="card-title">
              {{ currentRole
                ? `当前角色：${currentRole.name}（${currentRole.code}）`
                : '角色详情' }}
            </span>
          </div>
        </template>

        <el-empty v-if="!currentRole" description="请先在左侧选择一个角色" />

        <el-tabs v-else v-model="activeTab" class="detail-tabs">
          <!-- 角色信息 -->
          <el-tab-pane label="角色信息" name="info">
            <el-form :model="roleForm" label-width="100px" class="info-form">
              <el-form-item label="角色名称">
                <el-input v-model="roleForm.name" :disabled="currentRole.is_system" />
              </el-form-item>
              <el-form-item label="角色编码">
                <el-input v-model="roleForm.code" disabled />
              </el-form-item>
              <el-form-item label="描述">
                <el-input
                  v-model="roleForm.description"
                  type="textarea"
                  :rows="3"
                  :disabled="currentRole.is_system"
                  placeholder="角色职责描述"
                />
              </el-form-item>
              <el-form-item label="是否启用">
                <el-switch v-model="roleForm.is_active" :disabled="currentRole.is_system" />
              </el-form-item>
              <el-form-item label="系统内置">
                <el-tag :type="currentRole.is_system ? 'warning' : 'info'" size="small">
                  {{ currentRole.is_system ? '是' : '否' }}
                </el-tag>
              </el-form-item>
              <el-form-item v-if="!currentRole.is_system">
                <el-button type="primary" :loading="roleSaving" @click="saveRoleInfo">
                  保存修改
                </el-button>
              </el-form-item>
              <el-form-item v-else>
                <el-alert
                  type="warning"
                  :closable="false"
                  title="系统内置角色不可修改或删除"
                />
              </el-form-item>
            </el-form>
          </el-tab-pane>

          <!-- 数据权限 -->
          <el-tab-pane label="数据权限" name="data">
            <div class="toolbar">
              <el-button type="primary" size="small" @click="openDataCreate">
                <el-icon><Plus /></el-icon>新增数据权限
              </el-button>
              <el-button size="small" @click="loadDataPermissions">
                <el-icon><Refresh /></el-icon>刷新
              </el-button>
            </div>
            <el-table
              :data="dataPermissions"
              v-loading="dataLoading"
              border
              stripe
              size="small"
              style="margin-top: 12px"
            >
              <el-table-column type="index" label="序号" width="60" align="center" />
              <el-table-column prop="resource" label="资源" min-width="120" />
              <el-table-column label="权限范围" width="110" align="center">
                <template #default="{ row }">
                  <el-tag size="small">{{ scopeLabel(row.scope) }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="条件(JSON)" min-width="240">
                <template #default="{ row }">
                  <span class="conditions-text">{{ formatConditions(row.conditions) }}</span>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="130" align="center" fixed="right">
                <template #default="{ row }">
                  <el-button size="small" link type="primary" @click="openDataEdit(row)">编辑</el-button>
                  <el-button size="small" link type="danger" @click="onDataDelete(row)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>

          <!-- 字段权限 -->
          <el-tab-pane label="字段权限" name="field">
            <div class="toolbar">
              <el-button type="primary" size="small" @click="openFieldCreate">
                <el-icon><Plus /></el-icon>新增字段权限
              </el-button>
              <el-button size="small" @click="loadFieldPermissions">
                <el-icon><Refresh /></el-icon>刷新
              </el-button>
            </div>
            <el-table
              :data="fieldPermissions"
              v-loading="fieldLoading"
              border
              stripe
              size="small"
              style="margin-top: 12px"
            >
              <el-table-column type="index" label="序号" width="60" align="center" />
              <el-table-column prop="resource" label="资源" min-width="120" />
              <el-table-column prop="field_key" label="字段Key" min-width="140" />
              <el-table-column label="可读" width="90" align="center">
                <template #default="{ row }">
                  <el-switch
                    :model-value="row.can_read"
                    @change="(val) => toggleField(row, 'can_read', val)"
                  />
                </template>
              </el-table-column>
              <el-table-column label="可写" width="90" align="center">
                <template #default="{ row }">
                  <el-switch
                    :model-value="row.can_write"
                    @change="(val) => toggleField(row, 'can_write', val)"
                  />
                </template>
              </el-table-column>
              <el-table-column label="操作" width="90" align="center" fixed="right">
                <template #default="{ row }">
                  <el-button size="small" link type="danger" @click="onFieldDelete(row)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>

          <!-- 用户分配 -->
          <el-tab-pane label="用户分配" name="users">
            <div class="toolbar">
              <el-button type="primary" size="small" @click="openAssignUser">
                <el-icon><Plus /></el-icon>分配用户
              </el-button>
              <el-button size="small" @click="loadUserRoles">
                <el-icon><Refresh /></el-icon>刷新
              </el-button>
            </div>
            <el-table
              :data="userRoles"
              v-loading="userRolesLoading"
              border
              stripe
              size="small"
              style="margin-top: 12px"
            >
              <el-table-column type="index" label="序号" width="60" align="center" />
              <el-table-column prop="user_id" label="用户ID" width="80" align="center" />
              <el-table-column label="用户名" min-width="140">
                <template #default="{ row }">{{ userNameOf(row.user_id) }}</template>
              </el-table-column>
              <el-table-column label="分配时间" width="180">
                <template #default="{ row }">{{ formatTime(row.granted_at) }}</template>
              </el-table-column>
              <el-table-column label="过期时间" width="180">
                <template #default="{ row }">{{ formatTime(row.expires_at) }}</template>
              </el-table-column>
              <el-table-column label="操作" width="110" align="center" fixed="right">
                <template #default="{ row }">
                  <el-button size="small" link type="danger" @click="onUnassignUser(row)">取消分配</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>
        </el-tabs>
      </el-card>
    </div>

    <!-- 角色新增/编辑对话框 -->
    <el-dialog
      v-model="roleDialogVisible"
      :title="roleEditing.id ? '编辑角色' : '新增角色'"
      width="480px"
      @closed="resetRoleForm"
    >
      <el-form ref="roleFormRef" :model="roleDialogForm" :rules="roleRules" label-width="90px">
        <el-form-item label="角色名称" prop="name">
          <el-input v-model="roleDialogForm.name" placeholder="请输入角色名称" />
        </el-form-item>
        <el-form-item label="角色编码" prop="code">
          <el-input
            v-model="roleDialogForm.code"
            placeholder="英文标识，如 hr_manager"
            :disabled="!!roleEditing.id"
          />
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="roleDialogForm.description"
            type="textarea"
            :rows="3"
            placeholder="可选"
          />
        </el-form-item>
        <el-form-item label="是否启用">
          <el-switch v-model="roleDialogForm.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="roleDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="roleSaving" @click="saveRoleDialog">保存</el-button>
      </template>
    </el-dialog>

    <!-- 数据权限对话框 -->
    <el-dialog
      v-model="dataDialogVisible"
      :title="dataEditing.id ? '编辑数据权限' : '新增数据权限'"
      width="560px"
      @closed="resetDataForm"
    >
      <el-form ref="dataFormRef" :model="dataDialogForm" :rules="dataRules" label-width="100px">
        <el-form-item label="资源" prop="resource">
          <el-select
            v-model="dataDialogForm.resource"
            filterable
            allow-create
            default-first-option
            style="width: 100%"
            placeholder="选择或输入资源名称"
          >
            <el-option v-for="r in resourceOptions" :key="r.value" :label="r.label" :value="r.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="权限范围" prop="scope">
          <el-select v-model="dataDialogForm.scope" style="width: 100%">
            <el-option v-for="s in scopeOptions" :key="s.value" :label="s.label" :value="s.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="条件(JSON)">
          <el-input
            v-model="dataDialogForm.conditionsText"
            type="textarea"
            :rows="5"
            placeholder='如 {"unit_id": 1}，留空表示无条件'
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dataDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="dataSaving" @click="saveDataDialog">保存</el-button>
      </template>
    </el-dialog>

    <!-- 字段权限对话框 -->
    <el-dialog
      v-model="fieldDialogVisible"
      title="新增字段权限"
      width="500px"
      @closed="resetFieldForm"
    >
      <el-form ref="fieldFormRef" :model="fieldDialogForm" :rules="fieldRules" label-width="100px">
        <el-form-item label="资源" prop="resource">
          <el-select
            v-model="fieldDialogForm.resource"
            filterable
            allow-create
            default-first-option
            style="width: 100%"
            placeholder="选择或输入资源名称"
          >
            <el-option v-for="r in resourceOptions" :key="r.value" :label="r.label" :value="r.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="字段Key" prop="field_key">
          <el-input v-model="fieldDialogForm.field_key" placeholder="如 name / id_card" />
        </el-form-item>
        <el-form-item label="可读">
          <el-switch v-model="fieldDialogForm.can_read" />
        </el-form-item>
        <el-form-item label="可写">
          <el-switch v-model="fieldDialogForm.can_write" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="fieldDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="fieldSaving" @click="saveFieldDialog">保存</el-button>
      </template>
    </el-dialog>

    <!-- 用户分配对话框 -->
    <el-dialog v-model="assignDialogVisible" title="分配用户" width="480px">
      <el-form label-width="80px">
        <el-form-item label="角色">
          <el-input :model-value="currentRole?.name" disabled />
        </el-form-item>
        <el-form-item label="用户">
          <el-select
            v-model="assignForm.user_id"
            filterable
            placeholder="选择用户"
            style="width: 100%"
          >
            <el-option
              v-for="u in availableUsers"
              :key="u.id"
              :label="u.username"
              :value="u.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="assignDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="assignSaving" @click="submitAssign">确认分配</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh } from '@element-plus/icons-vue'
import api, { roleApi, userRoleApi, dataPermissionApi, fieldPermissionApi } from '@/api'

// ============ 角色列表 ============
const roles = ref([])
const rolesLoading = ref(false)
const currentRole = ref(null)
const roleTableRef = ref()

const loadRoles = async () => {
  rolesLoading.value = true
  try {
    roles.value = await roleApi.list()
    // 重新加载后保持当前行高亮
    if (currentRole.value) {
      const updated = roles.value.find((r) => r.id === currentRole.value.id)
      if (updated) {
        currentRole.value = updated
        syncRoleForm()
        roleTableRef.value?.setCurrentRow(updated)
      }
    }
  } finally {
    rolesLoading.value = false
  }
}

const onRoleSelect = (row) => {
  if (!row) return
  currentRole.value = row
  activeTab.value = 'info'
  syncRoleForm()
  loadAllDetail()
}

// ============ 右侧 Tabs ============
const activeTab = ref('info')

const loadAllDetail = () => {
  loadDataPermissions()
  loadFieldPermissions()
  loadUserRoles()
}

// ============ 角色信息（内联编辑） ============
const roleForm = reactive({
  name: '',
  code: '',
  description: '',
  is_active: true,
})
const roleSaving = ref(false)

const syncRoleForm = () => {
  const r = currentRole.value
  if (!r) return
  roleForm.name = r.name
  roleForm.code = r.code
  roleForm.description = r.description || ''
  roleForm.is_active = !!r.is_active
}

const saveRoleInfo = async () => {
  if (!currentRole.value) return
  roleSaving.value = true
  try {
    await roleApi.update(currentRole.value.id, {
      name: roleForm.name,
      description: roleForm.description || null,
      is_active: roleForm.is_active,
    })
    ElMessage.success('保存成功')
    await loadRoles()
  } finally {
    roleSaving.value = false
  }
}

// ============ 角色新增/编辑对话框 ============
const roleDialogVisible = ref(false)
const roleEditing = reactive({ id: null })
const roleFormRef = ref()
const roleDialogForm = reactive({
  name: '',
  code: '',
  description: '',
  is_active: true,
})
const roleRules = {
  name: [{ required: true, message: '请输入角色名称', trigger: 'blur' }],
  code: [
    { required: true, message: '请输入角色编码', trigger: 'blur' },
    {
      pattern: /^[a-zA-Z][a-zA-Z0-9_]*$/,
      message: '只能包含英文字母、数字和下划线，且以字母开头',
      trigger: 'blur',
    },
  ],
}

const resetRoleForm = () => {
  roleEditing.id = null
  Object.assign(roleDialogForm, { name: '', code: '', description: '', is_active: true })
  roleFormRef.value?.clearValidate?.()
}

const openRoleCreate = () => {
  resetRoleForm()
  roleDialogVisible.value = true
}

const openRoleEdit = (row) => {
  resetRoleForm()
  roleEditing.id = row.id
  Object.assign(roleDialogForm, {
    name: row.name,
    code: row.code,
    description: row.description || '',
    is_active: !!row.is_active,
  })
  roleDialogVisible.value = true
}

const saveRoleDialog = async () => {
  await roleFormRef.value?.validate?.()
  roleSaving.value = true
  try {
    if (roleEditing.id) {
      // 编辑时不可修改 code
      await roleApi.update(roleEditing.id, {
        name: roleDialogForm.name,
        description: roleDialogForm.description || null,
        is_active: roleDialogForm.is_active,
      })
      ElMessage.success('修改成功')
    } else {
      await roleApi.create({
        name: roleDialogForm.name,
        code: roleDialogForm.code,
        description: roleDialogForm.description || null,
        is_active: roleDialogForm.is_active,
      })
      ElMessage.success('新增成功')
    }
    roleDialogVisible.value = false
    await loadRoles()
  } finally {
    roleSaving.value = false
  }
}

const onRoleDelete = (row) => {
  ElMessageBox.confirm(
    `确定删除角色「${row.name}」吗？已分配用户的角色无法删除。`,
    '删除确认',
    { type: 'warning', confirmButtonText: '确定删除', cancelButtonText: '取消' },
  )
    .then(async () => {
      await roleApi.delete(row.id)
      ElMessage.success('删除成功')
      if (currentRole.value?.id === row.id) {
        currentRole.value = null
      }
      loadRoles()
    })
    .catch(() => {})
}

// ============ 数据权限 ============
const dataPermissions = ref([])
const dataLoading = ref(false)
const dataDialogVisible = ref(false)
const dataSaving = ref(false)
const dataFormRef = ref()
const dataEditing = reactive({ id: null })
const dataDialogForm = reactive({
  resource: '',
  scope: 'self',
  conditionsText: '',
})
const dataRules = {
  resource: [{ required: true, message: '请选择资源', trigger: 'change' }],
  scope: [{ required: true, message: '请选择权限范围', trigger: 'change' }],
}

const resourceOptions = [
  { label: '人员(persons)', value: 'persons' },
  { label: '合同(contracts)', value: 'contracts' },
  { label: '请假(leaves)', value: 'leaves' },
  { label: '单位(units)', value: 'units' },
  { label: '部门(departments)', value: 'departments' },
  { label: '报表(reports)', value: 'reports' },
]
const scopeOptions = [
  { label: '全部(all)', value: 'all' },
  { label: '本单位(unit)', value: 'unit' },
  { label: '本部门(department)', value: 'department' },
  { label: '仅本人(self)', value: 'self' },
]

const scopeLabel = (s) => {
  const m = { all: '全部', unit: '本单位', department: '本部门', self: '仅本人' }
  return m[s] || s
}

const loadDataPermissions = async () => {
  if (!currentRole.value) return
  dataLoading.value = true
  try {
    dataPermissions.value = await dataPermissionApi.list({ role_id: currentRole.value.id })
  } finally {
    dataLoading.value = false
  }
}

const resetDataForm = () => {
  dataEditing.id = null
  Object.assign(dataDialogForm, { resource: '', scope: 'self', conditionsText: '' })
  dataFormRef.value?.clearValidate?.()
}

const openDataCreate = () => {
  resetDataForm()
  dataDialogVisible.value = true
}

const openDataEdit = (row) => {
  resetDataForm()
  dataEditing.id = row.id
  Object.assign(dataDialogForm, {
    resource: row.resource,
    scope: row.scope,
    conditionsText: row.conditions ? JSON.stringify(row.conditions, null, 2) : '',
  })
  dataDialogVisible.value = true
}

const parseConditions = () => {
  const text = (dataDialogForm.conditionsText || '').trim()
  if (!text) return null
  try {
    return JSON.parse(text)
  } catch (e) {
    throw new Error('条件 JSON 格式错误：' + e.message)
  }
}

const formatConditions = (c) => {
  if (!c) return '—'
  try {
    return JSON.stringify(c)
  } catch {
    return String(c)
  }
}

const saveDataDialog = async () => {
  await dataFormRef.value?.validate?.()
  let conditions
  try {
    conditions = parseConditions()
  } catch (e) {
    ElMessage.error(e.message)
    return
  }
  dataSaving.value = true
  try {
    if (dataEditing.id) {
      await dataPermissionApi.update(dataEditing.id, {
        resource: dataDialogForm.resource,
        scope: dataDialogForm.scope,
        conditions,
      })
      ElMessage.success('修改成功')
    } else {
      await dataPermissionApi.create({
        role_id: currentRole.value.id,
        resource: dataDialogForm.resource,
        scope: dataDialogForm.scope,
        conditions,
      })
      ElMessage.success('新增成功')
    }
    dataDialogVisible.value = false
    loadDataPermissions()
  } finally {
    dataSaving.value = false
  }
}

const onDataDelete = (row) => {
  ElMessageBox.confirm('确定删除该数据权限规则吗？', '删除确认', {
    type: 'warning',
    confirmButtonText: '确定删除',
    cancelButtonText: '取消',
  })
    .then(async () => {
      await dataPermissionApi.delete(row.id)
      ElMessage.success('删除成功')
      loadDataPermissions()
    })
    .catch(() => {})
}

// ============ 字段权限 ============
const fieldPermissions = ref([])
const fieldLoading = ref(false)
const fieldDialogVisible = ref(false)
const fieldSaving = ref(false)
const fieldFormRef = ref()
const fieldDialogForm = reactive({
  resource: '',
  field_key: '',
  can_read: true,
  can_write: false,
})
const fieldRules = {
  resource: [{ required: true, message: '请选择资源', trigger: 'change' }],
  field_key: [{ required: true, message: '请输入字段Key', trigger: 'blur' }],
}

const loadFieldPermissions = async () => {
  if (!currentRole.value) return
  fieldLoading.value = true
  try {
    fieldPermissions.value = await fieldPermissionApi.list({ role_id: currentRole.value.id })
  } finally {
    fieldLoading.value = false
  }
}

const resetFieldForm = () => {
  Object.assign(fieldDialogForm, {
    resource: '',
    field_key: '',
    can_read: true,
    can_write: false,
  })
  fieldFormRef.value?.clearValidate?.()
}

const openFieldCreate = () => {
  resetFieldForm()
  fieldDialogVisible.value = true
}

const saveFieldDialog = async () => {
  await fieldFormRef.value?.validate?.()
  fieldSaving.value = true
  try {
    await fieldPermissionApi.create({
      role_id: currentRole.value.id,
      resource: fieldDialogForm.resource,
      field_key: fieldDialogForm.field_key,
      can_read: fieldDialogForm.can_read,
      can_write: fieldDialogForm.can_write,
    })
    ElMessage.success('新增成功')
    fieldDialogVisible.value = false
    loadFieldPermissions()
  } finally {
    fieldSaving.value = false
  }
}

const toggleField = async (row, key, val) => {
  try {
    await fieldPermissionApi.update(row.id, { [key]: val })
    row[key] = val
    ElMessage.success('已更新')
  } catch {
    // 失败由响应拦截器统一提示，开关自动回退
  }
}

const onFieldDelete = (row) => {
  ElMessageBox.confirm(
    `确定删除字段「${row.field_key}」的权限吗？`,
    '删除确认',
    { type: 'warning', confirmButtonText: '确定删除', cancelButtonText: '取消' },
  )
    .then(async () => {
      await fieldPermissionApi.delete(row.id)
      ElMessage.success('删除成功')
      loadFieldPermissions()
    })
    .catch(() => {})
}

// ============ 用户分配 ============
const userRoles = ref([])
const userRolesLoading = ref(false)
const users = ref([])
const assignDialogVisible = ref(false)
const assignSaving = ref(false)
const assignForm = reactive({ user_id: null })

const availableUsers = computed(() => {
  const assignedIds = new Set(userRoles.value.map((u) => u.user_id))
  return users.value.filter((u) => !assignedIds.has(u.id))
})

const loadUsers = async () => {
  try {
    users.value = await api.get('/auth/unit-admins')
  } catch {
    users.value = []
  }
}

const loadUserRoles = async () => {
  if (!currentRole.value) return
  userRolesLoading.value = true
  try {
    userRoles.value = await userRoleApi.list({ role_id: currentRole.value.id })
  } finally {
    userRolesLoading.value = false
  }
}

const userNameOf = (uid) => {
  const u = users.value.find((x) => x.id === uid)
  return u ? u.username : `用户#${uid}`
}

const openAssignUser = () => {
  assignForm.user_id = null
  assignDialogVisible.value = true
}

const submitAssign = async () => {
  if (!assignForm.user_id) {
    ElMessage.warning('请选择用户')
    return
  }
  assignSaving.value = true
  try {
    await userRoleApi.create({
      user_id: assignForm.user_id,
      role_id: currentRole.value.id,
    })
    ElMessage.success('分配成功')
    assignDialogVisible.value = false
    loadUserRoles()
    loadRoles()
  } finally {
    assignSaving.value = false
  }
}

const onUnassignUser = (row) => {
  ElMessageBox.confirm('确定取消该用户的角色分配吗？', '取消分配确认', {
    type: 'warning',
    confirmButtonText: '确定',
    cancelButtonText: '取消',
  })
    .then(async () => {
      await userRoleApi.delete(row.id)
      ElMessage.success('已取消分配')
      loadUserRoles()
      loadRoles()
    })
    .catch(() => {})
}

// ============ 工具 ============
const formatTime = (t) => {
  if (!t) return '—'
  return String(t).replace('T', ' ').slice(0, 19)
}

onMounted(() => {
  loadRoles()
  loadUsers()
})
</script>

<style scoped>
.role-layout {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}
.role-list-card {
  width: 600px;
  flex-shrink: 0;
}
.role-detail-card {
  flex: 1;
  min-width: 0;
}
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.card-title {
  font-weight: 600;
}
.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
}
.info-form {
  max-width: 540px;
}
.conditions-text {
  word-break: break-all;
  color: #666;
}
.detail-tabs {
  margin-top: 4px;
}
</style>
