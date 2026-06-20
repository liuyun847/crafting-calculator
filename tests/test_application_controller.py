"""
应用控制器测试

测试 application_controller 模块的核心功能
"""

from application_controller import ApplicationController


class TestApplicationControllerInit:
    """测试 ApplicationController 初始化"""

    def test_basic_init(self, terminal_io):
        """测试基本初始化"""
        controller = ApplicationController(terminal_io)

        assert controller.io == terminal_io
        assert controller.recipe_manager is not None
        assert controller.calculator is None
        assert controller.current_game is None
        assert controller.state == "main_menu"

    def test_state_initialization(self, terminal_io):
        """测试状态初始化"""
        controller = ApplicationController(terminal_io)

        assert controller.state == "main_menu"
        assert controller.pending_data == {}
        assert controller._current_chain_trees == []
        assert controller._current_main_tree is None
        assert controller._current_target_item == ""
        assert controller._current_target_rate == 0.0
        assert controller._node_id_map == {}


class TestPendingData:
    """测试 pending_data 管理"""

    def test_pending_data_storage(self, terminal_io):
        """测试 pending_data 存储"""
        controller = ApplicationController(terminal_io)

        controller.pending_data["test_key"] = "test_value"

        assert controller.pending_data["test_key"] == "test_value"

    def test_pending_data_clear(self, terminal_io):
        """测试 pending_data 清空"""
        controller = ApplicationController(terminal_io)
        controller.pending_data["key1"] = "value1"
        controller.pending_data["key2"] = "value2"

        controller.pending_data.clear()

        assert len(controller.pending_data) == 0


class TestPathSwitchingState:
    """测试路径切换状态"""

    def test_current_chain_trees(self, terminal_io):
        """测试当前链树"""
        controller = ApplicationController(terminal_io)

        controller._current_chain_trees = [{"tree": 1}, {"tree": 2}]

        assert len(controller._current_chain_trees) == 2

    def test_current_main_tree(self, terminal_io):
        """测试当前主树"""
        controller = ApplicationController(terminal_io)

        controller._current_main_tree = {"main": "tree"}

        assert controller._current_main_tree is not None
        assert controller._current_main_tree["main"] == "tree"

    def test_current_target_item(self, terminal_io):
        """测试当前目标物品"""
        controller = ApplicationController(terminal_io)

        controller._current_target_item = "铁锭"

        assert controller._current_target_item == "铁锭"

    def test_current_target_rate(self, terminal_io):
        """测试当前目标速度"""
        controller = ApplicationController(terminal_io)

        controller._current_target_rate = 1.5

        assert controller._current_target_rate == 1.5

    def test_node_id_map(self, terminal_io):
        """测试节点 ID 映射"""
        controller = ApplicationController(terminal_io)

        controller._node_id_map[1] = {"item": "铁锭"}
        controller._node_id_map[2] = {"item": "铜锭"}

        assert len(controller._node_id_map) == 2
        assert controller._node_id_map[1]["item"] == "铁锭"
