<template>
  <div class="dashboard-page">
    <!-- 顶部欢迎条 -->
    <div class="welcome-bar">
      <div class="welcome-left">
        <span class="hello">{{ greeting }}，{{ userName }}</span>
        <el-tag :type="roleTagType" size="small" effect="dark" class="role-tag">{{ roleLabel }}</el-tag>
      </div>
      <div class="welcome-right">
        <span class="date-text">{{ todayStr }}</span>
      </div>
    </div>

    <!-- 第一行：通知公告（所有角色可见，置顶显示） -->
    <el-card shadow="never" class="notice-card">
      <template #header>
        <div class="h">
          <span class="h-icon" style="color:#f56c6c">📢</span>&nbsp;通知公告
          <el-tag v-if="notices.length > 0" type="danger" size="small" effect="plain" style="margin-left:8px">
            {{ notices.length }} 条
          </el-tag>
          <el-button v-if="notices.length > 0" type="primary" link size="small" style="margin-left:auto" @click="readAllNotices">
            全部标为已读
          </el-button>
        </div>
      </template>
      <div v-if="notices.length === 0" class="empty-tip">暂无通知公告</div>
      <div v-else class="notice-list">
        <div v-for="n in notices.slice(0, 5)" :key="n.id" class="notice-item" :class="{ unread: !n.is_read }" @click="readNotice(n)">
          <el-tag :type="noticeTagType(n)" size="small" effect="plain">{{ noticeTypeLabel(n) }}</el-tag>
          <span class="notice-title">{{ n.title }}</span>
          <span class="notice-time">{{ formatNoticeTime(n.created_at) }}</span>
        </div>
      </div>
    </el-card>

    <!-- 第二行：待办中心（所有角色可见） -->
    <el-row :gutter="16" class="row-margin">
      <el-col :span="8">
        <el-card shadow="hover" class="todo-card c-pending">
          <div class="todo-big">{{ myPendingCount }}</div>
          <div class="todo-small">待我审批</div>
          <div class="todo-mini">需及时处理</div>
          <el-button type="primary" link size="small" class="todo-link" @click="goToWorkflow('my_approve')">
            去处理 →
          </el-button>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover" class="todo-card c-submitted">
          <div class="todo-big">{{ mySubmittedCount }}</div>
          <div class="todo-small">我发起的</div>
          <div class="todo-mini">进行中 / 已完成</div>
          <el-button type="primary" link size="small" class="todo-link" @click="goToWorkflow('my_apply')">
            查看 →
          </el-button>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover" class="todo-card c-message">
          <div class="todo-big">{{ unreadMessages }}</div>
          <div class="todo-small">未读消息</div>
          <div class="todo-mini">系统通知 / 审批提醒</div>
          <el-button type="primary" link size="small" class="todo-link" @click="goToMessages">
            查看 →
          </el-button>
        </el-card>
      </el-col>
    </el-row>

    <!-- 第三行：快捷入口 -->
    <el-card shadow="never" class="row-margin">
      <template #header>
        <div class="h">
          <span class="h-icon" style="color:#67c23a">⚡</span>&nbsp;快捷入口
        </div>
      </template>
      <div class="quick-entry-grid">
        <div
          v-for="entry in quickEntries"
          :key="entry.path"
          class="quick-entry-item"
          @click="router.push(entry.path)"
        >
          <div class="entry-icon" :style="{ background: entry.bgColor }">{{ entry.icon }}</div>
          <div class="entry-name">{{ entry.name }}</div>
          <div class="entry-desc">{{ entry.desc }}</div>
        </div>
      </div>
    </el-card>

    <!-- 第四行：个人待办事项（所有角色可见） -->
    <el-card shadow="never" class="row-margin">
      <template #header>
        <div class="h">
          <span class="h-icon" style="color:#409eff">📋</span>&nbsp;我的待办事项
          <el-button type="primary" link size="small" style="margin-left:auto" @click="addTodoDialog = true">
            + 新建待办
          </el-button>
        </div>
      </template>
      <el-table :data="todos" size="small" stripe>
        <el-table-column prop="title" label="待办内容" min-width="200" show-overflow-tooltip />
        <el-table-column prop="priority" label="优先级" width="100">
          <template #default="{ row }">
            <el-tag :type="priorityType(row.priority)" size="small">{{ priorityLabel(row.priority) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="due_date" label="截止日期" width="120" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'completed' ? 'success' : 'warning'" size="small">
              {{ row.status === 'completed' ? '已完成' : '进行中' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" align="center">
          <template #default="{ row }">
            <el-button v-if="row.status !== 'completed'" type="success" link size="small" @click="completeTodo(row)">
              完成
            </el-button>
            <el-button type="danger" link size="small" @click="deleteTodo(row)">删除</el-button>
          </template>
        </el-table-column>
        <template #empty><el-empty description="暂无待办事项" :image-size="60" /></template>
      </el-table>
      <!-- 分页组件 -->
      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="todoPage"
          v-model:page-size="todoPageSize"
          :page-sizes="[10, 20, 50]"
          :total="todoTotal"
          layout="total, sizes, prev, pager, next, jumper"
          background
          @size-change="loadTodos"
          @current-change="loadTodos"
        />
      </div>
    </el-card>

    <!-- =========== 以下为领导/管理员专属面板 =========== -->
    <template v-if="showLeaderPanel">
      <div class="section-divider">
        <span class="divider-text">📊 数据大屏 · 管理视角</span>
      </div>

      <!-- 第四行：4个总览数字（仅领导可见） -->
      <el-row :gutter="16" class="row-margin">
        <el-col :span="6">
          <el-card shadow="hover" class="stat-card c1">
            <div class="big">{{ overview.total_person || 0 }}</div>
            <div class="small">人员总数</div>
            <div class="mini">男 {{ overview.male || 0 }} · 女 {{ overview.female || 0 }} · 未知 {{ overview.unknown_gender || 0 }}</div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" class="stat-card c2">
            <div class="big">{{ overview.total_users || 0 }}</div>
            <div class="small">系统账号数</div>
            <div class="mini">{{ overview.total_units || 0 }} 个单位</div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" class="stat-card c3">
            <div class="big">{{ approval.pending_count || 0 }}</div>
            <div class="small">待审批事项</div>
            <div class="mini">流程总数 {{ approval.total_instances || 0 }} · 今日办结 {{ approval.today_done_count || 0 }}</div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" class="stat-card c4">
            <div class="big">{{ approval.avg_approval_hours || 0 }} <span class="u">小时</span></div>
            <div class="small">平均审批时长</div>
            <div class="mini">越短效率越高；建议 ≤24 小时</div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 第五行：人员结构分布（仅领导可见） -->
      <el-row :gutter="16" class="row-margin">
        <el-col :span="6">
          <el-card shadow="never">
            <template #header><div class="h">年龄分布</div></template>
            <div class="bar-chart">
              <div v-for="(a, i) in demographics.age_distribution" :key="i" class="bar-row">
                <div class="label">{{ a.name }}</div>
                <div class="bar-bg">
                  <div class="bar-fill c1-bg" :style="{ width: agePct(a.value) + '%' }"></div>
                </div>
                <div class="val">{{ a.value }}</div>
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="never">
            <template #header><div class="h">学历构成</div></template>
            <div class="bar-chart">
              <div v-for="(a, i) in demoEdu" :key="i" class="bar-row">
                <div class="label">{{ a.name || '未填' }}</div>
                <div class="bar-bg">
                  <div class="bar-fill c2-bg" :style="{ width: eduPct(a.value) + '%' }"></div>
                </div>
                <div class="val">{{ a.value }}</div>
              </div>
              <el-empty v-if="demoEdu.length === 0" description="暂无数据" :image-size="60" />
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="never">
            <template #header><div class="h">政治面貌</div></template>
            <div class="bar-chart">
              <div v-for="(a, i) in demographics.political_distribution" :key="i" class="bar-row">
                <div class="label">{{ a.name }}</div>
                <div class="bar-bg">
                  <div class="bar-fill c3-bg" :style="{ width: politPct(a.value) + '%' }"></div>
                </div>
                <div class="val">{{ a.value }}</div>
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="never">
            <template #header><div class="h">部门人数 TOP 10</div></template>
            <div class="bar-chart">
              <div v-for="(a, i) in demographics.department_top" :key="i" class="bar-row">
                <div class="label">{{ a.name }}</div>
                <div class="bar-bg">
                  <div class="bar-fill c4-bg" :style="{ width: deptPct(a.value) + '%' }"></div>
                </div>
                <div class="val">{{ a.value }}</div>
              </div>
              <el-empty v-if="demographics.department_top.length === 0" description="暂无数据" :image-size="60" />
            </div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 第六行：预警提醒（仅领导可见） -->
      <el-row :gutter="16" class="row-margin">
        <el-col :span="12">
          <el-card shadow="never">
            <template #header>
              <div class="h">
                <span class="h-icon" style="color:#f56c6c">⚠</span>&nbsp;
                合同即将到期（30天内）
                <el-tag type="danger" size="small" effect="plain" style="margin-left:8px">
                  共 {{ warnings.expiring_contracts_total }} 份
                </el-tag>
                <span v-if="warnings.expired_contracts > 0" style="margin-left:8px">
                  <el-tag type="danger" size="small">已过期 {{ warnings.expired_contracts }} 份</el-tag>
                </span>
              </div>
            </template>
            <el-table :data="warnings.expiring_contracts" size="small" stripe>
              <el-table-column prop="person_name" label="姓名" width="100" />
              <el-table-column prop="contract_type" label="合同类型" width="120" />
              <el-table-column prop="contract_no" label="合同编号" />
              <el-table-column prop="end_date" label="到期日期" width="110" />
              <el-table-column label="剩余" width="80">
                <template #default="{ row }">
                  <el-tag :type="row.days_left <= 7 ? 'danger' : 'warning'" size="small">
                    {{ row.days_left }} 天
                  </el-tag>
                </template>
              </el-table-column>
              <template #empty><el-empty description="暂无到期合同" :image-size="60" /></template>
            </el-table>
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card shadow="never">
            <template #header>
              <div class="h">
                <span class="h-icon" style="color:#e6a23c">⏰</span>&nbsp;
                近两年内将达到法定退休年龄人员
              </div>
            </template>
            <el-table :data="warnings.retire_soon" size="small" stripe>
              <el-table-column prop="person_name" label="姓名" width="100" />
              <el-table-column prop="gender" label="性别" width="70" />
              <el-table-column prop="birth_date" label="出生年月" width="120" />
              <el-table-column prop="department" label="部门" />
              <el-table-column label="剩余年限" width="110">
                <template #default="{ row }">
                  <el-tag :type="row.years_left === 0 ? 'danger' : (row.years_left === 1 ? 'warning' : '')" size="small">
                    还有 {{ row.years_left }} 年（{{ row.retire_age }}岁）
                  </el-tag>
                </template>
              </el-table-column>
              <template #empty><el-empty description="暂无近期退休人员" :image-size="60" /></template>
            </el-table>
          </el-card>
        </el-col>
      </el-row>

      <!-- 第七行：今日操作动态（仅领导可见） -->
      <el-row :gutter="16" class="row-margin">
        <el-col :span="24">
          <el-card shadow="never">
            <template #header><div class="h"><span class="h-icon">📅</span>&nbsp;今日操作动态</div></template>
            <el-table :data="today_ops" size="small" stripe>
              <el-table-column prop="time" label="时间" width="80" />
              <el-table-column prop="operator_name" label="操作人" width="110" />
              <el-table-column prop="action" label="动作" width="160">
                <template #default="{ row }">
                  <el-tag size="small">{{ row.action }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="detail" label="详情" show-overflow-tooltip />
              <template #empty><el-empty description="今日暂无操作" :image-size="60" /></template>
            </el-table>
          </el-card>
        </el-col>
      </el-row>
    </template>

    <!-- =========== 三员专属：系统监控面板 =========== -->
    <template v-if="showTriOfficerPanel">
      <div class="section-divider">
        <span class="divider-text">🛡 系统监控 · 三员视角</span>
      </div>
      <el-row :gutter="16" class="row-margin">
        <el-col :span="6">
          <el-card shadow="hover" class="stat-card c1">
            <div class="big">{{ sysStats.total_users || 0 }}</div>
            <div class="small">系统账号总数</div>
            <div class="mini">激活 {{ sysStats.active_users || 0 }} · 停用 {{ sysStats.inactive_users || 0 }}</div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" class="stat-card c2">
            <div class="big">{{ sysStats.today_logins || 0 }}</div>
            <div class="small">今日登录次数</div>
            <div class="mini">在线用户 {{ sysStats.online_users || 0 }} 人</div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" class="stat-card c3">
            <div class="big">{{ sysStats.today_operations || 0 }}</div>
            <div class="small">今日操作数</div>
            <div class="mini">审计日志累计 {{ sysStats.total_logs || 0 }} 条</div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" class="stat-card c4">
            <div class="big">{{ sysStats.failed_logins || 0 }}</div>
            <div class="small">今日登录失败</div>
            <div class="mini">疑似异常 {{ sysStats.locked_users || 0 }} 个账号锁定</div>
          </el-card>
        </el-col>
      </el-row>

      <el-card shadow="never" class="row-margin">
        <template #header>
          <div class="h">
            <span class="h-icon">📜</span>&nbsp;最近审计日志
            <el-button type="primary" link size="small" style="margin-left:auto" @click="router.push('/system/audit-logs')">
              查看全部 →
            </el-button>
          </div>
        </template>
        <el-table :data="recentLogs" size="small" stripe>
          <el-table-column prop="time" label="时间" width="150" />
          <el-table-column prop="operator" label="操作人" width="120" />
          <el-table-column prop="action" label="动作" width="160">
            <template #default="{ row }">
              <el-tag size="small" :type="logTagType(row.action)">{{ row.action }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="detail" label="详情" show-overflow-tooltip />
          <el-table-column prop="ip" label="IP地址" width="130" />
          <template #empty><el-empty description="暂无审计日志" :image-size="60" /></template>
        </el-table>
      </el-card>
    </template>

    <!-- 新建待办对话框 -->
    <el-dialog v-model="addTodoDialog" title="新建待办事项" width="500px">
      <el-form label-width="80px">
        <el-form-item label="内容">
          <el-input v-model="newTodo.title" placeholder="请输入待办内容" />
        </el-form-item>
        <el-form-item label="优先级">
          <el-select v-model="newTodo.priority" style="width:100%">
            <el-option label="高" value="high" />
            <el-option label="中" value="medium" />
            <el-option label="低" value="low" />
          </el-select>
        </el-form-item>
        <el-form-item label="截止日期">
          <el-date-picker v-model="newTodo.due_date" type="date" value-format="YYYY-MM-DD" style="width:100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addTodoDialog = false">取消</el-button>
        <el-button type="primary" @click="saveTodo">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { analyticsApi, noticeApi, todoApi, messageApi, workflowApi } from '@/api'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()
const authStore = useAuthStore()
const userRole = computed(() => authStore.user?.role || 'person')
const userName = computed(() => authStore.user?.name || authStore.user?.username || '同事')

// 角色判断
const leaderRoles = ['super_admin', 'unit_admin', 'dept_leader', 'hr', 'finance', 'dept_admin']
const triOfficerRoles = ['system_admin', 'security_officer', 'auditor']
const showLeaderPanel = computed(() => leaderRoles.includes(userRole.value) || triOfficerRoles.includes(userRole.value))
const showTriOfficerPanel = computed(() => triOfficerRoles.includes(userRole.value))

// 角色标签
const roleLabel = computed(() => {
  const map = {
    super_admin: '超级管理员', unit_admin: '单位管理员', dept_admin: '部门管理员',
    dept_leader: '部门领导', hr: '人事人员', finance: '财务人员', person: '普通员工',
    system_admin: '系统管理员(三员)', security_officer: '安全保密管理员', auditor: '安全审计员',
  }
  return map[userRole.value] || userRole.value
})
const roleTagType = computed(() => {
  if (userRole.value === 'super_admin') return 'danger'
  if (triOfficerRoles.includes(userRole.value)) return 'warning'
  if (leaderRoles.includes(userRole.value)) return 'success'
  return 'info'
})

const goToWorkflow = (tab) => {
  router.push({ path: '/workflow', query: tab ? { tab } : {} })
}

const goToMessages = () => {
  router.push('/messages')
}

// 欢迎语
const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 6) return '凌晨好'
  if (h < 9) return '早上好'
  if (h < 12) return '上午好'
  if (h < 14) return '中午好'
  if (h < 18) return '下午好'
  return '晚上好'
})
const todayStr = computed(() => {
  const d = new Date()
  const week = ['日', '一', '二', '三', '四', '五', '六']
  return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日 星期${week[d.getDay()]}`
})

// 通知公告
const notices = ref([])
const loadNotices = async () => {
  try {
    const data = await noticeApi.list({ page: 1, size: 5 })
    notices.value = data.items || data || []
  } catch (e) { console.error('通知加载失败', e) }
}
const readNotice = async (n) => {
  try {
    if (!n.is_read) {
      await noticeApi.read(n.id)
      n.is_read = true
    }
  } catch (e) { /* 忽略 */ }
}
const readAllNotices = async () => {
  try {
    await noticeApi.readAll()
    notices.value.forEach(n => n.is_read = true)
    ElMessage.success('已全部标为已读')
  } catch (e) { ElMessage.error('操作失败') }
}
const noticeTagType = (n) => n.notice_type === 'urgent' ? 'danger' : (n.notice_type === 'important' ? 'warning' : 'info')
const noticeTypeLabel = (n) => n.notice_type === 'urgent' ? '紧急' : (n.notice_type === 'important' ? '重要' : '通知')
const formatNoticeTime = (t) => {
  if (!t) return ''
  const d = new Date(t)
  const now = new Date()
  const diff = (now - d) / 1000
  if (diff < 60) return '刚刚'
  if (diff < 3600) return `${Math.floor(diff / 60)}分钟前`
  if (diff < 86400) return `${Math.floor(diff / 3600)}小时前`
  return d.toLocaleDateString()
}

// 待办审批数字
const myPendingCount = ref(0)
const mySubmittedCount = ref(0)
const unreadMessages = ref(0)
const loadWorkflowStats = async () => {
  try {
    const [pending, submitted, msgStats] = await Promise.all([
      workflowApi.list({ status: 'pending', my_approval: true, page: 1, size: 1 }),
      workflowApi.list({ submitted_by_me: true, page: 1, size: 1 }),
      messageApi.stats().catch(() => ({ unread: 0 })),
    ])
    myPendingCount.value = pending.total || 0
    mySubmittedCount.value = submitted.total || 0
    unreadMessages.value = msgStats.unread || 0
  } catch (e) { console.error('审批统计加载失败', e) }
}

// 个人待办
const todos = ref([])
const todoPage = ref(1)
const todoPageSize = ref(10)
const todoTotal = ref(0)
const loadTodos = async () => {
  try {
    const data = await todoApi.list({ page: todoPage.value, size: todoPageSize.value })
    todos.value = data.items || data || []
    todoTotal.value = data.total || todos.value.length
  } catch (e) { console.error('待办加载失败', e) }
}

// 快捷入口（路径必须与router/index.js中实际注册的path一致）
const quickEntries = ref([
  {
    name: '流程审批',
    desc: '查看审批流程，发起新审批',
    icon: '📝',
    bgColor: '#ecf5ff',
    path: '/workflow'
  },
  {
    name: '智能表格',
    desc: 'AI生成与填写表单',
    icon: '🤖',
    bgColor: '#f0f9eb',
    path: '/smart-forms'
  },
  {
    name: '人员档案',
    desc: '查看和管理人员信息',
    icon: '👥',
    bgColor: '#fef0f0',
    path: '/persons'
  },
  {
    name: '在职管理',
    desc: '考勤/绩效/奖惩/调岗',
    icon: '⏰',
    bgColor: '#fdf6ec',
    path: '/hr-management'
  },
  {
    name: '离职/批量',
    desc: '离职审批与批量操作',
    icon: '🔀',
    bgColor: '#faf0e6',
    path: '/hr-exit-batch'
  },
  {
    name: '统计报表',
    desc: '生成各类统计报表',
    icon: '📊',
    bgColor: '#ebf5ff',
    path: '/reports'
  },
  {
    name: '通知公告',
    desc: '查看系统通知与公告',
    icon: '📢',
    bgColor: '#fdf6ec',
    path: '/notices'
  },
  {
    name: '待办事项',
    desc: '管理个人全部待办',
    icon: '✅',
    bgColor: '#f0f9eb',
    path: '/todos'
  },
])
const addTodoDialog = ref(false)
const newTodo = reactive({ title: '', priority: 'medium', due_date: '' })
const saveTodo = async () => {
  if (!newTodo.title) { ElMessage.warning('请输入待办内容'); return }
  try {
    await todoApi.create(newTodo)
    ElMessage.success('待办已创建')
    addTodoDialog.value = false
    newTodo.title = ''; newTodo.priority = 'medium'; newTodo.due_date = ''
    loadTodos()
  } catch (e) { ElMessage.error('创建失败') }
}
const completeTodo = async (row) => {
  try {
    await todoApi.complete(row.id)
    ElMessage.success('已完成')
    loadTodos()
  } catch (e) { ElMessage.error('操作失败') }
}
const deleteTodo = async (row) => {
  try {
    await ElMessageBox.confirm('确定删除该待办？', '提示', { type: 'warning' })
    await todoApi.delete(row.id)
    ElMessage.success('已删除')
    loadTodos()
  } catch (e) { /* 取消 */ }
}
const priorityType = (p) => p === 'high' ? 'danger' : (p === 'medium' ? 'warning' : 'info')
const priorityLabel = (p) => p === 'high' ? '高' : (p === 'medium' ? '中' : '低')

// 领导驾驶舱数据
const overview = reactive({})
const demographics = reactive({ age_distribution: [], education_distribution: [],
                                 political_distribution: [], department_top: [] })
const approval = reactive({})
const warnings = reactive({ expiring_contracts: [], retire_soon: [] })
const today_ops = ref([])

const ageMax = computed(() => Math.max(1, ...demographics.age_distribution.map(x => x.value)))
const agePct = (v) => Math.round(v / ageMax.value * 100)
const eduMax = computed(() => Math.max(1, ...(demoEdu.value.map(x => x.value))))
const eduPct = (v) => Math.round(v / eduMax.value * 100)
const politMax = computed(() => Math.max(1, ...demographics.political_distribution.map(x => x.value)))
const politPct = (v) => Math.round(v / politMax.value * 100)
const deptMax = computed(() => Math.max(1, ...demographics.department_top.map(x => x.value)))
const deptPct = (v) => Math.round(v / deptMax.value * 100)
const demoEdu = computed(() => (demographics.education_distribution || []).slice(0, 8))

const loadDashboard = async () => {
  if (!showLeaderPanel.value && !showTriOfficerPanel.value) return
  try {
    const data = await analyticsApi.dashboardOverview()
    Object.assign(overview, data.overview || {})
    Object.assign(demographics, data.demographics || {})
    Object.assign(approval, data.approval || {})
    Object.assign(warnings, data.warnings || {})
    today_ops.value = data.today_operations || []
  } catch (e) { console.error('驾驶舱数据加载失败', e) }
}

// 三员监控数据
const sysStats = reactive({})
const recentLogs = ref([])
const loadSysStats = async () => {
  if (!showTriOfficerPanel.value) return
  try {
    // 复用驾驶舱接口的数据
    const data = await analyticsApi.dashboardOverview()
    sysStats.total_users = data.overview?.total_users || 0
    sysStats.active_users = data.overview?.active_users || 0
    sysStats.inactive_users = (data.overview?.total_users || 0) - (data.overview?.active_users || 0)
    sysStats.today_operations = data.today_operations?.length || 0
    sysStats.total_logs = data.overview?.total_logs || 0
    // 今日登录次数、失败次数、在线用户、锁定账号 - 简化处理
    sysStats.today_logins = data.overview?.today_logins || 0
    sysStats.online_users = data.overview?.online_users || 0
    sysStats.failed_logins = data.overview?.failed_logins || 0
    sysStats.locked_users = data.overview?.locked_users || 0
    recentLogs.value = (data.today_operations || []).map(op => ({
      time: op.time,
      operator: op.operator_name,
      action: op.action,
      detail: op.detail,
      ip: op.ip_address || '-',
    }))
  } catch (e) { console.error('系统监控数据加载失败', e) }
}
const logTagType = (action) => {
  if (!action) return 'info'
  if (action.includes('删除') || action.includes('停用')) return 'danger'
  if (action.includes('登录') || action.includes('登出')) return 'success'
  if (action.includes('创建') || action.includes('新增')) return 'primary'
  if (action.includes('修改') || action.includes('更新')) return 'warning'
  return 'info'
}

onMounted(() => {
  loadNotices()
  loadWorkflowStats()
  loadTodos()
  loadDashboard()
  loadSysStats()
})
</script>

<style scoped>
.dashboard-page { padding: 16px; }
.row-margin { margin-bottom: 16px; }

/* 欢迎条 */
.welcome-bar {
  display: flex; justify-content: space-between; align-items: center;
  background: linear-gradient(135deg, #1f497d 0%, #2d5a27 100%);
  color: #fff; padding: 16px 20px; border-radius: 8px; margin-bottom: 16px;
}
.welcome-left { display: flex; align-items: center; gap: 12px; }
.hello { font-size: 18px; font-weight: 600; }
.role-tag { border: none; }
.welcome-right .date-text { font-size: 13px; opacity: 0.9; }

/* 通知公告 */
.notice-card { margin-bottom: 16px; }
.notice-list { display: flex; flex-direction: column; gap: 8px; }
.notice-item {
  display: flex; align-items: center; gap: 12px;
  padding: 10px 12px; border-radius: 6px; cursor: pointer;
  background: #fafafa; transition: all .2s;
  border-left: 3px solid transparent;
}
.notice-item:hover { background: #f0f5ff; border-left-color: #409eff; }
.notice-item.unread { background: #fff8e6; border-left-color: #e6a23c; }
.notice-title { flex: 1; font-size: 13px; color: #303133; }
.notice-item.unread .notice-title { font-weight: 600; }
.notice-time { font-size: 12px; color: #909399; }
.empty-tip { text-align: center; color: #909399; padding: 24px; font-size: 13px; }

/* 待办卡 */
.todo-card { position: relative; padding: 8px 0; }
.todo-big { font-size: 32px; font-weight: 700; line-height: 1.1; }
.todo-small { font-size: 14px; color: #606266; margin-top: 4px; }
.todo-mini { font-size: 12px; color: #909399; margin-top: 4px; }
.todo-link { position: absolute; right: 12px; bottom: 12px; }
.c-pending .todo-big { color: #f56c6c; }
.c-submitted .todo-big { color: #409eff; }
.c-message .todo-big { color: #e6a23c; }

/* 分隔标题 */
.section-divider {
  display: flex; align-items: center; margin: 24px 0 16px;
}
.section-divider::before, .section-divider::after {
  content: ''; flex: 1; height: 1px; background: #dcdfe6;
}
.divider-text {
  padding: 0 16px; font-size: 14px; font-weight: 600;
  color: #1f497d; background: #f5f7fa;
  border-radius: 12px; padding: 4px 16px;
}

/* 总览卡 */
.stat-card { border-left: 4px solid; }
.stat-card.c1 { border-left-color: #2d5a27; }
.stat-card.c2 { border-left-color: #2b578a; }
.stat-card.c3 { border-left-color: #c9a54f; }
.stat-card.c4 { border-left-color: #d86a2f; }
.big { font-size: 32px; font-weight: 700; color: #2d5a27; line-height: 1.1; }
.c2 .big { color: #2b578a; }
.c3 .big { color: #c9a54f; }
.c4 .big { color: #d86a2f; }
.big .u { font-size: 14px; font-weight: normal; color: #909399; }
.small { font-size: 14px; color: #606266; margin-top: 4px; }
.mini { font-size: 12px; color: #909399; margin-top: 4px; }
.h { font-size: 15px; font-weight: 600; color: #303133; display: flex; align-items: center; }
.h-icon { font-size: 16px; }

/* 分页 */
.pagination-wrap {
  display: flex; justify-content: flex-end; margin-top: 12px;
}

/* 快捷入口 */
.quick-entry-grid {
  display: grid;
  grid-template-columns: repeat(8, 1fr);
  gap: 12px;
}
.quick-entry-item {
  display: flex; flex-direction: column; align-items: center;
  padding: 16px 8px; border-radius: 8px; cursor: pointer;
  transition: all .25s ease;
  border: 1px solid #ebeef5;
}
.quick-entry-item:hover {
  background: #f5f7fa;
  border-color: #c0c4cc;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.08);
}
.entry-icon {
  width: 48px; height: 48px; border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  font-size: 24px; margin-bottom: 8px;
}
.entry-name {
  font-size: 13px; font-weight: 600; color: #303133; margin-bottom: 4px;
}
.entry-desc {
  font-size: 11px; color: #909399; text-align: center;
}

/* 柱状图 */
.bar-chart { max-height: 340px; overflow-y: auto; }
.bar-row { display: flex; align-items: center; padding: 6px 0; font-size: 13px; }
.bar-row .label { width: 90px; color: #606266; flex-shrink: 0; }
.bar-row .bar-bg { flex: 1; height: 14px; background: #f0f2f5; border-radius: 3px; margin: 0 8px; overflow: hidden; }
.bar-fill { height: 100%; border-radius: 3px; min-width: 2px; transition: width .5s; }
.c1-bg { background: linear-gradient(90deg,#2d5a27,#4f8b48); }
.c2-bg { background: linear-gradient(90deg,#2b578a,#5b87c4); }
.c3-bg { background: linear-gradient(90deg,#c9a54f,#e4c984); }
.c4-bg { background: linear-gradient(90deg,#d86a2f,#e69568); }
.bar-row .val { width: 40px; text-align: right; color: #303133; font-weight: 600; }
</style>
