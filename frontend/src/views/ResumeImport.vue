<template>
  <div class="page-container">
    <div class="section-title">简历表导入</div>

    <el-card>
      <el-steps :active="activeStep" finish-status="success" align-center style="margin-bottom: 24px">
        <el-step title="上传示例" description="上传一个简历表" />
        <el-step title="配置字段" description="点击单元格配对" />
        <el-step title="保存模板" description="保存映射配置" />
        <el-step title="批量提取" description="批量上传提取" />
        <el-step title="确认入库" description="核对并入库" />
      </el-steps>

      <!-- 步骤1：上传示例 -->
      <div v-if="activeStep === 0">
        <el-upload
          ref="uploadRef"
          :auto-upload="false"
          :limit="1"
          accept=".docx,.xlsx"
          :on-change="onFileChange"
          :on-exceed="() => ElMessage.warning('一次只能上传一个示例文件')"
          :on-remove="() => { sampleFile = null }"
          :file-list="fileList"
          drag
          style="margin-bottom: 16px"
        >
          <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
          <div class="el-upload__text">将简历表拖到此处，或<em>点击上传</em></div>
          <template #tip>
            <div class="el-upload__tip">支持 Word(.docx) 和 Excel(.xlsx) 格式，先上传一个作为配置样例</div>
          </template>
        </el-upload>
        <div style="text-align: center">
          <el-button type="primary" :loading="uploading" :disabled="!sampleFile" @click="doUpload">
            <el-icon><Upload /></el-icon>解析表格
          </el-button>
        </div>
      </div>

      <!-- 步骤2：表格预览 + 点击配对 -->
      <div v-if="activeStep === 1">
        <el-alert
          :type="listMode ? 'success' : 'info'"
          :closable="false"
          style="margin-bottom: 12px"
        >
          <template #title>
            <span v-if="listMode">
              <strong>列表组配置模式</strong>（{{ listGroupName || '未命名' }}）：
              <span v-if="!listPendingLabel">请点击表头字段名单元格</span>
              <span v-else>已选"<strong>{{ listPendingLabel.field }}</strong>"，请点击对应的首行值单元格</span>
            </span>
            <span v-else>
              <span v-if="clickState === 'label'">请点击 <strong>字段名</strong> 单元格（标签）</span>
              <span v-else>已选标签"<strong>{{ pendingCell?.text }}</strong>"，请点击对应的 <strong>值</strong> 单元格</span>
            </span>
          </template>
        </el-alert>

        <!-- 操作按钮区 -->
        <div style="margin-bottom: 12px; display: flex; gap: 8px; flex-wrap: wrap">
          <el-button v-if="clickState === 'value'" @click="cancelPending">取消当前配对</el-button>
          <el-button v-if="!listMode" type="success" plain @click="startListGroup">
            <el-icon><Plus /></el-icon>添加列表组（子表）
          </el-button>
          <template v-if="listMode">
            <el-input v-model="listGroupName" placeholder="列表组名称(如:工作经历)" style="width: 180px" size="small" />
            <el-select v-model="listTargetTable" placeholder="目标子表" style="width: 140px" size="small">
              <el-option label="家庭成员" value="family" />
              <el-option label="工作经历" value="work" />
              <el-option label="学历经历" value="edu" />
              <el-option label="奖惩记录" value="reward" />
            </el-select>
            <el-button v-if="listPendingLabel" size="small" @click="listPendingLabel = null">取消本列</el-button>
            <el-button type="warning" size="small" @click="finishListGroup">完成列表组</el-button>
            <el-button size="small" @click="cancelListGroup">退出列表组模式</el-button>
          </template>
          <el-button v-if="mappings.length" type="danger" plain @click="mappings = []">清空所有映射</el-button>
        </div>

        <el-row :gutter="16">
          <!-- 左侧：表格预览 -->
          <el-col :span="16">
            <div v-if="grids.length > 1" style="margin-bottom: 8px">
              <el-radio-group v-model="currentGridIdx" size="small">
                <el-radio-button v-for="(g, i) in grids" :key="i" :label="i">{{ g.name }}</el-radio-button>
              </el-radio-group>
            </div>
            <div class="table-viewport">
              <table class="grid-table">
                <tbody>
                  <tr v-for="(row, ri) in renderRows" :key="ri">
                    <td
                      v-for="cell in row"
                      :key="cell.c"
                      :class="[...cellClass(cell.r, cell.c), cell.isMaster ? 'merged-master' : '']"
                      :rowspan="cell.rowspan > 1 ? cell.rowspan : undefined"
                      :colspan="cell.colspan > 1 ? cell.colspan : undefined"
                      @click="onCellClick(cell.r, cell.c, cell.text)"
                    >
                      <span class="cell-text">{{ cell.text }}</span>
                      <span
                        v-if="badgeForCell(cell.r, cell.c) !== null"
                        class="mapping-badge"
                      >{{ badgeForCell(cell.r, cell.c) + 1 }}</span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div class="legend">
              <span class="dot pending"></span>待选标签
              <span class="dot label"></span>已选标签格
              <span class="dot value"></span>已选值格
            </div>
          </el-col>

          <!-- 右侧：映射列表 -->
          <el-col :span="8">
            <div class="mapping-panel">
              <h4 style="margin: 0 0 8px">字段映射 ({{ mappings.length }})</h4>
              <div v-for="(m, i) in mappings" :key="i" class="mapping-item">
                <div class="mapping-head">
                  <span class="num-badge">{{ i + 1 }}</span>
                  <span class="field-name">{{ m.field_name }}</span>
                  <el-button size="small" type="danger" link @click="mappings.splice(i, 1)">
                    <el-icon><Delete /></el-icon>
                  </el-button>
                </div>
                <div class="mapping-value">值：{{ getCellValue(m.value_row, m.value_col) || '(空)' }}</div>
                <el-select
                  v-model="m.system_field_key"
                  size="small"
                  clearable
                  placeholder="对应系统字段（可选）"
                  style="width: 100%"
                >
                  <el-option v-for="f in systemFields" :key="f.value" :label="f.label" :value="f.value" />
                </el-select>
              </div>

              <h4 style="margin: 16px 0 8px">列表组 ({{ listGroups.length }})</h4>
              <div v-for="(lg, i) in listGroups" :key="i" class="list-group-item">
                <div class="mapping-head">
                  <el-icon><Files /></el-icon>
                  <span class="field-name">{{ lg.group_name }}</span>
                  <el-tag size="small">{{ targetTableLabel(lg.target_table) }}</el-tag>
                  <el-button size="small" type="danger" link @click="listGroups.splice(i, 1)">
                    <el-icon><Delete /></el-icon>
                  </el-button>
                </div>
                <div class="mapping-value">列数：{{ lg.columns.length }}</div>
              </div>

              <el-empty v-if="!mappings.length && !listGroups.length" description="点击表格配置字段" :image-size="60" />
            </div>
          </el-col>
        </el-row>

        <div style="text-align: center; margin-top: 16px">
          <el-button @click="activeStep = 0">上一步</el-button>
          <el-button type="primary" :disabled="!mappings.length && !listGroups.length" @click="activeStep = 2">
            下一步
          </el-button>
        </div>
      </div>

      <!-- 步骤3：保存模板 -->
      <div v-if="activeStep === 2">
        <el-form label-width="120px" style="max-width: 500px; margin: 20px auto">
          <el-form-item label="模板名称">
            <el-input v-model="templateName" placeholder="如：2026干部简历表模板" />
          </el-form-item>
          <el-form-item label="文件类型">
            <el-tag>{{ fileType }}</el-tag>
          </el-form-item>
          <el-form-item label="目标表格">
            <el-select v-model="templateTableIndex" style="width: 100%">
              <el-option v-for="(g, i) in grids" :key="i" :label="g.name" :value="i" />
            </el-select>
          </el-form-item>
          <el-form-item v-if="auth.isSuperAdmin" label="是否公开">
            <el-switch v-model="isPublic" />
            <span style="margin-left: 8px; color: #909399; font-size: 12px">公开模板所有单位可用</span>
          </el-form-item>
        </el-form>
        <div style="text-align: center">
          <el-button @click="activeStep = 1">上一步</el-button>
          <el-button type="primary" :loading="saving" @click="saveTemplate">
            <el-icon><Check /></el-icon>保存模板
          </el-button>
        </div>
      </div>

      <!-- 步骤4：批量提取 -->
      <div v-if="activeStep === 3">
        <el-form label-width="100px" style="margin-bottom: 16px">
          <el-form-item label="选择模板">
            <el-select v-model="selectedTemplateId" placeholder="选择已保存的模板" style="width: 320px" @change="loadTemplates">
              <el-option v-for="t in templates" :key="t.id" :label="`${t.name} (${t.file_type})`" :value="t.id" />
            </el-select>
            <el-button style="margin-left: 8px" @click="loadTemplates"><el-icon><Refresh /></el-icon>刷新</el-button>
          </el-form-item>
          <el-form-item label="简历表文件">
            <el-upload
              :auto-upload="false"
              accept=".docx,.xlsx"
              multiple
              :on-change="onBatchFileChange"
              :on-remove="(f) => removeBatchFile(f)"
              :file-list="batchFileList"
            >
              <el-button type="primary" plain><el-icon><Upload /></el-icon>选择多个简历表</el-button>
              <template #tip>
                <div class="el-upload__tip">可一次选择多个同格式的简历表批量提取</div>
              </template>
            </el-upload>
          </el-form-item>
        </el-form>
        <div style="text-align: center; margin-bottom: 16px">
          <el-button @click="activeStep = 2">上一步</el-button>
          <el-button
            type="primary"
            :loading="extracting"
            :disabled="!selectedTemplateId || batchFiles.length === 0"
            @click="doBatchExtract"
          >
            <el-icon><MagicStick /></el-icon>开始提取
          </el-button>
        </div>

        <el-table v-if="extractResults.length" :data="extractResults" border stripe>
          <el-table-column type="index" label="#" width="50" />
          <el-table-column prop="source_file" label="源文件" min-width="160" />
          <el-table-column label="状态" width="100" align="center">
            <template #default="{ row }">
              <el-tag :type="statusTag(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="提取姓名" width="100">
            <template #default="{ row }">{{ row.flat_fields?.name || '-' }}</template>
          </el-table-column>
          <el-table-column label="信息" min-width="200">
            <template #default="{ row }">
              <span v-if="row.status === 'success'" style="color: #67c23a">提取成功，可入库</span>
              <span v-else style="color: #e6a23c">{{ row.error }}</span>
            </template>
          </el-table-column>
        </el-table>

        <div v-if="successCount > 0" style="text-align: center; margin-top: 16px">
          <el-button type="success" @click="goImport">下一步：确认入库 ({{ successCount }}人)</el-button>
        </div>
      </div>

      <!-- 步骤5：确认入库 -->
      <div v-if="activeStep === 4">
        <el-alert type="info" :closable="false" style="margin-bottom: 12px">
          <template #title>
            共 {{ toImport.length }} 人待入库。可展开查看提取详情。冲突或失败的记录将被跳过。
          </template>
        </el-alert>

        <el-form v-if="auth.isSuperAdmin" label-width="100px" style="margin-bottom: 12px">
          <el-form-item label="目标单位">
            <el-select v-model="targetUnitId" placeholder="选择入库单位" style="width: 240px">
              <el-option v-for="u in units" :key="u.id" :label="u.name" :value="u.id" />
            </el-select>
          </el-form-item>
        </el-form>

        <el-table :data="toImport" border stripe>
          <el-table-column type="expand">
            <template #default="{ row }">
              <div style="padding: 12px 24px">
                <h4>字段</h4>
                <el-descriptions :column="3" border size="small">
                  <el-descriptions-item v-for="(v, k) in row.flat_fields" :key="k" :label="fieldLabel(k)">
                    {{ v || '-' }}
                  </el-descriptions-item>
                </el-descriptions>
                <div v-for="(items, tableName) in row.sub_tables" :key="tableName" style="margin-top: 12px">
                  <h4>{{ targetTableLabel(tableName) }}（{{ items.length }}条）</h4>
                  <el-table :data="items" border size="small">
                    <el-table-column v-for="k in Object.keys(items[0] || {})" :key="k" :prop="k" :label="fieldLabel(k)" />
                  </el-table>
                </div>
              </div>
            </template>
          </el-table-column>
          <el-table-column type="index" label="#" width="50" />
          <el-table-column prop="source_file" label="源文件" min-width="160" />
          <el-table-column label="姓名" width="100">
            <template #default="{ row }">{{ row.flat_fields?.name || '-' }}</template>
          </el-table-column>
          <el-table-column label="身份证号" width="180">
            <template #default="{ row }">{{ row.flat_fields?.id_card || '-' }}</template>
          </el-table-column>
          <el-table-column label="状态" width="100" align="center">
            <template #default="{ row }">
              <el-tag :type="statusTag(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
            </template>
          </el-table-column>
        </el-table>

        <div style="text-align: center; margin-top: 16px">
          <el-button @click="activeStep = 3">上一步</el-button>
          <el-button type="primary" :loading="importing" :disabled="toImport.length === 0" @click="doImport">
            <el-icon><Check /></el-icon>确认入库
          </el-button>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/api'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

const activeStep = ref(0)

// ===== 步骤1 =====
const fileList = ref([])
const sampleFile = ref(null)
const uploading = ref(false)
const fileType = ref('')
const grids = ref([])
const currentGridIdx = ref(0)

const onFileChange = (file) => {
  sampleFile.value = file.raw
  fileList.value = [file]
}

const doUpload = async () => {
  if (!sampleFile.value) return
  uploading.value = true
  try {
    const fd = new FormData()
    fd.append('file', sampleFile.value)
    const res = await api.post('/resume-import/upload-preview', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    grids.value = res.grids
    fileType.value = res.file_type
    currentGridIdx.value = 0
    activeStep.value = 1
    ElMessage.success(`解析成功：${res.grids.length} 个表格`)
  } finally {
    uploading.value = false
  }
}

const currentGrid = computed(() => grids.value[currentGridIdx.value] || { cells: [], merged_cells: [] })

// ===== 合并单元格渲染辅助 =====
// 把 merged_cells 信息转成"主格坐标 -> {rowspan, colspan}"映射，并生成被占用坐标集合
const mergedMap = computed(() => {
  const masterMap = {}  // "r,c" -> {rowspan, colspan}
  const occupied = {}   // "r,c" -> true (被合并占用的非主格)
  for (const m of currentGrid.value.merged_cells || []) {
    masterMap[`${m.row},${m.col}`] = { rowspan: m.rowspan, colspan: m.colspan }
    for (let r = m.row; r < m.row + m.rowspan; r++) {
      for (let c = m.col; c < m.col + m.colspan; c++) {
        if (r === m.row && c === m.col) continue
        occupied[`${r},${c}`] = true
      }
    }
  }
  return { masterMap, occupied }
})

// 预计算"渲染行"：每行只保留该渲染的格子（跳过被合并占用的），并附上坐标和span属性
const renderRows = computed(() => {
  const cells = currentGrid.value.cells || []
  const { masterMap, occupied } = mergedMap.value
  return cells.map((row, ri) => {
    const renderCells = []
    for (let ci = 0; ci < row.length; ci++) {
      if (occupied[`${ri},${ci}`]) continue  // 被合并占用，跳过不渲染
      const m = masterMap[`${ri},${ci}`]
      renderCells.push({
        r: ri,
        c: ci,
        text: row[ci],
        rowspan: m ? m.rowspan : 1,
        colspan: m ? m.colspan : 1,
        isMaster: !!m,
      })
    }
    return renderCells
  })
})

// ===== 步骤2：点击配对状态机 =====
const clickState = ref('label') // 'label' | 'value'
const pendingCell = ref(null) // {row, col, text}

// 列表组模式
const listMode = ref(false)
const listGroupName = ref('')
const listTargetTable = ref('work')
const listPendingLabel = ref(null) // {field, row, col}
const listCurrentColumns = ref([])

const mappings = ref([]) // [{field_name, system_field_key, label_row, label_col, value_row, value_col}]
const listGroups = ref([]) // [{group_name, target_table, columns:[...]}]

const systemFields = [
  { label: '姓名', value: 'name' }, { label: '性别', value: 'gender' },
  { label: '出生日期', value: 'birth_date' }, { label: '民族', value: 'ethnicity' },
  { label: '现籍贯', value: 'native_place' }, { label: '出生地', value: 'birth_place' },
  { label: '身份证号', value: 'id_card' }, { label: '政治面貌', value: 'political_status' },
  { label: '入党时间', value: 'party_join_date' }, { label: '手机号', value: 'phone' },
  { label: '办公电话', value: 'office_phone' }, { label: '部门', value: 'department' },
  { label: '职务', value: 'position' }, { label: '职级', value: 'rank' },
  { label: '参加工作时间', value: 'work_start_date' }, { label: '入职本单位', value: 'join_unit_date' },
  { label: '最高学历', value: 'education_level' }, { label: '学位', value: 'degree' },
  { label: '毕业院校', value: 'school' }, { label: '专业', value: 'major' },
  { label: '毕业时间', value: 'graduation_date' }, { label: '婚姻状况', value: 'marital_status' },
  { label: '配偶姓名', value: 'spouse_name' }, { label: '子女数', value: 'children_count' },
  { label: '家庭住址', value: 'home_address' },
  // 子表字段
  { label: '称谓(家庭)', value: 'relation' }, { label: '工作单位(经历)', value: 'unit' },
  { label: '证明人(经历)', value: 'witness' }, { label: '开始时间', value: 'start_date' },
  { label: '结束时间', value: 'end_date' },
]

const getCellValue = (r, c) => {
  const row = currentGrid.value.cells[r]
  return row ? row[c] : ''
}

const cellClass = (r, c) => {
  const classes = ['grid-cell']
  // 待选标签高亮
  if (pendingCell.value && pendingCell.value.row === r && pendingCell.value.col === c) {
    classes.push('pending-label')
  }
  // 列表组待选
  if (listMode.value && listPendingLabel.value && listPendingLabel.value.row === r && listPendingLabel.value.col === c) {
    classes.push('pending-label')
  }
  // 已映射的标签格/值格
  const idx = mappings.value.findIndex(
    (m) => (m.label_row === r && m.label_col === c) || (m.value_row === r && m.value_col === c)
  )
  if (idx >= 0) {
    const m = mappings.value[idx]
    if (m.label_row === r && m.label_col === c) classes.push('mapped-label')
    if (m.value_row === r && m.value_col === c) classes.push('mapped-value')
  }
  return classes
}

const badgeForCell = (r, c) => {
  const idx = mappings.value.findIndex(
    (m) => (m.label_row === r && m.label_col === c) || (m.value_row === r && m.value_col === c)
  )
  return idx >= 0 ? idx : null
}

const onCellClick = (r, c, text) => {
  const cellText = (text || '').toString().trim()

  // 列表组模式
  if (listMode.value) {
    if (!listPendingLabel.value) {
      listPendingLabel.value = { field: cellText || `字段${listCurrentColumns.value.length + 1}`, row: r, col: c }
    } else {
      listCurrentColumns.value.push({
        field_name: listPendingLabel.value.field,
        system_field_key: '',
        label_row: listPendingLabel.value.row,
        label_col: listPendingLabel.value.col,
        value_row: r,
        value_col: c,
      })
      listPendingLabel.value = null
      ElMessage.success(`已添加列（共${listCurrentColumns.value.length}列）`)
    }
    return
  }

  // 普通字段配对
  if (clickState.value === 'label') {
    pendingCell.value = { row: r, col: c, text: cellText }
    clickState.value = 'value'
  } else {
    if (!pendingCell.value) return
    const fieldName = pendingCell.value.text || `字段${mappings.value.length + 1}`
    mappings.value.push({
      field_name: fieldName,
      system_field_key: '',
      label_row: pendingCell.value.row,
      label_col: pendingCell.value.col,
      value_row: r,
      value_col: c,
    })
    pendingCell.value = null
    clickState.value = 'label'
  }
}

const cancelPending = () => {
  pendingCell.value = null
  clickState.value = 'label'
}

// 列表组配置
const startListGroup = () => {
  listMode.value = true
  listGroupName.value = ''
  listTargetTable.value = 'work'
  listCurrentColumns.value = []
  listPendingLabel.value = null
  ElMessage.info('进入列表组配置：奇数次点表头字段名，偶数次点首行值格')
}

const finishListGroup = () => {
  if (listCurrentColumns.value.length === 0) {
    ElMessage.warning('请至少配置一列')
    return
  }
  if (!listGroupName.value) {
    ElMessage.warning('请输入列表组名称')
    return
  }
  // 自动匹配系统字段（简单包含匹配）
  listCurrentColumns.value.forEach((col) => {
    if (!col.system_field_key) {
      const match = systemFields.find((f) =>
        col.field_name.includes(f.label) || f.label.includes(col.field_name)
      )
      if (match) col.system_field_key = match.value
    }
  })
  listGroups.value.push({
    group_name: listGroupName.value,
    target_table: listTargetTable.value,
    columns: [...listCurrentColumns.value],
  })
  listMode.value = false
  listCurrentColumns.value = []
  listPendingLabel.value = null
  ElMessage.success(`列表组"${listGroupName.value}"已保存`)
}

const cancelListGroup = () => {
  listMode.value = false
  listCurrentColumns.value = []
  listPendingLabel.value = null
}

// 自动匹配系统字段（普通字段）
const autoMatchFields = () => {
  mappings.value.forEach((m) => {
    if (!m.system_field_key) {
      const match = systemFields.find(
        (f) => m.field_name.includes(f.label) || f.label.includes(m.field_name)
      )
      if (match) m.system_field_key = match.value
    }
  })
}

const targetTableLabel = (key) => {
  const map = { family: '家庭成员', work: '工作经历', edu: '学历经历', reward: '奖惩记录' }
  return map[key] || key
}

const fieldLabel = (key) => {
  const f = systemFields.find((s) => s.value === key)
  return f ? f.label : key
}

// ===== 步骤3：保存模板 =====
const templateName = ref('')
const templateTableIndex = ref(0)
const isPublic = ref(false)
const saving = ref(false)

const saveTemplate = async () => {
  if (!templateName.value.trim()) {
    ElMessage.warning('请输入模板名称')
    return
  }
  // 自动匹配一次
  autoMatchFields()
  saving.value = true
  try {
    const payload = {
      name: templateName.value.trim(),
      file_type: fileType.value,
      table_index: templateTableIndex.value,
      is_public: isPublic.value,
      cell_mappings: mappings.value.map((m, i) => ({
        field_name: m.field_name,
        system_field_key: m.system_field_key || null,
        label_row: m.label_row, label_col: m.label_col,
        value_row: m.value_row, value_col: m.value_col, sort: i,
      })),
      list_groups: listGroups.value.map((lg) => ({
        group_name: lg.group_name,
        target_table: lg.target_table,
        columns: lg.columns.map((c) => ({
          field_name: c.field_name,
          system_field_key: c.system_field_key || null,
          label_row: c.label_row, label_col: c.label_col,
          value_row: c.value_row, value_col: c.value_col,
        })),
      })),
    }
    await api.post('/resume-import/templates', payload)
    ElMessage.success('模板保存成功')
    await loadTemplates()
    activeStep.value = 3
  } finally {
    saving.value = false
  }
}

// ===== 步骤4：批量提取 =====
const templates = ref([])
const selectedTemplateId = ref(null)
const batchFileList = ref([])
const batchFiles = ref([])
const extracting = ref(false)
const extractResults = ref([])

const loadTemplates = async () => {
  templates.value = await api.get('/resume-import/templates')
}

const onBatchFileChange = (file) => {
  batchFiles.value.push(file.raw)
  batchFileList.value.push(file)
}

const removeBatchFile = (file) => {
  const idx = batchFileList.value.findIndex((f) => f.uid === file.uid)
  if (idx >= 0) {
    batchFileList.value.splice(idx, 1)
    batchFiles.value.splice(idx, 1)
  }
}

const doBatchExtract = async () => {
  if (!selectedTemplateId.value) {
    ElMessage.warning('请选择模板')
    return
  }
  extracting.value = true
  try {
    const fd = new FormData()
    batchFiles.value.forEach((f) => fd.append('files', f))
    const res = await api.post(
      `/resume-import/batch-extract?template_id=${selectedTemplateId.value}`,
      fd,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    )
    extractResults.value = res
    const ok = res.filter((r) => r.status === 'success').length
    ElMessage.success(`提取完成：成功${ok} / 共${res.length}`)
  } finally {
    extracting.value = false
  }
}

const successCount = computed(() => extractResults.value.filter((r) => r.status === 'success').length)

const statusTag = (s) => ({ success: 'success', conflict: 'warning', failed: 'danger' }[s] || 'info')
const statusLabel = (s) => ({ success: '成功', conflict: '冲突', failed: '失败' }[s] || s)

const goImport = () => {
  activeStep.value = 4
}

// ===== 步骤5：入库 =====
const units = ref([])
const targetUnitId = ref(null)
const importing = ref(false)

const toImport = computed(() => extractResults.value.filter((r) => r.status === 'success'))

const doImport = async () => {
  let unitId = targetUnitId.value
  if (auth.isSuperAdmin && !unitId) {
    ElMessage.warning('请选择目标单位')
    return
  }
  if (!auth.isSuperAdmin) unitId = auth.user?.unit_id

  try {
    await ElMessageBox.confirm(`确认为 ${toImport.value.length} 人创建档案？`, '确认入库', { type: 'warning' })
  } catch {
    return
  }

  importing.value = true
  try {
    const res = await api.post('/resume-import/import', {
      unit_id: unitId,
      persons: toImport.value,
    })
    ElMessageBox.alert(
      `入库完成：成功 ${res.success_count} 人，失败 ${res.failed_count} 人，跳过 ${res.skipped_count} 人`,
      '入库结果',
      { type: res.failed_count > 0 ? 'warning' : 'success' }
    )
    if (res.success_count > 0) {
      // 重置向导
      activeStep.value = 0
      resetAll()
    }
  } finally {
    importing.value = false
  }
}

const resetAll = () => {
  sampleFile.value = null
  fileList.value = []
  grids.value = []
  mappings.value = []
  listGroups.value = []
  extractResults.value = []
  batchFiles.value = []
  batchFileList.value = []
  templateName.value = ''
}

const loadUnits = async () => {
  if (auth.isSuperAdmin) units.value = await api.get('/units')
}

onMounted(() => {
  loadTemplates()
  loadUnits()
})
</script>

<style scoped>
.grid-cell.merged-master {
  vertical-align: middle;
  text-align: center;
  background: #fafafa;
}
.table-viewport {
  overflow: auto;
  border: 1px solid #dcdfe6;
  max-height: 520px;
  background: #fff;
}
.grid-table {
  border-collapse: collapse;
  font-size: 13px;
}
.grid-table td {
  border: 1px solid #dcdfe6;
  padding: 6px 10px;
  min-width: 80px;
  max-width: 240px;
  position: relative;
  cursor: pointer;
  transition: background 0.15s;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.grid-table td:hover {
  background: #f0f7ff;
}
.grid-cell .cell-text {
  display: inline-block;
}
.grid-cell.pending-label {
  background: #fff3cd !important;
  outline: 2px solid #ffc107;
}
.grid-cell.mapped-label {
  background: #d4ecff;
}
.grid-cell.mapped-value {
  background: #d9f7d9;
}
.mapping-badge {
  position: absolute;
  top: 1px;
  right: 3px;
  background: #409eff;
  color: #fff;
  border-radius: 50%;
  width: 16px;
  height: 16px;
  font-size: 10px;
  line-height: 16px;
  text-align: center;
}
.legend {
  margin-top: 8px;
  font-size: 12px;
  color: #606266;
}
.legend .dot {
  display: inline-block;
  width: 12px;
  height: 12px;
  border-radius: 2px;
  margin: 0 4px 0 12px;
  vertical-align: middle;
}
.legend .dot.pending { background: #fff3cd; border: 1px solid #ffc107; }
.legend .dot.label { background: #d4ecff; }
.legend .dot.value { background: #d9f7d9; }

.mapping-panel {
  max-height: 520px;
  overflow-y: auto;
  padding: 8px;
  background: #fafafa;
  border-radius: 4px;
}
.mapping-item, .list-group-item {
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  padding: 8px;
  margin-bottom: 8px;
}
.mapping-head {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
}
.num-badge {
  background: #409eff;
  color: #fff;
  border-radius: 50%;
  width: 18px;
  height: 18px;
  font-size: 11px;
  line-height: 18px;
  text-align: center;
  flex-shrink: 0;
}
.field-name {
  font-weight: 600;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.mapping-value {
  font-size: 12px;
  color: #909399;
  margin-bottom: 6px;
  word-break: break-all;
}
</style>
