# Java 工单服务

## 服务边界

- Python `backend` 只负责意图识别、情绪分析、工单信息提取与事件消费。
- Java `ticket-service` 独占工单写入权限，负责创建、查询、状态流转、分配、并发控制、幂等和 SLA。
- React 继续请求 Python 的 `/api/v1/tickets` BFF；BFF 只转发到 Java，不访问工单表。
- Java 事务提交后向 RocketMQ 发布事件，Python 消费后通过现有 WebSocket 推送给页面。

## 本地启动

完整环境：

```bash
docker compose up -d --build
```

只启动基础设施：

```bash
docker compose up -d postgres redis namesrv broker
```

本地启动 Java（需要 JDK 17）：

```bash
cd ticket-service
mvn spring-boot:run
```

Java API 文档入口为 `http://localhost:8080/api/tickets`，健康检查为
`http://localhost:8080/actuator/health`。

## 五个接口

| 方法 | 路径 | 用途 |
|---|---|---|
| `POST` | `/api/tickets` | 幂等创建工单 |
| `GET` | `/api/tickets/{id}` | 查询详情和状态日志 |
| `GET` | `/api/tickets` | 按状态、优先级、处理人分页查询 |
| `PATCH` | `/api/tickets/{id}/status` | 经状态机校验后修改状态 |
| `POST` | `/api/tickets/{id}/assign` | 分配或重新分配处理人员 |

创建示例：

```bash
curl -X POST http://localhost:8080/api/tickets \
  -H "Content-Type: application/json" \
  -d '{
    "requestId": "req-20260725-001",
    "conversationId": "conv-1001",
    "userId": "user-101",
    "category": "REFUND",
    "priority": "HIGH",
    "summary": "用户申请订单退款"
  }'
```

修改状态：

```bash
curl -X PATCH http://localhost:8080/api/tickets/10001/status \
  -H "Content-Type: application/json" \
  -d '{
    "status": "IN_PROGRESS",
    "operatorId": "agent-007",
    "reason": "坐席开始处理"
  }'
```

## 状态机

```text
NEW -> ASSIGNED -> IN_PROGRESS -> RESOLVED -> CLOSED
                         |             |
                         v             v
                      PENDING       REOPENED
                         |             |
                         +------> IN_PROGRESS

CLOSED -> REOPENED -> IN_PROGRESS
```

非法跳转返回 HTTP `422` 和错误码 `INVALID_STATUS_TRANSITION`。状态更新和
`ticket_status_log` 写入位于同一个数据库事务中。

## 幂等与并发

创建请求以 `requestId` 为幂等键：

1. 先查数据库，已存在时直接返回原工单。
2. Redis `SETNX` 抢占 `ticket:idempotency:{requestId}`。
3. `ticket.request_id` 唯一约束作为最终防线。

`ticket.version` 由 MyBatis-Plus 乐观锁插件维护。并发更新失败返回 HTTP
`409`，调用方应重新读取最新工单后再提交。

## 事件

Java 向 `ticket-events` Topic 发布三类事件（同时作为消息 Tag 和
`eventType`）：

- `ticket.created`
- `ticket.status.changed`
- `ticket.sla.overdue`

事件只在数据库事务提交后发布。Python 的
`app/mq/ticket_event_consumer.py` 订阅这些 Topic，并转换为
`ticket_created`、`ticket_updated`、`ticket_sla_overdue` WebSocket 消息。

官方 Python RocketMQ 客户端依赖原生 `librocketmq`，因此事件消费者面向
Linux 容器运行；本地不启用时设置 `ROCKETMQ_CONSUMER_ENABLED=false`。

## 验证

```bash
cd ticket-service
mvn test

cd ../backend
pytest -q

cd ../frontend
npm run build
```
