<template>
  <div class="page-container">
    <div class="section-title">人事账号管理</div>

    <el-tabs v-model="activeTab" @tab-change="onTabChange">
      <!-- ============ 标签页1：名单管理 ============ -->
      <el-tab-pane label="名单管理" name="roster">
        <el-card>
          <div class="toolbar">
            <el-input
              v-model="rosterSearch.keyword"
              placeholder="按姓名搜索"
              style="width: 200px"
              clearable
              @keyup.enter="loadRoster"
              @clear="loadRoster"
            >
              <template #prefix><el-icon><Search /></el-icon></template>
            </el-input>
            <el-select
              v-model="rosterSearch.registered"
              placeholder="注册状态"
              style="width: 140px"
              clearable
              @change="loadRoster"
            >
              <el-option label="全部" :value="null" />
              <el-option label="已注册" :value="true" />
              <el-option label="未注册" :value="false" />
            </el-select>
            <template v-if="auth.isSuperAdmin">
              <el-select
                v-model="rosterSearch.unit_id"
                placeholder="选择单位"
                style="width: 200px"
                clearable
                @change="loadRoster"
              >
                <el-option v-for="u in units" :key="u.id" :label="u.name" :value="u.id" />
              </el-select>
            </template>
            <el-button type="primary" @click="loadRoster">
              <el-icon><Search /></el-icon>查询
            </el-button>
            <el-button @click="loadRoster">
              <el-icon><Refresh /></el-icon>刷新
            </el-button>
            <el-button type="success" @click="openAddRoster">
              <el-icon><Plus /></el-icon>手动添加名单
            </el-button>
          </div>

          <el-table :data="rosterList" v-loading="rosterLoading" border stripe style="margin-top: 16px">
            <el-table-column type="index" label="序号" width="60" align="center" />
            <el-table-column prop="name" label="姓名" width="120" />
            <el-table-column label="身份证号" min-width="200">
              <template #default="{ row }">{{ maskIdCard(row.id_card) }}</template>
            </el-table-column>
            <el-table-column label="单位" min-width="160">
              <template #default="{ row }">{{ row.unit_name || unitName(row.unit_id) }}</template>
            </el-table-column>
            <el-table-column label="注册状态" width="110" align="center">
              <template #default="{ row }">
                <el-tag :type="row.is_registered ? 'success' : 'info'" size="small">
                  {{ row.is_registered ? '已注册' : '未注册' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="用户名" width="160">
              <template #default="{ row }">{{ row.username || '—' }}</template>
            </el-table-column>
            <el-table-column label="操作" width="140" fixed="right">
              <template #default="{ row }">
                <el-button
                  v-if="!row.is_registered"
                  size="small"
                  type="primary"
                  @click="openCreateFromRoster(row)"
                >创建账号</el-button>
                <span v-else class="muted">—</span>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="!rosterLoading && rosterList.length === 0" description="暂无名单" />
        </el-card>
      </el-tab-pane>

      <!-- ============ 标签页2：批量创建 ============ -->
      <el-tab-pane label="批量创建" name="batch">
        <el-card>
          <el-alert
            type="info"
            :closable="false"
            show-icon
            style="margin-bottom: 16px"
            title="选择单位后，勾选未注册的员工一次性创建账号。默认初始密码为身份证后6位。"
          />
          <div class="toolbar">
            <span class="label">选择单位：</span>
            <el-select
              v-if="auth.isSuperAdmin"
              v-model="batchUnitId"
              placeholder="请选择单位"
              style="width: 240px"
              @change="loadBatchRoster"
            >
              <el-option v-for="u in units" :key="u.id" :label="u.name" :value="u.id" />
            </el-select>
            <span v-else class="readonly-unit">{{ unitName(batchUnitId) || '本单位' }}</span>
            <el-button @click="loadBatchRoster" style="margin-left: 12px">
              <el-icon><Refresh /></el-icon>刷新
            </el-button>
            <el-button :disabled="!batchUnitId" @click="invertSelection">反选</el-button>
            <el-button type="success" @click="openCreateBlank">
              <el-icon><Plus /></el-icon>单个创建
            </el-button>
            <span class="hint">已选 {{ selectedRosterIds.length }} 项</span>
          </div>

          <el-table
            ref="batchTableRef"
            :data="batchList"
            v-loading="batchLoading"
            border
            stripe
            style="margin-top: 16px"
            @selection-change="onBatchSelectionChange"
          >
            <el-table-column type="selection" width="50" align="center" />
            <el-table-column type="index" label="序号" width="60" align="center" />
            <el-table-column prop="name" label="姓名" width="120" />
            <el-table-column label="身份证号" min-width="200">
              <template #default="{ row }">{{ maskIdCard(row.id_card) }}</template>
            </el-table-column>
            <el-table-column label="单位" min-width="160">
              <template #default="{ row }">{{ row.unit_name || unitName(row.unit_id) }}</template>
            </el-table-column>
          </el-table>
          <el-empty v-if="!batchLoading && batchList.length === 0" description="该单位暂无未注册名单" />

          <div class="batch-footer">
            <div class="pwd-mode">
              <span class="label">密码模式：</span>
              <el-radio-group v-model="passwordMode">
                <el-radio value="idcard">身份证后6位</el-radio>
                <el-radio value="uniform">统一密码</el-radio>
              </el-radio-group>
              <el-input
                v-if="passwordMode === 'uniform'"
                v-model="uniformPassword"
                type="password"
                placeholder="统一初始密码（至少6位）"
                show-password
                style="width: 240px; margin-left: 12px"
              />
            </div>
            <el-button
              type="primary"
              :disabled="selectedRosterIds.length === 0 || !batchUnitId"
              :loading="batchCreating"
              @click="onBatchCreate"
            >
              <el-icon><Check /></el-icon>批量创建（{{ selectedRosterIds.length }}）
            </el-button>
          </div>
        </el-card>
      </el-tab-pane>

      <!-- ============ 标签页3：简历导入 ============ -->
      <el-tab-pane label="简历导入" name="resume">
        <el-card>
          <el-alert
            type="info" :closable="false" show-icon style="margin-bottom: 16px"
            title="上传员工简历文件（.docx 或 .xlsx），系统智能识别简历中的姓名、身份证、学历、家庭成员等信息，自动创建人员档案和账号。"
          />
          <div class="toolbar">
            <span class="label">选择单位：</span>
            <el-select
              v-if="auth.isSuperAdmin"
              v-model="resumeUnitId"
              placeholder="请选择单位"
              style="width: 240px"
            >
              <el-option v-for="u in units" :key="u.id" :label="u.name" :value="u.id" />
            </el-select>
            <span v-else class="readonly-unit">{{ unitName(resumeUnitId) || '本单位' }}</span>
            <el-input
              v-model="resumeDepartment"
              placeholder="统一部门（选填）"
              style="width: 180px; margin-left: 12px"
            />
            <el-input
              v-model="resumePosition"
              placeholder="统一岗位（选填）"
              style="width: 180px"
            />
            <el-radio-group v-model="resumePwdMode" style="margin-left: 12px">
              <el-radio value="idcard">身份证后6位</el-radio>
              <el-radio value="uniform">统一密码</el-radio>
            </el-radio-group>
            <el-input
              v-if="resumePwdMode === 'uniform'"
              v-model="resumeUniformPwd"
              type="password"
              placeholder="统一密码"
              show-password
              style="width: 180px"
            />
          </div>

          <el-upload
            ref="resumeBatchUploadRef"
            :auto-upload="false"
            accept=".docx,.xlsx"
            multiple
            :on-change="onResumeBatchChange"
            :on-remove="onResumeBatchRemove"
            :file-list="resumeBatchFileList"
            drag
            style="margin-top: 16px"
          >
            <el-icon class="el-icon--upload"><upload-filled /></el-icon>
            <div class="el-upload__text">将简历文件拖到此处，或<em>点击选择</em></div>
            <template #tip>
              <div class="el-upload__tip">支持 .docx 和 .xlsx 格式，可同时上传多个文件</div>
            </template>
          </el-upload>

          <div class="batch-footer">
            <span class="hint">已选 {{ resumeBatchFiles.length }} 个文件</span>
            <div>
              <el-button
                type="warning"
                :disabled="resumeBatchFiles.length === 0 || !resumeUnitId"
                :loading="resumePreviewing"
                @click="onResumeBatchPreview"
              >预览识别结果</el-button>
              <el-button
                type="primary"
                :disabled="resumeBatchFiles.length === 0 || !resumeUnitId"
                :loading="resumeBatchCreating"
                @click="onResumeBatchCreate"
              >一键创建账号</el-button>
            </div>
          </div>
        </el-card>
      </el-tab-pane>

      <!-- ============ 标签页4：账号列表 ============ -->
      <el-tab-pane label="账号列表" name="accounts">
        <el-card>
          <div class="toolbar">
            <el-input
              v-model="accountsSearch.keyword"
              placeholder="搜索用户名/姓名"
              style="width: 220px"
              clearable
              @keyup.enter="loadAccounts"
              @clear="loadAccounts"
            >
              <template #prefix><el-icon><Search /></el-icon></template>
            </el-input>
            <template v-if="auth.isSuperAdmin">
              <el-select
                v-model="accountsSearch.unit_id"
                placeholder="筛选单位"
                style="width: 200px; margin-left: 12px"
                clearable
                @change="onAccountsFilterChange"
              >
                <el-option v-for="u in units" :key="u.id" :label="u.name" :value="u.id" />
              </el-select>
            </template>
            <el-select
              v-model="accountsSearch.is_active"
              placeholder="状态"
              style="width: 130px; margin-left: 12px"
              clearable
              @change="onAccountsFilterChange"
            >
              <el-option label="全部" :value="null" />
              <el-option label="启用" :value="true" />
              <el-option label="停用" :value="false" />
            </el-select>
            <el-button type="primary" @click="loadAccounts" style="margin-left: 12px">
              <el-icon><Search /></el-icon>查询
            </el-button>
            <el-button @click="loadAccounts">
              <el-icon><Refresh /></el-icon>刷新
            </el-button>
          </div>

          <el-table :data="accountsList" v-loading="accountsLoading" border stripe style="margin-top: 16px">
            <template #empty><el-empty description="暂无账号" :image-size="80" /></template>
            <el-table-column type="index" label="序号" width="60" align="center" />
            <el-table-column prop="username" label="用户名" width="150" />
            <el-table-column prop="name" label="姓名" width="100" />
            <el-table-column prop="department" label="部门" width="120">
              <template #default="{ row }">{{ row.department || '—' }}</template>
            </el-table-column>
            <el-table-column prop="position" label="岗位" width="120">
              <template #default="{ row }">{{ row.position || '—' }}</template>
            </el-table-column>
            <el-table-column prop="phone" label="手机" width="140">
              <template #default="{ row }">{{ row.phone || '—' }}</template>
            </el-table-column>
            <el-table-column label="单位" min-width="140">
              <template #default="{ row }">{{ row.unit_name || unitName(row.unit_id) }}</template>
            </el-table-column>
            <el-table-column label="状态" width="90" align="center">
              <template #default="{ row }">
                <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">
                  {{ row.is_active ? '启用' : '停用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="首次登录" width="100" align="center">
              <template #default="{ row }">
                <el-tag :type="row.first_login ? 'warning' : 'info'" size="small">
                  {{ row.first_login ? '未改密' : '已改密' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="220" fixed="right">
              <template #default="{ row }">
                <el-button size="small" @click="openResetPwd(row)">重置密码</el-button>
                <el-button
                  size="small"
                  :type="row.is_active ? 'warning' : 'success'"
                  @click="onToggleAccount(row)"
                >{{ row.is_active ? '停用' : '启用' }}</el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-pagination
            v-model:current-page="accountsPage"
            :page-size="accountsPageSize"
            :total="accountsTotal"
            layout="total, prev, pager, next, jumper"
            style="margin-top: 16px; justify-content: flex-end"
            @current-change="loadAccounts"
          />
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <!-- ============ 手动添加名单对话框 ============ -->
    <el-dialog v-model="addRosterVisible" title="手动添加名单" width="460px">
      <el-form :model="addRosterForm" :rules="addRosterRules" ref="addRosterFormRef" label-width="90px">
        <el-form-item label="姓名" prop="name">
          <el-input v-model="addRosterForm.name" placeholder="请输入姓名" />
        </el-form-item>
        <el-form-item label="身份证号" prop="id_card">
          <el-input v-model="addRosterForm.id_card" placeholder="请输入身份证号" maxlength="18" />
        </el-form-item>
        <el-form-item label="单位" prop="unit_id">
          <el-select v-model="addRosterForm.unit_id" placeholder="请选择单位" style="width: 100%" :disabled="!auth.isSuperAdmin">
            <el-option v-for="u in units" :key="u.id" :label="u.name" :value="u.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addRosterVisible = false">取消</el-button>
        <el-button type="primary" :loading="addRosterSaving" @click="submitAddRoster">保存</el-button>
      </template>
    </el-dialog>

    <!-- ============ 单个创建账号对话框（复用） ============ -->
    <el-dialog v-model="createVisible" title="创建账号" width="520px">
      <el-form :model="createForm" :rules="createRules" ref="createFormRef" label-width="90px">
        <el-form-item label="姓名" prop="name">
          <el-input v-model="createForm.name" placeholder="请输入姓名" />
        </el-form-item>
        <el-form-item label="身份证号" prop="id_card">
          <el-input v-model="createForm.id_card" placeholder="请输入身份证号" maxlength="18" />
        </el-form-item>
        <el-form-item label="手机号" prop="phone">
          <el-input v-model="createForm.phone" placeholder="选填" />
        </el-form-item>
        <el-form-item label="单位" prop="unit_id">
          <el-select v-model="createForm.unit_id" placeholder="请选择单位" style="width: 100%" :disabled="!auth.isSuperAdmin">
            <el-option v-for="u in units" :key="u.id" :label="u.name" :value="u.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="部门" prop="department">
          <el-input v-model="createForm.department" placeholder="选填" />
        </el-form-item>
        <el-form-item label="岗位" prop="position">
          <el-input v-model="createForm.position" placeholder="选填" />
        </el-form-item>
        <el-form-item label="初始密码" prop="password">
          <el-input v-model="createForm.password" type="password" placeholder="选填，留空则默认身份证后6位" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="createSaving" @click="submitCreate">创建</el-button>
      </template>
    </el-dialog>

    <!-- ============ 单个创建结果对话框 ============ -->
    <el-dialog v-model="createResultVisible" title="创建成功" width="420px">
      <el-result icon="success" title="账号创建成功" sub-title="请妥善保管以下登录信息">
        <template #extra>
          <div class="result-info">
            <div class="result-row"><span class="result-label">用户名：</span>{{ createResult.username }}</div>
            <div class="result-row"><span class="result-label">初始密码：</span>{{ createResult.password }}</div>
          </div>
        </template>
      </el-result>
      <template #footer>
        <el-button type="primary" @click="createResultVisible = false">知道了</el-button>
      </template>
    </el-dialog>

    <!-- ============ 批量创建结果对话框 ============ -->
    <el-dialog v-model="batchResultVisible" title="批量创建结果" width="640px">
      <el-row :gutter="16">
        <el-col :span="12">
          <div class="result-stat success">成功 {{ batchResult.success.length }} 个</div>
        </el-col>
        <el-col :span="12">
          <div class="result-stat fail">失败 {{ batchResult.failed.length }} 个</div>
        </el-col>
      </el-row>
      <div v-if="batchResult.success.length" style="margin-top: 12px">
        <div class="result-sub-title">成功列表</div>
        <el-table :data="batchResult.success" border stripe size="small" max-height="220">
          <el-table-column type="index" label="#" width="50" align="center" />
          <el-table-column prop="name" label="姓名" width="100" />
          <el-table-column prop="username" label="用户名" min-width="120" />
          <el-table-column prop="password" label="初始密码" min-width="120" />
        </el-table>
      </div>
      <div v-if="batchResult.failed.length" style="margin-top: 12px">
        <div class="result-sub-title">失败列表</div>
        <el-table :data="batchResult.failed" border stripe size="small" max-height="220">
          <el-table-column type="index" label="#" width="50" align="center" />
          <el-table-column prop="name" label="姓名" width="100" />
          <el-table-column label="身份证号" min-width="180">
            <template #default="{ row }">{{ maskIdCard(row.id_card) }}</template>
          </el-table-column>
          <el-table-column prop="reason" label="失败原因" min-width="160">
            <template #default="{ row }">{{ row.reason || row.error || '—' }}</template>
          </el-table-column>
        </el-table>
      </div>
      <template #footer>
        <el-button type="primary" @click="onBatchResultClose">关闭</el-button>
      </template>
    </el-dialog>

    <!-- ============ 简历识别预览对话框 ============ -->
    <el-dialog v-model="resumePreviewVisible" title="简历智能识别结果预览" width="900px" top="5vh">
      <el-alert
        type="info" :closable="false" style="margin-bottom: 16px"
        :title="`共识别 ${resumePreviewResults.length} 份简历，请确认识别结果后再点击下方「一键创建账号」`"
      />
      <div class="resume-preview-list">
        <el-card
          v-for="(item, idx) in resumePreviewResults"
          :key="idx"
          class="resume-preview-card"
          shadow="hover"
        >
          <template #header>
            <div class="resume-preview-header">
              <span class="resume-filename">{{ item.filename }}</span>
              <el-tag
                :type="item.status === 'success' ? 'success' : (item.status === 'warning' ? 'warning' : 'danger')"
                size="small"
              >
                {{ item.status === 'success' ? '识别成功' : (item.status === 'warning' ? '部分识别' : '识别失败') }}
              </el-tag>
            </div>
          </template>
          <div v-if="item.status === 'failed'" class="resume-error">
            失败原因：{{ item.error || '解析失败' }}
          </div>
          <template v-else>
            <div class="resume-fields-grid">
              <div v-for="(val, key) in item.flat_fields" :key="key" class="resume-field-item">
                <span class="resume-field-label">{{ resumeFieldLabel(key) }}：</span>
                <span class="resume-field-value">{{ val || '—' }}</span>
              </div>
            </div>
            <div v-for="(rows, tableKey) in item.sub_tables" :key="tableKey" class="resume-sub-section">
              <div class="resume-sub-title">{{ resumeSubTableLabel(tableKey) }}（{{ rows.length }} 条）</div>
              <el-table :data="rows" border size="small" max-height="160">
                <el-table-column
                  v-for="col in Object.keys(rows[0] || {})"
                  :key="col"
                  :prop="col"
                  :label="resumeFieldLabel(col)"
                  min-width="100"
                />
              </el-table>
            </div>
          </template>
        </el-card>
      </div>
      <template #footer>
        <el-button @click="resumePreviewVisible = false">关闭</el-button>
        <el-button type="primary" :loading="resumeBatchCreating" @click="onResumeBatchCreate">
          确认无误，一键创建账号
        </el-button>
      </template>
    </el-dialog>

    <!-- ============ 重置密码对话框 ============ -->
    <el-dialog v-model="resetVisible" title="重置密码" width="420px">
      <el-form label-width="90px">
        <el-form-item label="账号">
          <el-input :model-value="resetTarget?.username" disabled />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input v-model="resetNewPwd" type="password" placeholder="留空则使用身份证后6位" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="resetVisible = false">取消</el-button>
        <el-button type="primary" :loading="resetSaving" @click="submitReset">确认重置</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh, Search, Check, UploadFilled } from '@element-plus/icons-vue'
import api, { hrAccountApi, resumeSmartApi } from '@/api'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

// ===== 公共数据 =====
const units = ref([])
const loadUnits = async () => {
  units.value = await api.get('/units')
}
const unitName = (id) => units.value.find((u) => u.id === id)?.name || ''
const defaultUnitId = () => (auth.isSuperAdmin ? null : auth.user?.unit_id || null)

// 身份证脱敏：前6位 + ******** + 后4位
const maskIdCard = (id) => {
  if (!id) return ''
  const s = String(id)
  if (s.length <= 10) return s
  return s.slice(0, 6) + '********' + s.slice(-4)
}

// 响应归一化：兼容数组与 {items, total}
const normalize = (res) => {
  if (Array.isArray(res)) return { items: res, total: res.length }
  const items = res.items || res.list || res.data || []
  const total = res.total != null ? res.total : items.length
  return { items, total }
}

// ============ Tab 切换 ============
const activeTab = ref('roster')
const loadedTabs = ref({ roster: false, batch: false, resume: false, accounts: false })
const onTabChange = (name) => {
  if (name === 'roster' && !loadedTabs.value.roster) loadRoster()
  else if (name === 'batch' && !loadedTabs.value.batch) loadBatchRoster()
  else if (name === 'accounts' && !loadedTabs.value.accounts) loadAccounts()
}

// ============ 标签页1：名单管理 ============
const rosterList = ref([])
const rosterLoading = ref(false)
const rosterSearch = reactive({
  keyword: '',
  registered: null,
  unit_id: defaultUnitId(),
})

const loadRoster = async () => {
  rosterLoading.value = true
  loadedTabs.value.roster = true
  try {
    const params = {}
    if (rosterSearch.keyword) params.keyword = rosterSearch.keyword
    if (rosterSearch.registered !== null) params.registered = rosterSearch.registered
    if (rosterSearch.unit_id) params.unit_id = rosterSearch.unit_id
    const res = await hrAccountApi.roster(params)
    rosterList.value = normalize(res).items
  } finally {
    rosterLoading.value = false
  }
}

// 手动添加名单
const addRosterVisible = ref(false)
const addRosterSaving = ref(false)
const addRosterFormRef = ref()
const addRosterForm = reactive({ name: '', id_card: '', unit_id: defaultUnitId() })
const addRosterRules = {
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  id_card: [
    { required: true, message: '请输入身份证号', trigger: 'blur' },
    { min: 15, message: '身份证号长度不正确', trigger: 'blur' },
  ],
  unit_id: [{ required: true, message: '请选择单位', trigger: 'change' }],
}

const openAddRoster = () => {
  addRosterForm.name = ''
  addRosterForm.id_card = ''
  addRosterForm.unit_id = defaultUnitId()
  addRosterVisible.value = true
}

const submitAddRoster = async () => {
  await addRosterFormRef.value.validate()
  addRosterSaving.value = true
  try {
    await hrAccountApi.importRoster([
      {
        name: addRosterForm.name.trim(),
        id_card: addRosterForm.id_card.trim(),
        unit_id: addRosterForm.unit_id,
      },
    ])
    ElMessage.success('名单已添加')
    addRosterVisible.value = false
    loadRoster()
  } finally {
    addRosterSaving.value = false
  }
}

// ============ 单个创建账号对话框（复用） ============
const createVisible = ref(false)
const createSaving = ref(false)
const createFormRef = ref()
const createForm = reactive({
  name: '',
  id_card: '',
  phone: '',
  unit_id: null,
  department: '',
  position: '',
  password: '',
})
const createRules = {
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  id_card: [
    { required: true, message: '请输入身份证号', trigger: 'blur' },
    { min: 15, message: '身份证号长度不正确', trigger: 'blur' },
  ],
  unit_id: [{ required: true, message: '请选择单位', trigger: 'change' }],
}

const openCreateFromRoster = (row) => {
  createForm.name = row.name || ''
  createForm.id_card = row.id_card || ''
  createForm.phone = ''
  createForm.unit_id = row.unit_id || defaultUnitId()
  createForm.department = ''
  createForm.position = ''
  createForm.password = ''
  createVisible.value = true
}

const openCreateBlank = () => {
  createForm.name = ''
  createForm.id_card = ''
  createForm.phone = ''
  createForm.unit_id = defaultUnitId()
  createForm.department = ''
  createForm.position = ''
  createForm.password = ''
  createVisible.value = true
}

const createResultVisible = ref(false)
const createResult = reactive({ username: '', password: '' })

const submitCreate = async () => {
  await createFormRef.value.validate()
  createSaving.value = true
  try {
    const payload = {
      name: createForm.name.trim(),
      id_card: createForm.id_card.trim(),
      unit_id: createForm.unit_id,
    }
    if (createForm.phone) payload.phone = createForm.phone.trim()
    if (createForm.department) payload.department = createForm.department.trim()
    if (createForm.position) payload.position = createForm.position.trim()
    if (createForm.password) payload.password = createForm.password
    const res = await hrAccountApi.createAccount(payload)
    createResult.username = res.username || ''
    createResult.password = res.password || ''
    createVisible.value = false
    createResultVisible.value = true
    // 刷新相关列表
    if (activeTab.value === 'roster') loadRoster()
    if (activeTab.value === 'batch') loadBatchRoster()
    if (activeTab.value === 'accounts') loadAccounts()
  } finally {
    createSaving.value = false
  }
}

// ============ 标签页2：批量创建 ============
const batchUnitId = ref(defaultUnitId())
const batchList = ref([])
const batchLoading = ref(false)
const batchTableRef = ref()
const selectedRosterIds = ref([])
const passwordMode = ref('idcard')
const uniformPassword = ref('')
const batchCreating = ref(false)

const loadBatchRoster = async () => {
  if (!batchUnitId.value) {
    batchList.value = []
    return
  }
  batchLoading.value = true
  loadedTabs.value.batch = true
  try {
    const res = await hrAccountApi.roster({ unit_id: batchUnitId.value, registered: false })
    batchList.value = normalize(res).items
  } finally {
    batchLoading.value = false
  }
}

const onBatchSelectionChange = (rows) => {
  selectedRosterIds.value = rows.map((r) => r.id)
}

const invertSelection = () => {
  if (!batchTableRef.value) return
  batchList.value.forEach((row) => {
    batchTableRef.value.toggleRowSelection(row)
  })
}

const batchResultVisible = ref(false)
const batchResult = reactive({ success: [], failed: [] })

const onBatchCreate = async () => {
  if (selectedRosterIds.value.length === 0) {
    ElMessage.warning('请至少选择一名员工')
    return
  }
  if (passwordMode.value === 'uniform') {
    if (!uniformPassword.value || uniformPassword.value.length < 6) {
      ElMessage.warning('统一密码至少6位')
      return
    }
  }
  try {
    await ElMessageBox.confirm(
      `确认为选中的 ${selectedRosterIds.value.length} 名员工创建账号？`,
      '批量创建确认',
      { type: 'warning' }
    )
  } catch (e) {
    return
  }
  batchCreating.value = true
  try {
    const payload = {
      unit_id: batchUnitId.value,
      roster_ids: selectedRosterIds.value,
      password_mode: passwordMode.value,
    }
    if (passwordMode.value === 'uniform') payload.uniform_password = uniformPassword.value
    const res = await hrAccountApi.batchCreate(payload)
    const success = res.success || res.succeeded || res.successes || []
    const failed = res.failed || res.failures || res.errors || []
    batchResult.success = success
    batchResult.failed = failed
    batchResultVisible.value = true
  } finally {
    batchCreating.value = false
  }
}

const onBatchResultClose = () => {
  batchResultVisible.value = false
  // 创建后刷新批量名单（已创建的应不再出现）
  if (batchResult.success.length > 0) {
    selectedRosterIds.value = []
    loadBatchRoster()
  }
}

// ============ 标签页3：简历导入（智能识别） ============
const resumeUnitId = ref(defaultUnitId())
const resumeDepartment = ref('')
const resumePosition = ref('')
const resumePwdMode = ref('idcard')
const resumeUniformPwd = ref('')
const resumeBatchFiles = ref([])
const resumeBatchFileList = ref([])
const resumeBatchUploadRef = ref()
const resumePreviewing = ref(false)
const resumeBatchCreating = ref(false)
const resumePreviewVisible = ref(false)
const resumePreviewResults = ref([])

// 字段中文标签
const RESUME_FIELD_LABELS = {
  name: '姓名', gender: '性别', birth_date: '出生日期', id_card: '身份证号',
  ethnicity: '民族', native_place: '籍贯', birth_place: '出生地',
  political_status: '政治面貌', party_join_date: '入党日期',
  phone: '手机号', office_phone: '办公电话', emergency_contact: '紧急联系人',
  education_level: '学历', degree: '学位', school: '毕业院校', major: '专业',
  graduation_date: '毕业日期', marital_status: '婚姻状况', spouse_name: '配偶姓名',
  home_address: '家庭住址', department: '部门', position: '岗位', rank: '职级',
  work_start_date: '参加工作日期', join_unit_date: '入职日期',
  relationship: '关系', work_unit: '工作单位', witness: '证明人',
  start_date: '开始日期', end_date: '结束日期',
}
const resumeFieldLabel = (key) => RESUME_FIELD_LABELS[key] || key
const resumeSubTableLabel = (key) => ({
  family_members: '家庭成员',
  education_records: '教育经历',
  work_records: '工作经历',
})[key] || key

const onResumeBatchChange = (file, fileList) => {
  resumeBatchFiles.value = fileList.map((f) => f.raw)
  resumeBatchFileList.value = fileList
}

const onResumeBatchRemove = (file, fileList) => {
  resumeBatchFiles.value = fileList.map((f) => f.raw)
  resumeBatchFileList.value = fileList
}

const onResumeBatchPreview = async () => {
  if (resumeBatchFiles.value.length === 0) {
    ElMessage.warning('请先选择简历文件')
    return
  }
  if (!resumeUnitId.value) {
    ElMessage.warning('请先选择单位')
    return
  }
  resumePreviewing.value = true
  try {
    const results = await resumeSmartApi.batchParse(resumeBatchFiles.value)
    resumePreviewResults.value = results || []
    resumePreviewVisible.value = true
  } catch (e) {
    ElMessage.error('预览失败：' + (e.response?.data?.detail || e.message))
  } finally {
    resumePreviewing.value = false
  }
}

const onResumeBatchCreate = async () => {
  if (resumeBatchFiles.value.length === 0) {
    ElMessage.warning('请先选择简历文件')
    return
  }
  if (!resumeUnitId.value) {
    ElMessage.warning('请先选择单位')
    return
  }
  if (resumePwdMode.value === 'uniform') {
    if (!resumeUniformPwd.value || resumeUniformPwd.value.length < 6) {
      ElMessage.warning('统一密码至少6位')
      return
    }
  }
  try {
    await ElMessageBox.confirm(
      `确认为选中的 ${resumeBatchFiles.value.length} 份简历智能识别并创建账号？`,
      '简历导入确认',
      { type: 'warning' }
    )
  } catch (e) {
    return
  }
  resumeBatchCreating.value = true
  try {
    const params = {
      unit_id: resumeUnitId.value,
      password_mode: resumePwdMode.value,
    }
    if (resumePwdMode.value === 'uniform') params.uniform_password = resumeUniformPwd.value
    if (resumeDepartment.value) params.department = resumeDepartment.value
    if (resumePosition.value) params.position = resumePosition.value
    const res = await resumeSmartApi.batchCreate(resumeBatchFiles.value, params)
    const success = res.success || res.succeeded || res.successes || []
    const failed = res.failed || res.failures || res.errors || []
    batchResult.success = success
    batchResult.failed = failed
    resumePreviewVisible.value = false
    batchResultVisible.value = true
    // 清空已选文件
    if (success.length > 0 && resumeBatchUploadRef.value) {
      resumeBatchUploadRef.value.clearFiles()
      resumeBatchFiles.value = []
      resumeBatchFileList.value = []
    }
  } catch (e) {
    ElMessage.error('批量创建失败：' + (e.response?.data?.detail || e.message))
  } finally {
    resumeBatchCreating.value = false
  }
}

// ============ 标签页3：账号列表 ============
const accountsList = ref([])
const accountsLoading = ref(false)
const accountsSearch = reactive({
  keyword: '',
  unit_id: defaultUnitId(),
  is_active: null,
})
const accountsPage = ref(1)
const accountsPageSize = ref(20)
const accountsTotal = ref(0)

const loadAccounts = async () => {
  accountsLoading.value = true
  loadedTabs.value.accounts = true
  try {
    const params = {
      page: accountsPage.value,
      page_size: accountsPageSize.value,
    }
    if (accountsSearch.keyword) params.keyword = accountsSearch.keyword
    if (accountsSearch.unit_id) params.unit_id = accountsSearch.unit_id
    if (accountsSearch.is_active !== null) params.is_active = accountsSearch.is_active
    const res = await hrAccountApi.accounts(params)
    const { items, total } = normalize(res)
    accountsList.value = items
    accountsTotal.value = total
  } finally {
    accountsLoading.value = false
  }
}

const onAccountsFilterChange = () => {
  accountsPage.value = 1
  loadAccounts()
}

// 重置密码
const resetVisible = ref(false)
const resetTarget = ref(null)
const resetNewPwd = ref('')
const resetSaving = ref(false)

const openResetPwd = (row) => {
  resetTarget.value = row
  resetNewPwd.value = ''
  resetVisible.value = true
}

const submitReset = async () => {
  if (resetNewPwd.value && resetNewPwd.value.length < 6) {
    ElMessage.warning('密码至少6位')
    return
  }
  resetSaving.value = true
  try {
    await hrAccountApi.resetPassword(resetTarget.value.id, resetNewPwd.value)
    ElMessage.success('密码已重置')
    resetVisible.value = false
  } finally {
    resetSaving.value = false
  }
}

// 启用/停用
const onToggleAccount = async (row) => {
  const action = row.is_active ? '停用' : '启用'
  try {
    await ElMessageBox.confirm(`确定要${action}账号「${row.username}」吗？`, '确认', { type: 'warning' })
    await hrAccountApi.toggleAccount(row.id)
    ElMessage.success(`已${action}`)
    loadAccounts()
  } catch (e) {
    // 取消
  }
}

onMounted(async () => {
  await loadUnits()
  await loadRoster()
})
</script>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.toolbar .label {
  color: #606266;
  font-size: 14px;
}
.readonly-unit {
  font-weight: 600;
  color: #303133;
}
.hint {
  margin-left: 8px;
  color: #909399;
  font-size: 13px;
}
.muted {
  color: #c0c4cc;
}
.batch-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 16px;
  flex-wrap: wrap;
  gap: 12px;
}
.pwd-mode {
  display: flex;
  align-items: center;
}
.pwd-mode .label {
  color: #606266;
  font-size: 14px;
  margin-right: 8px;
}
.result-info {
  text-align: left;
  background: #f5f7fa;
  padding: 12px 16px;
  border-radius: 4px;
}
.result-row {
  font-size: 15px;
  line-height: 2;
}
.result-label {
  color: #909399;
}
.result-stat {
  font-size: 15px;
  font-weight: 600;
  padding: 8px 12px;
  border-radius: 4px;
  text-align: center;
}
.result-stat.success {
  color: #67c23a;
  background: #f0f9eb;
}
.result-stat.fail {
  color: #f56c6c;
  background: #fef0f0;
}
.result-sub-title {
  font-weight: 600;
  margin-bottom: 8px;
  color: #303133;
}
.resume-preview-list {
  max-height: 60vh;
  overflow-y: auto;
}
.resume-preview-card {
  margin-bottom: 16px;
}
.resume-preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.resume-filename {
  font-weight: 600;
  color: #303133;
  font-size: 14px;
}
.resume-error {
  color: #f56c6c;
  font-size: 13px;
}
.resume-fields-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 6px 16px;
  margin-bottom: 12px;
}
.resume-field-item {
  font-size: 13px;
  display: flex;
}
.resume-field-label {
  color: #909399;
  flex-shrink: 0;
  min-width: 90px;
}
.resume-field-value {
  color: #303133;
  word-break: break-all;
}
.resume-sub-section {
  margin-top: 12px;
}
.resume-sub-title {
  font-weight: 600;
  font-size: 13px;
  color: #606266;
  margin-bottom: 6px;
  padding-left: 6px;
  border-left: 3px solid #409eff;
}
</style>
