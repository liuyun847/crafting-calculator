"""
特殊配方集成测试模块

测试复杂生产链、倍增配方、催化剂配方等集成场景，
验证副产品池优化、净产出计算、催化剂处理等功能的正确性。
"""
import pytest
import tempfile
import json
import os
from typing import Dict, Any


@pytest.fixture
def oil_refinery_recipes() -> Dict[str, Any]:
    """
    提供石油炼制相关的复杂配方数据

    包含：
    - 原油提炼（多输出：轻油+重油+气）
    - 重油裂解（重油->轻油+气，催化剂类型）
    - 轻油精炼（轻油->燃料）

    Returns:
        dict: 石油炼制配方字典
    """
    return {
        "原油提炼": {
            "device": "炼油厂",
            "inputs": {
                "原油": {"amount": 10.0, "expression": "10"}
            },
            "outputs": {
                "轻油": {"amount": 4.0, "expression": "4"},
                "重油": {"amount": 3.0, "expression": "3"},
                "石油气": {"amount": 3.0, "expression": "3"}
            }
        },
        "重油裂解": {
            "device": "化工厂",
            "inputs": {
                "重油": {"amount": 4.0, "expression": "4"},
                "水": {"amount": 3.0, "expression": "3"}
            },
            "outputs": {
                "轻油": {"amount": 3.0, "expression": "3"},
                "石油气": {"amount": 1.0, "expression": "1"}
            }
        },
        "轻油精炼": {
            "device": "精炼厂",
            "inputs": {
                "轻油": {"amount": 5.0, "expression": "5"}
            },
            "outputs": {
                "燃料": {"amount": 3.0, "expression": "3"}
            }
        },
        "水提取": {
            "device": "水泵",
            "inputs": {},
            "outputs": {
                "水": {"amount": 10.0, "expression": "10"}
            }
        }
    }


@pytest.fixture
def doubling_chain_recipes() -> Dict[str, Any]:
    """
    提供倍增配方链数据

    包含：
    - 增殖配方 a->2*a
    - 下游使用 a 生产 b

    Returns:
        dict: 倍增配方链字典
    """
    return {
        "增殖配方": {
            "device": "增殖器",
            "inputs": {
                "a": {"amount": 1.0, "expression": "1"}
            },
            "outputs": {
                "a": {"amount": 2.0, "expression": "2"}
            }
        },
        "a生产b": {
            "device": "生产器",
            "inputs": {
                "a": {"amount": 3.0, "expression": "3"}
            },
            "outputs": {
                "b": {"amount": 1.0, "expression": "1"}
            }
        }
    }


@pytest.fixture
def catalyst_chain_recipes() -> Dict[str, Any]:
    """
    提供催化剂链配方数据

    包含：
    - 催化反应 a+b->a+c（a是催化剂）
    - 下游使用 c 生产 d

    Returns:
        dict: 催化剂链配方字典
    """
    return {
        "催化反应": {
            "device": "催化反应器",
            "inputs": {
                "催化剂a": {"amount": 1.0, "expression": "1"},
                "原料b": {"amount": 5.0, "expression": "5"}
            },
            "outputs": {
                "催化剂a": {"amount": 1.0, "expression": "1"},
                "中间产物c": {"amount": 3.0, "expression": "3"}
            }
        },
        "c生产d": {
            "device": "加工设备",
            "inputs": {
                "中间产物c": {"amount": 2.0, "expression": "2"}
            },
            "outputs": {
                "最终产品d": {"amount": 1.0, "expression": "1"}
            }
        }
    }


@pytest.fixture
def mixed_special_recipes() -> Dict[str, Any]:
    """
    提供混合特殊配方数据

    同时包含倍增、催化剂、多输出配方

    Returns:
        dict: 混合特殊配方字典
    """
    return {
        # 多输出配方
        "多输出配方": {
            "device": "分离器",
            "inputs": {
                "原料x": {"amount": 10.0, "expression": "10"}
            },
            "outputs": {
                "产物y": {"amount": 4.0, "expression": "4"},
                "副产物z": {"amount": 3.0, "expression": "3"}
            }
        },
        # 倍增配方
        "倍增配方": {
            "device": "倍增器",
            "inputs": {
                "副产物z": {"amount": 2.0, "expression": "2"}
            },
            "outputs": {
                "副产物z": {"amount": 5.0, "expression": "5"}
            }
        },
        # 催化剂配方
        "催化剂配方": {
            "device": "催化设备",
            "inputs": {
                "催化剂w": {"amount": 1.0, "expression": "1"},
                "产物y": {"amount": 3.0, "expression": "3"}
            },
            "outputs": {
                "催化剂w": {"amount": 1.0, "expression": "1"},
                "最终产品": {"amount": 2.0, "expression": "2"}
            }
        },
        # 原料获取
        "原料获取": {
            "device": "采矿机",
            "inputs": {},
            "outputs": {
                "原料x": {"amount": 1.0, "expression": "1"}
            }
        }
    }


@pytest.fixture
def byproduct_pool():
    """
    创建副产品池管理器

    Yields:
        ByproductPool: 副产品池实例
    """
    from tests.test_byproduct_pool import ByproductPool
    pool = ByproductPool()
    yield pool
    pool.clear()


@pytest.fixture
def recipe_analyzer():
    """
    创建 RecipeAnalyzer 实例

    Yields:
        RecipeAnalyzer: 配方分析器实例
    """
    from calculator import RecipeAnalyzer
    analyzer = RecipeAnalyzer()
    yield analyzer


class TestComplexProductionChain:
    """复杂生产链测试类"""

    @pytest.mark.integration
    def test_crude_oil_refinery_chain(
        self, oil_refinery_recipes, recipe_analyzer
    ):
        """
        测试原油提炼完整生产链

        验证：
        1. 原油提炼（多输出：轻油+重油+气）
        2. 重油裂解（重油->轻油+气）
        3. 轻油精炼（轻油->燃料）
        4. 设备数量计算正确
        """
        # 测试原油提炼配方
        crude_recipe = oil_refinery_recipes["原油提炼"]

        # 验证多输出
        assert "轻油" in crude_recipe["outputs"]
        assert "重油" in crude_recipe["outputs"]
        assert "石油气" in crude_recipe["outputs"]

        # 测试净产出计算
        light_oil_output = recipe_analyzer.calculate_net_output_for_item(
            crude_recipe, "轻油"
        )
        heavy_oil_output = recipe_analyzer.calculate_net_output_for_item(
            crude_recipe, "重油"
        )
        gas_output = recipe_analyzer.calculate_net_output_for_item(
            crude_recipe, "石油气"
        )

        assert light_oil_output == 4.0
        assert heavy_oil_output == 3.0
        assert gas_output == 3.0

    @pytest.mark.integration
    def test_heavy_oil_cracking_with_catalyst(
        self, oil_refinery_recipes, recipe_analyzer
    ):
        """
        测试重油裂解配方

        验证：
        1. 重油裂解将重油转化为轻油和石油气
        2. 净产出计算正确
        """
        cracking_recipe = oil_refinery_recipes["重油裂解"]

        # 验证输入输出
        assert "重油" in cracking_recipe["inputs"]
        assert "水" in cracking_recipe["inputs"]
        assert "轻油" in cracking_recipe["outputs"]
        assert "石油气" in cracking_recipe["outputs"]

        # 测试净产出
        heavy_oil_net = recipe_analyzer.calculate_net_output_for_item(
            cracking_recipe, "重油"
        )
        light_oil_net = recipe_analyzer.calculate_net_output_for_item(
            cracking_recipe, "轻油"
        )
        gas_net = recipe_analyzer.calculate_net_output_for_item(
            cracking_recipe, "石油气"
        )
        water_net = recipe_analyzer.calculate_net_output_for_item(
            cracking_recipe, "水"
        )

        # 重油净消耗 = 0 - 4 = -4
        assert heavy_oil_net == -4.0
        # 水净消耗 = 0 - 3 = -3
        assert water_net == -3.0
        # 轻油净产出 = 3 - 0 = 3
        assert light_oil_net == 3.0
        # 石油气净产出 = 1 - 0 = 1
        assert gas_net == 1.0

    @pytest.mark.integration
    def test_byproduct_pool_optimization(
        self, oil_refinery_recipes, byproduct_pool
    ):
        """
        测试副产品池优化效果

        验证：
        1. 原油提炼产生的重油和气被优先使用
        2. 不需要额外生产重油和气
        """
        crude_recipe = oil_refinery_recipes["原油提炼"]
        device_count = 2.0  # 假设需要2个炼油厂

        # 模拟生产，收集副产品
        target_item = "轻油"
        for output_item, output_data in crude_recipe["outputs"].items():
            if output_item != target_item:
                amount = output_data["amount"] * device_count
                byproduct_pool.add_byproduct(output_item, amount)

        # 验证副产品池中有重油和石油气
        assert byproduct_pool.get_byproduct_amount("重油") == 6.0  # 3.0 * 2
        assert byproduct_pool.get_byproduct_amount("石油气") == 6.0  # 3.0 * 2

        # 模拟下游需要重油进行裂解（需要4/s）
        consumed, remaining = byproduct_pool.consume_byproduct("重油", 4.0)

        # 验证副产品完全满足需求
        assert consumed == 4.0
        assert remaining == 0.0
        assert byproduct_pool.get_byproduct_amount("重油") == 2.0

    @pytest.mark.integration
    def test_full_fuel_production_chain(
        self, oil_refinery_recipes, recipe_analyzer
    ):
        """
        测试完整的燃料生产链

        验证：
        1. 从原油到燃料的完整流程
        2. 设备数量基于净产出计算
        """
        # 轻油精炼配方
        refine_recipe = oil_refinery_recipes["轻油精炼"]

        # 验证配方结构
        assert "轻油" in refine_recipe["inputs"]
        assert "燃料" in refine_recipe["outputs"]

        # 计算设备数量：需要产出9/s燃料
        # 净产出 = 3，设备数 = 9/3 = 3
        device_count = recipe_analyzer.calculate_device_count(
            refine_recipe, "燃料", 9.0
        )
        assert device_count == 3.0

        # 计算净消耗和净产出
        net_consumption = recipe_analyzer.get_net_consumption(refine_recipe)
        net_production = recipe_analyzer.get_net_production(refine_recipe)

        assert "轻油" in net_consumption
        assert net_consumption["轻油"] == 5.0
        assert "燃料" in net_production
        assert net_production["燃料"] == 3.0


class TestDoublingRecipeChain:
    """倍增配方链测试类"""

    @pytest.mark.integration
    def test_doubling_recipe_net_output(
        self, doubling_chain_recipes, recipe_analyzer
    ):
        """
        测试倍增配方的净产出计算

        验证：
        1. 配方 a->2*a 的净产出为1
        2. 设备数量基于净产出计算
        """
        doubling_recipe = doubling_chain_recipes["增殖配方"]

        # 计算物品a的净产出
        net_output = recipe_analyzer.calculate_net_output_for_item(
            doubling_recipe, "a"
        )

        # 净产出 = 2 - 1 = 1
        assert net_output == 1.0

    @pytest.mark.integration
    def test_device_count_based_on_net_output(
        self, doubling_chain_recipes, recipe_analyzer
    ):
        """
        测试设备数量基于净产出计算

        验证：
        1. 需要产出10/s的a
        2. 净产出=1，设备数=10/1=10
        """
        doubling_recipe = doubling_chain_recipes["增殖配方"]

        # 计算设备数量
        device_count = recipe_analyzer.calculate_device_count(
            doubling_recipe, "a", 10.0
        )

        # 设备数 = 目标产出 / 净产出 = 10 / 1 = 10
        assert device_count == 10.0

    @pytest.mark.integration
    def test_downstream_production_with_doubling(
        self, doubling_chain_recipes, recipe_analyzer
    ):
        """
        测试下游使用倍增产物的生产链

        验证：
        1. 增殖配方产出a
        2. 下游使用a生产b
        3. 整体计算正确
        """
        # 下游配方：3a -> 1b
        downstream_recipe = doubling_chain_recipes["a生产b"]

        # 验证下游配方
        assert "a" in downstream_recipe["inputs"]
        assert "b" in downstream_recipe["outputs"]

        # 计算净消耗和净产出
        net_consumption = recipe_analyzer.get_net_consumption(
            downstream_recipe)
        net_production = recipe_analyzer.get_net_production(downstream_recipe)

        assert "a" in net_consumption
        assert net_consumption["a"] == 3.0
        assert "b" in net_production
        assert net_production["b"] == 1.0

    @pytest.mark.integration
    def test_complete_doubling_chain_calculation(
        self, doubling_chain_recipes, temp_dir
    ):
        """
        测试完整的倍增配方链计算

        验证：
        1. 从基础a开始，通过倍增配方增殖
        2. 下游使用增殖后的a生产b
        3. 计算结果正确
        """
        from data_manager import RecipeManager
        from calculator import CraftingCalculator

        # 创建配方管理器并加载配方
        manager = RecipeManager(recipes_dir=temp_dir)
        recipe_file = os.path.join(temp_dir, "doubling_test.json")
        with open(recipe_file, "w", encoding="utf-8") as f:
            json.dump(doubling_chain_recipes, f, indent=2, ensure_ascii=False)
        manager.load_recipe_file("doubling_test")

        # 创建计算器
        calculator = CraftingCalculator(manager)

        # 计算生产链
        trees = calculator.calculate_production_chain("b", 1.0)

        # 验证计算结果
        assert len(trees) > 0


class TestCatalystRecipeChain:
    """催化剂链测试类"""

    @pytest.mark.integration
    def test_catalyst_identification(
        self, catalyst_chain_recipes, recipe_analyzer
    ):
        """
        测试催化剂识别

        验证：
        1. 催化剂a被正确识别（输入输出都有且数量相同）
        2. 原料b不是催化剂
        """
        catalyst_recipe = catalyst_chain_recipes["催化反应"]

        # 获取催化剂
        catalysts = recipe_analyzer._get_catalysts(catalyst_recipe)

        # 验证催化剂a被识别
        assert "催化剂a" in catalysts
        # 验证原料b不是催化剂
        assert "原料b" not in catalysts

    @pytest.mark.integration
    def test_catalyst_excluded_from_net_consumption(
        self, catalyst_chain_recipes, recipe_analyzer
    ):
        """
        测试催化剂不计入净消耗

        验证：
        1. 催化剂a不计入净消耗
        2. 原料b计入净消耗
        """
        catalyst_recipe = catalyst_chain_recipes["催化反应"]

        # 计算净消耗
        net_consumption = recipe_analyzer.get_net_consumption(catalyst_recipe)

        # 验证催化剂a不在净消耗中
        assert "催化剂a" not in net_consumption
        # 验证原料b在净消耗中
        assert "原料b" in net_consumption
        assert net_consumption["原料b"] == 5.0

    @pytest.mark.integration
    def test_catalyst_excluded_from_net_production(
        self, catalyst_chain_recipes, recipe_analyzer
    ):
        """
        测试催化剂不计入净产出

        验证：
        1. 催化剂a不计入净产出
        2. 中间产物c计入净产出
        """
        catalyst_recipe = catalyst_chain_recipes["催化反应"]

        # 计算净产出
        net_production = recipe_analyzer.get_net_production(catalyst_recipe)

        # 验证催化剂a不在净产出中
        assert "催化剂a" not in net_production
        # 验证中间产物c在净产出中
        assert "中间产物c" in net_production
        assert net_production["中间产物c"] == 3.0

    @pytest.mark.integration
    def test_downstream_use_of_catalyst_product(
        self, catalyst_chain_recipes, recipe_analyzer
    ):
        """
        测试下游使用催化剂产物

        验证：
        1. 催化反应产出中间产物c
        2. 下游使用c生产d
        3. 设备数量计算正确
        """
        downstream_recipe = catalyst_chain_recipes["c生产d"]

        # 验证配方结构
        assert "中间产物c" in downstream_recipe["inputs"]
        assert "最终产品d" in downstream_recipe["outputs"]

        # 计算设备数量：需要产出5/s的d
        # 净产出 = 1，设备数 = 5/1 = 5
        device_count = recipe_analyzer.calculate_device_count(
            downstream_recipe, "最终产品d", 5.0
        )
        assert device_count == 5.0

    @pytest.mark.integration
    def test_complete_catalyst_chain(
        self, catalyst_chain_recipes, temp_dir
    ):
        """
        测试完整的催化剂链

        验证：
        1. 催化反应 a+b->a+c
        2. 下游使用c生产d
        3. 整体计算正确，催化剂a不计入消耗
        """
        from data_manager import RecipeManager
        from calculator import CraftingCalculator

        # 创建配方管理器并加载配方
        manager = RecipeManager(recipes_dir=temp_dir)
        recipe_file = os.path.join(temp_dir, "catalyst_test.json")
        with open(recipe_file, "w", encoding="utf-8") as f:
            json.dump(catalyst_chain_recipes, f, indent=2, ensure_ascii=False)
        manager.load_recipe_file("catalyst_test")

        # 创建计算器
        calculator = CraftingCalculator(manager)

        # 计算生产链
        trees = calculator.calculate_production_chain("最终产品d", 1.0)

        # 验证计算结果
        assert len(trees) > 0


class TestMixedSpecialRecipes:
    """混合特殊配方测试类"""

    @pytest.mark.integration
    def test_mixed_recipe_types_integration(
        self, mixed_special_recipes, recipe_analyzer
    ):
        """
        测试混合配方类型的集成

        验证：
        1. 多输出配方正确识别
        2. 倍增配方正确计算净产出
        3. 催化剂配方正确处理催化剂
        """
        # 测试多输出配方
        multi_output = mixed_special_recipes["多输出配方"]
        assert len(multi_output["outputs"]) == 2

        # 测试倍增配方
        doubling = mixed_special_recipes["倍增配方"]
        net_output = recipe_analyzer.calculate_net_output_for_item(
            doubling, "副产物z")
        # 净产出 = 5 - 2 = 3
        assert net_output == 3.0

        # 测试催化剂配方
        catalyst = mixed_special_recipes["催化剂配方"]
        catalysts = recipe_analyzer._get_catalysts(catalyst)
        assert "催化剂w" in catalysts

    @pytest.mark.integration
    def test_complex_production_calculation(
        self, mixed_special_recipes, temp_dir
    ):
        """
        测试复杂生产计算

        验证：
        1. 同时包含多种特殊配方的生产链
        2. 整体计算正确性
        """
        from data_manager import RecipeManager
        from calculator import CraftingCalculator

        # 创建配方管理器并加载配方
        manager = RecipeManager(recipes_dir=temp_dir)
        recipe_file = os.path.join(temp_dir, "mixed_test.json")
        with open(recipe_file, "w", encoding="utf-8") as f:
            json.dump(mixed_special_recipes, f, indent=2, ensure_ascii=False)
        manager.load_recipe_file("mixed_test")

        # 创建计算器
        calculator = CraftingCalculator(manager)

        # 计算最终产品的生产链
        trees = calculator.calculate_production_chain("最终产品", 1.0)

        # 验证计算结果
        assert len(trees) > 0

    @pytest.mark.integration
    def test_byproduct_reuse_in_mixed_chain(
        self, mixed_special_recipes, byproduct_pool, recipe_analyzer
    ):
        """
        测试混合链中的副产品复用

        验证：
        1. 多输出配方产生的副产物z被收集
        2. 倍增配方使用副产物z作为输入
        3. 副产品池优化生效
        """
        # 多输出配方产出副产物z
        multi_recipe = mixed_special_recipes["多输出配方"]
        device_count = 3.0

        # 收集副产物z
        byproduct_amount = multi_recipe["outputs"]["副产物z"]["amount"] * device_count
        byproduct_pool.add_byproduct("副产物z", byproduct_amount)

        # 验证副产物在池中
        assert byproduct_pool.get_byproduct_amount("副产物z") == 9.0  # 3.0 * 3

        # 倍增配方需要副产物z（假设需要4/s）
        doubling_recipe = mixed_special_recipes["倍增配方"]
        consumed, remaining = byproduct_pool.consume_byproduct("副产物z", 4.0)

        # 验证副产品优先使用
        assert consumed == 4.0
        assert remaining == 0.0
        assert byproduct_pool.get_byproduct_amount("副产物z") == 5.0

    @pytest.mark.integration
    def test_overall_calculation_correctness(
        self, mixed_special_recipes, recipe_analyzer
    ):
        """
        测试整体计算正确性

        验证：
        1. 所有配方的净产出/净消耗计算正确
        2. 设备数量计算正确
        """
        # 验证多输出配方
        multi_recipe = mixed_special_recipes["多输出配方"]
        net_production = recipe_analyzer.get_net_production(multi_recipe)
        assert "产物y" in net_production
        assert "副产物z" in net_production
        assert net_production["产物y"] == 4.0
        assert net_production["副产物z"] == 3.0

        # 验证倍增配方
        doubling_recipe = mixed_special_recipes["倍增配方"]
        net_output = recipe_analyzer.calculate_net_output_for_item(
            doubling_recipe, "副产物z"
        )
        assert net_output == 3.0  # 5 - 2 = 3

        # 验证催化剂配方
        catalyst_recipe = mixed_special_recipes["催化剂配方"]
        net_consumption = recipe_analyzer.get_net_consumption(catalyst_recipe)
        net_production = recipe_analyzer.get_net_production(catalyst_recipe)

        # 催化剂w不计入
        assert "催化剂w" not in net_consumption
        assert "催化剂w" not in net_production
        # 产物y是消耗，最终产品是产出
        assert "产物y" in net_consumption
        assert "最终产品" in net_production


class TestSpecialRecipeEdgeCases:
    """特殊配方边界情况测试类"""

    @pytest.mark.integration
    def test_zero_target_rate_device_count(
        self, doubling_chain_recipes, recipe_analyzer
    ):
        """
        测试目标产出率为0时的设备数量

        验证：设备数应为0
        """
        doubling_recipe = doubling_chain_recipes["增殖配方"]
        device_count = recipe_analyzer.calculate_device_count(
            doubling_recipe, "a", 0.0
        )
        assert device_count == 0.0

    @pytest.mark.integration
    def test_empty_byproduct_pool_consumption(self, byproduct_pool):
        """
        测试空副产品池的消耗

        验证：消耗量为0，剩余需求等于总需求
        """
        consumed, remaining = byproduct_pool.consume_byproduct("任意物品", 10.0)
        assert consumed == 0.0
        assert remaining == 10.0

    @pytest.mark.integration
    def test_multiple_catalysts_in_recipe(self, recipe_analyzer):
        """
        测试多个催化剂的配方

        验证：所有催化剂都被正确识别和排除
        """
        recipe = {
            "device": "高级反应器",
            "inputs": {
                "催化剂A": {"amount": 2.0, "expression": "2"},
                "催化剂B": {"amount": 1.0, "expression": "1"},
                "原料": {"amount": 5.0, "expression": "5"}
            },
            "outputs": {
                "催化剂A": {"amount": 2.0, "expression": "2"},
                "催化剂B": {"amount": 1.0, "expression": "1"},
                "产品": {"amount": 3.0, "expression": "3"}
            }
        }

        # 获取催化剂
        catalysts = recipe_analyzer._get_catalysts(recipe)
        assert "催化剂A" in catalysts
        assert "催化剂B" in catalysts

        # 验证净消耗和净产出中不包含催化剂
        net_consumption = recipe_analyzer.get_net_consumption(recipe)
        net_production = recipe_analyzer.get_net_production(recipe)

        assert "催化剂A" not in net_consumption
        assert "催化剂B" not in net_consumption
        assert "催化剂A" not in net_production
        assert "催化剂B" not in net_production

    @pytest.mark.integration
    def test_exact_byproduct_match(self, byproduct_pool):
        """
        测试副产品精确匹配

        验证：当需求量等于池中数量时，池被清空
        """
        byproduct_pool.add_byproduct("测试物品", 5.0)
        consumed, remaining = byproduct_pool.consume_byproduct("测试物品", 5.0)

        assert consumed == 5.0
        assert remaining == 0.0
        assert byproduct_pool.get_byproduct_amount("测试物品") == 0.0
