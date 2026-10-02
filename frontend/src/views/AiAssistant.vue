<template>
  <div class="ai-page">
    <el-tabs v-model="activeTab" type="border-card">
      <!-- AI 对话 -->
      <el-tab-pane label="智能对话" name="chat">
        <div class="chat-container">
          <div class="chat-header">
            <el-tag :type="aiStatus.model_available ? 'success' : 'warning'" size="small">
              {{ aiStatus.model_available ? `本地大模型在线 (${aiStatus.model_name})` : '大模型加载中 - 降级为知识库检索' }}
            </el-tag>
            <el-tag v-if="aiStatus.kb_doc_count > 0" type="info" size="small" style="margin-left:8px">
              知识库 {{ aiStatus.kb_doc_count }} 篇文档
            </el-tag>
          </div>
          <div class="chat-messages" ref="msgBox">
            <div v-for="(msg, i) in messages" :key="i" :class="['msg', msg.role]">
              <div class="msg-avatar">{{ msg.role === 'user' ? '我' : 'AI' }}</div>
              <div class="msg-content">
                <div class="msg-text">{{ msg.content }}</div>
                <div v-if="msg.source" class="msg-meta">
                  <el-tag size="small" type="info">{{ sourceLabel(msg.source) }}</el-tag>
                  <span v-if="msg.kb_hits" style="margin-left:6px;font-size:12px;color:#909399">
                    知识库命中 {{ msg.kb_hits }} 条
                  </span>
                </div>
              </div>
            </div>
            <div v-if="loading" class="msg assistant">
              <div class="msg-avatar">AI</div>
              <div class="msg-content"><div class="msg-text typing">正在思考中...</div></div>
            </div>
          </div>
          <div class="chat-input">
            <el-input
              v-model="inputText"
              type="textarea"
              :rows="2"
              placeholder="输入您的问题，如：如何发起请假审批？人员档案如何管理？"
              @keydown.enter.exact.prevent="sendChat"
            />
            <el-button type="primary" :loading="loading" @click="sendChat" style="margin-top:8px">
              发送
            </el-button>
          </div>
        </div>
      </el-tab-pane>

      <!-- 知识库管理 -->
      <el-tab-pane label="知识库管理" name="kb">
        <el-card shadow="never">
          <template #header>
            <div class="h">
              <span>📚 知识库文档</span>
              <el-upload
                :show-file-list="false"
                :before-upload="handleUpload"
                accept=".txt,.md,.pdf,.docx,.doc"
                style="margin-left:auto"
              >
                <el-button type="primary" size="small">+ 上传文档</el-button>
              </el-upload>
            </div>
          </template>
          <el-table :data="kbDocs" size="small" stripe>
            <el-table-column prop="filename" label="文件名" min-width="200" />
            <el-table-column prop="size_text" label="大小" width="100" />
            <el-table-column label="操作" width="100" align="center">
              <template #default="{ row }">
                <el-button type="danger" link size="small" @click="deleteDoc(row.filename)">删除</el-button>
              </template>
            </el-table-column>
            <template #empty><el-empty description="暂无知识库文档" :image-size="60" /></template>
          </el-table>
        </el-card>

        <el-card shadow="never" style="margin-top:16px">
          <template #header><div class="h">🔍 知识库检索测试</div></template>
          <el-input v-model="kbQuery" placeholder="输入关键词检索知识库" style="margin-bottom:12px">
            <template #append>
              <el-button @click="searchKb" :loading="kbLoading">检索</el-button>
            </template>
          </el-input>
          <div v-for="(r, i) in kbResults" :key="i" class="kb-result">
            <div class="kb-result-content">{{ r.content }}</div>
            <div class="kb-result-meta">来源: {{ r.metadata?.source || '未知' }}</div>
          </div>
          <el-empty v-if="kbResults.length === 0 && kbSearched" description="无匹配结果" :image-size="60" />
        </el-card>
      </el-tab-pane>

      <!-- 服务状态 -->
      <el-tab-pane label="服务状态" name="status">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="本地大模型">
            <el-tag :type="aiStatus.model_available ? 'success' : 'warning'">
              {{ aiStatus.model_available ? '已加载' : '未加载（首次提问时自动加载）' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="生成模型">{{ aiStatus.model_name || 'Qwen2-0.5B-Instruct（本地PyTorch）' }}</el-descriptions-item>
          <el-descriptions-item label="运行设备">{{ aiStatus.model_device === 'cuda' ? 'GPU (CUDA)' : aiStatus.model_device === 'cpu' ? 'CPU' : aiStatus.model_device || '-' }}</el-descriptions-item>
          <el-descriptions-item label="Embedding 模型">{{ aiStatus.embedding_model || '-' }}</el-descriptions-item>
          <el-descriptions-item label="知识库文档数">
            {{ aiStatus.kb_doc_count || 0 }} 篇
            <span v-if="aiStatus.kb_indexed_docs !== undefined" style="color:#909399;font-size:12px;margin-left:6px">
              （已入库 {{ aiStatus.kb_indexed_docs }} 篇）
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="知识库向量块">{{ aiStatus.kb_chunk_count || 0 }} 块</el-descriptions-item>
          <el-descriptions-item label="当前模式">
            <el-tag :type="aiStatus.mode === 'local+rag' ? 'success' : 'warning'">
              {{ sourceLabel(aiStatus.mode) }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>
        <el-alert
          v-if="!aiStatus.model_available"
          title="本地大模型未加载"
          type="info"
          :closable="false"
          style="margin-top:16px"
        >
          <template #default>
            模型将在您第一次发起对话时自动加载（约10-30秒），加载后即可正常问答。<br/>
            当前仍可通过知识库检索模式回答问题。
          </template>
        </el-alert>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, nextTick } from 'vue'
import { aiApi } from '@/api'
import { ElMessage, ElMessageBox } from 'element-plus'

const activeTab = ref('chat')
const aiStatus = reactive({})
const loading = ref(false)
const inputText = ref('')
const messages = ref([
  { role: 'assistant', content: '您好！我是智能助手，可以回答人员管理、审批流程等问题。请问有什么可以帮您？' }
])
const msgBox = ref(null)

const kbDocs = ref([])
const kbQuery = ref('')
const kbResults = ref([])
const kbLoading = ref(false)
const kbSearched = ref(false)

const sourceLabel = (s) => ({
  'local+rag': '本地大模型+知识库',
  'local+rag-v2': '本地大模型+知识库',
  'ollama+rag-v2': '大模型+知识库',
  'local_only': '本地大模型',
  'local': '本地大模型',
  'ollama': '大模型',
  'rag_only': '仅知识库',
  'rag_only-v2': '仅知识库检索',
  'fallback': '降级模式',
  'preset': '预设库',
}[s] || s)

const loadStatus = async () => {
  try {
    const data = await aiApi.status()
    Object.assign(aiStatus, data)
  } catch (e) { console.error('AI状态加载失败', e) }
}

const loadKbDocs = async () => {
  try {
    const data = await aiApi.listKbDocs()
    kbDocs.value = data.items || []
  } catch (e) { console.error(e) }
}

const sendChat = async () => {
  if (!inputText.value.trim() || loading.value) return
  const userMsg = inputText.value.trim()
  messages.value.push({ role: 'user', content: userMsg })
  inputText.value = ''
  loading.value = true
  await nextTick()
  msgBox.value?.scrollTo({ top: msgBox.value.scrollHeight, behavior: 'smooth' })
  try {
    const data = await aiApi.chat({ message: userMsg })
    messages.value.push({
      role: 'assistant',
      content: data.answer,
      source: data.source,
      kb_hits: data.kb_hits,
    })
  } catch (e) {
    messages.value.push({ role: 'assistant', content: '抱歉，回答失败，请稍后重试。' })
  } finally {
    loading.value = false
    await nextTick()
    msgBox.value?.scrollTo({ top: msgBox.value.scrollHeight, behavior: 'smooth' })
  }
}

const handleUpload = async (file) => {
  try {
    const data = await aiApi.uploadKbDoc(file)
    ElMessage.success(data.message)
    loadKbDocs()
    loadStatus()
  } catch (e) {
    ElMessage.error('上传失败: ' + (e.response?.data?.detail || e.message))
  }
  return false
}

const deleteDoc = async (filename) => {
  try {
    await ElMessageBox.confirm(`确定删除「${filename}」？`, '提示', { type: 'warning' })
    await aiApi.deleteKbDoc(filename)
    ElMessage.success('已删除')
    loadKbDocs()
    loadStatus()
  } catch (e) { /* 取消 */ }
}

const searchKb = async () => {
  if (!kbQuery.value.trim()) return
  kbLoading.value = true
  kbSearched.value = true
  try {
    const data = await aiApi.searchKb({ query: kbQuery.value, top_k: 5 })
    kbResults.value = data.results || []
  } catch (e) {
    ElMessage.error('检索失败')
  } finally {
    kbLoading.value = false
  }
}

onMounted(() => {
  loadStatus()
  loadKbDocs()
})
</script>

<style scoped>
.ai-page { padding: 16px; }
.h { display: flex; align-items: center; font-weight: 600; }

.chat-container { display: flex; flex-direction: column; height: calc(100vh - 220px); }
.chat-header { padding: 8px 0; }
.chat-messages {
  flex: 1; overflow-y: auto; padding: 12px; background: #f5f7fa;
  border-radius: 8px; margin-bottom: 12px;
}
.msg { display: flex; gap: 12px; margin-bottom: 16px; }
.msg-avatar {
  width: 36px; height: 36px; border-radius: 50%; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  font-size: 14px; font-weight: 600; color: #fff;
}
.msg.user .msg-avatar { background: #409eff; }
.msg.assistant .msg-avatar { background: #2d5a27; }
.msg-content { flex: 1; }
.msg-text {
  padding: 10px 14px; border-radius: 8px; font-size: 14px; line-height: 1.6;
  white-space: pre-wrap; word-break: break-word;
}
.msg.user .msg-text { background: #ecf5ff; color: #303133; }
.msg.assistant .msg-text { background: #fff; color: #303133; border: 1px solid #ebeef5; }
.msg-meta { margin-top: 4px; }
.typing { color: #909399; font-style: italic; }
.chat-input { display: flex; flex-direction: column; }

.kb-result {
  padding: 12px; background: #f5f7fa; border-radius: 6px; margin-bottom: 8px;
  border-left: 3px solid #409eff;
}
.kb-result-content { font-size: 13px; color: #303133; line-height: 1.6; margin-bottom: 4px; }
.kb-result-meta { font-size: 12px; color: #909399; }
</style>
