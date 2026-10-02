"""字段智能匹配引擎（模块 3、5 共用）

三级匹配策略：精确 → 同义词词典 → 模糊（编辑距离）
"""
from difflib import SequenceMatcher
from typing import Optional

# ===== 系统可用字段清单（key -> 显示名）=====
SYSTEM_FIELDS = {
    # 基本信息
    "name": "姓名", "gender": "性别", "birth_date": "出生日期",
    "ethnicity": "民族", "native_place": "现籍贯", "birth_place": "出生地",
    "id_card": "身份证号", "political_status": "政治面貌",
    "party_join_date": "入党时间", "party_apply_date": "申请入党时间",
    # 联系方式
    "phone": "手机号", "office_phone": "办公电话", "emergency_contact": "紧急联系人",
    # 工作信息
    "unit_name": "所在单位", "department": "部门", "position": "职务",
    "rank": "职级", "work_start_date": "参加工作时间", "join_unit_date": "入职本单位时间",
    # 学历
    "education_level": "最高学历", "degree": "学位", "school": "毕业院校",
    "major": "所学专业", "graduation_date": "毕业时间",
    # 家庭
    "marital_status": "婚姻状况", "spouse_name": "配偶姓名",
    "children_count": "子女数", "home_address": "家庭住址",
    # 派生
    "age": "年龄", "work_years": "工龄", "party_years": "党龄",
}

# ===== 同义词词典（多种表述 → 标准字段key）=====
SYNONYM_DICT = {
    # 姓名
    "姓名": "name", "名字": "name", "Name": "name",
    # 性别
    "性别": "gender", "sex": "gender", "Sex": "gender",
    # 出生日期
    "出生日期": "birth_date", "出生年月": "birth_date", "生日": "birth_date",
    "出生": "birth_date", "birthdate": "birth_date", "birthday": "birth_date",
    # 民族
    "民族": "ethnicity", "族别": "ethnicity",
    # 籍贯
    "现籍贯": "native_place", "籍贯": "native_place", "户籍": "native_place",
    "户籍地": "native_place", "户口所在地": "native_place",
    "出生地": "birth_place", "祖籍": "birth_place",
    # 身份证
    "身份证号": "id_card", "身份证": "id_card", "身份证号码": "id_card",
    "证件号码": "id_card", "身份证证件号": "id_card",
    # 政治面貌
    "政治面貌": "political_status", "政治面目": "political_status",
    "入党时间": "party_join_date", "入党年月": "party_join_date",
    # 联系方式
    "手机号": "phone", "手机": "phone", "联系电话": "phone",
    "电话": "phone", "移动电话": "phone", "联系方式": "phone",
    "办公电话": "office_phone", "办公": "office_phone",
    # 单位部门
    "所在单位": "unit_name", "工作单位": "unit_name", "单位": "unit_name",
    "部门": "department", "科室": "department", "处室": "department",
    # 职务
    "职务": "position", "职位": "position", "行政职务": "position",
    "职级": "rank", "级别": "rank", "军衔": "rank",
    # 时间
    "参加工作时间": "work_start_date", "参加工作": "work_start_date",
    "参加工作年月": "work_start_date", "工龄": "work_years",
    "入职时间": "join_unit_date", "入职本单位时间": "join_unit_date",
    # 学历
    "最高学历": "education_level", "学历": "education_level",
    "文化程度": "education_level", "最高文化程度": "education_level",
    "学位": "degree", "学位级别": "degree",
    "毕业院校": "school", "学校": "school", "毕业学校": "school",
    "所学专业": "major", "专业": "major",
    "毕业时间": "graduation_date", "毕业年月": "graduation_date",
    # 家庭
    "婚姻状况": "marital_status", "婚否": "marital_status", "婚姻": "marital_status",
    "配偶姓名": "spouse_name", "配偶": "spouse_name", "爱人姓名": "spouse_name",
    "子女数": "children_count", "子女情况": "children_count",
    "家庭住址": "home_address", "家庭地址": "home_address", "住址": "home_address",
    # 派生
    "年龄": "age", "岁数": "age",
    "党龄": "party_years",
}


def similarity(a: str, b: str) -> float:
    """字符串相似度（0~1）"""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def match_field(template_name: str, custom_fields: dict = None) -> tuple[str, float]:
    """匹配单个模板字段名到系统字段

    Args:
        template_name: 模板中的字段名（如"出生年月"）
        custom_fields: 自定义字段 dict {field_key: 显示名}，也参与匹配

    Returns:
        (system_field_key, confidence)  未匹配置信度为 0
    """
    name = template_name.strip()
    if not name:
        return "", 0.0

    # 1. 精确匹配系统字段显示名
    for key, display in SYSTEM_FIELDS.items():
        if name == display:
            return key, 1.0

    # 2. 同义词词典
    if name in SYNONYM_DICT:
        return SYNONYM_DICT[name], 0.95

    # 3. 模糊匹配：与所有系统字段+同义词比较，取最高
    best_key, best_score = "", 0.0
    candidates = {}
    candidates.update(SYSTEM_FIELDS)  # key->显示名
    # 反转同义词：表述->key
    candidates.update({v: k for k, v in {
        v: k for k, v in SYSTEM_FIELDS.items()
    }.items()})
    # 加入自定义字段
    if custom_fields:
        candidates.update(custom_fields)

    for key, display in candidates.items():
        score = max(similarity(name, display), similarity(name, key))
        if score > best_score:
            best_score = score
            best_key = key

    # 同时对同义词的 key 也做模糊
    for syn, key in SYNONYM_DICT.items():
        score = similarity(name, syn)
        if score > best_score:
            best_score = score
            best_key = key

    return (best_key, best_score) if best_score >= 0.6 else ("", best_score)


def match_all(template_names: list[str], custom_fields: dict = None) -> list[dict]:
    """批量匹配，返回每个字段名的匹配结果

    Returns:
        [{col_index, template_name, system_field_key, confidence, confirmed}]
    """
    results = []
    for i, name in enumerate(template_names):
        key, conf = match_field(name, custom_fields)
        results.append({
            "col_index": i,
            "template_name": name,
            "system_field_key": key,
            "confidence": round(conf, 3),
            "confirmed": conf >= 0.95,  # 高置信度自动确认
        })
    return results
