"""
应用控制器测试

测试 application_controller 模块的核心功能，包括终端交互方法。
"""

import pytest
from unittest.mock import patch

from application_controller import ApplicationController
from calculator import CraftingCalculator, CraftingNode
from io_interface import IOInterface


class MockIO(IOInterface):
    """测试用模拟 IO，记录输出并按队列返回预设输入"""

    def __init__(self, inputs=None):
        self._inputs = list(inputs) if inputs else []
        self._input_index = 0
        self.outputs = []

    def print(self, text: str) -> None:
        self.outputs.append(str(text))

    def input(self, prompt: str) -> str:
        if self._input_index < len(self._inputs):
            result = self._inputs[self._input_index]
            self._input_index += 1
            return result
        return ""

    def clear(self) -> None:
        pass

    def contains(self, text: str) -> bool:
        """检查输出中是否包含指定文本"""
        return any(text in out for out in self.outputs)

    def reset(self, inputs=None):
        """重置 IO 状态"""
        if inputs is not None:
            self._inputs = list(inputs)
            self._input_index = 0
        self.outputs = []


@pytest.fixture
def mock_io():
    """创建 MockIO 实例"""
    return MockIO()


@pytest.fixture
def controller(mock_io):
    """创建带 MockIO 的 ApplicationController"""
    return ApplicationController(mock_io)


@pytest.fixture
def loaded_controller(mock_io, recipe_manager):
    """创建已加载配方的控制器"""
    ctrl = ApplicationController(mock_io)
    ctrl.recipe_manager = recipe_manager
    ctrl.current_game = "test_game"
    ctrl.calculator = CraftingCalculator(recipe_manager)
    return ctrl


def _make_simple_tree():
    """构建简单的测试用合成树"""
    return {
        "item_name": "铁锭",
        "amount": 5.0,
        "device_count": 1.0,
        "recipe": {"device": "熔炉"},
        "inputs": {"铁矿石": 10.0, "煤炭": 5.0},
        "children": [
            {
                "item_name": "铁矿石",
                "amount": 10.0,
                "device_count": 2.0,
                "recipe": {"device": "采矿机"},
                "inputs": {},
                "children": [],
                "path_info": {"alternative_count": 0, "path_id": 0, "is_alternative": False},
                "alternative_paths": [],
            },
            {
                "item_name": "煤炭",
                "amount": 5.0,
                "device_count": 1.0,
                "recipe": {"device": "采矿机"},
                "inputs": {},
                "children": [],
                "path_info": {"alternative_count": 1, "path_id": 0, "is_alternative": False},
                "alternative_paths": [[
                    {"item_name": "煤炭", "amount": 5.0, "device_count": 0.5}
                ]],
            },
        ],
        "path_info": {"alternative_count": 0, "path_id": 0, "is_alternative": False},
        "alternative_paths": [],
    }


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


# ======================================================================
# 终端交互方法单元测试（使用 MockIO）
# ======================================================================


class TestOutputMethods:
    """测试纯输出方法"""

    def test_print_menu(self, controller, mock_io):
        """测试主菜单打印"""
        controller._print_menu()
        assert mock_io.contains("自动化建造游戏通用合成计算器")
        assert mock_io.contains("1. 选择配方文件")
        assert mock_io.contains("5. 退出程序")

    def test_print_recipe_list_empty(self, controller, mock_io):
        """测试空配方列表打印"""
        controller._print_recipe_list({})
        assert mock_io.contains("配方文件为空")

    def test_print_recipe_list_with_data(self, controller, mock_io):
        """测试有配方的列表打印"""
        recipes = {
            "铁矿冶炼": {
                "device": "熔炉",
                "outputs": {"铁锭": {"amount": 5.0}},
            }
        }
        controller._print_recipe_list(recipes)
        assert mock_io.contains("铁矿冶炼")
        assert mock_io.contains("熔炉")
        assert mock_io.contains("铁锭")

    def test_print_raw_materials_empty(self, controller, mock_io):
        """测试空基础原料打印"""
        controller._print_raw_materials({})
        assert mock_io.contains("无基础原料消耗")

    def test_print_raw_materials_with_data(self, controller, mock_io):
        """测试有基础原料的打印"""
        controller._print_raw_materials({"铁矿石": 10.0, "煤炭": 5.0})
        assert mock_io.contains("铁矿石: 10.00/s")
        assert mock_io.contains("煤炭: 5.00/s")

    def test_print_device_stats_empty(self, controller, mock_io):
        """测试空设备统计打印"""
        controller._print_device_stats({})
        assert mock_io.contains("无设备使用")

    def test_print_device_stats_with_data(self, controller, mock_io):
        """测试有设备统计的打印"""
        controller._print_device_stats({"熔炉": 2.0, "采矿机": 3.0})
        assert mock_io.contains("熔炉: 2.00 台")
        assert mock_io.contains("采矿机: 3.00 台")

    def test_print_chain_commands_help(self, controller, mock_io):
        """测试命令帮助打印"""
        controller._print_chain_commands_help()
        assert mock_io.contains("alt <编号>")
        assert mock_io.contains("la / list-alt")
        assert mock_io.contains("q / quit")


class TestPrintNameList:
    """测试名称列表打印"""

    def test_print_name_list_no_filter(self, controller, mock_io):
        """测试无过滤的名称列表"""
        name_list = [("铁锭", 3), ("铜锭", 2), ("钢板", 1)]
        result = controller._print_name_list(name_list, "")
        assert len(result) == 3
        assert "铁锭" in result
        assert mock_io.contains("已有名称列表 (共 3 项)")
        assert mock_io.contains("铁锭 (使用次数: 3)")

    def test_print_name_list_with_filter(self, controller, mock_io):
        """测试带搜索过滤的名称列表"""
        name_list = [("铁锭", 3), ("铜锭", 2), ("铁矿石", 1)]
        result = controller._print_name_list(name_list, "铁")
        assert len(result) == 2
        assert "铁锭" in result
        assert "铁矿石" in result
        assert "铜锭" not in result

    def test_print_name_list_no_match(self, controller, mock_io):
        """测试无匹配结果"""
        name_list = [("铁锭", 3)]
        result = controller._print_name_list(name_list, "不存在")
        assert len(result) == 0
        assert mock_io.contains("未找到匹配 '不存在' 的名称")


class TestPrintTree:
    """测试树形打印"""

    def test_print_tree_simple(self, controller, mock_io):
        """测试简单树打印"""
        tree = _make_simple_tree()
        controller._print_tree(tree)
        assert mock_io.contains("铁锭: 5.00/s")
        assert mock_io.contains("铁矿石: 10.00/s")
        assert mock_io.contains("煤炭: 5.00/s")
        assert mock_io.contains("设备数: 1.00")

    def test_print_tree_with_alternative_marker(self, controller, mock_io):
        """测试带替代路径标记的树打印"""
        tree = _make_simple_tree()
        controller._print_tree(tree)
        # 煤炭节点有1条替代路径，应显示 [1] 标记
        assert mock_io.contains("煤炭: 5.00/s [1]")

    def test_print_tree_device_info(self, controller, mock_io):
        """测试设备信息打印"""
        tree = _make_simple_tree()
        controller._print_tree(tree)
        assert mock_io.contains("设备: 熔炉")
        assert mock_io.contains("设备: 采矿机")


class TestValidateExpression:
    """测试表达式验证"""

    def test_valid_integer(self, controller):
        assert controller._validate_expression("10") is True

    def test_valid_expression(self, controller):
        assert controller._validate_expression("15/min") is True

    def test_valid_math_expression(self, controller):
        assert controller._validate_expression("2+3") is True

    def test_invalid_expression(self, controller):
        assert controller._validate_expression("abc") is False

    def test_empty_expression(self, controller):
        assert controller._validate_expression("") is False


class TestGenerateRecipeId:
    """测试配方 ID 生成"""

    def test_single_output(self, controller):
        outputs = {"铁锭": {"amount": 5.0}}
        recipe_id = controller._generate_recipe_id(outputs, {})
        assert recipe_id == "铁锭生产"

    def test_multiple_outputs_picks_max(self, controller):
        outputs = {"铁锭": {"amount": 2.0}, "铜锭": {"amount": 5.0}}
        recipe_id = controller._generate_recipe_id(outputs, {})
        assert recipe_id == "铜锭生产"

    def test_empty_outputs(self, controller):
        recipe_id = controller._generate_recipe_id({}, {})
        assert recipe_id == "未知配方"

    def test_duplicate_id_adds_counter(self, controller):
        outputs = {"铁锭": {"amount": 5.0}}
        existing = {"铁锭生产": {}}
        recipe_id = controller._generate_recipe_id(outputs, existing)
        assert recipe_id == "铁锭生产_2"

    def test_duplicate_id_multiple_counters(self, controller):
        outputs = {"铁锭": {"amount": 5.0}}
        existing = {"铁锭生产": {}, "铁锭生产_2": {}, "铁锭生产_3": {}}
        recipe_id = controller._generate_recipe_id(outputs, existing)
        assert recipe_id == "铁锭生产_4"


class TestConfirmRecipe:
    """测试配方确认"""

    def test_confirm_yes(self, controller, mock_io):
        mock_io.reset(["y"])
        assert controller._confirm_recipe() is True

    def test_confirm_yes_chinese(self, controller, mock_io):
        mock_io.reset(["是"])
        assert controller._confirm_recipe() is True

    def test_confirm_no(self, controller, mock_io):
        mock_io.reset(["n"])
        assert controller._confirm_recipe() is False

    def test_confirm_no_chinese(self, controller, mock_io):
        mock_io.reset(["否"])
        assert controller._confirm_recipe() is False

    def test_confirm_invalid_then_yes(self, controller, mock_io):
        mock_io.reset(["invalid", "y"])
        assert controller._confirm_recipe() is True
        assert mock_io.contains("请输入 y 或 n")


class TestInputItem:
    """测试物品输入"""

    def test_valid_input(self, controller, mock_io):
        mock_io.reset(["10"])
        result = controller._input_item()
        assert result["amount"] == 10.0
        assert result["expression"] == "10"

    def test_expression_input(self, controller, mock_io):
        mock_io.reset(["15/min"])
        result = controller._input_item()
        assert result["amount"] == 0.25
        assert result["expression"] == "15/min"

    def test_zero_amount_retry(self, controller, mock_io):
        mock_io.reset(["0", "5"])
        result = controller._input_item()
        assert result["amount"] == 5.0
        assert mock_io.contains("数量必须大于0")

    def test_invalid_expression_retry(self, controller, mock_io):
        mock_io.reset(["abc", "10"])
        result = controller._input_item()
        assert result["amount"] == 10.0
        assert mock_io.contains("表达式格式无效")


class TestCheckHasAlternatives:
    """测试替代路径检查"""

    def test_no_alternatives(self, controller):
        tree = {
            "item_name": "铁锭",
            "path_info": {"alternative_count": 0},
            "children": [
                {"item_name": "铁矿石", "path_info": {"alternative_count": 0}, "children": []}
            ],
        }
        assert controller._check_has_alternatives(tree) is False

    def test_root_has_alternatives(self, controller):
        tree = {
            "item_name": "铁锭",
            "path_info": {"alternative_count": 2},
            "children": [],
        }
        assert controller._check_has_alternatives(tree) is True

    def test_child_has_alternatives(self, controller):
        tree = {
            "item_name": "铁锭",
            "path_info": {"alternative_count": 0},
            "children": [
                {
                    "item_name": "煤炭",
                    "path_info": {"alternative_count": 1},
                    "children": [],
                }
            ],
        }
        assert controller._check_has_alternatives(tree) is True


class TestDictToNode:
    """测试字典转节点"""

    def test_simple_conversion(self, controller):
        tree_dict = _make_simple_tree()
        node = controller._dict_to_node(tree_dict)
        assert node.item_name == "铁锭"
        assert node.amount == 5.0
        assert node.device_count == 1.0
        assert len(node.children) == 2
        assert node.children[0].item_name == "铁矿石"
        assert node.children[1].item_name == "煤炭"

    def test_parent_child_relationship(self, controller):
        tree_dict = _make_simple_tree()
        node = controller._dict_to_node(tree_dict)
        assert node.children[0].parent is node
        assert node.children[1].parent is node

    def test_inputs_populated(self, controller):
        tree_dict = _make_simple_tree()
        node = controller._dict_to_node(tree_dict)
        assert "铁矿石" in node.inputs
        assert "煤炭" in node.inputs


class TestAssignNodeIds:
    """测试节点编号分配"""

    def test_assign_ids_simple_tree(self, controller):
        tree = _make_simple_tree()
        controller._assign_node_ids(tree)
        # 根节点=1, 铁矿石=2, 煤炭=3
        assert len(controller._node_id_map) == 3
        assert controller._node_id_map[1]["item_name"] == "铁锭"
        assert controller._node_id_map[2]["item_name"] == "铁矿石"
        assert controller._node_id_map[3]["item_name"] == "煤炭"

    def test_assign_ids_clears_previous(self, controller):
        controller._node_id_map[99] = {"old": True}
        tree = _make_simple_tree()
        controller._assign_node_ids(tree)
        assert 99 not in controller._node_id_map

    def test_get_node_by_id_exists(self, controller):
        tree = _make_simple_tree()
        controller._assign_node_ids(tree)
        node = controller._get_node_by_id(1)
        assert node is not None
        assert node["item_name"] == "铁锭"

    def test_get_node_by_id_not_exists(self, controller):
        node = controller._get_node_by_id(999)
        assert node is None


class TestBuildTreeFromPath:
    """测试从路径构建树"""

    def test_build_from_single_node(self, controller):
        path = [{"item_name": "铁锭", "amount": 5.0, "device_count": 1.0}]
        tree = controller._build_tree_from_path(path, 5.0)
        assert tree is not None
        assert tree["item_name"] == "铁锭"
        assert tree["children"] == []

    def test_build_from_multi_node(self, controller):
        path = [
            {"item_name": "铁锭", "amount": 5.0, "device_count": 1.0},
            {"item_name": "铁矿石", "amount": 10.0, "device_count": 2.0},
            {"item_name": "煤炭", "amount": 5.0, "device_count": 1.0},
        ]
        tree = controller._build_tree_from_path(path, 5.0)
        assert tree is not None
        assert tree["item_name"] == "铁锭"
        assert len(tree["children"]) == 2
        assert tree["children"][0]["item_name"] == "铁矿石"

    def test_build_from_empty_path(self, controller):
        tree = controller._build_tree_from_path([], 5.0)
        assert tree is None


class TestProcessMainMenu:
    """测试主菜单处理"""

    def test_invalid_choice(self, controller, mock_io):
        mock_io.reset(["9", ""])
        controller._process_main_menu()
        assert mock_io.contains("选择无效")

    def test_exit_choice(self, controller, mock_io):
        mock_io.reset(["5"])
        with pytest.raises(SystemExit):
            controller._process_main_menu()


class TestShowItemsList:
    """测试物品列表显示"""

    def test_no_game_loaded(self, controller, mock_io):
        controller._show_items_list_terminal()
        assert mock_io.contains("请先选择配方文件")

    def test_show_items(self, loaded_controller, mock_io):
        loaded_controller._show_items_list_terminal()
        assert mock_io.contains("可用物品列表")
        # sample_recipes 包含铁锭、铜锭、铁矿石等
        assert mock_io.contains("铁锭")
        assert mock_io.contains("铜锭")


class TestShowRecipeList:
    """测试配方列表显示"""

    def test_show_recipe_list(self, loaded_controller, mock_io):
        loaded_controller._show_recipe_list_terminal()
        assert mock_io.contains("当前配方文件中的配方")
        assert mock_io.contains("铁矿冶炼")
        assert mock_io.contains("铜矿冶炼")

    def test_recipe_management_no_game(self, controller, mock_io):
        controller._recipe_management_submenu()
        assert mock_io.contains("请先选择配方文件")


class TestDeleteRecipe:
    """测试删除配方"""

    def test_delete_submenu_cancel(self, loaded_controller, mock_io):
        mock_io.reset(["3", ""])
        loaded_controller._delete_recipe_terminal()
        assert mock_io.contains("已取消删除操作")

    def test_delete_submenu_invalid(self, loaded_controller, mock_io):
        mock_io.reset(["9", ""])
        loaded_controller._delete_recipe_terminal()
        assert mock_io.contains("选择无效")

    def test_delete_by_index_cancel(self, loaded_controller, mock_io):
        mock_io.reset(["0"])
        loaded_controller._delete_recipe_by_index()
        assert mock_io.contains("已取消删除操作")

    def test_delete_by_index_invalid_number(self, loaded_controller, mock_io):
        mock_io.reset(["abc"])
        loaded_controller._delete_recipe_by_index()
        assert mock_io.contains("请输入有效的数字")

    def test_delete_by_index_out_of_range(self, loaded_controller, mock_io):
        mock_io.reset(["99"])
        loaded_controller._delete_recipe_by_index()
        assert mock_io.contains("无效序号")

    def test_delete_by_name_empty(self, loaded_controller, mock_io):
        mock_io.reset([""])
        loaded_controller._delete_recipe_by_name()
        assert mock_io.contains("配方名称不能为空")

    def test_delete_by_name_not_found(self, loaded_controller, mock_io):
        mock_io.reset(["不存在的配方"])
        loaded_controller._delete_recipe_by_name()
        assert mock_io.contains("不存在")

    def test_delete_by_index_success(self, loaded_controller, mock_io):
        # sample_recipes 有 5 个配方，选择第1个，确认删除
        mock_io.reset(["1", "y"])
        loaded_controller._delete_recipe_by_index()
        assert mock_io.contains("成功删除配方")

    def test_confirm_and_delete_cancel(self, loaded_controller, mock_io):
        recipes = loaded_controller.recipe_manager.get_all_recipes()
        recipe_name = next(iter(recipes))
        mock_io.reset(["n"])
        loaded_controller._confirm_and_delete_recipe(recipe_name, recipes[recipe_name])
        assert mock_io.contains("已取消删除操作")


class TestModifyRecipe:
    """测试修改配方"""

    def test_modify_no_recipes(self, mock_io, recipe_manager):
        controller = ApplicationController(mock_io)
        controller.recipe_manager = recipe_manager
        controller.current_game = "test_game"
        controller.calculator = CraftingCalculator(recipe_manager)
        # 清空所有配方
        controller.recipe_manager.recipes = {}
        controller._modify_recipe_terminal()
        assert mock_io.contains("当前没有可修改的配方")

    def test_modify_invalid_index(self, loaded_controller, mock_io):
        mock_io.reset(["abc"])
        loaded_controller._modify_recipe_terminal()
        assert mock_io.contains("请输入有效的数字")

    def test_modify_cancel(self, loaded_controller, mock_io):
        mock_io.reset(["0"])
        loaded_controller._modify_recipe_terminal()
        assert mock_io.contains("已取消修改")


class TestSelectGame:
    """测试选择配方文件"""

    def test_select_game_no_games(self, mock_io, temp_dir):
        from data_manager import RecipeManager
        controller = ApplicationController(mock_io)
        controller.recipe_manager = RecipeManager(recipes_dir=temp_dir)
        controller._select_game_terminal()
        assert mock_io.contains("没有找到配方文件")

    def test_select_game_invalid_number(self, mock_io, recipe_manager):
        controller = ApplicationController(mock_io)
        controller.recipe_manager = recipe_manager
        mock_io.reset(["abc"])
        with patch("application_controller.config_manager"):
            controller._select_game_terminal()
        assert mock_io.contains("请输入有效的数字")

    def test_select_game_out_of_range(self, mock_io, recipe_manager):
        controller = ApplicationController(mock_io)
        controller.recipe_manager = recipe_manager
        mock_io.reset(["99"])
        with patch("application_controller.config_manager"):
            controller._select_game_terminal()
        assert mock_io.contains("选择无效")

    def test_select_game_success(self, mock_io, recipe_manager):
        controller = ApplicationController(mock_io)
        controller.recipe_manager = recipe_manager
        mock_io.reset(["1"])
        with patch("application_controller.config_manager") as mock_config:
            controller._select_game_terminal()
            mock_config.set_last_game.assert_called_once()
        assert mock_io.contains("成功加载配方文件")
        assert controller.current_game is not None


class TestChainInteractiveCommands:
    """测试生产链交互命令"""

    def test_quit_command(self, controller, mock_io):
        mock_io.reset(["q"])
        result = controller._process_chain_interactive_commands()
        assert result is False

    def test_quit_alias_exit(self, controller, mock_io):
        mock_io.reset(["exit"])
        result = controller._process_chain_interactive_commands()
        assert result is False

    def test_quit_alias_back(self, controller, mock_io):
        mock_io.reset(["b"])
        result = controller._process_chain_interactive_commands()
        assert result is False

    def test_help_command(self, controller, mock_io):
        mock_io.reset(["help"])
        result = controller._process_chain_interactive_commands()
        assert result is True
        assert mock_io.contains("生产链交互命令")

    def test_help_alias_question(self, controller, mock_io):
        mock_io.reset(["?"])
        result = controller._process_chain_interactive_commands()
        assert result is True

    def test_unknown_command(self, controller, mock_io):
        mock_io.reset(["xyz"])
        result = controller._process_chain_interactive_commands()
        assert result is True
        assert mock_io.contains("未知命令")

    def test_list_alt_command(self, controller, mock_io):
        """测试列出替代路径节点命令"""
        controller._current_main_tree = _make_simple_tree()
        controller._assign_node_ids(controller._current_main_tree)
        mock_io.reset(["la"])
        result = controller._process_chain_interactive_commands()
        assert result is True
        assert mock_io.contains("具有替代路径的节点列表")


class TestListAlternativeNodes:
    """测试列出替代路径节点"""

    def test_no_active_chain(self, controller, mock_io):
        controller._list_alternative_nodes()
        assert mock_io.contains("当前没有活动的生产链")

    def test_list_with_alternatives(self, controller, mock_io):
        controller._current_main_tree = _make_simple_tree()
        controller._assign_node_ids(controller._current_main_tree)
        controller._list_alternative_nodes()
        assert mock_io.contains("具有替代路径的节点列表")
        assert mock_io.contains("煤炭")

    def test_list_no_alternatives(self, controller, mock_io):
        tree = {
            "item_name": "铁锭",
            "amount": 5.0,
            "device_count": 1.0,
            "children": [],
            "path_info": {"alternative_count": 0},
        }
        controller._current_main_tree = tree
        controller._list_alternative_nodes()
        assert mock_io.contains("没有具有替代路径的节点")


class TestHandleAltCommand:
    """测试 alt 命令处理"""

    def test_invalid_node_id_string(self, controller, mock_io):
        result = controller._handle_alt_command("abc")
        assert result is False
        assert mock_io.contains("无效的节点编号")

    def test_node_not_exists(self, controller, mock_io):
        result = controller._handle_alt_command("999")
        assert result is False
        assert mock_io.contains("节点 #999 不存在")

    def test_node_no_alternatives(self, controller, mock_io):
        tree = _make_simple_tree()
        controller._assign_node_ids(tree)
        # 节点1（铁锭）没有替代路径
        result = controller._handle_alt_command("1")
        assert result is False
        assert mock_io.contains("没有可选的替代路径")

    def test_cancel_switch(self, controller, mock_io):
        tree = _make_simple_tree()
        controller._assign_node_ids(tree)
        controller._current_main_tree = tree
        controller._current_target_item = "铁锭"
        controller._current_target_rate = 5.0
        # 节点3（煤炭）有1条替代路径，输入0取消
        mock_io.reset(["0"])
        result = controller._handle_alt_command("3")
        assert result is False
        assert mock_io.contains("已取消路径切换")

    def test_invalid_path_choice(self, controller, mock_io):
        tree = _make_simple_tree()
        controller._assign_node_ids(tree)
        controller._current_main_tree = tree
        controller._current_target_item = "铁锭"
        controller._current_target_rate = 5.0
        # 节点3（煤炭）有1条替代路径，输入99超出范围
        mock_io.reset(["99"])
        result = controller._handle_alt_command("3")
        assert result is False
        assert mock_io.contains("无效的选择")

    def test_invalid_path_input(self, controller, mock_io):
        tree = _make_simple_tree()
        controller._assign_node_ids(tree)
        controller._current_main_tree = tree
        controller._current_target_item = "铁锭"
        controller._current_target_rate = 5.0
        mock_io.reset(["abc"])
        result = controller._handle_alt_command("3")
        assert result is False
        assert mock_io.contains("请输入有效的数字")


class TestSwitchToPath:
    """测试路径切换"""

    def test_no_active_chain(self, controller, mock_io):
        result = controller._switch_to_path(1, 0, [[{"item_name": "x"}]])
        assert result is False
        assert mock_io.contains("当前没有活动的生产链")

    def test_invalid_path_index(self, controller, mock_io):
        controller._current_main_tree = _make_simple_tree()
        result = controller._switch_to_path(1, -1, [[{"item_name": "x"}]])
        assert result is False
        assert mock_io.contains("无效的替代路径索引")

    def test_empty_alt_path(self, controller, mock_io):
        controller._current_main_tree = _make_simple_tree()
        result = controller._switch_to_path(1, 0, [[]])
        assert result is False
        assert mock_io.contains("选中的替代路径为空")

    def test_node_not_found(self, controller, mock_io):
        controller._current_main_tree = _make_simple_tree()
        result = controller._switch_to_path(999, 0, [[{"item_name": "x"}]])
        assert result is False
        assert mock_io.contains("无法获取节点 #999 的信息")

    def test_no_target_item(self, controller, mock_io):
        tree = _make_simple_tree()
        controller._current_main_tree = tree
        controller._assign_node_ids(tree)
        controller._current_target_item = ""
        controller._current_target_rate = 0.0
        result = controller._switch_to_path(1, 0, [[{"item_name": "x", "device_count": 1.0}]])
        assert result is False
        assert mock_io.contains("无法获取目标物品信息")

    def test_switch_success(self, controller, mock_io):
        tree = _make_simple_tree()
        controller._current_main_tree = tree
        controller._assign_node_ids(tree)
        controller._current_target_item = "铁锭"
        controller._current_target_rate = 5.0
        alt_path = [{"item_name": "煤炭", "amount": 5.0, "device_count": 0.5}]
        result = controller._switch_to_path(3, 0, [alt_path])
        assert result is True
        assert mock_io.contains("成功切换到新路径")


class TestShowAlternativePaths:
    """测试显示替代路径"""

    def test_show_alternative_paths(self, controller, mock_io):
        node_info = {
            "item_name": "煤炭",
            "device_count": 1.0,
        }
        alt_paths = [[
            {"item_name": "煤炭", "device_count": 0.5},
            {"item_name": "焦炭", "device_count": 0.3},
        ]]
        controller._show_alternative_paths(3, node_info, alt_paths)
        assert mock_io.contains("节点 #3 (煤炭) 的可选路径")
        assert mock_io.contains("路径 1")
        assert mock_io.contains("设备总数")

    def test_show_alternative_paths_with_diff(self, controller, mock_io):
        node_info = {
            "item_name": "煤炭",
            "device_count": 1.0,
        }
        # 替代路径设备数更少
        alt_paths = [[{"item_name": "煤炭", "device_count": 0.5}]]
        controller._show_alternative_paths(1, node_info, alt_paths)
        # 设备数减少应显示负数差异
        assert mock_io.contains("(-0.50)")


class TestDisplayCurrentChain:
    """测试显示当前生产链"""

    def test_no_chain(self, controller, mock_io):
        controller._current_main_tree = None
        controller._display_current_chain()
        # 无主树时不输出任何内容
        assert len(mock_io.outputs) == 0

    def test_display_chain(self, loaded_controller, mock_io):
        tree = _make_simple_tree()
        loaded_controller._current_main_tree = tree
        loaded_controller._current_target_item = "铁锭"
        loaded_controller._current_target_rate = 5.0
        loaded_controller._display_current_chain()
        assert mock_io.contains("生产链: 铁锭")
        assert mock_io.contains("5.00/s")
        assert mock_io.contains("基础原料消耗")


class TestDisplayRecipePreview:
    """测试配方预览"""

    def test_display_preview_with_items(self, controller, mock_io):
        inputs = {"铁矿石": {"amount": 10.0, "expression": "10"}}
        outputs = {"铁锭": {"amount": 5.0, "expression": "5"}}
        controller._display_recipe_preview("铁矿冶炼", "熔炉", inputs, outputs)
        assert mock_io.contains("配方预览")
        assert mock_io.contains("铁矿冶炼")
        assert mock_io.contains("熔炉")
        assert mock_io.contains("铁矿石")
        assert mock_io.contains("铁锭")

    def test_display_preview_empty(self, controller, mock_io):
        controller._display_recipe_preview("空配方", "无设备", {}, {})
        assert mock_io.contains("(无)")


class TestDisplayCurrentRecipeFields:
    """测试显示当前配方字段"""

    def test_display_fields_with_dict_items(self, controller, mock_io):
        inputs = {"铁矿石": {"amount": 10.0, "expression": "10"}}
        outputs = {"铁锭": {"amount": 5.0, "expression": "5"}}
        controller._display_current_recipe_fields("铁矿冶炼", "熔炉", inputs, outputs)
        assert mock_io.contains("当前配方信息")
        assert mock_io.contains("铁矿冶炼")
        assert mock_io.contains("10.00/s")

    def test_display_fields_empty_items(self, controller, mock_io):
        controller._display_current_recipe_fields("空配方", "无", {}, {})
        assert mock_io.contains("(无)")
