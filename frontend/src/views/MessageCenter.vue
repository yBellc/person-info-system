<template>
  <div class="message-center">
    <el-card shadow="never" class="filter-card">
      <div class="filter-row">
        <div class="filter-tags">
          <el-tag
            v-for="t in filterTabs"
            :key="t.key"
            :type="activeFilter === t.key ? 'primary' : 'info'"
            :effect="activeFilter === t.key ? 'dark' : 'plain'"
            class="filter-tag"
            :hit="activeFilter === t.key"
            @click="activeFilter = t.key; currentPage = 1; refresh()"
          >
            {{ t.label }}
            <span v-if="t.key === 'all'" class="filter-count">({{ total }})</span>
            <span v-else-if="t.key === 'unread'" class="filter-count">({{ unreadCount }})</span>
            <span v-else-if="stats && stats.by_type" class="filter-count">({{ stats.by_type[t.key] || 0 }})</span>
          </el-tag>
        </div>
        <div class="filter-actions">
          <el-button size="small" :disabled="unreadCount === 0" @click="handleReadAll">
            全部标为已读
          </el-button>
          <el-button size="small" @click="refresh">
            <el-icon><Refresh /></el-icon>刷新
          </el-button>
        </div>
      </div>
    </el-card>

    <el-card shadow="never" class="list-card" v-loading="loading">
      <div v-if="items.length === 0" class="empty-box">
        <el-empty description="暂无消息" />
      </div>

      <div v-for="msg in items" :key="msg.id" class="msg-item" :class="{ 'msg-unread': !msg.is_read }">
        <div class="msg-dot" v-if="!msg.is_read"></div>
        <div class="msg-icon-box">
          <div class="msg-icon" :class="`msg-icon-${msg.msg_type}`">
            <el-icon :size="18">{{ typeIcon(msg.msg_type) }}</el-icon>
          </div>
        </div>
        <div class="msg-body" @click="handleClick(msg)">
          <div class="msg-title-row">
            <span class="msg-title">{{ msg.title }}</span>
            <span class="msg-time">{{ formatTime(msg.created_at) }}</span>
          </div>
          <div class="msg-content">{{ msg.content || '（无内容）' }}</div>
          <div class="msg-meta">
            <el-tag size="small" :type="typeTag(msg.msg_type)" effect="light">{{ typeLabel(msg.msg_type) }}</el-tag>
            <span v-if="msg.sender_name" class="msg-sender">来自: {{ msg.sender_name }}</span>
          </div>
        </div>
        <div class="msg-actions">
          <el-button v-if="!msg.is_read" size="small" link type="primary" @click.stop="handleRead(msg)">
            标已读
          </el-button>
          <el-button size="small" link type="danger" @click.stop="handleDelete(msg)">
            删除
          </el-button>
        </div>
      </div>

      <div v-if="items.length > 0" class="pagination-wrap">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @change="refresh"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Bell, ChatLineRound, List, Warning, EditPen, User, Promotion } from '@element-plus/icons-vue'
import { messageApi } from '@/api'

const router = useRouter()

const loading = ref(false)
const items = ref([])
const total = ref(0)
const unreadCount = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const activeFilter = ref('all')
const stats = ref(null)

const filterTabs = [
  { key: 'all', label: '全部' },
  { key: 'unread', label: '未读' },
  { key: 'notice', label: '通知公告' },
  { key: 'approval', label: '审批流程' },
  { key: 'smart_form', label: '智能表格' },
  { key: 'todo', label: '待办事项' },
  { key: 'system', label: '系统消息' },
]

const labelMap = {
  notice: '通知公告', approval: '审批流程', smart_form: '智能表格',
  todo: '待办事项', mention: '@我', system: '系统消息',
}
const tagMap = {
  notice: 'warning', approval: 'danger', smart_form: 'primary',
  todo: 'info', mention: 'success', system: '',
}
const iconMap = {
  notice: 'Bell', approval: 'Promotion', smart_form: 'EditPen',
  todo: 'List', mention: 'ChatLineRound', system: 'Warning',
}

function typeLabel(t) { return labelMap[t] || t }
function typeTag(t) { return tagMap[t] || '' }
function typeIcon(t) { return iconMap[t] || 'User' }

function formatTime(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  const pad = n => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

async function refresh() {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value,
    }
    if (activeFilter.value === 'unread') params.is_read = false
    else if (activeFilter.value !== 'all') params.msg_type = activeFilter.value

    const [listRes, statsRes, unreadRes] = await Promise.all([
      messageApi.list(params),
      messageApi.stats(),
      messageApi.unreadCount(),
    ])
    items.value = listRes.items || []
    total.value = listRes.total || 0
    stats.value = statsRes
    unreadCount.value = unreadRes.unread_count || 0
    // 更新全局 store 中的未读计数
    try {
      const ev = new CustomEvent('unread-message-count', { detail: unreadCount.value })
      window.dispatchEvent(ev)
    } catch (e) {}
  } finally {
    loading.value = false
  }
}

async function handleRead(msg) {
  try {
    await messageApi.read(msg.id)
    msg.is_read = true
    msg.read_at = new Date().toISOString()
    unreadCount.value = Math.max(0, unreadCount.value - 1)
    try { window.dispatchEvent(new CustomEvent('unread-message-count', { detail: unreadCount.value })) } catch (e) {}
  } catch (e) {}
}

async function handleReadAll() {
  try {
    const r = await messageApi.readAll()
    ElMessage.success(`已标记 ${r.marked || 0} 条为已读`)
    unreadCount.value = 0
    await refresh()
  } catch (e) {}
}

async function handleDelete(msg) {
  try {
    await ElMessageBox.confirm('确定删除这条消息吗？', '提示', { type: 'warning' })
    await messageApi.delete(msg.id)
    ElMessage.success('删除成功')
    await refresh()
  } catch (e) {
    if (e !== 'cancel') {}
  }
}

function handleClick(msg) {
  // 未读的先标已读
  if (!msg.is_read) handleRead(msg)
  // 按 extra.router 跳转
  const path = msg.extra?.router
  if (path) {
    const tab = msg.extra?.tab
    if (tab) {
      router.push({ path, query: { tab } })
    } else {
      router.push(path)
    }
  }
}

let pollTimer = null
onMounted(() => {
  refresh()
  // 30秒轮询一次未读，保持同步
  pollTimer = setInterval(async () => {
    try {
      const r = await messageApi.unreadCount()
      unreadCount.value = r.unread_count || 0
      window.dispatchEvent(new CustomEvent('unread-message-count', { detail: unreadCount.value }))
    } catch (e) {}
  }, 30000)
})
onBeforeUnmount(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<style scoped>
.message-center {
  padding: 12px 20px;
}
.filter-card {
  margin-bottom: 12px;
}
.filter-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.filter-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.filter-tag {
  cursor: pointer;
  user-select: none;
}
.filter-count {
  opacity: 0.7;
  font-weight: 400;
  margin-left: 2px;
}
.list-card {
  min-height: 400px;
}
.empty-box {
  padding: 60px 0;
}
.msg-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 12px;
  border-bottom: 1px solid #f0f0f0;
  position: relative;
  transition: background 0.15s;
}
.msg-item:last-child { border-bottom: none; }
.msg-item:hover {
  background: #fafbfc;
}
.msg-unread {
  background: #f5faff;
}
.msg-dot {
  position: absolute;
  left: 0;
  top: 20px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #f56c6c;
}
.msg-icon-box {
  flex-shrink: 0;
  padding-top: 2px;
}
.msg-icon {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-weight: 600;
}
.msg-icon-notice     { background: linear-gradient(135deg, #f7ba2a, #e6a23c); }
.msg-icon-approval   { background: linear-gradient(135deg, #f56c6c, #c45656); }
.msg-icon-smart_form { background: linear-gradient(135deg, #409eff, #3076c4); }
.msg-icon-todo       { background: linear-gradient(135deg, #909399, #606266); }
.msg-icon-mention    { background: linear-gradient(135deg, #67c23a, #529b2e); }
.msg-icon-system     { background: linear-gradient(135deg, #8d83ea, #6a5cae); }
.msg-body {
  flex: 1;
  cursor: pointer;
  min-width: 0;
}
.msg-title-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 4px;
}
.msg-title {
  font-size: 15px;
  font-weight: 600;
  color: #1f2937;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.msg-time {
  font-size: 12px;
  color: #9ca3af;
  flex-shrink: 0;
}
.msg-content {
  font-size: 13px;
  color: #4b5563;
  line-height: 1.5;
  margin-bottom: 8px;
  white-space: pre-wrap;
  word-break: break-all;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.msg-meta {
  display: flex;
  align-items: center;
  gap: 10px;
}
.msg-sender {
  font-size: 12px;
  color: #6b7280;
}
.msg-actions {
  flex-shrink: 0;
  padding-top: 4px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  padding: 16px 4px 0;
}
</style>
