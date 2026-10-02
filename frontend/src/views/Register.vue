<template>
  <div class="register-page">
    <div class="bg-decoration">
      <div class="circle circle-1"></div>
      <div class="circle circle-2"></div>
      <div class="circle circle-3"></div>
    </div>

    <div class="register-container">
      <div class="register-brand">
        <div class="brand-logo">
          <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M32 4L4 18V46L32 60L60 46V18L32 4Z" stroke="currentColor" stroke-width="2" fill="none"/>
            <path d="M32 12L12 22V42L32 52L52 42V22L32 12Z" stroke="currentColor" stroke-width="1.5" fill="none" opacity="0.6"/>
            <circle cx="32" cy="32" r="8" fill="currentColor" opacity="0.8"/>
          </svg>
        </div>
        <h1>创建账号</h1>
        <p class="brand-subtitle">凭单位预导入名单自助注册</p>
        <div class="register-tips">
          <div class="tip-title">注册说明</div>
          <div class="tip-item">• 需单位管理员预先将您（姓名+身份证号）导入名单</div>
          <div class="tip-item">• 匹配成功后自动绑定单位，无需审核</div>
          <div class="tip-item">• 注册成功后即可登录系统使用</div>
        </div>
      </div>

      <div class="register-form-wrapper">
        <div class="register-card">
          <div class="register-header">
            <h2>用户注册</h2>
            <p>填写以下信息完成账号注册</p>
          </div>

          <el-form :model="form" :rules="rules" ref="formRef" label-position="top">
            <el-form-item label="用户名" prop="username">
              <el-input v-model="form.username" placeholder="登录用用户名（2-50位）" clearable size="large" />
            </el-form-item>
            <el-form-item label="密码" prop="password">
              <el-input v-model="form.password" type="password" placeholder="至少6位" show-password size="large" />
            </el-form-item>
            <el-form-item label="确认密码" prop="confirm_password">
              <el-input v-model="form.confirm_password" type="password" placeholder="再次输入密码" show-password size="large" />
            </el-form-item>
            <el-form-item label="姓名" prop="name">
              <el-input v-model="form.name" placeholder="本人真实姓名（须与名单一致）" clearable size="large" />
            </el-form-item>
            <el-form-item label="身份证号" prop="id_card">
              <el-input v-model="form.id_card" placeholder="18位身份证号" maxlength="18" clearable size="large" />
            </el-form-item>
            <el-button type="primary" size="large" :loading="loading" @click="handleRegister" class="register-btn">
              注 册
            </el-button>
            <div class="register-footer">
              已有账号？<router-link to="/login">去登录</router-link>
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
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

const formRef = ref()
const loading = ref(false)
const form = reactive({ username: '', password: '', confirm_password: '', name: '', id_card: '' })
const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 2, max: 50, message: '长度 2-50', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '至少 6 位', trigger: 'blur' },
  ],
  confirm_password: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== form.password) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur',
    },
  ],
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  id_card: [
    { required: true, message: '请输入身份证号', trigger: 'blur' },
    { len: 18, message: '须为 18 位', trigger: 'blur' },
  ],
}

const handleRegister = async () => {
  await formRef.value.validate()
  loading.value = true
  try {
    await auth.register(form)
    ElMessage.success('注册成功，请登录')
    router.push('/login')
  } catch (e) {
    // 错误信息由拦截器统一提示
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.register-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1a2b1e 0%, #243528 40%, #1e3322 100%);
  position: relative;
  overflow: hidden;
  padding: 40px 20px;
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
  width: 500px;
  height: 500px;
  background: #c4a000;
  top: -150px;
  left: -100px;
}

.circle-2 {
  width: 350px;
  height: 350px;
  background: #4a8a3e;
  bottom: -100px;
  right: -80px;
}

.circle-3 {
  width: 180px;
  height: 180px;
  border: 2px solid #c4a000;
  top: 30%;
  right: 40%;
  opacity: 0.08;
}

.register-container {
  display: flex;
  width: 960px;
  min-height: 620px;
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

.register-brand {
  flex: 0.85;
  background: linear-gradient(160deg, #1a2b1e 0%, #2d5a27 60%, #3a6a33 100%);
  padding: 48px 36px;
  color: #ffffff;
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
}

.register-brand::before {
  content: '';
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 30% 20%, rgba(196, 160, 0, 0.12) 0%, transparent 50%),
    radial-gradient(circle at 70% 80%, rgba(196, 160, 0, 0.08) 0%, transparent 40%);
  pointer-events: none;
}

.brand-logo {
  width: 56px;
  height: 56px;
  color: #c4a000;
  margin-bottom: 24px;
  position: relative;
  z-index: 1;
}

.brand-logo svg {
  width: 100%;
  height: 100%;
}

.register-brand h1 {
  font-size: 22px;
  font-weight: 700;
  margin: 0 0 8px;
  letter-spacing: 1px;
  position: relative;
  z-index: 1;
}

.brand-subtitle {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.65);
  margin: 0 0 36px;
  letter-spacing: 0.5px;
  position: relative;
  z-index: 1;
}

.register-tips {
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  padding: 16px;
  position: relative;
  z-index: 1;
}

.tip-title {
  font-size: 13px;
  font-weight: 600;
  color: #c4a000;
  margin-bottom: 10px;
}

.tip-item {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.7);
  line-height: 1.8;
}

.register-form-wrapper {
  flex: 1;
  padding: 40px 40px 28px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.register-card {
  width: 100%;
}

.register-header {
  margin-bottom: 24px;
}

.register-header h2 {
  font-size: 24px;
  font-weight: 700;
  color: #1a2b1e;
  margin: 0 0 6px;
}

.register-header p {
  font-size: 13px;
  color: #8a9a8e;
  margin: 0;
}

:deep(.el-form-item__label) {
  font-size: 13px;
  color: #4a5a4e;
  font-weight: 500;
  padding-bottom: 4px;
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

.register-btn {
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

.register-btn:hover {
  background: linear-gradient(135deg, #3a6a33 0%, #4a7a43 100%) !important;
  box-shadow: 0 6px 20px rgba(45, 90, 39, 0.3);
  transform: translateY(-1px);
}

.register-btn:active {
  transform: translateY(0);
}

.register-footer {
  text-align: center;
  margin-top: 16px;
  font-size: 13px;
}

.register-footer a {
  color: #4a8a3e;
  text-decoration: none;
  font-weight: 500;
}

.register-footer a:hover {
  color: #2d5a27;
  text-decoration: underline;
}

.copyright {
  text-align: center;
  font-size: 12px;
  color: #b0bab2;
  margin: 20px 0 0;
}

@media (max-width: 768px) {
  .register-container {
    flex-direction: column;
    width: 94%;
    max-width: 440px;
    min-height: auto;
  }

  .register-brand {
    display: none;
  }

  .register-form-wrapper {
    padding: 28px 24px 20px;
  }
}
</style>
