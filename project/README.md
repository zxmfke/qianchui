# 千锤·营销话术AI操作系统

营销话术全生命周期管理平台，基于 AI 赋能话术的创建、推荐、诊断、培训与演练。

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React 18 + TypeScript + Ant Design |
| 后端 | Python 3.11 + FastAPI + SQLAlchemy 2.0 (async) |
| 数据库 | PostgreSQL 16 + pgvector（向量检索） |
| 缓存 | Redis 7 |
| AI | OpenAI API / 兼容接口（可切换模型提供商） |
| 部署 | Docker Compose + Nginx 反向代理 |
| 测试 | Pytest (async) + Eval 框架 |

## 项目结构

```
千锤·营销话术AI操作系统/
├── docker-compose.yml       # 容器编排
├── .env.example             # 环境变量模板
├── nginx/
│   └── nginx.conf           # Nginx 反向代理配置
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini          # 数据库迁移配置
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/        # 迁移版本文件
│   ├── app/
│   │   ├── main.py          # FastAPI 入口
│   │   ├── core/            # 配置、安全、依赖
│   │   ├── models/          # SQLAlchemy 模型
│   │   ├── schemas/         # Pydantic 模式
│   │   ├── api/             # API 路由
│   │   ├── services/        # 业务逻辑
│   │   └── skills/          # AI Skill 模块
│   ├── tests/               # 单元/集成测试
│   └── evals/               # AI 能力 Eval 框架
└── frontend/
    ├── Dockerfile
    ├── package.json
    ├── src/
    │   ├── pages/           # 页面组件
    │   ├── components/      # 通用组件
    │   ├── services/        # API 调用
    │   └── stores/          # 状态管理
    └── public/
```

## 快速开始

### 1. 克隆并配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env，填入真实的 API Key 和 JWT Secret
```

### 2. Docker Compose 一键启动

```bash
docker compose up -d
```

启动后访问：

| 服务 | 地址 |
|------|------|
| 前端应用 | http://localhost |
| 后端 API | http://localhost/api |
| API 文档 (Swagger) | http://localhost/docs |
| 数据库 | localhost:5432 |
| Redis | localhost:6379 |

### 3. 初始化数据库

```bash
# 进入后端容器执行迁移
docker compose exec backend alembic upgrade head
```

## 开发模式

### 后端开发

```bash
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 启动开发服务器（需要本地 PostgreSQL 和 Redis）
uvicorn app.main:app --reload --port 8000
```

### 前端开发

```bash
cd frontend

npm install
npm run dev
```

### 运行测试

```bash
cd backend

# 运行全部测试
pytest -v

# 运行特定模块测试
pytest tests/test_auth.py -v

# 运行 AI Eval
python evals/run_all.py
```

## 环境变量说明

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DATABASE_URL` | PostgreSQL 异步连接串 | `postgresql+asyncpg://...` |
| `REDIS_URL` | Redis 连接串 | `redis://redis:6379/0` |
| `SECRET_KEY` | JWT 签名密钥（**生产环境必须修改**） | - |
| `ALGORITHM` | JWT 算法 | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token 过期时间（分钟） | `1440` |
| `LLM_PROVIDER` | AI 模型提供商 | `openai` |
| `LLM_MODEL` | 默认模型名称 | `gpt-4o-mini` |
| `LLM_API_BASE` | 模型 API 地址 | `https://api.openai.com/v1` |
| `LLM_API_KEY` | 模型 API Key | - |
| `LLM_TEMPERATURE` | 模型温度参数 | `0.7` |
| `CORS_ORIGINS` | 允许的跨域来源 | `["http://localhost:3000"]` |

## API 文档

启动服务后访问 **http://localhost/docs** 查看 Swagger 交互式文档。

主要模块：

- `/api/auth` — 认证（注册、登录、Token 刷新）
- `/api/scripts` — 话术管理（CRUD、搜索、版本）
- `/api/conversations` — AI 对话（流式 SSE）
- `/api/training` — 培训任务
- `/api/practice` — 模拟演练
- `/api/dashboard` — 数据看板
- `/api/enterprise` — 企业管理

## 贡献指南

1. 从 `main` 分支创建 feature 分支：`git checkout -b feature/xxx`
2. 编写代码并补充测试
3. 确保所有测试通过：`pytest -v`
4. 提交 PR 并描述改动内容
5. Code Review 通过后合并

### 代码规范

- Python: 遵循 PEP 8，使用 `ruff` 格式化
- TypeScript: 使用 ESLint + Prettier
- 提交信息: `<type>(<scope>): <description>`，如 `feat(scripts): 添加话术版本管理`
