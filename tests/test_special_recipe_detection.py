"""
特殊配方检测测试

测试 RecipeAnalyzer 类对特殊配方的识别和分析能力
"""
import pytest
from typing import Dict, Any
from calculator import RecipeAnalyzer, RecipeType


@pytest.fixture
def analyzer():
    """创建 RecipeAnalyzer 实例"""
    return RecipeAnalyzer()


@pytest.fixture
def doubling_recipe() -> Dict[str, Any]:
    """
    倍增配方: a -> 2*a

    输入 a=1/s，输出 a=2/s
    """
    return {
        "name": "倍增配方",
        "device": "倍增器",
        "inputs": {
            "a": {"amount": 1.0, "expression": "1"}
        },
        "outputs": {
            "a": {"amount": 2.0, "expression": "2"}
        }
    }


@pytest.fixture
def lossy_recipe() -> Dict[str, Any]:
    """
    损耗配方: 2*a -> a

    输入 a=2/s，输出 a=1/s
    """
    return {
        "name": "损耗配方",
        "device": "损耗器",
        "inputs": {
            "a": {"amount": 2.0, "expression": "2"}
        },
        "outputs": {
            "a": {"amount": 1.0, "expression": "1"}
        }
    }


@pytest.fixture
def catalyst_recipe() -> Dict[str, Any]:
    """
    催化剂配方: a + b -> a + c

    输入 a=1, b=2，输出 a=1, c=3
    """
    return {
        "name": "催化剂配方",
        "device": "催化反应器",
        "inputs": {
            "a": {"amount": 1.0, "expression": "1"},
            "b": {"amount": 2.0, "expression": "2"}
        },
        "outputs": {
            "a": {"amount": 1.0, "expression": "1"},
            "c": {"amount": 3.0, "expression": "3"}
        }
    }


@pytest.fixture
def invalid_zero_output_recipe() -> Dict[str, Any]:
    """
    无效配方（零产出）: a -> a

    输入 a=1，输出 a=1（净产出为0）
    """
    return {
        "name": "无效零产出配方",
        "device": "无效设备",
        "inputs": {
            "a": {"amount": 1.0, "expression": "1"}
        },
        "outputs": {
            "a": {"amount": 1.0, "expression": "1"}
        }
    }


@pytest.fixture
def invalid_negative_output_recipe() -> Dict[str, Any]:
    """
    无效配方（负产出）: 2*a -> a

    输入 a=2，输出 a=1（净产出为负）
    """
    return {
        "name": "无效负产出配方",
        "device": "无效设备",
        "inputs": {
            "a": {"amount": 2.0, "expression": "2"}
        },
        "outputs": {
            "a": {"amount": 1.0, "expression": "1"}
        }
    }


@pytest.mark.unit
class TestDoublingRecipe:
    """测试倍增配方检测"""

    def test_analyze_doubling_recipe(self, analyzer, doubling_recipe):
        """测试分析倍增配方类型"""
        result = analyzer.analyze_recipe(doubling_recipe)
        assert result["type"] == RecipeType.DOUBLING
        assert "a" in result["catalysts"]
        assert result["is_valid"] is True

    def test_calculate_net_output_doubling(self, analyzer, doubling_recipe):
        """测试计算倍增配方净产出"""
        net_output = analyzer.calculate_net_output_for_item(
            doubling_recipe, "a")
        assert net_output == 1.0  # 2.0 - 1.0 = 1.0

    def test_is_valid_production_doubling(self, analyzer, doubling_recipe):
        """测试倍增配方有效性验证"""
        assert analyzer.is_valid_production_recipe(doubling_recipe) is True


@pytest.mark.unit
class TestLossyRecipe:
    """测试损耗配方检测"""

    def test_analyze_lossy_recipe(self, analyzer, lossy_recipe):
        """测试分析损耗配方类型"""
        result = analyzer.analyze_recipe(lossy_recipe)
        assert result["type"] == RecipeType.LOSSY
        assert "a" in result["catalysts"]
        assert result["is_valid"] is False  # 损耗配方没有正净产出

    def test_calculate_net_output_lossy(self, analyzer, lossy_recipe):
        """测试计算损耗配方净产出"""
        net_output = analyzer.calculate_net_output_for_item(lossy_recipe, "a")
        assert net_output == -1.0  # 1.0 - 2.0 = -1.0

    def test_is_valid_production_lossy(self, analyzer, lossy_recipe):
        """测试损耗配方有效性验证"""
        assert analyzer.is_valid_production_recipe(lossy_recipe) is False


@pytest.mark.unit
class TestCatalystRecipe:
    """测试催化剂配方检测"""

    def test_analyze_catalyst_recipe(self, analyzer, catalyst_recipe):
        """测试分析催化剂配方类型"""
        result = analyzer.analyze_recipe(catalyst_recipe)
        assert result["type"] == RecipeType.CATALYST
        assert "a" in result["catalysts"]
        assert result["is_valid"] is True

    def test_identify_catalysts(self, analyzer, catalyst_recipe):
        """测试识别催化剂"""
        catalysts = analyzer._get_catalysts(catalyst_recipe)
        assert "a" in catalysts
        assert "b" not in catalysts

    def test_calculate_net_output_catalyst(self, analyzer, catalyst_recipe):
        """测试计算催化剂配方净产出"""
        net_output_a = analyzer.calculate_net_output_for_item(
            catalyst_recipe, "a")
        net_output_b = analyzer.calculate_net_output_for_item(
            catalyst_recipe, "b")
        net_output_c = analyzer.calculate_net_output_for_item(
            catalyst_recipe, "c")
        assert net_output_a == 0.0  # 催化剂，净产出为0
        assert net_output_b == -2.0  # 消耗2个b
        assert net_output_c == 3.0  # 产出3个c

    def test_is_valid_production_catalyst(self, analyzer, catalyst_recipe):
        """测试催化剂配方有效性验证"""
        assert analyzer.is_valid_production_recipe(catalyst_recipe) is True


@pytest.mark.unit
class TestInvalidRecipe:
    """测试无效配方检测"""

    def test_analyze_zero_output_recipe(self, analyzer, invalid_zero_output_recipe):
        """测试分析零产出配方"""
        result = analyzer.analyze_recipe(invalid_zero_output_recipe)
        assert result["type"] == RecipeType.INVALID
        assert result["is_valid"] is False

    def test_analyze_negative_output_recipe(self, analyzer, invalid_negative_output_recipe):
        """测试分析负产出配方"""
        result = analyzer.analyze_recipe(invalid_negative_output_recipe)
        assert result["type"] == RecipeType.LOSSY  # 被识别为损耗配方
        assert result["is_valid"] is False

    def test_calculate_net_output_zero(self, analyzer, invalid_zero_output_recipe):
        """测试计算零产出配方净产出"""
        net_output = analyzer.calculate_net_output_for_item(
            invalid_zero_output_recipe, "a")
        assert net_output == 0.0  # 1.0 - 1.0 = 0.0

    def test_calculate_net_output_negative(self, analyzer, invalid_negative_output_recipe):
        """测试计算负产出配方净产出"""
        net_output = analyzer.calculate_net_output_for_item(
            invalid_negative_output_recipe, "a")
        assert net_output == -1.0  # 1.0 - 2.0 = -1.0

    def test_is_valid_production_invalid(self, analyzer, invalid_zero_output_recipe, invalid_negative_output_recipe):
        """测试无效配方有效性验证"""
        assert analyzer.is_valid_production_recipe(
            invalid_zero_output_recipe) is False
        assert analyzer.is_valid_production_recipe(
            invalid_negative_output_recipe) is False


@pytest.mark.unit
class TestRecipeAnalyzerEdgeCases:
    """测试 RecipeAnalyzer 边界情况"""

    def test_empty_recipe(self, analyzer):
        """测试空配方"""
        empty_recipe = {"inputs": {}, "outputs": {}}
        result = analyzer.analyze_recipe(empty_recipe)
        assert result["type"] == RecipeType.INVALID
        assert result["is_valid"] is False

    def test_multiple_catalysts(self, analyzer):
        """测试多个催化剂"""
        recipe = {
            "inputs": {
                "a": {"amount": 1.0, "expression": "1"},
                "b": {"amount": 2.0, "expression": "2"},
                "c": {"amount": 3.0, "expression": "3"}
            },
            "outputs": {
                "a": {"amount": 1.0, "expression": "1"},
                "b": {"amount": 2.0, "expression": "2"},
                "d": {"amount": 4.0, "expression": "4"}
            }
        }
        catalysts = analyzer._get_catalysts(recipe)
        assert "a" in catalysts
        assert "b" in catalysts
        assert "c" not in catalysts
        assert "d" not in catalysts

    def test_partial_catalyst(self, analyzer):
        """测试部分催化剂（输入输出数量不同）"""
        recipe = {
            "inputs": {
                "a": {"amount": 2.0, "expression": "2"},
                "b": {"amount": 3.0, "expression": "3"}
            },
            "outputs": {
                "a": {"amount": 1.0, "expression": "1"},
                "c": {"amount": 4.0, "expression": "4"}
            }
        }
        catalysts = analyzer._get_catalysts(recipe)
        # a 是催化剂（虽然数量不同，但存在于输入输出中）
        assert "a" in catalysts
