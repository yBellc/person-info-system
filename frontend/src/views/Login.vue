<template>
  <div class="login-page">
    <div class="bg-decoration">
      <div class="circle circle-1"></div>
      <div class="circle circle-2"></div>
      <div class="circle circle-3"></div>
    </div>

    <div class="login-container">
      <div class="login-brand">
        <div class="brand-logo">
          <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M32 4L4 18V46L32 60L60 46V18L32 4Z" stroke="currentColor" stroke-width="2" fill="none"/>
            <path d="M32 12L12 22V42L32 52L52 42V22L32 12Z" stroke="currentColor" stroke-width="1.5" fill="none" opacity="0.6"/>
            <circle cx="32" cy="32" r="8" fill="currentColor" opacity="0.8"/>
          </svg>
        </div>
        <h1>单位内部信息管理系统</h1>
        <p class="brand-subtitle">综合信息管理平台</p>
        <div class="brand-features">
          <div class="feature-item"><span class="feature-dot"></span>人员档案管理</div>
          <div class="feature-item"><span class="feature-dot"></span>智能审批流程</div>
          <div class="feature-item"><span class="feature-dot"></span>AI 报表生成</div>
        </div>
      </div>

      <div class="login-form-wrapper">
        <div class="login-card">
          <div class="login-header">
            <h2>欢迎登录</h2>
            <p>请输入您的账号信息</p>
          </div>

          <el-form :model="form" :rules="rules" ref="formRef" @keyup.enter="handleLogin">
            <el-form-item prop="username">
              <el-input
                v-model="form.username"
                placeholder="请输入用户名"
                :prefix-icon="User"
                size="large"
                clearable
              />
            </el-form-item>
            <el-form-item prop="password">
              <el-input
                v-model="form.password"
                type="password"
                placeholder="请输入密码"
                :prefix-icon="Lock"
                size="large"
                show-password
              />
            </el-form-item>

            <div class="form-options">
              <el-checkbox v-model="rememberMe" size="small">记住我</el-checkbox>
            </div>

            <el-button
              class="login-btn"
              size="large"
              :loading="loading"
              @click="handleLogin"
            >
              登 录
            </el-button>

            <div class="login-footer">
              <router-link to="/register">没有账号？点击注册</router-link>
            </div>
          </el-form>
        </div>
        <p class="copyright">© 单位内部信息管理系统 · 仅供内部使用</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { User, Lock } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const formRef = ref()
const loading = ref(false)
const rememberMe = ref(false)
const form = reactive({ username: '', password: '' })
const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

const handleLogin = async () => {
  await formRef.value.validate()
  loading.value = true
  try {
    const data = await auth.login(form.username, form.password)
    if (data.first_login) {
      ElMessage.info('首次登录，请先修改密码')
      router.push('/change-password')
    } else {
      ElMessage.success('登录成功')
      router.push(route.query.redirect || '/')
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1a2b1e 0%, #243528 40%, #1e3322 100%);
  position: relative;
  overflow: hidden;
}

.bg-decoration {
  position: absolute;
  inset: 0;
  pointer-events: none;
  overflow: hidden;
}

.circle {
  position: absolute;
  border-radius: 50%;
  opacity: 0.06;
}

.circle-1 {
  width: 600px;
  height: 600px;
  background: #c4a000;
  top: -200px;
  right: -100px;
}

.circle-2 {
  width: 400px;
  height: 400px;
  background: #4a8a3e;
  bottom: -150px;
  left: -100px;
}

.circle-3 {
  width: 200px;
  height: 200px;
  border: 2px solid #c4a000;
  top: 40%;
  left: 55%;
  opacity: 0.08;
}

.login-container {
  display: flex;
  width: 920px;
  min-height: 520px;
  background: #ffffff;
  border-radius: 16px;
  overflow: hidden;
  box-shadow:
    0 20px 60px rgba(0, 0, 0, 0.3),
    0 8px 24px rgba(0, 0, 0, 0.15),
    0 0 0 1px rgba(196, 160, 0, 0.2);
  position: relative;
  z-index: 1;
  animation: fadeSlideIn 0.6s cubic-bezier(0.22, 1, 0.36, 1);
}

@keyframes fadeSlideIn {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}

.login-brand {
  flex: 1;
  background: linear-gradient(160deg, #1a2b1e 0%, #2d5a27 60%, #3a6a33 100%);
  padding: 48px 40px;
  color: #ffffff;
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
}

.login-brand::before {
  content: '';
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 20% 20%, rgba(196, 160, 0, 0.12) 0%, transparent 50%),
    radial-gradient(circle at 80% 80%, rgba(196, 160, 0, 0.08) 0%, transparent 40%);
  pointer-events: none;
}

.brand-logo {
  width: 64px;
  height: 64px;
  color: #c4a000;
  margin-bottom: 28px;
  position: relative;
  z-index: 1;
}

.brand-logo svg {
  width: 100%;
  height: 100%;
}

.login-brand h1 {
  font-size: 24px;
  font-weight: 700;
  margin: 0 0 8px;
  letter-spacing: 1px;
  position: relative;
  z-index: 1;
}

.brand-subtitle {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.65);
  margin: 0 0 40px;
  letter-spacing: 0.5px;
  position: relative;
  z-index: 1;
}

.brand-features {
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin-top: auto;
  position: relative;
  z-index: 1;
}

.feature-item {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.75);
}

.feature-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #c4a000;
  box-shadow: 0 0 8px rgba(196, 160, 0, 0.5);
}

.login-form-wrapper {
  flex: 1;
  padding: 48px 44px 32px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.login-card {
  width: 100%;
}

.login-header {
  margin-bottom: 32px;
}

.login-header h2 {
  font-size: 26px;
  font-weight: 700;
  color: #1a2b1e;
  margin: 0 0 8px;
}

.login-header p {
  font-size: 14px;
  color: #8a9a8e;
  margin: 0;
}

.form-options {
  display: flex;
  justify-content: flex-end;
  margin: -8px 0 20px;
}

.form-options :deep(.el-checkbox__label) {
  font-size: 13px;
  color: #8a9a8e;
}

:deep(.el-input__wrapper) {
  background: #f7f9f7;
  border: 1px solid #e0e5e1;
  border-radius: 8px;
  box-shadow: none;
  padding: 4px 12px;
  transition: all 0.2s ease;
}

:deep(.el-input__wrapper:hover) {
  border-color: #4a8a3e;
  background: #ffffff;
}

:deep(.el-input__wrapper.is-focus) {
  border-color: #2d5a27;
  background: #ffffff;
  box-shadow: 0 0 0 3px rgba(45, 90, 39, 0.1);
}

:deep(.el-input__inner) {
  color: #1a2b1e;
  font-size: 14px;
}

:deep(.el-input__inner::placeholder) {
  color: #b0bab2;
}

:deep(.el-input__prefix-inner) {
  color: #4a8a3e;
}

.login-btn {
  width: 100%;
  height: 44px;
  background: linear-gradient(135deg, #2d5a27 0%, #3a6a33 100%) !important;
  border: none !important;
  color: #ffffff !important;
  font-weight: 600 !important;
  font-size: 15px !important;
  letter-spacing: 4px;
  border-radius: 8px !important;
  margin-top: 8px;
  transition: all 0.25s ease;
}

.login-btn:hover {
  background: linear-gradient(135deg, #3a6a33 0%, #4a7a43 100%) !important;
  box-shadow: 0 6px 20px rgba(45, 90, 39, 0.3);
  transform: translateY(-1px);
}

.login-btn:active {
  transform: translateY(0);
}

.login-footer {
  text-align: center;
  margin-top: 20px;
  font-size: 13px;
}

.login-footer a {
  color: #4a8a3e;
  text-decoration: none;
  transition: color 0.2s;
}

.login-footer a:hover {
  color: #2d5a27;
  text-decoration: underline;
}

.copyright {
  text-align: center;
  font-size: 12px;
  color: #b0bab2;
  margin: 28px 0 0;
}

@media (max-width: 768px) {
  .login-container {
    flex-direction: column;
    width: 92%;
    max-width: 420px;
    min-height: auto;
  }

  .login-brand {
    padding: 32px 28px;
  }

  .brand-features {
    display: none;
  }

  .login-form-wrapper {
    padding: 32px 28px 24px;
  }
}
</style>
