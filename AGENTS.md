# 自动化建造游戏通用合成计算器 - 项目上下文

## 项目概述

自动化建造游戏通用合成计算器用于计算生产链和所需设备数量，帮助玩家计算生产特定物品所需的基础原料、设备数量和完整的合成树结构。

**主要功能：**
- 配方数据管理（支持多个游戏配方文件）
- 复杂表达式解析（数学表达式 + 时间单位转换）
- 合成树构建和多路径计算
- 设备数量统计和基础原料消耗分析
- 终端交互界面

## 技术栈

- **编程语言：** Python 3.12
- **核心库：** Python 标准库（os, re, math, typing）
- **第三方库：** PyYAML（YAML 数据解析）
- **数据格式：** YAML
- **测试框架：** pytest 7.x + pytest-cov

## 项目结构

```
合成计算/
├── main.py                  # 主程序入口（终端模式）
├── io_interface.py          # 输入输出抽象接口
├── application_controller.py # 应用程序控制器
├── calculator.py            # 核心计算引擎（CraftingCalculator）
├── crafting_node.py         # 合成树节点（CraftingNode）
├── path_engine.py           # 路径对比引擎（PathComparisonEngine）
├── recipe_analyzer.py       # 配方分析（RecipeAnalyzer、RecipeType）
├── byproduct_pool.py        # 副产品池（ByproductPool）
├── expression_parser.py     # 表达式解析模块
├── data_manager.py         # 数据管理模块
├── config_manager.py       # 配置管理模块
├── pyproject.toml          # 项目配置文件
├── shared/                 # 共享模块目录
│   ├── utils/              # 工具函数目录
│   │   └── __init__.py     # 含 format_device_count（设备数显示格式化）
│   └── __init__.py
├── tests/                  # 单元测试目录
├── recipes/                # 配方文件存储目录（YAML 格式）
└── config.yaml             # 用户配置文件
```

## 核心模块说明

| 模块 | 职责 |
|------|------|
| `io_interface.py` | IO抽象接口，`IOInterface`基类 + `TerminalIO`实现 |
| `application_controller.py` | 业务逻辑层，无状态单步命令分发（`_dispatch` + 各 `_cmd_*`） |
| `main.py` | 终端入口，创建 `TerminalIO` + `ApplicationController` |
| `calculator.py` | 计算引擎主模块，`CraftingCalculator`（合成树构建、设备数计算、路径标记） |
| `crafting_node.py` | 合成树节点 `CraftingNode`（支持主/替代路径标记） |
| `path_engine.py` | 路径对比引擎 `PathComparisonEngine`（主路径选择、替代路径查找） |
| `recipe_analyzer.py` | 配方分析 `RecipeAnalyzer` + `RecipeType`（净产出/净消耗/设备数/配方类型） |
| `byproduct_pool.py` | 副产品池 `ByproductPool`（副产品收集、消耗、溢出检测） |
| `expression_parser.py` | 解析数学表达式和时间单位（如 `15/min` → 个/秒） |
| `data_manager.py` | 配方数据的加载、保存、搜索、验证（YAML 格式） |
| `config_manager.py` | 配置持久化，记忆上次选择的配方文件（YAML 格式） |
| `shared/utils/` | 公共工具函数（YAML 文件读写、树遍历、设备数格式化等） |

## 运行方式

### 启动终端程序
```powershell
python main.py
```

### 设计原则：无状态单步命令
会话进程内存**不保存任何业务状态**，所有状态通过两种方式传递：
- **命令参数**：一次性传入（如 `calc 铁锭 15/min`）
- **持久化文件**：`config.yaml` 记忆当前配方文件，`recipes/*.yaml` 存配方数据

每条命令独立执行（读命令 → 解析参数 → 从 config 读取上下文 → 执行 → 输出 → 不保存任何内存状态），命令间不共享内存状态。REPL 循环仅用于组合多个单步命令。

### 使用流程
1. 启动后程序显示当前配方文件（从 `config.yaml` 读取）
2. 用 `use <文件名>` 选择配方文件
3. 用 `calc <物品> <速度>` 计算生产链
4. 用 `alts`/`use-path` 查看或切换替代路径（每次重新计算）
5. 用 `recipe add/set-*/delete` 管理配方

## 配方文件格式

```yaml
配方名称:
  device: 设备名称
  inputs:
    输入物品:
      amount: 10.0
      expression: "10"
  outputs:
    输出物品:
      amount: 5.0
      expression: "5"
```

## 表达式语法

- **纯数学表达式：** `8*3/2`、`(10+5)*2/60`
- **带时间单位：** `15/min`、`2.5*3.14/h`
- **支持单位：** `s/sec/second`, `m/min/minute`, `h/hour`
- **数学函数：** `sin`, `cos`, `sqrt`, `pow`, `abs`, `round`
- **常量：** `pi`, `e`

**转换规则：** 所有表达式最终转换为 **个/秒**

## 配置文件格式

```yaml
last_game: 配方文件名
```

## 重要特性

### IO抽象层架构
- 通过 `IOInterface` 分离业务逻辑和交互方式
- 终端实现 `TerminalIO`，易于扩展新的交互方式
- `input()` 仅用于 REPL 读取下一条命令行，无多步阻塞输入

### 无状态会话
- `ApplicationController` 实例仅持有 `io` 和 `recipe_manager`（无状态文件操作门面）
- 不缓存 `current_game`、`calculator`、计算结果等任何业务状态
- 每条命令通过 `_require_game()` 从 `config.yaml` 读取当前配方文件并按需创建 `CraftingCalculator`
- 路径切换不依赖前序 `calc` 结果，每次 `alts`/`use-path` 都重新计算

### 多路径计算与路径对比
- **主路径自动选择：** 根据设备数量选择最优路径
- **节点编号 `#N`：** 前序遍历编号（根=1），与 `alts`/`use-path` 命令的节点编号一致
- **节点标记 `[+N]`：** 表示该节点有 N 条其他可选路径
- **无状态路径切换：** `alts` 列出替代路径，`use-path` 重新计算并切换（不缓存中间树）

## 常见任务

### 配方管理（增删改查）

每步操作都是独立的单步命令：
```
recipe add <名称> --device <设备> --inputs <物品:表达式,...> --outputs <物品:表达式,...>
recipe set-device <名称> <设备>
recipe set-inputs <名称> <物品:表达式,...>
recipe set-outputs <名称> <物品:表达式,...>
recipe delete <名称>
recipe <名称>            # 查看详情（等价于 recipe show <名称>）
```

物品列表格式：`铁矿石:10,煤:5`（表达式可省略，默认 1）

### 计算生产链

```
calc <物品> <速度>                                # 计算主路径，输出节点编号和 [+N] 标记
alts <物品> <速度> <节点编号>                     # 查看该节点的所有替代路径详情
use-path <物品> <速度> <节点编号> <路径编号>      # 重新计算并切换到指定替代路径
```

`alts` 和 `use-path` 每次都重新计算，无需先执行 `calc`，命令间无状态依赖。

### 终端命令格式

**REPL 命令（每条独立无状态）：**
```
games                                # 列出所有配方文件
use <文件名>                         # 选择配方文件（持久化到 config.yaml）
game                                 # 显示当前配方文件
calc <物品> <速度>                   # 计算生产链（主路径）
alts <物品> <速度> <节点编号>        # 查看节点替代路径
use-path <物品> <速度> <节点编号> <路径编号>  # 切换到指定替代路径
items                                # 列出所有物品
recipes [页码] [搜索词]              # 列出配方
recipe <名称>                        # 查看配方详情
recipe add <名称> --device <设备> --inputs <列表> --outputs <列表>
recipe set-device <名称> <设备>      # 修改设备
recipe set-inputs <名称> <列表>      # 修改输入
recipe set-outputs <名称> <列表>     # 修改输出
recipe delete <名称>                 # 删除配方
help                                 # 显示所有命令
quit / exit / q                      # 退出
```

速度支持表达式（如 `15/min`、`8*3/2`）。命令大小写不敏感。

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
| expression_parser.py | test_expression_parser.py | 80% |
| config_manager.py | test_config_manager.py | 90% |
| data_manager.py | test_data_manager.py | 98% |
| calculator.py | test_crafting_calculator.py, test_integration.py, test_raw_resource_devices.py | 87% |
| crafting_node.py | test_crafting_node.py, test_path_comparison_engine.py | 100% |
| path_engine.py | test_path_comparison_engine.py | 98% |
| recipe_analyzer.py | test_special_recipe_detection.py, test_net_output_calculation.py, test_special_recipe_integration.py | 89% |
| byproduct_pool.py | test_byproduct_pool.py, test_special_recipe_integration.py | 100% |
| shared/utils/ | test_shared_utils.py 等 | 81% |
| io_interface.py | test_io_interface.py | 84% |
| application_controller.py | test_application_controller.py | 83%（无状态命令测试） |
| **整体** | 438 个测试用例 | **95%** |

### 测试 Fixtures

项目使用 pytest fixtures 提供共享的测试数据：

- `temp_dir`: 临时目录
- `sample_recipes`: 示例配方数据
- `recipe_manager`: 配方管理器实例
- `config_manager`: 配置管理器实例
- `calculator`: 合成计算器实例
- `path_comparison_engine`: 路径对比引擎实例
- `terminal_io`: 终端IO实例
- `application_controller`: 应用控制器实例

### pytest 配置

pytest 配置位于 `pyproject.toml` 文件中：

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
addopts = "-v --strict-markers"
markers = [
    "unit: 单元测试",
    "integration: 集成测试",
    "slow: 慢速测试",
]
```

## 路径对比功能说明

### 主路径选择算法
1. **总设备数量最少**（首要标准）
2. **配方数量更少**（设备数相同时）
3. **选择第一个**（以上都相同时）

### 无状态路径切换流程
1. `calc <物品> <速度>` 计算并显示主路径，节点带 `#N` 编号和 `[+N]` 标记，末尾列出带替代路径的节点
2. `alts <物品> <速度> <节点编号>` 重新计算主路径，定位编号节点，输出其所有替代路径详情（含设备数差异）
3. `use-path <物品> <速度> <节点编号> <路径编号>` 重新计算，构建切换后的树并显示完整生产链

三步命令相互独立，每步都从命令参数获取完整输入，不依赖前序命令的内存状态。

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
6. 配方文件和配置文件统一使用 YAML 格式（`.yaml` 或 `.yml` 扩展名）

## 项目历史

- 最初计划 GUI 版本（tkinter），后改为终端版本
- 重构为 IO 抽象层架构，分离业务逻辑和交互方式
- 新增配方管理增删改查功能
- 新增路径对比功能（主路径选择、节点标记、路径切换）
- 新增 shared 目录，提取公共工具函数
- 添加 pyproject.toml 项目配置文件
- 移除 Web 端代码，仅保留终端模式
- 数据格式从 JSON 迁移到 YAML
