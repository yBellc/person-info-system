"""Excel 模板解析与报表生成（模块 3）"""
from pathlib import Path
from typing import Optional

from openpyxl import load_workbook, Workbook
from openpyxl.styles import PatternFill, Font

from app.core.idcard import calc_age, calc_years, mask_id_card


def parse_template_headers(file_path: str, header_row: int = 1, sheet_index: int = 0) -> list[str]:
    """读取模板表头行的所有单元格文本

    Args:
        file_path: Excel 文件路径
        header_row: 表头行号（1-based）
        sheet_index: 工作表序号

    Returns:
        表头字段名列表（按列顺序）
    """
    wb = load_workbook(file_path, data_only=True)
    ws = wb.worksheets[sheet_index]
    headers = []
    for cell in ws[header_row]:
        val = cell.value
        headers.append(str(val).strip() if val is not None else "")
    wb.close()
    return headers


def get_field_value(person, field_key: str) -> Optional[str]:
    """根据字段 key 从人员对象取值（含派生字段、单位名、自定义字段）"""
    # 派生字段
    if field_key == "age":
        age = calc_age(person.birth_date)
        return str(age) if age is not None else ""
    if field_key == "work_years":
        y = calc_years(person.work_start_date)
        return str(y) if y is not None else ""
    if field_key == "party_years":
        y = calc_years(person.party_join_date)
        return str(y) if y is not None else ""
    if field_key == "unit_name":
        return getattr(person, "unit_name", "") or ""

    # 自定义字段：从 person.custom_values 查找
    custom_values = getattr(person, "_custom_values", None)
    if custom_values and field_key in custom_values:
        return str(custom_values[field_key]) if custom_values[field_key] is not None else ""

    # 常规字段
    val = getattr(person, field_key, None)
    if val is None:
        return ""
    # 日期转字符串
    if hasattr(val, "strftime"):
        return val.strftime("%Y-%m-%d")
    return str(val)


def fill_template(
    template_path: str,
    output_path: str,
    mappings: list[dict],
    persons: list,
    header_row: int = 1,
    data_start_row: int = 2,
) -> dict:
    """根据映射关系把人员数据填入模板，生成报表

    Args:
        template_path: 模板文件路径
        output_path: 输出文件路径
        mappings: [{col_index, system_field_key, ...}] 已确认的映射
        persons: 人员对象列表
        header_row: 表头行
        data_start_row: 数据起始行

    Returns:
        {total, filled, missing_cells}
    """
    wb = load_workbook(template_path)
    ws = wb.active

    # 只用已确认且有系统字段key的映射
    valid_maps = [m for m in mappings if m.get("system_field_key")]

    # 清除模板中可能残留的旧数据行（保留表头）
    max_col = ws.max_column
    if ws.max_row >= data_start_row:
        for row in range(data_start_row, ws.max_row + 1):
            for col in range(1, max_col + 1):
                cell = ws.cell(row=row, column=col)
                cell.value = None
                cell.fill = PatternFill(fill_type=None)

    missing_cells = []
    filled = 0

    for idx, person in enumerate(persons):
        row = data_start_row + idx
        for m in valid_maps:
            col = m["col_index"] + 1  # openpyxl 列 1-based
            key = m["system_field_key"]
            val = get_field_value(person, key)
            if val == "" or val is None:
                missing_cells.append({"row": row, "col": col, "name": person.name, "field": key})
            else:
                ws.cell(row=row, column=col, value=val)
                filled += 1

    # 缺失单元格标黄
    yellow = PatternFill(start_color="FFFACD", end_color="FFFACD", fill_type="solid")
    for mc in missing_cells:
        ws.cell(row=mc["row"], column=mc["col"]).fill = yellow

    wb.save(output_path)
    wb.close()

    return {
        "total": len(persons),
        "filled_cells": filled,
        "missing_cells": len(missing_cells),
        "missing_detail": missing_cells[:50],  # 只返回前50条
    }
