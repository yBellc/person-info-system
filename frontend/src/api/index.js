import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 120000,  // 默认 2 分钟（文件解析/上传较慢）
})

// 请求拦截：带上 token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截：统一错误处理
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const msg = error.response?.data?.detail || error.message || '请求失败'
    if (error.response?.status === 401) {
      // 未认证：清除登录态，跳登录
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      if (router.currentRoute.value.path !== '/login') {
        ElMessage.error('登录已过期，请重新登录')
        router.push('/login')
      }
    } else {
      ElMessage.error(msg)
    }
    return Promise.reject(error)
  }
)

export default api

// ============ 组织架构 API ============

// 部门管理
export const departmentApi = {
  list: (params) => api.get('/departments/', { params }),
  tree: (unitId) => api.get('/departments/tree', { params: { unit_id: unitId } }),
  get: (id) => api.get(`/departments/${id}`),
  create: (data) => api.post('/departments/', data),
  update: (id, data) => api.put(`/departments/${id}`, data),
  delete: (id) => api.delete(`/departments/${id}`),
}

// 职级管理
export const rankApi = {
  list: (params) => api.get('/ranks/', { params }),
  create: (data) => api.post('/ranks/', data),
  update: (id, data) => api.put(`/ranks/${id}`, data),
  delete: (id) => api.delete(`/ranks/${id}`),
}

// 岗位管理
export const positionApi = {
  list: (params) => api.get('/positions/', { params }),
  create: (data) => api.post('/positions/', data),
  update: (id, data) => api.put(`/positions/${id}`, data),
  delete: (id) => api.delete(`/positions/${id}`),
}

// 人员岗位
export const personPositionApi = {
  list: (params) => api.get('/person-positions/', { params }),
  create: (data) => api.post('/person-positions/', data),
  update: (id, data) => api.put(`/person-positions/${id}`, data),
  delete: (id) => api.delete(`/person-positions/${id}`),
}

// ============ 权限管理 API ============

export const roleApi = {
  list: (params) => api.get('/roles', { params }),
  create: (data) => api.post('/roles', data),
  update: (id, data) => api.put(`/roles/${id}`, data),
  delete: (id) => api.delete(`/roles/${id}`),
}

export const userRoleApi = {
  list: (params) => api.get('/user-roles', { params }),
  create: (data) => api.post('/user-roles', data),
  delete: (id) => api.delete(`/user-roles/${id}`),
}

export const dataPermissionApi = {
  list: (params) => api.get('/data-permissions', { params }),
  create: (data) => api.post('/data-permissions', data),
  update: (id, data) => api.put(`/data-permissions/${id}`, data),
  delete: (id) => api.delete(`/data-permissions/${id}`),
}

export const fieldPermissionApi = {
  list: (params) => api.get('/field-permissions', { params }),
  create: (data) => api.post('/field-permissions', data),
  update: (id, data) => api.put(`/field-permissions/${id}`, data),
  delete: (id) => api.delete(`/field-permissions/${id}`),
}

export const myPermissionsApi = {
  get: () => api.get('/my-permissions'),
}

// ============ 人事账号管理 API ============

export const hrAccountApi = {
  // 名单管理
  roster: (params) => api.get('/auth/hr/roster', { params }),
  importRoster: (items) => api.post('/auth/hr/roster/import', items),
  // 创建账号
  createAccount: (data) => api.post('/auth/hr/create-account', data),
  batchCreate: (data) => api.post('/auth/hr/batch-create', data),
  // 账号列表
  accounts: (params) => api.get('/auth/hr/accounts', { params }),
  // 重置密码
  resetPassword: (userId, newPassword) => api.put(`/auth/hr/accounts/${userId}/reset-password`, null, { params: { new_password: newPassword } }),
  // 启用/停用
  toggleAccount: (userId) => api.put(`/auth/hr/accounts/${userId}/toggle`),
}

// ============ 首次登录改密 API ============

export const authApi = {
  login: (data) => api.post('/auth/login', data),
  me: () => api.get('/auth/me'),
  changePassword: (data) => api.post('/auth/change-password', data),
  firstLoginChangePassword: (data) => api.post('/auth/first-login-change-password', data),
}

// ============ 工作台 API ============

export const todoApi = {
  list: (params) => api.get('/todos', { params }),
  create: (data) => api.post('/todos', data),
  update: (id, data) => api.put(`/todos/${id}`, data),
  delete: (id) => api.delete(`/todos/${id}`),
  complete: (id) => api.post(`/todos/${id}/complete`),
}

export const noticeApi = {
  list: (params) => api.get('/notices', { params }),
  create: (data) => api.post('/notices', data),
  update: (id, data) => api.put(`/notices/${id}`, data),
  delete: (id) => api.delete(`/notices/${id}`),
  read: (id) => api.post(`/notices/${id}/read`),
  readAll: () => api.post('/notices/read-all'),
}

export const workspaceApi = {
  stats: () => api.get('/stats'),
}

// ============ 统一站内消息中心 API ============

export const messageApi = {
  // 分页获取消息列表
  list: (params) => api.get('/messages', { params }),
  // 消息统计（总数、未读、按类型）
  stats: () => api.get('/messages/stats'),
  // 顶部铃铛未读总数（轻量，轮询用）
  unreadCount: () => api.get('/messages/unread-count'),
  // 单条标为已读
  read: (id) => api.put(`/messages/${id}/read`),
  // 全部标为已读
  readAll: () => api.put('/messages/read-all'),
  // 删除一条消息
  delete: (id) => api.delete(`/messages/${id}`),
}

// ============ OA流程引擎 API ============

export const workflowTemplateApi = {
  list: (params) => api.get('/workflow-templates', { params }),
  create: (data) => api.post('/workflow-templates', data),
  update: (id, data) => api.put(`/workflow-templates/${id}`, data),
  delete: (id) => api.delete(`/workflow-templates/${id}`),
}

export const workflowApi = {
  list: (params) => api.get('/workflow-instances', { params }),
  get: (id) => api.get(`/workflow-instances/${id}`),
  create: (data) => api.post('/workflow-instances', data),
  approve: (id, data) => api.post(`/workflow-instances/${id}/approve`, data),
  withdraw: (id) => api.post(`/workflow-instances/${id}/withdraw`),
}

// ============ 报销管理 API ============

export const expenseApi = {
  // 附件
  uploadAttachments: (instanceId, files) => {
    const formData = new FormData()
    files.forEach(f => formData.append('files', f))
    return api.post(`/workflow-instances/${instanceId}/attachments`, formData, {
      timeout: 120000,
    })
  },
  listAttachments: (instanceId) => api.get(`/workflow-instances/${instanceId}/attachments`),
  deleteAttachment: (id) => api.delete(`/attachments/${id}`),
  // 发票
  ocrInvoice: (attachmentId) => api.post(`/attachments/${attachmentId}/ocr`),
  verifyInvoice: (data) => api.post('/invoice/verify', data),
  checkDuplicate: (data) => api.post('/invoice/check-duplicate', data),
  listInvoices: (instanceId) => api.get(`/workflow-instances/${instanceId}/invoices`),
  // 凭证
  generateVoucher: (data) => api.post('/vouchers/generate', data),
  getVoucher: (instanceId) => api.get(`/workflow-instances/${instanceId}/voucher`),
  listVouchers: (params) => api.get('/vouchers', { params }),
  cancelVoucher: (id) => api.delete(`/vouchers/${id}`),
}

// ============ 在职人事管理 API（考勤/绩效/奖惩/调岗/合同/培训） ============

export const hrApi = {
  // 考勤
  listAttendance: (params) => api.get('/hr/attendance', { params }),
  createAttendance: (data) => api.post('/hr/attendance', data),
  updateAttendance: (id, data) => api.put(`/hr/attendance/${id}`, data),

  // 绩效
  listPerformance: (params) => api.get('/hr/performance', { params }),
  createPerformance: (data) => api.post('/hr/performance', data),
  updatePerformance: (id, data) => api.put(`/hr/performance/${id}`, data),
  deletePerformance: (id) => api.delete(`/hr/performance/${id}`),

  // 奖惩
  listRewards: (params) => api.get('/hr/rewards', { params }),
  createReward: (data) => api.post('/hr/rewards', data),
  updateReward: (id, data) => api.put(`/hr/rewards/${id}`, data),
  deleteReward: (id) => api.delete(`/hr/rewards/${id}`),

  // 调岗/调动
  listTransfers: (params) => api.get('/hr/transfers', { params }),
  createTransfer: (data) => api.post('/hr/transfers', data),
  approveTransfer: (id, payload) => api.post(`/hr/transfers/${id}/approve`, payload),

  // 合同
  listContracts: (params) => api.get('/hr/contracts', { params }),
  createContract: (data) => api.post('/hr/contracts', data),
  updateContract: (id, data) => api.put(`/hr/contracts/${id}`, data),

  // 培训
  listTrainings: (params) => api.get('/hr/trainings', { params }),
  createTraining: (data) => api.post('/hr/trainings', data),
  deleteTraining: (id) => api.delete(`/hr/trainings/${id}`),
}

// ============ 离职管理 & 数据复核 API ============

export const hrExitApi = {
  // 离职
  listResignations: (params) => api.get('/hr-exit/resignations', { params }),
  createResignation: (data) => api.post('/hr-exit/resignations', data),
  deptApprove: (id, payload) => api.post(`/hr-exit/resignations/${id}/dept-approve`, payload),
  hrApprove: (id, payload) => api.post(`/hr-exit/resignations/${id}/hr-approve`, payload),
  leadApprove: (id, payload) => api.post(`/hr-exit/resignations/${id}/lead-approve`, payload),
  disableAccount: (id) => api.post(`/hr-exit/resignations/${id}/disable-account`),

  // 交接
  getHandoverItems: (rid) => api.get(`/hr-exit/resignations/${rid}/handover-items`),
  addHandoverItem: (rid, data) => api.post(`/hr-exit/resignations/${rid}/handover-items`, data),
  confirmHandover: (hid) => api.post(`/hr-exit/handover-items/${hid}/confirm-handover`),
  confirmReceiver: (hid) => api.post(`/hr-exit/handover-items/${hid}/confirm-receiver`),
  confirmSupervisor: (hid) => api.post(`/hr-exit/handover-items/${hid}/confirm-supervisor`),

  // 双人复核
  listChangeReviews: (params) => api.get('/hr-exit/change-reviews', { params }),
  proposeChange: (data) => api.post('/hr-exit/change-reviews/propose', data),
  approveChange: (id, payload) => api.post(`/hr-exit/change-reviews/${id}/approve`, payload),
  rejectChange: (id, payload) => api.post(`/hr-exit/change-reviews/${id}/reject`, payload),
}

// ============ 驾驶舱 / 审批分析 / 批量操作 / 三员分立 API ============

export const analyticsApi = {
  // 驾驶舱总览
  dashboardOverview: () => api.get('/dashboard/overview'),

  // 审批分析
  approvalAnalytics: (params) => api.get('/analytics/approval', { params }),

  // 批量操作
  batchTransferDepartment: (data) => api.post('/batch/transfer-department', data),
  batchImportAttendance: (formdata, year, month, config = {}) =>
    api.post(`/batch/import-excel-attendance?year=${year}&month=${month}`, formdata, {
      ...config, headers: { 'Content-Type': 'multipart/form-data' },
    }),
  batchCreatePersons: (list) => api.post('/batch/create-persons', list),

  // 三员分立
  assignTriRole: (userId, triRole) => api.post('/tri-officer/assign', null, { params: { user_id: userId, tri_role: triRole } }),
  triWhoAmI: () => api.get('/tri-officer/whoami'),
}

// ============ 系统管理 API（审计日志、备份） ============

export const systemApi = {
  // 操作日志
  operationLogs: (params) => api.get('/system/operation-logs', { params }),
  // 登录日志
  loginLogs: (params) => api.get('/system/login-logs', { params }),
  // 日志统计
  logsStats: () => api.get('/system/logs/stats'),
  // 清理过期日志
  cleanLogs: (days) => api.delete('/system/logs/clean', { params: { days } }),

  // 数据库备份
  listBackups: () => api.get('/system/backups'),
  createBackup: () => api.post('/system/backups/create'),
  downloadBackup: (filename) => `/api/v1/system/backups/${filename}/download`,
  deleteBackup: (filename) => api.delete(`/system/backups/${filename}`),

  // 涉密分级管控
  clearanceLevels: () => api.get('/system/clearance/levels'),
  listUserClearance: () => api.get('/system/clearance/users'),
  setUserClearance: (userId, level) => api.put(`/system/clearance/users/${userId}`, null, { params: { level } }),
}

// ============ 智能简历识别 API ============

export const resumeSmartApi = {
  // 单个简历智能解析
  parse: (file) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/resume-smart/parse', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000,
    })
  },
  // 批量简历智能解析
  batchParse: (files) => {
    const formData = new FormData()
    files.forEach(f => formData.append('files', f))
    return api.post('/resume-smart/batch-parse', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 300000,
    })
  },
  // 应用到现有人员档案
  applyToPerson: (personId, data) => api.post(`/resume-smart/apply-to-person/${personId}`, data),
  // 从简历创建人员档案+账号
  createWithAccount: (data) => api.post('/resume-smart/create-with-account', data),
  // 批量从简历创建
  batchCreate: (files, params) => {
    const formData = new FormData()
    files.forEach(f => formData.append('files', f))
    const query = new URLSearchParams(params).toString()
    return api.post(`/resume-smart/batch-create?${query}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 300000,
    })
  },
}

// ============ AI 智能助手 API（Ollama + RAG 知识库） ============

export const aiApi = {
  // AI 服务状态
  status: () => api.get('/ai/status'),
  // AI 对话（RAG增强）
  chat: (data) => api.post('/ai/chat', data, { timeout: 180000 }),
  // AI 生成表单字段
  generateForm: (data) => api.post('/ai/generate-form', data, { timeout: 120000 }),
  // 知识库文档上传
  uploadKbDoc: (file) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/ai/kb/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000,
    })
  },
  // 知识库检索
  searchKb: (params) => api.get('/ai/kb/search', { params }),
  // 知识库文档列表（新版：支持分类/关键词筛选）
  listKbDocs: (params) => api.get('/ai/kb/docs', { params }),
  // 知识库统计概览
  kbStats: () => api.get('/ai/kb/stats'),
  // 重建/增量入库知识库
  buildKb: (data) => api.post('/ai/kb/build', data, { timeout: 600000 }),
  // 删除知识库文档（新版：带索引+向量库清理）
  deleteKbDoc: (filename) => api.delete(`/ai/kb/docs/${encodeURIComponent(filename)}`),
}
