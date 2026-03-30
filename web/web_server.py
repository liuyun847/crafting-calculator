"""
自动化建造游戏通用合成计算器 - Web 测试接口

提供与终端程序完全一致的 Web 交互界面，支持浏览器自动化测试。

安全配置：
- Secret Key: 优先从环境变量 FLASK_SECRET_KEY 读取，否则使用开发密钥
- CSRF 保护: 使用 Flask-WTF，API 端点已豁免（纯 API 服务）
"""

import os
import sys
import warnings
from typing import Dict, Any
from flask import Flask, render_template, request, jsonify, session
from flask_wtf.csrf import CSRFProtect

# 导入公共API模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.api import (
    BaseWebSession,
    get_session,
    save_session,
    get_games_api,
    select_game_api,
    get_items_api,
    get_recipes_api,
    get_recipe_api,
    create_recipe_api,
    update_recipe_api,
    delete_recipe_api,
    calculate_api,
    get_alternatives_api,
    compare_paths_api,
)


# ============================================================
# Secret Key 配置
# ============================================================
# 优先从环境变量读取密钥，用于生产环境
# 如果环境变量不存在，使用固定的开发密钥（仅用于开发环境）
_SECRET_KEY = os.environ.get("FLASK_SECRET_KEY")

if _SECRET_KEY is None:
    # 开发环境使用固定密钥（便于调试和测试）
    _SECRET_KEY = "dev-secret-key-for-web-server-only"
    # 在生产环境警告用户设置环境变量
    if os.environ.get("FLASK_ENV") == "production":
        warnings.warn(
            "生产环境应设置环境变量 FLASK_SECRET_KEY 以确保安全！",
            UserWarning,
            stacklevel=2,
        )

app = Flask(__name__)
app.secret_key = _SECRET_KEY

# ============================================================
# CSRF 保护配置
# ============================================================
# 初始化 CSRF 保护
csrf = CSRFProtect(app)


@app.route("/")
def index():
    """渲染前端页面"""
    return render_template("index.html")


@app.route("/api/terminal", methods=["POST"])
@csrf.exempt
def terminal():
    """处理终端命令"""
    data = request.get_json()
    command = data.get("command", "")

    web_session = get_session()
    result = web_session.process_command(command)
    save_session(web_session)

    return jsonify(
        {"success": True,
            "output": result["output"], "prompt": result["prompt"]}
    )


@app.route("/api/reset", methods=["POST"])
@csrf.exempt
def reset():
    """重置会话"""
    web_session = get_session()
    web_session.reset()
    save_session(web_session)
    return jsonify({"success": True, "message": "会话已重置"})


@app.route("/api/games", methods=["GET"])
def get_games():
    """获取配方文件列表"""
    return get_games_api()


@app.route("/api/select-game", methods=["POST"])
@csrf.exempt
def select_game():
    """选择配方文件（终端模式，返回命令输出）"""
    data = request.get_json()
    game_name = data.get("game", "")

    web_session = get_session()
    games = web_session.controller.recipe_manager.get_available_games()

    if game_name in games:
        web_session.io.clear()
        web_session.io.set_input(f"1 {game_name}")
        result = web_session.controller.process_command(f"1 {game_name}")
        save_session(web_session)
        return jsonify(
            {
                "success": True,
                "output": web_session.io.get_output(),
                "prompt": result["prompt"],
            }
        )
    else:
        return jsonify({"success": False, "error": "配方文件不存在"})


@app.route("/api/items", methods=["GET"])
def get_items():
    """获取物品列表"""
    return get_items_api()


@app.route("/api/recipes", methods=["GET"])
def get_recipes():
    """
    获取配方列表

    支持查询参数:
    - page: 页码 (默认 1)
    - per_page: 每页数量 (默认 20, 最大 100)
    - search: 搜索关键词 (搜索配方名称、设备名称、物品名称)
    """
    return get_recipes_api()


@app.route("/api/recipes/<recipe_name>", methods=["GET"])
def get_recipe(recipe_name):
    """
    获取单个配方详情

    Args:
        recipe_name: 配方名称（URL编码）
    """
    return get_recipe_api(recipe_name)


@app.route("/api/recipes", methods=["POST"])
@csrf.exempt
def create_recipe():
    """
    创建新配方

    请求体:
    {
        "name": "配方名称",
        "device": "设备名称",
        "inputs": {
            "物品1": {"amount": 数量, "expression": "原始表达式"},
            ...
        },
        "outputs": {
            "物品1": {"amount": 数量, "expression": "原始表达式"},
            ...
        }
    }
    """
    return create_recipe_api()


@app.route("/api/recipes/<recipe_name>", methods=["PUT"])
@csrf.exempt
def update_recipe(recipe_name):
    """
    更新现有配方（支持部分更新）

    请求体（所有字段都是可选的）:
    {
        "device": "设备名称",
        "inputs": {
            "物品1": {"amount": 数量, "expression": "原始表达式"},
            ...
        },
        "outputs": {
            "物品1": {"amount": 数量, "expression": "原始表达式"},
            ...
        }
    }

    Args:
        recipe_name: 配方名称（URL编码）
    """
    return update_recipe_api(recipe_name)


@app.route("/api/recipes/<recipe_name>", methods=["DELETE"])
@csrf.exempt
def delete_recipe(recipe_name):
    """
    删除配方

    Args:
        recipe_name: 配方名称（URL编码）
    """
    return delete_recipe_api(recipe_name)


# ============================================================
# 路径对比相关API端点
# ============================================================


@app.route("/api/calculate", methods=["POST"])
@csrf.exempt
def calculate_enhanced():
    """
    计算生产链（增强版）

    请求体:
    {
        "target_item": "目标物品名称",
        "target_rate": "目标生产速度（支持表达式如 '15/min'）",
        "game_name": "配方文件名称（可选，使用已选择的游戏）",
        "options": {
            "compare_paths": true,  // 是否启用路径对比
            "show_main_path_only": false,  // 是否只显示主路径
            "mark_alternatives": true  // 是否标记替代路径
        }
    }

    返回:
    {
        "success": true,
        "main_path": {...},  // 主路径的CraftingNode序列化
        "alternative_paths": [...],  // 替代路径列表
        "marked_nodes": [...],  // 标记了替代路径的节点
        "total_devices": 123.45,  // 总设备数
        "raw_materials": {...},  // 基础原料消耗
        "device_stats": {...}  // 设备统计
    }
    """
    return calculate_api(include_alternatives=True)


@app.route("/api/calculate/switch-path", methods=["POST"])
@csrf.exempt
def switch_path():
    """
    切换到指定路径

    请求体:
    {
        "game_name": "配方文件名称",
        "current_path_id": 0,  // 当前路径ID
        "node_id": "节点物品名称",  // 要切换的节点
        "target_path_index": 1  // 目标路径在替代路径列表中的索引
    }

    返回:
    {
        "success": true,
        "new_main_path": {...},  // 新的主路径
        "alternative_paths": [...],  // 新的替代路径列表
        "switched_node": {
            "item_name": "...",
            "previous_path_id": 0,
            "new_path_id": 1
        }
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "请求体不能为空"}), 400

    game_name = data.get("game_name", "")
    node_id = data.get("node_id", "")
    target_path_index = data.get("target_path_index", -1)

    if not game_name:
        return jsonify({"success": False, "error": "game_name不能为空"}), 400
    if not node_id:
        return jsonify({"success": False, "error": "node_id不能为空"}), 400
    if target_path_index < 0:
        return (
            jsonify({"success": False, "error": "target_path_index必须大于等于0"}),
            400,
        )

    # 获取会话
    web_session = get_session()

    # 切换到指定游戏
    games = web_session.controller.recipe_manager.get_available_games()
    if game_name not in games:
        return (
            jsonify({"success": False, "error": f"配方文件 '{game_name}' 不存在"}),
            404,
        )

    web_session.controller.current_game = game_name
    web_session.controller.recipe_manager.load_recipe_file(game_name)
    from calculator import CraftingCalculator

    web_session.controller.calculator = CraftingCalculator(
        web_session.controller.recipe_manager
    )

    calculator = web_session.controller.calculator

    # 注意：由于HTTP是无状态的，我们需要重新计算来获取当前状态
    # 在实际应用中，应该使用session来存储计算状态
    return (
        jsonify(
            {
                "success": False,
                "error": "路径切换功能需要配合前端状态管理实现。请先调用 /api/calculate 获取完整路径信息，然后在前端进行路径切换操作。",
            }
        ),
        501,
    )


@app.route("/api/calculate/alternatives", methods=["GET"])
def get_alternatives():
    """
    获取节点的可选路径列表

    查询参数:
    - game_name: 配方文件名称（必需）
    - target_item: 目标物品名称（必需）
    - target_rate: 目标生产速度（必需）
    - node_item: 节点物品名称（必需）

    返回:
    {
        "success": true,
        "alternatives": [
            {
                "path_id": 1,
                "node_chain": [...],
                "device_count": 10.5,
                "efficiency_score": 0.85,
                "recipe_name": "..."
            }
        ]
    }
    """
    return get_alternatives_api()


@app.route("/api/paths/compare", methods=["GET"])
def compare_paths():
    """
    对比多条路径

    查询参数:
    - game_name: 配方文件名称（必需）
    - target_item: 目标物品名称（必需）
    - target_rate: 目标生产速度（必需）
    - path_indices: 要对比的路径索引（逗号分隔，如"0,1,2"）

    返回:
    {
        "success": true,
        "comparisons": [
            {
                "path_index": 0,
                "total_devices": 10.5,
                "total_inputs": 3,
                "efficiency_score": 0.85,
                "strengths": ["设备数量少", "..."],
                "weaknesses": ["原料种类多", "..."]
            }
        ]
    }
    """
    return compare_paths_api()


if __name__ == "__main__":
    print("启动 Web 测试服务器...")
    print("访问地址: http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=True)
