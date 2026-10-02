<template>
  <div class="clearance-page">
    <el-card shadow="never">
      <template #header>
        <div class="h">
          <span>🛡 涉密分级管控</span>
          <el-tag type="warning" size="small" style="margin-left:8px">安全保密管理员专属</el-tag>
        </div>
      </template>

      <el-alert type="info" :closable="false" style="margin-bottom:16px">
        <template #default>
          <strong>涉密分级说明：</strong>
          人员数据按密级分为 公开(0) / 内部(1) / 秘密(2) / 机密(3) 四个等级。
          用户的涉密等级（clearance_level）决定其可见的数据范围。
          低密级用户查看高密级数据时，敏感字段（身份证号、手机号、家庭住址等）将自动脱敏。
        </template>
      </el-alert>

      <el-table :data="users" size="small" stripe>
        <el-table-column prop="username" label="用户名" width="120" />
        <el-table-column prop="role" label="角色" width="120">
          <template #default="{ row }">
            <el-tag size="small">{{ roleLabel(row.role) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="当前涉密等级" width="140">
          <template #default="{ row }">
            <el-tag :type="levelTagType(row.clearance_level)" size="small">
              {{ row.clearance_name }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="设置涉密等级" width="280">
          <template #default="{ row }">
            <el-radio-group v-model="row.clearance_level" size="small" @change="setLevel(row)">
              <el-radio-button :value="0">公开</el-radio-button>
              <el-radio-button :value="1">内部</el-radio-button>
              <el-radio-button :value="2">秘密</el-radio-button>
              <el-radio-button :value="3">机密</el-radio-button>
            </el-radio-group>
          </template>
        </el-table-column>
        <el-table-column prop="is_active" label="账号状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">
              {{ row.is_active ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <template #empty><el-empty description="暂无用户" :image-size="60" /></template>
      </el-table>
    </el-card>

    <el-card shadow="never" style="margin-top:16px">
      <template #header><div class="h">📋 涉密等级说明</div></template>
      <el-table :data="levels" size="small" border>
        <el-table-column prop="level" label="等级值" width="80" align="center" />
        <el-table-column prop="name" label="名称" width="100" />
        <el-table-column prop="desc" label="说明" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { systemApi } from '@/api'
import { ElMessage } from 'element-plus'

const users = ref([])
const levels = ref([])

const roleLabel = (r) => ({
  super_admin: '超管', unit_admin: '单位管理员', dept_admin: '部门管理员',
  dept_leader: '部门领导', hr: '人事', finance: '财务', person: '普通员工',
  system_admin: '系统管理员', security_officer: '保密管理员', auditor: '审计员',
}[r] || r)

const levelTagType = (l) => ['', 'info', 'warning', 'danger'][l] || 'info'

const loadData = async () => {
  try {
    const [userData, levelData] = await Promise.all([
      systemApi.listUserClearance(),
      systemApi.clearanceLevels(),
    ])
    users.value = userData.items || []
    levels.value = levelData || []
  } catch (e) {
    ElMessage.error('加载失败')
  }
}

const setLevel = async (row) => {
  try {
    await systemApi.setUserClearance(row.id, row.clearance_level)
    ElMessage.success(`${row.username} 涉密等级已更新`)
    const names = ['公开', '内部', '秘密', '机密']
    row.clearance_name = names[row.clearance_level] || '未知'
  } catch (e) {
    ElMessage.error('设置失败')
    loadData()
  }
}

onMounted(loadData)
</script>

<style scoped>
.clearance-page { padding: 16px; }
.h { font-size: 15px; font-weight: 600; display: flex; align-items: center; }
</style>
