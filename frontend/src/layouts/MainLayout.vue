<template>
  <el-container class="main-layout">
    <!-- 侧边栏 -->
    <el-aside :width="isCollapse ? '64px' : '230px'" class="sidebar">
      <div class="logo">
        <el-icon size="22" color="#c4a000"><Star /></el-icon>
        <span v-show="!isCollapse" class="logo-text">信息管理系统</span>
      </div>
      <div class="logo-sub" v-show="!isCollapse">
        <span class="rank-line"></span>
        <span class="logo-sub-text">综合管理平台</span>
        <span class="rank-line"></span>
      </div>
      <el-menu
        :default-active="$route.path"
        :collapse="isCollapse"
        :default-openeds="defaultOpeneds"
        router
        background-color="#1a2b1e"
        text-color="#a8b5ac"
        active-text-color="#c4a000"
      >
        <template v-for="item in menuItems" :key="item.key">
          <!-- 分组菜单 -->
          <el-sub-menu v-if="item.children" :index="item.key">
            <template #title>
              <el-icon><component :is="item.icon" /></el-icon>
              <span>{{ item.title }}</span>
            </template>
            <el-menu-item
              v-for="child in item.children"
              :key="child.fullPath"
              :index="child.fullPath"
            >
              <el-icon><component :is="child.meta.icon" /></el-icon>
              <template #title>{{ child.meta.title }}</template>
            </el-menu-item>
          </el-sub-menu>
          <!-- 独立菜单项 -->
          <el-menu-item v-else :index="item.fullPath">
            <el-icon><component :is="item.meta.icon" /></el-icon>
            <template #title>{{ item.meta.title }}</template>
          </el-menu-item>
        </template>
      </el-menu>
    </el-aside>

    <el-container>
      <!-- 顶部 -->
      <el-header class="header">
        <div class="header-left">
          <el-icon class="collapse-btn" @click="isCollapse = !isCollapse" size="20" color="#2d5a27">
            <Fold v-if="!isCollapse" />
            <Expand v-else />
          </el-icon>
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item>{{ $route.meta.title }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="header-right">
          <div class="header-badge">
            <el-icon size="14" color="#c4a000"><Star /></el-icon>
            <span class="badge-text">{{ roleLabel }}</span>
          </div>

          <!-- 顶部铃铛 - 统一消息中心入口 -->
          <el-popover
            placement="bottom-end"
            :width="380"
            trigger="click"
            :popper-style="{ padding: '0' }"
            popper-class="msg-popover"
          >
            <template #reference>
              <div class="bell-wrap" @click="loadBellMessages">
                <el-badge :value="bellUnread" :max="99" :hidden="bellUnread <= 0" class="bell-badge">
                  <el-icon size="22" color="#2d5a27" class="bell-icon">
                    <Bell />
                  </el-icon>
                </el-badge>
              </div>
            </template>

            <div class="bell-pop">
              <div class="bell-pop-header">
                <span class="bell-pop-title">消息中心</span>
                <span class="bell-pop-action"
                      :class="{ disabled: bellUnread === 0 }"
                      @click="handleBellReadAll">全部已读</span>
              </div>
              <el-divider style="margin:0" />

              <div v-loading="bellLoading" class="bell-pop-list">
                <div v-if="bellMessages.length === 0" class="bell-empty">
                  <el-empty description="暂无消息" :image-size="60" />
                </div>
                <div
                  v-for="m in bellMessages"
                  :key="m.id"
                  class="bell-item"
                  :class="{ 'bell-item-unread': !m.is_read }"
                  @click="handleBellClick(m)"
                >
                  <div class="bell-item-dot" v-if="!m.is_read"></div>
                  <div class="bell-item-title">
                    <el-tag size="small" effect="light" :type="bellTagType(m.msg_type)">{{ bellTypeName(m.msg_type) }}</el-tag>
                    <span class="bell-item-title-text">{{ m.title }}</span>
                  </div>
                  <div class="bell-item-content">{{ m.content || '（无内容）' }}</div>
                  <div class="bell-item-time">{{ formatBellTime(m.created_at) }}</div>
                </div>
              </div>

              <el-divider style="margin:0" />
              <div class="bell-pop-footer" @click="goMessageCenter">
                查看全部消息 →
              </div>
            </div>
          </el-popover>

          <el-dropdown @command="handleCommand">
            <span class="user-info">
              <el-avatar :size="32" class="user-avatar">
                {{ auth.user?.username?.charAt(0)?.toUpperCase() }}
              </el-avatar>
              <span class="username">{{ auth.user?.username }}</span>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="changePwd">
                  <el-icon><Lock /></el-icon>修改密码
                </el-dropdown-item>
                <el-dropdown-item command="logout" divided>
                  <el-icon><SwitchButton /></el-icon>退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <!-- 内容区 -->
      <el-main class="content">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>

    <!-- 修改密码对话框 -->
    <el-dialog v-model="pwdDialog" title="修改密码" width="420px">
      <el-form :model="pwdForm" label-width="80px">
        <el-form-item label="原密码">
          <el-input v-model="pwdForm.old" type="password" show-password />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input v-model="pwdForm.new" type="password" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="pwdDialog = false">取消</el-button>
        <el-button type="primary" @click="submitChangePwd">确认</el-button>
      </template>
    </el-dialog>
  </el-container>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { Bell, Fold, Expand, Star, Lock, SwitchButton } from '@element-plus/icons-vue'
import api, { messageApi } from '@/api'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const isCollapse = ref(false)

// ============ 顶部铃铛 - 统一消息中心 ============
const bellUnread = ref(0)
const bellMessages = ref([])
const bellLoading = ref(false)
let bellPollTimer = null

const bellTypeMap = {
  notice:     { name: '通知公告', type: 'warning' },
  approval:   { name: '审批流程', type: 'danger'  },
  smart_form: { name: '智能表格', type: 'primary' },
  todo:       { name: '待办事项', type: 'info'    },
  mention:    { name: '@我',      type: 'success' },
  system:     { name: '系统消息', type: ''        },
}
function bellTypeName(t) { return bellTypeMap[t]?.name || t || '' }
function bellTagType(t)  { return bellTypeMap[t]?.type || '' }

function formatBellTime(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  const now = new Date()
  const diffMs = now - d
  const diffMin = Math.floor(diffMs / 60000)
  if (diffMin < 1) return '刚刚'
  if (diffMin < 60) return `${diffMin} 分钟前`
  const diffH = Math.floor(diffMin / 60)
  if (diffH < 24) return `${diffH} 小时前`
  const pad = n => String(n).padStart(2, '0')
  return `${d.getMonth()+1}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

async function loadBellUnread() {
  try {
    const r = await messageApi.unreadCount()
    bellUnread.value = r.unread_count || 0
  } catch (e) {}
}

async function loadBellMessages() {
  bellLoading.value = true
  try {
    const res = await messageApi.list({ page: 1, page_size: 8 })
    bellMessages.value = res.items || []
    bellUnread.value = res.unread_count || 0
  } catch (e) {} finally {
    bellLoading.value = false
  }
}

async function handleBellClick(m) {
  // 点击跳转，未读的先标已读
  if (!m.is_read) {
    try {
      await messageApi.read(m.id)
      m.is_read = true
      bellUnread.value = Math.max(0, bellUnread.value - 1)
    } catch (e) {}
  }
  const path = m.extra?.router
  if (path) {
    const tab = m.extra?.tab
    router.push(tab ? { path, query: { tab } } : path)
  }
}

async function handleBellReadAll() {
  if (bellUnread.value <= 0) return
  try {
    await messageApi.readAll()
    ElMessage.success('已标记全部为已读')
    bellUnread.value = 0
    bellMessages.value.forEach(m => (m.is_read = true))
  } catch (e) {}
}

function goMessageCenter() {
  router.push('/messages')
}

// 全局事件：消息中心更新后同步铃铛
function handleUnreadEvent(e) {
  bellUnread.value = Number(e.detail) || 0
}

onMounted(() => {
  if (auth.isLoggedIn) {
    loadBellUnread()
    window.addEventListener('unread-message-count', handleUnreadEvent)
    bellPollTimer = setInterval(loadBellUnread, 30000)
    initSessionTimeout()
  }
})
onBeforeUnmount(() => {
  window.removeEventListener('unread-message-count', handleUnreadEvent)
  if (bellPollTimer) clearInterval(bellPollTimer)
  destroySessionTimeout()
})

// ============ 会话超时（30分钟无操作自动登出） ============
const IDLE_TIMEOUT = 30 * 60 * 1000 // 30分钟
const WARN_BEFORE = 60 * 1000 // 提前1分钟提醒
let idleTimer = null
let warnTimer = null

const resetIdleTimer = () => {
  if (idleTimer) clearTimeout(idleTimer)
  if (warnTimer) clearTimeout(warnTimer)
  warnTimer = setTimeout(() => {
    ElMessageBox.alert(
      '您已长时间未操作，系统将在 1 分钟后自动登出，请保存当前工作。点击确认继续使用。',
      '会话即将过期',
      { type: 'warning', confirmButtonText: '继续使用', showClose: false }
    )
      .then(() => resetIdleTimer())
      .catch(() => {})
  }, IDLE_TIMEOUT - WARN_BEFORE)
  idleTimer = setTimeout(() => {
    handleIdleTimeout()
  }, IDLE_TIMEOUT)
}

const handleIdleTimeout = () => {
  auth.logout()
  ElMessage.warning('长时间未操作，已自动登出')
  router.push('/login')
}

const idleEvents = ['mousemove', 'keydown', 'click', 'scroll', 'touchstart']
const setupIdleListeners = () => {
  idleEvents.forEach(evt => {
    document.addEventListener(evt, resetIdleTimer, { passive: true })
  })
}
const removeIdleListeners = () => {
  idleEvents.forEach(evt => {
    document.removeEventListener(evt, resetIdleTimer)
  })
}

const initSessionTimeout = () => {
  setupIdleListeners()
  resetIdleTimer()
}
const destroySessionTimeout = () => {
  removeIdleListeners()
  if (idleTimer) clearTimeout(idleTimer)
  if (warnTimer) clearTimeout(warnTimer)
}


// 按角色过滤菜单并分组
const filteredRoutes = computed(() => {
  const children = router.options.routes.find((r) => r.path === '/')?.children || []
  return children
    .filter((r) => !r.meta?.hideInMenu)
    .filter((r) => !r.meta?.roles || auth.role === 'super_admin' || r.meta.roles.includes(auth.role))
    .map((r) => ({ ...r, fullPath: '/' + r.path }))
})

// 构建分组菜单结构
const menuItems = computed(() => {
  const items = []
  const grouped = {}

  for (const route of filteredRoutes.value) {
    const groupName = route.meta?.group
    if (!groupName) {
      // 无分组的独立菜单项
      items.push({ ...route, key: route.fullPath })
    } else {
      // 有分组的菜单项
      if (!grouped[groupName]) {
        grouped[groupName] = {
          key: `group-${groupName}`,
          title: groupName,
          icon: route.meta.groupIcon || 'Folder',
          children: [],
        }
        items.push(grouped[groupName])
      }
      grouped[groupName].children.push(route)
    }
  }
  return items
})

// 默认展开当前路由所在分组
const defaultOpeneds = computed(() => {
  const currentGroup = filteredRoutes.value.find((r) => r.fullPath === route.path)
  if (currentGroup?.meta?.group) {
    return [`group-${currentGroup.meta.group}`]
  }
  return []
})

const roleLabel = computed(() => {
  const map = {
    super_admin: '超级管理员',
    unit_admin: '单位管理员',
    person: '普通用户',
    hr: '人事人员',
    finance: '财务人员',
    dept_leader: '部门领导',
    dept_admin: '部门管理员',
    system_admin: '系统管理员(三员)',
    security_officer: '安全保密管理员(三员)',
    auditor: '安全审计员(三员)',
  }
  return map[auth.role] || auth.role
})
const roleTagType = computed(() => {
  const map = {
    super_admin: 'danger',
    unit_admin: 'warning',
    person: 'info',
    hr: '',
    finance: 'success',
    dept_leader: 'warning',
    dept_admin: '',
    system_admin: 'primary',
    security_officer: 'warning',
    auditor: 'success',
  }
  return map[auth.role] || 'info'
})

// 修改密码
const pwdDialog = ref(false)
const pwdForm = ref({ old: '', new: '' })
const handleCommand = (cmd) => {
  if (cmd === 'changePwd') {
    pwdForm.value = { old: '', new: '' }
    pwdDialog.value = true
  } else if (cmd === 'logout') {
    ElMessageBox.confirm('确定要退出登录吗？', '提示', { type: 'warning' })
      .then(() => {
        auth.logout()
        router.push('/login')
      })
      .catch(() => {})
  }
}
const submitChangePwd = async () => {
  if (!pwdForm.value.old || !pwdForm.value.new) {
    ElMessage.warning('请填写完整')
    return
  }
  await api.post('/auth/change-password', {
    old_password: pwdForm.value.old,
    new_password: pwdForm.value.new,
  })
  ElMessage.success('密码修改成功，请重新登录')
  pwdDialog.value = false
  auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.main-layout {
  height: 100vh;
}

/* ===== 侧边栏 ===== */
.sidebar {
  background-color: #1a2b1e;
  transition: width 0.3s;
  overflow-x: hidden;
  border-right: 2px solid #2d5a27;
}

.logo {
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: #fff;
  border-bottom: 1px solid #2d5a27;
  background: linear-gradient(180deg, #1e3522 0%, #1a2b1e 100%);
}

.logo-text {
  font-size: 15px;
  font-weight: 700;
  white-space: nowrap;
  letter-spacing: 2px;
  color: #e8d060;
}

.logo-sub {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 8px 0;
  border-bottom: 1px solid #2d5a27;
}

.rank-line {
  display: inline-block;
  width: 24px;
  height: 1px;
  background: #c4a000;
  opacity: 0.6;
}

.logo-sub-text {
  font-size: 11px;
  color: #8a9b8e;
  letter-spacing: 1px;
}

.el-menu {
  border-right: none;
}

/* 分组菜单样式 */
.sidebar :deep(.el-sub-menu__title) {
  font-size: 14px;
  font-weight: 600;
  color: #c8d4cc !important;
}

.sidebar :deep(.el-sub-menu__title:hover) {
  background-color: #1e3522 !important;
}

.sidebar :deep(.el-sub-menu .el-menu-item) {
  padding-left: 48px !important;
  font-size: 13px;
}

.sidebar :deep(.el-sub-menu .el-menu-item.is-active) {
  background-color: rgba(196, 160, 0, 0.12) !important;
  border-right: 3px solid #c4a000;
}

/* ===== 顶部 ===== */
.header {
  background: #fff;
  border-bottom: 3px solid #2d5a27;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.collapse-btn {
  cursor: pointer;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  background: linear-gradient(90deg, rgba(45, 90, 39, 0.08), rgba(196, 160, 0, 0.08));
  border: 1px solid #d4d8ce;
  border-radius: 2px;
}

.badge-text {
  font-size: 13px;
  color: #2d5a27;
  font-weight: 600;
}

.header-right .user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.user-avatar {
  background: #2d5a27 !important;
  color: #fff !important;
  font-weight: 600;
  font-size: 14px;
}

.username {
  font-size: 14px;
  color: #1a2b1e;
  font-weight: 500;
}

/* ===== 内容区 ===== */
.content {
  background: #f5f6f0;
  overflow-y: auto;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* ===== 顶部铃铛消息 ===== */
.bell-wrap {
  position: relative;
  cursor: pointer;
  padding: 6px;
  border-radius: 6px;
  transition: background 0.15s;
}
.bell-wrap:hover {
  background: #f5f7f2;
}
.bell-icon {
  display: block;
}
.bell-badge :deep(.el-badge__content) {
  border: none;
}

.bell-pop {
  font-size: 14px;
}
.bell-pop-header {
  padding: 12px 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.bell-pop-title {
  font-weight: 600;
  color: #1a2b1e;
  font-size: 15px;
}
.bell-pop-action {
  font-size: 13px;
  color: #2d5a27;
  cursor: pointer;
}
.bell-pop-action:hover {
  color: #c4a000;
  text-decoration: underline;
}
.bell-pop-action.disabled {
  color: #c0c4cc;
  cursor: not-allowed;
  pointer-events: none;
}

.bell-pop-list {
  max-height: 380px;
  overflow-y: auto;
}
.bell-empty {
  padding: 24px 0 12px;
}

.bell-item {
  padding: 12px 16px;
  border-bottom: 1px solid #f0f0f0;
  cursor: pointer;
  position: relative;
  transition: background 0.15s;
}
.bell-item:last-child { border-bottom: none; }
.bell-item:hover { background: #fafbfc; }
.bell-item-unread { background: #f5faff; }

.bell-item-dot {
  position: absolute;
  left: 6px;
  top: 18px;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #f56c6c;
}

.bell-item-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
  padding-left: 12px;
}
.bell-item-title-text {
  font-weight: 600;
  color: #1f2937;
  font-size: 14px;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.bell-item-content {
  padding-left: 12px;
  color: #4b5563;
  font-size: 13px;
  line-height: 1.4;
  margin-bottom: 6px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.bell-item-time {
  padding-left: 12px;
  font-size: 12px;
  color: #9ca3af;
}

.bell-pop-footer {
  padding: 10px 16px;
  text-align: center;
  color: #2d5a27;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s;
}
.bell-pop-footer:hover {
  background: #f5f7f2;
  color: #c4a000;
}
</style>
