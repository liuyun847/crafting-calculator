"""
Web会话管理公共模块
提供跨应用的会话状态管理、状态序列化/反序列化功能
"""
import os
import sys
import uuid
from typing import Dict, Any, Optional
from flask import session

# 项目根目录配置
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from application_controller import ApplicationController
from io_interface import WebIO
from calculator import CraftingCalculator


class BaseWebSession:
    """Web会话状态管理基类"""

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
        pending_data = getattr(self.controller, "pending_data", {}).copy()
        if "existing_items" in pending_data and isinstance(
            pending_data["existing_items"], set
        ):
            pending_data["existing_items"] = list(
                pending_data["existing_items"])
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
            pending_data["existing_items"] = set(
                pending_data["existing_items"])
        return pending_data

    def load_game(self, game_name: str) -> bool:
        """
        加载指定游戏配方

        Args:
            game_name: 游戏名称

        Returns:
            加载成功返回True，失败返回False
        """
        available_games = self.controller.recipe_manager.get_available_games()
        if game_name not in available_games:
            return False

        try:
            self.controller.recipe_manager.load_recipe_file(game_name)
            self.controller.current_game = game_name
            self.controller.calculator = CraftingCalculator(
                self.controller.recipe_manager
            )
            return True
        except Exception:
            return False


def get_session(session_class=BaseWebSession) -> BaseWebSession:
    """
    获取或创建会话

    Args:
        session_class: 会话类，用于扩展自定义会话

    Returns:
        WebSession实例
    """
    # 使用全局字典存储WebSession对象，避免Flask session序列化问题
    if not hasattr(get_session, "_sessions"):
        get_session._sessions = {}

    session_id = session.get("session_id")
    if not session_id or session_id not in get_session._sessions:
        # 创建新会话
        session_id = str(uuid.uuid4())
        session["session_id"] = session_id
        get_session._sessions[session_id] = session_class()

    web_session = get_session._sessions[session_id]

    # 恢复状态
    if "state" in session:
        try:
            web_session.set_state(session["state"])
        except Exception:
            # 如果恢复失败，创建新会话
            get_session._sessions[session_id] = session_class()
            web_session = get_session._sessions[session_id]

    return web_session


def save_session(web_session: BaseWebSession):
    """
    保存会话状态

    Args:
        web_session: WebSession实例
    """
    session["state"] = web_session.get_state()


def get_current_game() -> Optional[str]:
    """
    获取当前游戏名称

    Returns:
        当前游戏名称，如果未选择返回None
    """
    web_session = get_session()
    return web_session.controller.current_game
