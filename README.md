# api-testing-demo

接口自动化测试练习项目：**pytest + requests**，34 个用例，覆盖正常流程与异常边界。

## 为什么自带一个 mock 服务

原本想用 [restful-booker](https://github.com/mwinteringham/restful-booker) 做靶场，但它部署在 Heroku 免费实例上——

```
$ curl https://restful-booker.herokuapp.com/booking
HTTP 000
```

已经连不上了。所以 `mock_server.py` 用标准库实现了一份**同形状**的接口（鉴权、CRUD、400/401/403/404 语义齐全），离线也能跑，不受别人服务器影响。

## 目录

```
api-testing-demo/
├─ mock_server.py          本地 API（201 行，只用标准库）
├─ conftest.py             pytest 夹具：起服务、鉴权、造数据、清数据
├─ tests/
│   ├─ test_health.py      健康检查与路由（5 个）
│   ├─ test_auth.py        鉴权（6 个）
│   ├─ test_crud.py        增删改查主流程（9 个）
│   └─ test_validation.py  参数校验与边界（14 个）
├─ pytest.ini
├─ requirements.txt
└─ 运行测试.bat
```

## 跑起来

```bash
pip install -r requirements.txt
python -m pytest
```

Windows 上也可以双击 `运行测试.bat`。

实测输出：

```
collected 34 items
...
============================= 34 passed in 0.75s =============================
```

## 覆盖了什么

| 类别 | 测的点 |
|---|---|
| 健康检查 | ping 通不通、返回体、Content-Type、未知路由 404 |
| 鉴权 | 正确凭据换 token、错误密码 401、缺 token / 错 token 403 |
| CRUD | 创建返回 ID、创建后能查、出现在列表、PUT 全量更新、PATCH 只改指定字段、删除返回 201、删完 404、重复删除 404 |
| 参数校验 | 缺字段、`depositpaid` 非布尔、`totalprice` 非数字、日期格式非 ISO、`bookingdates` 缺键、查不存在的资源 404 |

**参数化用例**（`@pytest.mark.parametrize`）一个函数覆盖多个边界值，所以 34 个用例其实只用了 20 个测试函数。

## 几个值得注意的设计

1. **每个用例前清空数据**（`autouse` 夹具）——否则用例执行顺序会影响结果，出现"单跑过、全跑挂"。
2. **造数据的夹具负责善后**——`yield` 之后自动删除，不靠用例自己清理。
3. **端口用 0** 让系统分配，避免和本机其他服务抢端口。
4. **等 `/ping` 通再开始测**，不靠 `sleep` 赌时间。

## 下一步可以加

- [ ] Allure 报告（`pip install allure-pytest` + allure 命令行）
- [ ] GitHub Actions：每次 push 自动跑
- [ ] Playwright 补 UI 层用例

## License

MIT

## 测试工作流

一套能日常用的流程，不只是"跑一下看看"。

```
写用例  →  冒烟先跑（-m smoke）  →  全量回归  →  出报告  →  看红字定位  →  修
                                        ↑                              ↓
                                     CI 每次提交自动跑  ←───────────────┘
```

### 1. 分层：冒烟 / 回归

用例打了标记（`pytest.ini` 里声明），可以分开跑：

```bash
pytest -m smoke            # 只跑冒烟（4 个，0.5s）—— 服务挂了立刻知道
pytest -m "not smoke"      # 跳过冒烟，只跑细节
pytest -m regression       # 回归组
```

**为什么分层**：CI 上先跑冒烟，挂了就不用浪费时间跑后面几百个用例。

### 2. 断言要能"说清哪不对"

`assertions.py` 提供四个helper，失败时会把实际响应体打出来：

```python
from assertions import assert_status, assert_json_field, assert_fields_present, assert_error_message

assert_status(response, 200, "创建预订")          # 失败会带上响应体
assert_fields_present(body, ["token"], "登录返回")  # 缺字段会说缺哪个
assert_error_message(response, "Bad credentials")  # 错误信息里必须有原因
```

对比一下：

| 写法 | 失败时你看到 |
|---|---|
| `assert r.status_code == 200` | `assert 500 == 200` ← 还得自己复现 |
| `assert_status(r, 200, "创建预订")` | 状态码 + 请求 URL + 响应体 ← 直接定位 |

### 3. 一键跑 + 出报告

双击 `一键测试.bat`：跑全量 → 生成 HTML 报告 → 自动开浏览器。

### 4. CI

`.github/workflows/test.yml` 在 push 时跑三个 Python 版本（3.11/3.12/3.13）。



### 5. 数据驱动用例

测试场景写在 `data/booking_cases.json` 里，加一行就是加一个用例，不用改代码：

```json
{"id": "价格为0", "payload": {...}, "expect": 200}
```

`tests/test_data_driven.py` 读这个文件，用 `@pytest.mark.parametrize` 展开。

### 6. 契约快照

`contract.py` 记录响应里每个字段的**类型结构**，结构变了就失败：

```
snapshots/create_booking.json
{ "booking": { "bookingdates": {"checkin": "str", ...}, "totalprice": "int" }, "bookingid": "int" }
```

**为什么需要**：后端把 `totalprice` 从数字改成字符串，功能断言可能照样过，但前端会炸。契约测试专盯这个。

```bash
python contract.py          # 重新生成快照（确认改动是预期的）
pytest tests/test_contract.py
```

### 7. 切换被测服务

默认跑本地 mock。要测真实服务就设环境变量：

```powershell
$env:API_BASE_URL = "http://127.0.0.1:8000"
python -m pytest
```

## 这个项目自己发现过两个缺陷

写完数据驱动用例后，**测试立刻抓到 mock 服务的两个真实缺陷**：

| 缺陷 | 症状 | 修复 |
|---|---|---|
| 空名字能创建 | `firstname: ""` 返回 200 | `validate()` 加非空检查 |
| 假日期能通过 | `2026-13-45` 被接受 | 正则只管位数，改用 `datetime.strptime` 真校验 |

补充 `checkout > checkin` 规则后，用例从 2 failed 变成全绿。

**这就是测试的价值**——不是"证明代码是对的"，是"在它错的时候立刻知道"。

## 还能加什么

- [ ] 数据驱动：用例参数放进 JSON/YAML，代码只写一遍
- [ ] 失败重试：网络抖动导致的偶发失败自动重跑
- [ ] 覆盖率：`pytest-cov`（需装包）
- [ ] Playwright 补 UI 层

