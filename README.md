# 工伤事故调查与纠正措施

记录工伤经过、伤害、现场和证人，维护调查、纠正措施、验证与关闭流程。

## 模块结构

- `app.py`：参数解析、依赖组装和HTTP服务启动。
- `src/domain.py`：数据结构、错误、状态和基础校验。
- `src/rules.py`：状态机、角色矩阵、优先级、期限和关闭不变量。
- `src/repository.py`：SQLite建表、事务、版本控制和审计链。
- `src/service.py`：权限检查、用例编排、并发控制和审计。
- `src/http_api.py`：JSON路由和统一错误响应。
- `src/audit.py`：UTC时间和SHA-256审计事件。
- `static/index.html`：最小演示页。
- `tests/`：完整流程、规则和失败测试。

## 初始化与启动

```bash
python3 app.py --db ./data.db --port 8311
```

默认端口为`8311`，首次启动自动建库。使用`X-Actor`和`X-Role`请求头传递身份。

## 主要接口

- `GET /health`
- `GET /api/items`
- `POST /api/items`
- `GET /api/items/{id}`
- `POST /api/items/{id}/records`，登记纠正措施，一律先进入待验收
- `POST /api/items/{id}/records/{rid}/accept`，安全员验收，需验收说明、责任人、验收号
- `POST /api/items/{id}/records/{rid}/update`，修改措施内容或责任人
- `GET /api/items/{id}/records/{rid}/acceptances`，验收单历史（含已作废）
- `POST /api/items/{id}/transition`，必须提交`expected_version`
- `GET /api/audit`

允许角色：reporter, investigator, safety_manager, viewer。严重度越高、伤害指数越大或未关闭措施越多，优先级越高；严重事故必须在4小时内启动调查。

## 验收规则

- 措施登记后停在待验收，不能直接写成已关闭；仅安全员可验收，验收号全局唯一，重复拒绝。
- 存在无有效验收的措施时，事故不能进入验证；关闭前逐项确认每条措施均已验收。
- 验收后修改责任人或内容，该措施退回待验收，原通过结论作废，但验收单留存可查。

## 测试

```bash
python3 -m unittest discover -s tests -v
```
