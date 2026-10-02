# -*- coding: utf-8 -*-
"""文档解析服务：将 Word/PDF/Excel 文档识别为表单字段

支持三种文档类型：
1. Word (.docx) - 提取表格、段落中的字段标签
2. Excel (.xlsx/.xls) - 提取表头行作为字段
3. PDF (.pdf) - 提取文本中的字段标签

改进：支持更多占位符模式识别、复杂表格结构、非标准布局
"""
import os
import re
import json
from typing import Optional

from app.services.field_matcher import match_field


# 占位符文本模式 - 识别为"待填写"的单元格
PLACEHOLDER_PATTERNS = [
    r'^[\s_]+$',           # 纯下划线
    r'^[_\.]{2,}$',        # 下划线或点号序列
    r'^[-—–]{2,}$',        # 破折号序列
    r'^[\?？]{1,}$',       # 问号
    r'^[（(][\s_　]*[)）]$',  # 空括号
    r'^\[[\s_　]*\]$',     # 方括号
    r'^〔[\s_　]*〕$',     # 中文方括号
    r'^[〈〈][\s_　]*[〉〉]$',  # 尖括号
    r'待填写|待填|待补充|请填写|请填|请输入|填写此处|此处填写|此处',
    r'^无$|^—$|^--$|^-$|^N/A$|^n/a$',
]


def is_placeholder(text: str) -> bool:
    """判断文本是否为占位符（应填写的区域）"""
    if not text or not text.strip():
        return True
    t = text.strip()
    for pattern in PLACEHOLDER_PATTERNS:
        if re.match(pattern, t, re.IGNORECASE):
            return True
    return False


# ===== 字段类型推断 =====
def infer_field_type(label: str, value: str = "") -> str:
    """根据字段标签和值推断字段类型"""
    label_lower = label.lower()

    # 日期类型
    date_keywords = ["日期", "时间", "出生", "入伍", "入党", "参加", "毕业", "入职", "截止"]
    for kw in date_keywords:
        if kw in label:
            return "date"

    # 数字类型
    number_keywords = ["年龄", "工龄", "党龄", "数量", "人数", "金额", "次数", "编号"]
    for kw in number_keywords:
        if kw in label:
            return "number"

    # 单选类型
    if any(kw in label for kw in ["性别", "民族", "政治面貌", "婚姻状况", "是否", "婚否"]):
        return "radio"

    # 下拉选择
    if any(kw in label for kw in ["学历", "学位", "职级", "职务", "部门", "单位"]):
        return "select"

    # 多行文本
    if any(kw in label for kw in ["说明", "备注", "描述", "地址", "简介", "总结", "意见", "原因"]):
        return "textarea"

    return "text"


# ===== 选项推断 =====
def infer_options(label: str) -> Optional[list]:
    """根据字段标签推断选项列表"""
    if "性别" in label:
        return ["男", "女"]
    if "政治面貌" in label:
        return ["中共党员", "中共预备党员", "共青团员", "群众", "民主党派", "无党派人士"]
    if "婚姻" in label or "婚否" in label:
        return ["未婚", "已婚", "离异", "丧偶"]
    if "学历" in label:
        return ["博士研究生", "硕士研究生", "大学本科", "大学专科", "高中", "其他"]
    if "是否" in label:
        return ["是", "否"]
    return None


# ===== Word 文档解析 =====
def parse_docx(file_path: str) -> dict:
    """解析 Word 文档，提取表单字段"""
    from docx import Document

    doc = Document(file_path)
    fields = []
    raw_text_parts = []

    # 1. 提取表格中的字段（多种策略）
    for table_idx, table in enumerate(doc.tables):
        _extract_fields_from_table(table, table_idx, fields)

    # 2. 提取段落中的字段（模式匹配）
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        raw_text_parts.append(text)
        # 匹配 "标签：____" 或 "标签：[   ]" 或 "标签：........." 或 "标签："
        patterns = [
            r'([^\s：:]{2,8})[：:]\s*[_\[\]〔〕\.\s]{2,}',
            r'([^\s：:]{2,8})[：:]\s*$',
            r'([^\s（(]{2,8})[（(]\s*[）)]',
            r'([^\s：:]{2,8})[：:]\s*[^\s]{1,20}(?=[_\s]|$)',  # 标签:值 模式
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                label = match.strip()
                if label and not _is_label_duplicate(label, fields):
                    fields.append({
                        "label": label,
                        "value_hint": "",
                        "source": "段落",
                    })

    # 3. 如果没识别到字段，尝试用表格结构推断
    if not fields and doc.tables:
        for table_idx, table in enumerate(doc.tables):
            if len(table.rows) >= 1:
                header_row = table.rows[0]
                for cell in header_row.cells:
                    label = cell.text.strip()
                    if label and not _is_label_duplicate(label, fields):
                        fields.append({
                            "label": label,
                            "value_hint": "",
                            "source": f"表格{table_idx + 1}-表头",
                        })

    preview = "\n".join(raw_text_parts[:30])[:2000]
    return {"fields": fields, "preview": preview, "raw_text": "\n".join(raw_text_parts)[:5000]}


def _extract_fields_from_table(table, table_idx: int, fields: list):
    """从表格中提取字段，支持多种布局策略

    策略：
    1. 标签-值 配对：奇数列是标签，偶数列是值
    2. 占位符检测：含"待填写"、下划线等的单元格相邻的标签
    3. 双列表单：左列标签、右列值
    4. 跨行合并处理
    """
    for row_idx, row in enumerate(table.rows):
        cells = [cell.text.strip() for cell in row.cells]
        non_empty_count = sum(1 for c in cells if c)

        # 策略1：检测"标签:值"模式（同一单元格内）
        for i, cell_text in enumerate(cells):
            if not cell_text:
                continue
            label = _extract_label(cell_text)
            if label and not _is_label_duplicate(label, fields):
                fields.append({
                    "label": label,
                    "value_hint": "",
                    "source": f"表格{table_idx + 1}-行{row_idx + 1}-列{i + 1}",
                })
                continue

        # 策略2：检测标签-占位符配对（标签在左/上，空单元格在右/下）
        for i, cell_text in enumerate(cells):
            if not cell_text or is_placeholder(cell_text):
                continue
            # 检查是否像标签
            label = _extract_label(cell_text)
            if not label:
                continue
            # 检查右侧单元格是否为占位符
            if i + 1 < len(cells) and is_placeholder(cells[i + 1]):
                if not _is_label_duplicate(label, fields):
                    fields.append({
                        "label": label,
                        "value_hint": cells[i + 1] if i + 1 < len(cells) else "",
                        "source": f"表格{table_idx + 1}-行{row_idx + 1}-列{i + 1}",
                    })
            # 检查下方单元格是否为占位符（仅当当前行是标签行时）
            if row_idx + 1 < len(table.rows):
                below_row = table.rows[row_idx + 1]
                below_cells = [c.text.strip() for c in below_row.cells]
                if i < len(below_cells) and is_placeholder(below_cells[i]):
                    if not _is_label_duplicate(label, fields):
                        fields.append({
                            "label": label,
                            "value_hint": below_cells[i],
                            "source": f"表格{table_idx + 1}-行{row_idx + 1}-列{i + 1}",
                        })


# ===== Excel 文档解析 =====
def parse_xlsx(file_path: str, header_row: int = 1) -> dict:
    """解析 Excel 文档，提取表头作为字段"""
    from openpyxl import load_workbook

    wb = load_workbook(file_path, read_only=True, data_only=True)
    ws = wb.active

    fields = []
    raw_text_parts = []

    for row_idx, row in enumerate(ws.iter_rows(values_only=True), 1):
        if row_idx < header_row:
            continue
        if row_idx == header_row:
            # 表头行
            for col_idx, cell in enumerate(row):
                if cell and str(cell).strip():
                    label = str(cell).strip()
                    if not _is_label_duplicate(label, fields):
                        fields.append({
                            "label": label,
                            "value_hint": "",
                            "source": f"表头-列{col_idx + 1}",
                            "col_index": col_idx,
                        })
            break  # 只取表头行

        # 收集前几行作为预览
        if row_idx <= header_row + 5:
            raw_text_parts.append(" | ".join(str(c) if c else "" for c in row))

    # 额外策略：如果表头行识别的字段太少，尝试从多行表头提取
    if len(fields) < 2 and header_row > 0:
        # 重新扫描前几行，找所有可能的表头
        for scan_row_idx in range(1, min(header_row + 3, ws.max_row + 1)):
            scan_row = list(ws.iter_rows(min_row=scan_row_idx, max_row=scan_row_idx, values_only=True))[0]
            for col_idx, cell in enumerate(scan_row):
                if cell and str(cell).strip():
                    label = str(cell).strip()
                    if 2 <= len(label) <= 20 and not _is_label_duplicate(label, fields):
                        fields.append({
                            "label": label,
                            "value_hint": "",
                            "source": f"扫描-行{scan_row_idx}-列{col_idx + 1}",
                            "col_index": col_idx,
                        })

    wb.close()

    preview = "\n".join(raw_text_parts[:20])[:2000]
    return {"fields": fields, "preview": preview, "raw_text": preview}


# ===== PDF 文档解析 =====
def parse_pdf(file_path: str) -> dict:
    """解析 PDF 文档，提取文本中的字段"""
    try:
        import pdfplumber
    except ImportError:
        return {"fields": [], "preview": "PDF解析需要安装pdfplumber: pip install pdfplumber", "raw_text": ""}

    fields = []
    raw_text_parts = []

    with pdfplumber.open(file_path) as pdf:
        for page_idx, page in enumerate(pdf.pages[:5]):  # 只解析前5页
            text = page.extract_text()
            if not text:
                continue
            raw_text_parts.append(text)

            # 提取表格中的字段
            tables = page.extract_tables()
            for table_idx, table in enumerate(tables):
                for row_idx, row in enumerate(table):
                    for i, cell in enumerate(row):
                        if not cell:
                            continue
                        cell_text = str(cell).strip()
                        label = _extract_label(cell_text)
                        if label and not _is_label_duplicate(label, fields):
                            fields.append({
                                "label": label,
                                "value_hint": str(row[i + 1]) if i + 1 < len(row) and is_placeholder(str(row[i + 1])) else "",
                                "source": f"第{page_idx + 1}页-表格{table_idx + 1}",
                            })

            # 提取段落中的字段
            for line in text.split("\n"):
                line = line.strip()
                if not line:
                    continue
                patterns = [
                    r'([^\s：:]{2,8})[：:]\s*[_\[\]〔〕\.\s]{2,}',
                    r'([^\s：:]{2,8})[：:]\s*$',
                    r'([^\s（(]{2,8})[（(]\s*[）)]',
                    r'([^\s：:]{2,8})[：:]\s*[^\s]{1,20}(?=[_\s]|$)',
                ]
                for pattern in patterns:
                    matches = re.findall(pattern, line)
                    for match in matches:
                        label = match.strip()
                        if label and not _is_label_duplicate(label, fields):
                            fields.append({
                                "label": label,
                                "value_hint": "",
                                "source": f"第{page_idx + 1}页",
                            })

    full_text = "\n".join(raw_text_parts)
    preview = full_text[:2000]
    return {"fields": fields, "preview": preview, "raw_text": full_text[:5000]}


# ===== 辅助函数 =====
def _extract_label(text: str) -> str:
    """从单元格文本中提取字段标签"""
    text = text.strip()
    # 移除尾部的冒号和填充符
    text = re.sub(r'[：:]\s*$', '', text)
    text = re.sub(r'[_\.\s]+$', '', text)
    # 移除括号内容
    text = re.sub(r'[（(].*?[）)]', '', text)
    text = text.strip()
    # 只保留2-20个字符的中文/英文标签
    if 2 <= len(text) <= 20 and re.match(r'^[\u4e00-\u9fa5a-zA-Z0-9（）()]+$', text):
        return text
    return ""


def _is_label_duplicate(label: str, existing_fields: list) -> bool:
    """检查标签是否已存在"""
    return any(f["label"] == label for f in existing_fields)


# ===== 主入口：解析文档并智能匹配 =====
def parse_document(file_path: str, file_type: str, header_row: int = 1, custom_fields: dict = None) -> dict:
    """解析文档，提取字段并智能匹配系统字段

    Args:
        file_path: 文件路径
        file_type: 文件类型 (docx/pdf/xlsx)
        header_row: Excel表头行号
        custom_fields: 自定义字段 {key: display_name}

    Returns:
        {
            "fields": [{label, field_type, options, auto_fill_key, confidence, is_required, ...}],
            "preview": "原文预览",
            "source_type": "docx",
        }
    """
    file_type = file_type.lower().lstrip(".")

    # 解析文档
    if file_type == "docx":
        raw = parse_docx(file_path)
    elif file_type in ("xlsx", "xls"):
        raw = parse_xlsx(file_path, header_row=header_row)
    elif file_type == "pdf":
        raw = parse_pdf(file_path)
    else:
        return {"fields": [], "preview": f"不支持的文件类型: {file_type}", "raw_text": ""}

    # 智能匹配系统字段
    result_fields = []
    for idx, f in enumerate(raw["fields"]):
        label = f["label"]
        field_type = infer_field_type(label, f.get("value_hint", ""))
        options = infer_options(label)

        # 匹配系统字段（用于自动填充）
        system_key, confidence = match_field(label, custom_fields)

        result_fields.append({
            "field_key": f"field_{idx + 1}",
            "field_label": label,
            "field_type": field_type,
            "field_options": options,
            "is_required": confidence >= 0.8,
            "is_readonly": bool(system_key) and confidence >= 0.9,
            "auto_fill_key": system_key if confidence >= 0.6 else None,
            "confidence": round(confidence, 3),
            "default_value": "",
            "sort_order": idx,
            "placeholder": f"请输入{label}",
            "source": f.get("source", ""),
        })

    return {
        "fields": result_fields,
        "preview": raw.get("preview", ""),
        "source_type": file_type,
        "total_fields": len(result_fields),
        "auto_filled_fields": sum(1 for f in result_fields if f["auto_fill_key"]),
    }
