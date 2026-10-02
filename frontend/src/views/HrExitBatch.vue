<template>
  <div class="pg">
    <el-card shadow="never">
      <el-tabs v-model="tab" type="border-card">
        <!-- 离职管理 -->
        <el-tab-pane label="离职流程管理" name="resign">
          <div style="display:flex;justify-content:space-between;margin-bottom:12px">
            <div>
              <el-button type="primary" @click="openResignDlg">提交离职申请</el-button>
            </div>
            <div><el-select v-model="rstatus" clearable placeholder="状态过滤" style="width:160px" @change="loadResign">
              <el-option label="待审批" value="pending" />
              <el-option label="部门已批" value="dept_approved" />
              <el-option label="人事已批" value="hr_approved" />
              <el-option label="领导已批/完成" value="approved" />
              <el-option label="已驳回" value="rejected" />
            </el-select></div>
          </div>
          <el-table :data="resignList" v-loading="loading[0]" size="small" stripe>
            <el-table-column prop="person_name" label="姓名" width="100" />
            <el-table-column prop="resign_type" label="类型" width="120">
              <template #default="{ row }">
                <el-tag size="small">{{ resignType(row.resign_type) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="apply_date" label="申请日" width="110" />
            <el-table-column prop="last_work_date" label="最后工作日" width="110" />
            <el-table-column prop="status_label" label="状态" width="130">
              <template #default="{ row }">
                <el-tag size="small" :type="statusTag(row.status)">{{ row.status_label }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="交接" width="90">
              <template #default="{ row }">
                <el-tag size="small" :type="row.handover_completed ? 'success' : 'warning'">
                  {{ row.handover_completed ? '已完成' : '待完成' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="账号" width="90">
              <template #default="{ row }">
                <el-tag size="small" :type="row.account_disabled ? 'danger' : ''">
                  {{ row.account_disabled ? '已停用' : '在用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="300" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" size="small" @click="openHandoverDlg(row)">交接项</el-button>
                <el-button v-if="row.status==='pending' && isAdmin" link size="small" type="success" @click="approveStep(row, 'dept')">部门批</el-button>
                <el-button v-if="row.status==='dept_approved' && isAdmin" link size="small" type="success" @click="approveStep(row, 'hr')">人事批</el-button>
                <el-button v-if="row.status==='hr_approved' && isSuperAdmin" link size="small" type="success" @click="approveStep(row, 'lead')">领导批</el-button>
                <el-button v-if="row.status==='approved' && row.handover_completed && !row.account_disabled && isSuperAdmin"
                           link size="small" type="danger" @click="disableAccount(row)">停用账号</el-button>
              </template>
            </el-table-column>
            <template #empty><el-empty description="暂无离职申请" :image-size="60" /></template>
          </el-table>
        </el-tab-pane>

        <!-- 数据变更双人复核 -->
        <el-tab-pane label="关键数据变更复核" name="review">
          <div style="margin-bottom:12px;display:flex;justify-content:space-between;align-items:center">
            <el-radio-group v-model="reviewStatus" size="small" @change="loadReviews">
              <el-radio-button label="pending">待审核</el-radio-button>
              <el-radio-button label="approved">已通过</el-radio-button>
              <el-radio-button label="rejected">已驳回</el-radio-button>
            </el-radio-group>
            <span style="color:#909399;font-size:12px">以下关键字段需超管复核才能生效：姓名、身份证号、性别、部门、职务、职级、单位、政治面貌、学历、学位、入职时间、出生日期、手机</span>
          </div>
          <el-table :data="reviewList" v-loading="loading[1]" size="small" stripe>
            <el-table-column prop="target_display" label="目标人员" width="120" />
            <el-table-column label="变更字段" min-width="280">
              <template #default="{ row }">
                <div v-for="(c, i) in row.field_changes" :key="i" style="margin:3px 0;font-size:12px">
                  <span style="color:#2d5a27;font-weight:600">{{ c.label }}</span>
                  ：
                  <span style="color:#909399;text-decoration:line-through">{{ c.old || '(空)' }}</span>
                  ➜
                  <span style="color:#2b578a;font-weight:600">{{ c.new_value || '(空)' }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="proposer_name" label="提交人" width="100" />
            <el-table-column prop="proposed_at" label="提交时间" width="160" />
            <el-table-column prop="proposer_reason" label="修改原因" width="160" show-overflow-tooltip />
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag size="small" :type="reviewStatusTag(row.status)">{{ reviewStatusLabel(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="150" fixed="right" v-if="reviewStatus==='pending' && isSuperAdmin">
              <template #default="{ row }">
                <el-button link type="success" size="small" @click="reviewApprove(row)">通过</el-button>
                <el-button link type="danger" size="small" @click="reviewReject(row)">驳回</el-button>
              </template>
            </el-table-column>
            <template #empty><el-empty description="暂无变更审核" :image-size="60" /></template>
          </el-table>
        </el-tab-pane>

        <!-- 审批分析 -->
        <el-tab-pane label="审批流程优化分析" name="analysis">
          <div style="margin-bottom:12px">
            分析最近
            <el-select v-model="days" size="small" style="width:110px" @change="loadAnalytics">
              <el-option :label="7+'天'" :value="7" />
              <el-option :label="30+'天'" :value="30" />
              <el-option :label="90+'天'" :value="90" />
              <el-option :label="365+'天'" :value="365" />
            </el-select>
            的审批数据
          </div>
          <el-row :gutter="16">
            <el-col :span="24">
              <el-card shadow="never">
                <template #header><div class="h">各流程类型统计</div></template>
                <el-table :data="analytics.template_stats" size="small" stripe>
                  <el-table-column prop="name" label="流程名称" min-width="160" />
                  <el-table-column prop="total" label="总数" width="80" align="right" />
                  <el-table-column prop="approved" label="通过" width="80" align="right">
                    <template #default="{ row }"><span style="color:#67c23a;font-weight:600">{{ row.approved }}</span></template>
                  </el-table-column>
                  <el-table-column prop="rejected" label="驳回" width="80" align="right">
                    <template #default="{ row }"><span style="color:#f56c6c;font-weight:600">{{ row.rejected }}</span></template>
                  </el-table-column>
                  <el-table-column prop="pending" label="待办" width="80" align="right" />
                  <el-table-column prop="avg_hours" label="平均时长(小时)" width="120" align="right">
                    <template #default="{ row }">
                      <span :style="{ color: row.avg_hours > 24 ? '#f56c6c' : '' }">{{ row.avg_hours }}</span>
                    </template>
                  </el-table-column>
                  <el-table-column prop="reject_rate" label="驳回率%" width="100" align="right">
                    <template #default="{ row }">
                      <el-tag v-if="row.reject_rate >= 20" type="danger" size="small">{{ row.reject_rate }}%</el-tag>
                      <span v-else>{{ row.reject_rate }}%</span>
                    </template>
                  </el-table-column>
                  <template #empty><el-empty description="暂无审批数据" :image-size="60" /></template>
                </el-table>
              </el-card>
            </el-col>
          </el-row>
          <el-row :gutter="16" style="margin-top:16px">
            <el-col :span="12">
              <el-card shadow="never">
                <template #header><div class="h">审批节点瓶颈 TOP（按平均耗时降序）</div></template>
                <el-table :data="analytics.node_bottleneck" size="small" stripe>
                  <el-table-column prop="template" label="流程" min-width="130" />
                  <el-table-column prop="node_name" label="节点名称" min-width="120" />
                  <el-table-column prop="count" label="样本数" width="70" align="right" />
                  <el-table-column prop="avg_hours" label="平均(小时)" width="100" align="right">
                    <template #default="{ row }">
                      <span :style="{ color: row.avg_hours > 24 ? '#f56c6c' : (row.avg_hours > 12 ? '#e6a23c' : ''), fontWeight:600 }">
                        {{ row.avg_hours }}
                      </span>
                    </template>
                  </el-table-column>
                  <el-table-column prop="max_hours" label="最长(小时)" width="100" align="right" />
                  <template #empty><el-empty description="暂无瓶颈数据" :image-size="60" /></template>
                </el-table>
              </el-card>
            </el-col>
            <el-col :span="12">
              <el-card shadow="never">
                <template #header><div class="h">🛠️ 系统优化建议</div></template>
                <el-steps direction="vertical" :active="9999">
                  <el-step v-for="(s, i) in analytics.optimization_suggestions" :key="i"
                            :title="'建议 ' + (i+1)" :description="s" status="success" />
                </el-steps>
              </el-card>
            </el-col>
          </el-row>
        </el-tab-pane>

        <!-- 批量操作 -->
        <el-tab-pane label="批量操作（调岗/考勤导入/批量入职）" name="batch">
          <el-row :gutter="16">
            <el-col :span="8">
              <el-card shadow="never">
                <template #header><div class="h">① 批量调部门/岗位/职级</div></template>
                <p style="color:#606266;font-size:13px;line-height:1.7">
                  1. 先在"人员列表"中勾选人员复制到下方JSON数组。<br>
                  2. 填写需要变更的字段（留空不变）。<br>
                  3. 提交后生成批量调动记录，等待超管复核生效。
                </p>
                <el-form label-width="90px" size="small">
                  <el-form-item label="目标人员ID">
                    <el-input v-model="batchForm.person_ids" type="textarea" :rows="2" placeholder="如: [1,2,3]" />
                  </el-form-item>
                  <el-form-item label="部门→"><el-input v-model="batchForm.to_department" /></el-form-item>
                  <el-form-item label="职务→"><el-input v-model="batchForm.to_position" /></el-form-item>
                  <el-form-item label="职级→"><el-input v-model="batchForm.to_rank" /></el-form-item>
                  <el-form-item label="生效日"><el-date-picker v-model="batchForm.effective_date" type="date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item>
                  <el-form-item label="原因"><el-input v-model="batchForm.reason" type="textarea" /></el-form-item>
                </el-form>
                <el-button type="primary" :disabled="!isSuperAdmin" @click="submitBatchTransfer">
                  提交批量调动（等待复核）
                </el-button>
                <p v-if="!isSuperAdmin" style="color:#f56c6c;font-size:12px;margin-top:8px">* 仅超管可提交批量调动</p>
              </el-card>
            </el-col>
            <el-col :span="8">
              <el-card shadow="never">
                <template #header><div class="h">② 批量导入考勤（Excel）</div></template>
                <p style="color:#606266;font-size:13px;line-height:1.7">
                  Excel 表头：姓名、身份证、应出勤天数、实出勤天数、迟到次数、早退次数、旷工天数、事假天数、病假天数、年假天数、出差天数、加班小时数。<br>
                  系统按「身份证优先」→「姓名」匹配人员。
                </p>
                <el-form label-width="80px" size="small">
                  <el-form-item label="年份" required><el-input-number v-model="batchForm.year" :min="2000" style="width:100%" /></el-form-item>
                  <el-form-item label="月份" required><el-input-number v-model="batchForm.month" :min="1" :max="12" style="width:100%" /></el-form-item>
                  <el-form-item label="Excel文件" required>
                    <el-upload :auto-upload="false" :limit="1" :on-change="onFileChange" accept=".xlsx,.xls">
                      <el-button>选择文件</el-button>
                      <template #tip><div style="color:#909399;font-size:12px;margin-top:4px">{{ batchForm.file ? batchForm.file.name : '未选择文件' }}</div></template>
                    </el-upload>
                  </el-form-item>
                </el-form>
                <el-button type="primary" :disabled="!batchForm.file" @click="submitAttendanceImport">
                  开始导入
                </el-button>
                <el-alert v-if="importResult" :title="importResult" type="info" show-icon style="margin-top:12px;font-size:12px" :closable="false" />
              </el-card>
            </el-col>
            <el-col :span="8">
              <el-card shadow="never">
                <template #header><div class="h">③ 批量入职（新建人员档案）</div></template>
                <p style="color:#606266;font-size:13px;line-height:1.7">
                  按下方格式填写人员列表（JSON数组）。系统自动校验身份证唯一性和长度，成功记录数 + 失败明细一并返回。
                </p>
                <el-form label-width="90px" size="small">
                  <el-form-item label="人员JSON">
                    <el-input v-model="batchForm.personsJSON" type="textarea" :rows="10"
                      placeholder='[ {"name":"张三","gender":"男","id_card":"18位身份证号","department":"第一科室","position":"职员","rank":"一级科员","unit_id":1,"birth_date":"1990-01-01"} ]'
                      style="font-family: Consolas, monospace; font-size: 12px;" />
                  </el-form-item>
                </el-form>
                <el-button type="primary" :disabled="!isSuperAdmin" @click="submitBatchCreate">
                  执行批量入职
                </el-button>
                <p v-if="!isSuperAdmin" style="color:#f56c6c;font-size:12px;margin-top:8px">* 仅超管可批量入职</p>
                <el-alert v-if="batchCreateResult" :title="batchCreateResult" type="info" show-icon style="margin-top:12px;font-size:12px" :closable="false" />
              </el-card>
            </el-col>
          </el-row>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 离职申请框 -->
    <el-dialog v-model="resignDlg" title="提交离职申请" width="640px">
      <el-form :model="resignForm" label-width="110px" size="small">
        <PersonPicker v-model="resignForm.person_id" label="离职人员" required />
        <el-form-item label="离职类型" required>
          <el-select v-model="resignForm.resign_type" style="width:260px">
            <el-option label="主动辞职" value="resignation" />
            <el-option label="退休" value="retirement" />
            <el-option label="辞退/解聘" value="dismissal" />
            <el-option label="调出本单位" value="transfer_out" />
            <el-option label="其他" value="other" />
          </el-select>
        </el-form-item>
        <el-form-item label="申请日期" required>
          <el-date-picker v-model="resignForm.apply_date" type="date" value-format="YYYY-MM-DD" style="width:260px" />
        </el-form-item>
        <el-form-item label="最后工作日">
          <el-date-picker v-model="resignForm.last_work_date" type="date" value-format="YYYY-MM-DD" style="width:260px" />
        </el-form-item>
        <el-form-item label="离职原因">
          <el-input v-model="resignForm.reason" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="resignDlg = false">取消</el-button>
        <el-button type="primary" @click="submitResign">提交</el-button>
      </template>
    </el-dialog>

    <!-- 交接对话框 -->
    <el-dialog v-model="handoverDlg" width="760px">
      <template #title>
        工作交接 — {{ (currentResign && currentResign.person_name) || '' }}
        <el-tag style="margin-left:10px" :type="currentResign && currentResign.handover_completed ? 'success' : 'warning'">
          {{ currentResign && currentResign.handover_completed ? '全部交接完成' : '交接中' }}
        </el-tag>
      </template>
      <div style="display:flex;justify-content:space-between;margin-bottom:12px;align-items:center">
        <span style="color:#909399;font-size:12px">每项交接须交接人、接收人、监交人三方分别点击「我已确认」按钮完成确认。</span>
        <el-button type="primary" size="small" @click="addHandoverDlgVisible = true">新增交接项</el-button>
      </div>
      <el-table :data="handoverItems" size="small" border>
        <el-table-column prop="item_category" label="类别" width="100" />
        <el-table-column prop="item_name" label="项目名称" min-width="160" />
        <el-table-column prop="item_detail" label="详细" min-width="200" show-overflow-tooltip />
        <el-table-column label="交接人" width="110">
          <template #default="{ row }">
            <el-tag v-if="row.handover_confirmed_at" type="success" size="small">已确认</el-tag>
            <el-button v-else link size="small" type="primary" @click="confirmHandover(row.handover_user_id, row.id, 'handover')">我是交接人，确认</el-button>
          </template>
        </el-table-column>
        <el-table-column label="接收人" width="110">
          <template #default="{ row }">
            <el-tag v-if="row.receiver_confirmed_at" type="success" size="small">已确认</el-tag>
            <el-button v-else link size="small" type="primary" @click="confirmHandover(row.receiver_user_id, row.id, 'receiver')">我是接收人，确认</el-button>
          </template>
        </el-table-column>
        <el-table-column label="监交人" width="110">
          <template #default="{ row }">
            <el-tag v-if="row.supervisor_confirmed_at" type="success" size="small">已确认</el-tag>
            <el-button v-else link size="small" type="warning" @click="confirmHandover(row.supervisor_user_id, row.id, 'supervisor')">我是监交人，确认</el-button>
          </template>
        </el-table-column>
        <template #empty><el-empty description="尚未添加交接项" :image-size="60" /></template>
      </el-table>

      <!-- 新增交接项 -->
      <el-dialog v-model="addHandoverDlgVisible" title="新增交接项" width="560px" append-to-body>
        <el-form :model="handoverForm" label-width="90px" size="small">
          <el-form-item label="类别" required>
            <el-select v-model="handoverForm.item_category" style="width:100%">
              <el-option v-for="c in ['文档资料','钥匙门禁','办公设备','账号权限','印章','工作任务','其他物品','其他']" :key="c" :label="c" :value="c" />
            </el-select>
          </el-form-item>
          <el-form-item label="名称" required><el-input v-model="handoverForm.item_name" /></el-form-item>
          <el-form-item label="描述/数量"><el-input v-model="handoverForm.item_detail" type="textarea" /></el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="addHandoverDlgVisible = false">取消</el-button>
          <el-button type="primary" @click="submitAddHandover">添加</el-button>
        </template>
      </el-dialog>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { hrExitApi, analyticsApi } from '@/api'
import { useAuthStore } from '@/stores/auth'
import PersonPicker from './components/PersonPicker.vue'

const auth = useAuthStore()
const isAdmin = computed(() => ['super_admin', 'unit_admin'].includes(auth.role))
const isSuperAdmin = computed(() => auth.role === 'super_admin')

const tab = ref('resign')
const loading = reactive([false, false])

// ---------- 离职 ----------
const rstatus = ref('')
const resignList = ref([])
const resignDlg = ref(false)
const resignForm = reactive({
  person_id: null, resign_type: 'resignation',
  apply_date: new Date().toISOString().slice(0, 10),
  last_work_date: '', reason: '',
})

const resignType = (t) => ({
  resignation: '主动辞职', retirement: '退休', dismissal: '辞退/解聘',
  transfer_out: '调出单位', other: '其他',
}[t] || t)
const statusTag = (s) => ({
  pending: 'warning', dept_approved: '', hr_approved: 'warning',
  lead_approved: 'success', approved: 'success', rejected: 'danger',
  withdrawn: 'info',
}[s] || '')

const loadResign = async () => {
  loading[0] = true
  try {
    const d = await hrExitApi.listResignations({ status: rstatus.value || undefined, size: 500 })
    resignList.value = d.items || []
  } finally { loading[0] = false }
}

const openResignDlg = () => { Object.assign(resignForm, { person_id: null, resign_type: 'resignation', apply_date: new Date().toISOString().slice(0, 10), last_work_date: '', reason: '' }); resignDlg.value = true }
const submitResign = async () => {
  if (!resignForm.person_id) { ElMessage.warning('请选择人员'); return }
  await hrExitApi.createResignation({ ...resignForm })
  ElMessage.success('已提交离职申请')
  resignDlg.value = false
  loadResign()
}

const approveStep = async (row, step) => {
  try {
    const { value: opinion } = await ElMessageBox.prompt('请填写审批意见（可留空）', `${step === 'dept' ? '部门负责人' : step === 'hr' ? '人事' : '领导'}审批`,
      { inputPattern: /.*/, confirmButtonText: '通过', cancelButtonText: '驳回',
        distinguishCancelAndClose: true })
    const payload = { opinion: opinion || '', approved: true }
    let r
    if (step === 'dept') r = await hrExitApi.deptApprove(row.id, payload)
    if (step === 'hr') r = await hrExitApi.hrApprove(row.id, payload)
    if (step === 'lead') r = await hrExitApi.leadApprove(row.id, payload)
    ElMessage.success('审批已记录')
    loadResign()
  } catch (action) {
    if (action === 'cancel') {
      try {
        const { value: opinion } = await ElMessageBox.prompt('请填写驳回理由（必填）', '填写驳回意见', {
          inputValidator: (v) => !!v || '请填写驳回理由',
        })
        const payload = { opinion, approved: false }
        // 使用通过 endpoint，approved=false 会驳回
        if (step === 'dept') await hrExitApi.deptApprove(row.id, payload)
        if (step === 'hr') await hrExitApi.hrApprove(row.id, payload)
        if (step === 'lead') await hrExitApi.leadApprove(row.id, payload)
        ElMessage.info('已驳回')
        loadResign()
      } catch {}
    }
  }
}

const disableAccount = async (row) => {
  try {
    await ElMessageBox.confirm(`确认停用 ${row.person_name} 的账号？停用后将无法登录，且无法自动恢复（需超管重新启用）。`,
      '确认停用账号', { type: 'warning', confirmButtonText: '停用' })
    await hrExitApi.disableAccount(row.id)
    ElMessage.success('账号已停用')
    loadResign()
  } catch (e) { if (e !== 'cancel') ElMessage.error('操作失败') }
}

// ---------- 交接 ----------
const handoverDlg = ref(false)
const currentResign = ref(null)
const handoverItems = ref([])
const addHandoverDlgVisible = ref(false)
const handoverForm = reactive({ item_category: '文档资料', item_name: '', item_detail: '' })

const openHandoverDlg = async (row) => {
  currentResign.value = row
  handoverDlg.value = true
  const d = await hrExitApi.getHandoverItems(row.id)
  handoverItems.value = d.items || []
}

const submitAddHandover = async () => {
  if (!handoverForm.item_name) { ElMessage.warning('请填写项目名称'); return }
  await hrExitApi.addHandoverItem(currentResign.value.id, { ...handoverForm })
  ElMessage.success('已添加')
  addHandoverDlgVisible.value = false
  handoverForm.item_name = ''; handoverForm.item_detail = ''
  const d = await hrExitApi.getHandoverItems(currentResign.value.id)
  handoverItems.value = d.items || []
  loadResign()
}

const confirmHandover = async (curId, hid, who) => {
  try {
    await ElMessageBox.confirm(`确认完成交接（${who === 'handover' ? '交接人' : who === 'receiver' ? '接收人' : '监交人'}确认）？`,
      '确认', { type: 'info' })
    if (who === 'handover') await hrExitApi.confirmHandover(hid)
    if (who === 'receiver') await hrExitApi.confirmReceiver(hid)
    if (who === 'supervisor') await hrExitApi.confirmSupervisor(hid)
    ElMessage.success('已确认')
    const d = await hrExitApi.getHandoverItems(currentResign.value.id)
    handoverItems.value = d.items || []
    loadResign()
  } catch (e) { if (e !== 'cancel') ElMessage.error('失败') }
}

// ---------- 数据复核 ----------
const reviewStatus = ref('pending')
const reviewList = ref([])
const reviewStatusLabel = (s) => ({ pending: '待审核', approved: '已通过', rejected: '已驳回' }[s] || s)
const reviewStatusTag = (s) => ({ pending: 'warning', approved: 'success', rejected: 'danger' }[s] || '')

const loadReviews = async () => {
  loading[1] = true
  try {
    const d = await hrExitApi.listChangeReviews({ status: reviewStatus.value, size: 500 })
    reviewList.value = d.items || []
  } finally { loading[1] = false }
}

const reviewApprove = async (row) => {
  try {
    const { value: opinion } = await ElMessageBox.prompt('复核意见（可留空）', '确认通过此变更', { inputPattern: /.*/ })
    await hrExitApi.approveChange(row.id, { opinion: opinion || '' })
    ElMessage.success('复核通过，档案已更新')
    loadReviews()
  } catch (e) { if (e !== 'cancel') ElMessage.error(e) }
}
const reviewReject = async (row) => {
  try {
    const { value: opinion } = await ElMessageBox.prompt('请填写驳回理由（必填）', '驳回变更',
      { inputValidator: v => !!v || '请填写理由' })
    await hrExitApi.rejectChange(row.id, { opinion })
    ElMessage.info('已驳回')
    loadReviews()
  } catch {}
}

// ---------- 审批分析 ----------
const days = ref(90)
const analytics = reactive({ template_stats: [], node_bottleneck: [], optimization_suggestions: [] })
const loadAnalytics = async () => {
  const d = await analyticsApi.approvalAnalytics({ days: days.value })
  Object.assign(analytics, d)
}

// ---------- 批量操作 ----------
const batchForm = reactive({
  person_ids: '', to_department: '', to_position: '', to_rank: '',
  effective_date: '', reason: '',
  year: new Date().getFullYear(), month: new Date().getMonth() + 1, file: null,
  personsJSON: '',
})
const importResult = ref('')
const batchCreateResult = ref('')
const onFileChange = (f) => { batchForm.file = f.raw }

const submitBatchTransfer = async () => {
  try {
    let pids = JSON.parse(batchForm.person_ids)
    if (!Array.isArray(pids) || pids.length === 0) throw 0
    const r = await analyticsApi.batchTransferDepartment({
      person_ids: pids,
      to_department: batchForm.to_department || undefined,
      to_position: batchForm.to_position || undefined,
      to_rank: batchForm.to_rank || undefined,
      effective_date: batchForm.effective_date || undefined,
      reason: batchForm.reason || '',
    })
    ElMessage.success(r.message)
  } catch {
    ElMessage.error('人员ID格式不正确，应为 JSON 数组，如 [1,2,3]')
  }
}

const submitAttendanceImport = async () => {
  if (!batchForm.file) return
  const fd = new FormData()
  fd.append('file', batchForm.file)
  try {
    const r = await analyticsApi.batchImportAttendance(fd, batchForm.year, batchForm.month)
    importResult.value = `导入完成：总计 ${r.total} 条，成功 ${r.ok} 条，失败 ${r.fail} 条。${r.fail_details && r.fail_details.length ? '部分失败：' + r.fail_details.join('；') : ''}`
  } catch (e) {
    importResult.value = '导入失败：' + (e?.message || e)
  }
}

const submitBatchCreate = async () => {
  try {
    let persons = JSON.parse(batchForm.personsJSON)
    if (!Array.isArray(persons) || persons.length === 0) throw 0
    const r = await analyticsApi.batchCreatePersons(persons)
    batchCreateResult.value = `批量入职完成：成功 ${r.success_count} 条，失败 ${r.fail_count} 条。${r.fail_details && r.fail_details.length ? '失败原因：' + r.fail_details.join('；') : ''}`
  } catch {
    ElMessage.error('人员列表格式不正确，应为 JSON 数组')
  }
}

onMounted(() => {
  loadResign()
  loadReviews()
  loadAnalytics()
})
</script>

<style scoped>
.pg { padding: 16px; }
.h { font-weight: 600; color: #303133; }
</style>
