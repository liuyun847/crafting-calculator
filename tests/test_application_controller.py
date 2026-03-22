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


class TestProcessCommand:
    """测试 process_command 方法"""

    def test_main_menu_command(self, terminal_io):
        """测试主菜单命令"""
        controller = ApplicationController(terminal_io)

        result = controller.process_command("5")

        assert "output" in result
        assert "prompt" in result

    def test_empty_command(self, terminal_io):
        """测试空命令"""
        controller = ApplicationController(terminal_io)

        result = controller.process_command("")

        assert "output" in result
        assert "prompt" in result

    def test_help_command(self, terminal_io):
        """测试帮助命令"""
        controller = ApplicationController(terminal_io)

        result = controller.process_command("help")

        assert "output" in result
        assert "prompt" in result

    def test_reset_command(self, terminal_io):
        """测试重置命令"""
        controller = ApplicationController(terminal_io)
        controller.state = "some_state"

        result = controller.process_command("reset")

        assert controller.state == "main_menu"
        assert "output" in result


class TestStateTransitions:
    """测试状态转换"""

    def test_main_to_select_game(self, terminal_io):
        """测试从主菜单到选择游戏"""
        controller = ApplicationController(terminal_io)

        result = controller.process_command("1")

        assert controller.state == "select_game"

    def test_main_to_calculate_without_game(self, terminal_io):
        """测试未选择游戏时从主菜单到计算"""
        controller = ApplicationController(terminal_io)

        result = controller.process_command("2")

        # 未选择游戏时，保持在 main_menu 并提示用户
        assert controller.state == "main_menu"
        assert "请先选择配方文件" in result["output"]

    def test_main_to_calculate_with_game(self, terminal_io):
        """测试已选择游戏时从主菜单到计算"""
        controller = ApplicationController(terminal_io)
        # 模拟已选择游戏的状态
        controller.current_game = "test_game"
        controller.calculator = "mock_calculator"

        result = controller.process_command("2")

        assert controller.state == "calculate_item"

    def test_main_to_recipe_management_without_game(self, terminal_io):
        """测试未选择游戏时从主菜单到配方管理"""
        controller = ApplicationController(terminal_io)

        result = controller.process_command("4")

        # 未选择游戏时，保持在 main_menu 并提示用户
        assert controller.state == "main_menu"
        assert "请先选择配方文件" in result["output"]

    def test_main_to_recipe_management_with_game(self, terminal_io):
        """测试已选择游戏时从主菜单到配方管理"""
        controller = ApplicationController(terminal_io)
        # 模拟已选择游戏的状态
        controller.current_game = "test_game"

        result = controller.process_command("4")

        assert controller.state == "add_recipe_device"


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


class TestWebIOIntegration:
    """测试 WebIO 集成"""

    def test_web_io_controller(self, web_io):
        """测试 WebIO 控制器"""
        controller = ApplicationController(web_io)

        assert controller.io == web_io

        result = controller.process_command("help")

        assert "output" in result
        assert "prompt" in result

    def test_web_io_output_buffer(self, web_io):
        """测试 WebIO 输出缓冲区"""
        controller = ApplicationController(web_io)

        controller.process_command("help")

        assert web_io.has_output() is True

    def test_web_io_input_queue(self, web_io):
        """测试 WebIO 输入队列"""
        controller = ApplicationController(web_io)
        web_io.set_input("5")

        result = controller.process_command("")

        assert web_io.has_input() is False


class TestEdgeCases:
    """测试边界情况"""

    def test_invalid_command(self, terminal_io):
        """测试无效命令"""
        controller = ApplicationController(terminal_io)

        result = controller.process_command("invalid_command")

        assert "output" in result

    def test_whitespace_command(self, terminal_io):
        """测试空白命令"""
        controller = ApplicationController(terminal_io)

        result = controller.process_command("   ")

        assert "output" in result

    def test_numeric_command_out_of_range(self, terminal_io):
        """测试超出范围的数字命令"""
        controller = ApplicationController(terminal_io)

        result = controller.process_command("999")

        assert "output" in result

    def test_mixed_case_command(self, terminal_io):
        """测试混合大小写命令"""
        controller = ApplicationController(terminal_io)

        result1 = controller.process_command("HELP")
        result2 = controller.process_command("Help")
        result3 = controller.process_command("help")

        assert "output" in result1
        assert "output" in result2
        assert "output" in result3


class TestControllerLifecycle:
    """测试控制器生命周期"""

    def test_multiple_commands(self, terminal_io):
        """测试多个命令"""
        controller = ApplicationController(terminal_io)

        controller.process_command("help")
        controller.process_command("5")
        controller.process_command("reset")

        assert controller.state == "main_menu"

    def test_state_persistence(self, terminal_io):
        """测试状态持久化"""
        controller = ApplicationController(terminal_io)

        controller.process_command("1")
        state1 = controller.state

        controller.process_command("5")
        state2 = controller.state

        assert state1 == "select_game"
        assert state2 == "main_menu"

    def test_data_persistence(self, terminal_io):
        """测试数据持久化"""
        controller = ApplicationController(terminal_io)

        controller.pending_data["key"] = "value"
        controller.process_command("5")

        assert controller.pending_data["key"] == "value"


class TestErrorHandling:
    """测试错误处理"""

    def test_command_with_exception(self, terminal_io):
        """测试带异常的命令"""
        controller = ApplicationController(terminal_io)

        result = controller.process_command("invalid")

        assert "output" in result

    def test_state_recovery(self, terminal_io):
        """测试状态恢复"""
        controller = ApplicationController(terminal_io)

        controller.state = "invalid_state"
        result = controller.process_command("reset")

        assert controller.state == "main_menu"
