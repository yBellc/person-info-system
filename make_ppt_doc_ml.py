# -*- coding: utf-8 -*-
"""
内部人员信息管理系统汇报PPT（机器学习方向版）
严肃简洁深色风格，共10页
"""
import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml.ns import qn

OUT_DIR = r"e:\工作工作\text\person-info-system"
PPT_FILE = os.path.join(OUT_DIR, "内部人员信息管理系统汇报_机器学习方向版.pptx")

# ===== 主题色：严肃深色系 + 研究方向绿色点缀 =====
C_DARK   = RGBColor(0x1A, 0x2A, 0x3A)   # 深色背景
C_BLUE   = RGBColor(0x2B, 0x57, 0x8A)   # 主色蓝
C_GREEN  = RGBColor(0x2D, 0x5A, 0x27)   # 军队绿（研究方向主色）
C_GOLD   = RGBColor(0xC9, 0xA5, 0x4F)   # 金色点缀
C_WHITE  = RGBColor(0xFF, 0xFF, 0xFF)
C_LIGHT  = RGBColor(0xF5, 0xF7, 0xFA)   # 浅灰背景
C_GRAY   = RGBColor(0x8C, 0x8C, 0x8C)   # 灰色文字
C_TEXT   = RGBColor(0x33, 0x33, 0x33)   # 正文
C_LINE   = RGBColor(0xD8, 0xDE, 0xE6)   # 分割线

prs = Presentation()
prs.slide_width  = Inches(13.333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]


def set_run(run, size=18, bold=False, color=C_TEXT, font_name="微软雅黑"):
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    run.font.name = font_name
    rPr = run._r.get_or_add_rPr()
    ea = rPr.makeelement(qn('a:ea'), {'typeface': font_name})
    rPr.append(ea)


def add_text(slide, left, top, width, height, text, size=18, bold=False,
             color=C_TEXT, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP):
    tb = slide.shapes.add_textbox(left, top, width, height)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = Inches(0.05)
    tf.margin_right = Inches(0.05)
    lines = text.split("\n") if isinstance(text, str) else text
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.space_after = Pt(4)
        run = p.add_run()
        run.text = line
        set_run(run, size=size, bold=bold, color=color)
    return tb


def add_rect(slide, left, top, width, height, fill=None, line=None):
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, width, height)
    shape.shadow.inherit = False
    if fill is None:
        shape.fill.background()
    else:
        shape.fill.solid()
        shape.fill.fore_color.rgb = fill
    if line is None:
        shape.line.fill.background()
    else:
        shape.line.color.rgb = line
        shape.line.width = Pt(0.5)
    return shape


def add_page_header(slide, title, page_num, accent_color=C_BLUE):
    """每页顶部标题栏"""
    add_rect(slide, 0, 0, prs.slide_width, Inches(0.06), fill=accent_color)
    add_text(slide, Inches(0.8), Inches(0.35), Inches(10), Inches(0.6),
             title, size=26, bold=True, color=accent_color)
    add_rect(slide, Inches(0.8), Inches(1.05), Inches(1.2), Inches(0.04), fill=accent_color)
    add_text(slide, Inches(12.2), Inches(7.05), Inches(0.8), Inches(0.3),
             str(page_num), size=11, color=C_GRAY, align=PP_ALIGN.RIGHT)
    add_rect(slide, Inches(0.8), Inches(7.1), Inches(11.7), Inches(0.02), fill=C_LINE)
    add_text(slide, Inches(0.8), Inches(7.15), Inches(8), Inches(0.25),
             "单位内部信息管理系统", size=9, color=C_GRAY)


def add_bullet(slide, left, top, width, height, items, size=16, color=C_TEXT, accent=C_BLUE):
    """简洁的无序号列表"""
    tb = slide.shapes.add_textbox(left, top, width, height)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.TOP
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.LEFT
        p.space_after = Pt(10)
        r0 = p.add_run()
        r0.text = "—  "
        set_run(r0, size=size, color=accent, bold=True)
        r1 = p.add_run()
        r1.text = item
        set_run(r1, size=size, color=color)
    return tb


def add_card(slide, left, top, width, height, title, desc, color=C_BLUE, title_size=17, desc_size=13):
    """卡片式模块展示"""
    add_rect(slide, left, top, Inches(0.06), height, fill=color)
    add_text(slide, left + Inches(0.25), top + Inches(0.1), width - Inches(0.25), Inches(0.4),
             title, size=title_size, bold=True, color=color)
    add_text(slide, left + Inches(0.25), top + Inches(0.55), width - Inches(0.25), height - Inches(0.55),
             desc, size=desc_size, color=C_TEXT)


# ======================================================================
# 第1页：封面
# ======================================================================
s1 = prs.slides.add_slide(BLANK)
add_rect(s1, 0, 0, prs.slide_width, prs.slide_height, fill=C_DARK)
add_rect(s1, 0, 0, Inches(0.15), prs.slide_height, fill=C_GREEN)

# 副标题（研究方向）
add_text(s1, Inches(1.2), Inches(1.8), Inches(11), Inches(0.4),
         "基于机器学习的文档识别与数智化管理",
         size=14, color=C_GOLD)
# 标题
add_text(s1, Inches(1.2), Inches(2.3), Inches(11), Inches(1.2),
         "内部人员信息管理系统",
         size=42, bold=True, color=C_WHITE)
# 副标题
add_text(s1, Inches(1.2), Inches(3.6), Inches(11), Inches(0.6),
         "项目建设情况汇报",
         size=22, color=RGBColor(0xA0, 0xB8, 0xD0))

add_rect(s1, Inches(1.2), Inches(4.4), Inches(2.5), Inches(0.03), fill=C_GREEN)

add_text(s1, Inches(1.2), Inches(5.5), Inches(11), Inches(0.4),
         "汇报人：信息中心  ·  计算数学专业（机器学习图像处理方向）",
         size=15, color=RGBColor(0x80, 0x98, 0xB0))
add_text(s1, Inches(1.2), Inches(6.0), Inches(11), Inches(0.4),
         "2026年8月",
         size=15, color=RGBColor(0x80, 0x98, 0xB0))


# ======================================================================
# 第2页：个人研究背景与专业优势
# ======================================================================
s2 = prs.slides.add_slide(BLANK)
add_page_header(s2, "一、个人研究背景与专业优势", 2, accent_color=C_GREEN)

add_text(s2, Inches(0.8), Inches(1.3), Inches(11.5), Inches(0.5),
         "专业：计算数学  |  研究方向：基于机器学习的图像处理、识别与分割",
         size=18, bold=True, color=C_GREEN)

research = [
    ("文档图像识别与版面分析",
     "研究如何从扫描文档、表格中自动提取结构化信息\n涉及图像预处理、版面分割、OCR识别等技术"),
    ("目标检测与图像分割",
     "研究从图像中定位并分割出感兴趣区域\n如签名区、印章区、证件照片、表格单元格等"),
    ("深度学习模型部署与优化",
     "研究训练好的模型轻量化与加速\n使其在普通办公电脑/内网服务器高效运行"),
]

for i, (title, desc) in enumerate(research):
    col = i
    x = Inches(0.8) + col * Inches(4.1)
    y = Inches(2.1)
    add_rect(s2, x, y, Inches(3.95), Inches(4.4), fill=C_LIGHT, line=C_LINE)
    # 顶部色条
    add_rect(s2, x, y, Inches(3.95), Inches(0.08), fill=C_GREEN)
    # 序号圆
    add_text(s2, x + Inches(0.2), y + Inches(0.25), Inches(3.5), Inches(0.4),
             "0" + str(i+1), size=22, bold=True, color=C_GREEN)
    add_rect(s2, x + Inches(0.2), y + Inches(0.75), Inches(1.5), Inches(0.02), fill=C_GOLD)
    # 标题
    add_text(s2, x + Inches(0.2), y + Inches(1.0), Inches(3.5), Inches(0.6),
             title, size=16, bold=True, color=C_BLUE)
    # 描述
    add_text(s2, x + Inches(0.2), y + Inches(1.8), Inches(3.55), Inches(2.4),
             desc, size=14, color=C_TEXT)

# 底部一句话
add_rect(s2, Inches(0.8), Inches(6.7), Inches(11.5), Inches(0.4), fill=C_LIGHT)
add_text(s2, Inches(0.8), Inches(6.7), Inches(11.5), Inches(0.4),
         "建设信息管理系统过程中，持续将研究方向与单位实际需求结合，推动智能化落地",
         size=14, bold=True, color=C_GREEN, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)


# ======================================================================
# 第3页：项目建设背景
# ======================================================================
s3 = prs.slides.add_slide(BLANK)
add_page_header(s3, "二、项目建设背景", 3, accent_color=C_GREEN)

add_text(s3, Inches(0.8), Inches(1.3), Inches(11.5), Inches(0.5),
         "传统办公模式下的主要痛点", size=18, bold=True, color=C_GREEN)

items_bg = [
    "人员信息分散管理：员工档案以纸质或Excel形式散落在各科室，查询效率低，更新不及时",
    "表单收集靠人工：工资条、考核表、信息采集表需逐个下发、收集、汇总，一份小表耗时30分钟",
    "审批流程纸质化：请假、用章、出差等申请拿着单子跑领导，进度不透明，追溯困难",
    "纸质档案数字化难：大量历史手写档案、证件复印件需手工录入，耗时耗力易出错，正是机器学习识别的重点场景",
    "信息安全有隐患：邮件、微信群传输敏感信息，缺乏权限管控和操作审计，出问题无法追溯",
]
add_bullet(s3, Inches(0.8), Inches(2.0), Inches(11.5), Inches(4.0), items_bg, size=16, accent=C_GREEN)

add_rect(s3, Inches(0.8), Inches(6.2), Inches(11.5), Inches(0.6), fill=C_LIGHT)
add_text(s3, Inches(0.8), Inches(6.2), Inches(11.5), Inches(0.6),
         "目标：人员档案数字化、审批流程在线化、表单收集智能化、纸质文档识别自动化",
         size=15, bold=True, color=C_GREEN, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)


# ======================================================================
# 第4页：系统核心功能概览
# ======================================================================
s4 = prs.slides.add_slide(BLANK)
add_page_header(s4, "三、系统核心功能概览", 4, accent_color=C_GREEN)

add_text(s4, Inches(0.8), Inches(1.3), Inches(11.5), Inches(0.5),
         "六大核心模块，覆盖单位日常办公主要场景", size=18, bold=True, color=C_GREEN)

modules = [
    ("人员档案管理", "全员电子档案，支持自定义字段，简历智能识别，人事批量建档"),
    ("OA流程审批", "请假/报销/用章/出差四类流程，审批人自动匹配，含退回和流转记录"),
    ("智能表格", "上传文档自动识别字段，AI智能生成表单，下发填写，原模板导出"),
    ("组织架构管理", "单位/部门/岗位/职级体系一体化，审批流程自动匹配基于此架构"),
    ("统计报表", "上传Excel模板自动字段匹配，花名册/党员名册/学历统计一键导出"),
    ("系统安全（新增）", "审计日志、数据备份、会话超时、权限管控、密码策略，共7项安全加固"),
]

for i, (title, desc) in enumerate(modules):
    col = i % 2
    row = i // 2
    x = Inches(0.8) + col * Inches(5.9)
    y = Inches(2.0) + row * Inches(1.55)
    add_card(s4, x, y, Inches(5.65), Inches(1.35), title, desc, color=C_GREEN)

add_rect(s4, Inches(0.8), Inches(6.7), Inches(11.5), Inches(0.04), fill=C_LINE)
add_text(s4, Inches(0.8), Inches(6.8), Inches(11.5), Inches(0.3),
         "技术架构：Python FastAPI + Vue 3 + SQLite  |  单进程部署，内网服务器直接运行",
         size=13, color=C_GRAY)


# ======================================================================
# 第5页：现场功能演示
# ======================================================================
s5 = prs.slides.add_slide(BLANK)
add_page_header(s5, "四、现场功能演示", 5, accent_color=C_GREEN)

add_text(s5, Inches(0.8), Inches(1.3), Inches(11.5), Inches(0.5),
         "四块核心流程演示，重点展示智能识别能力", size=18, bold=True, color=C_GREEN)

demos = [
    ("1", "人员档案 + 简历自动识别",
     "打开人员档案 → 上传Word/PDF简历 → 系统自动提取40+字段 → 确认保存",
     "【文档版面分析 + 文本结构化提取】"),
    ("2", "AI智能生成表单（机器学习场景分类）",
     "进入智能表格 → AI创建 → 输入'创建一份年度考核表' → 看推荐结果并保存",
     "【多关键词场景分类 + 智能字段映射】"),
    ("3", "审批流程在线流转",
     "员工发起请假申请 → 部门领导审批 → 人事审批 → 查看审批进度时间轴",
     "【审批人自动匹配 + 完整流转记录】"),
    ("4", "报表智能匹配与导出",
     "上传花名册Excel模板 → 自动匹配系统字段 → 一键生成报表并下载",
     "【三级匹配策略：精确→同义词→相似度】"),
]

for i, (num, title, desc, tech) in enumerate(demos):
    y = Inches(2.1) + i * Inches(1.15)
    add_rect(s5, Inches(0.8), y, Inches(0.7), Inches(1.0), fill=C_GREEN)
    add_text(s5, Inches(0.8), y, Inches(0.7), Inches(1.0),
             num, size=26, bold=True, color=C_WHITE,
             align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    add_rect(s5, Inches(1.5), y, Inches(10.8), Inches(1.0), fill=C_LIGHT)
    add_text(s5, Inches(1.8), y + Inches(0.05), Inches(7.5), Inches(0.4),
             title, size=16, bold=True, color=C_GREEN)
    add_text(s5, Inches(1.8), y + Inches(0.5), Inches(7.5), Inches(0.4),
             desc, size=13, color=C_TEXT)
    # 技术标签（金色）
    add_rect(s5, Inches(9.5), y + Inches(0.2), Inches(2.6), Inches(0.6), fill=C_DARK)
    add_text(s5, Inches(9.5), y + Inches(0.2), Inches(2.6), Inches(0.6),
             tech, size=11, color=C_GOLD, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

add_text(s5, Inches(0.8), Inches(6.7), Inches(11.5), Inches(0.4),
         "（现场打开系统网页进行操作演示）",
         size=14, color=C_GRAY, align=PP_ALIGN.CENTER)


# ======================================================================
# 第6页：近期完成的安全加固（7项）
# ======================================================================
s6 = prs.slides.add_slide(BLANK)
add_page_header(s6, "五、近期完成的系统性安全加固（共7项）", 6, accent_color=C_GREEN)

add_text(s6, Inches(0.8), Inches(1.3), Inches(11.5), Inches(0.5),
         "针对体制内单位要求，确保上线后不出差错、可管可控",
         size=16, bold=True, color=C_GREEN)

sec_items = [
    ("01", "审计日志系统",
     "超管可查看所有操作记录：谁、在什么IP、做了什么、修改前后值。\n登录日志含成功失败、失败原因。满足'可追溯'硬性要求。"),
    ("02", "数据库备份机制",
     "超管界面一键备份/下载/删除，文件按时间戳命名，存服务器备份目录。\n后续增加自动定时备份策略。"),
    ("03", "会话超时机制",
     "30分钟无操作自动登出，提前1分钟弹窗提醒。\n防止人员离开电脑后被他人操作，涉密系统标配。"),
    ("04", "生产环境配置模板",
     "提供.env.production模板，部署时修改密钥、密码、数据库地址。\n默认密钥和密码自动检测告警。"),
    ("05", "API文档生产禁用",
     "正式环境下/docs、/redoc、/openapi自动禁用。\n防止接口信息暴露，降低被攻击风险。"),
    ("06", "CORS来源锁定",
     "跨域访问从'允许所有'改为'仅允许配置的内网地址'。\n收紧HTTP方法与请求头。"),
    ("07", "报表导出准确性修复",
     "修复自定义字段不填充、软删除数据泄露、模板旧数据残留三个bug。\n导出数据确保准确无误。"),
]

for i, (num, title, desc) in enumerate(sec_items):
    col = i % 2
    row = i // 2
    x = Inches(0.8) + col * Inches(5.95)
    y = Inches(2.0) + row * Inches(1.62)
    # 编号
    add_rect(s6, x, y, Inches(0.6), Inches(1.42), fill=C_GREEN)
    add_text(s6, x, y, Inches(0.6), Inches(1.42), num, size=18, bold=True, color=C_WHITE,
             align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    # 内容
    add_rect(s6, x + Inches(0.6), y, Inches(5.3), Inches(1.42), fill=C_LIGHT)
    add_text(s6, x + Inches(0.8), y + Inches(0.08), Inches(5), Inches(0.35),
             title, size=14, bold=True, color=C_GREEN)
    add_text(s6, x + Inches(0.8), y + Inches(0.45), Inches(5), Inches(0.9),
             desc, size=12, color=C_TEXT)


# ======================================================================
# 第7页：已实现的AI能力（结合研究方向）
# ======================================================================
s7 = prs.slides.add_slide(BLANK)
add_page_header(s7, "六、已实现的AI能力（结合研究方向）", 7, accent_color=C_GREEN)

add_text(s7, Inches(0.8), Inches(1.3), Inches(11.5), Inches(0.5),
         "已初步应用研究方向的相关技术，为后续深度学习升级打好框架",
         size=16, bold=True, color=C_GREEN)

ai_cards = [
    ("简历文档智能解析",
     "上传Word/PDF简历，自动提取40+字段\n（姓名、性别、学历、工作经历…）",
     "文档版面分析 + 文本结构化提取",
     C_GREEN),
    ("报表模板表头匹配",
     "上传Excel模板，自动匹配表头与标准字段\n置信度≥0.95自动确认",
     "三级匹配：精确→同义词词典→模糊相似度\n（机器学习模式匹配基础方法）",
     C_BLUE),
    ("AI智能表单生成",
     "输入自然语言生成业务表单\n如'年度考核表'→自动匹配10种预置场景",
     "多关键词场景分类\n后续可替换为文本分类深度学习模型",
     C_GOLD),
    ("身份证合法性校验",
     "内置18位身份证校验码算法\n自动校验格式、提取出生日期、计算年龄",
     "结构化数据验证\n保证基础数据质量",
     C_DARK),
]

for i, (title, desc, tech, color) in enumerate(ai_cards):
    col = i % 2
    row = i // 2
    x = Inches(0.8) + col * Inches(5.95)
    y = Inches(2.0) + row * Inches(2.35)
    add_rect(s7, x, y, Inches(5.85), Inches(2.15), fill=C_LIGHT, line=C_LINE)
    # 顶部色条
    add_rect(s7, x, y, Inches(5.85), Inches(0.06), fill=color)
    # 标题
    add_text(s7, x + Inches(0.25), y + Inches(0.2), Inches(5.4), Inches(0.4),
             title, size=17, bold=True, color=color)
    # 分隔
    add_rect(s7, x + Inches(0.25), y + Inches(0.7), Inches(1), Inches(0.02), fill=color)
    # 功能
    add_text(s7, x + Inches(0.25), y + Inches(0.85), Inches(5.4), Inches(0.6),
             desc, size=14, color=C_TEXT)
    # 技术栈（深色底）
    add_rect(s7, x + Inches(0.25), y + Inches(1.55), Inches(5.35), Inches(0.48), fill=C_DARK)
    add_text(s7, x + Inches(0.25), y + Inches(1.55), Inches(5.35), Inches(0.48),
             tech, size=11, color=C_GOLD, anchor=MSO_ANCHOR.MIDDLE)


# ======================================================================
# 第8页：基于研究方向的未来规划（重点页）
# ======================================================================
s8 = prs.slides.add_slide(BLANK)
add_page_header(s8, "七、基于研究方向的未来规划（重点）", 8, accent_color=C_GREEN)

add_text(s8, Inches(0.8), Inches(1.25), Inches(11.5), Inches(0.5),
         "结合机器学习图像处理研究方向，半年到一年的5件具体落地事项",
         size=15, bold=True, color=C_GREEN)

plans = [
    ("① 手写表格识别（最高优先级）",
     "痛点：历史手写登记表人工录入需30分钟/份",
     "方案：扫描件预处理 → 版面分割（实例分割模型切分单元格）→ 手写字符识别（CRNN）→ 自动回填档案",
     "效果：录入时间从30分钟降到1-2分钟，准确率≥95%"),
    ("② 证件自动识别与校验",
     "痛点：人事录入身份证/学位证需手工核对",
     "方案：证件类型检测 → 四角定位透视变换（分割+对齐）→ OCR识别 → 自动比对档案信息并发现不一致",
     "效果：录入零错误，节省人事大量核对时间"),
    ("③ 手写签名验证",
     "痛点：审批仍需打印签字再扫描，无法验真",
     "方案：首登3-5个签名样本建特征库 → 审批上传时用图像相似度匹配辅助验真 → 后续发展为在线电子签名",
     "效果：审批无需打印，签名辅助验真防伪造"),
    ("④ 人像与证照比对（人脸识别）",
     "痛点：新人照片与本人是否一致、内部考勤",
     "方案：证件照人脸检测+特征提取 → 入职照片比对确认本人 → 后续对接人脸识别考勤/签到",
     "效果：杜绝冒用身份，考勤更高效"),
    ("⑤ 纸质档案批量数字化",
     "痛点：历史存量档案手工电子化工作量巨大",
     "方案：批量扫描 → 自动分类（履历/审批/证件）→ 关键区域分割 → OCR识别 → 自动归入对应人员档案",
     "效果：核心技术：图像分类+目标检测+版面分割，全部自研可控"),
]

for i, (title, pain, method, effect) in enumerate(plans):
    y = Inches(1.9) + i * Inches(1.06)
    # 左边标题区
    add_rect(s8, Inches(0.8), y, Inches(3.1), Inches(0.95), fill=C_GREEN)
    add_text(s8, Inches(0.8), y, Inches(3.1), Inches(0.95),
             title, size=13, bold=True, color=C_WHITE,
             align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    # 右边内容区（三行：痛点 方案 效果）
    add_rect(s8, Inches(3.9), y, Inches(8.4), Inches(0.95), fill=C_LIGHT)
    add_text(s8, Inches(4.05), y + Inches(0.05), Inches(8.1), Inches(0.25),
             "痛点：" + pain, size=11, color=C_GRAY)
    add_text(s8, Inches(4.05), y + Inches(0.3), Inches(8.1), Inches(0.3),
             "方案：" + method, size=12, color=C_TEXT)
    add_text(s8, Inches(4.05), y + Inches(0.62), Inches(8.1), Inches(0.25),
             "效果：" + effect, size=11, bold=True, color=C_GREEN)

add_rect(s8, Inches(0.8), Inches(7.0), Inches(11.5), Inches(0.04), fill=C_GREEN)
add_text(s8, Inches(0.8), Inches(7.02), Inches(11.5), Inches(0.3),
         "★ 所有模型部署在内网服务器，数据不出单位，完全满足涉密要求",
         size=13, bold=True, color=C_GOLD, align=PP_ALIGN.CENTER)


# ======================================================================
# 第9页：单位数智化发展贡献设想
# ======================================================================
s9 = prs.slides.add_slide(BLANK)
add_page_header(s9, "八、对单位数智化发展的贡献设想", 9, accent_color=C_GREEN)

layers = [
    ("第一层", "档案全面数字化升级", C_GREEN,
     "解决'从纸到数'的核心瓶颈，这是很多单位数智化的最大瓶颈。通过手写识别、版面分割、证件识别，把历史存量档案快速电子化，让信息系统真正有数据可用。"),
    ("第二层", "办公流程深度智能化", C_BLUE,
     "在现有系统基础上逐步引入：\n① 自然语言问答：领导提问自动生成报表\n② 智能预警：证件过期、合同续签、退休临近自动提醒\n③ 审批智能辅助：根据历史记录给出审批建议，减轻领导负担"),
    ("第三层", "数据安全与隐私保护", C_GOLD,
     "结合图像处理与密码学保护敏感数据：\n① 证件照片上传后自动脱敏（身份证号打码、人脸模糊）再存储\n② 敏感图像轻量级加密存储，有权限才能查看原图\n③ 操作日志与图像均加密，确保隐私合规"),
]

for i, (layer, title, color, desc) in enumerate(layers):
    col = i
    x = Inches(0.8) + col * Inches(4.1)
    y = Inches(1.7)
    # 顶部色块
    add_rect(s9, x, y, Inches(3.95), Inches(1.0), fill=color)
    add_text(s9, x, y + Inches(0.05), Inches(3.95), Inches(0.4),
             layer, size=14, color=C_WHITE,
             align=PP_ALIGN.CENTER)
    add_text(s9, x, y + Inches(0.45), Inches(3.95), Inches(0.5),
             title, size=18, bold=True, color=C_WHITE,
             align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    # 下面白色内容
    add_rect(s9, x, y + Inches(1.0), Inches(3.95), Inches(4.8), fill=C_LIGHT, line=color)
    add_text(s9, x + Inches(0.2), y + Inches(1.2), Inches(3.55), Inches(4.4),
             desc, size=14, color=C_TEXT)

# 底部强调
add_rect(s9, Inches(0.8), Inches(6.65), Inches(11.5), Inches(0.5), fill=C_DARK)
add_text(s9, Inches(0.8), Inches(6.65), Inches(11.5), Inches(0.5),
         "核心优势：所有模型和算法自主可控，部署在内网，不调用外部API；可针对单位实际数据做定制化微调和迭代",
         size=14, bold=True, color=C_GOLD, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)


# ======================================================================
# 第10页：总结
# ======================================================================
s10 = prs.slides.add_slide(BLANK)
add_rect(s10, 0, 0, prs.slide_width, prs.slide_height, fill=C_DARK)
add_rect(s10, 0, 0, Inches(0.15), prs.slide_height, fill=C_GREEN)

add_text(s10, Inches(1.2), Inches(1.3), Inches(11), Inches(0.8),
         "总结 — 三句话汇报", size=34, bold=True, color=C_WHITE)
add_rect(s10, Inches(1.2), Inches(2.15), Inches(1.8), Inches(0.04), fill=C_GREEN)

summary = [
    ("当前进展",
     "六大核心模块开发完成，7项安全加固到位，\n系统已具备内网上线试运行条件",
     C_GREEN),
    ("专业结合",
     "系统已初步应用文档识别、字段匹配、场景分类等技术；\n后续持续结合研究方向，解决手写识别、签名验证等实际痛点",
     C_GOLD),
    ("下一步计划",
     "立即部署上线、小范围试运行，\n优先推进手写表格识别模块落地，完成从'有系统'到'有智能系统'的跨越",
     RGBColor(0x5B, 0x9B, 0xD5)),
]

for i, (tag, desc, color) in enumerate(summary):
    y = Inches(2.6) + i * Inches(1.3)
    # 标签
    add_rect(s10, Inches(1.2), y, Inches(2.0), Inches(1.05), fill=color)
    add_text(s10, Inches(1.2), y, Inches(2.0), Inches(1.05),
             tag, size=20, bold=True, color=C_WHITE,
             align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    # 描述
    add_text(s10, Inches(3.4), y + Inches(0.15), Inches(9), Inches(1.05),
             desc, size=17, color=C_WHITE)

add_rect(s10, Inches(5.5), Inches(6.6), Inches(2.3), Inches(0.03), fill=C_GREEN)
add_text(s10, Inches(1.2), Inches(6.75), Inches(11), Inches(0.5),
         "请领导批示，谢谢！", size=22, bold=True, color=C_WHITE, align=PP_ALIGN.CENTER)


# ===== 保存 PPT =====
prs.save(PPT_FILE)
print(f"[OK] PPT saved: {PPT_FILE}")
print(f"     Size: {os.path.getsize(PPT_FILE)/1024:.1f} KB")
print(f"     Slides: {len(prs.slides)}")

# ===== 生成 Word 讲稿 =====
from docx import Document
from docx.shared import Pt, RGBColor as DocxRGB, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn as docx_qn

DOC_FILE = os.path.join(OUT_DIR, "汇报讲稿_机器学习方向版.docx")

doc = Document()

# 全局样式
style = doc.styles['Normal']
style.font.name = '微软雅黑'
style.font.size = Pt(12)
style.element.rPr.rFonts.set(docx_qn('w:eastAsia'), '微软雅黑')

sections = doc.sections
for section in sections:
    section.top_margin = Cm(2.54)
    section.bottom_margin = Cm(2.54)
    section.left_margin = Cm(3.17)
    section.right_margin = Cm(3.17)

def doc_title(text, level=1):
    p = doc.add_heading(text, level=level)
    for run in p.runs:
        run.font.name = '微软雅黑'
        run.font.color.rgb = DocxRGB(0x1A, 0x2A, 0x3A)
        run._element.rPr.rFonts.set(docx_qn('w:eastAsia'), '微软雅黑')
    return p

def doc_paragraph(text, bold=False, size=12, color=None, quote=False):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(8)
    if quote:
        p.paragraph_format.left_indent = Cm(0.8)
    run = p.add_run(text)
    run.font.name = '微软雅黑'
    run.font.size = Pt(size)
    run.font.bold = bold
    if color:
        run.font.color.rgb = color
    run._element.rPr.rFonts.set(docx_qn('w:eastAsia'), '微软雅黑')
    return p

# ===== 讲稿正文 =====
doc_title("内部人员信息管理系统建设情况汇报 · 讲稿", 0)
doc_paragraph("（结合机器学习图像处理研究方向 · 总时长约 10-12 分钟）",
              color=DocxRGB(0x8C, 0x8C, 0x8C), size=11)
doc.add_paragraph()

# 第1页
doc_title("第 1 页 · 封面（约 30 秒）", 1)
doc_paragraph("各位领导，大家好。今天我向大家汇报内部人员信息管理系统的建设进展，以及我结合自身专业背景对单位数智化发展的一些思考。", quote=True)
doc_paragraph("我将从个人研究背景、项目建设背景、系统核心功能、近期安全加固进展、已实现的AI能力、基于研究方向的未来规划、对单位数智化的贡献设想七个方面进行汇报。", quote=True)

# 第2页
doc_title("第 2 页 · 个人研究背景与专业优势（约 1 分钟）", 1)
doc_paragraph("首先做一下自我介绍，我的专业是计算数学，研究方向是基于机器学习的图像处理、识别与分割，主要包括以下几个方面：", quote=True)
doc_paragraph("第一，文档图像识别与版面分析：研究如何从扫描的文档、表格中自动提取结构化信息，涉及图像预处理、版面分割、OCR识别等技术。", quote=True)
doc_paragraph("第二，目标检测与分割：研究如何从图像中定位并分割出感兴趣的区域，比如签名区、印章区、证件照片等。", quote=True)
doc_paragraph("第三，深度学习模型部署与优化：研究如何将训练好的模型轻量化、加速，使其能在普通办公电脑甚至内网服务器上高效运行。", quote=True)
doc_paragraph("做这个信息管理系统的过程中，我也一直尝试将这些研究方向和单位的实际需求结合起来。下面我具体汇报一下。", quote=True)

# 第3页
doc_title("第 3 页 · 项目建设背景（约 1.5 分钟）", 1)
doc_paragraph("我们建设这套系统的初衷，源于传统办公模式的几个长期痛点：", quote=True)
doc_paragraph("第一，人员信息分散。员工档案以纸质或Excel形式散落在各科室，查档跑多部门，更新不及时，版本不一致。", quote=True)
doc_paragraph("第二，表单收集靠人工。每月工资条确认、季度考核表这类工作，人事下发、收集、汇总，一份8人的小表要花30分钟以上，效率很低。", quote=True)
doc_paragraph("第三，审批流程纸质化。请假、用章、出差等申请，申请人拿着单子跑领导签字，进度不透明，追溯困难。", quote=True)
doc_paragraph("第四，纸质档案数字化难。大量历史手写档案、表格、证件复印件需要手工录入，耗时耗力，容易出错。——这一条正是我研究方向能发挥作用的地方。", quote=True)
doc_paragraph("第五，信息安全有隐患。邮件、微信群传输敏感信息，缺乏权限管控和操作审计，出了问题无法追溯。", quote=True)
doc_paragraph("基于以上痛点，我们的建设目标是：人员档案数字化、审批流程在线化、表单收集智能化、纸质文档识别自动化。", quote=True)

# 第4页
doc_title("第 4 页 · 系统核心功能概览（约 1.5 分钟）", 1)
doc_paragraph("目前系统已实现六大核心模块，基本覆盖了单位日常办公的主要场景。", quote=True)
doc_paragraph("第一，人员档案管理。全员电子档案，支持自定义扩展字段，简历自动识别填充，人事批量导入一键建档。", quote=True)
doc_paragraph("第二，OA流程审批。已上线请假、报销、用章、出差四类标准流程，审批人自动匹配——根据申请人所在部门，系统自动找到部门负责人、人事、财务，不需要手工配置每个节点。", quote=True)
doc_paragraph("第三，智能表格。上传现成的Word/Excel模板，系统自动识别字段，下发填写、自动汇总、按原模板导出，解决'发-填-收'难题。近期还引入了AI智能生成表格，输入一句话就能生成出差申请、加班申请、物资领用等表单。", quote=True)
doc_paragraph("第四，组织架构管理。单位、部门、岗位、职级一体化管理，审批流程的自动匹配就是基于这套架构。", quote=True)
doc_paragraph("第五，统计报表。上传Excel报表模板，系统自动完成字段匹配并导出带格式的报表，支持花名册、党员名册、学历统计等多种常用报表。", quote=True)
doc_paragraph("第六，系统安全。这也是近期刚完成的一轮全面加固，我后面会详细介绍。", quote=True)
doc_paragraph("技术栈：后端 Python FastAPI，前端 Vue 3，单文件数据库部署，内网服务器上直接运行，维护成本低。", quote=True)

# 第5页
doc_title("第 5 页 · 现场功能演示（约 3-4 分钟）", 1)
doc_paragraph("接下来我打开系统，现场演示几个核心流程，重点演示和我研究方向相关的智能识别部分。", quote=True)
doc_paragraph("演示分四块：", quote=True)
doc_paragraph("第一块，人员档案+简历自动识别。打开人员档案，上传一份Word或PDF简历，看系统如何自动提取姓名、学历、工作经历等字段。", quote=True)
doc_paragraph("（操作：我的信息 → 上传简历 → 预览识别结果 → 确认保存）",
              bold=True, color=DocxRGB(0x2B, 0x57, 0x8A))
doc_paragraph("第二块，AI智能表格生成。这是近期新做的功能，输入'创建一份年度考核表'，看系统如何基于关键词自动匹配并生成包含姓名、部门、职务、工作总结等字段的完整表格。——这个功能用到的就是文本语义匹配+场景分类，属于机器学习的基础能力。", quote=True)
doc_paragraph("（操作：智能表格 → AI创建 → 输入'年度考核表' → 看推荐结果 → 保存）",
              bold=True, color=DocxRGB(0x2B, 0x57, 0x8A))
doc_paragraph("第三块，审批流程。演示一个请假申请，从员工发起，到部门领导审批、人事审批，看时间轴的流转记录。", quote=True)
doc_paragraph("（操作：员工发请假 → 领导审批 → 人事审批 → 看进度时间轴）",
              bold=True, color=DocxRGB(0x2B, 0x57, 0x8A))
doc_paragraph("第四块，报表智能匹配。上传一份花名册Excel模板，看系统如何自动匹配表头和系统字段，最后一键导出。", quote=True)
doc_paragraph("（操作：报表模板 → 上传Excel → 看自动匹配结果 → 生成报表 → 下载）",
              bold=True, color=DocxRGB(0x2B, 0x57, 0x8A))
doc_paragraph("演示完成后回到PPT：好，这四块核心流程就是这样。接下来汇报近期我们做的一轮系统性安全加固。", quote=True)

# 第6页
doc_title("第 6 页 · 近期完成的安全加固（7项）（约 1.5 分钟）", 1)
doc_paragraph("近期针对体制内单位的特殊要求，我对系统做了7项关键的安全和可靠性加固，确保系统上线后'不出差错、可管可控'。", quote=True)
doc_paragraph("第一，审计日志系统。超管可以在系统里看到所有人的操作记录——谁、在什么IP、什么时候、做了什么操作，包括修改前后的具体值变化。登录日志也同样完整记录，包括成功失败、失败原因。这是体制内信息系统的硬性要求——可追溯。", quote=True)
doc_paragraph("第二，数据库备份机制。超管界面有'数据备份'按钮，一键备份、下载、删除，备份文件按时间戳命名，存在服务器专门的备份目录。后面我还会加自动定时备份。", quote=True)
doc_paragraph("第三，会话超时机制。30分钟无操作自动登出，提前1分钟弹窗提醒——这是涉密信息系统的标配，防止人离开电脑后被他人操作。", quote=True)
doc_paragraph("第四，生产环境配置模板。提供了 .env.production 配置文件，部署时只需修改密钥、密码、数据库地址。", quote=True)
doc_paragraph("第五，生产环境关闭API文档。正式环境下 /docs、/openapi.json 自动禁用，防止接口信息泄露。", quote=True)
doc_paragraph("第六，CORS来源锁定。跨域访问从'允许所有'改为'仅允许配置的内网地址'，并收紧HTTP方法。", quote=True)
doc_paragraph("第七，报表导出准确性修复。解决了自定义字段不填充、软删除数据泄露、模板旧数据残留三个bug，导出的报表确保准确。", quote=True)
doc_paragraph("这7项做完之后，系统在安全和可靠性上基本达到了内网部署的要求。", quote=True)

# 第7页
doc_title("第 7 页 · 已实现的AI能力（结合研究方向）（约 1 分钟）", 1)
doc_paragraph("在现有系统中，我已经初步应用了一些和研究方向相关的技术能力，虽然目前还属于基础版，但为后续深度应用打好了框架。", quote=True)
doc_paragraph("第一，简历文档智能解析。上传Word/PDF简历，系统自动提取40+个字段（姓名、性别、学历、工作经历等）。——这其中用到了文档版面分析、文本结构化提取等技术。", quote=True)
doc_paragraph("第二，报表模板表头自动匹配。上传一份Excel模板，系统自动把'出生年月''籍贯''手机'等表头和系统的标准字段做匹配，置信度达到0.95以上的自动确认。——这里用到了三级匹配策略：精确匹配→同义词词典→模糊相似度，核心算法是字符串相似度计算，是机器学习中模式匹配的基础方法。", quote=True)
doc_paragraph("第三，AI智能表单生成。用户输入自然语言（如'创建一份物资领用表'），系统自动匹配到预置的10种业务场景，并生成相应的字段结构和自动填充规则。——这里用到了多关键词场景分类，后续可以用分类模型替换。", quote=True)
doc_paragraph("第四，身份证号合法性校验。内置了18位身份证号的校验码算法，自动校验格式、提取出生日期、计算年龄——属于基础的结构化数据验证能力。", quote=True)
doc_paragraph("这些能力目前还主要是基于规则+传统算法实现的，后面结合我研究的深度学习模型，在识别准确率和处理复杂度上会有质的提升。", quote=True)

# 第8页
doc_title("第 8 页 · 基于研究方向的未来规划（重点，约 2 分钟）", 1)
doc_paragraph("接下来汇报结合我机器学习图像处理研究方向，未来半年到一年，我计划在系统里做的几件具体事情，每一件都能直接解决单位的实际痛点。", quote=True)

doc_paragraph("第一，手写表格识别（OCR + 版面分割）——这是优先级最高的。", bold=True, color=DocxRGB(0x2D, 0x5A, 0x27))
doc_paragraph("单位有大量历史存档的手写登记表（入职表、履历表、考核表等），目前如果要录入系统需要人工逐字敲，一份表格要半小时。我计划开发手写表格识别模块：第一步扫描件图像预处理（去噪、倾斜校正、二值化、增强）；第二步版面分割（用实例分割模型，自动切分出表格的每个单元格）；第三步手写字符识别（用CRNN或类似的序列识别模型，识别中文/数字/日期）；最后自动回填到系统的人员档案中，人工只需审核和修正。预期效果：一份手写表格的录入时间从30分钟降到1-2分钟，准确率达到95%以上。", quote=True)

doc_paragraph("第二，证件文档自动识别与校验。", bold=True, color=DocxRGB(0x2D, 0x5A, 0x27))
doc_paragraph("人事录入身份证、学位证、毕业证这些，经常要核对信息。我计划做一个证件识别模块：上传证件照片或扫描件，自动检测证件类型、定位四角、做透视变换（分割+对齐），然后识别出身份证号、姓名、证件有效期等字段，同时自动和已录入的档案信息做比对校验，发现不一致自动提示。这样既提高效率，又防止录入错误。", quote=True)

doc_paragraph("第三，手写签名验证。", bold=True, color=DocxRGB(0x2D, 0x5A, 0x27))
doc_paragraph("审批流程中，现在很多单位还是要打印出来签字再扫描回来。我计划做手写签名验证：每个人首次登录时在手写板或手机上留下3-5个签名样本，建立签名特征库；审批上传签名扫描件时，系统用图像相似度匹配+特征提取的方法判断签名真伪，给管理员辅助参考；后续可以进一步发展为在线电子签名，彻底不需要打印签字。", quote=True)

doc_paragraph("第四，人像与证照比对（人脸识别）。", bold=True, color=DocxRGB(0x2D, 0x5A, 0x27))
doc_paragraph("人员档案里一般都有证件照，我们可以做人脸识别校验：新人入职上传照片时，自动和身份证照片比对，确认是本人；内部会议签到、考勤打卡，可以对接人脸识别；这部分用到的是人脸检测+特征提取+比对的深度学习模型，部署在内网服务器即可。", quote=True)

doc_paragraph("第五，纸质档案批量数字化。", bold=True, color=DocxRGB(0x2D, 0x5A, 0x27))
doc_paragraph("对于历史存档的大量纸质档案，做一个批量档案数字化工具：批量扫描 → 自动检测页面类型（履历表/审批单/证件复印件等）→ 自动分割关键信息区域 → OCR识别 → 自动归档到对应的人员档案下。——这里面用到的图像分类、目标检测、版面分割，都是我研究方向的核心内容。", quote=True)

# 第9页
doc_title("第 9 页 · 对单位数智化发展的贡献设想（约 1 分钟）", 1)
doc_paragraph("最后，站在单位数智化发展的角度，我认为我的研究方向可以在以下三个层面持续贡献：", quote=True)

doc_paragraph("第一层，档案全面数字化升级。", bold=True, color=DocxRGB(0x2D, 0x5A, 0x27))
doc_paragraph("解决'从纸到数'的核心难题——这是目前很多单位数智化的最大瓶颈。通过手写识别、版面分割、证件识别，把历史存量档案快速电子化，让信息系统有数据可用。", quote=True)

doc_paragraph("第二层，办公流程深度智能化。", bold=True, color=DocxRGB(0x2B, 0x57, 0x8A))
doc_paragraph("在现有系统的基础上，逐步引入：自然语言问答（领导问'去年单位谁休了病假？'，系统直接生成报表）；智能预警（身份证过期、证件到期、合同续签、退休年龄临近等自动提醒）；审批智能辅助（根据历史审批记录，自动给出审批建议，减少领导决策负担）。", quote=True)

doc_paragraph("第三层，数据安全与隐私保护。", bold=True, color=DocxRGB(0xC9, 0xA5, 0x4F))
doc_paragraph("结合图像处理和密码学，做一些敏感数据的保护：证件照片上传后自动脱敏（身份证号打码、人脸模糊）后再存储；敏感图像采用轻量级加密存储，有权限的人才能查看原图；操作日志中的图像也做加密，确保隐私合规。", quote=True)

doc_paragraph("以上所有技术，我都可以基于开源模型在内网部署，不需要调用外部API，完全符合单位的涉密内网要求——这一点非常关键，所有数据都不出内网。", quote=True)

# 第10页
doc_title("第 10 页 · 总结（约 40 秒）", 1)
doc_paragraph("最后做一个总结，用三句话概括。", quote=True)
doc_paragraph("第一，当前进展：六大核心模块开发完成，7项安全加固到位，系统已具备内网上线试运行的条件。", bold=True, quote=True)
doc_paragraph("第二，专业结合：系统中已经初步应用了文档识别、字段匹配、场景分类等技术，后续将持续结合我机器学习图像处理的研究方向，解决手写识别、证件识别、签名验证等实际痛点。", bold=True, quote=True)
doc_paragraph("第三，下一步计划：立即部署上线、小范围试运行，优先推进手写表格识别模块的落地，逐步完成从'有系统'到'有智能系统'的跨越。", bold=True, quote=True)
doc_paragraph("以上是我的汇报，请各位领导批示。谢谢大家！", quote=True)

# 附：时长分配
doc.add_page_break()
doc_title("附：时长分配建议", 1)
table = doc.add_table(rows=11, cols=3)
table.style = 'Light Grid Accent 1'
hdr_cells = table.rows[0].cells
hdr_cells[0].text = '页面'
hdr_cells[1].text = '内容'
hdr_cells[2].text = '时长'
data = [
    ('第1页','封面','0.5 分钟'),('第2页','个人研究背景（新）','1.0 分钟'),
    ('第3页','项目背景','1.5 分钟'),('第4页','系统功能概览','1.5 分钟'),
    ('第5页','功能演示（现场操作）','3.5 分钟'),('第6页','7项安全加固（新）','1.5 分钟'),
    ('第7页','已实现AI能力（新）','1.0 分钟'),('第8页','未来规划（重点）','2.0 分钟'),
    ('第9页','数智化贡献设想（新）','1.0 分钟'),('第10页','总结','0.7 分钟'),
]
for i, (a, b, c) in enumerate(data):
    r = table.rows[i+1].cells
    r[0].text, r[1].text, r[2].text = a, b, c

doc.add_paragraph()
doc_title("汇报小贴士", 2)
tips = [
    "第8页（手写表格识别）是亮点，讲的时候可以放慢一点，让领导意识到这是你专业的独特价值，是别的程序员做不了的。",
    "强调'内网部署、数据不出单位'，这对体制内非常重要——领导最担心数据安全。",
    "建议在PPT第8页配一张图：左边放一张手写表格扫描件，右边放识别后的结构化效果（哪怕是模拟的），视觉冲击很强。",
    "如果被问到'手写识别能达到多少准确率'，可以回答：印刷体98%以上，工整手写体90%-95%，潦草手写体需要针对我们单位样本做模型微调，预计能到85%-90%以上，最后人工复核一下就可以了。——这个回答比较稳妥，不说死。",
    "如果被问到'和AI公司做的有什么区别'，可以回答：第一，所有模型和算法自主可控，部署在内网，不需要调外部API，满足保密要求；第二，我可以针对单位的实际数据和场景做定制化微调和迭代，通用AI公司做不到这么深入和灵活。",
]
for i, t in enumerate(tips, 1):
    doc_paragraph(f"{i}. {t}", size=11)

doc.save(DOC_FILE)
print(f"[OK] DOC saved: {DOC_FILE}")
print(f"     Size: {os.path.getsize(DOC_FILE)/1024:.1f} KB")
