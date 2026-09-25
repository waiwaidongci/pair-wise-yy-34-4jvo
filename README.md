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
- `POST /api/items/{id}/records`，措施登记后一律停在待验收，不能指定状态
- `POST /api/items/{id}/records/{record_id}/accept`，安全员验收，需提交验收说明`note`、责任人`owner`和验收号`acceptance_no`，验收号全局唯一，重复拒绝
- `POST /api/items/{id}/records/{record_id}/update`，修改措施内容`detail`或责任人`owner`；已验收措施被修改后退回待验收，原验收单作废但留存
- `GET /api/items/{id}/records/{record_id}/acceptances`，查看验收单（含已作废）
- `POST /api/items/{id}/transition`，必须提交`expected_version`
- `GET /api/audit`

允许角色：reporter, investigator, safety_manager, viewer。严重度越高、伤害指数越大或未关闭措施越多，优先级越高；严重事故必须在4小时内启动调查。存在未验收措施时事故不能进入验证，关闭前逐项确认全部验收通过；事故关闭后措施不可再登记、验收或修改。

## 测试

```bash
python3 -m unittest discover -s tests -v
```
