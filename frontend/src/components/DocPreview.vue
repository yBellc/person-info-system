<template>
  <div class="doc-preview">
    <!-- Word 文档预览 -->
    <div v-if="fileType === 'docx'" class="doc-word-preview">
      <div ref="wordContainer" v-html="wordHtml" class="word-content"
        :class="{ 'edit-mode': mode === 'fill', 'annotate-mode': mode === 'annotate' }"
        @click="onCellClick" @blur="onCellBlur"></div>
    </div>

    <!-- Excel 文档预览 -->
    <div v-else-if="fileType === 'xlsx' || fileType === 'xls'" class="doc-excel-preview">
      <div ref="excelContainer" v-html="excelHtml" class="excel-content"
        :class="{ 'edit-mode': mode === 'fill', 'annotate-mode': mode === 'annotate' }"
        @click="onCellClick" @blur="onCellBlur"></div>
    </div>

    <!-- PDF 预览 -->
    <div v-else-if="fileType === 'pdf'" class="doc-pdf-preview">
      <iframe :src="pdfUrl" frameborder="0" class="pdf-frame"></iframe>
    </div>

    <!-- 无源文件提示 -->
    <div v-if="!fileType && !loading" class="no-source">
      <el-empty description="该表单没有原版文档" />
    </div>

    <!-- 加载中 -->
    <div v-if="loading" class="loading">
      <el-icon class="is-loading" :size="24"><Loading /></el-icon>
      <span>正在加载文档...</span>
    </div>

    <!-- 错误提示 -->
    <div v-if="error" class="error">
      <el-alert :title="error" type="error" show-icon :closable="false" />
    </div>

    <!-- 模式提示条 -->
    <div v-if="mode === 'annotate' && !loading && !error && fileType" class="mode-hint annotate-hint">
      <el-icon size="14"><EditPen /></el-icon>
      <span>标注模式：点击任意单元格添加填写字段，点击已有字段可删除</span>
      <span class="field-count">已标注 {{ fields.length }} 个字段</span>
    </div>
    <div v-else-if="mode === 'fill' && !loading && !error && fileType" class="mode-hint fill-hint">
      <el-icon size="14"><EditPen /></el-icon>
      <span>点击黄色单元格直接填写</span>
    </div>
    <div v-else-if="mode === 'view' && !loading && !error && fileType" class="mode-hint view-hint">
      <el-icon size="14"><EditPen /></el-icon>
      <span>查看模式：只读预览已填写内容</span>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, computed, nextTick } from 'vue'
import mammoth from 'mammoth'
import * as XLSX from 'xlsx'
import { Loading, EditPen } from '@element-plus/icons-vue'

const props = defineProps({
  formId: { type: Number, required: true },
  formType: { type: String, default: '' },
  // 模式: view(只读查看), fill(填写模式), annotate(标注模式)
  mode: { type: String, default: 'view' },
  fillData: { type: Object, default: () => ({}) },
  // 字段定义列表
  fields: { type: Array, default: () => [] },
})

const emit = defineEmits(['update:fillData', 'update:fields', 'annotate'])

const loading = ref(false)
const error = ref('')
const wordHtml = ref('')
const excelHtml = ref('')
const pdfUrl = ref('')
const wordContainer = ref(null)
const excelContainer = ref(null)

const fileType = computed(() => props.formType || '')

// 占位符文本模式（识别为"可填写区域"的内容）
const PLACEHOLDER_PATTERNS = [
  /^[\s_]+$/,           // 纯下划线
  /^[_\.]{2,}$/,        // 下划线或点号序列
  /^[-—–]{2,}$/,        // 破折号序列
  /^[\?？]{1,}$/,       // 问号
  /^[（(][\s_　]*[)）]$/, // 空括号 () （）
  /^\[[\s_　]*\]$/,     // 方括号 []
  /^〔[\s_　]*〕$/,     // 中文方括号
  /^[〈〈][\s_　]*[〉〉]$/, // 尖括号
  /待填写|待填|待补充|请填写|请填|请输入|填写此处|此处填写|此处/,  // 提示文本
  /^无$|^—$|^--$|^-$|^N\/A$|^n\/a$/i,  // 常见的"无"表示
]

const isPlaceholderText = (text) => {
  if (!text) return true  // 空文本也是占位符
  const t = text.trim()
  if (!t) return true
  return PLACEHOLDER_PATTERNS.some(p => p.test(t))
}

// 带认证的文件下载
const fetchFile = async (url) => {
  const token = localStorage.getItem('token')
  const response = await fetch(url, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!response.ok) throw new Error(`HTTP ${response.status}`)
  return response.arrayBuffer()
}

const loadDocument = async () => {
  if (!fileType.value) return
  loading.value = true
  error.value = ''
  try {
    const fileUrl = `/api/v1/smart-forms/${props.formId}/source-file`
    if (fileType.value === 'docx') {
      await loadWord(fileUrl)
    } else if (fileType.value === 'xlsx' || fileType.value === 'xls') {
      await loadExcel(fileUrl)
    } else if (fileType.value === 'pdf') {
      const token = localStorage.getItem('token')
      pdfUrl.value = token ? `${fileUrl}?token=${token}` : fileUrl
    } else {
      error.value = '不支持的文件类型'
    }
  } catch (e) {
    error.value = `加载文档失败: ${e.message}`
  } finally {
    loading.value = false
  }
}

const loadWord = async (fileUrl) => {
  try {
    const arrayBuffer = await fetchFile(fileUrl)
    const result = await mammoth.convertToHtml({ arrayBuffer })
    wordHtml.value = result.value
    await nextTick()
    assignCellPaths(wordContainer.value)
    markEditableByFields(wordContainer.value)
    applyExistingData(wordContainer.value)
  } catch (e) {
    error.value = `Word文档解析失败: ${e.message}`
  }
}

const loadExcel = async (fileUrl) => {
  try {
    const arrayBuffer = await fetchFile(fileUrl)
    const workbook = XLSX.read(arrayBuffer, { type: 'array' })
    let html = ''
    for (let si = 0; si < workbook.SheetNames.length; si++) {
      const sheetName = workbook.SheetNames[si]
      const sheet = workbook.Sheets[sheetName]
      const tableHtml = XLSX.utils.sheet_to_html(sheet, { editable: false })
      html += `<div class="excel-sheet" data-sheet-index="${si}" data-sheet-name="${sheetName}">
        <div class="sheet-name">${sheetName}</div>${tableHtml}</div>`
    }
    excelHtml.value = html
    await nextTick()
    assignCellPaths(excelContainer.value)
    markEditableByFields(excelContainer.value)
    applyExistingData(excelContainer.value)
  } catch (e) {
    error.value = `Excel文档解析失败: ${e.message}`
  }
}

/**
 * 为容器中所有 td/th 单元格分配唯一的 path 标识
 * Word: table:{tableIndex},row:{rowIndex},col:{colIndex}
 * Excel: sheet:{sheetName},row:{rowIndex},col:{colIndex}
 */
const assignCellPaths = (container) => {
  if (!container) return

  const isExcel = container.classList.contains('excel-content')
  const sheetDivs = isExcel
    ? container.querySelectorAll('.excel-sheet')
    : [container]

  for (let si = 0; si < sheetDivs.length; si++) {
    const sheetDiv = sheetDivs[si]
    const tables = sheetDiv.querySelectorAll('table')
    for (let ti = 0; ti < tables.length; ti++) {
      const table = tables[ti]
      const rows = table.querySelectorAll('tr')
      for (let ri = 0; ri < rows.length; ri++) {
        const cells = rows[ri].querySelectorAll('td, th')
        for (let ci = 0; ci < cells.length; ci++) {
          const cell = cells[ci]
          let path
          if (isExcel) {
            const sheetName = sheetDiv.dataset.sheetName || `Sheet${si + 1}`
            path = `sheet:${sheetName},row:${ri + 1},col:${ci + 1}`
          } else {
            path = `table:${ti},row:${ri},col:${ci}`
          }
          cell.setAttribute('data-path', path)
          cell.classList.add('doc-cell')
        }
      }
    }
  }
}

/**
 * 根据字段定义中的 source_cell_path 精确标记可编辑单元格
 */
const markEditableByFields = (container) => {
  if (!container) return

  const fieldsWithPath = props.fields.filter(f => f.source_cell_path)
  const fieldsWithoutPath = props.fields.filter(f => !f.source_cell_path)
  const matchedFieldKeys = new Set()

  // 第一轮：按 source_cell_path 精确匹配
  const editablePathMap = {}
  for (const f of fieldsWithPath) {
    editablePathMap[f.source_cell_path] = f
  }

  for (const cell of container.querySelectorAll('.doc-cell')) {
    const path = cell.getAttribute('data-path')
    if (editablePathMap[path]) {
      const field = editablePathMap[path]
      cell.setAttribute('contenteditable', props.mode === 'fill' ? 'true' : 'false')
      cell.setAttribute('data-field-key', field.field_key)
      cell.classList.add('editable-cell')
      cell.setAttribute('data-placeholder', field.field_label)
      cell.classList.remove('annotatable-cell', 'placeholder-cell', 'label-cell')
      matchedFieldKeys.add(field.field_key)
      delete editablePathMap[path]
    }
  }

  // 第二轮：标签匹配（仅填写模式）- 处理所有未匹配的字段
  if (props.mode === 'fill') {
    const unmatchedFields = props.fields.filter(f => !matchedFieldKeys.has(f.field_key))
    for (const field of unmatchedFields) {
      const matched = findAndMarkByLabel(container, field)
      if (matched) {
        matchedFieldKeys.add(field.field_key)
      }
    }

    // 第三轮：终极回退 - 按顺序匹配所有剩余空单元格/占位符单元格
    const stillUnmatched = props.fields.filter(f => !matchedFieldKeys.has(f.field_key))
    if (stillUnmatched.length > 0) {
      const emptyCells = []
      for (const cell of container.querySelectorAll('.doc-cell')) {
        if (cell.getAttribute('data-field-key')) continue
        const text = (cell.textContent || '').trim()
        if (!text || isPlaceholderText(text)) {
          emptyCells.push(cell)
        }
      }
      for (let i = 0; i < stillUnmatched.length && i < emptyCells.length; i++) {
        const field = stillUnmatched[i]
        const cell = emptyCells[i]
        cell.setAttribute('contenteditable', 'true')
        cell.setAttribute('data-field-key', field.field_key)
        cell.classList.add('editable-cell')
        cell.setAttribute('data-placeholder', field.field_label)
        matchedFieldKeys.add(field.field_key)
      }
    }
  }

  // 标注模式：标记所有可交互单元格
  if (props.mode === 'annotate') {
    markAllCellsAsAnnotatable(container)
  }
}

/**
 * 标注模式：标记所有单元格为可交互状态
 * - 空单元格 → annotatable-cell（蓝色虚线）
 * - 占位符文本 → placeholder-cell（橙色虚线）
 * - 已有文字且非占位符 → annotatable-cell（可点击标注）
 */
const markAllCellsAsAnnotatable = (container) => {
  for (const cell of container.querySelectorAll('.doc-cell')) {
    const hasField = cell.getAttribute('data-field-key')
    if (hasField) continue  // 已有字段的不再标记

    const text = (cell.textContent || '').trim()
    if (!text) {
      // 空单元格
      cell.classList.add('annotatable-cell')
    } else if (isPlaceholderText(text)) {
      // 占位符单元格
      cell.classList.add('placeholder-cell')
    } else {
      // 有内容但可能是标签或其他内容的单元格
      cell.classList.add('annotatable-cell')
    }
  }
}

/**
 * 通过标签文本查找并标记相邻空单元格
 * Returns true if a match was found and marked
 */
const findAndMarkByLabel = (container, field) => {
  const allCells = container.querySelectorAll('.doc-cell')
  const label = field.field_label
  
  // 模糊匹配：精确匹配、加冒号、包含关系
  const matchesLabel = (text) => {
    const clean = text.trim().replace(/[：:]$/, '')
    return clean === label || clean.includes(label) || label.includes(clean)
  }
  
  for (const cell of allCells) {
    if (cell.getAttribute('data-field-key')) continue
    const text = (cell.textContent || '').trim()
    if (!matchesLabel(text)) continue
    
    const row = cell.parentElement
    const cellIndex = Array.from(row.children).indexOf(cell)
    let target = null
    
    // 查找右侧单元格（优先占位符，其次任意空单元格）
    if (cellIndex < row.children.length - 1) {
      const right = row.children[cellIndex + 1]
      if (right && !right.getAttribute('data-field-key')) {
        if (isPlaceholderText(right.textContent) || !(right.textContent || '').trim()) {
          target = right
        }
      }
    }
    
    // 查找下方单元格
    if (!target) {
      const table = row.parentElement
      if (table && table.tagName === 'TBODY') {
        const rowIndex = Array.from(table.children).indexOf(row)
        if (rowIndex < table.children.length - 1) {
          const belowRow = table.children[rowIndex + 1]
          if (belowRow && belowRow.children[cellIndex]) {
            const below = belowRow.children[cellIndex]
            if (below && !below.getAttribute('data-field-key')) {
              if (isPlaceholderText(below.textContent) || !(below.textContent || '').trim()) {
                target = below
              }
            }
          }
        }
      }
    }
    
    if (target) {
      target.setAttribute('contenteditable', 'true')
      target.setAttribute('data-field-key', field.field_key)
      target.classList.add('editable-cell')
      target.setAttribute('data-placeholder', field.field_label)
      cell.classList.add('field-label-cell')
      return true
    }
  }
  return false
}

/**
 * 填入已有数据（填写模式和查看模式都需要）
 */
const applyExistingData = (container) => {
  if (!container) return
  const editableCells = container.querySelectorAll('[data-field-key]')
  for (const cell of editableCells) {
    const fieldKey = cell.getAttribute('data-field-key')
    const value = props.fillData[fieldKey]
    if (value) {
      cell.textContent = String(value)
      cell.classList.add('filled-cell')
    }
  }
}

/**
 * 点击事件处理
 */
const onCellClick = (e) => {
  const cell = e.target.closest('.doc-cell')
  if (!cell) return

  if (props.mode === 'annotate') {
    handleAnnotateClick(cell)
  } else if (props.mode === 'fill' && cell.getAttribute('contenteditable') === 'true') {
    clearActiveCells()
    cell.classList.add('active-cell')
  }
}

/**
 * 在标注模式下查找某个单元格附近最近的文本标签
 * 返回 { label: string, targetCell: HTMLElement, targetPath: string }
 */
const findAdjacentLabel = (cell) => {
  const row = cell.parentElement
  const cellIndex = Array.from(row.children).indexOf(cell)

  // 1. 查找左侧相邻单元格（可能是标签）
  if (cellIndex > 0) {
    const left = row.children[cellIndex - 1]
    if (left) {
      const leftText = (left.textContent || '').trim()
      if (leftText && !isPlaceholderText(leftText) && leftText.length <= 20 && !left.getAttribute('data-field-key')) {
        return { label: leftText, labelCell: left }
      }
    }
  }

  // 2. 查找上方单元格
  const table = row.parentElement
  if (table && table.tagName === 'TBODY') {
    const rowIndex = Array.from(table.children).indexOf(row)
    if (rowIndex > 0) {
      const aboveRow = table.children[rowIndex - 1]
      if (aboveRow && aboveRow.children[cellIndex]) {
        const above = aboveRow.children[cellIndex]
        const aboveText = (above.textContent || '').trim()
        if (aboveText && !isPlaceholderText(aboveText) && aboveText.length <= 20 && !above.getAttribute('data-field-key')) {
          return { label: aboveText, labelCell: above }
        }
      }
    }
  }

  return null
}

/**
 * 标注模式点击处理 — 核心改进
 * 所有单元格均可点击：
 * - 已有字段 → 询问删除
 * - 空单元格 → 弹出对话框输入标签
 * - 占位符单元格 → 建议作为字段（可选修改标签）
 * - 标签类单元格 → 建议以此为标签，标注相邻的空单元格
 */
const handleAnnotateClick = (cell) => {
  const path = cell.getAttribute('data-path')
  const existingFieldKey = cell.getAttribute('data-field-key')

  // 已有字段 → 询问删除
  if (existingFieldKey) {
    const field = props.fields.find(f => f.field_key === existingFieldKey)
    const label = field?.field_label || existingFieldKey
    if (confirm(`删除字段「${label}」？`)) {
      removeFieldFromCell(cell)
    }
    return
  }

  const text = (cell.textContent || '').trim()
  const isPlaceholder = isPlaceholderText(text)

  // 如果点击的是标签类文本单元格 → 建议以此为标签
  if (text && !isPlaceholder && text.length <= 20) {
    const adjacent = findAdjacentLabel(cell)
    // 检查文本是否像字段标签（短文本、非占位符）
    const labelSuggestion = text.replace(/[：:]$/, '').trim()
    if (labelSuggestion.length >= 1) {
      // 检查右侧/下方是否有可填写的单元格
      const targetInfo = findTargetCellForLabel(cell)
      if (targetInfo) {
        // 有目标单元格 → 以当前文本为标签
        if (confirm(`将「${labelSuggestion}」设为字段标签？\n\n填写位置：${targetInfo.targetPath}\n点击"取消"手动输入标签`)) {
          addFieldAt(labelSuggestion, targetInfo.targetPath)
          targetInfo.targetCell.classList.remove('annotatable-cell', 'placeholder-cell')
          targetInfo.targetCell.setAttribute('data-field-key', generateFieldKey(labelSuggestion))
          targetInfo.targetCell.classList.add('editable-cell')
          cell.classList.add('field-label-cell')
          cell.classList.remove('annotatable-cell', 'placeholder-cell')
        } else {
          // 用户取消 → 手动输入标签，在当前单元格
          manualAnnotateCell(cell, path)
        }
        return
      } else {
        // 没有相邻的空单元格 → 询问是否在当前位置标注
        if (confirm(`文本「${text}」看起来像字段标签，但未找到相邻空单元格。\n是否直接标注当前单元格为填写区域？`)) {
          addFieldAt(labelSuggestion, path)
          cell.classList.remove('annotatable-cell', 'placeholder-cell')
          cell.setAttribute('data-field-key', generateFieldKey(labelSuggestion))
          cell.classList.add('editable-cell')
        }
        return
      }
    }
  }

  // 空单元格或占位符单元格 → 手动输入标签
  manualAnnotateCell(cell, path)
}

/**
 * 为标签单元格查找可作为填写区域的目标单元格
 * 优先右侧、其次下方
 */
const findTargetCellForLabel = (labelCell) => {
  const row = labelCell.parentElement
  const cellIndex = Array.from(row.children).indexOf(labelCell)

  // 1. 右侧单元格
  if (cellIndex < row.children.length - 1) {
    const right = row.children[cellIndex + 1]
    if (right && !right.getAttribute('data-field-key') && isPlaceholderText(right.textContent)) {
      return { targetCell: right, targetPath: right.getAttribute('data-path') }
    }
  }

  // 2. 下方单元格
  const table = row.parentElement
  if (table && table.tagName === 'TBODY') {
    const rowIndex = Array.from(table.children).indexOf(row)
    if (rowIndex < table.children.length - 1) {
      const belowRow = table.children[rowIndex + 1]
      if (belowRow && belowRow.children[cellIndex]) {
        const below = belowRow.children[cellIndex]
        if (!below.getAttribute('data-field-key') && isPlaceholderText(below.textContent)) {
          return { targetCell: below, targetPath: below.getAttribute('data-path') }
        }
      }
    }
  }

  // 3. 右侧非空但可覆盖的单元格（用户明确选择时）
  if (cellIndex < row.children.length - 1) {
    const right = row.children[cellIndex + 1]
    if (right && !right.getAttribute('data-field-key')) {
      return { targetCell: right, targetPath: right.getAttribute('data-path') }
    }
  }

  // 4. 下方非空但可覆盖的单元格
  if (table && table.tagName === 'TBODY') {
    const rowIndex = Array.from(table.children).indexOf(row)
    if (rowIndex < table.children.length - 1) {
      const belowRow = table.children[rowIndex + 1]
      if (belowRow && belowRow.children[cellIndex]) {
        const below = belowRow.children[cellIndex]
        if (!below.getAttribute('data-field-key')) {
          return { targetCell: below, targetPath: below.getAttribute('data-path') }
        }
      }
    }
  }

  return null
}

/**
 * 手动标注单元格（弹出对话框输入标签）
 */
const manualAnnotateCell = (cell, path) => {
  const text = (cell.textContent || '').trim()
  let defaultLabel = ''
  if (text && !isPlaceholderText(text)) {
    defaultLabel = text.replace(/[：:]$/, '').trim()
  } else {
    // 尝试从相邻单元格找标签
    const adjacent = findAdjacentLabel(cell)
    if (adjacent) {
      defaultLabel = adjacent.label
    }
  }

  const label = prompt('请输入此字段的标签（如: 姓名）:', defaultLabel || '')
  if (!label) return

  addFieldAt(label, path)
  cell.classList.remove('annotatable-cell', 'placeholder-cell')
  cell.setAttribute('data-field-key', generateFieldKey(label))
  cell.classList.add('editable-cell')

  // 如果有找到相邻标签，标记它
  const adjacent = findAdjacentLabel(cell)
  if (adjacent && adjacent.labelCell) {
    adjacent.labelCell.classList.add('field-label-cell')
    adjacent.labelCell.classList.remove('annotatable-cell', 'placeholder-cell')
  }
}

const removeFieldFromCell = (cell) => {
  const path = cell.getAttribute('data-path')
  const fieldKey = cell.getAttribute('data-field-key')
  const newFields = props.fields.filter(f => f.field_key !== fieldKey)
  emit('update:fields', newFields)

  // 如果旁边有标签单元格，恢复它
  const row = cell.parentElement
  const cellIndex = Array.from(row.children).indexOf(cell)
  if (cellIndex > 0) {
    const left = row.children[cellIndex - 1]
    if (left && left.classList.contains('field-label-cell')) {
      left.classList.remove('field-label-cell')
      left.classList.add('annotatable-cell')
    }
  }

  cell.removeAttribute('contenteditable')
  cell.removeAttribute('data-field-key')
  cell.classList.remove('editable-cell', 'filled-cell', 'field-label-cell')
  cell.classList.add('annotatable-cell')
}

const generateFieldKey = (label) => {
  const existing = props.fields.map(f => f.field_key)
  let base = label.toLowerCase().replace(/[^\w\u4e00-\u9fa5]/g, '_').replace(/^_+|_+$/g, '')
  if (!base) base = 'field'
  let key = base
  let counter = 2
  while (existing.includes(key)) {
    key = `${base}_${counter}`
    counter++
  }
  return key
}

const addFieldAt = (label, cellPath) => {
  const newField = {
    field_key: generateFieldKey(label),
    field_label: label,
    field_type: 'text',
    source_cell_path: cellPath,
    is_required: false,
    is_readonly: false,
    field_options: null,
    auto_fill_key: null,
    default_value: '',
    placeholder: `请输入${label}`,
  }
  const newFields = [...props.fields, newField]
  emit('update:fields', newFields)
  emit('annotate', newField)
}

/**
 * 失焦事件：保存填写数据
 */
const onCellBlur = (e) => {
  if (props.mode !== 'fill') return
  const cell = e.target.closest('[data-field-key]')
  if (!cell) return

  const fieldKey = cell.getAttribute('data-field-key')
  const value = (cell.textContent || '').trim()

  if (fieldKey) {
    const newData = { ...props.fillData, [fieldKey]: value }
    emit('update:fillData', newData)

    if (value) cell.classList.add('filled-cell')
    else cell.classList.remove('filled-cell')
  }
  cell.classList.remove('active-cell')
}

const clearActiveCells = () => {
  const containers = [wordContainer.value, excelContainer.value].filter(Boolean)
  for (const c of containers) {
    c.querySelectorAll('.active-cell').forEach(el => el.classList.remove('active-cell'))
  }
}

/**
 * 公开方法
 */
const getFillData = () => {
  const result = { ...props.fillData }
  const containers = [wordContainer.value, excelContainer.value].filter(Boolean)
  for (const c of containers) {
    const cells = c.querySelectorAll('[data-field-key]')
    for (const cell of cells) {
      const fieldKey = cell.getAttribute('data-field-key')
      if (fieldKey) result[fieldKey] = (cell.textContent || '').trim()
    }
  }
  return result
}

const getAllAnnotatedFields = () => {
  const containers = [wordContainer.value, excelContainer.value].filter(Boolean)
  const result = []
  for (const c of containers) {
    const cells = c.querySelectorAll('[data-field-key]')
    for (const cell of cells) {
      const fieldKey = cell.getAttribute('data-field-key')
      const path = cell.getAttribute('data-path')
      if (fieldKey && path) {
        const existing = props.fields.find(f => f.field_key === fieldKey)
        if (existing) {
          result.push({ ...existing, source_cell_path: path })
        }
      }
    }
  }
  return result
}

defineExpose({ getFillData, getAllAnnotatedFields })

// 生命周期
onMounted(() => {
  if (props.formId) loadDocument()
})

watch(() => [props.formId, props.mode], () => {
  if (props.formId) loadDocument()
}, { deep: true })

watch(() => props.fields, () => {
  if (loading.value) return
  const container = wordContainer.value || excelContainer.value
  if (container) {
    container.querySelectorAll('.doc-cell').forEach(cell => {
      cell.removeAttribute('contenteditable')
      cell.removeAttribute('data-field-key')
      cell.classList.remove('editable-cell', 'filled-cell', 'field-label-cell', 'annotatable-cell', 'placeholder-cell', 'active-cell')
    })
    markEditableByFields(container)
    applyExistingData(container)
  }
}, { deep: true })

watch(() => props.fillData, () => {
  if (!loading.value) {
    const container = wordContainer.value || excelContainer.value
    if (container) applyExistingData(container)
  }
}, { deep: true })
</script>

<style scoped>
.doc-preview {
  position: relative;
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 16px;
  min-height: 300px;
}

.loading, .error, .no-source {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
  color: #909399;
  gap: 8px;
}

.mode-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 4px;
  font-size: 12px;
  margin-bottom: 8px;
}

.annotate-hint {
  background: #ecf5ff;
  border: 1px solid #d9ecff;
  color: #409eff;
}

.annotate-hint .field-count {
  margin-left: auto;
  font-weight: 600;
  color: #409eff;
  background: #fff;
  padding: 2px 8px;
  border-radius: 10px;
}

.fill-hint {
  background: #fdf6ec;
  border: 1px solid #f5dab1;
  color: #e6a23c;
}

.view-hint {
  background: #ecf5ff;
  border: 1px solid #b3d8ff;
  color: #409eff;
}

/* Word 文档样式 */
.word-content {
  font-family: 'Times New Roman', '宋体', serif;
  font-size: 12px;
  line-height: 1.8;
  color: #333;
  max-width: 100%;
  overflow-x: auto;
}

.word-content :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 8px 0;
}

.word-content :deep(table td),
.word-content :deep(table th) {
  border: 1px solid #999;
  padding: 6px 10px;
  min-width: 60px;
}

.word-content :deep(h1),
.word-content :deep(h2),
.word-content :deep(h3) {
  margin: 12px 0;
}

.word-content :deep(p) {
  margin: 6px 0;
}

/* ===== 标注模式样式 ===== */
.word-content.annotate-mode :deep(.annotatable-cell),
.excel-content.annotate-mode :deep(.annotatable-cell) {
  background: #f0f9ff;
  cursor: pointer;
  outline: 1px dashed #91d5ff;
  outline-offset: -1px;
  transition: all 0.15s;
}

.word-content.annotate-mode :deep(.annotatable-cell:hover),
.excel-content.annotate-mode :deep(.annotatable-cell:hover) {
  background: #e1f4ff;
  outline-color: #409eff;
  transform: scale(1.01);
}

/* 占位符单元格 - 橙色虚线 */
.word-content.annotate-mode :deep(.placeholder-cell),
.excel-content.annotate-mode :deep(.placeholder-cell) {
  background: #fdf6ec;
  cursor: pointer;
  outline: 1px dashed #e6a23c;
  outline-offset: -1px;
  transition: all 0.15s;
}

.word-content.annotate-mode :deep(.placeholder-cell:hover),
.excel-content.annotate-mode :deep(.placeholder-cell:hover) {
  background: #faecd8;
  outline-color: #f59c2a;
}

/* 已标注字段 - 绿色 */
.word-content.annotate-mode :deep(.editable-cell),
.excel-content.annotate-mode :deep(.editable-cell) {
  background: #f0f9eb;
  outline: 2px solid #67c23a;
  outline-offset: -2px;
  cursor: pointer;
  position: relative;
}

.word-content.annotate-mode :deep(.editable-cell)::after,
.excel-content.annotate-mode :deep(.editable-cell)::after {
  content: '✓';
  position: absolute;
  top: 2px;
  right: 4px;
  color: #67c23a;
  font-size: 10px;
  font-weight: bold;
}

/* 标签单元格 - 红色 */
.word-content.annotate-mode :deep(.field-label-cell),
.excel-content.annotate-mode :deep(.field-label-cell) {
  background: #fef0f0;
  font-weight: 600;
  color: #f56c6c;
}

/* ===== 填写模式样式 ===== */
.word-content.edit-mode :deep(.editable-cell),
.excel-content.edit-mode :deep(.editable-cell) {
  background: #fffbe6;
  cursor: text;
  transition: background 0.2s;
}

.word-content.edit-mode :deep(.editable-cell:hover),
.excel-content.edit-mode :deep(.editable-cell:hover) {
  background: #fef0d0;
}

.word-content.edit-mode :deep(.editable-cell.active-cell),
.excel-content.edit-mode :deep(.editable-cell.active-cell) {
  background: #f0f7ff;
  outline: 2px solid #409eff;
  outline-offset: -2px;
}

.word-content.edit-mode :deep(.editable-cell:empty::before),
.excel-content.edit-mode :deep(.editable-cell:empty::before) {
  content: attr(data-placeholder);
  color: #c0c4cc;
  font-style: italic;
  font-size: 11px;
}

.word-content.edit-mode :deep(.filled-cell),
.excel-content.edit-mode :deep(.filled-cell) {
  background: #f0f9eb !important;
  color: #333;
  font-weight: 500;
}

/* 查看模式下已填写的单元格样式 */
.word-content:not(.edit-mode):not(.annotate-mode) :deep(.filled-cell),
.excel-content:not(.edit-mode):not(.annotate-mode) :deep(.filled-cell) {
  background: #ecf5ff !important;
  color: #333;
  font-weight: 500;
}

.word-content.edit-mode :deep(.field-label-cell),
.excel-content.edit-mode :deep(.field-label-cell) {
  background: #f5f7fa;
  font-weight: 600;
  color: #606266;
}

/* Excel 文档样式 */
.excel-content {
  font-family: 'Calibri', '微软雅黑', sans-serif;
  font-size: 12px;
  overflow-x: auto;
}

.excel-sheet {
  margin-bottom: 16px;
}

.sheet-name {
  font-weight: bold;
  padding: 6px 12px;
  background: #f5f7fa;
  border: 1px solid #e4e7ed;
  border-bottom: none;
}

.excel-content :deep(table) {
  border-collapse: collapse;
  width: 100%;
}

.excel-content :deep(td),
.excel-content :deep(th) {
  border: 1px solid #d0d7de;
  padding: 4px 8px;
  min-width: 80px;
}

/* PDF */
.pdf-frame {
  width: 100%;
  height: 600px;
  border: none;
}
</style>
