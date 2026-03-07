"""
集成测试

测试模块之间的集成和端到端场景
"""

import os
import pytest
from io_interface import TerminalIO, WebIO
from application_controller import ApplicationController
from data_manager import RecipeManager
from calculator import CraftingCalculator
from expression_parser import parse_expression


class TestDataManagerCalculatorIntegration:
    """测试 DataManager 和 Calculator 集成"""

    def test_calculator_with_recipe_manager(self, recipe_manager):
        """测试计算器使用配方管理器"""
        calculator = CraftingCalculator(recipe_manager)

        assert calculator.recipe_manager == recipe_manager
        assert len(calculator.recipes) > 0

    def test_calculator_production_chain(self, recipe_manager):
        """测试计算器生产链计算"""
        calculator = CraftingCalculator(recipe_manager)

        trees = calculator.calculate_production_chain("铁锭", 1.0)

        assert len(trees) > 0
        assert trees[0]["item_name"] == "铁锭"

    def test_calculator_with_complex_recipes(self, complex_recipes):
        """测试计算器使用复杂配方"""
        from data_manager import RecipeManager
        import tempfile
        import os
        import json

        temp_dir = tempfile.mkdtemp()
        recipe_file = os.path.join(temp_dir, "complex.json")

        with open(recipe_file, "w", encoding="utf-8") as f:
            json.dump(complex_recipes, f)

        manager = RecipeManager(recipes_dir=temp_dir)
        manager.load_recipe_file("complex")

        calculator = CraftingCalculator(manager)
        trees = calculator.calculate_production_chain("高级电路板", 1.0)

        assert len(trees) > 0

        import shutil

        shutil.rmtree(temp_dir)


class TestExpressionParserCalculatorIntegration:
    """测试表达式解析器和计算器集成"""

    def test_parse_expression_for_rate(self):
        """测试解析生产速度表达式"""
        rate = parse_expression("15/min")

        assert rate == 0.25

    def test_parse_complex_expression(self):
        """测试解析复杂表达式"""
        rate = parse_expression("5*2/3/min")

        assert rate == pytest.approx(0.05555555555555555)

    def test_parse_expression_with_calculator(self, recipe_manager):
        """测试表达式解析与计算器集成"""
        calculator = CraftingCalculator(recipe_manager)

        rate = parse_expression("15/min")
        trees = calculator.calculate_production_chain("铁锭", rate)

        assert len(trees) > 0


class TestIOControllerIntegration:
    """测试 IO 和控制器集成"""

    def test_terminal_io_controller(self, terminal_io):
        """测试终端 IO 和控制器"""
        controller = ApplicationController(terminal_io)

        assert controller.io == terminal_io

        result = controller.process_command("help")

        assert "output" in result
        assert "prompt" in result

    def test_web_io_controller(self, web_io):
        """测试 Web IO 和控制器"""
        controller = ApplicationController(web_io)

        assert controller.io == web_io

        result = controller.process_command("help")

        assert "output" in result
        assert "prompt" in result

    def test_controller_state_management(self, terminal_io):
        """测试控制器状态管理"""
        controller = ApplicationController(terminal_io)

        assert controller.state == "main_menu"

        # 命令 "1" 会显示游戏列表并进入 select_game 状态
        result = controller.process_command("1")
        assert controller.state == "select_game"

        # 在 select_game 状态下，命令 "5" 是无效选择，会返回主菜单
        result = controller.process_command("5")
        assert controller.state == "main_menu"


class TestEndToEndCalculation:
    """测试端到端计算流程"""

    def test_full_calculation_workflow(self, recipe_manager, terminal_io):
        """测试完整计算工作流"""
        calculator = CraftingCalculator(recipe_manager)

        trees = calculator.calculate_production_chain("铁锭", 1.0)

        assert len(trees) > 0

        tree_dict = trees[0]
        assert tree_dict["item_name"] == "铁锭"
        assert tree_dict["amount"] == 1.0

        raw_materials = calculator.get_raw_materials(
            calculator.build_crafting_tree(
                "铁锭", 1.0, calculator.find_production_paths("铁锭")[0]
            )
        )

        assert len(raw_materials) > 0

    def test_complex_calculation_workflow(self, recipe_manager):
        """测试复杂计算工作流"""
        calculator = CraftingCalculator(recipe_manager)

        trees = calculator.calculate_production_chain("电路板", 1.0)

        assert len(trees) > 0

        tree_dict = trees[0]
        assert tree_dict["item_name"] == "电路板"

        device_stats = calculator.get_device_stats(
            calculator.build_crafting_tree(
                "电路板", 1.0, calculator.find_production_paths("电路板")[0]
            )
        )

        assert len(device_stats) > 0


class TestRecipeManagementWorkflow:
    """测试配方管理工作流"""

    def test_add_and_use_recipe(self, recipe_manager):
        """测试添加并使用配方"""
        recipe_data = {
            "device": "测试设备",
            "inputs": {"原料": {"amount": 1.0, "expression": "1"}},
            "outputs": {"产品": {"amount": 1.0, "expression": "1"}},
        }

        recipe_manager.add_recipe(
            "测试配方",
            recipe_data["device"],
            recipe_data["inputs"],
            recipe_data["outputs"],
        )

        assert "测试配方" in recipe_manager.recipes

        calculator = CraftingCalculator(recipe_manager)
        trees = calculator.calculate_production_chain("产品", 1.0)

        assert len(trees) > 0

    def test_update_and_use_recipe(self, recipe_manager):
        """测试更新并使用配方"""
        recipe_data = {
            "device": "设备",
            "inputs": {"原料": {"amount": 1.0, "expression": "1"}},
            "outputs": {"产品": {"amount": 1.0, "expression": "1"}},
        }

        recipe_manager.add_recipe(
            "更新测试",
            recipe_data["device"],
            recipe_data["inputs"],
            recipe_data["outputs"],
        )

        updated_data = {
            "device": "新设备",
            "inputs": {"新原料": {"amount": 2.0, "expression": "2"}},
            "outputs": {"新产品": {"amount": 1.0, "expression": "1"}},
        }

        recipe_manager.update_recipe(
            "更新测试",
            updated_data["device"],
            updated_data["inputs"],
            updated_data["outputs"],
        )

        recipe = recipe_manager.get_recipe("更新测试")
        assert recipe["device"] == "新设备"

    def test_delete_and_verify_recipe(self, recipe_manager):
        """测试删除并验证配方"""
        recipe_data = {
            "device": "设备",
            "inputs": {"原料": {"amount": 1.0, "expression": "1"}},
            "outputs": {"产品": {"amount": 1.0, "expression": "1"}},
        }

        recipe_manager.add_recipe(
            "删除测试",
            recipe_data["device"],
            recipe_data["inputs"],
            recipe_data["outputs"],
        )

        assert "删除测试" in recipe_manager.recipes

        recipe_manager.delete_recipe("删除测试")

        assert "删除测试" not in recipe_manager.recipes


class TestPathComparisonIntegration:
    """测试路径对比集成"""

    def test_multi_path_calculation(self, recipe_manager):
        """测试多路径计算"""
        calculator = CraftingCalculator(recipe_manager)

        trees = calculator.calculate_production_chain("电路板", 1.0)

        assert len(trees) >= 1

    def test_main_path_selection(self, recipe_manager):
        """测试主路径选择"""
        calculator = CraftingCalculator(recipe_manager)

        trees = calculator.calculate_production_chain("铁锭", 1.0)

        if len(trees) > 1:
            device_counts = [calculator._count_total_devices(tree) for tree in trees]
            assert device_counts[0] <= device_counts[1]


class TestConfigIntegration:
    """测试配置集成"""

    def test_config_with_recipe_manager(self, temp_dir):
        """测试配置与配方管理器集成"""
        from config_manager import ConfigManager

        config_file = os.path.join(temp_dir, "config.json")
        config_manager = ConfigManager(config_file=config_file)

        config_manager.set_last_game("test_game")

        last_game = config_manager.get_last_game()

        assert last_game == "test_game"


class TestErrorHandlingIntegration:
    """测试错误处理集成"""

    def test_invalid_item_calculation(self, recipe_manager):
        """测试无效物品计算"""
        calculator = CraftingCalculator(recipe_manager)

        trees = calculator.calculate_production_chain("不存在的物品", 1.0)

        assert len(trees) == 0

    def test_invalid_expression_parsing(self):
        """测试无效表达式解析"""
        with pytest.raises(ValueError):
            parse_expression("invalid expression")

    def test_invalid_recipe_operations(self, recipe_manager):
        """测试无效配方操作"""
        with pytest.raises(KeyError):
            recipe_manager.get_recipe("不存在的配方")

        with pytest.raises(KeyError):
            recipe_manager.delete_recipe("不存在的配方")


class TestPerformanceIntegration:
    """测试性能集成"""

    def test_large_recipe_set(self, recipe_manager):
        """测试大配方集"""
        for i in range(100):
            recipe_data = {
                "device": f"设备{i}",
                "inputs": {f"原料{i}": {"amount": 1.0, "expression": "1"}},
                "outputs": {f"产品{i}": {"amount": 1.0, "expression": "1"}},
            }

            recipe_manager.add_recipe(
                f"配方{i}",
                recipe_data["device"],
                recipe_data["inputs"],
                recipe_data["outputs"],
            )

        assert len(recipe_manager.recipes) >= 100

    def test_complex_calculation_performance(self, recipe_manager):
        """测试复杂计算性能"""
        calculator = CraftingCalculator(recipe_manager)

        import time

        start_time = time.time()

        trees = calculator.calculate_production_chain("电路板", 1.0)

        end_time = time.time()
        elapsed = end_time - start_time

        assert len(trees) > 0
        assert elapsed < 10.0


class TestDataPersistenceIntegration:
    """测试数据持久化集成"""

    def test_recipe_persistence(self, temp_dir):
        """测试配方持久化"""
        from data_manager import RecipeManager

        manager1 = RecipeManager(recipes_dir=temp_dir)
        manager1.current_game = "test_game"

        recipe_data = {
            "device": "设备",
            "inputs": {"原料": {"amount": 1.0, "expression": "1"}},
            "outputs": {"产品": {"amount": 1.0, "expression": "1"}},
        }

        manager1.add_recipe(
            "持久化测试",
            recipe_data["device"],
            recipe_data["inputs"],
            recipe_data["outputs"],
        )

        manager2 = RecipeManager(recipes_dir=temp_dir)
        manager2.load_recipe_file("test_game")

        assert "持久化测试" in manager2.recipes

    def test_config_persistence(self, temp_dir):
        """测试配置持久化"""
        from config_manager import ConfigManager

        config_file = os.path.join(temp_dir, "config.json")
        manager1 = ConfigManager(config_file=config_file)

        manager1.set_last_game("game1")

        manager2 = ConfigManager(config_file=config_file)

        last_game = manager2.get_last_game()

        assert last_game == "game1"
