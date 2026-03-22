# 自动化建造游戏通用合成计算器 - 项目上下文

## 项目概述

自动化建造游戏通用合成计算器用于计算生产链和所需设备数量，帮助玩家计算生产特定物品所需的基础原料、设备数量和完整的合成树结构。

**主要功能：**
- 配方数据管理（支持多个游戏配方文件）
- 复杂表达式解析（数学表达式 + 时间单位转换）
- 合成树构建和多路径计算
- 设备数量统计和基础原料消耗分析
- 终端交互界面 + Web浏览器界面

## 技术栈

- **编程语言：** Python 3.12
- **核心库：** Python 标准库（json, os, re, math, typing）
- **Web框架：** Flask
- **数据格式：** JSON
- **测试框架：** pytest 7.x + pytest-cov

## 项目结构

```
合成计算/
├── main.py                  # 主程序入口（终端模式）
├── io_interface.py          # 输入输出抽象接口
├── application_controller.py # 应用程序控制器
├── calculator.py            # 核心计算引擎
├── expression_parser.py     # 表达式解析模块
├── data_manager.py         # 数据管理模块
├── config_manager.py       # 配置管理模块
├── pyproject.toml          # 项目配置文件
├── shared/                 # 共享模块目录
│   ├── api/                # 公共API模块
│   │   ├── __init__.py
│   │   ├── calculation_api.py
│   │   ├── recipe_api.py
│   │   └── session.py
│   ├── utils/              # 工具函数目录
│   │   └── __init__.py
│   └── __init__.py
├── tests/                  # 单元测试目录
├── web/                    # Web测试接口目录（终端风格）
│   ├── web_server.py      # Flask Web服务器
│   ├── test_recipe_api.py # API测试脚本
│   └── templates/
│       └── index.html     # Web前端界面
├── web_gui/                # Web GUI应用目录（现代化界面）
│   ├── app.py             # Flask GUI应用
│   ├── static/            # 静态资源
│   │   ├── css/
│   │   │   └── main.css
│   │   └── js/
│   │       └── main.js
│   └── templates/         # HTML模板
│       ├── base.html
│       ├── dashboard.html
│       ├── select_game.html
│       ├── calculate.html
│       └── recipe_management.html
├── recipes/                # 配方文件存储目录
└── config.json             # 用户配置文件
```

## 核心模块说明

| 模块 | 职责 |
|------|------|
| `io_interface.py` | IO抽象接口，`IOInterface`基类 + `TerminalIO`/`WebIO`实现 |
| `application_controller.py` | 业务逻辑层，配方管理（增删改查）、路径对比、主菜单处理 |
| `main.py` | 终端入口，创建 `TerminalIO` + `ApplicationController` |
| `calculator.py` | 计算引擎，`CraftingNode`、`CraftingCalculator`、`PathComparisonEngine` |
| `expression_parser.py` | 解析数学表达式和时间单位（如 `15/min` → 个/秒） |
| `data_manager.py` | 配方数据的加载、保存、搜索、验证 |
| `config_manager.py` | 配置持久化，记忆上次选择的配方文件 |
| `web/web_server.py` | Flask Web服务器，RESTful API + 终端风格Web界面 |
| `web_gui/app.py` | Flask Web GUI应用，现代化图形界面 |
| `shared/api/` | 公共API模块，提供跨Web应用的共享会话管理、配方API、计算API等功能 |

### API 端点（web/web_server.py）

```
GET  /api/games              # 获取配方文件列表
POST /api/select-game        # 选择配方文件
GET  /api/items              # 获取物品列表
GET  /api/recipes            # 获取配方列表（支持分页、搜索）
GET  /api/recipes/<name>     # 获取单个配方详情
POST /api/recipes            # 创建新配方
PUT  /api/recipes/<name>     # 更新配方
DELETE /api/recipes/<name>   # 删除配方
POST /api/calculate          # 计算生产链
POST /api/calculate/switch-path  # 切换到指定路径
GET  /api/calculate/alternatives  # 获取节点的可选路径
GET  /api/paths/compare      # 对比多条路径
POST /api/terminal           # 终端命令处理（主要测试接口）
POST /api/reset              # 重置终端会话
```

### API 端点（web_gui/app.py）

**页面路由：**
```
GET /                        # 首页仪表盘
GET /select-game             # 配方选择页面
GET /calculate               # 生产链计算页面
GET /recipe-management       # 配方管理页面
```

**API 路由：**
```
GET  /api/games              # 获取配方文件列表
POST /api/select-game        # 选择配方文件
GET  /api/items              # 获取物品列表
GET  /api/recipes            # 获取配方列表（支持分页、搜索）
GET  /api/recipes/<name>     # 获取单个配方详情
POST /api/recipes            # 创建新配方
PUT  /api/recipes/<name>     # 更新配方
DELETE /api/recipes/<name>   # 删除配方
POST /api/calculate          # 计算生产链
GET  /api/calculate/alternatives  # 获取节点的可选路径
POST /api/cache/clear        # 清除所有缓存
GET  /api/cache/stats        # 获取缓存状态信息
```

## 运行方式

### 启动终端程序
```powershell
python main.py
```

### 启动Web服务器（终端风格）
```powershell
python web\web_server.py  # 访问 http://127.0.0.1:5000
```

### 启动Web GUI服务器（现代化界面）
```powershell
python web_gui\app.py  # 访问 http://127.0.0.1:5000
```

### 使用流程
1. 程序自动加载上次选择的配方文件
2. 选择配方文件（或创建新文件）
3. 输入目标物品名称
4. 输入目标生产速度（支持表达式，如 `15/min`）
5. 查看计算结果（生产链、设备统计、基础原料）

## 配方文件格式

```json
{
  "配方名称": {
    "device": "设备名称",
    "inputs": {
      "输入物品": {"amount": 10.0, "expression": "10"}
    },
    "outputs": {
      "输出物品": {"amount": 5.0, "expression": "5"}
    }
  }
}
```

## 表达式语法

- **纯数学表达式：** `8*3/2`、`(10+5)*2/60`
- **带时间单位：** `15/min`、`2.5*3.14/h`
- **支持单位：** `s/sec/second`, `m/min/minute`, `h/hour`
- **数学函数：** `sin`, `cos`, `sqrt`, `pow`, `abs`, `round`
- **常量：** `pi`, `e`

**转换规则：** 所有表达式最终转换为 **个/秒**

## 配置文件格式

```json
{"last_game": "配方文件名"}
```

## 重要特性

### IO抽象层架构
- 通过 `IOInterface` 分离业务逻辑和交互方式
- 终端和Web界面共享相同的 `ApplicationController`
- 易于扩展新界面（如GUI）

### 多路径计算与路径对比
- **主路径自动选择：** 根据设备数量选择最优路径
- **节点标记 `[+N]`：** 表示该节点有 N 条其他可选路径
- **交互式路径切换：** `alt <节点编号>` 命令切换路径

### 智能提示功能
- 设备/物品名称建议，按使用频率排序
- 最近使用优先，模糊搜索支持
- 表达式实时预览（如 `15/min` → `0.25/秒`）

## 常见任务

### 配方管理（增删改查）

**终端模式：**
1. 运行 `python main.py`
2. 选择 `4. 配方管理` 进入子菜单
3. 选择操作：`1`查看 `2`添加 `3`修改 `4`删除

**Web API：** 见上方 API 端点列表

### 计算生产链

**终端模式：**
1. 选择 `2. 计算生产链`
2. 输入目标物品和生产速度
3. 查看结果（主路径、带 `[+N]` 标记的节点）
4. **路径对比命令：**
   - `alt <编号>` / `a <编号>` - 切换到替代路径
   - `la` / `list-alt` - 列出所有带标记的节点
   - `h` / `help` - 显示帮助
   - `q` / `quit` - 退出

**Web 模式：** 访问 http://127.0.0.1:5000，操作与终端一致

### 终端命令格式

**主菜单：**
```
1              # 选择配方文件
1 <序号>       # 直接选择指定配方文件
2              # 计算生产链
2 <物品> <速度> # 直接计算
3              # 查看物品列表
4              # 配方管理
5/exit/quit    # 退出
help           # 显示帮助
reset          # 重置会话
```

**配方管理子菜单：**
```
1  # 查看配方列表
2  # 添加配方
3  # 修改配方
4  # 删除配方
5  # 返回主菜单
```

## 单元测试

```powershell
python -m pytest tests/                                    # 运行所有测试
python -m pytest tests/ --cov=. --cov-report=html         # 生成覆盖率报告
python -m pytest tests/test_expression_parser.py          # 运行特定测试文件
python -m pytest tests/ -m unit                           # 只运行单元测试
python -m pytest tests/ -m integration                    # 只运行集成测试
```

### 测试覆盖情况

| 模块 | 测试文件 | 覆盖率 |
|------|---------|--------|
| expression_parser.py | test_expression_parser.py | 82% |
| config_manager.py | test_config_manager.py | 98% |
| data_manager.py | test_data_manager.py | 98% |
| calculator.py | test_crafting_*.py, test_path_*.py, test_byproduct_pool.py, test_special_recipe_*.py, test_raw_resource_devices.py, test_net_output_calculation.py | 92% |
| io_interface.py | test_io_interface.py | 92% |
| application_controller.py | test_application_controller.py | 10% |
| web_gui | test_web_gui.py | - |
| **整体** | 293+ 个测试用例 | **57%** |

### 测试 Fixtures

项目使用 pytest fixtures 提供共享的测试数据：

- `temp_dir`: 临时目录
- `sample_recipes`: 示例配方数据
- `recipe_manager`: 配方管理器实例
- `config_manager`: 配置管理器实例
- `calculator`: 合成计算器实例
- `path_comparison_engine`: 路径对比引擎实例
- `terminal_io`: 终端IO实例
- `web_io`: WebIO实例
- `application_controller`: 应用控制器实例

### pytest.ini 配置

```ini
[pytest]
testpaths = tests
python_files = test_*.py
addopts = -v --strict-markers
markers =
    unit: 单元测试
    integration: 集成测试
    slow: 慢速测试
```

## 路径对比功能说明

### 主路径选择算法
1. **总设备数量最少**（首要标准）
2. **配方数量更少**（设备数相同时）
3. **选择第一个**（以上都相同时）

### 路径切换流程
1. 计算生产链后，系统显示主路径和带标记的节点
2. 输入 `la` 查看所有带标记的节点及其编号
3. 输入 `alt <编号>` 查看该节点的所有替代路径
4. 选择要切换的路径，系统显示设备数量变化
5. 确认后重新显示生产链

## 环境信息

- **Python 版本：** 3.12
- **操作系统：** Windows 10/11
- **Shell：** PowerShell 5.1

## 注意事项

1. 所有配方文件的 amount 字段最终会转换为标准单位（个/秒）
2. 物品名称搜索时忽略首尾空格
3. 基础原料指没有配方可以生产的物品
4. 设备数量计算基于配方输出速度
5. 程序支持多个游戏配方文件同时存在

## 项目历史

- 最初计划 GUI 版本（tkinter），后改为终端版本
- 添加基于 Flask 的 Web 浏览器界面
- 重构为 IO 抽象层架构，终端和 Web 共享业务逻辑
- 新增配方管理增删改查功能
- 新增路径对比功能（主路径选择、节点标记、路径切换）
- 新增 shared 目录，提取公共 API 模块，实现跨 Web 应用的共享功能
- 添加 pyproject.toml 项目配置文件
- 重构 Web 应用，统一使用共享的 API 模块
- 新增缓存管理功能，提高计算性能
- 新增路径切换相关的 API 端点
