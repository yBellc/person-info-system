<template>
  <div class="operation-logs-page">
    <!-- 统计卡片 -->
    <el-row :gutter="16" class="stats-row">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-value">{{ stats.operation_logs_total || 0 }}</div>
            <div class="stat-label">操作日志总数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-value">{{ stats.operation_logs_today || 0 }}</div>
            <div class="stat-label">今日操作数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card stat-success">
          <div class="stat-content">
            <div class="stat-value">{{ stats.login_success_today || 0 }}</div>
            <div class="stat-label">今日登录成功</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card stat-danger">
          <div class="stat-content">
            <div class="stat-value">{{ stats.login_failed_today || 0 }}</div>
            <div class="stat-label">今日登录失败</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Tab 切换 -->
    <el-tabs v-model="activeTab" class="logs-tabs">
      <!-- 操作日志 -->
      <el-tab-pane label="操作日志" name="operation">
        <el-card shadow="never">
          <el-form :inline="true" class="filter-form">
            <el-form-item label="操作人">
              <el-input v-model="opFilter.operator_name" placeholder="用户名" clearable style="width: 140px" />
            </el-form-item>
            <el-form-item label="操作类型">
              <el-select v-model="opFilter.action" placeholder="全部" clearable style="width: 160px">
                <el-option v-for="a in actionTypes" :key="a" :label="a" :value="a" />
              </el-select>
            </el-form-item>
            <el-form-item label="日期范围">
              <el-date-picker
                v-model="opFilter.dateRange"
                type="daterange"
                range-separator="至"
                start-placeholder="开始"
                end-placeholder="结束"
                value-format="YYYY-MM-DD"
                style="width: 240px"
              />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="loadOpLogs">查询</el-button>
              <el-button @click="resetOpFilter">重置</el-button>
            </el-form-item>
          </el-form>

          <el-table :data="opLogs" v-loading="opLoading" stripe style="width: 100%">
            <el-table-column prop="created_at" label="时间" width="160" />
            <el-table-column prop="operator_name" label="操作人" width="120" />
            <el-table-column prop="action" label="类型" width="140">
              <template #default="{ row }">
                <el-tag :type="getActionTagType(row.action)" size="small">{{ row.action }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="ip_address" label="IP" width="130" />
            <el-table-column prop="target_type" label="目标" width="100" />
            <el-table-column prop="detail" label="详情" show-overflow-tooltip min-width="200" />
            <el-table-column label="变更" width="80">
              <template #default="{ row }">
                <el-button v-if="row.old_value || row.new_value" link type="primary" @click="showDiff(row)">
                  查看
                </el-button>
                <span v-else class="text-muted">-</span>
              </template>
            </el-table-column>
          </el-table>

          <el-pagination
            v-model:current-page="opFilter.page"
            v-model:page-size="opFilter.size"
            :total="opTotal"
            :page-sizes="[20, 50, 100]"
            layout="total, sizes, prev, pager, next"
            class="pagination"
            @size-change="loadOpLogs"
            @current-change="loadOpLogs"
          />
        </el-card>
      </el-tab-pane>

      <!-- 登录日志 -->
      <el-tab-pane label="登录日志" name="login">
        <el-card shadow="never">
          <el-form :inline="true" class="filter-form">
            <el-form-item label="用户名">
              <el-input v-model="loginFilter.username" placeholder="用户名" clearable style="width: 140px" />
            </el-form-item>
            <el-form-item label="状态">
              <el-select v-model="loginFilter.success" placeholder="全部" clearable style="width: 120px">
                <el-option label="成功" :value="true" />
                <el-option label="失败" :value="false" />
              </el-select>
            </el-form-item>
            <el-form-item label="日期范围">
              <el-date-picker
                v-model="loginFilter.dateRange"
                type="daterange"
                range-separator="至"
                start-placeholder="开始"
                end-placeholder="结束"
                value-format="YYYY-MM-DD"
                style="width: 240px"
              />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="loadLoginLogs">查询</el-button>
              <el-button @click="resetLoginFilter">重置</el-button>
            </el-form-item>
          </el-form>

          <el-table :data="loginLogs" v-loading="loginLoading" stripe style="width: 100%">
            <el-table-column prop="login_time" label="登录时间" width="160" />
            <el-table-column prop="username" label="用户名" width="120" />
            <el-table-column prop="ip_address" label="IP地址" width="140" />
            <el-table-column label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="row.success ? 'success' : 'danger'" size="small">
                  {{ row.success ? '成功' : '失败' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="fail_reason" label="失败原因" show-overflow-tooltip min-width="200" />
            <el-table-column prop="logout_time" label="登出时间" width="160" />
          </el-table>

          <el-pagination
            v-model:current-page="loginFilter.page"
            v-model:page-size="loginFilter.size"
            :total="loginTotal"
            :page-sizes="[20, 50, 100]"
            layout="total, sizes, prev, pager, next"
            class="pagination"
            @size-change="loadLoginLogs"
            @current-change="loadLoginLogs"
          />
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <!-- 变更对比对话框 -->
    <el-dialog v-model="diffVisible" title="变更详情" width="700px">
      <el-row :gutter="16">
        <el-col :span="12">
          <h4 style="color: #f56c6c">变更前</h4>
          <pre class="diff-content">{{ formatJSON(diffData.old_value) }}</pre>
        </el-col>
        <el-col :span="12">
          <h4 style="color: #67c23a">变更后</h4>
          <pre class="diff-content">{{ formatJSON(diffData.new_value) }}</pre>
        </el-col>
      </el-row>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { systemApi } from '@/api'

const activeTab = ref('operation')
const stats = ref({})

// 操作日志
const opLoading = ref(false)
const opLogs = ref([])
const opTotal = ref(0)
const opFilter = reactive({
  page: 1,
  size: 20,
  operator_name: '',
  action: '',
  dateRange: null,
})

const actionTypes = [
  'login', 'logout', 'register', 'change_password', 'first_login_change_pwd',
  'create', 'update', 'delete', 'transfer', 'export',
  'create_unit_admin', 'toggle_admin', 'reset_admin_pwd',
  'apply_admin', 'approve_admin', 'reject_admin',
  'hr_create_account', 'hr_batch_create', 'hr_reset_password',
  'generate_report', 'backup_database', 'delete_backup', 'clean_logs',
]

const getActionTagType = (action) => {
  if (['login', 'register', 'create'].includes(action)) return 'success'
  if (['delete', 'reject_admin', 'reset_admin_pwd'].includes(action)) return 'danger'
  if (['change_password', 'update', 'transfer', 'toggle_admin'].includes(action)) return 'warning'
  if (['backup_database', 'clean_logs'].includes(action)) return 'info'
  return ''
}

const loadOpLogs = async () => {
  opLoading.value = true
  try {
    const params = {
      page: opFilter.page,
      size: opFilter.size,
      operator_name: opFilter.operator_name || undefined,
      action: opFilter.action || undefined,
      start_date: opFilter.dateRange?.[0] || undefined,
      end_date: opFilter.dateRange?.[1] || undefined,
    }
    const data = await systemApi.operationLogs(params)
    opLogs.value = data.items
    opTotal.value = data.total
  } finally {
    opLoading.value = false
  }
}

const resetOpFilter = () => {
  opFilter.operator_name = ''
  opFilter.action = ''
  opFilter.dateRange = null
  opFilter.page = 1
  loadOpLogs()
}

// 登录日志
const loginLoading = ref(false)
const loginLogs = ref([])
const loginTotal = ref(0)
const loginFilter = reactive({
  page: 1,
  size: 20,
  username: '',
  success: null,
  dateRange: null,
})

const loadLoginLogs = async () => {
  loginLoading.value = true
  try {
    const params = {
      page: loginFilter.page,
      size: loginFilter.size,
      username: loginFilter.username || undefined,
      success: loginFilter.success ?? undefined,
      start_date: loginFilter.dateRange?.[0] || undefined,
      end_date: loginFilter.dateRange?.[1] || undefined,
    }
    const data = await systemApi.loginLogs(params)
    loginLogs.value = data.items
    loginTotal.value = data.total
  } finally {
    loginLoading.value = false
  }
}

const resetLoginFilter = () => {
  loginFilter.username = ''
  loginFilter.success = null
  loginFilter.dateRange = null
  loginFilter.page = 1
  loadLoginLogs()
}

// 变更对比
const diffVisible = ref(false)
const diffData = ref({})
const showDiff = (row) => {
  diffData.value = { old_value: row.old_value, new_value: row.new_value }
  diffVisible.value = true
}
const formatJSON = (val) => {
  if (!val) return '(无)'
  if (typeof val === 'string') {
    try { return JSON.stringify(JSON.parse(val), null, 2) } catch { return val }
  }
  return JSON.stringify(val, null, 2)
}

const loadStats = async () => {
  try {
    stats.value = await systemApi.logsStats()
  } catch {}
}

onMounted(() => {
  loadStats()
  loadOpLogs()
  loadLoginLogs()
})
</script>

<style scoped>
.operation-logs-page {
  padding: 16px;
}
.stats-row {
  margin-bottom: 16px;
}
.stat-card {
  border-left: 4px solid #2d5a27;
}
.stat-card.stat-success {
  border-left-color: #67c23a;
}
.stat-card.stat-danger {
  border-left-color: #f56c6c;
}
.stat-content {
  text-align: center;
}
.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #2d5a27;
}
.stat-success .stat-value { color: #67c23a; }
.stat-danger .stat-value { color: #f56c6c; }
.stat-label {
  font-size: 13px;
  color: #909399;
  margin-top: 4px;
}
.logs-tabs {
  margin-top: 8px;
}
.filter-form {
  margin-bottom: 12px;
}
.pagination {
  margin-top: 16px;
  justify-content: flex-end;
}
.diff-content {
  background: #f5f7fa;
  padding: 12px;
  border-radius: 4px;
  font-size: 12px;
  max-height: 300px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
}
.text-muted {
  color: #c0c4cc;
}
</style>
