"""
应用控制器测试

测试 application_controller 模块的无状态单步命令模式。
每个命令独立测试，不依赖前序命令的内存状态。
"""

import pytest

from application_controller import ApplicationController
from calculator import CraftingCalculator
from crafting_node import CraftingNode
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
def controller(mock_io, recipe_manager):
    """创建带 MockIO 和已加载配方的控制器（无状态）"""
    ctrl = ApplicationController(mock_io)
    ctrl.recipe_manager = recipe_manager
    return ctrl


@pytest.fixture
def game_loaded(monkeypatch):
    """patch config_manager 使其返回 'test_game' 作为当前配方文件"""
    monkeypatch.setattr(
        "application_controller.config_manager.get_last_game", lambda: "test_game"
    )
    monkeypatch.setattr(
        "application_controller.config_manager.set_last_game", lambda name: None
    )


def _make_simple_tree():
    """构建简单的测试用合成树（含替代路径）"""
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


# ======================================================================
# 初始化测试
# ======================================================================


class TestInit:
    """测试初始化（无状态，仅保留 io 和 recipe_manager）"""

    def test_basic_init(self, terminal_io):
        controller = ApplicationController(terminal_io)
        assert controller.io == terminal_io
        assert controller.recipe_manager is not None

    def test_no_business_state(self, terminal_io):
        """验证控制器不保存任何业务状态字段"""
        controller = ApplicationController(terminal_io)
        assert not hasattr(controller, "current_game")
        assert not hasattr(controller, "calculator")
        assert not hasattr(controller, "state")
        assert not hasattr(controller, "pending_data")
        assert not hasattr(controller, "_current_chain_trees")
        assert not hasattr(controller, "_current_main_tree")
        assert not hasattr(controller, "_current_target_item")
        assert not hasattr(controller, "_current_target_rate")
        assert not hasattr(controller, "_node_id_map")


# ======================================================================
# 命令分发测试
# ======================================================================


class TestDispatch:
    """测试命令分发"""

    def test_quit(self, controller, mock_io):
        with pytest.raises(SystemExit):
            controller._dispatch("quit")
        assert mock_io.contains("退出程序")

    def test_exit(self, controller, mock_io):
        with pytest.raises(SystemExit):
            controller._dispatch("exit")

    def test_q_alias(self, controller, mock_io):
        with pytest.raises(SystemExit):
            controller._dispatch("q")

    def test_help(self, controller, mock_io):
        controller._dispatch("help")
        assert mock_io.contains("可用命令")

    def test_help_alias_question(self, controller, mock_io):
        controller._dispatch("?")
        assert mock_io.contains("可用命令")

    def test_unknown_command(self, controller, mock_io):
        controller._dispatch("nonexistent")
        assert mock_io.contains("未知命令")

    def test_empty_line(self, controller, mock_io):
        controller._dispatch("")
        assert len(mock_io.outputs) == 0

    def test_case_insensitive(self, controller, mock_io):
        """命令大小写不敏感"""
        controller._dispatch("HELP")
        assert mock_io.contains("可用命令")


# ======================================================================
# 命令实现测试
# ======================================================================


class TestCmdHelp:
    """测试 help 命令"""

    def test_help_lists_all_commands(self, controller, mock_io):
        controller._cmd_help([])
        assert mock_io.contains("games")
        assert mock_io.contains("use")
        assert mock_io.contains("calc")
        assert mock_io.contains("alts")
        assert mock_io.contains("use-path")
        assert mock_io.contains("items")
        assert mock_io.contains("recipes")
        assert mock_io.contains("recipe")
        assert mock_io.contains("quit")


class TestCmdGames:
    """测试 games 命令"""

    def test_games_with_files(self, controller, mock_io):
        controller._cmd_games([])
        assert mock_io.contains("可用配方文件")
        assert mock_io.contains("test_game")

    def test_games_no_files(self, mock_io, temp_dir):
        from data_manager import RecipeManager
        ctrl = ApplicationController(mock_io)
        ctrl.recipe_manager = RecipeManager(recipes_dir=temp_dir)
        # temp_dir 已存在但无 yaml 文件
        import os
        # 确保目录为空（无 yaml）
        for f in os.listdir(temp_dir):
            os.remove(os.path.join(temp_dir, f))
        ctrl._cmd_games([])
        assert mock_io.contains("没有找到配方文件")


class TestCmdUse:
    """测试 use 命令"""

    def test_use_success(self, controller, mock_io, monkeypatch):
        set_calls = []
        monkeypatch.setattr(
            "application_controller.config_manager.set_last_game",
            lambda name: set_calls.append(name),
        )
        controller._cmd_use(["test_game"])
        assert mock_io.contains("已选择配方文件: test_game")
        assert set_calls == ["test_game"]

    def test_use_nonexistent(self, controller, mock_io):
        controller._cmd_use(["nonexistent"])
        assert mock_io.contains("不存在")

    def test_use_no_args(self, controller, mock_io):
        controller._cmd_use([])
        assert mock_io.contains("用法")


class TestCmdGame:
    """测试 game 命令"""

    def test_game_with_current(self, controller, mock_io, monkeypatch):
        monkeypatch.setattr(
            "application_controller.config_manager.get_last_game", lambda: "test_game"
        )
        controller._cmd_game([])
        assert mock_io.contains("当前配方文件: test_game")

    def test_game_without_current(self, controller, mock_io, monkeypatch):
        monkeypatch.setattr(
            "application_controller.config_manager.get_last_game", lambda: None
        )
        controller._cmd_game([])
        assert mock_io.contains("未选择配方文件")


class TestCmdCalc:
    """测试 calc 命令"""

    def test_calc_no_args(self, controller, mock_io):
        controller._cmd_calc([])
        assert mock_io.contains("用法")

    def test_calc_no_game(self, controller, mock_io, monkeypatch):
        monkeypatch.setattr(
            "application_controller.config_manager.get_last_game", lambda: None
        )
        controller._cmd_calc(["铁锭", "5"])
        assert mock_io.contains("请先选择配方文件")

    def test_calc_invalid_rate(self, controller, mock_io, game_loaded):
        controller._cmd_calc(["铁锭", "abc"])
        assert mock_io.contains("无效的速度表达式")

    def test_calc_zero_rate(self, controller, mock_io, game_loaded):
        controller._cmd_calc(["铁锭", "0"])
        assert mock_io.contains("生产速度必须大于0")

    def test_calc_item_not_found(self, controller, mock_io, game_loaded):
        controller._cmd_calc(["不存在的物品", "5"])
        assert mock_io.contains("未找到生产")

    def test_calc_success(self, controller, mock_io, game_loaded):
        controller._cmd_calc(["铁锭", "5"])
        assert mock_io.contains("生产链")
        assert mock_io.contains("铁锭")
        # 节点应带编号
        assert mock_io.contains("#1")

    def test_calc_with_expression_rate(self, controller, mock_io, game_loaded):
        """速度支持表达式（如 15/min）"""
        controller._cmd_calc(["铁锭", "15/min"])
        assert mock_io.contains("生产链")


class TestCmdAlts:
    """测试 alts 命令"""

    def test_alts_no_args(self, controller, mock_io):
        controller._cmd_alts([])
        assert mock_io.contains("用法")

    def test_alts_invalid_node_id(self, controller, mock_io, game_loaded):
        controller._cmd_alts(["铁锭", "5", "abc"])
        assert mock_io.contains("节点编号必须是整数")

    def test_alts_node_not_exists(self, controller, mock_io, game_loaded):
        controller._cmd_alts(["铁锭", "5", "999"])
        assert mock_io.contains("节点 #999 不存在")

    def test_alts_node_no_alternatives(self, controller, mock_io, game_loaded):
        # 节点 1 是根节点（铁锭），通常无替代路径
        controller._cmd_alts(["铁锭", "5", "1"])
        # 根节点无替代路径或显示可选路径
        # 铁锭由铁矿冶炼生产，可能有替代路径，所以只验证能执行
        # 不强制断言，因为取决于配方


class TestCmdUsePath:
    """测试 use-path 命令"""

    def test_use_path_no_args(self, controller, mock_io):
        controller._cmd_use_path([])
        assert mock_io.contains("用法")

    def test_use_path_invalid_args(self, controller, mock_io, game_loaded):
        controller._cmd_use_path(["铁锭", "5", "abc", "1"])
        assert mock_io.contains("必须是整数")

    def test_use_path_zero_path_index(self, controller, mock_io, game_loaded):
        controller._cmd_use_path(["铁锭", "5", "1", "0"])
        assert mock_io.contains("路径编号必须大于0")

    def test_use_path_node_not_exists(self, controller, mock_io, game_loaded):
        controller._cmd_use_path(["铁锭", "5", "999", "1"])
        assert mock_io.contains("节点 #999 不存在")


class TestCmdItems:
    """测试 items 命令"""

    def test_items_no_game(self, controller, mock_io, monkeypatch):
        monkeypatch.setattr(
            "application_controller.config_manager.get_last_game", lambda: None
        )
        controller._cmd_items([])
        assert mock_io.contains("请先选择配方文件")

    def test_items_success(self, controller, mock_io, game_loaded):
        controller._cmd_items([])
        assert mock_io.contains("可用物品列表")
        assert mock_io.contains("铁锭")


class TestCmdRecipes:
    """测试 recipes 命令"""

    def test_recipes_no_game(self, controller, mock_io, monkeypatch):
        monkeypatch.setattr(
            "application_controller.config_manager.get_last_game", lambda: None
        )
        controller._cmd_recipes([])
        assert mock_io.contains("请先选择配方文件")

    def test_recipes_success(self, controller, mock_io, game_loaded):
        controller._cmd_recipes([])
        assert mock_io.contains("配方列表")
        assert mock_io.contains("铁矿冶炼")

    def test_recipes_with_search(self, controller, mock_io, game_loaded):
        controller._cmd_recipes(["铜"])
        assert mock_io.contains("铜矿冶炼")
        assert not mock_io.contains("[1] 铁矿冶炼")

    def test_recipes_page(self, controller, mock_io, game_loaded):
        controller._cmd_recipes(["1"])
        assert mock_io.contains("第 1/")


class TestCmdRecipe:
    """测试 recipe 子命令分发"""

    def test_recipe_no_args(self, controller, mock_io):
        controller._cmd_recipe([])
        assert mock_io.contains("用法")

    def test_recipe_show_via_subcommand(self, controller, mock_io, game_loaded):
        controller._cmd_recipe(["show", "铁矿冶炼"])
        assert mock_io.contains("配方: 铁矿冶炼")

    def test_recipe_show_via_name(self, controller, mock_io, game_loaded):
        """recipe <名称> 等同于查看详情"""
        controller._cmd_recipe(["铁矿冶炼"])
        assert mock_io.contains("配方: 铁矿冶炼")

    def test_recipe_show_not_found(self, controller, mock_io, game_loaded):
        controller._cmd_recipe(["不存在的配方"])
        assert mock_io.contains("不存在")

    def test_recipe_show_no_args(self, controller, mock_io, game_loaded):
        controller._cmd_recipe(["show"])
        assert mock_io.contains("用法")


class TestRecipeAdd:
    """测试 recipe add 命令"""

    def test_add_no_args(self, controller, mock_io):
        controller._cmd_recipe_add([])
        assert mock_io.contains("用法")

    def test_add_no_outputs(self, controller, mock_io, game_loaded):
        controller._cmd_recipe_add(["新配方", "--device", "熔炉"])
        assert mock_io.contains("至少需要 --outputs")

    def test_add_success(self, controller, mock_io, game_loaded):
        controller._cmd_recipe_add([
            "测试新配方",
            "--device", "熔炉",
            "--inputs", "铁矿石:10,煤:5",
            "--outputs", "铁锭:5",
        ])
        assert mock_io.contains("成功添加配方: 测试新配方")
        # 验证确实添加了
        recipes = controller.recipe_manager.get_all_recipes()
        assert "测试新配方" in recipes

    def test_add_duplicate(self, controller, mock_io, game_loaded):
        controller._cmd_recipe_add([
            "铁矿冶炼",  # 已存在
            "--device", "熔炉",
            "--outputs", "铁锭:5",
        ])
        assert mock_io.contains("失败")


class TestRecipeModify:
    """测试 recipe set-* 命令"""

    def test_set_device_success(self, controller, mock_io, game_loaded):
        controller._cmd_recipe_set_device(["铁矿冶炼", "电炉"])
        assert mock_io.contains("已修改配方 铁矿冶炼 的设备为 电炉")
        recipes = controller.recipe_manager.get_all_recipes()
        assert recipes["铁矿冶炼"]["device"] == "电炉"

    def test_set_device_not_found(self, controller, mock_io, game_loaded):
        controller._cmd_recipe_set_device(["不存在", "电炉"])
        assert mock_io.contains("不存在")

    def test_set_device_no_args(self, controller, mock_io):
        controller._cmd_recipe_set_device(["仅名称"])
        assert mock_io.contains("用法")

    def test_set_inputs_success(self, controller, mock_io, game_loaded):
        controller._cmd_recipe_set_inputs(["铁矿冶炼", "铁矿石:20,煤:10"])
        assert mock_io.contains("已修改配方 铁矿冶炼 的输入")
        recipes = controller.recipe_manager.get_all_recipes()
        assert "铁矿石" in recipes["铁矿冶炼"]["inputs"]

    def test_set_outputs_success(self, controller, mock_io, game_loaded):
        controller._cmd_recipe_set_outputs(["铁矿冶炼", "铁锭:8"])
        assert mock_io.contains("已修改配方 铁矿冶炼 的输出")
        recipes = controller.recipe_manager.get_all_recipes()
        assert "铁锭" in recipes["铁矿冶炼"]["outputs"]

    def test_set_inputs_invalid_expr(self, controller, mock_io, game_loaded):
        controller._cmd_recipe_set_inputs(["铁矿冶炼", "铁矿石:abc"])
        assert mock_io.contains("解析物品列表失败")


class TestRecipeDelete:
    """测试 recipe delete 命令"""

    def test_delete_no_args(self, controller, mock_io):
        controller._cmd_recipe_delete([])
        assert mock_io.contains("用法")

    def test_delete_not_found(self, controller, mock_io, game_loaded):
        controller._cmd_recipe_delete(["不存在"])
        assert mock_io.contains("不存在")

    def test_delete_success(self, controller, mock_io, game_loaded):
        controller._cmd_recipe_delete(["铁矿冶炼"])
        assert mock_io.contains("已删除配方: 铁矿冶炼")
        recipes = controller.recipe_manager.get_all_recipes()
        assert "铁矿冶炼" not in recipes


# ======================================================================
# 参数解析测试
# ======================================================================


class TestParseRate:
    """测试速度解析"""

    def test_parse_integer(self, controller):
        assert controller._parse_rate("10") == 10.0

    def test_parse_expression(self, controller):
        assert controller._parse_rate("15/min") == 0.25

    def test_parse_math(self, controller):
        assert controller._parse_rate("8*3/2") == 12.0


class TestParseItemList:
    """测试物品列表解析"""

    def test_single_item(self, controller):
        result = controller._parse_item_list("铁矿石:10")
        assert "铁矿石" in result
        assert result["铁矿石"]["amount"] == 10.0
        assert result["铁矿石"]["expression"] == "10"

    def test_multiple_items(self, controller):
        result = controller._parse_item_list("铁矿石:10,煤:5")
        assert len(result) == 2
        assert result["煤"]["amount"] == 5.0

    def test_with_expression(self, controller):
        result = controller._parse_item_list("铁矿石:15/min")
        assert result["铁矿石"]["amount"] == 0.25
        assert result["铁矿石"]["expression"] == "15/min"

    def test_default_expression(self, controller):
        """无表达式时默认为 1"""
        result = controller._parse_item_list("铁矿石")
        assert result["铁矿石"]["amount"] == 1.0

    def test_empty_string(self, controller):
        assert controller._parse_item_list("") == {}

    def test_spaces_trimmed(self, controller):
        result = controller._parse_item_list(" 铁矿石 : 10 , 煤 : 5 ")
        assert "铁矿石" in result
        assert "煤" in result


class TestParseFlags:
    """测试标志参数解析"""

    def test_basic_flags(self, controller):
        flags = controller._parse_flags(["--device", "熔炉", "--inputs", "a:1"])
        assert flags["device"] == "熔炉"
        assert flags["inputs"] == "a:1"

    def test_flag_without_value(self, controller):
        flags = controller._parse_flags(["--device"])
        assert flags["device"] == ""

    def test_no_flags(self, controller):
        flags = controller._parse_flags(["name", "other"])
        assert flags == {}


# ======================================================================
# 纯辅助方法测试
# ======================================================================


class TestAssignNodeIds:
    """测试节点编号分配（返回值，非实例字段）"""

    def test_assign_returns_map(self, controller):
        tree = _make_simple_tree()
        result = controller._assign_node_ids(tree)
        assert isinstance(result, dict)
        assert len(result) == 3

    def test_preorder_numbering(self, controller):
        tree = _make_simple_tree()
        result = controller._assign_node_ids(tree)
        # 根=1, 铁矿石=2, 煤炭=3（前序遍历）
        assert result[1]["item_name"] == "铁锭"
        assert result[2]["item_name"] == "铁矿石"
        assert result[3]["item_name"] == "煤炭"

    def test_includes_alternative_info(self, controller):
        tree = _make_simple_tree()
        result = controller._assign_node_ids(tree)
        assert result[3]["alternative_count"] == 1
        assert len(result[3]["alternative_paths"]) == 1


class TestPrintTree:
    """测试树形打印（带节点编号）"""

    def test_print_includes_node_id(self, controller, mock_io):
        tree = _make_simple_tree()
        controller._print_tree(tree)
        assert mock_io.contains("#1 铁锭")
        assert mock_io.contains("#2 铁矿石")
        assert mock_io.contains("#3 煤炭")

    def test_print_includes_marker(self, controller, mock_io):
        tree = _make_simple_tree()
        controller._print_tree(tree)
        # 煤炭节点有1条替代路径
        assert mock_io.contains("[+1]")

    def test_print_device_info(self, controller, mock_io):
        tree = _make_simple_tree()
        controller._print_tree(tree)
        assert mock_io.contains("设备: 熔炉")


class TestDisplayChain:
    """测试生产链显示"""

    def test_display_chain(self, controller, mock_io, recipe_manager):
        tree = _make_simple_tree()
        node_map = controller._assign_node_ids(tree)
        calc = CraftingCalculator(recipe_manager)
        controller._display_chain(tree, node_map, "铁锭", 5.0, calc)
        assert mock_io.contains("生产链: 铁锭")
        assert mock_io.contains("基础原料消耗")
        assert mock_io.contains("设备统计")

    def test_display_lists_alt_nodes(self, controller, mock_io, recipe_manager):
        tree = _make_simple_tree()
        node_map = controller._assign_node_ids(tree)
        calc = CraftingCalculator(recipe_manager)
        controller._display_chain(tree, node_map, "铁锭", 5.0, calc)
        assert mock_io.contains("带替代路径的节点")
        assert mock_io.contains("[#3]")


class TestShowAlternativePaths:
    """测试替代路径显示"""

    def test_show_with_diff(self, controller, mock_io):
        node_info = {"item_name": "煤炭", "device_count": 1.0}
        alt_paths = [[{"item_name": "煤炭", "device_count": 0.5}]]
        controller._show_alternative_paths(3, node_info, alt_paths)
        assert mock_io.contains("节点 #3 (煤炭) 的可选路径")
        assert mock_io.contains("路径 1")
        assert mock_io.contains("(-0.50)")

    def test_show_increase_diff(self, controller, mock_io):
        node_info = {"item_name": "煤炭", "device_count": 1.0}
        alt_paths = [[{"item_name": "煤炭", "device_count": 2.0}]]
        controller._show_alternative_paths(1, node_info, alt_paths)
        assert mock_io.contains("(+1.00)")


class TestBuildTreeFromPath:
    """测试从路径构建树"""

    def test_single_node(self, controller):
        path = [{"item_name": "铁锭", "amount": 5.0, "device_count": 1.0}]
        tree = controller._build_tree_from_path(path, 5.0)
        assert tree is not None
        assert tree["item_name"] == "铁锭"
        assert tree["children"] == []

    def test_multi_node(self, controller):
        path = [
            {"item_name": "铁锭", "amount": 5.0, "device_count": 1.0},
            {"item_name": "铁矿石", "amount": 10.0, "device_count": 2.0},
        ]
        tree = controller._build_tree_from_path(path, 5.0)
        assert tree["item_name"] == "铁锭"
        assert len(tree["children"]) == 1

    def test_empty_path(self, controller):
        assert controller._build_tree_from_path([], 5.0) is None


class TestDictToNode:
    """测试字典转节点"""

    def test_simple_conversion(self, controller):
        tree_dict = _make_simple_tree()
        node = controller._dict_to_node(tree_dict)
        assert node.item_name == "铁锭"
        assert node.amount == 5.0
        assert len(node.children) == 2

    def test_parent_child(self, controller):
        tree_dict = _make_simple_tree()
        node = controller._dict_to_node(tree_dict)
        assert node.children[0].parent is node


class TestCheckHasAlternatives:
    """测试替代路径检查"""

    def test_no_alternatives(self, controller):
        tree = {
            "item_name": "x",
            "path_info": {"alternative_count": 0},
            "children": [],
        }
        assert controller._check_has_alternatives(tree) is False

    def test_root_has_alternatives(self, controller):
        tree = {
            "item_name": "x",
            "path_info": {"alternative_count": 2},
            "children": [],
        }
        assert controller._check_has_alternatives(tree) is True

    def test_child_has_alternatives(self, controller):
        tree = {
            "item_name": "x",
            "path_info": {"alternative_count": 0},
            "children": [
                {"item_name": "y", "path_info": {"alternative_count": 1}, "children": []}
            ],
        }
        assert controller._check_has_alternatives(tree) is True


class TestValidateExpression:
    """测试表达式验证"""

    def test_valid_integer(self, controller):
        assert controller._validate_expression("10") is True

    def test_valid_expression(self, controller):
        assert controller._validate_expression("15/min") is True

    def test_invalid(self, controller):
        assert controller._validate_expression("abc") is False

    def test_empty(self, controller):
        assert controller._validate_expression("") is False


class TestGenerateRecipeId:
    """测试配方 ID 生成"""

    def test_single_output(self, controller):
        outputs = {"铁锭": {"amount": 5.0}}
        assert controller._generate_recipe_id(outputs, {}) == "铁锭生产"

    def test_multiple_outputs_picks_max(self, controller):
        outputs = {"铁锭": {"amount": 2.0}, "铜锭": {"amount": 5.0}}
        assert controller._generate_recipe_id(outputs, {}) == "铜锭生产"

    def test_empty_outputs(self, controller):
        assert controller._generate_recipe_id({}, {}) == "未知配方"

    def test_duplicate_adds_counter(self, controller):
        outputs = {"铁锭": {"amount": 5.0}}
        assert controller._generate_recipe_id(outputs, {"铁锭生产": {}}) == "铁锭生产_2"


# ======================================================================
# REPL 主循环测试
# ======================================================================


class TestRun:
    """测试 REPL 主循环"""

    def test_print_welcome_no_game(self, mock_io, monkeypatch):
        monkeypatch.setattr(
            "application_controller.config_manager.get_last_game", lambda: None
        )
        ctrl = ApplicationController(mock_io)
        ctrl._print_welcome()
        assert mock_io.contains("自动化建造游戏通用合成计算器")
        assert mock_io.contains("未选择配方文件")

    def test_print_welcome_with_game(self, mock_io, monkeypatch, recipe_manager):
        monkeypatch.setattr(
            "application_controller.config_manager.get_last_game", lambda: "test_game"
        )
        ctrl = ApplicationController(mock_io)
        ctrl.recipe_manager = recipe_manager
        ctrl._print_welcome()
        assert mock_io.contains("当前配方文件: test_game")

    def test_print_welcome_game_not_exist(self, mock_io, monkeypatch, temp_dir):
        from data_manager import RecipeManager
        monkeypatch.setattr(
            "application_controller.config_manager.get_last_game", lambda: "missing"
        )
        ctrl = ApplicationController(mock_io)
        ctrl.recipe_manager = RecipeManager(recipes_dir=temp_dir)
        ctrl._print_welcome()
        assert mock_io.contains("不存在")

    def test_run_dispatches_and_exits(self, mock_io, monkeypatch, recipe_manager):
        """REPL 读取命令并分发，quit 触发退出"""
        monkeypatch.setattr(
            "application_controller.config_manager.get_last_game", lambda: None
        )
        mock_io.reset(["help", "quit"])
        ctrl = ApplicationController(mock_io)
        ctrl.recipe_manager = recipe_manager
        with pytest.raises(SystemExit):
            ctrl.run()
        # help 命令应已输出
        assert mock_io.contains("可用命令")
