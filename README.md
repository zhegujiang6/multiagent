# 全链路客户服务与工单闭环协同智能体

Full-Chain Customer Service & Ticket Closed-Loop Collaborative Agent

基于 **Multi-Agent + LLM** 的智能客服运营解决方案。6 个专业 AI Agent 协同工作，覆盖从客户接入、意图识别、知识检索、工单创建到闭环解决的全链路。

## 系统架构

```
用户消息 → 并行预处理(意图+情绪) → 画像增强 → 路由决策
                                              │
                        ┌─────────────────────┼─────────────────────┐
                        ▼                     ▼                     ▼
                    FAQ 回答             创建工单              转人工
                        │                     │                     │
                        └─────────────────────┴─────────────────────┘
                                              │
                                              ▼
                                         回复合成
```

### 6 个核心 Agent

| Agent | 职责 | 触发条件 |
|-------|------|---------|
| **Orchestrator** | 场景理解、任务分解、子Agent编排、结果聚合 | 始终运行 |
| **Intent Classifier** | 13分类意图识别 + 实体提取 | 每轮对话 |
| **Sentiment Analyzer** | 5分类情绪分析 + 触发词检测 + 趋势追踪 | 每轮对话 |
| **FAQ Agent** | RAG知识检索 + 答案生成 + 来源引用 | FAQ/产品信息类问题 |
| **Ticket Agent** | 工单信息提取、分类、优先级计算、SLA设定 | 退款/技术/物流类问题 |
| **Profile Enricher** | 客户画像增强、VIP识别、服务策略建议 | 已识别用户 |

### 工单状态机

```
new → assigned → in_progress → resolved → closed
                    ↓    ↑         ↑
                  pending/waiting   reopened
```

## 快速开始

### 前置条件

- Docker Desktop（包含 Docker Compose）
- Python 3.12+（本地开发）
- Node.js 20+（前端开发）
- OpenAI 兼容的模型服务及 API Key

### 1. 克隆并配置

```bash
cd multiagent
cp .env.example .env
# 编辑 .env，填写 LLM_API_KEY、LLM_API_BASE 和模型名称
```

### 2. 启动基础设施

```bash
docker compose up -d postgres redis qdrant
```

等待所有服务健康：
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`
- Qdrant: `localhost:6333`

### 3. 初始化数据库和知识库

```bash
cd backend
pip install -r requirements.txt

# 数据库迁移
alembic upgrade head

# 加载知识库种子数据（50+ FAQ + 10 SOP）
python -m app.rag.seed_data
```

### 4. 启动后端

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API 文档：`http://localhost:8000/docs`

### 5. 启动前端

```bash
cd frontend
npm ci
npm run dev
```

- 客户聊天界面：`http://localhost:5173/chat`
- 坐席工作台：`http://localhost:5173/workspace`

### 6. 一键启动（Docker）

```bash
# 构建并启动所有服务
docker compose up -d --build

# 加载知识库
docker compose exec backend python -m app.rag.seed_data

# 访问
# 前端: http://localhost
# API文档: http://localhost:8000/docs
```

## API 概览

更完整的本地启动、验证命令见 [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md)。

### REST 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/v1/conversations` | 创建会话 |
| `GET` | `/api/v1/conversations/{id}` | 获取会话详情 |
| `GET` | `/api/v1/conversations/{id}/messages` | 获取消息历史 |
| `POST` | `/api/v1/conversations/{id}/messages` | 发送消息 |
| `GET` | `/api/v1/tickets` | 工单列表（支持筛选） |
| `POST` | `/api/v1/tickets` | 创建工单 |
| `GET` | `/api/v1/tickets/{id}` | 工单详情 |
| `PATCH` | `/api/v1/tickets/{id}` | 更新工单状态 |
| `GET` | `/api/v1/admin/metrics` | 控制台指标 |
| `GET` | `/api/v1/health` | 健康检查 |

### WebSocket

```
ws://localhost:8000/api/v1/ws/chat?conversation_id={id}
```

消息类型：
- `agent_status` — Agent 处理状态（started/completed）
- `ticket_created` — 工单自动创建
- `escalating` — 转接人工
- `message` — Agent 回复消息
- `typing` — 输入状态指示

## 演示场景

参考 `data/demo_scenarios.json`，包含 5 个完整演示场景：

1. **订单物流查询** — AI 通过 RAG 自动回答，无需人工介入
2. **退款退货处理** — 自动创建工单，SLA 追踪
3. **情绪愤怒转人工** — 检测到愤怒/绝望情绪自动升级
4. **VIP 客户优先服务** — 识别 VIP 身份，升级服务等级
5. **工单闭环流程** — 完整的工单生命周期演示

## 项目结构

```
multiagent/
├── backend/
│   ├── app/
│   │   ├── agents/             # 6个AI Agent + Orchestrator
│   │   │   ├── orchestrator.py # LangGraph StateGraph ⭐
│   │   │   └── prompts/        # System Prompts (YAML)
│   │   ├── rag/                # RAG管道 (Embedder + Qdrant + Retriever)
│   │   ├── models/             # SQLAlchemy ORM (7表)
│   │   ├── schemas/            # Pydantic + AgentState
│   │   ├── services/           # 业务逻辑 (Conversation/Ticket/SLA)
│   │   ├── api/                # REST + WebSocket 端点
│   │   └── core/               # DB/Redis/LLM/Security
│   └── alembic/                # 数据库迁移
├── frontend/
│   └── src/
│       ├── app/                # 应用入口与路由
│       ├── features/           # 聊天、工作台、知识功能
│       ├── shared/             # 共享 API、类型和 UI 组件
│       ├── store/              # Zustand 状态管理
│       └── styles/             # 全局样式
├── data/                       # 种子数据与演示场景
├── docker/                     # PostgreSQL / Qdrant 配置
├── docs/
│   ├── DEVELOPMENT.md          # 本地开发与验证指南
│   └── design/                 # 设计和分析文档
├── scripts/
│   └── document-generation/    # Word 文档生成工具
└── docker-compose.yml          # 完整服务编排
```

## 技术栈

| 层级 | 技术 |
|------|------|
| LLM | OpenAI 兼容 API（模型可配置） |
| Agent 编排 | LangGraph 0.2+ |
| 后端 | Python 3.12+ + FastAPI |
| 向量库 | Qdrant |
| Embedding | sentence-transformers (本地免费) |
| 数据库 | PostgreSQL 16 + Redis 7 |
| 前端 | React 18 + TypeScript + Vite + TailwindCSS 4 |
| 状态管理 | Zustand |
| 部署 | Docker Compose |

## MVP 范围

当前 MVP 实现了完整设计文档 Phase 0-2 的核心功能：

- ✅ 6 个专业 Agent 协同工作
- ✅ LangGraph 有状态编排
- ✅ RAG 知识检索（50+ FAQ + 10 SOP）
- ✅ 工单生命周期状态机（8 状态 + 12 条合法转换）
- ✅ SLA 智能追踪与自动升级
- ✅ 实时 WebSocket 通信
- ✅ 情绪感知与自动转人工
- ✅ 客户画像增强
- ✅ Customer Chat Widget + Agent Workspace
- 🔜 多模态（图片/语音/视频）— Phase 4
- 🔜 多渠道接入 — Phase 3
- 🔜 Co-pilot 实时辅助 — Phase 4
- 🔜 知识自进化闭环 — Phase 3

## License

MIT

## Java 工单业务中心

项目现已将工单业务从 Python Agent 服务拆分到独立的
`ticket-service`（JDK 17 + Spring Boot 3 + MyBatis-Plus）。Python 只负责
AI 决策与 RocketMQ 事件消费，工单表仅由 Java 写入。

完整的接口、状态机、幂等、乐观锁和启动说明见
[`docs/TICKET_SERVICE.md`](docs/TICKET_SERVICE.md)。
