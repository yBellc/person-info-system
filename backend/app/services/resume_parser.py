"""简历表解析服务（模块 5）

核心能力：
1. 把 docx/xlsx 表格解析为行列网格（grid），正确处理合并单元格
2. 按字段-单元格坐标映射提取结构化人员数据
3. 列表组（子表）按行高推算逐行提取
4. 数据清洗（去空格换行、日期归一化、手机号校验）
"""
import re
from datetime import datetime, date
from pathlib import Path
from typing import Optional

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
from docx import Document
from difflib import SequenceMatcher

# Word XML 命名空间
_W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_W = "{%s}" % _W_NS


# ==================== 表格解析为网格 ====================

def parse_docx_to_grids(file_path: str) -> list:
    """解析 docx 的所有表格为行列网格

    Returns:
        [{name, rows, cols, grid, merged_cells}]
        grid[row][col] = 文本
        merged_cells: [{row, col, rowspan, colspan}] 合并单元格主格信息
    """
    doc = Document(file_path)
    result = []
    for ti, table in enumerate(doc.tables):
        grid, merged_cells = _docx_table_to_grid(table)
        rows = len(grid)
        cols = max((len(r) for r in grid), default=0)
        result.append({
            "name": f"表格{ti + 1}",
            "rows": rows,
            "cols": cols,
            "grid": grid,
            "merged_cells": merged_cells,
        })
    return result


def _docx_table_to_grid(table) -> tuple:
    """将单个 docx table 转为网格，正确处理合并单元格。

    直接解析底层 XML 的 <w:gridSpan>（横向合并）和 <w:vMerge>（纵向合并），
    这是 Word 表格结构的权威来源，比 python-docx 高层 cell API 可靠。

    算法：
    1. 遍历每个 <w:tr> 行和其中的 <w:tc> 单元格
    2. 跳过已被合并占用的网格位置（用 occupied 集合记录）
    3. 读 gridSpan 得横向跨度，读 vMerge 判断纵向合并
    4. vMerge restart 是主格，后续 vMerge（无 val）是延续格
    """
    tbl = table._tbl
    trs = tbl.findall(f"{_W}tr")
    rows = len(trs)

    # 先确定列数（取 tblGrid 或所有行的最大格数，考虑 gridSpan）
    cols = 0
    for tr in trs:
        row_cols = 0
        for tc in tr.findall(f"{_W}tc"):
            tcPr = tc.find(f"{_W}tcPr")
            gridSpan = 1
            if tcPr is not None:
                gs = tcPr.find(f"{_W}gridSpan")
                if gs is not None:
                    try:
                        gridSpan = int(gs.get(f"{_W}val", "1"))
                    except ValueError:
                        gridSpan = 1
            row_cols += gridSpan
        cols = max(cols, row_cols)

    grid = [["" for _ in range(cols)] for _ in range(rows)]
    merged_cells = []
    # occupied[r][c] = True 表示被某个合并单元格占用（非主格位置）
    occupied = [[False] * cols for _ in range(rows)]
    # 记录每个待延续的纵向合并：列号 -> (起始行, 主格文本)
    vmerge_open = {}

    for ri, tr in enumerate(trs):
        ci = 0  # 当前网格列游标
        for tc in tr.findall(f"{_W}tc"):
            # 跳过被占用的列
            while ci < cols and occupied[ri][ci]:
                ci += 1
            if ci >= cols:
                break

            tcPr = tc.find(f"{_W}tcPr")
            gridSpan = 1
            is_vmerge = False
            is_vmerge_restart = False
            if tcPr is not None:
                gs = tcPr.find(f"{_W}gridSpan")
                if gs is not None:
                    try:
                        gridSpan = int(gs.get(f"{_W}val", "1"))
                    except ValueError:
                        gridSpan = 1
                vm = tcPr.find(f"{_W}vMerge")
                if vm is not None:
                    is_vmerge = True
                    val = vm.get(f"{_W}val", "")
                    if val == "restart":
                        is_vmerge_restart = True

            # 取文本（拼接所有 <w:t>）
            text = ""
            for t in tc.iter(f"{_W}t"):
                text += t.text or ""
            text = text.strip()

            # 处理纵向合并
            if is_vmerge and not is_vmerge_restart:
                # 延续格：合并到该列已开启的 vMerge 主格
                if ci in vmerge_open:
                    start_r, _span = vmerge_open[ci]
                    # 标记本格的跨度区域为占用
                    for cc in range(ci, min(ci + gridSpan, cols)):
                        for rr in range(ri, ri + 1):
                            if rr < rows and cc < cols:
                                occupied[rr][cc] = True
                    # 更新主格 rowspan（稍后统一计算）
                ci += gridSpan
                continue

            # 普通格或 vMerge restart 主格
            start_r = ri
            start_c = ci

            if is_vmerge_restart:
                # 计算纵向跨度：往下数连续的 vMerge 延续格
                rowspan = 1
                for rr in range(ri + 1, rows):
                    # 找该行对应列的 tc（用该行的 occupied 状态）
                    tc_below = _find_tc_at(trs[rr], ci, occupied[rr], cols)
                    if tc_below is None:
                        break
                    tcPr_below = tc_below.find(f"{_W}tcPr")
                    vm_below = None
                    if tcPr_below is not None:
                        vm_below = tcPr_below.find(f"{_W}vMerge")
                    if vm_below is not None and vm_below.get(f"{_W}val", "") != "restart":
                        rowspan += 1
                    else:
                        break
                vmerge_open[ci] = (start_r, rowspan)
            else:
                rowspan = 1

            colspan = gridSpan

            # 填值到主格
            grid[start_r][start_c] = text
            # 标记被合并占用的位置
            for rr in range(start_r, start_r + rowspan):
                for cc in range(start_c, start_c + colspan):
                    if rr == start_r and cc == start_c:
                        continue
                    if rr < rows and cc < cols:
                        occupied[rr][cc] = True

            # 记录合并信息
            if rowspan > 1 or colspan > 1:
                merged_cells.append({
                    "row": start_r, "col": start_c,
                    "rowspan": rowspan, "colspan": colspan,
                })

            ci += gridSpan

    return grid, merged_cells


def _find_tc_at(tr, target_ci, occupied_row, cols):
    """在指定 <w:tr> 中，按网格列游标定位 target_ci 对应的 <w:tc> 元素

    Args:
        tr: <w:tr> 元素
        target_ci: 目标网格列号
        occupied_row: 该行的占用状态列表（bool[]）
        cols: 总列数
    """
    ci = 0
    for tc in tr.findall(f"{_W}tc"):
        # 跳过被占用的列
        while ci < cols and occupied_row[ci]:
            ci += 1
        if ci > target_ci:
            return None
        tcPr = tc.find(f"{_W}tcPr")
        gridSpan = 1
        if tcPr is not None:
            gs = tcPr.find(f"{_W}gridSpan")
            if gs is not None:
                try:
                    gridSpan = int(gs.get(f"{_W}val", "1"))
                except ValueError:
                    gridSpan = 1
        if ci == target_ci:
            return tc
        ci += gridSpan
    return None


def parse_xlsx_to_grids(file_path: str) -> list:
    """解析 xlsx 的所有工作表为行列网格

    Returns:
        [{name, rows, cols, grid, merged_cells}]
    """
    wb = load_workbook(file_path, data_only=True)
    result = []
    for ws in wb.worksheets:
        grid, merged_cells = _xlsx_sheet_to_grid(ws)
        rows = len(grid)
        cols = max((len(r) for r in grid), default=0)
        # 补齐每行到等长
        for r in grid:
            while len(r) < cols:
                r.append("")
        result.append({
            "name": ws.title or f"表格{len(result)+1}",
            "rows": rows,
            "cols": cols,
            "grid": grid,
            "merged_cells": merged_cells,
        })
    wb.close()
    return result


def _xlsx_sheet_to_grid(ws) -> tuple:
    """将 openpyxl worksheet 转为网格，处理合并单元格。

    openpyxl 中合并单元格只有左上角有值，其余为 None（或 MergedCell）。
    我们把合并区域记录下来，值保留在左上角。
    """
    max_row = ws.max_row or 0
    max_col = ws.max_column or 0
    grid = [["" for _ in range(max_col)] for _ in range(max_row)]
    merged_cells = []

    # 先填充所有非合并单元格的值
    for r in range(max_row):
        for c in range(max_col):
            val = ws.cell(row=r + 1, column=c + 1).value
            if val is not None:
                grid[r][c] = _xlsx_val_to_str(val)

    # 处理合并区域
    for mr in ws.merged_cells.ranges:
        min_r, min_c = mr.min_row - 1, mr.min_col - 1
        max_r, max_c = mr.max_row - 1, mr.max_col - 1
        rowspan = max_r - min_r + 1
        colspan = max_c - min_c + 1
        if rowspan > 1 or colspan > 1:
            # 值已在左上角，只需记录合并信息
            merged_cells.append({
                "row": min_r, "col": min_c,
                "rowspan": rowspan, "colspan": colspan,
            })
            # 确保被合并占用的格子为空（openpyxl 通常已是 None/空）
            for rr in range(min_r, max_r + 1):
                for cc in range(min_c, max_c + 1):
                    if (rr, cc) != (min_r, min_c) and rr < max_row and cc < max_col:
                        grid[rr][cc] = ""

    return grid, merged_cells


def _xlsx_val_to_str(val) -> str:
    """把 openpyxl 单元格值转为字符串"""
    if val is None:
        return ""
    if isinstance(val, datetime):
        return val.strftime("%Y-%m-%d")
    if isinstance(val, date):
        return val.strftime("%Y-%m-%d")
    return str(val).strip()


def parse_document_to_grids(file_path: str, ext: str = None) -> list:
    """根据扩展名选择解析器

    Args:
        file_path: 文件路径
        ext: 扩展名(如 .docx/.xlsx)，None 则从路径推断
    Returns:
        网格列表
    """
    if ext is None:
        ext = Path(file_path).suffix.lower()
    if ext == ".docx":
        return parse_docx_to_grids(file_path)
    elif ext in (".xlsx", ".xls"):
        return parse_xlsx_to_grids(file_path)
    else:
        raise ValueError(f"不支持的文件格式: {ext}，仅支持 .docx 和 .xlsx")


# ==================== 从网格提取记录 ====================

def _similarity(a: str, b: str) -> float:
    """字符串相似度"""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def extract_record_from_grid(
    grid: list,
    cell_mappings: list,
    list_groups: list = None,
) -> Optional[dict]:
    """按映射配置从网格提取一条人员记录

    Args:
        grid: 二维文本网格
        cell_mappings: [{field_name, system_field_key, label_row, label_col, value_row, value_col}]
        list_groups: [{group_name, target_table, columns:[{field_name, system_field_key, value_row, value_col}]}]

    Returns:
        {flat_fields: {key: value}, sub_tables: {table_name: [{...}]}}
        若网格与映射不匹配（相似度<40%）返回 None
    """
    if not cell_mappings:
        return None

    rows = len(grid)
    cols = max((len(r) for r in grid), default=0) if rows > 0 else 0

    # 1. 尺寸校验 + 字段名相似度匹配（判断是否同类表）
    matched_count = 0
    total = len(cell_mappings)
    for m in cell_mappings:
        lr, lc = m["label_row"], m["label_col"]
        if lr >= rows or lc >= cols:
            continue
        label_text = grid[lr][lc] if lc < len(grid[lr]) else ""
        if _similarity(label_text, m["field_name"]) >= 0.4 or m["field_name"] in label_text or label_text in m["field_name"]:
            matched_count += 1

    # 相似度阈值：至少 40% 的字段标签能匹配
    if total > 0 and matched_count / total < 0.4:
        return None

    # 2. 提取扁平字段
    flat_fields = {}
    for m in cell_mappings:
        vr, vc = m["value_row"], m["value_col"]
        if vr >= rows or vc >= cols:
            continue
        value = grid[vr][vc] if vc < len(grid[vr]) else ""
        value = clean_value(value, m.get("system_field_key"))
        if m.get("system_field_key"):
            flat_fields[m["system_field_key"]] = value

    # 3. 提取列表组（子表）
    sub_tables = {}
    if list_groups:
        for lg in list_groups:
            columns = lg.get("columns", [])
            if not columns:
                continue
            items = _extract_list_group(grid, columns)
            if items:
                sub_tables[lg.get("target_table") or lg.get("group_name")] = items

    return {"flat_fields": flat_fields, "sub_tables": sub_tables}


def _extract_list_group(grid: list, columns: list) -> list:
    """提取列表组（子表多行），复刻表格助手的 groupHeight 推算逻辑

    只配置第一行的值格坐标，按"组高"逐行往下推算。

    Args:
        columns: [{field_name, system_field_key, value_row, value_col}]
    """
    rows = len(grid)
    cols = max((len(r) for r in grid), default=0) if rows > 0 else 0

    start_row = min(c["value_row"] for c in columns)
    max_row = max(c["value_row"] for c in columns)
    group_height = max_row - start_row + 1

    items = []
    for g in range(20):  # 最多提取 20 组，避免无限循环
        item = {}
        row_has_data = False
        out_of_bounds = False
        for c in columns:
            row_offset = c["value_row"] - start_row
            actual_row = start_row + g * group_height + row_offset
            if actual_row >= rows:
                out_of_bounds = True
                break
            col = c["value_col"]
            if col >= cols:
                continue
            val = grid[actual_row][col] if col < len(grid[actual_row]) else ""
            val = clean_value(val, c.get("system_field_key"))
            if c.get("system_field_key"):
                item[c["system_field_key"]] = val
            if val:
                row_has_data = True
        if out_of_bounds or not row_has_data:
            break
        items.append(item)
    return items


# ==================== 数据清洗 ====================

# 日期字段集合（需要归一化）
_DATE_FIELDS = {
    "birth_date", "party_join_date", "party_apply_date",
    "work_start_date", "join_unit_date", "graduation_date",
}


def clean_value(text: str, field_key: str = None) -> str:
    """清洗提取的值

    - 去除多余空白、换行、不可见字符
    - 日期字段归一化为 YYYY-MM-DD
    - 坐标标签残留（如"(1,2)"）清除
    """
    if text is None:
        return ""
    s = str(text)
    # 去除坐标标签残留
    s = re.sub(r"\(\d+,\s*\d+\)$", "", s)
    # 去除多余空白和换行（保留单个空格）
    s = re.sub(r"\s+", " ", s).strip()
    # 去除常见全角空格
    s = s.replace("\u3000", "").strip()

    if not s:
        return ""

    # 日期归一化
    if field_key in _DATE_FIELDS:
        s = _normalize_date(s)

    return s


def _normalize_date(s: str) -> str:
    """把各种日期格式归一化为 YYYY-MM-DD"""
    # YYYY-MM-DD / YYYY/MM/DD / YYYY.MM.DD
    m = re.match(r"^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})", s)
    if m:
        y, mo, d = m.groups()
        return f"{int(y):04d}-{int(mo):02d}-{int(d):02d}"
    # YYYY年M月D日
    m = re.match(r"^(\d{4})年(\d{1,2})月(\d{1,2})日?", s)
    if m:
        y, mo, d = m.groups()
        return f"{int(y):04d}-{int(mo):02d}-{int(d):02d}"
    # YYYY年M月
    m = re.match(r"^(\d{4})年(\d{1,2})月?", s)
    if m:
        y, mo = m.groups()
        return f"{int(y):04d}-{int(mo):02d}-01"
    # YYYYMMDD（8位纯数字）
    if re.match(r"^\d{8}$", s):
        return f"{s[0:4]}-{s[4:6]}-{s[6:8]}"
    return s


def grid_to_html_preview(grid_info: dict) -> str:
    """把网格转为前端可用的简化结构（不含HTML，由前端渲染）

    这里返回结构化数据，前端用 v-for 渲染。
    """
    return {
        "name": grid_info["name"],
        "rows": grid_info["rows"],
        "cols": grid_info["cols"],
        "cells": grid_info["grid"],
        "merged_cells": grid_info.get("merged_cells", []),
    }
