<template>
  <div class="kb-page">
    <!-- 顶部：统计卡片 -->
    <el-row :gutter="16" class="row-margin">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card doc-count">
          <div class="stat-icon"><el-icon><Collection /></el-icon></div>
          <div class="stat-info">
            <div class="stat-num">{{ stats.total_docs || 0 }}</div>
            <div class="stat-label">文档总数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card indexed-card">
          <div class="stat-icon"><el-icon><Select /></el-icon></div>
          <div class="stat-info">
            <div class="stat-num">{{ stats.indexed_docs || 0 }}<span class="stat-sub">/{{ stats.total_docs || 0 }}</span></div>
            <div class="stat-label">已入库</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card chunk-card">
          <div class="stat-icon"><el-icon><Grid /></el-icon></div>
          <div class="stat-info">
            <div class="stat-num">{{ stats.vector_store_chunks || 0 }}</div>
            <div class="stat-label">向量库分块数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card size-card">
          <div class="stat-icon"><el-icon><Files /></el-icon></div>
          <div class="stat-info">
            <div class="stat-num">{{ stats.total_size_human || '0B' }}</div>
            <div class="stat-label">总大小</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 操作栏：上传 + 入库 + 筛选 -->
    <el-card shadow="never" class="row-margin toolbar-card">
      <el-row :gutter="12" align="middle">
        <el-col :span="16">
          <el-space wrap>
            <el-upload
              class="upload-btn"
              :action="uploadUrl"
              :headers="uploadHeaders"
              :show-file-list="false"
              :before-upload="beforeUpload"
              :on-success="onUploadSuccess"
              :on-error="onUploadError"
              multiple
              accept=".txt,.md,.log,.docx,.xlsx,.xls,.pdf"
            >
              <el-button type="primary" :icon="UploadFilled" :loading="uploading">
                上传文档
              </el-button>
            </el-upload>
            <el-tooltip content="扫描新增/修改的文档，增量入库" placement="top">
              <el-button type="success" :icon="Refresh" :loading="building" @click="buildKB(false)">
                增量入库
              </el-button>
            </el-tooltip>
            <el-tooltip content="强制全部重新分块入库（耗时较长）" placement="top">
              <el-button type="warning" :icon="Warning" :loading="building" @click="buildKB(true)">
                重建知识库
              </el-button>
            </el-tooltip>
            <el-button :icon="Search" @click="loadStats">刷新统计</el-button>
          </el-space>
        </el-col>
        <el-col :span="8">
          <el-space style="float: right;">
            <el-select
              v-model="filterCategory"
              placeholder="分类筛选"
              clearable
              style="width: 140px"
              @change="loadDocs"
            >
              <el-option v-for="(c, k) in categoryOptions" :key="k" :label="`${k} (${c})`" :value="k" />
            </el-select>
            <el-input
              v-model="keyword"
              placeholder="文件名关键词"
              style="width: 200px"
              clearable
              @keyup.enter="loadDocs"
              :prefix-icon="Search"
            />
          </el-space>
        </el-col>
      </el-row>
      <div class="upload-tip">
        支持格式：<el-tag size="small" type="info">TXT / MD</el-tag>
        <el-tag size="small" type="info">Word DOCX</el-tag>
        <el-tag size="small" type="info">Excel XLSX</el-tag>
        <el-tag size="small" type="info">PDF</el-tag>
        ，单文件 ≤ 10MB。分类规则：文件名包含"规章制度/审批规范/操作手册/FAQ案例/政策公文/涉密保密"等关键词自动识别。
      </div>
    </el-card>

    <!-- 文档列表 -->
    <el-card shadow="never" class="row-margin list-card">
      <template #header>
        <div class="card-header">
          <span style="font-weight:600">知识库文档列表</span>
          <span class="doc-total">共 {{ docs.length }} 份文档</span>
        </div>
      </template>

      <el-table
        v-loading="loadingDocs"
        :data="docs"
        stripe
        size="default"
        empty-text="暂无知识库文档，点击上方上传即可添加"
        @selection-change="onSelectionChange"
      >
        <el-table-column type="selection" width="48" />
        <el-table-column type="index" label="#" width="50" align="center" />
        <el-table-column label="文档名称" min-width="240">
          <template #default="{ row }">
            <div class="doc-name">
              <el-icon class="doc-icon" :style="{ color: iconColor(row.filename) }">
                <component :is="iconFor(row.filename)" />
              </el-icon>
              <span class="doc-fn">{{ row.filename }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="category" label="分类" width="110" align="center">
          <template #default="{ row }">
            <el-tag :type="categoryTagType(row.category)" size="small">{{ row.category }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="入库状态" width="110" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.indexed" type="success" size="small" effect="dark">
              已入库 · {{ row.chunks }}块
            </el-tag>
            <el-tag v-else type="info" size="small">未入库</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="size_human" label="大小" width="100" align="center" />
        <el-table-column prop="mtime_human" label="更新时间" width="150" align="center" />
        <el-table-column label="操作" width="220" align="center" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" :icon="Refresh" @click="rebuildOne(row)">
              重新入库
            </el-button>
            <el-popconfirm title="确认删除该文档？（同时会从向量库移除）" @confirm="deleteDoc(row)">
              <template #reference>
                <el-button type="danger" link size="small" :icon="Delete">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  UploadFilled,
  Refresh,
  Warning,
  Search,
  Delete,
  Collection,
  Select,
  Grid,
  Files,
  Document,
  Notebook,
  Picture,
  DataAnalysis,
} from '@element-plus/icons-vue'

import { api, aiApi } from '@/api'

// ============ 响应式状态 ============
const stats = ref({})
const docs = ref([])
const loadingDocs = ref(false)
const uploading = ref(false)
const building = ref(false)
const keyword = ref('')
const filterCategory = ref('')
const selectedRows = ref([])

// 计算 el-upload 需要的 URL 和 Headers（api 实例 baseURL = /api/v1）
function getAuthHeaders() {
  const token = localStorage.getItem('token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}
const uploadUrl = '/api/v1/ai/kb/upload'
const uploadHeaders = computed(() => getAuthHeaders())

const categoryOptions = computed(() => stats.value.categories || {})

function iconFor(fn) {
  const ext = fn.split('.').pop().toLowerCase()
  if (['docx', 'doc'].includes(ext)) return Document
  if (['xlsx', 'xls'].includes(ext)) return DataAnalysis
  if (['pdf'].includes(ext)) return Notebook
  if (['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(ext)) return Picture
  return Files
}
function iconColor(fn) {
  const ext = fn.split('.').pop().toLowerCase()
  return { docx: '#409eff', doc: '#409eff', xlsx: '#67c23a', xls: '#67c23a', pdf: '#f56c6c', txt: '#909399', md: '#909399', log: '#909399' }[ext] || '#909399'
}
function categoryTagType(cat) {
  return ({ '规章制度': 'danger', '审批规范': 'warning', '操作手册': 'primary', 'FAQ案例': 'success', '政策公文': 'info', '涉密管理': 'warning', '其他': 'info' }[cat] || 'info')
}

async function loadStats() {
  try {
    const data = await aiApi.kbStats()
    stats.value = data
  } catch (e) {}
}
async function loadDocs() {
  loadingDocs.value = true
  try {
    const data = await aiApi.listKbDocs({
      category: filterCategory.value || undefined,
      keyword: keyword.value || undefined,
    })
    docs.value = data.items || []
  } finally {
    loadingDocs.value = false
  }
}

function beforeUpload(file) {
  const allowed = ['txt', 'md', 'log', 'docx', 'xlsx', 'xls', 'pdf']
  const ext = file.name.split('.').pop().toLowerCase()
  if (!allowed.includes(ext)) {
    ElMessage.error('仅支持 TXT/MD/DOCX/XLSX/PDF 格式')
    return false
  }
  if (file.size > 10 * 1024 * 1024) {
    ElMessage.error('文件大小不能超过 10MB')
    return false
  }
  uploading.value = true
  return true
}
function onUploadSuccess(res) {
  uploading.value = false
  if (res?.ok) {
    ElMessage.success(res.message || '上传成功')
    loadStats()
    loadDocs()
  } else {
    ElMessage.error(res?.detail || res?.message || '上传失败')
  }
}
function onUploadError(err) {
  uploading.value = false
  ElMessage.error('上传失败：' + (err?.message || '未知错误'))
}

async function buildKB(force = false) {
  let filenames = null
  if (selectedRows.value?.length) {
    const ok = await ElMessageBox.confirm(
      `已选中 ${selectedRows.value.length} 份文档，将只对它们执行【${force ? '强制重建' : '增量入库'}】。是否继续？`,
      '入库确认',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'info' },
    ).catch(() => false)
    if (!ok) return
    filenames = selectedRows.value.map((r) => r.filename)
  } else if (force) {
    const ok = await ElMessageBox.confirm(
      '将强制重新入库全部文档，耗时较久，是否继续？',
      '重建确认',
      { confirmButtonText: '确定重建', cancelButtonText: '取消', type: 'warning' },
    ).catch(() => false)
    if (!ok) return
  }

  building.value = true
  try {
    const data = await aiApi.buildKb({ filenames, force })
    if (data?.ok) {
      ElMessage.success(
        `入库完成：成功 ${data.ok_count}，失败 ${data.fail_count}，跳过 ${data.skip_count}，总分块 ${data.total_chunks}`,
      )
    } else {
      ElMessage.warning('部分文档入库失败，请检查详情')
    }
    loadStats()
    loadDocs()
  } catch (e) {
    ElMessage.error('入库失败：' + (e.response?.data?.detail || e.message))
  } finally {
    building.value = false
  }
}

async function rebuildOne(row) {
  building.value = true
  try {
    const data = await aiApi.buildKb({ filenames: [row.filename], force: true })
    if (data?.ok) ElMessage.success(`重新入库完成：${row.filename} (${data.total_chunks}块)`)
    loadStats()
    loadDocs()
  } catch (e) {
    ElMessage.error('入库失败：' + (e.response?.data?.detail || e.message))
  } finally {
    building.value = false
  }
}

async function deleteDoc(row) {
  try {
    const data = await aiApi.deleteKbDoc(row.filename)
    if (data?.ok) ElMessage.success(data.message || '删除成功')
    loadStats()
    loadDocs()
  } catch (e) {
    ElMessage.error('删除失败：' + (e.response?.data?.detail || e.message))
  }
}

function onSelectionChange(rows) {
  selectedRows.value = rows
}

onMounted(() => {
  loadStats()
  loadDocs()
})
</script>

<style scoped>
.kb-page {
  padding: 0 2px;
}
.row-margin {
  margin-bottom: 20px;
}
.stat-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 6px;
  border: none;
  border-radius: 12px;
  background: linear-gradient(135deg, #f5f8f2 0%, #eef6e4 100%);
  transition: all .25s;
}
.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px -10px rgba(103,121,88,0.25);
}
.stat-icon {
  width: 52px; height: 52px;
  border-radius: 14px;
  display: flex; align-items: center; justify-content: center;
  font-size: 26px; color: #fff;
  background: linear-gradient(135deg,#5b7c3e,#8aa85d);
}
.doc-count .stat-icon { background: linear-gradient(135deg,#4a6b2f,#7aa05a); }
.indexed-card .stat-icon { background: linear-gradient(135deg,#2f7a4f,#4db18c); }
.chunk-card .stat-icon { background: linear-gradient(135deg,#2f5b7a,#4d8db1); }
.size-card .stat-icon { background: linear-gradient(135deg,#8a5b2f,#c9943e); }
.stat-info { flex: 1; margin-left: 14px; }
.stat-num { font-size: 26px; font-weight: 700; color: #3c5222; }
.stat-sub { font-size: 14px; font-weight: 400; color: #9aa48c; margin-left: 4px; }
.stat-label { font-size: 13px; color: #7d876d; margin-top: 2px; }

.toolbar-card .upload-tip {
  margin-top: 14px;
  color: #909399;
  font-size: 12px;
  line-height: 1.8;
  padding-left: 4px;
}
.card-header {
  display: flex; justify-content: space-between; align-items: center;
}
.doc-total { font-size: 13px; color: #909399; }

.doc-name {
  display: flex; align-items: center; gap: 8px;
  font-size: 14px;
}
.doc-icon { font-size: 20px; flex-shrink: 0; }
.doc-fn {
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  max-width: 440px;
}
</style>
