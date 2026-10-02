# 人员基本信息系统

单位人员基本信息统一管理平台 —— 解决反复录入、手工填表的痛点，实现一次录入、自动填表、智能识别。

## 核心功能

| 模块 | 功能 | 状态 |
|------|------|------|
| 模块1 账号权限 | 三级权限（超管/单位管理员/普通用户）+ 名单匹配免审核注册 | ✅ 已实现 |
| 模块2 信息存储 | 核心字段 + 自定义字段动态扩展 + 多段子表（家庭/学历/工作经历/奖惩） | ✅ 已实现 |
| 模块3 自动填表 | Excel 模板上传 → 智能字段匹配 → 自动填充生成报表 + 聚合统计 | ✅ 已实现 |
| 模块4 信息维护 | 派生字段实时计算（年龄/工龄）+ 字段级变更历史 + 身份证联动回填 | ✅ 已实现 |
| 模块5 简历表导入 | 批量简历表模板化处理 + 多段时间格式自适应解析 | 🔜 二期 |
| 模块6 业务扩展 | 休假/福利/晋升（插件化架构预留） | 🔜 三期+ |

## 技术栈

- **后端**：Python 3.11+ / FastAPI / SQLAlchemy / openpyxl / python-docx
- **前端**：Vue 3 / Vite / Element Plus / ECharts / Pinia
- **数据库**：开发用 SQLite，部署用 PostgreSQL
- **认证**：JWT

## 快速开始

### 1. 启动后端

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

首次启动会自动建表并创建超级管理员：**admin / admin123**

- API 文档：http://127.0.0.1:8000/docs

### 2. 启动前端

```bash
cd frontend
npm install
npm run dev
```

- 访问：http://127.0.0.1:5173

### 3. 典型使用流程

```
超级管理员登录
  → 创建单位（如"一年级一班"）
  → （可选）创建单位管理员账号

单位管理员登录
  → 预导入本单位名单（姓名+身份证号）

普通用户注册
  → 填用户名/密码/姓名/身份证号 → 匹配名单 → 自动绑定单位 → 填写个人信息

单位管理员
  → 查看/修改本单位人员信息
  → 上传统计表 Excel 模板 → 智能匹配字段 → 生成报表下载
```

## 项目结构

```
人员基本信息系统/
├── backend/
│   ├── app/
│   │   ├── main.py              应用入口（含初始化）
│   │   ├── __init__.py          配置
│   │   ├── database.py          数据库连接
│   │   ├── core/                安全/权限/身份证工具
│   │   ├── models/              数据模型（user/person/report）
│   │   ├── schemas/             Pydantic 校验模型
│   │   ├── routers/             API 路由（auth/units/persons/...）
│   │   └── services/            字段匹配引擎/表格解析
│   ├── uploads/                 上传文件存储
│   ├── requirements.txt
│   ├── test_api.py              接口流程测试
│   └── test_report.py           报表流程测试
├── frontend/
│   └── src/
│       ├── api/                 axios 封装
│       ├── stores/              Pinia（auth）
│       ├── router/              路由+权限守卫
│       ├── layouts/             主布局（侧边栏菜单）
│       ├── components/          通用组件（人员表单对话框）
│       └── views/               页面
└── docs/plans/                  架构设计文档
```

## 关键设计说明

### 数据隔离
后端按 `unit_id` 强制过滤，单位管理员只能访问本单位数据，不依赖前端控制。

### 字段动态扩展
核心字段存主表（查询高效），自定义字段存键值对表（增删不改库结构）。

### 身份证联动
输入身份证号自动校验 18 位校验位，并回填出生日期和性别（注册、新增、修改均生效）。

### 报表智能匹配
三级匹配策略：精确匹配 → 同义词词典（"文化程度"→学历）→ 模糊相似度。置信度 ≥0.95 自动确认，0.6~0.95 待确认，<0.6 标红人工指定。

### 变更历史
所有字段级修改自动记录操作人、旧值、新值、原因，可追溯。

## 部署到服务器

1. 后端用 PostgreSQL：设置环境变量 `DATABASE_URL=postgresql://user:pass@host:5432/dbname`
2. 生产关闭 debug：`DEBUG=False`，并修改 `SECRET_KEY`
3. 前端打包：`npm run build`，产物部署到 Nginx
4. Nginx 配置：`/` 托管前端静态文件，`/api` 反向代理到 FastAPI:8000
5. 启用 HTTPS

详见 `docs/plans/2026-07-27-人员基本信息系统-架构设计.md`。
