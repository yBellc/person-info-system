<template>
  <div class="pg">
    <el-card shadow="never">
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center">
          <span>在职人事管理（考勤/绩效/奖惩/调岗/合同/培训）</span>
          <div>
            <el-button type="primary" @click="openAddDialog">
              <el-icon><Plus /></el-icon>&nbsp;新增记录
            </el-button>
          </div>
        </div>
      </template>

      <el-tabs v-model="tab" type="border-card">
        <!-- 考勤 -->
        <el-tab-pane label="考勤记录" name="attendance">
          <div class="filter"><el-form :inline="true" size="small">
            <el-form-item label="年份"><el-input-number v-model="f.year" :min="2000" :max="2100" /></el-form-item>
            <el-form-item label="月份"><el-input-number v-model="f.month" :min="1" :max="12" /></el-form-item>
            <el-form-item><el-button type="primary" size="small" @click="loadAttendance">查询</el-button></el-form-item>
          </el-form></div>
          <el-table :data="attendanceList" v-loading="loading[0]" size="small" stripe>
            <el-table-column prop="year" label="年" width="70" />
            <el-table-column prop="month" label="月" width="60" />
            <el-table-column prop="person_name" label="姓名" width="100" />
            <el-table-column prop="work_days" label="应出勤" width="80" />
            <el-table-column prop="actual_days" label="实出勤" width="80" />
            <el-table-column prop="late_count" label="迟到" width="60" />
            <el-table-column prop="early_leave_count" label="早退" width="60" />
            <el-table-column prop="absenteeism_days" label="旷工" width="60" />
            <el-table-column prop="personal_leave_days" label="事假" width="60" />
            <el-table-column prop="sick_leave_days" label="病假" width="60" />
            <el-table-column prop="annual_leave_days" label="年假" width="60" />
            <el-table-column prop="business_trip_days" label="出差" width="60" />
            <el-table-column prop="overtime_hours" label="加班h" width="70" />
            <template #empty><el-empty description="暂无考勤，点击新增录入" :image-size="60" /></template>
          </el-table>
        </el-tab-pane>

        <!-- 绩效 -->
        <el-tab-pane label="绩效考核" name="performance">
          <el-table :data="perfList" v-loading="loading[1]" size="small" stripe>
            <el-table-column prop="period_name" label="考核周期" width="130" />
            <el-table-column prop="period_type" label="类型" width="90" />
            <el-table-column prop="person_name" label="姓名" width="100" />
            <el-table-column prop="result" label="结果" width="90">
              <template #default="{ row }"><el-tag size="small" :type="resultType(row.result)">{{ row.result }}</el-tag></template>
            </el-table-column>
            <el-table-column prop="score" label="分数" width="70" />
            <el-table-column prop="evaluate_date" label="考核日期" width="110" />
            <el-table-column prop="feedback" label="评语" show-overflow-tooltip />
            <template #empty><el-empty description="暂无考核记录" :image-size="60" /></template>
          </el-table>
        </el-tab-pane>

        <!-- 奖惩 -->
        <el-tab-pane label="奖惩记录" name="reward">
          <div class="filter"><el-form :inline="true" size="small">
            <el-form-item label="类型">
              <el-select v-model="f.rewardType" clearable style="width:130px">
                <el-option label="奖励" value="reward" />
                <el-option label="处分" value="punishment" />
              </el-select>
            </el-form-item>
            <el-form-item><el-button type="primary" size="small" @click="loadRewards">查询</el-button></el-form-item>
          </el-form></div>
          <el-table :data="rewardList" v-loading="loading[2]" size="small" stripe>
            <el-table-column prop="date" label="日期" width="110" />
            <el-table-column prop="person_name" label="姓名" width="100" />
            <el-table-column label="类型" width="80">
              <template #default="{ row }">
                <el-tag size="small" :type="row.type === 'reward' ? 'success' : 'danger'">
                  {{ row.type === 'reward' ? '奖励' : '处分' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="name" label="名称" min-width="150" />
            <el-table-column prop="approval_authority" label="批准机关" />
            <el-table-column prop="document_no" label="文号" width="140" />
            <template #empty><el-empty description="暂无奖惩记录" :image-size="60" /></template>
          </el-table>
        </el-tab-pane>

        <!-- 调岗/调动 -->
        <el-tab-pane label="调动/调岗" name="transfer">
          <el-table :data="transList" v-loading="loading[3]" size="small" stripe>
            <el-table-column prop="person_name" label="姓名" width="100" />
            <el-table-column prop="transfer_type" label="类型" width="110">
              <template #default="{ row }">
                <el-tag size="small">{{ transferType(row.transfer_type) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="原信息" min-width="180">
              <template #default="{ row }">
                {{ row.from_department || '-' }} / {{ row.from_position || '-' }} / {{ row.from_rank || '-' }}
              </template>
            </el-table-column>
            <el-table-column label="新信息" min-width="180">
              <template #default="{ row }">
                {{ row.to_department || '-' }} / {{ row.to_position || '-' }} / {{ row.to_rank || '-' }}
              </template>
            </el-table-column>
            <el-table-column prop="effective_date" label="生效日" width="110" />
            <el-table-column label="复核状态" width="100">
              <template #default="{ row }">
                <el-tag size="small" :type="row.is_approved ? 'success' : 'warning'">
                  {{ row.is_approved ? '已复核生效' : '待复核' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="100" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" size="small" v-if="!row.is_approved && isSuperAdmin"
                             @click="approveTransfer(row)">复核通过</el-button>
              </template>
            </el-table-column>
            <template #empty><el-empty description="暂无调动记录" :image-size="60" /></template>
          </el-table>
        </el-tab-pane>

        <!-- 合同 -->
        <el-tab-pane label="合同记录" name="contract">
          <div class="filter"><el-form :inline="true" size="small">
            <el-form-item label="状态">
              <el-select v-model="f.contractStatus" clearable style="width:140px">
                <el-option label="有效" value="active" />
                <el-option label="已到期" value="expired" />
                <el-option label="已终止" value="terminated" />
                <el-option label="已续签" value="renewed" />
              </el-select>
            </el-form-item>
            <el-form-item><el-button type="primary" size="small" @click="loadContracts">查询</el-button></el-form-item>
          </el-form></div>
          <el-table :data="contractList" v-loading="loading[4]" size="small" stripe>
            <el-table-column prop="person_name" label="姓名" width="100" />
            <el-table-column prop="contract_type" label="合同类型" width="120" />
            <el-table-column prop="contract_no" label="编号" width="150" />
            <el-table-column prop="start_date" label="开始" width="110" />
            <el-table-column prop="end_date" label="结束" width="110" />
            <el-table-column prop="term_months" label="期限(月)" width="80" />
            <el-table-column prop="status" label="状态" width="90">
              <template #default="{ row }">
                <el-tag size="small" :type="contractStatusTag(row.status)">{{ contractStatusLabel(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <template #empty><el-empty description="暂无合同记录" :image-size="60" /></template>
          </el-table>
        </el-tab-pane>

        <!-- 培训 -->
        <el-tab-pane label="培训记录" name="training">
          <el-table :data="trainList" v-loading="loading[5]" size="small" stripe>
            <el-table-column prop="person_name" label="姓名" width="100" />
            <el-table-column prop="training_name" label="培训名称" min-width="180" />
            <el-table-column prop="training_type" label="类别" width="100" />
            <el-table-column prop="organizer" label="主办" width="120" />
            <el-table-column prop="start_date" label="开始" width="110" />
            <el-table-column prop="end_date" label="结束" width="110" />
            <el-table-column prop="duration_hours" label="学时" width="70" />
            <el-table-column prop="result" label="结果" width="90">
              <template #default="{ row }">
                <el-tag v-if="row.result" size="small" :type="row.result === '合格' || row.result === '优秀' ? 'success' : 'danger'">{{ row.result }}</el-tag>
              </template>
            </el-table-column>
            <template #empty><el-empty description="暂无培训记录" :image-size="60" /></template>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 新增对话框（通用，根据tab显示不同表单） -->
    <el-dialog v-model="addDlg" :title="'新增' + currentTabLabel" width="760px">
      <PersonPicker v-model="form.person_id" :label="'姓名'" required />
      <template v-if="tab === 'attendance'">
        <el-form :model="form" label-width="120px" size="small">
          <el-row :gutter="16">
            <el-col :span="8"><el-form-item label="年份" required><el-input-number v-model="form.year" :min="2000" :max="2100" style="width:100%" /></el-form-item></el-col>
            <el-col :span="8"><el-form-item label="月份" required><el-input-number v-model="form.month" :min="1" :max="12" style="width:100%" /></el-form-item></el-col>
          </el-row>
          <el-row :gutter="16">
            <el-col :span="6"><el-form-item label="应出勤天数"><el-input-number v-model="form.work_days" :precision="1" :min="0" style="width:100%" /></el-form-item></el-col>
            <el-col :span="6"><el-form-item label="实出勤天数"><el-input-number v-model="form.actual_days" :precision="1" :min="0" style="width:100%" /></el-form-item></el-col>
            <el-col :span="6"><el-form-item label="迟到次数"><el-input-number v-model="form.late_count" :min="0" style="width:100%" /></el-form-item></el-col>
            <el-col :span="6"><el-form-item label="早退次数"><el-input-number v-model="form.early_leave_count" :min="0" style="width:100%" /></el-form-item></el-col>
            <el-col :span="6"><el-form-item label="旷工天数"><el-input-number v-model="form.absenteeism_days" :precision="1" :min="0" style="width:100%" /></el-form-item></el-col>
            <el-col :span="6"><el-form-item label="事假天数"><el-input-number v-model="form.personal_leave_days" :precision="1" :min="0" style="width:100%" /></el-form-item></el-col>
            <el-col :span="6"><el-form-item label="病假天数"><el-input-number v-model="form.sick_leave_days" :precision="1" :min="0" style="width:100%" /></el-form-item></el-col>
            <el-col :span="6"><el-form-item label="年假天数"><el-input-number v-model="form.annual_leave_days" :precision="1" :min="0" style="width:100%" /></el-form-item></el-col>
            <el-col :span="6"><el-form-item label="出差天数"><el-input-number v-model="form.business_trip_days" :precision="1" :min="0" style="width:100%" /></el-form-item></el-col>
            <el-col :span="6"><el-form-item label="加班小时数"><el-input-number v-model="form.overtime_hours" :precision="1" :min="0" style="width:100%" /></el-form-item></el-col>
          </el-row>
        </el-form>
      </template>
      <template v-else-if="tab === 'performance'">
        <el-form :model="form" label-width="120px" size="small">
          <el-row :gutter="16">
            <el-col :span="8"><el-form-item label="周期名称" required><el-input v-model="form.period_name" placeholder="如 2026Q1" /></el-form-item></el-col>
            <el-col :span="8"><el-form-item label="周期类型" required><el-select v-model="form.period_type" style="width:100%"><el-option label="季度" value="quarter" /><el-option label="年度" value="year" /></el-select></el-form-item></el-col>
            <el-col :span="8"><el-form-item label="年份"><el-input-number v-model="form.year" :min="2000" style="width:100%" /></el-form-item></el-col>
            <el-col :span="8"><el-form-item label="考核结果"><el-select v-model="form.result" style="width:100%"><el-option label="优秀" value="优秀" /><el-option label="良好" value="良好" /><el-option label="称职" value="称职" /><el-option label="不称职" value="不称职" /></el-select></el-form-item></el-col>
            <el-col :span="8"><el-form-item label="考核分数"><el-input-number v-model="form.score" :min="0" :max="100" :precision="1" style="width:100%" /></el-form-item></el-col>
            <el-col :span="8"><el-form-item label="考核日期"><el-date-picker v-model="form.evaluate_date" type="date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item></el-col>
          </el-row>
          <el-form-item label="评语/反馈"><el-input v-model="form.feedback" type="textarea" :rows="3" /></el-form-item>
          <el-form-item label="文号"><el-input v-model="form.document_no" /></el-form-item>
        </el-form>
      </template>
      <template v-else-if="tab === 'reward'">
        <el-form :model="form" label-width="120px" size="small">
          <el-row :gutter="16">
            <el-col :span="8"><el-form-item label="类型" required><el-select v-model="form.type" style="width:100%"><el-option label="奖励" value="reward" /><el-option label="处分" value="punishment" /></el-select></el-form-item></el-col>
            <el-col :span="8"><el-form-item label="日期" required><el-date-picker v-model="form.date" type="date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item></el-col>
            <el-col :span="8"><el-form-item label="名称" required><el-input v-model="form.name" /></el-form-item></el-col>
            <el-col :span="12"><el-form-item label="批准机关"><el-input v-model="form.approval_authority" /></el-form-item></el-col>
            <el-col :span="12"><el-form-item label="文号"><el-input v-model="form.document_no" /></el-form-item></el-col>
          </el-row>
        </el-form>
      </template>
      <template v-else-if="tab === 'transfer'">
        <el-form :model="form" label-width="120px" size="small">
          <el-form-item label="调动类型" required>
            <el-select v-model="form.transfer_type" style="width:300px">
              <el-option label="调部门" value="department" /><el-option label="调职务" value="position" />
              <el-option label="调职级" value="rank" /><el-option label="调单位" value="unit" />
              <el-option label="调薪酬" value="salary" />
            </el-select>
          </el-form-item>
          <el-alert type="info" :closable="false" show-icon style="margin-bottom:12px">
            下面仅填写"变更为"的字段；无需变动的字段留空即可。复核通过后会写入人员档案。
          </el-alert>
          <el-row :gutter="16">
            <el-col :span="12"><el-form-item label="部门 →"><el-input v-model="form.to_department" /></el-form-item></el-col>
            <el-col :span="12"><el-form-item label="职务 →"><el-input v-model="form.to_position" /></el-form-item></el-col>
            <el-col :span="12"><el-form-item label="职级 →"><el-input v-model="form.to_rank" /></el-form-item></el-col>
            <el-col :span="12"><el-form-item label="单位ID →"><el-input-number v-model="form.to_unit_id" style="width:100%" /></el-form-item></el-col>
            <el-col :span="12"><el-form-item label="薪资 →"><el-input-number v-model="form.to_salary" :precision="2" style="width:100%" /></el-form-item></el-col>
            <el-col :span="12"><el-form-item label="生效日期"><el-date-picker v-model="form.effective_date" type="date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item></el-col>
          </el-row>
          <el-form-item label="调动原因"><el-input v-model="form.reason" type="textarea" :rows="2" /></el-form-item>
          <el-form-item label="批准机关/文号"><el-input v-model="form.approval_authority" />&nbsp;&nbsp;<el-input v-model="form.document_no" /></el-form-item>
        </el-form>
      </template>
      <template v-else-if="tab === 'contract'">
        <el-form :model="form" label-width="120px" size="small">
          <el-row :gutter="16">
            <el-col :span="12"><el-form-item label="合同类型" required><el-select v-model="form.contract_type" style="width:100%"><el-option label="劳动合同" value="劳动合同" /><el-option label="聘用合同" value="聘用合同" /><el-option label="保密协议" value="保密协议" /><el-option label="借调协议" value="借调协议" /></el-select></el-form-item></el-col>
            <el-col :span="12"><el-form-item label="合同编号"><el-input v-model="form.contract_no" /></el-form-item></el-col>
            <el-col :span="8"><el-form-item label="签订日期"><el-date-picker v-model="form.sign_date" type="date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item></el-col>
            <el-col :span="8"><el-form-item label="开始日期" required><el-date-picker v-model="form.start_date" type="date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item></el-col>
            <el-col :span="8"><el-form-item label="结束日期"><el-date-picker v-model="form.end_date" type="date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item></el-col>
            <el-col :span="12"><el-form-item label="期限(月)"><el-input-number v-model="form.term_months" style="width:100%" /></el-form-item></el-col>
            <el-col :span="12"><el-form-item label="状态"><el-select v-model="form.status" style="width:100%"><el-option label="有效" value="active" /><el-option label="已到期" value="expired" /><el-option label="已续签" value="renewed" /></el-select></el-form-item></el-col>
          </el-row>
          <el-form-item label="备注"><el-input v-model="form.remark" type="textarea" /></el-form-item>
        </el-form>
      </template>
      <template v-else-if="tab === 'training'">
        <el-form :model="form" label-width="120px" size="small">
          <el-form-item label="培训名称" required><el-input v-model="form.training_name" /></el-form-item>
          <el-row :gutter="16">
            <el-col :span="8"><el-form-item label="类别"><el-input v-model="form.training_type" placeholder="入职/在岗/业务/安全/晋升" /></el-form-item></el-col>
            <el-col :span="8"><el-form-item label="主办单位"><el-input v-model="form.organizer" /></el-form-item></el-col>
            <el-col :span="8"><el-form-item label="学时"><el-input-number v-model="form.duration_hours" :min="0" :precision="1" style="width:100%" /></el-form-item></el-col>
            <el-col :span="12"><el-form-item label="开始日期"><el-date-picker v-model="form.start_date" type="date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item></el-col>
            <el-col :span="12"><el-form-item label="结束日期"><el-date-picker v-model="form.end_date" type="date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item></el-col>
            <el-col :span="8"><el-form-item label="方式"><el-select v-model="form.training_way" style="width:100%"><el-option label="线上" value="线上" /><el-option label="线下" value="线下" /><el-option label="脱产" value="脱产" /><el-option label="在职" value="在职" /></el-select></el-form-item></el-col>
            <el-col :span="8"><el-form-item label="结果"><el-select v-model="form.result" style="width:100%"><el-option label="优秀" value="优秀" /><el-option label="合格" value="合格" /><el-option label="不合格" value="不合格" /></el-select></el-form-item></el-col>
            <el-col :span="8"><el-form-item label="证书编号"><el-input v-model="form.certificate_no" /></el-form-item></el-col>
          </el-row>
        </el-form>
      </template>
      <template #footer>
        <el-button @click="addDlg = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitAdd">确认新增</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { hrApi } from '@/api'
import { useAuthStore } from '@/stores/auth'
import PersonPicker from './components/PersonPicker.vue'

const auth = useAuthStore()
const isSuperAdmin = computed(() => auth.role === 'super_admin')
const tab = ref('attendance')
const loading = reactive([false, false, false, false, false, false])
const attendanceList = ref([])
const perfList = ref([])
const rewardList = ref([])
const transList = ref([])
const contractList = ref([])
const trainList = ref([])

const f = reactive({
  year: new Date().getFullYear(),
  month: new Date().getMonth() + 1,
  rewardType: '',
  contractStatus: '',
})

const currentTabLabel = computed(() => ({
  attendance: '考勤记录', performance: '绩效考核', reward: '奖惩记录',
  transfer: '调动/调岗', contract: '合同记录', training: '培训记录',
}[tab.value]))

const resultType = (r) => ({ '优秀': 'success', '良好': '', '称职': 'warning', '不称职': 'danger' })[r] || ''
const transferType = (t) => ({ department: '调部门', position: '调职务', rank: '调职级', unit: '调单位', salary: '调薪酬' })[t] || t
const contractStatusLabel = (s) => ({ active: '有效', expired: '已到期', terminated: '已终止', renewed: '已续签' })[s] || s
const contractStatusTag = (s) => ({ active: 'success', expired: 'warning', terminated: 'danger', renewed: 'info' })[s] || ''

const loadAttendance = async () => {
  loading[0] = true
  try { attendanceList.value = (await hrApi.listAttendance({ year: f.year, month: f.month, size: 500 })).items }
  finally { loading[0] = false }
}
const loadPerf = async () => {
  loading[1] = true
  try { perfList.value = (await hrApi.listPerformance({ size: 500 })).items }
  finally { loading[1] = false }
}
const loadRewards = async () => {
  loading[2] = true
  try { rewardList.value = (await hrApi.listRewards({ type: f.rewardType || undefined, size: 500 })).items }
  finally { loading[2] = false }
}
const loadTrans = async () => {
  loading[3] = true
  try { transList.value = (await hrApi.listTransfers({ size: 500 })).items }
  finally { loading[3] = false }
}
const loadContracts = async () => {
  loading[4] = true
  try { contractList.value = (await hrApi.listContracts({ status: f.contractStatus || undefined, size: 500 })).items }
  finally { loading[4] = false }
}
const loadTrain = async () => {
  loading[5] = true
  try { trainList.value = (await hrApi.listTrainings({ size: 500 })).items }
  finally { loading[5] = false }
}

watch(tab, (t) => {
  if (t === 'attendance') loadAttendance()
  if (t === 'performance') loadPerf()
  if (t === 'reward') loadRewards()
  if (t === 'transfer') loadTrans()
  if (t === 'contract') loadContracts()
  if (t === 'training') loadTrain()
})

// 新增对话框
const addDlg = ref(false)
const submitting = ref(false)
const emptyForm = () => ({
  person_id: null,
  // 考勤
  year: new Date().getFullYear(), month: new Date().getMonth() + 1,
  work_days: 0, actual_days: 0, late_count: 0, early_leave_count: 0,
  absenteeism_days: 0, personal_leave_days: 0, sick_leave_days: 0,
  annual_leave_days: 0, business_trip_days: 0, overtime_hours: 0,
  // 绩效
  period_name: '', period_type: 'quarter', year: new Date().getFullYear(),
  result: '', score: null, evaluate_date: '', feedback: '', document_no: '',
  // 奖惩
  type: 'reward', date: '', name: '', approval_authority: '',
  // 调动
  transfer_type: 'department', to_department: '', to_position: '', to_rank: '',
  to_unit_id: null, to_salary: null, effective_date: '', reason: '',
  // 合同
  contract_type: '劳动合同', contract_no: '', start_date: '', end_date: '',
  sign_date: '', term_months: null, status: 'active', remark: '',
  // 培训
  training_name: '', training_type: '', organizer: '', start_date: '', end_date: '',
  duration_hours: 0, training_way: '', result: '', certificate_no: '',
})
const form = reactive(emptyForm())

const openAddDialog = () => { Object.assign(form, emptyForm()); addDlg.value = true }

const submitAdd = async () => {
  if (!form.person_id) { ElMessage.warning('请选择人员'); return }
  submitting.value = true
  try {
    let payload = { ...form }
    let r
    if (tab.value === 'attendance') r = await hrApi.createAttendance(payload)
    if (tab.value === 'performance') r = await hrApi.createPerformance(payload)
    if (tab.value === 'reward') r = await hrApi.createReward(payload)
    if (tab.value === 'transfer') r = await hrApi.createTransfer(payload)
    if (tab.value === 'contract') r = await hrApi.createContract(payload)
    if (tab.value === 'training') r = await hrApi.createTraining(payload)
    ElMessage.success(r.message || '新增成功')
    addDlg.value = false
    // 刷新
    watch(tab.value, null, { immediate: false })
    if (tab.value === 'attendance') loadAttendance()
    if (tab.value === 'performance') loadPerf()
    if (tab.value === 'reward') loadRewards()
    if (tab.value === 'transfer') loadTrans()
    if (tab.value === 'contract') loadContracts()
    if (tab.value === 'training') loadTrain()
  } finally { submitting.value = false }
}

const approveTransfer = async (row) => {
  try {
    await ElMessageBox.confirm(`确认复核通过 ${row.person_name} 的${transferType(row.transfer_type)}？通过后将立即写入人员档案。`,
      '确认复核', { type: 'warning' })
    await hrApi.approveTransfer(row.id, {})
    ElMessage.success('复核通过，档案已更新')
    loadTrans()
  } catch (e) { if (e !== 'cancel') ElMessage.error('复核失败') }
}

onMounted(() => loadAttendance())
</script>

<style scoped>
.pg { padding: 16px; }
.filter { margin-bottom: 12px; }
</style>
