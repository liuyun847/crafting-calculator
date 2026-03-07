"""
自动化建造游戏通用合成计算器 - Web 测试接口

提供与终端程序完全一致的 Web 交互界面，支持浏览器自动化测试。
"""

import os
import sys
from typing import Dict, Any
from flask import Flask, render_template, request, jsonify, session

app = Flask(__name__)
app.secret_key = os.urandom(24)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from io_interface import WebIO
from application_controller import ApplicationController


class WebSession:
    """Web会话状态管理"""

    def __init__(self):
        self.io = WebIO()
        self.controller = ApplicationController(self.io)

    def process_command(self, command: str) -> Dict[str, Any]:
        """
        处理命令并返回响应

        Args:
            command: 用户输入的命令

        Returns:
            包含output和prompt的字典
        """
        self.io.clear()
        self.io.set_input(command)
        result = self.controller.process_command(command)
        return {"output": self.io.get_output(), "prompt": result["prompt"]}

    def reset(self):
        """重置会话状态"""
        self.io = WebIO()
        self.controller = ApplicationController(self.io)

    def get_state(self) -> Dict[str, Any]:
        """
        获取会话状态（用于序列化）

        Returns:
            会话状态字典
        """
        return {
            "current_game": self.controller.current_game,
            "state": self.controller.state,
            "pending_data": self._serialize_pending_data(),
        }

    def set_state(self, state: Dict[str, Any]) -> None:
        """
        设置会话状态（用于反序列化）

        Args:
            state: 会话状态字典
        """
        self.controller.current_game = state.get("current_game")
        self.controller.state = state.get("state", "main_menu")
        self.controller.pending_data = self._deserialize_pending_data(
            state.get("pending_data", {})
        )

        if self.controller.current_game:
            try:
                self.controller.recipe_manager.load_recipe_file(
                    self.controller.current_game
                )
                from calculator import CraftingCalculator

                self.controller.calculator = CraftingCalculator(
                    self.controller.recipe_manager
                )
            except Exception:
                self.controller.current_game = None
                self.controller.calculator = None

    def _serialize_pending_data(self) -> Dict[str, Any]:
        """
        序列化pending_data（处理set类型）

        Returns:
            序列化后的pending_data
        """
        pending_data = self.controller.pending_data.copy()
        if "existing_items" in pending_data and isinstance(
            pending_data["existing_items"], set
        ):
            pending_data["existing_items"] = list(pending_data["existing_items"])
        return pending_data

    def _deserialize_pending_data(self, pending_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        反序列化pending_data（处理set类型）

        Args:
            pending_data: 待反序列化的pending_data

        Returns:
            反序列化后的pending_data
        """
        if "existing_items" in pending_data and isinstance(
            pending_data["existing_items"], list
        ):
            pending_data["existing_items"] = set(pending_data["existing_items"])
        return pending_data


def get_session() -> WebSession:
    """
    获取或创建会话

    Returns:
        WebSession实例
    """
    # 使用全局字典存储WebSession对象，避免Flask session序列化问题
    if not hasattr(get_session, "_sessions"):
        get_session._sessions = {}

    session_id = session.get("session_id")
    if not session_id or session_id not in get_session._sessions:
        # 创建新会话
        import uuid

        session_id = str(uuid.uuid4())
        session["session_id"] = session_id
        get_session._sessions[session_id] = WebSession()

    web_session = get_session._sessions[session_id]

    # 恢复状态
    if "state" in session:
        try:
            web_session.set_state(session["state"])
        except Exception:
            # 如果恢复失败，创建新会话
            get_session._sessions[session_id] = WebSession()
            web_session = get_session._sessions[session_id]

    return web_session


def save_session(web_session: WebSession):
    """
    保存会话状态

    Args:
        web_session: WebSession实例
    """
    session["state"] = web_session.get_state()


@app.route("/")
def index():
    """渲染前端页面"""
    return render_template("index.html")


@app.route("/api/terminal", methods=["POST"])
def terminal():
    """处理终端命令"""
    data = request.get_json()
    command = data.get("command", "")

    web_session = get_session()
    result = web_session.process_command(command)
    save_session(web_session)

    return jsonify(
        {"success": True, "output": result["output"], "prompt": result["prompt"]}
    )


@app.route("/api/reset", methods=["POST"])
def reset():
    """重置会话"""
    web_session = get_session()
    web_session.reset()
    save_session(web_session)
    return jsonify({"success": True, "message": "会话已重置"})


@app.route("/api/games", methods=["GET"])
def get_games():
    """获取配方文件列表"""
    web_session = get_session()
    games = web_session.controller.recipe_manager.get_available_games()
    return jsonify({"success": True, "games": games})


@app.route("/api/select-game", methods=["POST"])
def select_game():
    """选择配方文件"""
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
    web_session = get_session()
    if not web_session.controller.calculator:
        return jsonify({"success": False, "error": "请先选择配方文件"})

    recipes = web_session.controller.recipe_manager.get_all_recipes()
    items = set()
    for recipe in recipes.values():
        items.update(recipe.get("inputs", {}).keys())
        items.update(recipe.get("outputs", {}).keys())

    return jsonify({"success": True, "items": sorted(list(items))})





@app.route("/api/recipes", methods=["GET"])
def get_recipes():
    """
    获取配方列表

    支持查询参数:
    - page: 页码 (默认 1)
    - per_page: 每页数量 (默认 20, 最大 100)
    - search: 搜索关键词 (搜索配方名称、设备名称、物品名称)
    """
    web_session = get_session()
    recipe_manager = web_session.controller.recipe_manager

    # 解析分页参数
    try:
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 20))
    except ValueError:
        return jsonify({"success": False, "error": "分页参数必须是整数"}), 400

    if page < 1:
        return jsonify({"success": False, "error": "页码必须大于0"}), 400
    if per_page < 1 or per_page > 100:
        return jsonify({"success": False, "error": "每页数量必须在1-100之间"}), 400

    # 获取所有配方
    all_recipes = recipe_manager.get_all_recipes()

    # 搜索过滤
    search = request.args.get("search", "").strip().lower()
    if search:
        filtered_recipes = {}
        for name, recipe in all_recipes.items():
            # 搜索配方名称
            if search in name.lower():
                filtered_recipes[name] = recipe
                continue
            # 搜索设备名称
            if search in recipe.get("device", "").lower():
                filtered_recipes[name] = recipe
                continue
            # 搜索物品名称
            inputs = recipe.get("inputs", {})
            outputs = recipe.get("outputs", {})
            for item_name in list(inputs.keys()) + list(outputs.keys()):
                if search in item_name.lower():
                    filtered_recipes[name] = recipe
                    break
        all_recipes = filtered_recipes

    # 计算分页
    total = len(all_recipes)
    total_pages = (total + per_page - 1) // per_page

    # 确保页码不超过最大页数
    if total > 0 and page > total_pages:
        page = total_pages

    # 获取当前页的数据
    start = (page - 1) * per_page
    end = start + per_page
    recipe_items = list(all_recipes.items())[start:end]

    # 构建返回的配方列表
    recipes = []
    for name, recipe in recipe_items:
        recipes.append(
            {
                "name": name,
                "device": recipe.get("device", ""),
                "inputs": recipe.get("inputs", {}),
                "outputs": recipe.get("outputs", {}),
            }
        )

    return jsonify(
        {
            "success": True,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "recipes": recipes,
        }
    )


@app.route("/api/recipes/<recipe_name>", methods=["GET"])
def get_recipe(recipe_name):
    """
    获取单个配方详情

    Args:
        recipe_name: 配方名称（URL编码）
    """
    from urllib.parse import unquote

    web_session = get_session()
    recipe_manager = web_session.controller.recipe_manager

    # 解码URL编码的配方名称
    decoded_name = unquote(recipe_name)

    try:
        recipe = recipe_manager.get_recipe(decoded_name)
        return jsonify(
            {
                "success": True,
                "name": decoded_name,
                "device": recipe.get("device", ""),
                "inputs": recipe.get("inputs", {}),
                "outputs": recipe.get("outputs", {}),
            }
        )
    except KeyError:
        return (
            jsonify({"success": False, "error": f"配方 '{decoded_name}' 不存在"}),
            404,
        )


@app.route("/api/recipes", methods=["POST"])
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
    web_session = get_session()
    recipe_manager = web_session.controller.recipe_manager

    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "请求体不能为空"}), 400

    # 验证必填字段
    required_fields = ["name", "device", "inputs", "outputs"]
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return (
            jsonify(
                {
                    "success": False,
                    "error": f"缺少必填字段: {', '.join(missing_fields)}",
                }
            ),
            400,
        )

    recipe_name = data["name"]
    device_name = data["device"]
    inputs = data["inputs"]
    outputs = data["outputs"]

    # 验证inputs和outputs格式
    if not isinstance(inputs, dict):
        return jsonify({"success": False, "error": "inputs必须是对象"}), 400
    if not isinstance(outputs, dict):
        return jsonify({"success": False, "error": "outputs必须是对象"}), 400

    # 验证每个物品的格式
    for item_type, items in [("inputs", inputs), ("outputs", outputs)]:
        for item_name, item_data in items.items():
            if not isinstance(item_data, dict):
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": f"{item_type}中的'{item_name}'格式错误",
                        }
                    ),
                    400,
                )
            if "amount" not in item_data:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": f"{item_type}中的'{item_name}'缺少amount字段",
                        }
                    ),
                    400,
                )
            try:
                float(item_data["amount"])
            except (ValueError, TypeError):
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": f"{item_type}中的'{item_name}'的amount必须是数字",
                        }
                    ),
                    400,
                )
            # 如果没有expression，使用amount作为默认值
            if "expression" not in item_data:
                item_data["expression"] = str(item_data["amount"])

    # 检查配方是否已存在
    if recipe_name in recipe_manager.get_all_recipes():
        return jsonify({"success": False, "error": f"配方 '{recipe_name}' 已存在"}), 409

    # 添加配方
    try:
        recipe_manager.add_recipe(recipe_name, device_name, inputs, outputs)
        return (
            jsonify(
                {
                    "success": True,
                    "message": f"配方 '{recipe_name}' 创建成功",
                    "recipe": {
                        "name": recipe_name,
                        "device": device_name,
                        "inputs": inputs,
                        "outputs": outputs,
                    },
                }
            ),
            201,
        )
    except Exception as e:
        return jsonify({"success": False, "error": f"创建配方失败: {str(e)}"}), 500


@app.route("/api/recipes/<recipe_name>", methods=["PUT"])
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
    from urllib.parse import unquote

    web_session = get_session()
    recipe_manager = web_session.controller.recipe_manager

    # 解码URL编码的配方名称
    decoded_name = unquote(recipe_name)

    # 检查配方是否存在
    if decoded_name not in recipe_manager.get_all_recipes():
        return (
            jsonify({"success": False, "error": f"配方 '{decoded_name}' 不存在"}),
            404,
        )

    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "请求体不能为空"}), 400

    # 获取现有配方数据
    existing_recipe = recipe_manager.get_recipe(decoded_name)

    # 准备更新后的数据
    device_name = data.get("device", existing_recipe.get("device", ""))
    inputs = data.get("inputs", existing_recipe.get("inputs", {}))
    outputs = data.get("outputs", existing_recipe.get("outputs", {}))

    # 验证inputs和outputs格式
    if "inputs" in data:
        if not isinstance(inputs, dict):
            return jsonify({"success": False, "error": "inputs必须是对象"}), 400
        # 验证每个物品的格式
        for item_name, item_data in inputs.items():
            if not isinstance(item_data, dict):
                return (
                    jsonify(
                        {"success": False, "error": f"inputs中的'{item_name}'格式错误"}
                    ),
                    400,
                )
            if "amount" not in item_data:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": f"inputs中的'{item_name}'缺少amount字段",
                        }
                    ),
                    400,
                )
            try:
                float(item_data["amount"])
            except (ValueError, TypeError):
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": f"inputs中的'{item_name}'的amount必须是数字",
                        }
                    ),
                    400,
                )
            if "expression" not in item_data:
                item_data["expression"] = str(item_data["amount"])

    if "outputs" in data:
        if not isinstance(outputs, dict):
            return jsonify({"success": False, "error": "outputs必须是对象"}), 400
        # 验证每个物品的格式
        for item_name, item_data in outputs.items():
            if not isinstance(item_data, dict):
                return (
                    jsonify(
                        {"success": False, "error": f"outputs中的'{item_name}'格式错误"}
                    ),
                    400,
                )
            if "amount" not in item_data:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": f"outputs中的'{item_name}'缺少amount字段",
                        }
                    ),
                    400,
                )
            try:
                float(item_data["amount"])
            except (ValueError, TypeError):
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": f"outputs中的'{item_name}'的amount必须是数字",
                        }
                    ),
                    400,
                )
            if "expression" not in item_data:
                item_data["expression"] = str(item_data["amount"])

    # 更新配方
    try:
        recipe_manager.update_recipe(decoded_name, device_name, inputs, outputs)
        return jsonify(
            {
                "success": True,
                "message": f"配方 '{decoded_name}' 更新成功",
                "recipe": {
                    "name": decoded_name,
                    "device": device_name,
                    "inputs": inputs,
                    "outputs": outputs,
                },
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": f"更新配方失败: {str(e)}"}), 500


@app.route("/api/recipes/<recipe_name>", methods=["DELETE"])
def delete_recipe(recipe_name):
    """
    删除配方

    Args:
        recipe_name: 配方名称（URL编码）
    """
    from urllib.parse import unquote

    web_session = get_session()
    recipe_manager = web_session.controller.recipe_manager

    # 解码URL编码的配方名称
    decoded_name = unquote(recipe_name)

    # 检查配方是否存在
    if decoded_name not in recipe_manager.get_all_recipes():
        return (
            jsonify({"success": False, "error": f"配方 '{decoded_name}' 不存在"}),
            404,
        )

    # 删除配方
    try:
        recipe_manager.delete_recipe(decoded_name)
        return jsonify({"success": True, "message": f"配方 '{decoded_name}' 删除成功"})
    except Exception as e:
        return jsonify({"success": False, "error": f"删除配方失败: {str(e)}"}), 500


# ============================================================
# 路径对比相关API端点
# ============================================================


@app.route("/api/calculate", methods=["POST"])
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
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "请求体不能为空"}), 400

    # 获取参数
    target_item = data.get("target_item", "")
    target_rate = data.get("target_rate", 0)
    game_name = data.get("game_name", "")
    options = data.get("options", {})

    # 验证必填参数
    if not target_item:
        return jsonify({"success": False, "error": "target_item不能为空"}), 400
    if not target_rate:
        return jsonify({"success": False, "error": "target_rate不能为空"}), 400

    # 获取会话
    web_session = get_session()

    # 如果指定了game_name，先切换到该游戏
    if game_name:
        games = web_session.controller.recipe_manager.get_available_games()
        if game_name in games:
            web_session.controller.current_game = game_name
            web_session.controller.recipe_manager.load_recipe_file(game_name)
            from calculator import CraftingCalculator

            web_session.controller.calculator = CraftingCalculator(
                web_session.controller.recipe_manager
            )
        else:
            return (
                jsonify({"success": False, "error": f"配方文件 '{game_name}' 不存在"}),
                404,
            )

    # 检查计算器是否可用
    if not web_session.controller.calculator:
        return jsonify({"success": False, "error": "请先选择配方文件"}), 400

    # 解析目标生产速度
    from expression_parser import parse_expression

    try:
        target_rate_value = parse_expression(str(target_rate))
    except Exception as e:
        return (
            jsonify({"success": False, "error": f"无法解析目标生产速度: {str(e)}"}),
            400,
        )

    try:
        calculator = web_session.controller.calculator

        # 查找所有生产路径
        production_paths = calculator.find_production_paths(target_item)

        # 使用路径对比引擎选择主路径
        main_path_recipes = calculator.path_engine.find_main_path(production_paths)

        # 构建主路径合成树
        main_tree = calculator.build_crafting_tree(
            target_item, target_rate_value, main_path_recipes or []
        )

        if not main_tree:
            return jsonify({"success": False, "error": "无法构建合成树"}), 500

        # 查找所有完整路径的节点列表（用于替代路径识别）
        all_node_paths = []
        for path_recipes in production_paths:
            try:
                temp_tree = calculator.build_crafting_tree(
                    target_item, target_rate_value, path_recipes
                )
                if temp_tree:
                    node_path = calculator._flatten_tree_to_path(temp_tree)
                    all_node_paths.append(node_path)
            except Exception:
                continue

        # 在主路径上查找替代路径
        alternative_paths = []
        marked_nodes = []

        if options.get("compare_paths", True):

            def find_alternatives(node):
                # 查找当前节点的替代路径
                alts = calculator.path_engine.find_alternative_paths_at_node(
                    node, all_node_paths, node.path_id
                )
                if alts:
                    node.alternative_paths = alts
                    marked_nodes.append(
                        {
                            "item_name": node.item_name,
                            "amount": node.amount,
                            "alternative_count": len(alts),
                        }
                    )

                # 递归处理子节点
                for child in node.children:
                    find_alternatives(child)

            find_alternatives(main_tree)

            # 收集替代路径（序列化）
            def collect_alternatives(node):
                for alt_path in node.alternative_paths:
                    serialized = [
                        {
                            "item_name": n.item_name,
                            "amount": n.amount,
                            "device_count": n.device_count,
                            "recipe": n.recipe,
                        }
                        for n in alt_path
                    ]
                    if serialized not in alternative_paths:
                        alternative_paths.append(serialized)
                for child in node.children:
                    collect_alternatives(child)

            collect_alternatives(main_tree)

        # 计算统计数据
        total_devices = calculator._count_total_devices(main_tree.to_dict())
        raw_materials = calculator.get_raw_materials(main_tree)
        device_stats = calculator.get_device_stats(main_tree)

        # 准备返回结果
        result = {
            "success": True,
            "main_path": main_tree.to_dict(),
            "alternative_paths": (
                alternative_paths
                if not options.get("show_main_path_only", False)
                else []
            ),
            "marked_nodes": (
                marked_nodes if options.get("mark_alternatives", True) else []
            ),
            "total_devices": total_devices,
            "raw_materials": raw_materials,
            "device_stats": device_stats,
            "target_item": target_item,
            "target_rate": target_rate_value,
        }

        return jsonify(result)

    except Exception as e:
        return jsonify({"success": False, "error": f"计算失败: {str(e)}"}), 500


@app.route("/api/calculate/switch-path", methods=["POST"])
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
    # 获取查询参数
    game_name = request.args.get("game_name", "")
    target_item = request.args.get("target_item", "")
    target_rate = request.args.get("target_rate", "")
    node_item = request.args.get("node_item", "")

    # 验证参数
    if not game_name:
        return jsonify({"success": False, "error": "game_name参数不能为空"}), 400
    if not target_item:
        return jsonify({"success": False, "error": "target_item参数不能为空"}), 400
    if not target_rate:
        return jsonify({"success": False, "error": "target_rate参数不能为空"}), 400
    if not node_item:
        return jsonify({"success": False, "error": "node_item参数不能为空"}), 400

    # 解析目标生产速度
    from expression_parser import parse_expression

    try:
        target_rate_value = parse_expression(str(target_rate))
    except Exception as e:
        return (
            jsonify({"success": False, "error": f"无法解析target_rate: {str(e)}"}),
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

    try:
        # 查找所有生产路径
        production_paths = calculator.find_production_paths(target_item)

        # 查找目标节点所在的替代路径
        alternatives = []
        path_id_counter = 1

        for path_recipes in production_paths:
            # 为每条路径构建临时树
            try:
                temp_tree = calculator.build_crafting_tree(
                    target_item, target_rate_value, path_recipes
                )
                if not temp_tree:
                    continue

                # 检查该路径是否包含目标节点
                def find_node(node):
                    if node.item_name == node_item:
                        return node
                    for child in node.children:
                        result = find_node(child)
                        if result:
                            return result
                    return None

                target_node = find_node(temp_tree)
                if not target_node:
                    continue

                # 计算该路径的设备数
                def count_devices(node):
                    total = node.device_count
                    for child in node.children:
                        total += count_devices(child)
                    return total

                device_count = count_devices(temp_tree)

                # 获取配方名称
                recipe_name = ""
                if target_node.recipe:
                    # 从配方管理器查找配方名称
                    recipes = calculator.recipe_manager.get_all_recipes()
                    for name, recipe in recipes.items():
                        if recipe == target_node.recipe:
                            recipe_name = name
                            break

                # 计算效率分数（基于设备数的倒数，归一化到0-1）
                efficiency_score = min(1.0, max(0.0, 1.0 / (1.0 + device_count * 0.1)))

                # 构建节点链
                node_chain = []
                current = target_node
                while current:
                    node_chain.append(
                        {
                            "item_name": current.item_name,
                            "amount": current.amount,
                            "device_count": current.device_count,
                            "recipe_name": (
                                recipe_name if current == target_node else ""
                            ),
                        }
                    )
                    if current.children:
                        current = current.children[0]
                    else:
                        break

                alternatives.append(
                    {
                        "path_id": path_id_counter,
                        "node_chain": node_chain,
                        "device_count": device_count,
                        "efficiency_score": efficiency_score,
                        "recipe_name": recipe_name,
                    }
                )

                path_id_counter += 1

            except Exception as e:
                # 跳过构建失败的路径
                continue

        # 按设备数排序
        alternatives.sort(key=lambda x: x["device_count"])

        # 重新分配path_id
        for i, alt in enumerate(alternatives):
            alt["path_id"] = i + 1

        return jsonify(
            {
                "success": True,
                "node_item": node_item,
                "target_item": target_item,
                "target_rate": target_rate_value,
                "alternatives_count": len(alternatives),
                "alternatives": alternatives,
            }
        )

    except Exception as e:
        return jsonify({"success": False, "error": f"获取替代路径失败: {str(e)}"}), 500


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
    # 获取查询参数
    game_name = request.args.get("game_name", "")
    target_item = request.args.get("target_item", "")
    target_rate = request.args.get("target_rate", "")
    path_indices_str = request.args.get("path_indices", "")

    # 验证参数
    if not game_name:
        return jsonify({"success": False, "error": "game_name参数不能为空"}), 400
    if not target_item:
        return jsonify({"success": False, "error": "target_item参数不能为空"}), 400
    if not target_rate:
        return jsonify({"success": False, "error": "target_rate参数不能为空"}), 400

    # 解析path_indices
    try:
        path_indices = [
            int(x.strip()) for x in path_indices_str.split(",") if x.strip()
        ]
        if not path_indices:
            path_indices = [0, 1, 2]  # 默认对比前3条路径
    except ValueError:
        path_indices = [0, 1, 2]

    # 解析目标生产速度
    from expression_parser import parse_expression

    try:
        target_rate_value = parse_expression(str(target_rate))
    except Exception as e:
        return (
            jsonify({"success": False, "error": f"无法解析target_rate: {str(e)}"}),
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

    try:
        # 查找所有生产路径
        production_paths = calculator.find_production_paths(target_item)

        if not production_paths:
            return jsonify({"success": False, "error": "未找到生产路径"}), 404

        # 过滤有效的path_indices
        valid_indices = [i for i in path_indices if 0 <= i < len(production_paths)]
        if not valid_indices:
            valid_indices = [0]

        # 对比每条路径
        comparisons = []

        for idx in valid_indices:
            path_recipes = production_paths[idx]

            # 构建合成树
            tree = calculator.build_crafting_tree(
                target_item, target_rate_value, path_recipes
            )
            if not tree:
                continue

            tree_dict = tree.to_dict()

            # 计算统计信息
            total_devices = calculator._count_total_devices(tree_dict)
            raw_materials = calculator.get_raw_materials(tree)
            device_stats = calculator.get_device_stats(tree)

            # 计算效率分数（基于设备数的倒数）
            efficiency_score = min(1.0, max(0.0, 1.0 / (1.0 + total_devices * 0.1)))

            # 分析优缺点
            strengths = []
            weaknesses = []

            # 设备数量评价
            if total_devices < 5:
                strengths.append("设备数量很少")
            elif total_devices < 10:
                strengths.append("设备数量较少")
            elif total_devices > 30:
                weaknesses.append("设备数量较多")

            # 基础原料评价
            if len(raw_materials) <= 2:
                strengths.append("原料种类简单")
            elif len(raw_materials) >= 5:
                weaknesses.append("原料种类复杂")

            # 设备种类评价
            if len(device_stats) <= 2:
                strengths.append("设备种类简单")
            elif len(device_stats) >= 4:
                weaknesses.append("设备种类较多")

            comparisons.append(
                {
                    "path_index": idx,
                    "total_devices": total_devices,
                    "total_inputs": len(raw_materials),
                    "device_type_count": len(device_stats),
                    "efficiency_score": efficiency_score,
                    "raw_materials": raw_materials,
                    "device_stats": device_stats,
                    "strengths": strengths,
                    "weaknesses": weaknesses,
                }
            )

        # 按效率分数排序
        comparisons.sort(key=lambda x: x["efficiency_score"], reverse=True)

        return jsonify(
            {
                "success": True,
                "target_item": target_item,
                "target_rate": target_rate_value,
                "comparisons_count": len(comparisons),
                "comparisons": comparisons,
            }
        )

    except Exception as e:
        return jsonify({"success": False, "error": f"路径对比失败: {str(e)}"}), 500


if __name__ == "__main__":
    print("启动 Web 测试服务器...")
    print("访问地址: http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=True)
