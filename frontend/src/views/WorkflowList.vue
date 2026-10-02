<template>
  <div class="page-container">
    <div class="section-title">流程审批</div>

    <el-card>
      <div class="toolbar">
        <el-button type="primary" @click="openCreate">
          <el-icon :icon="Plus" /> 发起流程
        </el-button>
        <el-button @click="loadData">
          <el-icon :icon="Refresh" /> 刷新
        </el-button>
      </div>

      <el-tabs v-model="activeTab" @tab-change="onTabChange" style="margin-top: 12px">
        <el-tab-pane label="待我审批" name="my_approve" />
        <el-tab-pane label="我已审批" name="my_handled" />
        <el-tab-pane v-if="auth.isAdmin" label="审批记录" name="approval_record" />
        <el-tab-pane label="我发起的" name="my_apply" />
      </el-tabs>

      <el-table :data="list" v-loading="loading" border stripe>
        <el-table-column label="标题" min-width="220">
          <template #default="{ row }">
            <el-link type="primary" @click="openDetail(row)">{{ row.title }}</el-link>
          </template>
        </el-table-column>
        <el-table-column label="流程类型" width="140" align="center">
          <template #default="{ row }">
            <el-tag size="small" type="info">{{ row.template_name || row.template?.name || '—' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="110" align="center">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="申请人" width="120">
          <template #default="{ row }">{{ row.applicant_name || row.applicant?.name || '—' }}</template>
        </el-table-column>
        <el-table-column label="当前节点" width="140">
          <template #default="{ row }">{{ row.current_node_name || row.current_node || '—' }}</template>
        </el-table-column>
        <el-table-column label="提交时间" width="170">
          <template #default="{ row }">{{ formatTime(row.created_at || row.submitted_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="openDetail(row)">详情</el-button>
            <template v-if="row.status === 'pending'">
              <template v-if="activeTab === 'my_apply'">
                <el-button size="small" type="warning" @click="onWithdraw(row)">撤回</el-button>
              </template>
              <template v-if="activeTab === 'my_approve'">
                <el-button size="small" type="success" @click="openApprove(row, 'approve')">同意</el-button>
                <el-button size="small" type="danger" @click="openApprove(row, 'reject')">拒绝</el-button>
              </template>
            </template>
            <template v-if="row.status === 'approved'">
              <el-button v-if="isExpenseRow(row)" size="small" type="primary" plain @click="downloadVoucher(row)">凭证</el-button>
              <el-button size="small" type="success" plain @click="downloadApprovedForm(row)">下载审批单</el-button>
            </template>
            <template v-if="row.status === 'rejected'">
              <el-button size="small" type="info" plain @click="downloadApprovedForm(row)">查看</el-button>
            </template>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!loading && list.length === 0" description="暂无流程" />

      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next, jumper"
        style="margin-top: 16px; justify-content: flex-end"
        @current-change="loadData"
      />
    </el-card>

    <!-- 发起流程对话框 -->
    <el-dialog v-model="createVisible" title="发起流程" width="640px" @closed="resetCreate">
      <!-- 第一步：选择模板 -->
      <div v-if="!selectedTemplate">
        <div v-if="templates.length === 0 && !templateLoading" class="empty-tip">暂无可用流程模板</div>
        <div v-loading="templateLoading" class="template-grid">
          <el-card
            v-for="tpl in templates"
            :key="tpl.id"
            class="template-card"
            shadow="hover"
            @click="selectTemplate(tpl)"
          >
            <div class="tpl-name">{{ tpl.name }}</div>
            <div class="tpl-desc">{{ tpl.description || '暂无描述' }}</div>
          </el-card>
        </div>
      </div>

      <!-- 第二步：填写表单 -->
      <div v-else>
        <div class="selected-tpl">
          <el-tag type="info">{{ selectedTemplate.name }}</el-tag>
          <el-button link type="primary" @click="selectedTemplate = null">重新选择</el-button>
        </div>
        <el-form ref="createFormRef" :model="createForm" :rules="createRules" label-width="100px" style="margin-top: 12px">
          <el-form-item label="流程标题" prop="title">
            <el-input v-model="createForm.title" placeholder="请输入流程标题" />
          </el-form-item>
          <el-form-item
            v-for="field in formSchema"
            :key="field.key"
            :label="field.label"
            :prop="field.key"
            :rules="field.required ? [{ required: true, message: `请输入${field.label}`, trigger: 'change' }] : []"
          >
            <el-input
              v-if="field.type === 'text'"
              v-model="createForm[field.key]"
              :placeholder="`请输入${field.label}`"
            />
            <el-input
              v-else-if="field.type === 'textarea'"
              v-model="createForm[field.key]"
              type="textarea"
              :rows="3"
              :placeholder="`请输入${field.label}`"
            />
            <el-input-number
              v-else-if="field.type === 'number'"
              v-model="createForm[field.key]"
              style="width: 100%"
            />
            <el-date-picker
              v-else-if="field.type === 'date'"
              v-model="createForm[field.key]"
              type="date"
              value-format="YYYY-MM-DD"
              :placeholder="`请选择${field.label}`"
              style="width: 100%"
            />
            <el-select
              v-else-if="field.type === 'select'"
              v-model="createForm[field.key]"
              :placeholder="`请选择${field.label}`"
              style="width: 100%"
            >
              <el-option
                v-for="opt in field.options || []"
                :key="opt.value ?? opt"
                :label="opt.label ?? opt"
                :value="opt.value ?? opt"
              />
            </el-select>
          </el-form-item>

          <!-- 附件上传 -->
          <el-form-item label="附件">
            <el-upload
              v-model:file-list="createFileList"
              :auto-upload="false"
              multiple
              :limit="10"
              :on-exceed="handleUploadExceed"
              accept=".jpg,.jpeg,.png,.bmp,.tiff,.pdf,.doc,.docx,.xls,.xlsx"
            >
              <el-button type="primary" plain>
                <el-icon :icon="UploadFilled" /> 选择文件
              </el-button>
              <div class="upload-tip">支持图片(jpg/png/bmp/tiff)、PDF、Word、Excel，最多10个文件</div>
            </el-upload>
          </el-form-item>
        </el-form>
      </div>

      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button v-if="selectedTemplate" type="primary" :loading="creating" @click="onCreate">提交</el-button>
      </template>
    </el-dialog>

    <!-- 详情抽屉 -->
    <el-drawer v-model="detailVisible" title="流程详情" size="640px">
      <div v-if="detail" v-loading="detailLoading" class="wf-detail">
        <div class="detail-title">{{ detail.title }}</div>
        <div class="detail-meta">
          <el-tag :type="statusType(detail.status)" size="small">{{ statusLabel(detail.status) }}</el-tag>
          <span>流程类型：{{ detail.template_name || detail.template?.name || '—' }}</span>
          <span>申请人：{{ detail.applicant_name || detail.applicant?.name || '—' }}</span>
          <span>当前节点：{{ detail.current_node_name || detail.current_node || '—' }}</span>
          <span>提交时间：{{ formatTime(detail.created_at || detail.submitted_at) }}</span>
        </div>

        <!-- 表单数据：使用 detail.form_schema 渲染 -->
        <el-divider content-position="left">表单数据</el-divider>
        <div v-if="detailFormSchema.length" class="form-data">
          <div v-for="field in detailFormSchema" :key="field.key" class="form-row">
            <div class="form-label">{{ field.label }}</div>
            <div class="form-value">{{ formatFormValue(detail.form_data, field) }}</div>
          </div>
        </div>
        <!-- 无 form_schema 时，显示原始键值对 -->
        <div v-else-if="detail.form_data && Object.keys(detail.form_data).length" class="form-data">
          <div v-for="(val, key) in detail.form_data" :key="key" class="form-row">
            <div class="form-label">{{ key }}</div>
            <div class="form-value">{{ val === null || val === undefined || val === '' ? '—' : val }}</div>
          </div>
        </div>
        <el-empty v-if="!detail.form_data || !Object.keys(detail.form_data).length" description="无表单数据" :image-size="60" />

        <!-- 附件管理 -->
        <el-divider content-position="left">
          <span>附件列表</span>
          <el-tag size="small" type="info" style="margin-left: 8px">{{ detailAttachments.length }} 个文件</el-tag>
        </el-divider>
        <div class="attachment-section">
          <template v-if="detailAttachments.length">
          <div class="attachment-list">
            <div
              v-for="att in detailAttachments"
              :key="att.id"
              class="attachment-item"
            >
              <div class="att-icon" :title="att.file_type || ''">
                <el-icon :size="28" :icon="fileIcon(att)" />
              </div>
              <div class="att-info">
                <div class="att-name">
                  <el-link type="primary" :href="att.download_url" target="_blank">{{ att.filename }}</el-link>
                  <el-tag
                    v-if="att.is_invoice"
                    size="small"
                    type="warning"
                    style="margin-left: 6px"
                  >发票</el-tag>
                  <el-tag
                    v-if="att.ocr_status === 'success'"
                    size="small"
                    type="success"
                    style="margin-left: 4px"
                  >已识别</el-tag>
                  <el-tag
                    v-if="att.verification_status === 'verified'"
                    size="small"
                    type="success"
                    style="margin-left: 4px"
                  >真</el-tag>
                  <el-tag
                    v-else-if="att.verification_status === 'fake'"
                    size="small"
                    type="danger"
                    style="margin-left: 4px"
                  >伪</el-tag>
                  <el-tag
                    v-if="att.duplicate === true"
                    size="small"
                    type="warning"
                    style="margin-left: 4px"
                  >重复</el-tag>
                </div>
                <div class="att-meta">
                  <span>{{ formatFileSize(att.file_size) }}</span>
                  <span v-if="att.uploaded_at"> · {{ formatTime(att.uploaded_at) }}</span>
                </div>

                <!-- 发票 OCR 面板 -->
                <div v-if="att.is_invoice" class="invoice-ocr-panel">
                  <div class="ocr-actions">
                    <el-button
                      size="small"
                      type="primary"
                      plain
                      :loading="ocrLoading[att.id]"
                      @click="onOcrInvoice(att)"
                    >
                      🔍 发票智能识别
                    </el-button>
                    <el-button
                      size="small"
                      type="success"
                      plain
                      :disabled="!att.ocr_data"
                      :loading="verifyLoading[att.id]"
                      @click="onVerifyInvoice(att)"
                    >
                      ✅ 发票验真
                    </el-button>
                    <el-button
                      size="small"
                      type="warning"
                      plain
                      :disabled="!att.ocr_data"
                      :loading="duplicateLoading[att.id]"
                      @click="onCheckDuplicate(att)"
                    >
                      ⚠️ 发票查重
                    </el-button>
                  </div>

                  <!-- OCR 识别结果 -->
                  <div v-if="att.ocr_data" class="ocr-result">
                    <el-descriptions :column="2" size="small" border>
                      <el-descriptions-item label="发票号码">{{ att.ocr_data.invoice_number || '—' }}</el-descriptions-item>
                      <el-descriptions-item label="开票日期">{{ att.ocr_data.invoice_date || '—' }}</el-descriptions-item>
                      <el-descriptions-item label="金额">{{ att.ocr_data.amount || att.ocr_data.total_amount || '—' }}</el-descriptions-item>
                      <el-descriptions-item label="发票类型">{{ att.ocr_data.invoice_type || '—' }}</el-descriptions-item>
                      <el-descriptions-item label="销售方">{{ att.ocr_data.seller || '—' }}</el-descriptions-item>
                      <el-descriptions-item label="购买方">{{ att.ocr_data.buyer || '—' }}</el-descriptions-item>
                    </el-descriptions>
                  </div>

                  <!-- 验真结果 -->
                  <div v-if="att.verification_result" class="verify-result">
                    <el-alert
                      :title="att.verification_result.verified ? '✅ 发票验真：真' : '❌ 发票验真：伪'"
                      :type="att.verification_result.verified ? 'success' : 'error'"
                      :description="att.verification_result.message || att.verification_result.details || ''"
                      show-icon
                      :closable="false"
                    />
                  </div>

                  <!-- 查重结果 -->
                  <div v-if="att.duplicate_result" class="duplicate-result">
                    <el-alert
                      :title="att.duplicate_result.is_duplicate ? '⚠️ 发票查重：发现重复' : '✅ 发票查重：无重复'"
                      :type="att.duplicate_result.is_duplicate ? 'warning' : 'success'"
                      :description="att.duplicate_result.message || ''"
                      show-icon
                      :closable="false"
                    />
                  </div>
                </div>
              </div>
              <div class="att-actions">
                <el-button
                  size="small"
                  type="danger"
                  link
                  @click="onDeleteAttachment(att)"
                >删除</el-button>
              </div>
            </div>
          </div>

          <div class="attachment-add">
            <el-upload
              :auto-upload="true"
              :show-file-list="false"
              :http-request="onAddAttachment"
              accept=".jpg,.jpeg,.png,.bmp,.tiff,.pdf,.doc,.docx,.xls,.xlsx"
            >
              <el-button size="small" plain>
                <el-icon :icon="Plus" /> 添加附件
              </el-button>
            </el-upload>
          </div>
          </template>
          <el-empty v-else description="暂无附件" :image-size="60" />
        </div>

        <!-- 凭证生成面板（仅报销类且已通过） -->
        <template v-if="isExpenseWorkflow && detail.status === 'approved'">
          <el-divider content-position="left">凭证管理</el-divider>
          <div class="voucher-section">
            <!-- 已有凭证 -->
            <div v-if="detailVoucher" class="voucher-existing">
              <el-tag type="success" size="small" style="margin-bottom: 8px">
                <el-icon :icon="CircleCheck" /> 凭证已生成
              </el-tag>
              <el-descriptions :column="1" size="small" border>
                <el-descriptions-item label="凭证编号">{{ detailVoucher.voucher_no || '—' }}</el-descriptions-item>
                <el-descriptions-item label="凭证日期">{{ detailVoucher.voucher_date || '—' }}</el-descriptions-item>
                <el-descriptions-item label="摘要">{{ detailVoucher.summary || '—' }}</el-descriptions-item>
                <el-descriptions-item label="借方合计">{{ detailVoucher.total_debit || '—' }}</el-descriptions-item>
                <el-descriptions-item label="贷方合计">{{ detailVoucher.total_credit || '—' }}</el-descriptions-item>
              </el-descriptions>
              <div v-if="detailVoucher.items?.length" class="voucher-items">
                <div class="voucher-sub-title">凭证明细</div>
                <el-table :data="detailVoucher.items" size="small" border>
                  <el-table-column prop="subject" label="科目" />
                  <el-table-column prop="debit" label="借方金额" align="right">
                    <template #default="{ row }">
                      <span v-if="row.debit">{{ row.debit }}</span>
                      <span v-else class="muted">—</span>
                    </template>
                  </el-table-column>
                  <el-table-column prop="credit" label="贷方金额" align="right">
                    <template #default="{ row }">
                      <span v-if="row.credit">{{ row.credit }}</span>
                      <span v-else class="muted">—</span>
                    </template>
                  </el-table-column>
                </el-table>
              </div>
            </div>
            <!-- 未生成凭证 -->
            <div v-else class="voucher-empty">
              <div v-if="voucherLoading" class="voucher-loading">正在加载凭证数据...</div>
              <el-button
                v-else
                type="primary"
                :loading="generatingVoucher"
                @click="onGenerateVoucher"
              >
                📝 一键生成凭证
              </el-button>
            </div>
          </div>
        </template>

        <!-- 审批流程 -->
        <el-divider content-position="left">审批流程</el-divider>
        <el-timeline v-if="approvalNodes.length">
          <el-timeline-item
            v-for="(node, idx) in approvalNodes"
            :key="idx"
            :type="nodeTimelineType(node)"
            :timestamp="formatTime(node.handled_at || node.created_at)"
            placement="top"
          >
            <div class="node-title">
              <span>{{ node.name || node.node_name || `节点 ${idx + 1}` }}</span>
              <el-tag :type="nodeStatusType(node.status)" size="small" style="margin-left: 8px">
                {{ nodeStatusLabel(node.status) }}
              </el-tag>
            </div>
            <div class="node-info">处理人：{{ node.assignee_name || node.handler_name || node.assignee?.name || '—' }}</div>
            <div v-if="node.opinion" class="node-info">审批意见：{{ node.opinion }}</div>
          </el-timeline-item>
        </el-timeline>
        <el-empty v-else description="暂无审批记录" :image-size="60" />

        <!-- 详情中的操作按钮 -->
        <div class="detail-actions">
          <template v-if="activeTab === 'my_apply' && detail?.status === 'pending'">
            <el-button type="warning" @click="onWithdraw(detail)">撤回流程</el-button>
          </template>
          <template v-if="activeTab === 'my_approve' && detail?.status === 'pending'">
            <el-button type="success" @click="openApprove(detail, 'approve')">同意</el-button>
            <el-button type="danger" @click="openApprove(detail, 'reject')">拒绝</el-button>
          </template>
          <template v-if="detail?.status === 'approved'">
            <el-button v-if="isExpenseRow(detail)" type="primary" @click="downloadVoucher(detail)">📥 下载凭证</el-button>
            <el-button type="success" @click="downloadApprovedForm(detail)">📄 下载审批单</el-button>
          </template>
          <template v-if="detail?.status === 'rejected'">
            <el-button type="info" @click="downloadApprovedForm(detail)">📄 查看审批详情</el-button>
          </template>
        </div>
      </div>
    </el-drawer>

    <!-- 审批对话框 -->
    <el-dialog v-model="approveVisible" :title="approveAction === 'approve' ? '同意审批' : '拒绝审批'" width="600px">
      <!-- 审批请求详情 -->
      <div v-if="approveTarget" class="approve-detail">
        <div class="approve-section">
          <div class="approve-section-title">📋 流程信息</div>
          <div class="approve-info-row">
            <span class="approve-info-label">标题：</span>
            <span class="approve-info-value">{{ approveTarget.title }}</span>
          </div>
          <div class="approve-info-row">
            <span class="approve-info-label">类型：</span>
            <span class="approve-info-value">{{ approveTarget.template_name || approveTarget.template?.name || '—' }}</span>
          </div>
          <div class="approve-info-row">
            <span class="approve-info-label">申请人：</span>
            <span class="approve-info-value">{{ approveTarget.applicant_name || approveTarget.applicant?.name || '—' }}</span>
          </div>
        </div>

        <!-- 表单数据 -->
        <div class="approve-section">
          <div class="approve-section-title">📝 表单数据</div>
          <div v-if="approveFormSchema.length" class="approve-form-data">
            <div v-for="field in approveFormSchema" :key="field.key" class="approve-form-row">
              <span class="approve-form-label">{{ field.label }}：</span>
              <span class="approve-form-value">{{ formatFormValue(approveTarget.form_data, field) }}</span>
            </div>
          </div>
          <div v-else-if="approveTarget.form_data && Object.keys(approveTarget.form_data).length" class="approve-form-data">
            <div v-for="(val, key) in approveTarget.form_data" :key="key" class="approve-form-row">
              <span class="approve-form-label">{{ key }}：</span>
              <span class="approve-form-value">{{ val === null || val === undefined || val === '' ? '—' : val }}</span>
            </div>
          </div>
          <div v-else class="approve-empty">无表单数据</div>
        </div>

        <!-- 附件列表 -->
        <div v-if="approveAttachments.length" class="approve-section">
          <div class="approve-section-title">
            📎 附件列表
            <el-tag size="small" type="info" style="margin-left: 4px">{{ approveAttachments.length }}</el-tag>
          </div>
          <div class="approve-attachment-list">
            <div v-for="att in approveAttachments" :key="att.id" class="approve-attachment-item">
              <el-icon :size="20" :icon="fileIcon(att)" class="att-icon-mini" />
              <el-link :href="att.download_url" target="_blank" class="approve-attachment-name">
                {{ att.filename }}
              </el-link>
              <span class="approve-attachment-size">{{ formatFileSize(att.file_size) }}</span>
            </div>
          </div>
        </div>

        <el-alert
          type="info"
          :closable="false"
          show-icon
          title="请仔细审阅以上所有信息（包括表单数据和附件），确认无误后再进行审批操作。"
          style="margin: 12px 0"
        />
      </div>

      <el-form :model="approveForm" label-width="80px">
        <el-form-item label="审批意见" :required="approveAction === 'reject'">
          <el-input
            v-model="approveForm.opinion"
            type="textarea"
            :rows="4"
            :placeholder="approveAction === 'reject' ? '拒绝审批必须填写审批意见（如：不符合报销规定、材料不全等）' : '请输入审批意见（可选）'"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="approveVisible = false">取消</el-button>
        <el-button :type="approveAction === 'approve' ? 'success' : 'danger'" :loading="approving" @click="onApprove">
          确定
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh, UploadFilled, CircleCheck, Picture, Document, Grid, Files } from '@element-plus/icons-vue'
import { workflowApi, workflowTemplateApi, expenseApi } from '@/api'
import { useAuthStore } from '@/stores/auth'
import { exportVoucherDocx, exportApprovalFormDocx } from '@/utils/docxExport'

const auth = useAuthStore()
const route = useRoute()

const list = ref([])
const loading = ref(false)
const activeTab = ref('my_approve')
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

// 发起流程
const createVisible = ref(false)
const templates = ref([])
const templateLoading = ref(false)
const selectedTemplate = ref(null)
const createFormRef = ref(null)
const creating = ref(false)
const createForm = reactive({})
const createRules = {
  title: [{ required: true, message: '请输入流程标题', trigger: 'blur' }],
}
const createFileList = ref([])

// 详情
const detailVisible = ref(false)
const detail = ref(null)
const detailLoading = ref(false)

// 详情附件
const detailAttachments = ref([])
const ocrLoading = reactive({})
const verifyLoading = reactive({})
const duplicateLoading = reactive({})

// 凭证
const detailVoucher = ref(null)
const voucherLoading = ref(false)
const generatingVoucher = ref(false)

// 审批
const approveVisible = ref(false)
const approving = ref(false)
const approveAction = ref('approve')
const approveForm = reactive({ opinion: '' })
const approveTarget = ref(null)
const approveAttachments = ref([])

const statusLabel = (s) => ({
  pending: '审批中',
  approved: '已通过',
  rejected: '已拒绝',
  withdrawn: '已撤回',
}[s] || s || '—')

const statusType = (s) => ({
  pending: 'primary',
  approved: 'success',
  rejected: 'danger',
  withdrawn: 'info',
}[s] || 'info')

const nodeStatusLabel = (s) => ({
  pending: '待处理',
  approved: '已通过',
  rejected: '已拒绝',
  withdrawn: '已撤回',
  current: '进行中',
  done: '已完成',
  skipped: '已跳过',
}[s] || (s || '—'))

const nodeStatusType = (s) => ({
  pending: 'info',
  current: 'primary',
  approved: 'success',
  done: 'success',
  rejected: 'danger',
  withdrawn: 'info',
  skipped: 'info',
}[s] || 'info')

const nodeTimelineType = (node) => {
  const s = node.status
  if (s === 'approved' || s === 'done') return 'success'
  if (s === 'rejected') return 'danger'
  if (s === 'current' || s === 'pending') return 'primary'
  return 'info'
}

// 模板表单 schema（用于创建对话框）
const formSchema = computed(() => {
  const tpl = selectedTemplate.value || detail.value?.template
  if (!tpl) return []
  let schema = tpl.form_schema
  if (typeof schema === 'string') {
    try { schema = JSON.parse(schema) } catch (e) { schema = [] }
  }
  return Array.isArray(schema) ? schema : []
})

// 详情表单 schema（优先使用 detail.form_schema，回退到模板的 form_schema）
const detailFormSchema = computed(() => {
  if (!detail.value) return []
  let schema = detail.value.form_schema
  if (schema) {
    if (typeof schema === 'string') {
      try { schema = JSON.parse(schema) } catch (e) { schema = null }
    }
    if (Array.isArray(schema) && schema.length) return schema
  }
  const tpl = detail.value.template
  if (tpl) {
    let tplSchema = tpl.form_schema
    if (typeof tplSchema === 'string') {
      try { tplSchema = JSON.parse(tplSchema) } catch (e) { tplSchema = [] }
    }
    if (Array.isArray(tplSchema)) return tplSchema
  }
  return []
})

// 审批对话框中的表单 schema
const approveFormSchema = computed(() => {
  if (!approveTarget.value) return []
  let schema = approveTarget.value.form_schema
  if (schema) {
    if (typeof schema === 'string') {
      try { schema = JSON.parse(schema) } catch (e) { schema = null }
    }
    if (Array.isArray(schema) && schema.length) return schema
  }
  const tpl = approveTarget.value.template
  if (tpl) {
    let tplSchema = tpl.form_schema
    if (typeof tplSchema === 'string') {
      try { tplSchema = JSON.parse(tplSchema) } catch (e) { tplSchema = [] }
    }
    if (Array.isArray(tplSchema)) return tplSchema
  }
  return []
})

// 是否报销类流程（用于列表行判断）
const isExpenseRow = (row) => {
  if (!row) return false
  const tpl = row.template
  const category = tpl?.category || tpl?.type || ''
  return category === 'expense' || category === '报销' ||
    (tpl?.name && (tpl.name.includes('报销') || tpl.name.includes('expense')))
}

// 是否报销类流程（用于详情判断）
const isExpenseWorkflow = computed(() => {
  if (!detail.value) return false
  const tpl = detail.value.template
  if (!tpl) return false
  const category = tpl.category || tpl.type || ''
  return category === 'expense' || category === '报销' ||
    (tpl.name && (tpl.name.includes('报销') || tpl.name.includes('expense')))
})

const approvalNodes = computed(() => {
  if (!detail.value) return []
  const nodes = detail.value.nodes || detail.value.approval_nodes || []
  return Array.isArray(nodes) ? nodes : []
})

const detailActions = computed(() => {
  if (!detail.value) return []
  const actions = []
  if (activeTab.value === 'my_apply' && detail.value.status === 'pending') actions.push('withdraw')
  if (activeTab.value === 'my_approve' && detail.value.status === 'pending') {
    actions.push('approve')
    actions.push('reject')
  }
  return actions
})

const formatTime = (t) => {
  if (!t) return ''
  return String(t).replace('T', ' ').slice(0, 19)
}

// 后端返回的凭证数据 → 前端展示格式
const normalizeVoucher = (v) => {
  if (!v) return null
  const debitItems = v.debit_items || []
  const creditItems = v.credit_items || []
  const items = [
    ...debitItems.map(it => ({
      subject: it.account || '',
      debit: it.amount || 0,
      credit: '',
      summary: it.summary || '',
    })),
    ...creditItems.map(it => ({
      subject: it.account || '',
      debit: '',
      credit: it.amount || 0,
      summary: it.summary || '',
    })),
  ]
  const totalDebit = debitItems.reduce((s, it) => s + (it.amount || 0), 0)
  const totalCredit = creditItems.reduce((s, it) => s + (it.amount || 0), 0)
  return {
    voucher_no: v.voucher_number,
    voucher_date: v.voucher_date,
    summary: v.summary,
    total_debit: totalDebit.toFixed(2),
    total_credit: totalCredit.toFixed(2),
    items,
  }
}

// 后端OCR结果 → 前端展示格式
const normalizeOcrData = (data) => {
  if (!data) return null
  return {
    invoice_number: data.invoice_number,
    invoice_date: data.invoice_date,
    amount: data.total_amount || data.invoice_amount,
    total_amount: data.total_amount,
    seller: data.seller_name,
    buyer: data.buyer_name,
    invoice_type: data.invoice_type,
    confidence: data.confidence,
    raw_text: data.raw_text,
  }
}

// 后端验真结果 → 前端展示格式
const normalizeVerifyResult = (data) => {
  if (!data) return null
  const verified = data.verify_result === 'real'
  const detail = data.verify_detail || {}
  return {
    verified,
    message: verified ? '✅ 真发票，验证通过' : '❌ 验真失败：' + (detail.result || '信息不符'),
    details: detail,
  }
}

const formatFormValue = (formData, field) => {
  if (!formData) return '—'
  const val = formData[field.key]
  if (val === null || val === undefined || val === '') return '—'
  if (field.type === 'select' && Array.isArray(field.options)) {
    const opt = field.options.find((o) => (o.value ?? o) === val)
    if (opt) return opt.label ?? opt.value ?? opt
  }
  return val
}

const formatFileSize = (bytes) => {
  if (!bytes) return ''
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1024 / 1024).toFixed(2) + ' MB'
}

const fileIcon = (att) => {
  const type = (att.file_type || '').toLowerCase()
  const ext = (att.filename || '').split('.').pop()?.toLowerCase() || ''
  if (['jpg', 'jpeg', 'png', 'bmp', 'tiff', 'gif'].includes(ext) || type.startsWith('image')) return Picture
  if (ext === 'pdf' || type.includes('pdf')) return Document
  if (['doc', 'docx'].includes(ext)) return Document
  if (['xls', 'xlsx'].includes(ext)) return Grid
  return Files
}

const handleUploadExceed = () => {
  ElMessage.warning('最多只能上传 10 个文件')
}

const loadData = async () => {
  loading.value = true
  try {
    const res = await workflowApi.list({
      tab: activeTab.value,
      page: page.value,
      page_size: pageSize.value,
    })
    if (Array.isArray(res)) {
      list.value = res
      total.value = res.length
    } else {
      list.value = res.items || res.data || []
      total.value = res.total ?? list.value.length
    }
  } finally {
    loading.value = false
  }
}

const onTabChange = () => {
  page.value = 1
  loadData()
}

const loadTemplates = async () => {
  templateLoading.value = true
  try {
    const res = await workflowTemplateApi.list({ is_active: true })
    if (Array.isArray(res)) {
      templates.value = res
    } else {
      templates.value = res.items || res.data || []
    }
  } finally {
    templateLoading.value = false
  }
}

const resetCreate = () => {
  selectedTemplate.value = null
  Object.keys(createForm).forEach((k) => delete createForm[k])
  createFormRef.value?.clearValidate?.()
  createFileList.value = []
}

const openCreate = async () => {
  resetCreate()
  createVisible.value = true
  await loadTemplates()
}

const selectTemplate = (tpl) => {
  selectedTemplate.value = tpl
  Object.keys(createForm).forEach((k) => delete createForm[k])
  createForm.title = ''
  const schema = (() => {
    let s = tpl.form_schema
    if (typeof s === 'string') { try { s = JSON.parse(s) } catch (e) { s = [] } }
    return Array.isArray(s) ? s : []
  })()
  schema.forEach((f) => {
    createForm[f.key] = f.type === 'number' ? undefined : ''
  })
}

const onCreate = async () => {
  await createFormRef.value?.validate?.()
  creating.value = true
  try {
    const formData = {}
    formSchema.value.forEach((f) => {
      formData[f.key] = createForm[f.key]
    })
    const result = await workflowApi.create({
      template_id: selectedTemplate.value.id,
      title: createForm.title,
      form_data: formData,
    })
    const instanceId = result?.id
    if (instanceId && createFileList.value.length > 0) {
      const files = createFileList.value.map(f => f.raw).filter(Boolean)
      if (files.length) {
        try {
          await expenseApi.uploadAttachments(instanceId, files)
        } catch (e) {
          ElMessage.warning('流程已创建，但部分附件上传失败')
        }
      }
    }
    ElMessage.success('流程发起成功')
    createVisible.value = false
    page.value = 1
    activeTab.value = 'my_apply'
    loadData()
  } finally {
    creating.value = false
  }
}

const openDetail = async (row) => {
  detail.value = row
  detailVisible.value = true
  detailLoading.value = true
  detailAttachments.value = []
  detailVoucher.value = null
  try {
    const data = await workflowApi.get(row.id)
    detail.value = { ...row, ...data }
    loadDetailAttachments(row.id)
    if (isExpenseWorkflow.value && detail.value.status === 'approved') {
      loadVoucher(row.id)
    }
  } finally {
    detailLoading.value = false
  }
}

const loadDetailAttachments = async (instanceId) => {
  try {
    const res = await expenseApi.listAttachments(instanceId)
    detailAttachments.value = Array.isArray(res) ? res : (res.items || res.data || [])
  } catch (e) {
    detailAttachments.value = []
  }
}

const loadVoucher = async (instanceId) => {
  voucherLoading.value = true
  try {
    const data = await expenseApi.getVoucher(instanceId)
    detailVoucher.value = normalizeVoucher(data)
  } catch (e) {
    detailVoucher.value = null
  } finally {
    voucherLoading.value = false
  }
}

const onAddAttachment = async (uploadFile) => {
  if (!detail.value) return
  try {
    await expenseApi.uploadAttachments(detail.value.id, [uploadFile.file])
    ElMessage.success('附件上传成功')
    loadDetailAttachments(detail.value.id)
  } catch (e) {
    ElMessage.error('附件上传失败')
  }
}

const onDeleteAttachment = (att) => {
  ElMessageBox.confirm(`确定删除附件「${att.filename}」吗？`, '删除确认', {
    type: 'warning',
    confirmButtonText: '确定删除',
    cancelButtonText: '取消',
  })
    .then(async () => {
      await expenseApi.deleteAttachment(att.id)
      ElMessage.success('删除成功')
      loadDetailAttachments(detail.value.id)
    })
    .catch(() => {})
}

const onOcrInvoice = async (att) => {
  ocrLoading[att.id] = true
  try {
    const data = await expenseApi.ocrInvoice(att.id)
    att.ocr_data = normalizeOcrData(data)
    att.ocr_status = 'success'
    ElMessage.success('发票识别成功')
  } catch (e) {
    ElMessage.error('发票识别失败')
  } finally {
    ocrLoading[att.id] = false
  }
}

const onVerifyInvoice = async (att) => {
  if (!att.ocr_data) return
  verifyLoading[att.id] = true
  try {
    const data = await expenseApi.verifyInvoice({
      invoice_number: att.ocr_data.invoice_number,
      invoice_date: att.ocr_data.invoice_date,
      total_amount: att.ocr_data.total_amount || att.ocr_data.amount,
    })
    att.verification_result = normalizeVerifyResult(data)
    att.verification_status = data?.verify_result === 'real' ? 'verified' : 'fake'
    ElMessage.success(att.verification_status === 'verified' ? '发票验真：真' : '发票验真：伪')
  } catch (e) {
    ElMessage.error('发票验真失败')
  } finally {
    verifyLoading[att.id] = false
  }
}

const onCheckDuplicate = async (att) => {
  if (!att.ocr_data) return
  duplicateLoading[att.id] = true
  try {
    const data = await expenseApi.checkDuplicate({
      invoice_number: att.ocr_data.invoice_number,
      invoice_date: att.ocr_data.invoice_date,
    })
    att.duplicate_result = data
    att.duplicate = data?.is_duplicate || false
    if (data?.is_duplicate) {
      ElMessage.warning('⚠️ 该发票可能重复报销！')
    } else {
      ElMessage.success('✅ 该发票未重复报销')
    }
  } catch (e) {
    ElMessage.error('查重操作失败')
  } finally {
    duplicateLoading[att.id] = false
  }
}

const onGenerateVoucher = async () => {
  if (!detail.value) return
  generatingVoucher.value = true
  try {
    const data = await expenseApi.generateVoucher({
      instance_id: detail.value.id,
    })
    detailVoucher.value = normalizeVoucher(data)
    ElMessage.success('凭证生成成功')
  } catch (e) {
    ElMessage.error('凭证生成失败')
  } finally {
    generatingVoucher.value = false
  }
}

const downloadVoucher = async (row) => {
  if (!isExpenseRow(row)) {
    ElMessage.info('该流程为非报销流程，仅报销流程可生成记账凭证')
    return
  }
  try {
    const voucher = await expenseApi.getVoucher(row.id)
    if (!voucher) {
      ElMessage.warning('该流程尚未生成凭证，请先在详情页点击"一键生成凭证"')
      return
    }
    const normalized = normalizeVoucher(voucher)
    await exportVoucherDocx(row, normalized)
    ElMessage.success('凭证下载成功（Word文档）')
  } catch (e) {
    console.error(e)
    ElMessage.error('凭证下载失败')
  }
}

const downloadApprovedForm = async (row) => {
  try {
    let data = row
    // 如果列表行没有 nodes 数据，先获取详情
    if (!row.nodes || row.nodes.length === 0) {
      try {
        const detailData = await workflowApi.get(row.id)
        if (detailData) data = detailData
      } catch (e) { /* ignore, use row data */ }
    }
    await exportApprovalFormDocx(data)
    ElMessage.success('审批单下载成功（Word文档）')
  } catch (e) {
    console.error(e)
    ElMessage.error('审批单下载失败')
  }
}

const buildVoucherHtml = (voucher, row) => {
  const items = [...(voucher.debit_items || []), ...(voucher.credit_items || [])]
  const itemsHtml = items.map(it => `
    <tr>
      <td>${it.account || ''}</td>
      <td>${it.summary || ''}</td>
      <td style="text-align:right">${it.debit || ''}</td>
      <td style="text-align:right">${it.credit || ''}</td>
    </tr>
  `).join('')
  return `<!DOCTYPE html><html><head><meta charset="UTF-8"><title>记账凭证</title>
  <style>body{font-family:'Microsoft YaHei',sans-serif;padding:40px;}h2{text-align:center;}table{width:100%;border-collapse:collapse;margin-top:20px;}th,td{border:1px solid #333;padding:8px;text-align:center;}th{background:#f0f0f0;}.info{display:flex;justify-content:space-between;margin:20px 0;}</style>
  </head><body>
  <h2>记 账 凭 证</h2>
  <div class="info"><span>凭证编号：${voucher.voucher_number || '—'}</span><span>日期：${voucher.voucher_date || '—'}</span></div>
  <table><thead><tr><th style="width:30%">科目</th><th>摘要</th><th style="width:15%">借方金额</th><th style="width:15%">贷方金额</th></tr></thead>
  <tbody>${itemsHtml}</tbody></table>
  <p style="margin-top:30px;text-align:right">制单：<span>${row.applicant_name || ''}</span> &nbsp;&nbsp; 审核：<span>财务</span></p>
  </body></html>`
}

const buildApprovedFormHtml = (row) => {
  const formData = row.form_data || {}
  const formItems = Object.entries(formData).map(([k, v]) => {
    const labelMap = {
      expense_type: '费用类型', amount: '金额', reason: '事由',
      start_date: '开始日期', end_date: '结束日期', days: '天数',
      leave_type: '请假类型', remark: '备注', seal_type: '用章类型',
      seal_reason: '用章事由', file_name: '文件名称',
      purchaser: '采购人', supplier: '供应商', items: '采购明细',
      budget: '预算', total_amount: '总金额',
    }
    const displayKey = labelMap[k] || k
    let displayVal = v
    if (typeof v === 'object') displayVal = JSON.stringify(v)
    return `<tr><td style="width:30%">${displayKey}</td><td>${displayVal ?? '—'}</td></tr>`
  }).join('')

  const statusColor = row.status === 'approved' ? '#52c41a' : row.status === 'rejected' ? '#ff4d4f' : '#faad14'
  const nodes = row.nodes || []
  const nodesHtml = nodes.map((n, i) => {
    const nodeStatusText = n.status === 'approved' ? '<span style="color:#52c41a;font-weight:bold">✓ 已通过</span>'
      : n.status === 'rejected' ? '<span style="color:#ff4d4f;font-weight:bold">✗ 已拒绝</span>'
      : n.status === 'done' ? '<span style="color:#52c41a">✓ 已处理</span>'
      : n.status === 'skipped' ? '<span style="color:#999">⊘ 已跳过</span>'
      : '<span style="color:#faad14">待处理</span>'
    const opinionHtml = n.opinion ? `<div style="margin-top:4px;color:#666;font-size:13px">审批意见：${n.opinion}</div>` : ''
    const timeHtml = n.handled_at ? `<div style="color:#999;font-size:12px">${formatTime(n.handled_at)}</div>` : ''
    return `
      <tr>
        <td style="width:15%">步骤 ${i + 1}</td>
        <td style="width:25%">${n.node_name || '节点'}</td>
        <td style="width:15%">${n.handler_name || '—'}</td>
        <td style="width:15%">${nodeStatusText}</td>
        <td>${opinionHtml}${timeHtml}</td>
      </tr>`
  }).join('')

  return `<!DOCTYPE html><html><head><meta charset="UTF-8"><title>审批单</title>
  <style>
    body{font-family:'Microsoft YaHei',sans-serif;padding:40px;color:#333;}
    h2{text-align:center;margin-bottom:20px;}
    h3{margin-top:28px;margin-bottom:12px;border-left:4px solid #1677ff;padding-left:10px;}
    table{width:100%;border-collapse:collapse;margin-top:10px;font-size:14px;}
    th,td{border:1px solid #d9d9d9;padding:10px 12px;text-align:left;}
    th{background:#f5f5f5;font-weight:600;text-align:center;}
    .info-table td{background:#fafafa;}
    .approval-table td,.approval-table th{text-align:left;}
    .footer{margin-top:40px;text-align:right;font-size:13px;color:#666;}
  </style>
  </head><body>
  <h2>审 批 单</h2>
  <table class="info-table">
    <tr><td style="width:200px">标题</td><td>${row.title || '—'}</td></tr>
    <tr><td>流程类型</td><td>${row.template_name || '—'}</td></tr>
    <tr><td>状态</td><td style="color:${statusColor};font-weight:bold">${statusLabel(row.status)}</td></tr>
    <tr><td>申请人</td><td>${row.applicant_name || '—'}</td></tr>
    <tr><td>提交时间</td><td>${formatTime(row.submitted_at || row.created_at)}</td></tr>
    ${row.finished_at ? `<tr><td>完成时间</td><td>${formatTime(row.finished_at)}</td></tr>` : ''}
  </table>
  <h3>📋 表单数据</h3>
  <table><tbody>${formItems || '<tr><td colspan="2" style="text-align:center;color:#999">无表单数据</td></tr>'}</tbody></table>
  <h3>📝 审批流程</h3>
  <table class="approval-table">
    <thead><tr><th>步骤</th><th>节点</th><th>审批人</th><th>结果</th><th>审批意见 / 时间</th></tr></thead>
    <tbody>${nodesHtml || '<tr><td colspan="5" style="text-align:center;color:#999">暂无审批记录</td></tr>'}</tbody>
  </table>
  <div class="footer">
    <p>申请人签字：${row.applicant_name || ''} &nbsp;&nbsp; 日期：${formatTime(row.created_at)}</p>
    <p>系统生成时间：${formatTime(new Date().toISOString())}</p>
  </div>
  </body></html>`
}

const onWithdraw = (row) => {
  ElMessageBox.confirm(`确定撤回流程「${row.title}」吗？`, '撤回确认', {
    type: 'warning',
    confirmButtonText: '确定撤回',
    cancelButtonText: '取消',
  })
    .then(async () => {
      await workflowApi.withdraw(row.id)
      ElMessage.success('撤回成功')
      if (detail.value && detail.value.id === row.id) {
        detail.value = { ...detail.value, status: 'withdrawn' }
      }
      loadData()
    })
    .catch(() => {})
}

const openApprove = async (row, action) => {
  approveTarget.value = row
  approveAction.value = action
  approveForm.opinion = ''
  approveVisible.value = true
  approveAttachments.value = []
  try {
    const res = await expenseApi.listAttachments(row.id)
    approveAttachments.value = Array.isArray(res) ? res : (res.items || res.data || [])
  } catch (e) {
    approveAttachments.value = []
  }
}

const onApprove = async () => {
  if (!approveTarget.value) return
  // 拒绝审批时强制要求填写审批意见
  if (approveAction.value === 'reject' && (!approveForm.opinion || !approveForm.opinion.trim())) {
    ElMessage.warning('拒绝审批时必须填写审批意见')
    return
  }
  approving.value = true
  try {
    await workflowApi.approve(approveTarget.value.id, {
      action: approveAction.value,
      opinion: approveForm.opinion,
    })
    ElMessage.success(approveAction.value === 'approve' ? '已同意' : '已拒绝')
    approveVisible.value = false
    if (detail.value && detail.value.id === approveTarget.value.id) {
      detailVisible.value = false
    }
    loadData()
  } finally {
    approving.value = false
  }
}

onMounted(() => {
  if (route.query.tab) {
    activeTab.value = route.query.tab
  }
  loadData()
})
</script>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
}
.empty-tip {
  text-align: center;
  color: #909399;
  padding: 24px 0;
}
.template-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}
.template-card {
  cursor: pointer;
  transition: all 0.2s;
}
.template-card:hover {
  border-color: #409eff;
}
.template-card :deep(.el-card__body) {
  padding: 14px;
}
.tpl-name {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 6px;
}
.tpl-desc {
  font-size: 12px;
  color: #909399;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.selected-tpl {
  display: flex;
  align-items: center;
  gap: 12px;
}
.wf-detail .detail-title {
  font-size: 20px;
  font-weight: 600;
  margin-bottom: 12px;
  color: #303133;
}
.detail-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  color: #909399;
  font-size: 13px;
  align-items: center;
}
.form-data .form-row {
  display: flex;
  padding: 6px 0;
  border-bottom: 1px dashed #ebeef5;
}
.form-data .form-row:last-child {
  border-bottom: none;
}
.form-label {
  width: 120px;
  color: #909399;
  flex-shrink: 0;
}
.form-value {
  color: #303133;
  flex: 1;
  word-break: break-all;
}
.node-title {
  font-weight: 600;
  color: #303133;
  margin-bottom: 4px;
}
.node-info {
  font-size: 13px;
  color: #606266;
  line-height: 1.6;
}
.detail-actions {
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid #ebeef5;
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}
.upload-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}
.attachment-section {
  padding: 4px 0;
}
.attachment-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.attachment-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  background: #fafafa;
}
.att-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #409eff;
  flex-shrink: 0;
}
.att-info {
  flex: 1;
  min-width: 0;
}
.att-name {
  font-size: 14px;
  word-break: break-all;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
}
.att-meta {
  font-size: 12px;
  color: #909399;
  margin-top: 2px;
}
.att-actions {
  flex-shrink: 0;
}
.attachment-add {
  margin-top: 8px;
}
.invoice-ocr-panel {
  margin-top: 10px;
  padding: 10px;
  background: #f0f9ff;
  border: 1px dashed #bae6fd;
  border-radius: 6px;
}
.ocr-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 10px;
}
.ocr-result {
  margin-top: 8px;
}
.verify-result {
  margin-top: 8px;
}
.duplicate-result {
  margin-top: 8px;
}
.voucher-section {
  padding: 4px 0;
}
.voucher-empty {
  text-align: center;
  padding: 20px;
}
.voucher-loading {
  text-align: center;
  color: #909399;
  padding: 12px;
}
.voucher-existing {
  border: 1px solid #ebeef5;
  border-radius: 6px;
  padding: 12px;
}
.voucher-items {
  margin-top: 12px;
}
.voucher-sub-title {
  font-weight: 600;
  margin-bottom: 8px;
  color: #303133;
}
.muted {
  color: #c0c4cc;
}
.approve-detail {
  max-height: 360px;
  overflow-y: auto;
  margin-bottom: 12px;
}
.approve-section {
  margin-bottom: 12px;
}
.approve-section-title {
  font-weight: 600;
  font-size: 14px;
  color: #303133;
  margin-bottom: 6px;
}
.approve-info-row {
  font-size: 13px;
  padding: 3px 0;
  color: #606266;
}
.approve-info-label {
  color: #909399;
}
.approve-form-data {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.approve-form-row {
  font-size: 13px;
  padding: 3px 0;
  border-bottom: 1px dashed #f0f0f0;
}
.approve-form-label {
  color: #909399;
}
.approve-form-value {
  color: #303133;
}
.approve-empty {
  font-size: 13px;
  color: #909399;
}
.approve-attachment-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.approve-attachment-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  padding: 4px 0;
}
.att-icon-mini {
  color: #409eff;
}
.approve-attachment-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.approve-attachment-size {
  color: #909399;
  font-size: 12px;
}
</style>