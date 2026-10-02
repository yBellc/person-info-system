"""身份证号工具：解析出生日期与性别（模块 4 联动回填）"""
import re
from datetime import date
from typing import Optional, Tuple


def validate_id_card(id_card: str) -> bool:
    """校验身份证号格式（18位）+ 校验位"""
    if not id_card or len(id_card) != 18:
        return False
    # 前17位必须数字，第18位数字或X
    if not re.match(r"^\d{17}[\dXx]$", id_card):
        return False

    # 校验位算法（GB 11643-1999）
    weights = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
    check_map = ["1", "0", "X", "9", "8", "7", "6", "5", "4", "3", "2"]
    total = sum(int(id_card[i]) * weights[i] for i in range(17))
    check_char = check_map[total % 11]
    return id_card[17].upper() == check_char


def parse_id_card(id_card: str) -> Tuple[Optional[date], Optional[str]]:
    """从身份证号解析出生日期与性别

    Returns:
        (birth_date, gender)  gender: '男'/'女'
    """
    if not validate_id_card(id_card):
        return None, None

    # 出生日期：第7-14位
    birth_str = id_card[6:14]
    try:
        birth_date = date(int(birth_str[0:4]), int(birth_str[4:6]), int(birth_str[6:8]))
    except ValueError:
        return None, None

    # 性别：第17位奇数为男，偶数为女
    gender_num = int(id_card[16])
    gender = "男" if gender_num % 2 == 1 else "女"

    return birth_date, gender


def mask_id_card(id_card: Optional[str]) -> Optional[str]:
    """身份证号脱敏：保留前6后4，中间打码"""
    if not id_card or len(id_card) < 10:
        return id_card
    return id_card[:6] + "********" + id_card[-4:]


def calc_age(birth_date: Optional[date], ref_date: Optional[date] = None) -> Optional[int]:
    """计算年龄（派生字段，实时算）"""
    if not birth_date:
        return None
    today = ref_date or date.today()
    age = today.year - birth_date.year
    # 生日未过则减1
    if (today.month, today.day) < (birth_date.month, birth_date.day):
        age -= 1
    return age


def calc_years(start_date: Optional[date], ref_date: Optional[date] = None) -> Optional[float]:
    """计算年限（工龄/党龄/司龄），保留1位小数"""
    if not start_date:
        return None
    today = ref_date or date.today()
    days = (today - start_date).days
    if days < 0:
        return 0.0
    return round(days / 365.25, 1)
