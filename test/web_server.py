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
        return {
            "output": self.io.get_output(),
            "prompt": result["prompt"]
        }

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
            "pending_data": self._serialize_pending_data()
        }

    def set_state(self, state: Dict[str, Any]) -> None:
        """
        设置会话状态（用于反序列化）

        Args:
            state: 会话状态字典
        """
        self.controller.current_game = state.get("current_game")
        self.controller.state = state.get("state", "main_menu")
        self.controller.pending_data = self._deserialize_pending_data(state.get("pending_data", {}))

        if self.controller.current_game:
            try:
                self.controller.recipe_manager.load_recipe_file(self.controller.current_game)
                from calculator import CraftingCalculator
                self.controller.calculator = CraftingCalculator(self.controller.recipe_manager)
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
        if "existing_items" in pending_data and isinstance(pending_data["existing_items"], set):
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
        if "existing_items" in pending_data and isinstance(pending_data["existing_items"], list):
            pending_data["existing_items"] = set(pending_data["existing_items"])
        return pending_data


def get_session() -> WebSession:
    """
    获取或创建会话

    Returns:
        WebSession实例
    """
    if "web_session" not in session:
        session["web_session"] = WebSession()
        return session["web_session"]

    web_session = session["web_session"]
    if "state" in session:
        web_session.set_state(session["state"])
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

    return jsonify({
        "success": True,
        "output": result["output"],
        "prompt": result["prompt"]
    })


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
        return jsonify({
            "success": True,
            "output": web_session.io.get_output(),
            "prompt": result["prompt"]
        })
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


@app.route("/api/calculate", methods=["POST"])
def calculate():
    """计算生产链"""
    data = request.get_json()
    target_item = data.get("item", "")
    target_rate = data.get("rate", 0)

    web_session = get_session()
    if not web_session.controller.calculator:
        return jsonify({"success": False, "error": "请先选择配方文件"})

    web_session.io.clear()
    web_session.io.set_input(f"2 {target_item} {target_rate}")
    result = web_session.controller.process_command(f"2 {target_item} {target_rate}")
    save_session(web_session)
    return jsonify({
        "success": True,
        "output": web_session.io.get_output(),
        "prompt": result["prompt"]
    })


@app.route("/api/recipes", methods=["GET"])
def get_recipes():
    """获取配方列表"""
    web_session = get_session()
    recipes = web_session.controller.recipe_manager.get_all_recipes()
    return jsonify({"success": True, "recipes": recipes})


if __name__ == "__main__":
    print("启动 Web 测试服务器...")
    print("访问地址: http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=True)
