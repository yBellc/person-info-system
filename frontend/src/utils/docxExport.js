import {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  WidthType, AlignmentType, BorderStyle, HeadingLevel, ShadingType,
  PageBreak, Footer, Header, PageNumber, TabStopType, TabStopPosition,
} from 'docx'
import { saveAs } from 'file-saver'

// ===== 通用样式常量 =====
const FONT = 'Microsoft YaHei'
const COLOR_PRIMARY = '2D5A27'
const COLOR_ACCENT = 'C4A000'
const COLOR_DARK = '1A2B1E'
const COLOR_TEXT = '333333'
const COLOR_MUTED = '666666'
const COLOR_BORDER = 'D4D8CE'
const COLOR_HEADER_BG = 'EEF1EA'

// ===== 通用边框 =====
const thinBorder = {
  top: { style: BorderStyle.SINGLE, size: 1, color: COLOR_BORDER },
  bottom: { style: BorderStyle.SINGLE, size: 1, color: COLOR_BORDER },
  left: { style: BorderStyle.SINGLE, size: 1, color: COLOR_BORDER },
  right: { style: BorderStyle.SINGLE, size: 1, color: COLOR_BORDER },
}

const noBorder = {
  top: { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' },
  bottom: { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' },
  left: { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' },
  right: { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' },
}

// ===== 辅助函数 =====
function txt(text, opts = {}) {
  return new TextRun({
    text: String(text ?? ''),
    font: FONT,
    size: opts.size || 22,
    bold: opts.bold || false,
    color: opts.color || COLOR_TEXT,
    italics: opts.italics || false,
  })
}

function para(runs, opts = {}) {
  return new Paragraph({
    children: Array.isArray(runs) ? runs : [runs],
    alignment: opts.alignment || AlignmentType.LEFT,
    spacing: opts.spacing || { before: 80, after: 80 },
    indent: opts.indent,
  })
}

function headerCell(text, width) {
  return new TableCell({
    width: width ? { size: width, type: WidthType.PERCENTAGE } : undefined,
    shading: { type: ShadingType.CLEAR, fill: COLOR_HEADER_BG },
    children: [para(txt(text, { bold: true, color: COLOR_DARK, size: 22 }), { alignment: AlignmentType.CENTER })],
    borders: thinBorder,
  })
}

function dataCell(text, opts = {}) {
  return new TableCell({
    width: opts.width ? { size: opts.width, type: WidthType.PERCENTAGE } : undefined,
    children: [para(txt(text, { size: 22, color: opts.color || COLOR_TEXT }), { alignment: opts.alignment || AlignmentType.LEFT })],
    borders: thinBorder,
  })
}

// ===== 导出记账凭证 =====
export async function exportVoucherDocx(row, voucher) {
  const lines = voucher?.lines || []
  const totalDebit = lines.reduce((s, l) => s + (parseFloat(l.debit) || 0), 0)
  const totalCredit = lines.reduce((s, l) => s + (parseFloat(l.credit) || 0), 0)

  const lineRows = lines.map((l, i) => new TableRow({
    children: [
      dataCell(String(i + 1), { alignment: AlignmentType.CENTER, width: 8 }),
      dataCell(l.summary || '', { width: 25 }),
      dataCell(l.subject_code || '', { alignment: AlignmentType.CENTER, width: 12 }),
      dataCell(l.subject_name || '', { width: 20 }),
      dataCell(l.debit ? parseFloat(l.debit).toFixed(2) : '', { alignment: AlignmentType.RIGHT, width: 12 }),
      dataCell(l.credit ? parseFloat(l.credit).toFixed(2) : '', { alignment: AlignmentType.RIGHT, width: 12 }),
    ],
  }))

  // 合计行
  lineRows.push(new TableRow({
    children: [
      new TableCell({
        children: [para(txt('合计', { bold: true, color: COLOR_DARK }), { alignment: AlignmentType.CENTER })],
        columnSpan: 4,
        shading: { type: ShadingType.CLEAR, fill: COLOR_HEADER_BG },
        borders: thinBorder,
      }),
      dataCell(totalDebit.toFixed(2), { alignment: AlignmentType.RIGHT, color: COLOR_DARK }),
      dataCell(totalCredit.toFixed(2), { alignment: AlignmentType.RIGHT, color: COLOR_DARK }),
    ],
  }))

  const voucherTable = new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    rows: [
      new TableRow({
        children: [
          headerCell('序号', 8),
          headerCell('摘要', 25),
          headerCell('科目编码', 12),
          headerCell('科目名称', 20),
          headerCell('借方金额', 12),
          headerCell('贷方金额', 12),
        ],
      }),
      ...lineRows,
    ],
  })

  const doc = new Document({
    sections: [{
      properties: {
        page: { margin: { top: 1440, bottom: 1440, left: 1080, right: 1080 } },
      },
      headers: {
        default: new Header({
          children: [para(txt('单位内部信息管理系统 · 记账凭证', { size: 18, color: COLOR_MUTED }), { alignment: AlignmentType.RIGHT })],
        }),
      },
      footers: {
        default: new Footer({
          children: [new Paragraph({
            children: [txt('第 ', { size: 18, color: COLOR_MUTED }), txt('', { size: 18 }), txt(' 页', { size: 18, color: COLOR_MUTED })],
            alignment: AlignmentType.CENTER,
          })],
        }),
      },
      children: [
        // 标题
        new Paragraph({
          children: [txt('记 账 凭 证', { bold: true, size: 36, color: COLOR_PRIMARY })],
          alignment: AlignmentType.CENTER,
          spacing: { before: 200, after: 200 },
        }),
        // 凭证信息表
        new Table({
          width: { size: 100, type: WidthType.PERCENTAGE },
          borders: noBorder,
          rows: [
            new TableRow({
              children: [
                new TableCell({
                  children: [para([txt('凭证编号：', { bold: true }), txt(voucher?.voucher_no || `V-${row.id}`)])],
                  borders: noBorder,
                }),
                new TableCell({
                  children: [para([txt('日期：', { bold: true }), txt(voucher?.voucher_date || row.created_at?.slice(0, 10) || '')])],
                  borders: noBorder,
                }),
                new TableCell({
                  children: [para([txt('附单据：', { bold: true }), txt(`${voucher?.attachment_count || 1} 张`)])],
                  borders: noBorder,
                }),
              ],
            }),
          ],
        }),
        para(txt('')),
        // 明细表
        voucherTable,
        para(txt('')),
        // 金额大写
        para([
          txt('金额大写：', { bold: true, color: COLOR_DARK }),
          txt(voucher?.amount_in_words || toChineseAmount(totalDebit), { color: COLOR_DARK }),
        ]),
        para(txt('')),
        // 签字栏
        new Table({
          width: { size: 100, type: WidthType.PERCENTAGE },
          borders: noBorder,
          rows: [
            new TableRow({
              children: [
                new TableCell({ children: [para(txt('制单：' + (row.applicant_name || ''), { size: 20 }))], borders: noBorder }),
                new TableCell({ children: [para(txt('审核：', { size: 20 }))], borders: noBorder }),
                new TableCell({ children: [para(txt('记账：', { size: 20 }))], borders: noBorder }),
                new TableCell({ children: [para(txt('出纳：', { size: 20 }))], borders: noBorder }),
              ],
            }),
          ],
        }),
      ],
    }],
  })

  const blob = await Packer.toBlob(doc)
  saveAs(blob, `记账凭证_${row.id}_${Date.now()}.docx`)
}

// ===== 导出审批单 =====
export async function exportApprovalFormDocx(row) {
  const formData = row.form_data || {}
  const labelMap = {
    expense_type: '费用类型', amount: '金额', reason: '事由',
    start_date: '开始日期', end_date: '结束日期', days: '天数',
    leave_type: '请假类型', remark: '备注', seal_type: '用章类型',
    seal_reason: '用章事由', file_name: '文件名称',
    purchaser: '采购人', supplier: '供应商', items: '采购明细',
    budget: '预算', total_amount: '总金额',
  }

  // 表单数据行
  const formRows = Object.entries(formData).map(([k, v]) => {
    const label = labelMap[k] || k
    let val = v
    if (typeof v === 'object') val = JSON.stringify(v)
    return new TableRow({
      children: [
        new TableCell({
          width: { size: 25, type: WidthType.PERCENTAGE },
          shading: { type: ShadingType.CLEAR, fill: COLOR_HEADER_BG },
          children: [para(txt(label, { bold: true, color: COLOR_DARK }), { alignment: AlignmentType.CENTER })],
          borders: thinBorder,
        }),
        dataCell(val ?? '—', { width: 75 }),
      ],
    })
  })

  const formTable = new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    rows: formRows.length > 0 ? formRows : [
      new TableRow({
        children: [new TableCell({
          children: [para(txt('暂无表单数据', { color: COLOR_MUTED }), { alignment: AlignmentType.CENTER })],
          columnSpan: 2,
          borders: thinBorder,
        })],
      }),
    ],
  })

  // 审批流程行
  const nodes = row.nodes || []
  const nodeRows = nodes.map((n, i) => {
    const statusText = n.status === 'approved' ? '✓ 已通过' : n.status === 'rejected' ? '✗ 已拒绝' : n.status === 'done' ? '✓ 已处理' : n.status === 'skipped' ? '⊘ 已跳过' : '待处理'
    const statusColor = n.status === 'approved' || n.status === 'done' ? '2E7D32' : n.status === 'rejected' ? 'B71C1C' : 'E65100'
    return new TableRow({
      children: [
        dataCell(String(i + 1), { alignment: AlignmentType.CENTER }),
        dataCell(n.node_name || '节点'),
        dataCell(n.handler_name || '—', { alignment: AlignmentType.CENTER }),
        dataCell(statusText, { alignment: AlignmentType.CENTER, color: statusColor }),
        dataCell(n.opinion || '—'),
        dataCell(n.handled_at ? n.handled_at.slice(0, 19).replace('T', ' ') : '—', { alignment: AlignmentType.CENTER, color: COLOR_MUTED }),
      ],
    })
  })

  const approvalTable = new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    rows: [
      new TableRow({
        children: [
          headerCell('步骤', 8),
          headerCell('节点', 15),
          headerCell('审批人', 15),
          headerCell('结果', 12),
          headerCell('审批意见', 30),
          headerCell('时间', 20),
        ],
      }),
      ...(nodeRows.length > 0 ? nodeRows : [new TableRow({
        children: [new TableCell({
          children: [para(txt('暂无审批记录', { color: COLOR_MUTED }), { alignment: AlignmentType.CENTER })],
          columnSpan: 6,
          borders: thinBorder,
        })],
      })]),
    ],
  })

  // 基本信息表
  const statusText = row.status === 'approved' ? '已通过' : row.status === 'rejected' ? '已拒绝' : row.status === 'pending' ? '审批中' : row.status
  const statusColor = row.status === 'approved' ? '2E7D32' : row.status === 'rejected' ? 'B71C1C' : 'E65100'

  const infoTable = new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    rows: [
      new TableRow({
        children: [
          new TableCell({
            width: { size: 20, type: WidthType.PERCENTAGE },
            shading: { type: ShadingType.CLEAR, fill: COLOR_HEADER_BG },
            children: [para(txt('标题', { bold: true, color: COLOR_DARK }), { alignment: AlignmentType.CENTER })],
            borders: thinBorder,
          }),
          new TableCell({
            width: { size: 80, type: WidthType.PERCENTAGE },
            children: [para(txt(row.title || '—'))],
            borders: thinBorder,
            columnSpan: 3,
          }),
        ],
      }),
      new TableRow({
        children: [
          new TableCell({
            shading: { type: ShadingType.CLEAR, fill: COLOR_HEADER_BG },
            children: [para(txt('流程类型', { bold: true, color: COLOR_DARK }), { alignment: AlignmentType.CENTER })],
            borders: thinBorder,
          }),
          dataCell(row.template_name || '—'),
          new TableCell({
            shading: { type: ShadingType.CLEAR, fill: COLOR_HEADER_BG },
            children: [para(txt('状态', { bold: true, color: COLOR_DARK }), { alignment: AlignmentType.CENTER })],
            borders: thinBorder,
          }),
          dataCell(statusText, { color: statusColor, bold: true }),
        ],
      }),
      new TableRow({
        children: [
          new TableCell({
            shading: { type: ShadingType.CLEAR, fill: COLOR_HEADER_BG },
            children: [para(txt('申请人', { bold: true, color: COLOR_DARK }), { alignment: AlignmentType.CENTER })],
            borders: thinBorder,
          }),
          dataCell(row.applicant_name || '—'),
          new TableCell({
            shading: { type: ShadingType.CLEAR, fill: COLOR_HEADER_BG },
            children: [para(txt('提交时间', { bold: true, color: COLOR_DARK }), { alignment: AlignmentType.CENTER })],
            borders: thinBorder,
          }),
          dataCell(row.submitted_at?.slice(0, 19).replace('T', ' ') || row.created_at?.slice(0, 19).replace('T', ' ') || '—'),
        ],
      }),
      ...(row.finished_at ? [new TableRow({
        children: [
          new TableCell({
            shading: { type: ShadingType.CLEAR, fill: COLOR_HEADER_BG },
            children: [para(txt('完成时间', { bold: true, color: COLOR_DARK }), { alignment: AlignmentType.CENTER })],
            borders: thinBorder,
          }),
          new TableCell({
            children: [para(txt(row.finished_at?.slice(0, 19).replace('T', ' ')))],
            borders: thinBorder,
            columnSpan: 3,
          }),
        ],
      })] : []),
    ],
  })

  const doc = new Document({
    sections: [{
      properties: {
        page: { margin: { top: 1440, bottom: 1440, left: 1080, right: 1080 } },
      },
      headers: {
        default: new Header({
          children: [para(txt('单位内部信息管理系统 · 审批单', { size: 18, color: COLOR_MUTED }), { alignment: AlignmentType.RIGHT })],
        }),
      },
      footers: {
        default: new Footer({
          children: [new Paragraph({
            children: [txt('系统生成时间：' + new Date().toLocaleString('zh-CN'), { size: 18, color: COLOR_MUTED })],
            alignment: AlignmentType.CENTER,
          })],
        }),
      },
      children: [
        // 标题
        new Paragraph({
          children: [txt('审 批 单', { bold: true, size: 36, color: COLOR_PRIMARY })],
          alignment: AlignmentType.CENTER,
          spacing: { before: 200, after: 300 },
        }),
        // 基本信息
        infoTable,
        para(txt('')),
        // 表单数据标题
        new Paragraph({
          children: [txt('📋 表单数据', { bold: true, size: 26, color: COLOR_DARK })],
          spacing: { before: 200, after: 100 },
          border: { bottom: { style: BorderStyle.SINGLE, size: 2, color: COLOR_PRIMARY } },
        }),
        formTable,
        para(txt('')),
        // 审批流程标题
        new Paragraph({
          children: [txt('📝 审批流程', { bold: true, size: 26, color: COLOR_DARK })],
          spacing: { before: 200, after: 100 },
          border: { bottom: { style: BorderStyle.SINGLE, size: 2, color: COLOR_PRIMARY } },
        }),
        approvalTable,
        para(txt('')),
        para(txt('')),
        // 签字栏
        new Table({
          width: { size: 100, type: WidthType.PERCENTAGE },
          borders: noBorder,
          rows: [
            new TableRow({
              children: [
                new TableCell({ children: [para(txt('申请人签字：' + (row.applicant_name || ''), { size: 22 }))], borders: noBorder }),
                new TableCell({ children: [para(txt('日期：' + (row.created_at?.slice(0, 10) || ''), { size: 22 }))], borders: noBorder }),
                new TableCell({ children: [para(txt('单位盖章：', { size: 22 }))], borders: noBorder }),
              ],
            }),
          ],
        }),
      ],
    }],
  })

  const blob = await Packer.toBlob(doc)
  saveAs(blob, `审批单_${row.id}_${Date.now()}.docx`)
}

// ===== 金额转中文大写 =====
function toChineseAmount(num) {
  if (!num || num === 0) return '零元整'
  const cnNums = ['零', '壹', '贰', '叁', '肆', '伍', '陆', '柒', '捌', '玖']
  const cnIntRadice = ['', '拾', '佰', '仟', '万', '拾', '佰', '仟', '亿']
  const cnDecRadice = ['角', '分']
  const integerPart = Math.floor(Math.abs(num))
  const decimalPart = Math.round((Math.abs(num) - integerPart) * 100)
  let result = ''
  if (integerPart > 0) {
    const intStr = String(integerPart)
    let zeroCount = 0
    for (let i = 0; i < intStr.length; i++) {
      const n = parseInt(intStr[i])
      const p = intStr.length - i - 1
      const q = p % 4
      if (n === 0) {
        zeroCount++
      } else {
        if (zeroCount > 0) result += cnNums[0]
        zeroCount = 0
        result += cnNums[n] + cnIntRadice[p]
      }
      if (q === 0 && zeroCount < 4) result += cnIntRadice[p / 4 + 3] || ''
    }
    result += '元'
  }
  if (decimalPart > 0) {
    const decStr = String(decimalPart).padStart(2, '0')
    if (decStr[0] !== '0') result += cnNums[parseInt(decStr[0])] + cnDecRadice[0]
    if (decStr[1] !== '0') result += cnNums[parseInt(decStr[1])] + cnDecRadice[1]
  } else {
    result += '整'
  }
  return result
}
