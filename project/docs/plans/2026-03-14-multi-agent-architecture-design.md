# 多 Agent 架构设计方案

> 日期: 2026-03-14
> 状态: 设计中
> 参考: OpenClaw 架构模式

---

## 一、现状分析

### 当前架构（单 Agent）

```
用户消息
    ↓
AgentRuntime.process_message()
    ↓
ConversationContext: 加载企业记忆、话术、历史
    ↓
SkillDispatcher.dispatch()  →  LLM 意图识别
    ↓
匹配 Skill → skill.execute()
未匹配   → _general_chat()
    ↓
返回 { text, cards, suggested_actions, skill_used }
```

**局限性：**

| 问题 | 描述 |
|------|------|
| 单一 Agent | 所有企业共享同一 AgentRuntime，无法定制 |
| Skills 写死 | 11 个 Skill 在启动时硬注册，无法动态增删 |
| 无 Memory 层 | ConversationContext 每次重建，无长期记忆 |
| 不可扩展 | 新增能力必须改代码，超管无法在线配置 |
| 无隔离 | 不同企业 / 不同场景的 Agent 共享上下文 |

### 目标架构（多 Agent + 可配置）

参考 OpenClaw 的 Gateway → Agent → Skills → Memory 分层架构，设计一套：

1. **超管后台**可在线创建和管理多个 Agent
2. 每个 Agent 拥有**独立的 Skills 集合**和 **Memory 存储**
3. 不同企业 / 场景可分配不同 Agent
4. Agent 之间可以**通信协作**

---

## 二、核心概念

### 2.1 实体模型

```
Platform (平台)
  └── Enterprise (企业)
       └── Agent (智能体)
            ├── Skills[]     (能力集)
            ├── Memory[]     (记忆库)
            ├── Sessions[]   (会话)
            └── Config       (配置)
```

| 概念 | 说明 | 对标 OpenClaw |
|------|------|--------------|
| **Agent** | 可独立工作的 AI 智能体实例 | Pi agent |
| **Skill** | Agent 的一项能力（意图+执行逻辑） | Skills (bundled/managed/workspace) |
| **Memory** | Agent 的长期记忆（知识、经验、偏好） | Workspace + AGENTS.md + SOUL.md |
| **Session** | Agent 与用户的对话上下文 | Session model (main/group) |
| **Gateway** | 统一的控制平面，路由消息到正确的 Agent | Gateway WS control plane |

### 2.2 Agent 类型

| 类型 | 用途 | 示例 |
|------|------|------|
| **对话 Agent** | 面向客户的对话场景 | 咨询接待、售后服务 |
| **分析 Agent** | 后台数据分析与洞察 | 诊断分析、飞轮引擎 |
| **操作 Agent** | 页面操作与自动化 | page-agent、工作流自动化 |
| **专家 Agent** | 特定领域深度能力 | 话术专家、培训教练 |

---

## 三、数据库设计

### 3.1 新增表

```sql
-- Agent 定义
CREATE TABLE agents (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    enterprise_id UUID NOT NULL REFERENCES enterprises(id),
    name        VARCHAR(100) NOT NULL,
    description TEXT,
    type        VARCHAR(30) NOT NULL DEFAULT 'conversation',
    -- 'conversation' | 'analysis' | 'operation' | 'expert'
    
    -- Agent 人设配置
    system_prompt   TEXT,           -- 基础系统提示词
    soul_prompt     TEXT,           -- 人格/性格描述 (SOUL.md)
    tools_prompt    TEXT,           -- 工具使用指导 (TOOLS.md)
    
    -- 模型配置
    model_provider  VARCHAR(30) DEFAULT 'openai',
    model_name      VARCHAR(100),
    temperature     NUMERIC(3,2) DEFAULT 0.7,
    max_tokens      INTEGER DEFAULT 4096,
    
    -- 行为配置
    config          JSONB DEFAULT '{}',
    -- {
    --   "greeting": "您好，有什么可以帮您？",
    --   "fallback_agent_id": null,
    --   "max_context_turns": 20,
    --   "activation_mode": "always",  -- always | mention | keyword
    --   "allowed_channels": ["chat", "whatsapp"],
    -- }
    
    is_active   BOOLEAN DEFAULT true,
    created_by  UUID REFERENCES users(id),
    created_at  TIMESTAMPTZ DEFAULT now(),
    updated_at  TIMESTAMPTZ DEFAULT now()
);

-- Agent 技能配置（多对多）
CREATE TABLE agent_skills (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id    UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    skill_id    UUID NOT NULL REFERENCES skill_definitions(id),
    priority    INTEGER DEFAULT 0,          -- 技能匹配优先级
    config      JSONB DEFAULT '{}',         -- 技能级别的配置覆盖
    is_enabled  BOOLEAN DEFAULT true,
    created_at  TIMESTAMPTZ DEFAULT now(),
    UNIQUE(agent_id, skill_id)
);

-- 技能定义（全局注册表）
CREATE TABLE skill_definitions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(100) NOT NULL UNIQUE,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    category    VARCHAR(30) NOT NULL,
    -- 'builtin' | 'managed' | 'custom'
    
    -- 技能元数据
    intent_patterns     JSONB DEFAULT '[]',     -- 意图匹配模式
    required_params     JSONB DEFAULT '[]',     -- 必需参数
    system_prompt       TEXT,                   -- 技能专属提示词
    execute_handler     VARCHAR(200),           -- Python handler 路径
    
    -- 权限与版本
    version     VARCHAR(20) DEFAULT '1.0',
    is_public   BOOLEAN DEFAULT true,           -- 是否对所有企业可用
    enterprise_id UUID REFERENCES enterprises(id), -- 企业自定义技能
    
    created_at  TIMESTAMPTZ DEFAULT now(),
    updated_at  TIMESTAMPTZ DEFAULT now()
);

-- Agent 记忆
CREATE TABLE agent_memories (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id    UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    type        VARCHAR(30) NOT NULL,
    -- 'fact' | 'preference' | 'experience' | 'knowledge' | 'instruction'
    
    content     TEXT NOT NULL,                   -- 记忆内容
    metadata    JSONB DEFAULT '{}',
    -- {
    --   "source": "conversation|manual|system",
    --   "confidence": 0.95,
    --   "related_session_id": "...",
    --   "tags": ["pricing", "objection"],
    -- }
    
    importance  NUMERIC(3,2) DEFAULT 0.5,       -- 重要性 0-1
    access_count INTEGER DEFAULT 0,             -- 被检索次数
    last_accessed_at TIMESTAMPTZ,
    expires_at  TIMESTAMPTZ,                    -- 可选过期时间
    
    created_at  TIMESTAMPTZ DEFAULT now(),
    updated_at  TIMESTAMPTZ DEFAULT now()
);

-- Agent 间通信日志
CREATE TABLE agent_messages (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    from_agent_id UUID NOT NULL REFERENCES agents(id),
    to_agent_id   UUID NOT NULL REFERENCES agents(id),
    session_id    UUID REFERENCES conversations(id),
    message_type  VARCHAR(30) NOT NULL,
    -- 'request' | 'response' | 'notify' | 'delegate'
    content     JSONB NOT NULL,
    status      VARCHAR(20) DEFAULT 'sent',
    -- 'sent' | 'delivered' | 'processed' | 'failed'
    created_at  TIMESTAMPTZ DEFAULT now()
);
```

### 3.2 现有表改造

```sql
-- conversations 表增加 agent_id
ALTER TABLE conversations ADD COLUMN agent_id UUID REFERENCES agents(id);

-- messages 表增加 agent_id（记录是哪个 Agent 回复的）
ALTER TABLE messages ADD COLUMN agent_id UUID REFERENCES agents(id);

-- 企业表增加默认 Agent 配置
ALTER TABLE enterprises ADD COLUMN default_agent_id UUID REFERENCES agents(id);
```

---

## 四、后端架构

### 4.1 整体分层

```
┌─────────────────────────────────────────────────────┐
│                   API Gateway Layer                  │
│  (FastAPI Router: /api/v2/agents, /api/v2/skills)   │
├─────────────────────────────────────────────────────┤
│                Agent Router / Gateway                │
│  消息路由: 根据 session → agent_id 分发到对应 Agent   │
├────────────┬────────────┬────────────┬──────────────┤
│  Agent A   │  Agent B   │  Agent C   │  Agent D     │
│ (咨询接待) │ (诊断分析) │ (话术专家) │ (page-agent) │
├────────────┴────────────┴────────────┴──────────────┤
│              Shared Infrastructure                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐             │
│  │  Skill   │ │  Memory  │ │  Model   │             │
│  │  Engine  │ │  Store   │ │  Router  │             │
│  └──────────┘ └──────────┘ └──────────┘             │
├─────────────────────────────────────────────────────┤
│              Database / Cache / Vector Store          │
└─────────────────────────────────────────────────────┘
```

### 4.2 核心模块

#### AgentGateway（消息路由器）

```python
class AgentGateway:
    """统一控制平面 — 路由用户消息到正确的 Agent 实例"""
    
    async def route_message(
        self, session_id: UUID, user_input: str, enterprise_id: UUID
    ) -> AgentResponse:
        # 1. 查找 session 关联的 agent_id
        agent_id = await self._resolve_agent(session_id, enterprise_id)
        
        # 2. 获取或创建 Agent 实例
        agent = await self._get_agent_instance(agent_id)
        
        # 3. 处理消息
        response = await agent.process_message(user_input, session_id)
        
        # 4. 检查是否需要委派给其他 Agent
        if response.delegate_to:
            return await self._delegate(response.delegate_to, user_input, session_id)
        
        return response
    
    async def _resolve_agent(self, session_id, enterprise_id) -> UUID:
        """优先级: session 绑定 > 企业默认 > 平台默认"""
        ...
    
    async def agent_to_agent(
        self, from_id: UUID, to_id: UUID, message: dict
    ) -> dict:
        """Agent 间通信"""
        ...
```

#### AgentRuntime V2（Agent 运行时）

```python
class AgentRuntimeV2:
    """单个 Agent 的运行时 — 具有独立的 Skills、Memory、Config"""
    
    def __init__(self, agent_def: AgentDefinition):
        self.agent_id = agent_def.id
        self.config = agent_def.config
        self.skill_engine = SkillEngine(agent_def.skills)
        self.memory_store = MemoryStore(agent_def.id)
        self.model_config = agent_def.model_config
    
    async def process_message(
        self, user_input: str, session_id: UUID
    ) -> AgentResponse:
        # 1. 加载上下文
        context = await self._build_context(session_id)
        
        # 2. 检索相关记忆
        memories = await self.memory_store.recall(
            query=user_input, limit=5
        )
        context.inject_memories(memories)
        
        # 3. 技能分发
        skill_match = await self.skill_engine.dispatch(user_input, context)
        
        # 4. 执行
        if skill_match:
            result = await skill_match.skill.execute(user_input, context)
        else:
            result = await self._general_chat(user_input, context)
        
        # 5. 记忆提取 & 存储
        await self._extract_and_store_memories(user_input, result, context)
        
        return result
    
    async def _extract_and_store_memories(self, input, result, context):
        """从对话中自动提取值得记忆的信息"""
        ...
```

#### SkillEngine（技能引擎 V2）

```python
class SkillEngine:
    """可配置的技能引擎 — 支持动态注册/卸载"""
    
    def __init__(self, skill_configs: list[AgentSkillConfig]):
        self.skills = self._load_skills(skill_configs)
    
    def _load_skills(self, configs) -> list[SkillInstance]:
        """按优先级加载技能，支持 builtin + managed + custom"""
        instances = []
        for cfg in sorted(configs, key=lambda c: c.priority):
            if not cfg.is_enabled:
                continue
            handler = self._resolve_handler(cfg.skill_def.execute_handler)
            instances.append(SkillInstance(
                definition=cfg.skill_def,
                handler=handler,
                config=cfg.config,
            ))
        return instances
    
    async def dispatch(self, user_input: str, context) -> SkillMatch | None:
        """两阶段匹配: 快速模式匹配 → LLM 精确分类"""
        # 阶段1: 基于 intent_patterns 的快速匹配
        for skill in self.skills:
            if skill.quick_match(user_input):
                return SkillMatch(skill=skill, confidence=0.9)
        
        # 阶段2: LLM 意图分类（只在需要时调用）
        return await self._llm_dispatch(user_input, context)
```

#### MemoryStore（记忆存储）

```python
class MemoryStore:
    """Agent 记忆管理 — 支持语义检索 + 衰减"""
    
    def __init__(self, agent_id: UUID):
        self.agent_id = agent_id
    
    async def remember(self, memory: MemoryInput) -> UUID:
        """存储新记忆"""
        ...
    
    async def recall(
        self, query: str, limit: int = 5, types: list[str] | None = None
    ) -> list[Memory]:
        """语义检索相关记忆（基于 pgvector）"""
        ...
    
    async def forget(self, memory_id: UUID):
        """手动删除记忆"""
        ...
    
    async def decay(self):
        """定期衰减不重要/长期未访问的记忆"""
        ...
```

### 4.3 API 设计

#### Agent 管理（超管 + 企业管理员）

```
POST   /api/v2/agents                    创建 Agent
GET    /api/v2/agents                    列出 Agent
GET    /api/v2/agents/{id}               获取详情
PUT    /api/v2/agents/{id}               更新配置
DELETE /api/v2/agents/{id}               删除
POST   /api/v2/agents/{id}/clone         克隆
POST   /api/v2/agents/{id}/test          测试对话
```

#### Skill 管理

```
GET    /api/v2/skills                    列出技能（含 builtin + custom）
POST   /api/v2/skills                    创建自定义技能
GET    /api/v2/skills/{id}               详情
PUT    /api/v2/skills/{id}               更新
DELETE /api/v2/skills/{id}               删除

POST   /api/v2/agents/{id}/skills        给 Agent 绑定技能
DELETE /api/v2/agents/{id}/skills/{sid}  解绑技能
PUT    /api/v2/agents/{id}/skills/{sid}  更新技能配置
```

#### Memory 管理

```
GET    /api/v2/agents/{id}/memories          列出记忆
POST   /api/v2/agents/{id}/memories          添加记忆
PUT    /api/v2/agents/{id}/memories/{mid}    更新
DELETE /api/v2/agents/{id}/memories/{mid}    删除
POST   /api/v2/agents/{id}/memories/search   语义搜索
```

#### Agent 间通信

```
POST   /api/v2/agents/{id}/send              向另一个 Agent 发送消息
GET    /api/v2/agents/{id}/messages           查看通信日志
```

---

## 五、超级管理员后台

### 5.1 Agent 管理界面

```
┌──────────────────────────────────────────────────┐
│ Agent 管理中心                            [+ 新建] │
├──────────────────────────────────────────────────┤
│ ┌────────────────┐ ┌────────────────┐            │
│ │ 🤖 咨询接待      │ │ 🔍 诊断分析      │           │
│ │ 类型: conversation│ │ 类型: analysis  │           │
│ │ 技能: 5 个       │ │ 技能: 3 个      │           │
│ │ 记忆: 128 条     │ │ 记忆: 56 条     │           │
│ │ 状态: ● 活跃     │ │ 状态: ● 活跃    │           │
│ │ [配置] [测试]    │ │ [配置] [测试]   │           │
│ └────────────────┘ └────────────────┘            │
│ ┌────────────────┐ ┌────────────────┐            │
│ │ 💬 话术专家      │ │ 🎯 page-agent  │           │
│ │ 类型: expert    │ │ 类型: operation │           │
│ │ 技能: 4 个       │ │ 技能: 1 个      │           │
│ │ 记忆: 89 条      │ │ 记忆: 0 条      │           │
│ │ 状态: ● 活跃     │ │ 状态: ○ 停用    │           │
│ │ [配置] [测试]    │ │ [配置] [测试]   │           │
│ └────────────────┘ └────────────────┘            │
└──────────────────────────────────────────────────┘
```

### 5.2 Agent 配置页

```
┌──────────────────────────────────────────────────┐
│ 编辑 Agent: 咨询接待                               │
├─────────┬────────────────────────────────────────┤
│         │ 基础信息                                 │
│ 基础    │ 名称: [咨询接待]                          │
│ 信息    │ 类型: [conversation ▼]                   │
│         │ 描述: [面向客户的智能咨询接待...]            │
│─────────│────────────────────────────────────────│
│         │ 人设提示词 (SOUL)                         │
│ 人设    │ ┌──────────────────────────────────┐    │
│ 配置    │ │ 你是千锤科技的智能客服，专业、      │    │
│         │ │ 友好、有同理心。你的目标是帮助      │    │
│         │ │ 客户了解产品并解决问题...           │    │
│         │ └──────────────────────────────────┘    │
│─────────│────────────────────────────────────────│
│         │ 模型配置                                 │
│ 模型    │ Provider: [openai ▼]                    │
│         │ Model: [gpt-4 ▼]                        │
│         │ Temperature: [0.7]                      │
│         │ Max Tokens: [4096]                      │
│─────────│────────────────────────────────────────│
│         │ 技能列表                    [+ 添加技能] │
│ 技能    │ ☑ script-recommend  话术推荐    优先级:1 │
│         │ ☑ script-diagnose   话术诊断    优先级:2 │
│         │ ☑ memory-query      记忆查询    优先级:3 │
│         │ ☐ flywheel-sense    飞轮感知           │
│         │ ☐ data-insight      数据洞察           │
│─────────│────────────────────────────────────────│
│         │ 记忆库                        [+ 添加]  │
│ 记忆    │ 📌 fact: 公司主营消费医疗行业     0.9    │
│         │ 📌 knowledge: 种植牙价格8k-30k  0.8    │
│         │ 📌 preference: 偏好先共情再推荐  0.7    │
│         │ [共 128 条记忆] [查看全部] [语义搜索]   │
└─────────┴────────────────────────────────────────┘
```

---

## 六、迁移策略

### Phase 1: 数据库 + 模型层（1 周）

- [ ] 创建 `agents`, `skill_definitions`, `agent_skills`, `agent_memories`, `agent_messages` 表
- [ ] 改造现有表添加 `agent_id` 字段
- [ ] 迁移现有 11 个 Skill 到 `skill_definitions` 表
- [ ] 为每个企业自动创建默认 Agent（迁移脚本）
- [ ] 编写 Pydantic schemas

### Phase 2: 核心引擎重构（1-2 周）

- [ ] 实现 `AgentGateway`（消息路由）
- [ ] 重构 `AgentRuntime` → `AgentRuntimeV2`（支持多实例）
- [ ] 实现 `SkillEngine`（可配置技能引擎）
- [ ] 实现 `MemoryStore`（基础版，先用 JSON 查询，后接 pgvector）
- [ ] 重构 conversation API 适配 Agent 路由

### Phase 3: API + 超管后台（1 周）

- [ ] 实现 Agent CRUD API (`/api/v2/agents`)
- [ ] 实现 Skill 管理 API (`/api/v2/skills`)
- [ ] 实现 Memory 管理 API (`/api/v2/agents/{id}/memories`)
- [ ] 前端超管后台：Agent 管理页
- [ ] 前端超管后台：Skill 管理页
- [ ] 前端超管后台：Memory 管理页

### Phase 4: 高级功能（后续迭代）

- [ ] Agent 间通信协议
- [ ] 语义记忆检索（pgvector embedding）
- [ ] 记忆自动提取（对话后自动总结存储）
- [ ] 记忆衰减机制
- [ ] Agent 克隆 / 模板
- [ ] Agent 性能监控仪表盘
- [ ] 自定义 Skill 在线编辑器

---

## 七、与 OpenClaw 架构对标

| OpenClaw 概念 | 本项目对应 | 说明 |
|--------------|-----------|------|
| Gateway (WS control plane) | AgentGateway | 统一消息路由与控制 |
| Pi agent runtime | AgentRuntimeV2 | 支持多实例的 Agent 运行时 |
| Skills (bundled/managed/workspace) | skill_definitions (builtin/managed/custom) | 三级技能体系 |
| AGENTS.md + SOUL.md + TOOLS.md | system_prompt + soul_prompt + tools_prompt | Agent 人设三件套 |
| Workspace + sessions | agent_memories + conversations | 记忆 + 会话 |
| Session model (main/group) | session + agent_id 路由 | 会话隔离 |
| sessions_send (agent-to-agent) | agent_messages + /send API | Agent 间通信 |
| DM pairing + allowlist | Agent activation_mode + channel config | 接入控制 |
| ClawHub skill registry | skill_definitions 表 | 技能注册中心 |
| openclaw doctor | /health + Agent 健康监控 | 运维诊断 |

---

## 八、关键设计决策

### Q1: Agent 实例是单例还是每次请求新建？

**决策: 按需缓存，LRU 淘汰。**

Agent 定义从数据库加载后缓存在内存中（TTL 5 分钟）。同一 Agent 的并发请求共享定义但各自持有独立的会话上下文。这样既避免了每次数据库查询，又确保配置变更能在短时间内生效。

### Q2: 技能如何支持「自定义」？

**分三级实现：**

- **builtin**: 代码级实现，随版本发布（现有的 11 个 Skill）
- **managed**: 平台维护的模板技能，通过配置即可使用
- **custom**: 企业自定义，通过 `system_prompt` + `intent_patterns` + LLM 执行，无需写代码

Custom Skill 本质是一个 Prompt-as-Skill：配置意图匹配模式和专属系统提示词，由 LLM 执行。

### Q3: Memory 是否需要向量检索？

**Phase 2 用 JSONB + GIN 索引，Phase 4 升级 pgvector。**

前期记忆量不大（数百条级别），全文搜索 + tag 过滤足够。当单个 Agent 记忆超过 1000 条时，自动启用 pgvector 语义检索。数据库已经在用 pgvector 镜像。

### Q4: 如何保证向后兼容？

- 现有 API (`/api/conversations`, `/api/skills`) 保持不变
- 新 API 放在 `/api/v2/` 前缀下
- 迁移脚本为每个企业自动创建一个「默认 Agent」，绑定所有现有 Skill
- 旧的 `AgentRuntime` 作为 `AgentRuntimeV2` 的薄包装继续工作

---

## 九、文件结构变更

```
backend/app/
├── agent/
│   ├── gateway.py           # NEW: AgentGateway 路由器
│   ├── runtime_v2.py        # NEW: AgentRuntimeV2
│   ├── runtime.py           # 保留: 向后兼容薄包装
│   ├── context.py           # 改造: 支持 agent_id
│   ├── skill_engine.py      # NEW: SkillEngine V2
│   └── memory_store.py      # NEW: MemoryStore
├── api/
│   ├── v2/
│   │   ├── agents.py        # NEW: Agent CRUD
│   │   ├── skills.py        # NEW: Skill 管理
│   │   ├── memories.py      # NEW: Memory 管理
│   │   └── agent_comms.py   # NEW: Agent 间通信
│   └── ... (现有 API 保持不变)
├── models/
│   ├── agent.py             # NEW: Agent + AgentSkill + AgentMemory
│   └── ... (现有模型改造加 agent_id)
├── schemas/
│   └── agent.py             # NEW: Agent 相关 schemas
└── services/
    └── agent_service.py     # NEW: Agent 业务逻辑

frontend/src/
├── pages/admin/
│   ├── AdminAgentsPage.tsx   # NEW: Agent 管理
│   ├── AdminSkillsPage.tsx   # NEW: Skill 管理
│   └── ... (现有页面不变)
├── services/
│   └── agent.ts             # NEW: Agent API 服务
└── ...
```

---

## 十、总结

本架构设计的核心思路是：**从单 Agent 演进到多 Agent，保持向后兼容，分阶段落地。**

关键收益：
1. **可配置性**: 超管可在线创建/配置 Agent，无需改代码
2. **隔离性**: 不同企业/场景用不同 Agent，互不干扰
3. **可扩展性**: 新增能力只需创建 Skill 定义，无需重启
4. **记忆能力**: Agent 具备长期记忆，对话越多越智能
5. **协作能力**: Agent 间可委派任务、共享信息

参考 OpenClaw 的分层架构，但简化为适合 B2B SaaS 场景的方案，不做消息渠道集成（WhatsApp/Telegram 等），聚焦在 Agent 运行时 + 技能引擎 + 记忆存储的核心能力。
