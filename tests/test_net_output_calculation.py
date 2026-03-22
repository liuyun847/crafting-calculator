"""
净产出率计算测试

测试 RecipeAnalyzer 类的净产出率计算方法，包括：
1. 同物品净产出计算（倍增配方）
2. 催化剂净消耗排除
3. 设备数量基于净产出计算
4. 损耗配方负净产出
"""
import pytest
from typing import Dict, Any


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


@pytest.fixture
def doubling_recipe() -> Dict[str, Any]:
    """
    倍增配方：a -> 2*a
    输入1个a，输出2个a，净产出应为1

    Returns:
        dict: 倍增配方数据
    """
    return {
        "device": "倍增器",
        "inputs": {
            "a": {"amount": 1.0, "expression": "1"}
        },
        "outputs": {
            "a": {"amount": 2.0, "expression": "2"}
        }
    }


@pytest.fixture
def catalyst_recipe() -> Dict[str, Any]:
    """
    催化剂配方：a + b -> a + c
    a是催化剂，净消耗只计算b

    Returns:
        dict: 催化剂配方数据
    """
    return {
        "device": "化学反应器",
        "inputs": {
            "a": {"amount": 1.0, "expression": "1"},
            "b": {"amount": 5.0, "expression": "5"}
        },
        "outputs": {
            "a": {"amount": 1.0, "expression": "1"},
            "c": {"amount": 3.0, "expression": "3"}
        }
    }


@pytest.fixture
def loss_recipe() -> Dict[str, Any]:
    """
    损耗配方：2*a -> a
    输入2个a，输出1个a，净产出=-1

    Returns:
        dict: 损耗配方数据
    """
    return {
        "device": "损耗设备",
        "inputs": {
            "a": {"amount": 2.0, "expression": "2"}
        },
        "outputs": {
            "a": {"amount": 1.0, "expression": "1"}
        }
    }


@pytest.fixture
def simple_recipe() -> Dict[str, Any]:
    """
    简单配方：原料 -> 产品

    Returns:
        dict: 简单配方数据
    """
    return {
        "device": "生产设备",
        "inputs": {
            "原料": {"amount": 5.0, "expression": "5"}
        },
        "outputs": {
            "产品": {"amount": 3.0, "expression": "3"}
        }
    }


@pytest.mark.unit
class TestCalculateNetOutputForItem:
    """测试 calculate_net_output_for_item 方法"""

    def test_doubling_recipe_same_item(self, recipe_analyzer, doubling_recipe):
        """
        测试同物品净产出计算：配方 a->2*a
        输入1输出2，净产出应为1
        """
        net_output = recipe_analyzer.calculate_net_output_for_item(
            doubling_recipe, "a")

        assert net_output == 1.0

    def test_loss_recipe_same_item(self, recipe_analyzer, loss_recipe):
        """
        测试损耗配方负净产出：配方 2*a->a
        输入2输出1，净产出应为-1
        """
        net_output = recipe_analyzer.calculate_net_output_for_item(
            loss_recipe, "a")

        assert net_output == -1.0

    def test_simple_recipe_output_item(self, recipe_analyzer, simple_recipe):
        """
        测试简单配方的输出物品净产出
        输入5，输出3，净产出应为3
        """
        net_output = recipe_analyzer.calculate_net_output_for_item(
            simple_recipe, "产品")

        assert net_output == 3.0

    def test_simple_recipe_input_item(self, recipe_analyzer, simple_recipe):
        """
        测试简单配方的输入物品净产出
        输入5，输出3，输入物品净产出应为-5
        """
        net_output = recipe_analyzer.calculate_net_output_for_item(
            simple_recipe, "原料")

        assert net_output == -5.0

    def test_catalyst_recipe_catalyst_item(self, recipe_analyzer, catalyst_recipe):
        """
        测试催化剂物品的净产出
        催化剂a输入1输出1，净产出应为0
        """
        net_output = recipe_analyzer.calculate_net_output_for_item(
            catalyst_recipe, "a")

        assert net_output == 0.0

    def test_catalyst_recipe_input_item(self, recipe_analyzer, catalyst_recipe):
        """
        测试催化剂配方中非催化剂输入物品的净产出
        原料b输入5，净产出应为-5
        """
        net_output = recipe_analyzer.calculate_net_output_for_item(
            catalyst_recipe, "b")

        assert net_output == -5.0

    def test_catalyst_recipe_output_item(self, recipe_analyzer, catalyst_recipe):
        """
        测试催化剂配方中输出物品的净产出
        产品c输出3，净产出应为3
        """
        net_output = recipe_analyzer.calculate_net_output_for_item(
            catalyst_recipe, "c")

        assert net_output == 3.0

    def test_nonexistent_item(self, recipe_analyzer, simple_recipe):
        """
        测试配方中不存在的物品
        应返回0
        """
        net_output = recipe_analyzer.calculate_net_output_for_item(
            simple_recipe, "不存在的物品")

        assert net_output == 0.0


@pytest.mark.unit
class TestCalculateDeviceCount:
    """测试 calculate_device_count 方法"""

    def test_doubling_recipe_device_count(self, recipe_analyzer, doubling_recipe):
        """
        测试倍增配方的设备数量计算
        配方 a->2*a，净产出=1
        需要产出10/s，设备数=10/1=10台
        """
        device_count = recipe_analyzer.calculate_device_count(
            doubling_recipe, "a", 10.0
        )

        assert device_count == 10.0

    def test_simple_recipe_device_count(self, recipe_analyzer, simple_recipe):
        """
        测试简单配方的设备数量计算
        配方 原料->产品，净产出=3
        需要产出9/s，设备数=9/3=3台
        """
        device_count = recipe_analyzer.calculate_device_count(
            simple_recipe, "产品", 9.0
        )

        assert device_count == 3.0

    def test_loss_recipe_device_count(self, recipe_analyzer, loss_recipe):
        """
        测试损耗配方的设备数量计算
        配方 2*a->a，净产出=-1（负产出）
        需要产出10/s，设备数=10/(-1)=-10台（表示需要消耗）
        """
        device_count = recipe_analyzer.calculate_device_count(
            loss_recipe, "a", 10.0
        )

        assert device_count == -10.0

    def test_zero_target_rate(self, recipe_analyzer, simple_recipe):
        """
        测试目标产出率为0的情况
        设备数应为0
        """
        device_count = recipe_analyzer.calculate_device_count(
            simple_recipe, "产品", 0.0
        )

        assert device_count == 0.0

    def test_catalyst_recipe_device_count(self, recipe_analyzer, catalyst_recipe):
        """
        测试催化剂配方的设备数量计算
        配方 a+b->a+c，产品c净产出=3
        需要产出9/s，设备数=9/3=3台
        """
        device_count = recipe_analyzer.calculate_device_count(
            catalyst_recipe, "c", 9.0
        )

        assert device_count == 3.0


@pytest.mark.unit
class TestGetNetConsumption:
    """测试 get_net_consumption 方法"""

    def test_simple_recipe_net_consumption(self, recipe_analyzer, simple_recipe):
        """
        测试简单配方的净消耗
        应返回所有输入物品
        """
        net_consumption = recipe_analyzer.get_net_consumption(simple_recipe)

        assert "原料" in net_consumption
        assert net_consumption["原料"] == 5.0

    def test_catalyst_recipe_excludes_catalyst(self, recipe_analyzer, catalyst_recipe):
        """
        测试催化剂配方的净消耗排除催化剂
        a是催化剂，净消耗只应包含b
        """
        net_consumption = recipe_analyzer.get_net_consumption(catalyst_recipe)

        assert "a" not in net_consumption
        assert "b" in net_consumption
        assert net_consumption["b"] == 5.0

    def test_doubling_recipe_net_consumption(self, recipe_analyzer, doubling_recipe):
        """
        测试倍增配方的净消耗
        同物品配方 a->2*a，净消耗 = 1 - 2 = -1 < 0，所以没有净消耗
        """
        net_consumption = recipe_analyzer.get_net_consumption(doubling_recipe)

        # 倍增配方没有净消耗（产出大于消耗）
        assert "a" not in net_consumption

    def test_loss_recipe_net_consumption(self, recipe_analyzer, loss_recipe):
        """
        测试损耗配方的净消耗
        同物品配方 2*a->a，净消耗 = 2 - 1 = 1 > 0
        """
        net_consumption = recipe_analyzer.get_net_consumption(loss_recipe)

        assert "a" in net_consumption
        assert net_consumption["a"] == 1.0

    def test_empty_input_recipe(self, recipe_analyzer):
        """
        测试无输入配方的净消耗
        应返回空字典
        """
        recipe = {
            "device": "采矿机",
            "inputs": {},
            "outputs": {
                "矿石": {"amount": 1.0, "expression": "1"}
            }
        }

        net_consumption = recipe_analyzer.get_net_consumption(recipe)

        assert net_consumption == {}


@pytest.mark.unit
class TestGetNetProduction:
    """测试 get_net_production 方法"""

    def test_simple_recipe_net_production(self, recipe_analyzer, simple_recipe):
        """
        测试简单配方的净产出
        应返回所有输出物品
        """
        net_production = recipe_analyzer.get_net_production(simple_recipe)

        assert "产品" in net_production
        assert net_production["产品"] == 3.0

    def test_catalyst_recipe_excludes_catalyst(self, recipe_analyzer, catalyst_recipe):
        """
        测试催化剂配方的净产出排除催化剂
        a是催化剂，净产出只应包含c
        """
        net_production = recipe_analyzer.get_net_production(catalyst_recipe)

        assert "a" not in net_production
        assert "c" in net_production
        assert net_production["c"] == 3.0

    def test_doubling_recipe_net_production(self, recipe_analyzer, doubling_recipe):
        """
        测试倍增配方的净产出
        同物品配方，输出a净产出应为2-1=1
        """
        net_production = recipe_analyzer.get_net_production(doubling_recipe)

        assert "a" in net_production
        assert net_production["a"] == 1.0

    def test_loss_recipe_net_production(self, recipe_analyzer, loss_recipe):
        """
        测试损耗配方的净产出
        同物品配方，输出a净产出应为1-2=-1
        """
        net_production = recipe_analyzer.get_net_production(loss_recipe)

        assert "a" in net_production
        assert net_production["a"] == -1.0

    def test_empty_output_recipe(self, recipe_analyzer):
        """
        测试无输出配方的净产出
        应返回空字典
        """
        recipe = {
            "device": "销毁器",
            "inputs": {
                "废料": {"amount": 1.0, "expression": "1"}
            },
            "outputs": {}
        }

        net_production = recipe_analyzer.get_net_production(recipe)

        assert net_production == {}


@pytest.mark.unit
class TestNetOutputEdgeCases:
    """测试净产出计算的边界情况"""

    def test_multiple_catalysts(self, recipe_analyzer):
        """
        测试多个催化剂的配方
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

        net_consumption = recipe_analyzer.get_net_consumption(recipe)
        net_production = recipe_analyzer.get_net_production(recipe)

        # 催化剂应被排除
        assert "催化剂A" not in net_consumption
        assert "催化剂B" not in net_consumption
        assert "催化剂A" not in net_production
        assert "催化剂B" not in net_production

        # 原料和产品应被包含
        assert "原料" in net_consumption
        assert "产品" in net_production

    def test_different_input_output_amounts_same_item(self, recipe_analyzer):
        """
        测试同物品输入输出量不同的配方
        """
        recipe = {
            "device": "精炼器",
            "inputs": {
                "a": {"amount": 3.0, "expression": "3"}
            },
            "outputs": {
                "a": {"amount": 5.0, "expression": "5"}
            }
        }

        net_output = recipe_analyzer.calculate_net_output_for_item(recipe, "a")

        # 净产出 = 5 - 3 = 2
        assert net_output == 2.0

    def test_zero_net_output(self, recipe_analyzer):
        """
        测试净产出为0的配方（纯催化剂）
        """
        recipe = {
            "device": "纯催化设备",
            "inputs": {
                "催化剂": {"amount": 2.0, "expression": "2"},
                "原料": {"amount": 5.0, "expression": "5"}
            },
            "outputs": {
                "催化剂": {"amount": 2.0, "expression": "2"}
            }
        }

        net_production = recipe_analyzer.get_net_production(recipe)

        # 没有净产出（只有催化剂输出）
        assert net_production == {}
