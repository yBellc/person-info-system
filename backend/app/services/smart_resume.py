"""智能简历识别服务

核心能力：
1. 自动识别 docx/xlsx 简历中的字段，无需用户预先配置映射模板
2. 通过关键字匹配 + 位置启发式（标签右方/下方为值）提取结构化数据
3. 支持扁平字段（姓名、身份证、学历等）和列表字段（家庭成员、教育经历等）
4. 数据清洗（日期归一化、手机号校验、性别/政治面貌标准化）
5. 支持 docx 段落文本的正则提取（非表格简历也能识别）

识别策略：
- 扁平字段：扫描所有单元格文本，匹配到关键字后取相邻单元格的值
  - 如果是"姓名: 张三"格式，取冒号后的内容
  - 如果是表格中的"label | value"并排，取右方单元格
  - 如果是表格中的"label / value"上下，取下方单元格
- 段落文本：对 docx 的 paragraphs 做正则提取，补充表格未覆盖的字段
- 列表字段：找到表头关键字（如"姓名|关系|单位"），从下一行开始按列提取
"""
import re
from datetime import datetime, date
from pathlib import Path
from typing import Optional

from app.services.resume_parser import (
    parse_document_to_grids, clean_value, _normalize_date,
)


# ==================== 字段关键字配置 ====================

# 扁平字段：关键字列表 -> 系统字段key
# 按优先级排序，前面的是首选关键字
FIELD_KEYWORDS = {
    "name": ["姓名", "名字", "Name", "name"],
    "gender": ["性别", "Gender", "sex", "Sex"],
    "birth_date": ["出生年月", "出生日期", "生日", "出生", "Birthday", "birthdate"],
    "id_card": ["身份证号", "身份证号码", "身份证", "证件号码", "身份证证件号", "ID"],
    "ethnicity": ["民族", "族别"],
    "native_place": ["籍贯", "户籍", "户籍地"],
    "birth_place": ["出生地", "出生地址", "祖籍"],
    "political_status": ["政治面貌", "政治面目"],
    "party_join_date": ["入党时间", "入党日期", "入党年月"],
    "party_apply_date": ["申请入党时间", "递交入党申请书时间"],
    "phone": ["手机", "手机号码", "手机号", "联系电话", "电话", "移动电话", "Phone", "Mobile"],
    "office_phone": ["办公电话", "办公座机", "办公"],
    "emergency_contact": ["紧急联系人", "应急联系人"],
    "education_level": ["学历", "文化程度", "最高学历", "最高文化程度"],
    "degree": ["学位", "学位级别"],
    "school": ["毕业院校", "院校", "学校", "毕业学校"],
    "major": ["专业", "所学专业"],
    "graduation_date": ["毕业时间", "毕业日期", "毕业年月"],
    "marital_status": ["婚姻状况", "婚否", "婚姻"],
    "spouse_name": ["配偶姓名", "配偶", "爱人姓名"],
    "children_count": ["子女数", "子女数量", "子女情况"],
    "home_address": ["家庭住址", "住址", "家庭地址", "通讯地址"],
    "department": ["部门", "所在部门", "科室", "处室"],
    "position": ["岗位", "职务", "职位", "行政职务"],
    "rank": ["职级", "级别"],
    "work_start_date": ["参加工作时间", "参加工作日期", "参加工作", "参加工作年月"],
    "join_unit_date": ["入职时间", "入职日期", "进本单位时间", "入职", "入职本单位时间"],
}

# 关键字否定前缀：避免"姓名"匹配到"家庭成员姓名"等场景
# 如果单元格文本在关键字前面出现了这些前缀，则不算匹配
FIELD_NEGATIVE_PREFIXES = {
    "name": ["家庭成员", "成员", "配偶", "证明人", "父母", "联系人", "爱人", "紧急联系"],
    "phone": ["办公", "家庭", "紧急联系"],
    "position": ["配偶", "家庭成员", "父亲", "母亲", "爱人"],
    "work_unit": ["配偶", "父亲", "母亲", "家庭"],
}

# 性别标准化
_GENDER_MAP = {
    "男": "男", "male": "男", "m": "男", "Male": "男",
    "女": "女", "female": "女", "f": "女", "Female": "女",
}

# 政治面貌标准化
_POLITICAL_MAP = {
    "党员": "中共党员", "中共党员": "中共党员", "共产党员": "中共党员",
    "预备党员": "中共预备党员", "中共预备党员": "中共预备党员",
    "团员": "共青团员", "共青团员": "共青团员",
    "群众": "群众", "市民": "群众",
    "民主党派": "民主党派", "无党派": "无党派人士", "无党派人士": "无党派人士",
}

# 婚姻状况标准化
_MARITAL_MAP = {
    "未婚": "未婚", "已婚": "已婚", "丧偶": "丧偶", "离婚": "离婚", "离异": "离婚",
}

# 日期字段集合
_DATE_FIELDS = {
    "birth_date", "party_join_date", "party_apply_date",
    "work_start_date", "join_unit_date", "graduation_date",
}

# 列表字段表头关键字
_LIST_GROUP_HEADERS = {
    "family_members": {
        "name": "家庭成员",
        "header_keywords": [["家庭成员姓名", "成员姓名", "姓名"], ["关系", "称谓"], ["工作单位", "单位"], ["职务", "岗位"], ["联系电话", "电话"]],
        "field_keys": ["name", "relationship", "work_unit", "position", "phone"],
    },
    "education_records": {
        "name": "教育经历",
        "header_keywords": [["起始时间", "开始时间", "从"], ["终止时间", "结束时间", "至"], ["学校", "院校"], ["专业"], ["学历", "文化程度"], ["学位"]],
        "field_keys": ["start_date", "end_date", "school", "major", "education_level", "degree"],
    },
    "work_records": {
        "name": "工作经历",
        "header_keywords": [["起始时间", "开始时间", "从"], ["终止时间", "结束时间", "至"], ["工作单位", "单位"], ["职务", "岗位"], ["证明人"]],
        "field_keys": ["start_date", "end_date", "work_unit", "position", "witness"],
    },
}


# ==================== 智能提取主函数 ====================

def smart_parse_resume(file_path: str, ext: str = None) -> dict:
    """智能解析简历，自动识别字段

    Args:
        file_path: 简历文件路径
        ext: 文件扩展名，None 则自动推断

    Returns:
        {
            "flat_fields": {field_key: value, ...},
            "sub_tables": {table_name: [{...}, ...], ...},
            "raw_text": "全文文本（用于调试）",
            "grids_count": 网格数量,
        }
    """
    if ext is None:
        ext = Path(file_path).suffix.lower()

    grids = parse_document_to_grids(file_path, ext)

    flat_fields = {}
    sub_tables = {}
    all_text_parts = []

    for grid_info in grids:
        grid = grid_info["grid"]
        if not grid:
            continue

        # 收集全文文本
        for row in grid:
            for cell in row:
                if cell:
                    all_text_parts.append(cell)

        # 提取扁平字段
        flat = _extract_flat_fields_from_grid(grid)
        for k, v in flat.items():
            if v and k not in flat_fields:
                flat_fields[k] = v

        # 提取列表字段
        lists = _extract_list_groups_from_grid(grid)
        for table_key, items in lists.items():
            if items:
                if table_key not in sub_tables:
                    sub_tables[table_key] = []
                sub_tables[table_key].extend(items)

    # 从 docx 段落文本补充提取（非表格简历也能识别）
    paragraph_text = ""
    if ext == ".docx":
        paragraph_text = _extract_docx_paragraphs(file_path)
        if paragraph_text:
            all_text_parts.append(paragraph_text)
            # 正则提取补充字段（只填表格未提取到的）
            text_flat = _extract_flat_fields_from_text(paragraph_text)
            for k, v in text_flat.items():
                if v and k not in flat_fields:
                    flat_fields[k] = v
            # 从文本中提取列表字段
            text_lists = _extract_list_groups_from_text(paragraph_text)
            for table_key, items in text_lists.items():
                if items:
                    if table_key not in sub_tables:
                        sub_tables[table_key] = []
                    sub_tables[table_key].extend(items)

    # 后处理：标准化字段值
    flat_fields = _normalize_fields(flat_fields)

    return {
        "flat_fields": flat_fields,
        "sub_tables": sub_tables,
        "raw_text": "\n".join(all_text_parts)[:5000],  # 限制长度
        "grids_count": len(grids),
    }


# ==================== docx 段落文本提取 ====================

def _extract_docx_paragraphs(file_path: str) -> str:
    """提取 docx 的所有段落文本（包括段落内的文本框）

    python-docx 的 doc.paragraphs 只返回正文段落，
    不含表格内文本（表格已由 grid 单独处理）。
    """
    try:
        from docx import Document
        doc = Document(file_path)
        parts = []
        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                parts.append(text)
        # 也提取页眉页脚
        for section in doc.sections:
            for header_footer in [section.header, section.footer]:
                if header_footer:
                    for para in header_footer.paragraphs:
                        text = para.text.strip()
                        if text:
                            parts.append(text)
        return "\n".join(parts)
    except Exception:
        return ""


# ==================== 从纯文本提取字段 ====================

def _extract_flat_fields_from_text(text: str) -> dict:
    """从纯文本中用正则提取扁平字段

    适用于段落式简历，如"姓名：张三\n性别：男"
    也支持一行多个字段，如"性别：男 出生年月：1990年1月"
    """
    result = {}
    if not text:
        return result

    for field_key, keywords in FIELD_KEYWORDS.items():
        if field_key in result:
            continue
        for kw in keywords:
            # 检查否定前缀
            # 匹配 "关键字：值" 或 "关键字:值"，值到下一个关键字或行尾
            # 使用非贪婪匹配，遇到下一个"关键字："或换行停止
            pat = rf"{re.escape(kw)}\s*[:：]\s*(.+?)(?=\n|[\u4e00-\u9fa5]{{2,}}\s*[:：]|$)"
            m = re.search(pat, text)
            if m:
                val = m.group(1).strip()
                val = val.rstrip("；;，,。.").strip()
                # 否定前缀检查
                if _has_negative_prefix(kw + "：" + val, kw, field_key):
                    continue
                # 合理长度校验
                max_len = 200 if field_key in ("home_address",) else 100
                if val and len(val) <= max_len:
                    result[field_key] = val
                    break

    # 特殊正则：身份证号（18位）
    if "id_card" not in result:
        m = re.search(r"\b(\d{17}[\dXx])\b", text)
        if m:
            result["id_card"] = m.group(1).upper()

    # 特殊正则：手机号
    if "phone" not in result:
        m = re.search(r"\b(1[3-9]\d{9})\b", text)
        if m:
            result["phone"] = m.group(1)

    return result


def _extract_list_groups_from_text(text: str) -> dict:
    """从纯文本中提取列表字段（家庭成员、教育经历、工作经历）

    策略：找到章节标题（如"家庭成员"），逐行提取直到下一个章节标题
    """
    result = {}

    # 章节标题与对应的表头关键字
    section_configs = {
        "family_members": {
            "section_titles": ["家庭成员", "家庭情况", "家庭主要成员", "主要社会关系"],
            "field_patterns": [
                ("name", r"([\u4e00-\u9fa5]{2,4})"),
                ("relationship", r"(父亲|母亲|丈夫|妻子|儿子|女儿|哥哥|弟弟|姐姐|妹妹|公公|婆婆|岳父|岳母)"),
                ("work_unit", None),  # 工作单位较难提取，留空
                ("position", None),
                ("phone", r"(1[3-9]\d{9})"),
            ],
        },
        "education_records": {
            "section_titles": ["教育经历", "教育背景", "学习经历", "学历经历"],
            "field_patterns": [
                ("start_date", r"(\d{4}[-/.年]\d{1,2}月?)"),
                ("end_date", r"(至|—|-)\s*(\d{4}[-/.年]\d{1,2}月?)"),
                ("school", None),
                ("major", None),
                ("education_level", r"(博士|硕士|本科|大专|中专|高中)"),
                ("degree", None),
            ],
        },
        "work_records": {
            "section_titles": ["工作经历", "工作背景", "工作简历", "工作履历"],
            "field_patterns": [
                ("start_date", r"(\d{4}[-/.年]\d{1,2}月?)"),
                ("end_date", r"(至|—|-)\s*(\d{4}[-/.年]\d{1,2}月?)"),
                ("work_unit", None),
                ("position", None),
            ],
        },
    }

    lines = text.split("\n")

    for table_key, config in section_configs.items():
        section_start = -1
        section_end = len(lines)

        # 找章节起始位置
        for i, line in enumerate(lines):
            for title in config["section_titles"]:
                if title in line and len(line) < 20:
                    section_start = i + 1
                    break
            if section_start >= 0:
                break

        if section_start < 0:
            continue

        # 找章节结束位置（下一个章节标题）
        all_titles = []
        for cfg in section_configs.values():
            all_titles.extend(cfg["section_titles"])
        # 加上其他常见章节标题
        all_titles.extend(["个人简历", "基本信息", "联系方式", "自我评价", "技能", "证书"])

        for i in range(section_start, len(lines)):
            line = lines[i].strip()
            if not line:
                continue
            for title in all_titles:
                if title in line and len(line) < 20:
                    section_end = i
                    break
            else:
                continue
            break

        # 从章节行中提取数据
        items = []
        for i in range(section_start, section_end):
            line = lines[i].strip()
            if not line:
                continue

            item = {}
            # 尝试提取日期范围
            date_matches = re.findall(r"(\d{4}[-/.年]\d{1,2}月?)", line)
            if len(date_matches) >= 1:
                item["start_date"] = _normalize_date(date_matches[0])
            if len(date_matches) >= 2:
                item["end_date"] = _normalize_date(date_matches[1])

            # 提取关系（家庭成员）
            if table_key == "family_members":
                rel_match = re.search(r"(父亲|母亲|丈夫|妻子|儿子|女儿|哥哥|弟弟|姐姐|妹妹|公公|婆婆|岳父|岳母)", line)
                if rel_match:
                    item["relationship"] = rel_match.group(1)
                # 提取姓名（关系前或后的中文）
                name_match = re.search(r"[\u4e00-\u9fa5]{2,4}", line)
                if name_match:
                    name_val = name_match.group()
                    if name_val != item.get("relationship"):
                        item["name"] = name_val
                # 手机号
                phone_match = re.search(r"(1[3-9]\d{9})", line)
                if phone_match:
                    item["phone"] = phone_match.group(1)

            # 提取学历（教育经历）
            if table_key == "education_records":
                edu_match = re.search(r"(博士|硕士|本科|大专|中专|高中)", line)
                if edu_match:
                    item["education_level"] = edu_match.group(1)

            if item:
                items.append(item)

        if items:
            result[table_key] = items

    return result


# ==================== 扁平字段提取 ====================

def _has_negative_prefix(cell_text: str, keyword: str, field_key: str) -> bool:
    """检查关键字前面是否有否定前缀（如"家庭成员"在"姓名"前）"""
    prefixes = FIELD_NEGATIVE_PREFIXES.get(field_key, [])
    if not prefixes:
        return False
    idx = cell_text.find(keyword)
    if idx <= 0:
        return False
    before = cell_text[:idx]
    return any(p in before for p in prefixes)


def _extract_flat_fields_from_grid(grid: list) -> dict:
    """从单个网格中提取扁平字段

    策略：
    1. 扫描所有单元格，匹配关键字
    2. 优先级1：同单元格内的"关键字:值"格式
    3. 优先级2：右侧单元格（label | value 横向布局）
    4. 优先级3：下方单元格（label / value 纵向布局）
    """
    result = {}
    rows = len(grid)
    if rows == 0:
        return result
    cols = max((len(r) for r in grid), default=0)

    # 建立 (row, col) -> 已用 标记，避免一个值被多次匹配
    used_cells = set()

    for r in range(rows):
        for c in range(min(len(grid[r]), cols)):
            cell_text = grid[r][c].strip() if c < len(grid[r]) else ""
            if not cell_text:
                continue

            # 策略1：同单元格内 "关键字:值" 或 "关键字：值"
            for field_key, keywords in FIELD_KEYWORDS.items():
                if field_key in result:
                    continue
                for kw in keywords:
                    # 否定前缀检查：跳过"家庭成员姓名"等误匹配
                    if _has_negative_prefix(cell_text, kw, field_key):
                        continue
                    # 匹配 "关键字:值" 或 "关键字：值"
                    patterns = [
                        rf"{re.escape(kw)}\s*[:：]\s*(.+)",
                        rf"(?:^|\n|[\s，,；;。.、]){re.escape(kw)}\s*[:：]\s*(.+)",
                    ]
                    for pat in patterns:
                        m = re.search(pat, cell_text)
                        if m:
                            val = m.group(1).strip()
                            val = val.rstrip("；;，,。.").strip()
                            if val and len(val) <= 100:  # 合理长度
                                result[field_key] = val
                                used_cells.add((r, c))
                                break
                    if field_key in result:
                        break

            if (r, c) in used_cells:
                continue

            # 策略2：当前格是纯标签（长度短、无冒号值），找右侧
            if len(cell_text) <= 12 and ":" not in cell_text and "：" not in cell_text:
                for field_key, keywords in FIELD_KEYWORDS.items():
                    if field_key in result:
                        continue
                    for kw in keywords:
                        # 否定前缀检查
                        if _has_negative_prefix(cell_text, kw, field_key):
                            continue
                        if cell_text == kw or cell_text == kw + "：" or cell_text == kw + ":":
                            # 右侧单元格
                            if c + 1 < len(grid[r]):
                                val = grid[r][c + 1].strip()
                                if val and (r, c + 1) not in used_cells:
                                    result[field_key] = val
                                    used_cells.add((r, c + 1))
                                    break
                            # 下方单元格
                            elif r + 1 < rows and c < len(grid[r + 1]):
                                val = grid[r + 1][c].strip()
                                if val and (r + 1, c) not in used_cells:
                                    result[field_key] = val
                                    used_cells.add((r + 1, c))
                                    break
                    if field_key in result:
                        break

    return result


# ==================== 列表字段提取 ====================

def _extract_list_groups_from_grid(grid: list) -> dict:
    """从网格中提取列表字段（家庭成员、教育经历、工作经历）

    策略：
    1. 找到包含表头关键字的行
    2. 按表头列位置逐行提取数据
    3. 遇到空行或非数据行停止
    """
    result = {}
    rows = len(grid)
    if rows == 0:
        return result
    cols = max((len(r) for r in grid), default=0)

    for table_key, config in _LIST_GROUP_HEADERS.items():
        header_keywords = config["header_keywords"]
        field_keys = config["field_keys"]

        # 找表头行：该行需要匹配至少2个关键字组
        header_row_idx = -1
        col_mapping = {}  # col_index -> field_key

        for r in range(rows):
            matched_cols = {}
            for col_idx in range(min(len(grid[r]), cols)):
                cell = grid[r][col_idx].strip() if col_idx < len(grid[r]) else ""
                if not cell:
                    continue
                for fk_idx, kw_group in enumerate(header_keywords):
                    if fk_idx in matched_cols.values():
                        continue
                    for kw in kw_group:
                        if kw in cell or cell in kw:
                            matched_cols[col_idx] = field_keys[fk_idx]
                            break

            # 至少匹配2列才算表头
            if len(matched_cols) >= 2:
                header_row_idx = r
                col_mapping = matched_cols
                break

        if header_row_idx < 0:
            continue

        # 从表头下一行开始提取数据
        items = []
        for r in range(header_row_idx + 1, rows):
            item = {}
            row_has_data = False
            for col_idx, field_key in col_mapping.items():
                if col_idx >= len(grid[r]):
                    continue
                val = grid[r][col_idx].strip()
                if val:
                    val = clean_value(val, field_key)
                    item[field_key] = val
                    row_has_data = True

            if row_has_data:
                # 跳过明显是备注或下一节标题的行
                first_val = next(iter(item.values()), "")
                if len(first_val) > 50 and not any(c.isdigit() for c in first_val):
                    # 可能是下一节标题，停止
                    break
                items.append(item)
            else:
                # 空行：如果已收集到数据则停止
                if items:
                    break

        if items:
            result[table_key] = items

    return result


# ==================== 字段标准化 ====================

def _normalize_fields(fields: dict) -> dict:
    """标准化字段值"""
    result = dict(fields)

    # 性别
    if "gender" in result:
        g = result["gender"].strip()
        result["gender"] = _GENDER_MAP.get(g, g if g in ("男", "女") else "")

    # 政治面貌
    if "political_status" in result:
        p = result["political_status"].strip()
        result["political_status"] = _POLITICAL_MAP.get(p, p)

    # 婚姻状况
    if "marital_status" in result:
        m = result["marital_status"].strip()
        result["marital_status"] = _MARITAL_MAP.get(m, m)

    # 日期字段归一化
    for key in _DATE_FIELDS:
        if key in result and result[key]:
            result[key] = _normalize_date(result[key])

    # 子女数转整数
    if "children_count" in result and result["children_count"]:
        try:
            result["children_count"] = int(re.search(r"\d+", str(result["children_count"])).group())
        except (AttributeError, ValueError):
            result.pop("children_count", None)

    # 身份证号清洗：只保留18位
    if "id_card" in result and result["id_card"]:
        id_val = re.sub(r"\s", "", result["id_card"])
        m = re.search(r"\d{17}[\dXx]", id_val)
        if m:
            result["id_card"] = m.group().upper()
        else:
            result.pop("id_card", None)

    # 手机号清洗
    if "phone" in result and result["phone"]:
        m = re.search(r"1\d{10}", result["phone"])
        if m:
            result["phone"] = m.group()
        else:
            result.pop("phone", None)

    # 去除空值
    return {k: v for k, v in result.items() if v}
