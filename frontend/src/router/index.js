import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/Login.vue'),
    meta: { public: true, title: '登录' },
  },
  {
    path: '/register',
    name: 'register',
    component: () => import('@/views/Register.vue'),
    meta: { public: true, title: '注册' },
  },
  {
    path: '/change-password',
    name: 'change-password',
    component: () => import('@/views/FirstLoginChangePassword.vue'),
    meta: { public: true, title: '首次登录改密' },
  },
  {
    path: '/',
    component: () => import('@/layouts/MainLayout.vue'),
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'dashboard',
        component: () => import('@/views/Dashboard.vue'),
        meta: { title: '工作台', icon: 'Odometer' },
      },
      {
        path: 'my-profile',
        name: 'my-profile',
        component: () => import('@/views/MyProfile.vue'),
        meta: { title: '我的信息', icon: 'User', roles: ['person'] },
      },
      // ---- 人员管理 ----
      {
        path: 'persons',
        name: 'persons',
        component: () => import('@/views/PersonList.vue'),
        meta: { title: '人员档案', icon: 'UserFilled', group: '人员管理', groupIcon: 'UserFilled', roles: ['unit_admin', 'super_admin', 'system_admin', 'security_officer'] },
      },
      {
        path: 'persons/:id',
        name: 'person-detail',
        component: () => import('@/views/PersonDetail.vue'),
        meta: { title: '人员详情', hideInMenu: true },
      },
      {
        path: 'hr-management',
        name: 'hr-management',
        component: () => import('@/views/HrManagement.vue'),
        meta: { title: '在职人事管理', icon: 'Calendar', group: '人员管理', groupIcon: 'UserFilled', roles: ['unit_admin', 'super_admin', 'system_admin', 'hr'] },
      },
      {
        path: 'hr-exit-batch',
        name: 'hr-exit-batch',
        component: () => import('@/views/HrExitBatch.vue'),
        meta: { title: '离职/复核/批量', icon: 'Switch', group: '人员管理', groupIcon: 'UserFilled', roles: ['unit_admin', 'super_admin', 'system_admin'] },
      },
      {
        path: 'roster',
        name: 'roster',
        component: () => import('@/views/RosterManage.vue'),
        meta: { title: '人员名单', icon: 'Notebook', group: '人员管理', groupIcon: 'UserFilled', roles: ['unit_admin', 'super_admin', 'system_admin', 'security_officer'] },
      },
      {
        path: 'custom-fields',
        name: 'custom-fields',
        component: () => import('@/views/CustomFields.vue'),
        meta: { title: '字段管理', icon: 'Document', group: '人员管理', groupIcon: 'UserFilled', roles: ['unit_admin', 'super_admin', 'system_admin'] },
      },
      {
        path: 'resume-import',
        name: 'resume-import',
        component: () => import('@/views/ResumeImport.vue'),
        meta: { title: '简历表导入', icon: 'Upload', group: '人员管理', groupIcon: 'UserFilled', roles: ['unit_admin', 'super_admin', 'system_admin'] },
      },
      // ---- 组织架构 ----
      {
        path: 'units',
        name: 'units',
        component: () => import('@/views/UnitManage.vue'),
        meta: { title: '单位管理', icon: 'OfficeBuilding', group: '组织架构', groupIcon: 'Share', roles: ['super_admin'] },
      },
      {
        path: 'departments',
        name: 'departments',
        component: () => import('@/views/DepartmentManage.vue'),
        meta: { title: '部门管理', icon: 'Share', group: '组织架构', groupIcon: 'Share', roles: ['unit_admin', 'super_admin'] },
      },
      {
        path: 'positions',
        name: 'positions',
        component: () => import('@/views/PositionManage.vue'),
        meta: { title: '岗位管理', icon: 'Postcard', group: '组织架构', groupIcon: 'Share', roles: ['unit_admin', 'super_admin'] },
      },
      {
        path: 'ranks',
        name: 'ranks',
        component: () => import('@/views/RankManage.vue'),
        meta: { title: '职级管理', icon: 'Medal', group: '组织架构', groupIcon: 'Share', roles: ['unit_admin', 'super_admin'] },
      },
      // ---- 统计报表 ----
      {
        path: 'reports',
        name: 'reports',
        component: () => import('@/views/Reports.vue'),
        meta: { title: '统计报表', icon: 'DataAnalysis', group: '统计报表', groupIcon: 'DataAnalysis', roles: ['unit_admin', 'super_admin'] },
      },
      {
        path: 'report-templates',
        name: 'report-templates',
        component: () => import('@/views/ReportTemplates.vue'),
        meta: { title: '报表模板', icon: 'Files', group: '统计报表', groupIcon: 'DataAnalysis', roles: ['unit_admin', 'super_admin'] },
      },
      // ---- 系统管理 ----
      {
        path: 'unit-admins',
        name: 'unit-admins',
        component: () => import('@/views/UnitAdmins.vue'),
        meta: { title: '管理员账号', icon: 'UserFilled', group: '系统管理', groupIcon: 'Setting', roles: ['super_admin', 'system_admin'] },
      },
      {
        path: 'admin-applications',
        name: 'admin-applications',
        component: () => import('@/views/AdminApplications.vue'),
        meta: { title: '管理员审批', icon: 'Check', group: '系统管理', groupIcon: 'Setting', roles: ['super_admin', 'system_admin'] },
      },
      {
        path: 'hr-accounts',
        name: 'hr-accounts',
        component: () => import('@/views/HrAccountManage.vue'),
        meta: { title: '账号管理', icon: 'UserFilled', group: '系统管理', groupIcon: 'Setting', roles: ['unit_admin', 'super_admin', 'system_admin'] },
      },
      {
        path: 'roles',
        name: 'roles',
        component: () => import('@/views/RoleManage.vue'),
        meta: { title: '角色权限', icon: 'Lock', group: '系统管理', groupIcon: 'Setting', roles: ['super_admin', 'security_officer'] },
      },
      {
        path: 'operation-logs',
        name: 'operation-logs',
        component: () => import('@/views/OperationLogs.vue'),
        meta: { title: '审计日志', icon: 'Document', group: '系统管理', groupIcon: 'Setting', roles: ['super_admin', 'auditor'] },
      },
      {
        path: 'database-backup',
        name: 'database-backup',
        component: () => import('@/views/DatabaseBackup.vue'),
        meta: { title: '数据备份', icon: 'FolderOpened', group: '系统管理', groupIcon: 'Setting', roles: ['super_admin', 'system_admin'] },
      },
      {
        path: 'clearance-manage',
        name: 'clearance-manage',
        component: () => import('@/views/ClearanceManage.vue'),
        meta: { title: '涉密分级管控', icon: 'Lock', group: '系统管理', groupIcon: 'Setting', roles: ['super_admin', 'security_officer'] },
      },
      // ---- 日常办公 ----
      {
        path: 'notices',
        name: 'notices',
        component: () => import('@/views/NoticeList.vue'),
        meta: { title: '通知公告', icon: 'Bell', group: '日常办公', groupIcon: 'Calendar' },
      },
      {
        path: 'todos',
        name: 'todos',
        component: () => import('@/views/TodoList.vue'),
        meta: { title: '待办事项', icon: 'List', group: '日常办公', groupIcon: 'Calendar' },
      },
      {
        path: 'workflow',
        name: 'workflow',
        component: () => import('@/views/WorkflowList.vue'),
        meta: { title: '流程审批', icon: 'SetUp', group: '日常办公', groupIcon: 'Calendar' },
      },
      {
        path: 'smart-forms',
        name: 'smart-forms',
        component: () => import('@/views/SmartFormList.vue'),
        meta: { title: '智能表格', icon: 'Document', group: '日常办公', groupIcon: 'Calendar' },
      },
      {
        path: 'ai-assistant',
        name: 'ai-assistant',
        component: () => import('@/views/AiAssistant.vue'),
        meta: { title: 'AI智能助手', icon: 'ChatDotRound', group: '日常办公', groupIcon: 'Calendar' },
      },
      {
        path: 'knowledge-base',
        name: 'knowledge-base',
        component: () => import('@/views/KnowledgeBase.vue'),
        meta: { title: '知识库管理', icon: 'Collection', group: '日常办公', groupIcon: 'Calendar', roles: ['super_admin', 'unit_admin', 'hr', 'system_admin', 'security_officer'] },
      },
      // ---- 消息中心（不在侧边栏展示菜单） ----
      {
        path: 'messages',
        name: 'messages',
        component: () => import('@/views/MessageCenter.vue'),
        meta: { title: '消息中心', icon: 'Bell', hideInMenu: true },
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const auth = useAuthStore()
  document.title = `${to.meta.title || ''} - 人员基本信息系统`

  if (to.meta.public) {
    // 已登录用户访问登录页，跳转首页
    if (to.name === 'login' && auth.isLoggedIn) return next('/')
    return next()
  }

  if (!auth.isLoggedIn) {
    return next({ name: 'login', query: { redirect: to.fullPath } })
  }

  // 角色校验（super_admin 可访问所有页面）
  if (to.meta.roles && auth.role !== 'super_admin' && !to.meta.roles.includes(auth.role)) {
    return next({ name: 'dashboard' })
  }

  // 首次登录强制改密（除改密页本身）
  if (auth.isFirstLogin && to.name !== 'change-password') {
    return next({ name: 'change-password' })
  }

  next()
})

export default router
