# 软件测试可视化

接口自动化 + UI 自动化练习项目：**pytest + requests + Playwright**，接口 98 个用例、UI 9 个用例，覆盖正常流程、异常边界、并发安全、契约规则、角色越权、分页边界、库存超卖、幂等重放、性能基线、浏览器端主流程（含房型与库存），并自带零依赖的指标工具（报告 / 覆盖率 / 性能 / 失败现场留存）。

配套文档：**[测试方案](docs/测试方案.md)**（范围 / 策略 / 等价类 / 边界值 / 判定表 / 用例清单）、**[缺陷记录](docs/缺陷记录.md)**（7 个缺陷的完整缺陷单）。

## 下次打开先看这里

桌面上有 **「软件测试项目」** 快捷方式（或双击根目录的 `开始使用.bat`），打开就是**主页面**——
启动后控制台窗口会自己退出，只留下主页面，不会有个黑窗一直挂在那儿：

![主页面](docs/gui-main.png)

1. **自动做环境自检**：顶部直接显示 Python / pytest / UI / Allure 是否就绪，缺什么用橙色列出来；
2. **选被测项目**：`选文件夹…`（整个项目）或 `选源码文件…`（单个文件）；
   如果选到的目录里有多个项目（工作区），下面的「**子项目**」会列出来，挑一个再体检——
   直接扫整个工作区又勾着「跑自带测试」时，程序会拦住你，不让它去跑别人项目的测试；
3. 点 **开始体检**：结果按 高 / 中 / 低 分级列在下面，双击某行可直接打开源文件；
4. 需要留档就点 **生成 HTML 报告**；想看命令行菜单（跑用例、覆盖率、性能、Allure）点右下角 **打开控制台菜单**。

**能检测哪些文件**（主页面里也写着）：

| 类型 | 检测内容 |
|---|---|
| Python 源码 `.py` | 语法错误、硬编码凭据、危险调用（eval / exec / os.system）、可变默认参数、TODO/FIXME、print 残留、assert 做校验 |
| Java / JavaScript / TypeScript / Go | 轻量文本规则（非 AST）：硬编码凭据、危险调用（eval / Runtime.exec / exec.Command）、调试残留（console.log / System.out / debugger）、TODO/FIXME |
| 敏感文件 | `.env` / `id_rsa` / `credentials.json` / `.npmrc` / `.pypirc` / `secrets.json` / `config.ini`、`*.pem` `*.key` `*.pfx` `*.p12` |
| 项目卫生（仅目录模式） | README、`.gitignore`、tests 目录、`requirements.txt` 是否存在 |
| 说明 | Java / JS / TS / Go 用正则规则，精度低于 Python AST；不做类型检查 |

**觉得某条是误报？** 确认它是"有意为之"以后，在那一行加 `# scanner: ignore`，体检器会跳过这一行：

```python
except ValueError:  # scanner: ignore - 解析不了就走下面的兜底
    pass
```

不加标记就照常报——这样"有意降级"和"忘了处理"能区分开。

> 所有 `.bat` 都是**纯 ASCII 启动器**，只负责调用 Python 脚本；中文提示由 Python 输出。
> 原因是 cmd 会用控制台代码页（936）读取批处理，UTF-8 中文一旦跨读取缓冲区就会裂开，
> 出现"半行被当成命令执行"的怪错——这个坑 v1.0.2 已经踩过并修掉。

**换一台电脑时**按这个顺序：

1. `pip install -r requirements.txt`
2. 双击 `安装UI依赖.bat`（要跑 UI 时）
3. 双击 `开始使用.bat`，主页面顶部的环境状态会告诉你缺什么

环境自检会检查：Python 版本、pytest / requests / allure-pytest、playwright + Chromium、Java + allure 命令 —— 并用注册表里的环境变量判断（新装的东西不用重启也行）。


## 为什么自带一个 mock 服务

原本想用 [restful-booker](https://github.com/mwinteringham/restful-booker) 做靶场，但它部署在 Heroku 免费实例上——

```
$ curl https://restful-booker.herokuapp.com/booking
HTTP 000
```

已经连不上了。所以 `mock_server.py` 用标准库实现了一份**同形状**的接口（鉴权、CRUD、400/401/403/404 语义齐全），离线也能跑，不受别人服务器影响。

## 目录

```
软件测试可视化/
├─ mock_server.py          本地 API（只用标准库，线程安全）
├─ conftest.py             pytest 夹具：起服务、鉴权、造数据、清数据
├─ check_env.py            环境自检（Python / 依赖 / 浏览器 / Java）
├─ tester_gui.py           主页面：自动自检 + 选项目/文件 + 体检 + 出报告
├─ start_menu.py           控制台菜单（跑用例 / 覆盖率 / 性能 / Allure）
├─ launch_gui.vbs          无控制台启动主页面（快捷方式指向它）
├─ 开始使用.bat            启动器（纯 ASCII，调 launch_gui.vbs 后立即退出）
├─ retry.py                失败重试插件（零依赖，给 flaky 用例用）
├─ coverage_simple.py      语句覆盖率（零依赖，sys.settrace）
├─ perf_load.py            性能基线（并发梯度 + p50/p95/p99，零依赖）
├─ assertions.py           失败信息更清楚的断言库
├─ contract.py             生成 / 比对契约快照
├─ schema_validator.py     JSON Schema 校验（零依赖，规则级契约）
├─ reports.py              report.xml → 自包含 HTML 报告
├─ allure_run.py           跑用例 + 带历史趋势 + 生成 Allure 报告
├─ scanner.py              图形化体检器（静态检查 + 跑测试）
├─ tests/
│   ├─ test_health.py      健康检查与路由（5 个）
│   ├─ test_auth.py        鉴权（6 个）
│   ├─ test_crud.py        增删改查主流程（9 个）
│   ├─ test_validation.py  参数校验与边界（18 个）
│   ├─ test_smoke.py       冒烟层（4 个）
│   ├─ test_data_driven.py 数据驱动（7 个）
│   ├─ test_contract.py    契约快照（2 个）
│   ├─ test_schema.py      契约规则 / JSON Schema（8 个）
│   ├─ test_roles.py       角色越权（6 个）
│   ├─ test_pagination.py  分页与过滤（8 个）
│   ├─ test_inventory.py   库存与超卖（5 个）
│   ├─ test_idempotency.py 幂等键（5 个）
│   └─ test_concurrency.py 并发安全与延迟（6 个）
├─ ui_tests/
│   ├─ conftest.py         Playwright 夹具：浏览器 + 独立上下文 + 失败截图
│   └─ test_booking_ui.py  UI 主流程（6 个）
├─ live_tests/             真实公开 API 联网冒烟（默认 skip，LIVE_API=1 开启）
├─ web/index.html          管理页面（登录 / 新建 / 改价 / 删除 / 房型库存）
├─ schema/                 契约规则（JSON Schema，4 份）
├─ artifacts/              失败现场（截图 / trace），不进版本库
├─ docs/
│   ├─ 测试方案.md          范围、策略、等价类/边界值/判定表、用例清单
│   └─ 缺陷记录.md          4 个缺陷的标准缺陷单
├─ data/booking_cases.json 数据驱动用例表
├─ snapshots/              契约快照
├─ examples/               演示用的"偶发失败"用例（默认不跑）
├─ pytest.ini
├─ requirements.txt        依赖：pytest / requests / allure-pytest
├─ requirements-ui.txt     UI 层依赖（playwright）
└─ 运行测试.bat / 安装UI依赖.bat / 运行UI测试.bat / 生成Allure报告.bat / 一键测试.bat
```

## 跑起来

```bash
pip install -r requirements.txt
python -m pytest
```

Windows 上也可以双击 `运行测试.bat`。

实测输出：

```
collected 98 items
...
==================== 95 passed, 3 skipped in 1.50s ====================
```

（跳过的 3 个是 `test_my_api_template.py` 里的模板用例，删掉 `@pytest.mark.skip` 就会执行。）

UI 层要另装浏览器，单独跑：

```
python -m pytest ui_tests -q
9 passed in 3.80s
```

## 覆盖了什么

| 类别 | 测的点 |
|---|---|
| 健康检查 | ping 通不通、返回体、Content-Type、未知路由 404 |
| 鉴权 | 正确凭据换 token、错误密码 401、缺 token / 错 token 403 |
| CRUD | 创建返回 ID、创建后能查、出现在列表、PUT 全量更新、PATCH 只改指定字段、删除返回 201、删完 404、重复删除 404 |
| 参数校验 | 缺字段、`depositpaid` 非布尔、`totalprice` 非数字或负数、日期格式非 ISO、非法日期、同日入住退房、闰日、`bookingdates` 缺键、查不存在的资源 404 |
| 契约 | 字段类型快照（`contract.py`）+ JSON Schema 规则：必填、价格 ≥ 0、日期必须真实存在、不允许多余字段 |
| 角色权限 | admin 可写、viewer 只读；viewer 的增/改/删都要 403，且数据不能被改动 |
| 分页 | 首页 / 第二页 / 最后一页不满 / 越界页空列表 / size 非法（0、-1、101）/ 按房型过滤 |
| 库存 | 下单扣库存、售罄 409、删除退还、10 线程抢 5 间房不超卖 |
| 幂等 | 同一个 `Idempotency-Key` 重复提交返回同一单；并发 10 线程同 key 只建一单；不带 key 仍是两单 |
| 并发 | 10 线程并发建 30 条不重号、不丢数据、改不同单子互不干扰、重复删除只成功一次、健康检查延迟 < 200ms |
| UI | 页面加载、登录解锁创建、创建后列表可见、空名字显示后端错误、改价、删除、房型选择与库存显示、售罄提示 |

**参数化用例**（`@pytest.mark.parametrize`）一个函数覆盖多个边界值，所以 107 个用例其实只用了 89 个测试函数。

## 几个值得注意的设计

1. **每个用例前清空数据**（`autouse` 夹具）——否则用例执行顺序会影响结果，出现"单跑过、全跑挂"。
2. **造数据的夹具负责善后**——`yield` 之后自动删除，不靠用例自己清理。
3. **端口用 0** 让系统分配，避免和本机其他服务抢端口。
4. **等 `/ping` 通再开始测**，不靠 `sleep` 赌时间。

## 能力清单（已完成 / 没做）

- [x] 本地 mock 服务 + 分层用例（冒烟 / 回归）
- [x] 数据驱动用例（`data/booking_cases.json`）
- [x] 契约快照（字段类型变了就红）
- [x] JSON Schema 规则契约（必填 / 范围 / 真实日期，零依赖校验器）
- [x] 零依赖 HTML 报告（`reports.py`）
- [x] GitHub Actions 五关流水线（静态 → 冒烟 → 回归矩阵 → 覆盖率 → UI）
- [x] 失败重试（`retry.py`，只给 flaky 用例开）
- [x] 并发用例 + 零依赖语句覆盖率（95.0%）
- [x] 角色权限（admin / viewer）与越权用例
- [x] 分页、过滤与边界用例
- [x] 房间库存 + 并发超卖用例
- [x] 幂等键（重复提交只建一单）
- [x] 性能基线（并发梯度 + p95/p99 + 阈值判定，零依赖）
- [x] 真实公开 API 冒烟（dummyjson，10 条联网用例，默认跳过）
- [x] Playwright UI 层（`ui_tests/`，9 条主流程，含房型与库存）
- [x] ruff 静态检查（未定义名字 / 语法错，CI 第 1 关拦截）
- [x] 失败现场留存（截图 + trace，CI 自动上传 artifact）
- [x] 测试方案 + 缺陷记录文档（`docs/`）
- [x] Allure 富报告（Temurin JDK 25 + Allure CLI 2.46.1，本机已装）

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

### 8. 失败重试（治理 flaky 用例）

CI 里最烦的不是"一直红"，而是"有时红有时绿"——这类用例叫 **flaky**（偶发失败）。
`retry.py` 是项目自带的零依赖重试插件（不需要 `pytest-rerunfailures`）：

```python
@pytest.mark.flaky(reruns=2, delay=0.3)
def test_第三方接口():
    ...
```

重试**只对打了标记的用例生效**，跑完会单独打印"重试记录"，点名谁靠重试才过的：

```
  RERUN tests/test_x.py::test_y：第 1 次没通过，0.3s 后重试
------------------------ 重试记录 ------------------------
  tests/test_x.py::test_y  重试 1 次后通过
  共 1 个用例靠重试变绿 —— 记下来查根因，别长期留着
```

**为什么不能全局重试**：重试会掩盖真缺陷，还会拖慢 CI。正确顺序是：先查是不是用例自己的问题（等待时间不够、依赖了执行顺序、共享数据没清），确认是外部抖动才加标记，并把它记进待办。

想看效果：`python -m pytest examples/ -q`（两条故意偶发失败的用例，默认不在回归里跑）。

### 9. 并发安全

`tests/test_concurrency.py` 用线程池同时打 10 个请求，守四类 bug：

| 场景 | 断言 | 打中的是哪类 bug |
|---|---|---|
| 并发创建 30 条 | ID 不重复、列表正好 30 条 | 发号没加锁 → 两张单拿到同一个号 |
| 并发读 | 读到的条数稳定 | 读写同一份数据没隔离 |
| 并发改不同单子 | 互不串数据 | 共享状态写错 |
| 并发删同一条 | 只有 1 个返回 201 | "先查再删"两步之间被插队 |

写这组用例时顺手审出 mock 的 `do_DELETE` 是"先查在不在、再删"两步——实测 240 次并发删除没撞上（窗口只有几微秒），但结构上就是错的，已改成一把锁里的原子 `pop`。**代码审查能发现的问题，别等线上发生。**

### 10. 覆盖率（零依赖）

`python coverage_simple.py` 用标准库 `sys.settrace` 统计 `mock_server.py` 的语句覆盖：

```
被测文件: mock_server.py
可执行行: 282    已覆盖: 268    覆盖率: 95.0%
未覆盖的行: 143、177-178、352-361、365
```

- **分母** = 编译后字节码里的可执行行（不是"文件共多少行"）；
- **分子** = 跑完接口场景后真正执行过的行；
- `123-124` 是"页面文件缺失"的兜底分支，`229-238` 是命令行入口 `main()`，都属于正常走不到的行。

CI 里带 `--min 90`，覆盖率掉下去流水线直接红。

### 11. UI 层（Playwright）

接口通了不代表用户能用——按钮没绑事件、字段渲染错位，接口测试一个都发现不了。
所以给 mock 配了一个管理页面 `web/index.html`（原生 HTML + JS，无构建步骤），
再用 Playwright 从浏览器里点它：

![预订管理页面](docs/ui-page.png)

**最省事的装法**：双击 `安装UI依赖.bat`（自动装包 + 下载浏览器），装完双击 `运行UI测试.bat`。

命令行装法：

```bash
pip install -r requirements-ui.txt      # 装 playwright
python -m playwright install chromium   # 下载浏览器（约 300MB，只需一次）
python -m pytest ui_tests -v
```

> `运行UI测试.bat` 会先自检：没装 playwright 或浏览器没装好时，它会直接告诉你缺什么、该双击哪个文件，不会一闪而过。

用例覆盖：页面加载（未登录时创建按钮禁用）→ 登录解锁 → 创建后列表出现 →
空名字提交显示后端错误 → 改价生效 → 删除后行消失。

后来又补了**房型与库存**：选「限量间」下单后，页面顶部的余量从 5 变 4；卖光后再点创建，
页面直接显示「limited 房间已售罄」——UI 用例现在也能证明"前端真的把库存算对了"。

**两个关键写法**

1. **自动等待**：用 `expect(locator).to_have_text(...)` 而不是 `assert page.text_content(...)`——
   `expect` 会轮询到超时，页面还没渲染完也不会误报，不用写 `time.sleep`。
2. **每个用例独立 context**：cookie / 存储隔离，用例之间不会串登录态。

**失败时自动留证据**：用例红了会往 `artifacts/ui/` 写两样东西——

```
artifacts/ui/test_change_price_updates_the_row-20261104-194148.png   失败瞬间整页截图
artifacts/ui/test_change_price_updates_the_row-20261104-194148.zip   Playwright trace
```

截图能直接看出"卡在哪个状态"，trace 可以逐步回放：

```bash
python -m playwright show-trace artifacts/ui/xxx.zip
```

CI 里 UI 关失败时会把这个目录作为 artifact 上传，不用在本机复现。

> UI 用例放在 `ui_tests/` 而不是 `tests/`：默认 `pytest` 不加载浏览器，没装 Playwright 的机器照样能跑接口用例。CI 里 UI 是单独一关（第 4 关）。

### 12. 契约升级：JSON Schema（零依赖）

`contract.py` 的快照只能证明"结构没变"，管不了"值合不合法"——`totalprice: -1` 类型仍是数字，快照照样通过。
`schema_validator.py` 补上规则级契约，用 4 份 schema 描述"什么样的响应才算合法"：

| schema | 管什么 |
|---|---|
| `booking.schema.json` | 5 个字段必填、价格 ≥ 0、日期必须是真实存在的 YYYY-MM-DD、不许多字段 |
| `booking_created.schema.json` | `bookingid` 为正整数 + `booking` 复用上面的定义（`$ref`） |
| `booking_list.schema.json` | 数组，每项只有 `bookingid` |
| `error.schema.json` | 错误响应必须有非空 `error` 字段 |

```bash
python -m pytest tests/test_schema.py -v
```

校验器只有 100 多行，支持 `type / required / properties / items / enum / minimum / maximum / minLength / format(date) / $ref`，
报错会一次性列出所有问题：

```
SchemaError: 契约不符：
  - 创建响应.booking.totalprice: 不能小于 0，实际 -1
  - 创建响应.booking.bookingdates.checkin: 不是真实存在的日期，实际 '2026-13-45'
```

**为什么自己写而不用 jsonschema 包**：这个项目坚持"不装包也能跑"，而且校验器本身也当教学材料——
面试被问"什么是契约测试"时，能说清快照和规则的区别，比背定义强。

### 13. Allure 报告（需要 Java）

Allure 能出"用例分组、步骤、附件、趋势"的富报告，代价是要 Java 运行时。本机已装好：

| 组件 | 位置 | 说明 |
|---|---|---|
| Temurin JDK 25 | `D:\tools\jdk-25.0.5+8` | 免安装 zip，用户级；`JAVA_HOME` 已设 |
| Allure CLI 2.46.1 | `D:\tools\allure-2.46.1` | 解压版，`bin` 已加进用户 PATH |
| allure-pytest | pip 包 | 已并入 `requirements.txt` |

```powershell
python -m pytest --alluredir=allure-results -q
allure serve allure-results      # 起服务并自动开浏览器
```

也可以双击 `生成Allure报告.bat`（会先检查 JAVA_HOME 和 allure 是否就绪）。

![Allure 报告](docs/allure-report.png)

**报告里有什么，全靠这几行标注撑起来**：

| 标注 | 用在哪 | 报告里看到的效果 |
|---|---|---|
| `allure.feature("接口 · CRUD")` | 每个测试文件顶部（`pytestmark`） | Behaviors 视图按业务分组，一眼看出哪块测得多 |
| `@allure.story("创建预订")` | 关键用例 | 同一个 feature 下再按场景分层 |
| `@allure.severity(CRITICAL)` | 核心用例 | 报告里标出严重级别，能按级别筛 |
| `with allure.step("POST /booking 创建一条预订")` | 多步骤用例 | 报告里展开成执行步骤，失败停在哪一步一目了然 |
| `allure.attach(response.text, ...)` | 关键断言前 | 响应体直接挂在报告里，不用回头复现 |
| UI 失败截图 | `ui_tests/conftest.py` | 失败用例详情页直接看图 |
| `environment.properties` | `conftest.py` 自动写 | 报告 Environment 区块显示服务地址 / Python / 系统 |

![用例详情：步骤与附件](docs/allure-test-detail.png)

**VS Code 能装 JDK 吗**：VS Code 本身不装 JDK，是"Extension Pack for Java"扩展会提示下载一个，需要你在窗口里点确认。这次改用命令行装了免安装版（不需要管理员）；以后要写 Java，在 VS Code 里装 Java 扩展、把 `java.jdt.ls.java.home` 指向 `D:\tools\jdk-25.0.5+8` 就能复用同一个 JDK。

**环境坑（已修复）**：机器 PATH 里曾有一条 2021 年 Oracle 残留的 `C:\Program Files\Common Files\Oracle\Java\javapath`，指向已删除的 JRE、又排在用户 PATH 前面，导致直接敲 `java -version` 会崩（0xC0000005）。已用管理员脚本 `D:\tools\fix-java-path.ps1` 删掉该条目，并把 `D:\tools\jdk-25.0.5+8\bin` 放到机器 PATH 首位（原 PATH 备份在 `D:\tools\machine-path-backup.txt`，可回滚）。**新开的窗口**里 `java -version` 已正常；已经开着的终端 / VS Code 要重启才能读到新 PATH。

### 14. 业务模型升级：角色 / 分页 / 库存

只测 CRUD 练不出真本事，所以给 mock 加了三样真实系统才有的东西（纯标准库，无外部依赖）：

| 能力 | 入口 | 关键行为 |
|---|---|---|
| 角色权限 | `POST /auth` 用 admin / viewer 两个账号 | admin 可写，viewer 只读；写操作越权返回 403 |
| 分页与过滤 | `GET /booking?page=1&size=10&roomtype=limited` | 带 `page/size` 返回信封 `{items,total,page,size}`，不带则保持数组（向后兼容） |
| 房间库存 | `GET /rooms`、`POST /booking?roomtype=limited` | 下单扣库存、售罄 409、删除退还 |

**这三个能力各自撞出了一个真实缺陷**（详见 `docs/缺陷记录.md`）：

- **越权**：admin 校验只写在了"创建"上，viewer 居然能 PUT / PATCH / DELETE → 测试抓红 → 四个写接口统一走 `_admin_only()`；
- **超卖**：库存是"先查、再扣"两步，10 个线程抢 5 间房卖出了 9 间 → 改成锁内一次性 `reserve()`。

超卖那条不是靠碰运气：mock 里用 10ms 模拟"查库存要访问数据库"的耗时，竞态窗口才真实存在；修完之后延迟去掉，套件仍然 3 秒内跑完。

```powershell
python -m pytest tests/test_roles.py tests/test_pagination.py tests/test_inventory.py -v
```

### 15. 幂等：重复提交只成功一次

用户手抖点两下、客户端超时重试、消息队列重投，都会让同一个请求到达两次。
接口约定：请求头带 `Idempotency-Key`，重复提交返回**第一次那一单**。

```powershell
python -m pytest tests/test_idempotency.py -v
```

关键在"查 key + 扣库存 + 发号 + 记 key"必须在同一把锁里完成：

```python
def create_once(self, body, roomtype, idempotency_key=None):
    with self.lock:
        if idempotency_key and idempotency_key in self.idempotent:
            return self.idempotent[idempotency_key], False   # 重放：不改任何状态
        ...
```

用例里最狠的一条是 **10 个线程拿同一个 key 同时提交**：

| 实现方式 | 结果 |
|---|---|
| 先查 key、再建单（两步） | 10 个线程同时查不到 → 建出 10 单 |
| 查 + 建在同一把锁里 | 只有 1 单，其余 9 个返回同一个 bookingid |

另外，删除预订会顺手清掉指向它的幂等键，避免重放时返回"幽灵单"。

### 16. 性能基线：并发梯度 + p95/p99

功能测试问"对不对"，性能基线问"多快、并发上去会不会塌"。

```powershell
python perf_load.py                          # 默认 120 请求，并发 1/5/20
python perf_load.py --requests 300 --levels 1,10,50
```

实测输出（本机，仅标准库线程池）：

```
场景     并发   请求数   p50     p95     p99     最大    吞吐       错误
ping      1     80     1.7ms   1.9ms   2.0ms   2.1ms   589.2/s    0
ping     10     80    12.6ms  13.9ms  14.5ms  14.6ms   764.6/s    0
ping     30     80    33.7ms  38.2ms  39.2ms  39.7ms   716.2/s    0
create    1     80     1.9ms   2.2ms   2.3ms   4.4ms   518.6/s    0
create   10     80    13.9ms  15.7ms  17.0ms  17.5ms   676.9/s    0
create   30     80    36.9ms  45.7ms  46.4ms  46.6ms   648.5/s    0
```

- 每个场景每个并发级都从干净库存开始（脚本内部直接 `STORE.reset()`）；
- p95 超过阈值就返回退出码 1，CI 里当"参考数据"跑（不阻断）；阈值可用 `--p95-ping` 等参数放宽；
- 结果同时写进 `perf-results.json`，CI 作为 artifact 上传。

**第一次跑就发现一个真问题**：并发 10 时 p99 突然飙到 515ms。原因是 `ThreadingHTTPServer` 默认监听队列只有 5，
多出来的连接在队列里排队。把 `request_queue_size` 调到 64 后，p99 回到 14ms 左右——
这就是性能基线存在的意义：**功能全绿的时候，它还能告诉你哪里在悄悄变慢**。

### 17. Allure 历史趋势

单次报告只回答"这一轮过没过"；趋势图回答"这几周有没有变差"。

```powershell
python allure_run.py          # 跑用例 + 带上历史 + 生成报告
python allure_run.py --open   # 生成后直接打开
```

原理很简单：Allure 的 Trend 读的是报告目录里的 `history/`。所以每次生成前，先把上一次的
`allure-report/history` 拷进 `allure-results/`，生成时它就会被带进新报告。本地连跑两次就能看到折线。

CI 里用 `actions/cache` 把 `allure-history` 存下来（key 用 `run_id`，`restore-keys` 前缀匹配上一份），
每次运行先恢复、跑完再写回，于是 GitHub 上的报告也能积累趋势——不用 gh-pages、不用额外服务器。

`生成Allure报告.bat` 也已经改成调用 `allure_run.py`，双击即可。

### 18. 静态检查（ruff）

`compileall` 只能发现语法错，管不了"名字写错了、变量没定义"。加一层 ruff：

```bash
pip install ruff
ruff check .
```

配置（`ruff.toml`）只开 `E9 / F63 / F7 / F82` 四组规则——语法错、未定义名字、无效比较、重复定义。
不启风格规则，因为这里的目标是"发现 bug"，不是"统一空格"。

**接入第一天就抓到两个真问题**：

1. `reports.py` 里有一段重构后遗留的死代码，引用着已经改名的 `HTML_OUT` / `render_html`；
2. `tester_gui.py` 的异常回调写成 `lambda: self._fail(err)`——`err` 在 `except` 块结束后会被删除，
   回调真正执行时必然 `NameError`。

两个都不是风格问题，是"不跑不知道、跑了才炸"的问题。CI 第 1 关现在会跑 `ruff check .`，这类问题进不了主干。

### 19. 真实公开 API：换环境也能跑

本地 mock 是自己写的靶场，真实项目里接口不归你管。为了验证"这套用例思路不是只能跑在我家"，
加了一组对 [dummyjson](https://dummyjson.com)（公开假数据 API）的联网用例：

```powershell
$env:LIVE_API = "1"
python -m pytest live_tests -v
```

或者双击 `运行真实API测试.bat`。

10 条用例：登录拿 JWT、错密码被拒、详情契约校验、分页 total/limit/skip、翻页换窗口、
创建返回新 id、更新标题、删除标记 `isDeleted`、跨公网延迟冒烟。

和本地套件的三个不同：

1. **默认不跑**：`LIVE_API=1` 才执行，日常回归不被外网拖慢；
2. **连不上就 skip**：网络问题不该报成"测试失败"；
3. **阈值放宽**：延迟从 200ms 放到 3s——测的是"通不通、会不会离谱"。

实测 `10 passed in 22.52s`（跨公网，比本地 1.4 秒慢十几倍，但结论一样）：
**同一套测试思路，换一个不受控的服务照样能跑**。

## 这个项目自己发现过七个问题

写完数据驱动用例后，**测试立刻抓到 mock 服务的两个真实缺陷**：

| 缺陷 | 症状 | 修复 |
|---|---|---|
| 空名字能创建 | `firstname: ""` 返回 200 | `validate()` 加非空检查 |
| 假日期能通过 | `2026-13-45` 被接受 | 正则只管位数，改用 `datetime.strptime` 真校验 |

补充 `checkout > checkin` 规则后，用例从 2 failed 变成全绿。

第三个问题是写并发用例时审出来的：`do_DELETE` 里"先查在不在、再删"不是原子操作（见第 9 节），已经改成一把锁里完成。

第四个问题是补"等价类划分"时发现的：`totalprice` 只校验了类型没校验范围，**负数价格也能创建**。
补用例 → 变红 → 加一行范围校验 → 变绿（详细过程见 `docs/缺陷记录.md` 的 BUG-004）。

第五、六个问题是升级业务模型时撞出来的：**viewer 能删数据**（越权）和**10 人抢 5 间房卖出 9 间**（超卖）。前者是"校验写漏了一个接口"，后者是"锁只加了一半"，都是真实项目里最常见的两类错。

第七个是 ruff 静态检查抓的：`tester_gui.py` 里异常回调 `lambda: self._fail(err)` 捕获的是 `except` 块结束就失效的变量，真出错时反而抛 `NameError`，把原始错误盖住了。

**这就是测试的价值**——不是"证明代码是对的"，是"在它错的时候立刻知道"。

## 还能加什么

- [ ] 用 `pytest-xdist` 把用例并行跑（现在 3 秒，收益不大，属于扩展练习）
- [ ] 把 `API_BASE_URL` 指向一个真实后端，验证"同一套用例换环境能跑"

