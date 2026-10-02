<template>
  <div class="page-container">
    <div class="section-title">我的信息</div>

    <!-- 申请管理员入口（仅普通用户可见） -->
    <el-card v-if="auth.role === 'person'" style="margin-bottom: 16px">
      <div class="apply-bar">
        <div>
          <el-icon size="20" color="#e6a23c"><Promotion /></el-icon>
          <span style="margin-left: 8px; font-weight: 600">申请成为单位管理员</span>
          <span style="margin-left: 12px; color: #909399; font-size: 13px">
            管理员可维护本单位及下属单位的人员信息、名单、报表
          </span>
        </div>
        <div>
          <el-button v-if="myApplication?.status !== 'pending'" type="warning" plain @click="openApply">
            申请管理员
          </el-button>
          <el-tag v-else type="warning" size="large">审核中（提交于 {{ formatTime(myApplication.created_at) }}）</el-tag>
        </div>
      </div>
      <el-alert
        v-if="myApplication?.status === 'rejected'"
        type="error" :closable="false" style="margin-top: 12px"
        :title="`您的申请已被驳回${myApplication.review_note ? '：' + myApplication.review_note : ''}。可重新申请。`"
      />
      <el-alert
        v-if="myApplication?.status === 'approved'"
        type="success" :closable="false" style="margin-top: 12px"
        title="您的申请已批准，当前已是单位管理员。"
      />
    </el-card>

    <el-card v-loading="loading">
      <el-result v-if="!personId" icon="warning" title="未关联人员档案" sub-title="请联系单位管理员" />
      <template v-else>
        <div class="action-bar">
          <el-button type="primary" @click="editVisible = true">
            <el-icon><Edit /></el-icon>编辑我的信息
          </el-button>
          <el-button type="success" plain @click="openResumeUpload">
            <el-icon><Upload /></el-icon>上传简历自动填充
          </el-button>
        </div>
        <el-alert
          type="info"
          :closable="false"
          title="您可以填写和修改自己的基本信息。职务、职级、所属单位等字段需由单位管理员修改。"
          style="margin-bottom: 16px"
        />
        <PersonDetailInline v-if="person" :person="person" />
      </template>
    </el-card>

    <!-- 编辑对话框 -->
    <person-form-dialog
      v-model:visible="editVisible"
      :person="person"
      :units="[]"
      @saved="loadData"
    />

    <!-- 上传简历对话框 -->
    <el-dialog v-model="resumeUploadVisible" title="上传简历自动填充" width="560px">
      <el-alert
        type="info" :closable="false" style="margin-bottom: 16px"
        title="上传您的简历文件（.docx 或 .xlsx），系统会自动识别简历中的姓名、身份证、学历、联系方式等字段，并填充到您的个人信息表单中。您可以确认后再保存。"
      />
      <el-upload
        ref="resumeUploadRef"
        :auto-upload="false"
        :limit="1"
        accept=".docx,.xlsx"
        :on-change="onResumeFileChange"
        :on-exceed="onExceed"
        drag
      >
        <el-icon class="el-icon--upload"><upload-filled /></el-icon>
        <div class="el-upload__text">将简历文件拖到此处，或<em>点击选择</em></div>
        <template #tip>
          <div class="el-upload__tip">仅支持 .docx 和 .xlsx 格式，单个文件</div>
        </template>
      </el-upload>
      <template #footer>
        <el-button @click="resumeUploadVisible = false">取消</el-button>
        <el-button type="primary" :loading="resumeParsing" :disabled="!resumeFile" @click="onParseResume">
          智能识别
        </el-button>
      </template>
    </el-dialog>

    <!-- 识别结果预览对话框 -->
    <el-dialog v-model="resumeResultVisible" title="简历识别结果" width="720px" top="5vh">
      <el-alert
        v-if="resumeResult"
        type="success" :closable="false" style="margin-bottom: 16px"
        :title="`识别到 ${resumeResult.stats.flat_field_count} 个字段，${resumeResult.stats.sub_table_rows} 条子表记录`"
      />
      <div v-if="resumeResult" class="resume-result">
        <div class="result-section">
          <div class="result-section-title">基本信息（将填充到表单）</div>
          <div class="field-grid">
            <div v-for="(val, key) in resumeResult.flat_fields" :key="key" class="field-item">
              <span class="field-label">{{ fieldLabel(key) }}：</span>
              <span class="field-value">{{ val || '—' }}</span>
            </div>
          </div>
        </div>
        <div v-for="(items, tableKey) in resumeResult.sub_tables" :key="tableKey" class="result-section">
          <div class="result-section-title">{{ subTableLabel(tableKey) }}（{{ items.length }} 条）</div>
          <el-table :data="items" border size="small" max-height="180">
            <el-table-column
              v-for="col in Object.keys(items[0] || {})"
              :key="col"
              :prop="col"
              :label="fieldLabel(col)"
              min-width="100"
            />
          </el-table>
        </div>
      </div>
      <template #footer>
        <el-button @click="resumeResultVisible = false">取消</el-button>
        <el-button type="warning" @click="onApplyResume(false)">仅填充空字段</el-button>
        <el-button type="primary" :loading="resumeApplying" @click="onApplyResume(true)">覆盖已有值并保存</el-button>
      </template>
    </el-dialog>

    <!-- 申请管理员对话框 -->
    <el-dialog v-model="applyVisible" title="申请成为单位管理员" width="460px">
      <el-alert
        type="info" :closable="false" style="margin-bottom: 16px"
        :title="`提交后由超级管理员审批。批准后您将获得「${auth.user?.unit_name || '本单位'}」及其下属单位的管理权限，同时保留您的个人档案。`"
      />
      <el-form>
        <el-form-item label="申请理由">
          <el-input v-model="applyReason" type="textarea" :rows="4" placeholder="请说明申请理由，如您的职务、管理职责等" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="applyVisible = false">取消</el-button>
        <el-button type="primary" :loading="applying" @click="submitApply">提交申请</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Edit, Upload, UploadFilled, Promotion } from '@element-plus/icons-vue'
import api, { resumeSmartApi } from '@/api'
import { useAuthStore } from '@/stores/auth'
import PersonFormDialog from '@/components/PersonFormDialog.vue'
import PersonDetailInline from '@/components/PersonDetailInline.vue'

const auth = useAuthStore()
const personId = auth.personId
const person = ref(null)
const loading = ref(false)
const editVisible = ref(false)

// 申请相关
const myApplication = ref(null)
const applyVisible = ref(false)
const applyReason = ref('')
const applying = ref(false)

// 简历识别相关
const resumeUploadVisible = ref(false)
const resumeUploadRef = ref()
const resumeFile = ref(null)
const resumeParsing = ref(false)
const resumeResult = ref(null)
const resumeResultVisible = ref(false)
const resumeApplying = ref(false)

// 字段中文标签
const FIELD_LABELS = {
  name: '姓名', gender: '性别', birth_date: '出生日期', id_card: '身份证号',
  ethnicity: '民族', native_place: '籍贯', birth_place: '出生地',
  political_status: '政治面貌', party_join_date: '入党日期', party_apply_date: '申请入党日期',
  phone: '手机号', office_phone: '办公电话', emergency_contact: '紧急联系人',
  education_level: '学历', degree: '学位', school: '毕业院校', major: '专业',
  graduation_date: '毕业日期', marital_status: '婚姻状况', spouse_name: '配偶姓名',
  children_count: '子女数', home_address: '家庭住址',
  department: '部门', position: '岗位', rank: '职级',
  work_start_date: '参加工作日期', join_unit_date: '入职日期',
  relationship: '关系', work_unit: '工作单位', witness: '证明人',
  start_date: '开始日期', end_date: '结束日期',
}
const fieldLabel = (key) => FIELD_LABELS[key] || key
const subTableLabel = (key) => ({
  family_members: '家庭成员',
  education_records: '教育经历',
  work_records: '工作经历',
})[key] || key

const loadData = async () => {
  if (!personId) return
  loading.value = true
  try {
    person.value = await api.get(`/persons/${personId}`)
  } finally {
    loading.value = false
  }
}

const loadMyApplication = async () => {
  if (auth.role !== 'person') return
  try {
    const apps = await api.get('/auth/applications/mine')
    myApplication.value = apps[0] || null
  } catch (e) {}
}

const openApply = () => {
  applyReason.value = ''
  applyVisible.value = true
}

const submitApply = async () => {
  applying.value = true
  try {
    await api.post('/auth/applications', { reason: applyReason.value })
    ElMessage.success('申请已提交，等待超级管理员审批')
    applyVisible.value = false
    await loadMyApplication()
  } finally {
    applying.value = false
  }
}

// ===== 简历识别 =====
const openResumeUpload = () => {
  resumeFile.value = null
  resumeResult.value = null
  resumeUploadVisible.value = true
  // 清除上次选择的文件
  if (resumeUploadRef.value) {
    resumeUploadRef.value.clearFiles()
  }
}

const onResumeFileChange = (file) => {
  resumeFile.value = file.raw
}

const onExceed = () => {
  ElMessage.warning('只能上传一个文件，请先移除已选文件')
}

const onParseResume = async () => {
  if (!resumeFile.value) {
    ElMessage.warning('请先选择简历文件')
    return
  }
  resumeParsing.value = true
  try {
    const result = await resumeSmartApi.parse(resumeFile.value)
    resumeResult.value = result
    resumeUploadVisible.value = false
    resumeResultVisible.value = true
  } catch (e) {
    ElMessage.error('简历解析失败：' + (e.response?.data?.detail || e.message))
  } finally {
    resumeParsing.value = false
  }
}

const onApplyResume = async (overwrite) => {
  if (!resumeResult.value || !personId) return
  resumeApplying.value = true
  try {
    const res = await resumeSmartApi.applyToPerson(personId, {
      flat_fields: resumeResult.value.flat_fields,
      sub_tables: resumeResult.value.sub_tables,
      overwrite: overwrite,
    })
    ElMessage.success(`应用成功：更新 ${res.updated_fields.length} 个字段，新增 ${Object.values(res.added_sub_tables || {}).reduce((a, b) => a + b, 0)} 条子表记录`)
    if (res.skipped_fields.length > 0) {
      ElMessage.info(`跳过 ${res.skipped_fields.length} 个已有值的字段`)
    }
    resumeResultVisible.value = false
    await loadData()
  } catch (e) {
    ElMessage.error('应用失败：' + (e.response?.data?.detail || e.message))
  } finally {
    resumeApplying.value = false
  }
}

const formatTime = (t) => t ? new Date(t).toLocaleString('zh-CN') : ''

onMounted(() => {
  loadData()
  loadMyApplication()
})
</script>

<style scoped>
.apply-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.action-bar {
  margin-bottom: 16px;
  display: flex;
  gap: 8px;
}
.resume-result {
  max-height: 60vh;
  overflow-y: auto;
}
.result-section {
  margin-bottom: 20px;
}
.result-section-title {
  font-weight: 600;
  color: #303133;
  margin-bottom: 8px;
  padding-left: 8px;
  border-left: 3px solid #409eff;
}
.field-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px 16px;
}
.field-item {
  font-size: 13px;
  display: flex;
}
.field-label {
  color: #909399;
  flex-shrink: 0;
  min-width: 90px;
}
.field-value {
  color: #303133;
  word-break: break-all;
}
</style>
