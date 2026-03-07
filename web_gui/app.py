"""
自动化建造游戏通用合成计算器 - Web GUI 应用

提供现代化的图形界面Web应用，支持：
- 配方文件选择
- 生产链计算与可视化
- 配方管理（CRUD）
- 路径切换
"""

import os
import sys
from typing import Dict, Any, Optional
from flask import Flask, render_template, request, jsonify, session

# 设置项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from io_interface import WebIO
from application_controller import ApplicationController
from data_manager import RecipeManager
from calculator import CraftingCalculator
from config_manager import config_manager

app = Flask(__name__, 
    template_folder='templates',
    static_folder='static'
)
app.secret_key = os.urandom(24)

# ========================================
# 会话管理
# ========================================

class WebSession:
    """Web会话状态管理"""

    def __init__(self):
        self.io = WebIO()
        self.controller = ApplicationController(self.io)
        self._load_last_game()

    def _load_last_game(self):
        """加载上次选择的游戏"""
        last_game = config_manager.get_last_game()
        if last_game:
            available_games = self.controller.recipe_manager.get_available_games()
            if last_game in available_games:
                try:
                    self.controller.recipe_manager.load_recipe_file(last_game)
                    self.controller.current_game = last_game
                    self.controller.calculator = CraftingCalculator(
                        self.controller.recipe_manager
                    )
                except Exception:
                    pass

    def get_state(self) -> Dict[str, Any]:
        """获取会话状态"""
        return {
            "current_game": self.controller.current_game,
            "state": self.controller.state,
        }

    def set_state(self, state: Dict[str, Any]) -> None:
        """设置会话状态"""
        if state.get("current_game"):
            self.controller.current_game = state["current_game"]
            try:
                self.controller.recipe_manager.load_recipe_file(
                    state["current_game"]
                )
                self.controller.calculator = CraftingCalculator(
                    self.controller.recipe_manager
                )
            except Exception:
                self.controller.current_game = None
                self.controller.calculator = None


def get_session() -> WebSession:
    """获取或创建会话"""
    if not hasattr(get_session, "_sessions"):
        get_session._sessions = {}

    session_id = session.get("session_id")
    if not session_id or session_id not in get_session._sessions:
        import uuid
        session_id = str(uuid.uuid4())
        session["session_id"] = session_id
        get_session._sessions[session_id] = WebSession()

    return get_session._sessions[session_id]


def get_current_game() -> Optional[str]:
    """获取当前游戏名称"""
    web_session = get_session()
    return web_session.controller.current_game


# ========================================
# 页面路由
# ========================================

@app.route("/")
def index():
    """首页仪表盘"""
    web_session = get_session()
    controller = web_session.controller

    # 获取统计信息
    stats = {
        "current_game": controller.current_game,
        "recipe_count": 0,
        "item_count": 0,
    }

    if controller.calculator:
        recipes = controller.recipe_manager.get_all_recipes()
        stats["recipe_count"] = len(recipes)

        # 统计物品数量
        items = set()
        for recipe in recipes.values():
            items.update(recipe.get("inputs", {}).keys())
            items.update(recipe.get("outputs", {}).keys())
        stats["item_count"] = len(items)

    # 获取可用游戏列表
    available_games = controller.recipe_manager.get_available_games()

    return render_template("dashboard.html",
        current_game=controller.current_game,
        stats=stats,
        available_games=available_games
    )


@app.route("/select-game")
def select_game():
    """配方选择页面"""
    web_session = get_session()
    controller = web_session.controller
    games = controller.recipe_manager.get_available_games()

    return render_template("select_game.html",
        current_game=controller.current_game,
        games=games
    )


@app.route("/calculate")
def calculate_page():
    """生产链计算页面"""
    web_session = get_session()
    controller = web_session.controller

    # 获取物品列表用于自动补全
    items = []
    if controller.calculator:
        recipes = controller.recipe_manager.get_all_recipes()
        item_set = set()
        for recipe in recipes.values():
            item_set.update(recipe.get("inputs", {}).keys())
            item_set.update(recipe.get("outputs", {}).keys())
        items = sorted(list(item_set))

    return render_template("calculate.html",
        current_game=controller.current_game,
        items=items
    )


@app.route("/recipe-management")
def recipe_management_page():
    """配方管理页面"""
    web_session = get_session()
    controller = web_session.controller

    return render_template("recipe_management.html",
        current_game=controller.current_game
    )


# ========================================
# API路由 - 配方文件
# ========================================

@app.route("/api/games", methods=["GET"])
def get_games():
    """获取配方文件列表"""
    web_session = get_session()
    games = web_session.controller.recipe_manager.get_available_games()
    return jsonify({"success": True, "games": games})


@app.route("/api/select-game", methods=["POST"])
def api_select_game():
    """选择配方文件"""
    data = request.get_json()
    game_name = data.get("game", "")

    web_session = get_session()
    controller = web_session.controller
    games = controller.recipe_manager.get_available_games()

    if game_name not in games:
        return jsonify({"success": False, "error": "配方文件不存在"}), 404

    try:
        controller.recipe_manager.load_recipe_file(game_name)
        controller.current_game = game_name
        controller.calculator = CraftingCalculator(controller.recipe_manager)
        config_manager.set_last_game(game_name)

        return jsonify({
            "success": True,
            "message": f"已切换到配方文件: {game_name}",
            "game": game_name
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ========================================
# API路由 - 物品
# ========================================

@app.route("/api/items", methods=["GET"])
def get_items():
    """获取物品列表"""
    web_session = get_session()
    controller = web_session.controller

    if not controller.calculator:
        return jsonify({"success": False, "error": "请先选择配方文件"}), 400

    recipes = controller.recipe_manager.get_all_recipes()
    items = set()
    for recipe in recipes.values():
        items.update(recipe.get("inputs", {}).keys())
        items.update(recipe.get("outputs", {}).keys())

    return jsonify({"success": True, "items": sorted(list(items))})


# ========================================
# API路由 - 配方管理
# ========================================

@app.route("/api/recipes", methods=["GET"])
def get_recipes():
    """获取配方列表"""
    web_session = get_session()
    controller = web_session.controller

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

    all_recipes = controller.recipe_manager.get_all_recipes()

    # 搜索过滤
    search = request.args.get("search", "").strip().lower()
    if search:
        filtered_recipes = {}
        for name, recipe in all_recipes.items():
            if search in name.lower():
                filtered_recipes[name] = recipe
                continue
            if search in recipe.get("device", "").lower():
                filtered_recipes[name] = recipe
                continue
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
    if total > 0 and page > total_pages:
        page = total_pages

    start = (page - 1) * per_page
    end = start + per_page
    recipe_items = list(all_recipes.items())[start:end]

    recipes = []
    for name, recipe in recipe_items:
        recipes.append({
            "name": name,
            "device": recipe.get("device", ""),
            "inputs": recipe.get("inputs", {}),
            "outputs": recipe.get("outputs", {}),
        })

    return jsonify({
        "success": True,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
        "recipes": recipes,
    })


@app.route("/api/recipes/<recipe_name>", methods=["GET"])
def get_recipe(recipe_name):
    """获取单个配方详情"""
    from urllib.parse import unquote
    web_session = get_session()
    controller = web_session.controller

    decoded_name = unquote(recipe_name)

    try:
        recipe = controller.recipe_manager.get_recipe(decoded_name)
        return jsonify({
            "success": True,
            "name": decoded_name,
            "device": recipe.get("device", ""),
            "inputs": recipe.get("inputs", {}),
            "outputs": recipe.get("outputs", {}),
        })
    except KeyError:
        return jsonify({"success": False, "error": f"配方 '{decoded_name}' 不存在"}), 404


@app.route("/api/recipes", methods=["POST"])
def create_recipe():
    """创建新配方"""
    web_session = get_session()
    controller = web_session.controller

    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "请求体不能为空"}), 400

    required_fields = ["name", "device", "inputs", "outputs"]
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return jsonify({
            "success": False,
            "error": f"缺少必填字段: {', '.join(missing_fields)}"
        }), 400

    recipe_name = data["name"]
    device_name = data["device"]
    inputs = data["inputs"]
    outputs = data["outputs"]

    # 验证格式
    if not isinstance(inputs, dict):
        return jsonify({"success": False, "error": "inputs必须是对象"}), 400
    if not isinstance(outputs, dict):
        return jsonify({"success": False, "error": "outputs必须是对象"}), 400

    # 检查配方是否已存在
    if recipe_name in controller.recipe_manager.get_all_recipes():
        return jsonify({"success": False, "error": f"配方 '{recipe_name}' 已存在"}), 409

    try:
        controller.recipe_manager.add_recipe(recipe_name, device_name, inputs, outputs)
        return jsonify({
            "success": True,
            "message": f"配方 '{recipe_name}' 创建成功",
            "recipe": {
                "name": recipe_name,
                "device": device_name,
                "inputs": inputs,
                "outputs": outputs,
            },
        }), 201
    except Exception as e:
        return jsonify({"success": False, "error": f"创建配方失败: {str(e)}"}), 500


@app.route("/api/recipes/<recipe_name>", methods=["PUT"])
def update_recipe(recipe_name):
    """更新配方"""
    from urllib.parse import unquote
    web_session = get_session()
    controller = web_session.controller

    decoded_name = unquote(recipe_name)

    if decoded_name not in controller.recipe_manager.get_all_recipes():
        return jsonify({"success": False, "error": f"配方 '{decoded_name}' 不存在"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "请求体不能为空"}), 400

    existing_recipe = controller.recipe_manager.get_recipe(decoded_name)

    device_name = data.get("device", existing_recipe.get("device", ""))
    inputs = data.get("inputs", existing_recipe.get("inputs", {}))
    outputs = data.get("outputs", existing_recipe.get("outputs", {}))

    try:
        controller.recipe_manager.update_recipe(decoded_name, device_name, inputs, outputs)
        return jsonify({
            "success": True,
            "message": f"配方 '{decoded_name}' 更新成功",
            "recipe": {
                "name": decoded_name,
                "device": device_name,
                "inputs": inputs,
                "outputs": outputs,
            },
        })
    except Exception as e:
        return jsonify({"success": False, "error": f"更新配方失败: {str(e)}"}), 500


@app.route("/api/recipes/<recipe_name>", methods=["DELETE"])
def delete_recipe(recipe_name):
    """删除配方"""
    from urllib.parse import unquote
    web_session = get_session()
    controller = web_session.controller

    decoded_name = unquote(recipe_name)

    if decoded_name not in controller.recipe_manager.get_all_recipes():
        return jsonify({"success": False, "error": f"配方 '{decoded_name}' 不存在"}), 404

    try:
        controller.recipe_manager.delete_recipe(decoded_name)
        return jsonify({
            "success": True,
            "message": f"配方 '{decoded_name}' 删除成功"
        })
    except Exception as e:
        return jsonify({"success": False, "error": f"删除配方失败: {str(e)}"}), 500


# ========================================
# API路由 - 生产链计算
# ========================================

@app.route("/api/calculate", methods=["POST"])
def calculate():
    """计算生产链"""
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "请求体不能为空"}), 400

    target_item = data.get("target_item", "")
    target_rate = data.get("target_rate", "")

    if not target_item:
        return jsonify({"success": False, "error": "target_item不能为空"}), 400
    if not target_rate:
        return jsonify({"success": False, "error": "target_rate不能为空"}), 400

    web_session = get_session()
    controller = web_session.controller

    if not controller.calculator:
        return jsonify({"success": False, "error": "请先选择配方文件"}), 400

    # 解析目标生产速度
    from expression_parser import parse_expression
    try:
        target_rate_value = parse_expression(str(target_rate))
    except Exception as e:
        return jsonify({"success": False, "error": f"无法解析目标生产速度: {str(e)}"}), 400

    try:
        calculator = controller.calculator

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

        # 查找所有完整路径的节点列表
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
        marked_nodes = []

        def find_alternatives(node):
            alts = calculator.path_engine.find_alternative_paths_at_node(
                node, all_node_paths, node.path_id
            )
            if alts:
                node.alternative_paths = alts
                marked_nodes.append({
                    "item_name": node.item_name,
                    "amount": node.amount,
                    "alternative_count": len(alts),
                })

            for child in node.children:
                find_alternatives(child)

        find_alternatives(main_tree)

        # 计算统计数据
        total_devices = calculator._count_total_devices(main_tree.to_dict())
        raw_materials = calculator.get_raw_materials(main_tree)
        device_stats = calculator.get_device_stats(main_tree)

        return jsonify({
            "success": True,
            "main_path": main_tree.to_dict(),
            "marked_nodes": marked_nodes,
            "total_devices": total_devices,
            "raw_materials": raw_materials,
            "device_stats": device_stats,
            "target_item": target_item,
            "target_rate": target_rate_value,
        })

    except Exception as e:
        return jsonify({"success": False, "error": f"计算失败: {str(e)}"}), 500


@app.route("/api/calculate/alternatives", methods=["GET"])
def get_alternatives():
    """获取节点的可选路径列表"""
    game_name = request.args.get("game_name", "")
    target_item = request.args.get("target_item", "")
    target_rate = request.args.get("target_rate", "")
    node_item = request.args.get("node_item", "")

    if not game_name:
        return jsonify({"success": False, "error": "game_name参数不能为空"}), 400
    if not target_item:
        return jsonify({"success": False, "error": "target_item参数不能为空"}), 400
    if not target_rate:
        return jsonify({"success": False, "error": "target_rate参数不能为空"}), 400
    if not node_item:
        return jsonify({"success": False, "error": "node_item参数不能为空"}), 400

    from expression_parser import parse_expression
    try:
        target_rate_value = parse_expression(str(target_rate))
    except Exception as e:
        return jsonify({"success": False, "error": f"无法解析target_rate: {str(e)}"}), 400

    web_session = get_session()
    controller = web_session.controller

    games = controller.recipe_manager.get_available_games()
    if game_name not in games:
        return jsonify({"success": False, "error": f"配方文件 '{game_name}' 不存在"}), 404

    controller.current_game = game_name
    controller.recipe_manager.load_recipe_file(game_name)
    controller.calculator = CraftingCalculator(controller.recipe_manager)

    calculator = controller.calculator

    try:
        production_paths = calculator.find_production_paths(target_item)
        alternatives = []
        path_id_counter = 1

        for path_recipes in production_paths:
            try:
                temp_tree = calculator.build_crafting_tree(
                    target_item, target_rate_value, path_recipes
                )
                if not temp_tree:
                    continue

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

                def count_devices(node):
                    total = node.device_count
                    for child in node.children:
                        total += count_devices(child)
                    return total

                device_count = count_devices(temp_tree)

                recipe_name = ""
                if target_node.recipe:
                    recipes = calculator.recipe_manager.get_all_recipes()
                    for name, recipe in recipes.items():
                        if recipe == target_node.recipe:
                            recipe_name = name
                            break

                efficiency_score = min(1.0, max(0.0, 1.0 / (1.0 + device_count * 0.1)))

                node_chain = []
                current = target_node
                while current:
                    node_chain.append({
                        "item_name": current.item_name,
                        "amount": current.amount,
                        "device_count": current.device_count,
                        "recipe_name": recipe_name if current == target_node else "",
                    })
                    if current.children:
                        current = current.children[0]
                    else:
                        break

                alternatives.append({
                    "path_id": path_id_counter,
                    "node_chain": node_chain,
                    "device_count": device_count,
                    "efficiency_score": efficiency_score,
                    "recipe_name": recipe_name,
                })

                path_id_counter += 1

            except Exception:
                continue

        alternatives.sort(key=lambda x: x["device_count"])
        for i, alt in enumerate(alternatives):
            alt["path_id"] = i + 1

        return jsonify({
            "success": True,
            "node_item": node_item,
            "target_item": target_item,
            "target_rate": target_rate_value,
            "alternatives_count": len(alternatives),
            "alternatives": alternatives,
        })

    except Exception as e:
        return jsonify({"success": False, "error": f"获取替代路径失败: {str(e)}"}), 500


# ========================================
# 错误处理
# ========================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({"success": False, "error": "页面未找到"}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"success": False, "error": "服务器内部错误"}), 500


# ========================================
# 启动应用
# ========================================

if __name__ == "__main__":
    print("启动 Web GUI 服务器...")
    print("访问地址: http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=True)
