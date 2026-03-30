"""
自动化建造游戏通用合成计算器 - Web GUI 应用

提供现代化的图形界面Web应用，支持：
- 配方文件选择
- 生产链计算与可视化
- 配方管理（CRUD）
- 路径切换

安全配置：
- Secret Key: 通过 shared.security 模块统一管理
- CSRF 保护: 使用 Flask-WTF，API 端点已豁免（纯 API 服务）
"""

import os
import sys
from typing import Optional
from flask import Flask, render_template, request, jsonify, session
from flask_wtf.csrf import CSRFProtect

# 添加项目根目录到路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from config_manager import config_manager
from shared.security import get_flask_secret_key
# 导入公共API模块
from shared.api import (
    BaseWebSession,
    get_session as base_get_session,
    save_session,
    get_current_game,
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
    clear_api_cache,
    get_api_cache_stats,
)


# 扩展WebSession，添加加载上次游戏的功能
class WebSession(BaseWebSession):
    """扩展的Web会话，支持自动加载上次选择的游戏"""
    def __init__(self):
        super().__init__()
        self._load_last_game()

    def _load_last_game(self):
        """加载上次选择的游戏"""
        last_game = config_manager.get_last_game()
        if last_game:
            self.load_game(last_game)


def get_session() -> WebSession:
    """获取或创建扩展的会话"""
    return base_get_session(session_class=WebSession)


app = Flask(__name__,
            template_folder='templates',
            static_folder='static'
            )
app.secret_key = get_flask_secret_key("web-gui")

# ============================================================
# CSRF 保护配置
# ============================================================
# 初始化 CSRF 保护
csrf = CSRFProtect(app)


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
    return get_games_api()


@app.route("/api/select-game", methods=["POST"])
@csrf.exempt
def api_select_game():
    """选择配方文件"""
    response = select_game_api()
    # 如果选择成功，更新配置并清空缓存
    if response.status_code == 200:
        data = request.get_json()
        config_manager.set_last_game(data.get("game", ""))
        # 切换游戏后清空所有缓存
        clear_api_cache()
        web_session = get_session()
        if web_session.controller.calculator:
            web_session.controller.calculator.clear_cache()
    return response


# ========================================
# API路由 - 物品
# ========================================

@app.route("/api/items", methods=["GET"])
def get_items():
    """获取物品列表"""
    return get_items_api()


# ========================================
# API路由 - 配方管理
# ========================================

@app.route("/api/recipes", methods=["GET"])
def get_recipes():
    """获取配方列表"""
    return get_recipes_api()


@app.route("/api/recipes/<recipe_name>", methods=["GET"])
def get_recipe(recipe_name):
    """获取单个配方详情"""
    return get_recipe_api(recipe_name)


@app.route("/api/recipes", methods=["POST"])
@csrf.exempt
def create_recipe():
    """创建新配方"""
    response = create_recipe_api()
    # 如果创建成功，清空缓存
    if response.status_code == 200:
        clear_api_cache()
        web_session = get_session()
        if web_session.controller.calculator:
            web_session.controller.calculator.clear_cache()
    return response


@app.route("/api/recipes/<recipe_name>", methods=["PUT"])
@csrf.exempt
def update_recipe(recipe_name):
    """更新配方"""
    response = update_recipe_api(recipe_name)
    # 如果更新成功，清空缓存
    if response.status_code == 200:
        clear_api_cache()
        web_session = get_session()
        if web_session.controller.calculator:
            web_session.controller.calculator.clear_cache()
    return response


@app.route("/api/recipes/<recipe_name>", methods=["DELETE"])
@csrf.exempt
def delete_recipe(recipe_name):
    """删除配方"""
    response = delete_recipe_api(recipe_name)
    # 如果删除成功，清空缓存
    if response.status_code == 200:
        clear_api_cache()
        web_session = get_session()
        if web_session.controller.calculator:
            web_session.controller.calculator.clear_cache()
    return response


# ========================================
# API路由 - 生产链计算
# ========================================

@app.route("/api/calculate", methods=["POST"])
@csrf.exempt
def calculate():
    """计算生产链"""
    return calculate_api(include_alternatives=False)


@app.route("/api/calculate/alternatives", methods=["GET"])
def get_alternatives():
    """获取节点的可选路径列表"""
    return get_alternatives_api()


# ========================================
# API路由 - 缓存管理
# ========================================

@app.route("/api/cache/clear", methods=["POST"])
@csrf.exempt
def clear_cache():
    """清除所有缓存"""
    # 清除API层缓存
    clear_api_cache()
    # 清除计算层缓存
    web_session = get_session()
    if web_session.controller.calculator:
        web_session.controller.calculator.clear_cache()
    return jsonify({
        "success": True,
        "message": "缓存已清除"
    })

@app.route("/api/cache/stats", methods=["GET"])
def get_cache_stats():
    """获取缓存状态信息"""
    api_stats = get_api_cache_stats()
    calculator_stats = {
        "calculate_production_chain": 0,
        "find_production_paths": 0,
        "_item_exists": 0
    }
    
    web_session = get_session()
    if web_session.controller.calculator:
        # 获取计算层缓存信息
        calculator = web_session.controller.calculator
        calculator_stats["calculate_production_chain"] = calculator.calculate_production_chain.cache_info().currsize
        calculator_stats["find_production_paths"] = calculator.find_production_paths.cache_info().currsize
        calculator_stats["_item_exists"] = calculator._item_exists.cache_info().currsize
    
    return jsonify({
        "success": True,
        "api_cache": api_stats,
        "calculator_cache": calculator_stats,
        "total_cache_entries": api_stats["cache_size"] + sum(calculator_stats.values())
    })


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
