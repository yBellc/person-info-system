<template>
  <div class="change-pwd-page">
    <div class="change-pwd-card">
      <div class="header">
        <el-icon size="40" color="#e6a23c"><Key /></el-icon>
        <h2>首次登录 - 修改密码</h2>
        <p>您的账号使用初始密码登录，请设置新密码后继续使用</p>
      </div>
      <el-form :model="form" :rules="rules" ref="formRef">
        <el-form-item prop="new_password">
          <el-input
            v-model="form.new_password"
            type="password"
            placeholder="新密码（至少6位）"
            :prefix-icon="Lock"
            size="large"
            show-password
          />
        </el-form-item>
        <el-form-item prop="confirm_password">
          <el-input
            v-model="form.confirm_password"
            type="password"
            placeholder="确认新密码"
            :prefix-icon="Lock"
            size="large"
            show-password
          />
        </el-form-item>
        <el-button type="primary" size="large" :loading="loading" style="width: 100%" @click="handleSubmit">
          确认修改
        </el-button>
      </el-form>
      <el-alert
        title="修改成功后将进入系统主页"
        type="info"
        :closable="false"
        style="margin-top: 16px"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { Key, Lock } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()
const formRef = ref()
const loading = ref(false)

const form = reactive({ new_password: '', confirm_password: '' })

const rules = {
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码至少6位', trigger: 'blur' },
  ],
  confirm_password: [
    { required: true, message: '请确认新密码', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== form.new_password) callback(new Error('两次输入的密码不一致'))
        else callback()
      },
      trigger: 'blur',
    },
  ],
}

const handleSubmit = async () => {
  await formRef.value.validate()
  loading.value = true
  try {
    await auth.changeFirstPassword(form.new_password)
    ElMessage.success('密码修改成功，欢迎使用系统！')
    router.push('/')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.change-pwd-page {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
}
.change-pwd-card {
  width: 420px;
  padding: 40px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
}
.header {
  text-align: center;
  margin-bottom: 32px;
}
.header h2 {
  margin: 12px 0 4px;
  color: #303133;
}
.header p {
  color: #909399;
  font-size: 13px;
}
</style>
