# 千锤·营销话术AI操作系统 — 部署指南

## 系统要求

| 组件 | 最低要求 |
|------|---------|
| 操作系统 | Linux (Ubuntu 20.04+) / macOS / Windows 10+ |
| Docker | 20.10+ |
| Docker Compose | v2.0+ |
| 内存 | 4GB+ |
| 磁盘 | 10GB+ |

## 快速部署（3 步完成）

### 第 1 步：准备环境变量

```bash
# 复制示例配置
cp .env.example .env

# 编辑配置（必须修改 LLM_API_KEY）
vi .env
```

**必须配置的项目：**

| 变量 | 说明 | 示例 |
|------|------|------|
| `LLM_API_KEY` | AI 大模型 API Key | `sk-xxx` |
| `SECRET_KEY` | JWT 签名密钥（生产环境必改） | `openssl rand -hex 32` 生成 |

**可选配置：**

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `LLM_PROVIDER` | `openai` | 模型提供商（openai/azure/deepseek） |
| `LLM_API_BASE` | `https://api.openai.com/v1` | API 地址（国内可用代理） |
| `LLM_MODEL` | `gpt-4` | 模型名称 |
| `POSTGRES_PASSWORD` | `qianchui123` | 数据库密码（生产环境必改） |
| `HTTP_PORT` | `80` | 对外服务端口 |

### 第 2 步：构建并启动

```bash
# 构建所有镜像并后台启动
docker compose up -d --build

# 查看服务状态
docker compose ps
```

正常启动后应看到 5 个容器全部 `running`：

```
qianchui-postgres   ✓ running (healthy)
qianchui-redis      ✓ running (healthy)
qianchui-backend    ✓ running
qianchui-frontend   ✓ running
qianchui-nginx      ✓ running
```

### 第 3 步：初始化数据（可选）

系统启动时会**自动创建超级管理员账号**（superadmin / kst@2026），无需手动操作。

如果需要填充演示数据：

```bash
# 进入后端容器执行种子数据脚本
docker compose exec backend python seed_data.py
```

## 访问系统

| 入口 | 地址 | 说明 |
|------|------|------|
| 前台应用 | `http://localhost` | 普通用户使用 |
| 超管后台 | `http://localhost` → 用超管账号登录自动跳转 | 系统管理 |
| API 文档 | `http://localhost/docs` | Swagger UI |
| 健康检查 | `http://localhost/health` | 服务状态 |

## 账号信息

| 角色 | 用户名 | 密码 | 说明 |
|------|--------|------|------|
| 超级管理员 | `superadmin` | `kst@2026` | 启动时自动创建，管理所有企业和用户 |
| 演示管理员 | `demo` | `demo123456` | 运行 seed_data.py 后可用 |
| 团队成员 | `张明`/`李婷`/`王浩`/`刘芳` | `demo123456` | 运行 seed_data.py 后可用 |

## 运维操作

### 查看日志

```bash
# 查看所有服务日志
docker compose logs -f

# 查看单个服务日志
docker compose logs -f backend
docker compose logs -f postgres
```

### 数据库备份

```bash
# 导出
docker compose exec postgres pg_dump -U qianchui qianchui > backup_$(date +%Y%m%d).sql

# 恢复
cat backup_20260313.sql | docker compose exec -T postgres psql -U qianchui qianchui
```

### 更新部署

```bash
# 拉取最新代码后重新构建
git pull
docker compose up -d --build
```

### 停止/销毁

```bash
# 停止所有服务（保留数据）
docker compose down

# 停止并删除所有数据（谨慎操作）
docker compose down -v
```

### 修改端口

如果 80 端口被占用，修改 `.env`：

```bash
HTTP_PORT=8080
```

然后重启：`docker compose up -d`

## 架构说明

```
浏览器 → Nginx(:80) → 前端静态文件(:80)
                     → 后端 API(:8000) → PostgreSQL(:5432)
                                       → Redis(:6379)
```

| 服务 | 技术栈 | 说明 |
|------|--------|------|
| 前端 | React 18 + TypeScript + Tailwind CSS | SPA，Nginx 托管 |
| 后端 | Python 3.11 + FastAPI + SQLAlchemy 2.0 | 异步 API |
| 数据库 | PostgreSQL 16 + pgvector | 向量搜索支持 |
| 缓存 | Redis 7 | 会话和缓存 |
| 网关 | Nginx | 反向代理 + SSE + WebSocket |

## 故障排查

### 后端启动失败

```bash
# 查看后端日志
docker compose logs backend

# 常见原因：数据库未就绪，等待 healthcheck 通过后重试
docker compose restart backend
```

### 数据库连接失败

```bash
# 检查 PostgreSQL 是否健康
docker compose exec postgres pg_isready -U qianchui

# 手动连接测试
docker compose exec postgres psql -U qianchui -d qianchui -c "SELECT 1"
```

### 前端 API 请求失败

确认 Nginx 配置中 backend upstream 指向正确。检查：

```bash
docker compose exec nginx nginx -t
```
