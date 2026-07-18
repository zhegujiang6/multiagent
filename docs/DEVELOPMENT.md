# 本地开发指南

## 首次准备

1. 确保 Docker Desktop 正在运行。
2. 在项目根目录复制环境变量示例，并填写模型服务配置：

   ```powershell
   Copy-Item .env.example .env
   ```

3. 安装后端和前端依赖：

   ```powershell
   python -m pip install -r backend/requirements.txt
   npm.cmd --prefix frontend ci
   ```

## 启动本地开发环境

在项目根目录启动 PostgreSQL、Redis 和 Qdrant：

```powershell
docker compose up -d postgres redis qdrant
```

首次启动时执行数据库迁移和知识库初始化：

```powershell
Set-Location backend
alembic upgrade head
python -m app.rag.seed_data
```

后端与前端需要分别占用一个终端：

```powershell
# 终端一：项目根目录
Set-Location backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 终端二：项目根目录
npm.cmd --prefix frontend run dev
```

访问地址：

- 客户聊天：`http://localhost:5173/chat`
- 坐席工作台：`http://localhost:5173/workspace`
- API 文档：`http://localhost:8000/docs`
- 健康检查：`http://localhost:8000/api/v1/health`

## 一键启动完整环境

```powershell
docker compose up -d --build
docker compose exec backend python -m app.rag.seed_data
```

完整环境的前端地址为 `http://localhost`。

## 变更后验证

```powershell
python -m compileall -q backend/app
python -m pytest -q backend/tests
npm.cmd --prefix frontend run build
docker compose config --quiet
```

基础设施容器通常只需启动一次；日常开发可只重启前后端进程。
