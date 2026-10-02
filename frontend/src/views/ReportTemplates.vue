<template>
  <div class="page-container">
    <div class="section-title">报表模板与生成</div>

    <el-alert
      type="info"
      :closable="false"
      show-icon
      style="margin-bottom: 16px"
      title="流程：上传模板 → 智能匹配字段 → 确认/修改映射 → 保存模板 → 生成报表 → 下载"
    />

    <!-- 上半部分：模板列表 -->
    <el-card>
      <div class="toolbar">
        <span class="card-title">模板列表</span>
        <el-button type="primary" @click="openUpload">
          <el-icon><Upload /></el-icon>上传新模板
        </el-button>
        <el-button type="success" @click="openAIGenerate">
          <el-icon><MagicStick /></el-icon>AI 智能生成
        </el-button>
        <el-button @click="loadTemplates">
          <el-icon><Refresh /></el-icon>刷新
        </el-button>
      </div>

      <el-table :data="templates" v-loading="loadingTemplates" border stripe style="margin-top: 16px">
        <el-table-column type="index" label="序号" width="60" align="center" />
        <el-table-column prop="name" label="名称" min-width="180" />
        <el-table-column label="是否公开" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_public ? 'success' : 'info'" size="small">
              {{ row.is_public ? '公开' : '私有' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="180">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="240" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="success" @click="openGenerate(row)">生成报表</el-button>
            <el-button size="small" type="danger" @click="onDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 上传 + 匹配 对话框 -->
    <el-dialog
      v-model="uploadVisible"
      title="上传模板并智能匹配字段"
      width="900px"
      top="5vh"
      :close-on-click-modal="false"
      @closed="resetUpload"
    >
      <el-alert
        type="warning"
        :closable="false"
        show-icon
        style="margin-bottom: 12px"
        title="仅支持 .xlsx / .xls 模板文件，首行默认为表头行（可在下方调整）。"
      />

      <!-- 步骤1：上传 -->
      <div class="step-block">
        <div class="step-title">① 选择并上传模板文件</div>
        <el-upload
          ref="uploadRef"
          :auto-upload="false"
          :limit="1"
          accept=".xlsx,.xls"
          :on-change="onFileChange"
          :on-exceed="onExceed"
          :on-remove="onFileRemove"
          :file-list="fileList"
          drag
        >
          <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
          <div class="el-upload__text">将模板文件拖到此处，或<em>点击上传</em></div>
          <template #tip>
            <div class="el-upload__tip">表头行：
              <el-input-number v-model="headerRow" :min="1" :max="20" size="small" style="width: 110px" />
              ；数据起始行：
              <el-input-number v-model="dataStartRow" :min="1" :max="20" size="small" style="width: 110px" />
            </div>
          </template>
        </el-upload>

        <div style="margin-top: 12px">
          <el-button
            type="primary"
            :loading="matching"
            :disabled="!selectedFile"
            @click="doUploadAndMatch"
          >
            <el-icon><MagicStick /></el-icon>上传并智能匹配
          </el-button>
        </div>
      </div>

      <!-- 步骤2：匹配结果 -->
      <div v-if="matchedHeaders.length" class="step-block">
        <div class="step-title">② 确认/修改字段映射</div>
        <div class="step-tip">
          匹配状态：🟢 高置信度　🟡 中等置信度　🔴 未匹配。
          可下拉修改每列对应的系统字段，或选择「设为空」跳过该列。
        </div>
        <el-table :data="matchRows" border stripe size="small" max-height="320">
          <el-table-column label="列号" width="70" align="center">
            <template #default="{ row }">第 {{ row.col_index + 1 }} 列</template>
          </el-table-column>
          <el-table-column prop="template_name" label="模板字段名" min-width="140" />
          <el-table-column label="识别/对应的系统字段" min-width="220">
            <template #default="{ row }">
              <el-select
                v-model="row.system_field_key"
                clearable
                placeholder="设为空（跳过该列）"
                style="width: 100%"
              >
                <el-option
                  v-for="f in systemFields"
                  :key="f.value"
                  :label="f.label + ' (' + f.value + ')'"
                  :value="f.value"
                />
              </el-select>
            </template>
          </el-table-column>
          <el-table-column label="置信度" width="100" align="center">
            <template #default="{ row }">
              {{ row.confidence != null ? (row.confidence * 100).toFixed(0) + '%' : '—' }}
            </template>
          </el-table-column>
          <el-table-column label="状态" width="90" align="center">
            <template #default="{ row }">
              <span class="status-dot">{{ statusDot(row) }}</span>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- 步骤3：保存模板 -->
      <div v-if="matchedHeaders.length" class="step-block">
        <div class="step-title">③ 设置模板名称并保存</div>
        <el-form label-width="100px" style="margin-top: 8px">
          <el-form-item label="模板名称" required>
            <el-input v-model="templateName" placeholder="如：2026年度人员花名册模板" style="width: 360px" />
          </el-form-item>
          <el-form-item label="是否公开">
            <el-switch v-model="isPublic" />
            <span class="hint" style="margin-left: 8px">{{ isPublic ? '所有人可用' : '仅本人可用' }}</span>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="saving" @click="saveTemplate">
              <el-icon><Check /></el-icon>保存模板
            </el-button>
          </el-form-item>
        </el-form>
      </div>
    </el-dialog>

    <!-- 生成报表对话框 -->
    <el-dialog
      v-model="generateVisible"
      title="生成报表"
      width="560px"
    >
      <el-form label-width="100px">
        <el-form-item label="模板">
          <span class="readonly-text">{{ generatingTemplate?.name }}</span>
        </el-form-item>
        <el-form-item label="生成范围" v-if="auth.isSuperAdmin">
          <el-select v-model="generateUnitId" placeholder="全单位（不限）" clearable style="width: 100%">
            <el-option v-for="u in units" :key="u.id" :label="u.name" :value="u.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="生成范围" v-else>
          <span class="readonly-text">{{ currentUnitName || '本单位' }}</span>
        </el-form-item>
        <el-form-item v-if="auth.isSuperAdmin" label="">
          <span class="hint">不选单位则统计全部人员</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="generateVisible = false">取消</el-button>
        <el-button type="primary" :loading="generating" @click="doGenerate">
          <el-icon><MagicStick /></el-icon>生成
        </el-button>
      </template>
    </el-dialog>

    <!-- AI 智能生成对话框 -->
    <el-dialog
      v-model="aiVisible"
      title="AI 智能生成报表"
      width="720px"
      top="5vh"
      :close-on-click-modal="false"
      @closed="resetAIGenerate"
    >
      <el-alert
        type="success"
        :closable="false"
        show-icon
        style="margin-bottom: 16px"
        title="输入报表需求描述，系统自动识别字段并生成 Excel 报表，无需上传模板文件"
      />

      <!-- 步骤1：输入描述 -->
      <div class="step-block">
        <div class="step-title">① 描述报表需求</div>
        <el-input
          v-model="aiDescription"
          type="textarea"
          :rows="3"
          placeholder="例如：生成一份党员花名册，包含姓名、性别、年龄、入党时间、党龄、部门、职务"
        />
        <div class="ai-quick-tags">
          <span class="ai-quick-label">快速选择：</span>
          <el-tag
            v-for="preset in aiPresets"
            :key="preset.text"
            class="ai-quick-tag"
            @click="aiDescription = preset.text"
            effect="plain"
            type="success"
          >
            {{ preset.label }}
          </el-tag>
        </div>
        <div style="margin-top: 12px">
          <el-button type="primary" :loading="aiRecommending" :disabled="!aiDescription.trim()" @click="doAIRecommend">
            <el-icon><MagicStick /></el-icon>智能识别字段
          </el-button>
        </div>
      </div>

      <!-- 步骤2：确认字段 -->
      <div v-if="aiFields.length" class="step-block">
        <div class="step-title">② 确认报表字段（共 {{ aiFields.length }} 个）</div>
        <el-table :data="aiFields" border stripe size="small" max-height="280">
          <el-table-column type="index" label="序号" width="60" align="center" />
          <el-table-column label="字段名" min-width="120">
            <template #default="{ row }">
              <el-input v-model="row.field_label" size="small" />
            </template>
          </el-table-column>
          <el-table-column label="系统字段" width="160">
            <template #default="{ row }">
              <el-select v-model="row.field_key" size="small" filterable style="width: 100%">
                <el-option v-for="f in systemFields" :key="f.value" :label="f.label + ' (' + f.value + ')'" :value="f.value" />
              </el-select>
            </template>
          </el-table-column>
          <el-table-column label="来源" width="100" align="center">
            <template #default="{ row }">
              <el-tag v-if="row.in_preset" type="success" size="small">预设</el-tag>
              <el-tag v-else-if="row.extracted_from_desc" type="warning" size="small">提取</el-tag>
              <el-tag v-else type="info" size="small">默认</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="70" align="center">
            <template #default="{ $index }">
              <el-button size="small" type="danger" link @click="aiFields.splice($index, 1)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
        <div style="margin-top: 8px">
          <el-button size="small" @click="addFieldToAI">+ 添加字段</el-button>
        </div>
      </div>

      <!-- 步骤3：生成 -->
      <div v-if="aiFields.length" class="step-block">
        <div class="step-title">③ 设置名称并生成</div>
        <el-form label-width="100px">
          <el-form-item label="报表名称">
            <el-input v-model="aiTemplateName" placeholder="如：2026年度党员花名册" style="width: 360px" />
          </el-form-item>
          <el-form-item label="生成范围" v-if="auth.isSuperAdmin">
            <el-select v-model="aiUnitId" placeholder="全单位（不限）" clearable style="width: 100%">
              <el-option v-for="u in units" :key="u.id" :label="u.name" :value="u.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="是否公开">
            <el-switch v-model="aiIsPublic" :disabled="!auth.isSuperAdmin" />
            <span class="hint" style="margin-left: 8px">{{ aiIsPublic ? '所有人可用' : '仅本人可用' }}</span>
          </el-form-item>
          <el-form-item>
            <el-button type="success" :loading="aiGenerating" @click="doAIGenerate">
              <el-icon><MagicStick /></el-icon>一键生成报表
            </el-button>
          </el-form-item>
        </el-form>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Upload, Refresh, UploadFilled, MagicStick, Check,
} from '@element-plus/icons-vue'
import api from '@/api'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

// ---------- 系统字段字典（中文 label - 英文 value） ----------
const systemFields = [
  { label: '姓名', value: 'name' },
  { label: '性别', value: 'gender' },
  { label: '出生日期', value: 'birth_date' },
  { label: '年龄', value: 'age' },
  { label: '身份证号', value: 'id_card' },
  { label: '民族', value: 'ethnicity' },
  { label: '现籍贯', value: 'native_place' },
  { label: '政治面貌', value: 'political_status' },
  { label: '入党时间', value: 'party_join_date' },
  { label: '所在单位', value: 'unit_name' },
  { label: '部门', value: 'department' },
  { label: '职务', value: 'position' },
  { label: '职级', value: 'rank' },
  { label: '参加工作时间', value: 'work_start_date' },
  { label: '最高学历', value: 'education_level' },
  { label: '学位', value: 'degree' },
  { label: '毕业院校', value: 'school' },
  { label: '专业', value: 'major' },
  { label: '手机号', value: 'phone' },
  { label: '工龄', value: 'work_years' },
  { label: '党龄', value: 'party_years' },
]

// ---------- 模板列表 ----------
const templates = ref([])
const loadingTemplates = ref(false)
const units = ref([])

const loadTemplates = async () => {
  loadingTemplates.value = true
  try {
    const res = await api.get('/reports/templates')
    templates.value = Array.isArray(res) ? res : (res?.items || [])
  } finally {
    loadingTemplates.value = false
  }
}

const loadUnits = async () => {
  if (auth.isSuperAdmin) {
    units.value = await api.get('/units')
  }
}

// ---------- 上传 + 匹配 ----------
const uploadVisible = ref(false)
const uploadRef = ref(null)
const fileList = ref([])
const selectedFile = ref(null)

const headerRow = ref(1)
const dataStartRow = ref(2)
const templateName = ref('')
const isPublic = ref(false)

const matching = ref(false)
const saving = ref(false)

const matchedHeaders = ref([])   // 服务端返回的表头数组
const matchRows = ref([])        // 编辑用的映射行

const openUpload = () => {
  resetUpload()
  uploadVisible.value = true
}

const resetUpload = () => {
  fileList.value = []
  selectedFile.value = null
  headerRow.value = 1
  dataStartRow.value = 2
  templateName.value = ''
  isPublic.value = false
  matchedHeaders.value = []
  matchRows.value = []
  uploadRef.value?.clearFiles?.()
}

const onFileChange = (file) => {
  selectedFile.value = file.raw
  // 仅保留最后一个
  fileList.value = [file]
}

const onFileRemove = () => {
  selectedFile.value = null
  fileList.value = []
}

const onExceed = () => {
  ElMessage.warning('一次只能上传一个模板文件')
}

const doUploadAndMatch = async () => {
  if (!selectedFile.value) {
    ElMessage.warning('请先选择模板文件')
    return
  }
  matching.value = true
  try {
    const formData = new FormData()
    formData.append('file', selectedFile.value)
    const res = await api.post(
      `/reports/upload-and-match?header_row=${headerRow.value}`,
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    )
    // 期望返回 { headers: [...], mappings: [...] }
    matchedHeaders.value = res?.headers || []
    matchRows.value = (res?.mappings || []).map((m) => ({
      col_index: m.col_index,
      template_name: m.template_name,
      system_field_key: m.system_field_key || '',
      confidence: m.confidence != null ? Number(m.confidence) : null,
      confirmed: !!m.confirmed,
    }))
    // 自动填充模板名（去后缀）
    if (!templateName.value && selectedFile.value.name) {
      templateName.value = selectedFile.value.name.replace(/\.(xlsx|xls)$/i, '')
    }
    if (matchRows.value.length === 0) {
      ElMessage.warning('未识别到任何表头列，请确认表头行设置是否正确')
    } else {
      ElMessage.success(`成功识别 ${matchRows.value.length} 列`)
    }
  } finally {
    matching.value = false
  }
}

const statusDot = (row) => {
  if (!row.system_field_key) return '🔴'
  const c = row.confidence
  if (c == null) return '🟢'
  if (c >= 0.8) return '🟢'
  if (c >= 0.5) return '🟡'
  return '🔴'
}

// ---------- 保存模板 ----------
const saveTemplate = async () => {
  if (!templateName.value.trim()) {
    ElMessage.warning('请输入模板名称')
    return
  }
  if (matchRows.value.length === 0) {
    ElMessage.warning('请先上传并匹配字段')
    return
  }
  saving.value = true
  try {
    const payload = {
      name: templateName.value.trim(),
      header_row: headerRow.value,
      data_start_row: dataStartRow.value,
      is_public: isPublic.value,
      mappings: matchRows.value.map((r) => ({
        col_index: r.col_index,
        template_name: r.template_name,
        system_field_key: r.system_field_key || null,
        confidence: r.confidence,
        confirmed: !!r.system_field_key,
      })),
    }
    const created = await api.post('/reports/templates', payload)
    const newId = created?.id
    // 保存成功后上传实际模板文件
    if (newId && selectedFile.value) {
      try {
        const formData = new FormData()
        formData.append('file', selectedFile.value)
        await api.post(`/reports/templates/${newId}/upload-file`, formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        })
      } catch (e) {
        // 文件上传失败不阻断，仅提示
        ElMessage.warning('模板已保存，但模板文件上传失败，生成报表时可能无法使用')
      }
    }
    ElMessage.success('模板保存成功')
    uploadVisible.value = false
    loadTemplates()
  } finally {
    saving.value = false
  }
}

// ---------- 删除模板 ----------
const onDelete = (row) => {
  ElMessageBox.confirm(`确定删除模板「${row.name}」吗？`, '删除确认', {
    type: 'warning',
    confirmButtonText: '确定删除',
    cancelButtonText: '取消',
  })
    .then(async () => {
      await api.delete(`/reports/templates/${row.id}`)
      ElMessage.success('删除成功')
      loadTemplates()
    })
    .catch(() => {})
}

// ---------- 生成报表 ----------
const generateVisible = ref(false)
const generating = ref(false)
const generatingTemplate = ref(null)
const generateUnitId = ref(null)

const currentUnitName = computed(() => {
  const u = units.value.find((x) => x.id === (auth.user?.unit_id))
  return u ? u.name : ''
})

const openGenerate = (row) => {
  generatingTemplate.value = row
  generateUnitId.value = auth.isSuperAdmin ? null : (auth.user?.unit_id || null)
  generateVisible.value = true
}

const doGenerate = async () => {
  if (!generatingTemplate.value) return
  generating.value = true
  try {
    const payload = { template_id: generatingTemplate.value.id }
    const uid = auth.isSuperAdmin ? generateUnitId.value : (auth.user?.unit_id || null)
    if (uid) payload.unit_id = uid
    const res = await api.post('/reports/generate', payload)
    const total = res?.total ?? 0
    const filled = res?.filled_cells ?? 0
    const missing = res?.missing_cells ?? 0
    const file = res?.output_file
    const html = [
      `报表已生成`,
      `<div style="margin:8px 0;line-height:1.8">`,
      `总人数：<b>${total}</b><br/>`,
      `已填充单元格：<b style="color:#67c23a">${filled}</b><br/>`,
      `缺失单元格：<b style="color:#f56c6c">${missing}</b>`,
      `</div>`,
    ].join('')
    ElMessageBox.alert(html, '生成结果', {
      dangerouslyUseHTMLString: true,
      confirmButtonText: file ? '下载文件' : '知道了',
      showCancelButton: !!file,
      cancelButtonText: '关闭',
    })
      .then(async () => {
        if (file) await downloadFile(file)
      })
      .catch(() => {})
    if (!file) {
      // 无文件输出，仅刷新列表
    }
    loadTemplates()
  } finally {
    generating.value = false
  }
}

// ---------- 下载文件 ----------
const downloadFile = async (filename) => {
  try {
    const blob = await api.get(`/reports/download/${filename}`, { responseType: 'blob' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  } catch (e) {
    // 错误已由拦截器提示
  }
}

// ---------- 工具 ----------
const formatTime = (t) => (t ? String(t).replace('T', ' ').slice(0, 19) : '')

// ---------- AI 智能生成 ----------
const aiVisible = ref(false)
const aiDescription = ref('')
const aiFields = ref([])
const aiTemplateName = ref('')
const aiIsPublic = ref(false)
const aiUnitId = ref(null)
const aiRecommending = ref(false)
const aiGenerating = ref(false)

const aiPresets = [
  { label: '花名册', text: '生成一份人员花名册，包含姓名、性别、年龄、身份证号、部门、职务、职级、手机号、政治面貌' },
  { label: '党员名册', text: '生成一份党员花名册，包含姓名、性别、年龄、政治面貌、入党时间、党龄、部门、职务、手机号' },
  { label: '学历统计', text: '生成一份学历统计表，包含姓名、性别、年龄、最高学历、学位、毕业院校、所学专业、毕业时间、部门' },
  { label: '通讯录', text: '生成一份单位通讯录，包含姓名、部门、职务、手机号、办公电话、所在单位' },
  { label: '年龄结构', text: '生成一份年龄结构表，包含姓名、性别、出生日期、年龄、部门、职务' },
  { label: '新入职人员', text: '生成一份新入职人员表，包含姓名、性别、出生日期、身份证号、部门、职务、入职本单位时间、手机号、最高学历' },
  { label: '部门人员分布', text: '生成一份部门人员分布表，包含部门、姓名、性别、年龄、职务、职级、参加工作时间' },
  { label: '职级结构统计', text: '生成一份职级结构统计表，包含姓名、部门、职务、职级、年龄、学历' },
  { label: '民族构成统计', text: '生成一份民族构成统计表，包含姓名、性别、民族、年龄、部门、职务' },
]

const openAIGenerate = () => {
  resetAIGenerate()
  aiVisible.value = true
}

const resetAIGenerate = () => {
  aiDescription.value = ''
  aiFields.value = []
  aiTemplateName.value = ''
  aiIsPublic.value = false
  aiUnitId.value = auth.isSuperAdmin ? null : (auth.user?.unit_id || null)
}

const doAIRecommend = async () => {
  if (!aiDescription.value.trim()) return
  aiRecommending.value = true
  try {
    const res = await api.post('/reports/ai-recommend-fields', {
      description: aiDescription.value,
    })
    aiFields.value = res?.recommended_fields || []
    aiTemplateName.value = res?.suggested_name || '自定义报表'
    if (aiFields.value.length === 0) {
      ElMessage.warning('未识别到相关字段，请尝试更详细的描述')
    } else {
      ElMessage.success(`智能识别到 ${aiFields.value.length} 个字段`)
    }
  } finally {
    aiRecommending.value = false
  }
}

const addFieldToAI = () => {
  aiFields.value.push({
    field_key: '',
    field_label: '',
    in_preset: false,
    extracted_from_desc: false,
  })
}

const doAIGenerate = async () => {
  if (aiFields.value.length === 0) {
    ElMessage.warning('请先智能识别字段')
    return
  }
  const validFields = aiFields.value.filter(f => f.field_key && f.field_label)
  if (validFields.length === 0) {
    ElMessage.warning('请确保至少有一个有效的字段')
    return
  }
  aiGenerating.value = true
  try {
    const payload = {
      description: aiDescription.value,
      template_name: aiTemplateName.value || '自定义报表',
      is_public: aiIsPublic,
    }
    if (auth.isSuperAdmin && aiUnitId.value) {
      payload.unit_id = aiUnitId.value
    } else if (!auth.isSuperAdmin) {
      payload.unit_id = auth.user?.unit_id || null
    }
    const res = await api.post('/reports/ai-generate', payload)
    const html = [
      `报表已智能生成`,
      `<div style="margin:8px 0;line-height:1.8">`,
      `报表名称：<b>${res?.template_name || ''}</b><br/>`,
      `总人数：<b>${res?.total ?? 0}</b><br/>`,
      `字段数：<b>${res?.field_count ?? 0}</b><br/>`,
      `已填充单元格：<b style="color:#67c23a">${res?.filled_cells ?? 0}</b><br/>`,
      `缺失单元格：<b style="color:#f56c6c">${res?.missing_cells ?? 0}</b>`,
      `</div>`,
    ].join('')
    ElMessageBox.alert(html, '生成成功', {
      dangerouslyUseHTMLString: true,
      confirmButtonText: res?.output_file ? '下载报表' : '知道了',
      showCancelButton: !!res?.output_file,
      cancelButtonText: '关闭',
    })
      .then(async () => {
        if (res?.output_file) await downloadFile(res.output_file)
      })
      .catch(() => {})
    aiVisible.value = false
    loadTemplates()
  } finally {
    aiGenerating.value = false
  }
}

onMounted(() => {
  loadTemplates()
  loadUnits()
})
</script>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
}
.card-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  margin-right: 8px;
}
.step-block {
  margin-top: 16px;
  padding-top: 8px;
  border-top: 1px dashed #ebeef5;
}
.step-block:first-of-type {
  border-top: none;
  margin-top: 0;
  padding-top: 0;
}
.step-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 8px;
}
.step-tip {
  font-size: 13px;
  color: #909399;
  margin-bottom: 8px;
  line-height: 1.6;
}
.status-dot {
  font-size: 16px;
}
.hint {
  color: #909399;
  font-size: 12px;
}
.readonly-text {
  font-weight: 600;
  color: #303133;
}
.ai-quick-tags {
  margin-top: 10px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}
.ai-quick-label {
  font-size: 13px;
  color: #909399;
  margin-right: 4px;
}
.ai-quick-tag {
  cursor: pointer;
  transition: all 0.2s;
}
.ai-quick-tag:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(45, 90, 39, 0.15);
}
</style>
