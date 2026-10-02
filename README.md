# 人员信息管理系统（内网版）

单位人员基本信息统一管理平台 —— 解决反复录入、手工填表的痛点，实现一次录入、自动填表、智能识别、涉密分级管控、AI 智能问答。

> **版本**: v2.0  
> **适用环境**: 内网 Windows / 无外网依赖  
> **Python**: 3.11+ | **Node.js**: 18+

---

## 功能清单

| 模块 | 功能 | 说明 |
|------|------|------|
| 账号权限 | 三级权限（超管/单位管理员/普通用户）+ 名单匹配免审核注册 | JWT 认证，首次登录强制改密 |
| 人员档案 | 核心字段 + 自定义字段 + 多段子表（家庭/学历/工作经历/奖惩） | 派生字段自动计算（年龄/工龄） |
| 自动填表 | Excel/Word 模板上传 → 智能字段匹配 → 自动填充 | 三级匹配策略，置信度阈值控制 |
| 变更历史 | 字段级修改记录，可追溯旧值/新值/操作人/原因 | 审计留痕 |
| 组织架构 | 部门管理、岗位管理、职级管理 | 支持编制人数与实有人数对比 |
| 通知公告 | 发布/阅读/置顶/撤回 | 管理员可查看阅读统计 |
| 待办事项 | 个人待办清单，支持完成/删除/新建 | 支持按状态筛选 |
| 流程审批 | 请假/报销/出差等审批流程，多级审批人 | 工作流引擎，支持驳回/通过/转办 |
| 智能表格 | 自定义表单模板，动态字段 + 数据收集 | 支持导出 Excel |
| 报销管理 | 费用报销申请，多级审批，支持附件 | 与审批流联动 |
| 涉密分级 | 数据字段打密级标签（公开/内部/秘密/机密） | 用户 ClearanceLevel 控制访问权限，导出自动脱敏 |
| **AI 智能助手** | **本地大模型 + RAG 知识库问答** | **Qwen2-0.5B + BGE 中文 Embedding，不依赖外网** |
| 知识库管理 | 文档上传/入库/删除，支持多格式 | 语义分块 + 向量检索 |
| 系统监控 | 操作日志、数据库备份、服务状态 | 管理员可查看全站日志 |

---

## 技术栈

### 后端
| 组件 | 版本/型号 | 用途 |
|------|-----------|------|
| Python | 3.11+ | 运行环境 |
| FastAPI | 0.109+ | Web 框架 |
| SQLAlchemy | 2.0+ | ORM |
| PyTorch | 2.3+ | 本地大模型推理 |
| Transformers | 4.44+ | 模型加载（Qwen2-0.5B-Instruct） |
| ChromaDB | 0.5+ | 向量数据库 |
| BGE Embedding | bge-small-zh-v1.5 | 中文语义向量编码 |
| openpyxl / python-docx | - | 报表生成 |
| JWT / bcrypt | - | 认证与密码哈希 |

### 前端
| 组件 | 版本 | 用途 |
|------|------|------|
| Vue 3 | 3.4+ | 框架 |
| Vite | 5.0+ | 构建工具 |
| Element Plus | 2.5+ | UI 组件库 |
| Pinia | 2.1+ | 状态管理 |
| Vue Router | 4.2+ | 路由 |
| ECharts | 5.4+ | 图表 |
| Axios | 1.6+ | HTTP 客户端 |

### 数据库
- **开发**: SQLite（`backend/person_info.db`）
- **生产**: PostgreSQL（推荐）

---

## 快速开始

### 1. 环境准备

```bash
# Python 3.11+
python --version

# Node.js 18+
node --version
```

### 2. 启动后端

```bash
cd backend
pip install -r requirements.txt

# 首次启动会自动建表、创建测试数据
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

- API 文档: http://127.0.0.1:8000/docs
- 托管前端: http://127.0.0.1:8000

### 3. 启动前端（开发调试用）

```bash
cd frontend
npm install
npm run dev
```

- 开发地址: http://127.0.0.1:5173

> 生产环境只需启动后端，前端页面由后端托管（`backend/app/main.py` 已配置 StaticFiles）。

### 4. 典型使用流程

```
超级管理员(admin) 登录
  → 创建单位 → 创建部门/岗位/职级
  → 创建单位管理员账号
  → 上传知识库文档 → 执行"重建知识库"

单位管理员登录
  → 预导入本单位人员名单（姓名+身份证号）
  → 发布通知公告

普通用户注册
  → 填用户名/密码/姓名/身份证号
  → 匹配名单 → 自动绑定单位 → 填写个人信息

单位管理员
  → 查看/修改本单位人员信息
  → 上传统计表模板 → 智能匹配字段 → 生成报表
  → 审批下属的请假/报销申请

所有用户
  → AI 智能助手 → 查询制度/流程/操作指南
```

---

## 项目结构

```
person-info-system/
├── .gitignore                 # Git 排除规则（敏感文件/大模型/构建产物）
├── README.md                  # 本文件
├── START.bat                  # 一键启动（后端+前端）
├── INSTALL_SERVICE.bat        # 安装 Windows 开机自启服务
├── launcher.py                # 服务启动器（带看门狗）
├── deploy_service.py          # 服务部署/检查脚本
│
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI 入口（初始化+挂载静态文件）
│   │   ├── database.py        # 数据库连接（SQLite/PostgreSQL）
│   │   ├── core/              # 安全/权限/身份证工具/日志
│   │   ├── models/            # SQLAlchemy 数据模型
│   │   ├── schemas/           # Pydantic 校验模型
│   │   ├── routers/           # API 路由（20+ 模块）
│   │   │   ├── auth.py        # 登录/注册/JWT
│   │   │   ├── persons.py     # 人员档案 CRUD + 脱敏
│   │   │   ├── workflow.py    # 审批流程
│   │   │   ├── ai_router.py   # AI 问答 + 知识库管理
│   │   │   └── ...
│   │   └── services/          # 业务逻辑层
│   │       ├── ai_service.py  # RAG 知识库 + 本地大模型推理
│   │       └── ...
│   ├── storage/               # 数据存储（不上传到 Git）
│   │   ├── attachments/       # 附件（*.pdf, *.xlsx）
│   │   ├── knowledge_base/    # 知识库文档 + 向量索引
│   │   │   ├── docs/          # 原始文档（.txt/.md/.pdf）
│   │   │   └── chromadb/      # 向量数据库（ChromaDB）
│   │   └── models/            # 大模型文件（.bin/.safetensors）
│   │       ├── Qwen2-0.5B-Instruct/
│   │       └── bge-small-zh-v1.5/
│   ├── requirements.txt
│   └── person_info.db         # SQLite 数据库（.gitignore 排除）
│
├── frontend/
│   ├── src/
│   │   ├── api/               # axios 封装 + 各模块 API
│   │   ├── stores/            # Pinia 状态管理
│   │   ├── router/            # 路由 + 权限守卫
│   │   ├── views/             # 页面组件（30+ 页面）
│   │   └── App.vue
│   ├── package.json
│   └── vite.config.js
│
└── docs/                      # 项目文档
    ├── 系统使用手册与首测清单.md
    ├── 系统功能差距分析与建设规划.md
    └── plans/                 # 架构设计文档
```

---

## 关键设计

### 涉密分级管控
- **数据密级**: 0=公开, 1=内部, 2=秘密, 3=机密
- **用户 ClearanceLevel**: 0~3，决定可访问的最高密级
- **字段级标签**: `sensitive_level` 标记每个字段的密级
- **访问控制**: 后端强制过滤，低密级用户看不到高密级字段值（显示为 `****`）
- **导出脱敏**: 导出 Excel/Word 时自动根据用户密级脱敏
- **特殊规则**: 用户始终可查看自己的档案，且不对自己的档案脱敏

### AI 智能问答（RAG）
- **本地大模型**: Qwen2-0.5B-Instruct，PyTorch 直接加载
- **Embedding 模型**: BAAI/bge-small-zh-v1.5，中文语义优化
- **向量库**: ChromaDB，384 维向量存储
- **分块策略**: 按标题/段落/句子三级语义分块（非固定长度）
- **查询改写**: 关键词扩展 + 同义词补充，提升召回率
- **回答规则**: 必须引用知识库来源，不得编造，区分通用知识

### 数据隔离
- 后端按 `unit_id` 强制过滤，单位管理员只能访问本单位数据
- 超管（`super_admin`）可跨单位查看

### 字段动态扩展
- 核心字段存主表（查询高效）
- 自定义字段存键值对表（增删不改库结构）

---

## 生产部署

1. **数据库**: PostgreSQL，设置环境变量 `DATABASE_URL=postgresql://user:pass@host:5432/dbname`
2. **关闭调试**: `DEBUG=False`，修改 `SECRET_KEY`
3. **前端打包**: `npm run build`，产物自动由后端托管
4. **Nginx 配置**（可选）: `/` 托管前端静态文件，`/api` 反向代理到 FastAPI:8000
5. **Windows 自启**: 运行 `INSTALL_SERVICE.bat` 安装计划任务
6. **HTTPS**: 生产环境启用

详见 [docs/技术手册.md](docs/技术手册.md)。

---

## 账号密码速查

> ⚠️ 仅交接/测试使用，部署后立即修改！

| 账号 | 密码 | 角色 | 说明 |
|------|------|------|------|
| `admin` | `Test@1234` | super_admin | 超级管理员，等级3（机密） |
| `leader` | `Test@1234` | super_admin | 张局长，超管权限 |
| `leader_01` ~ `leader_03` | `Test@1234` | unit_admin | 单位管理员（局领导） |
| `bgs_leader` | `Test@1234` | person | 王科长，流程第一道审批 |
| `hr_01` / `cw_01` | `Test@1234` | person | 人事/财务审批人 |
| `office_01` ~ `office_05` | `Test@1234` | person | 办公室员工 |
| `finance_01` ~ `finance_04` | `Test@1234` | person | 财务处员工 |
| `test_user_1` ~ `test_user_3` | `test123` | person | 首次登录需改密 |

完整列表见 [docs/技术手册.md#账号密码清单](docs/技术手册.md)。

---

## 交接要点

1. **代码仓库**: 本仓库（不含 `storage/` 大模型文件，需同事手动下载）
2. **必装依赖**: Python 3.11+、Node.js 18+、Git
3. **必配环境**: `BGE_MODEL_PATH` 指向 `bge-small-zh-v1.5` 文件夹（若路径不同）
4. **启动方式**: `START.bat` 或 `python launcher.py`
5. **常见问题**: 见 [docs/技术手册.md#常见问题](docs/技术手册.md)
6. **系统文档**: `docs/` 目录下所有 `.md` 文件

---

## License

仅供内部使用，未经授权不得外传。
