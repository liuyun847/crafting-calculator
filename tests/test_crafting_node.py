"""
CraftingNode 类测试

测试 calculator 模块中的 CraftingNode 类
"""
import pytest
from calculator import CraftingNode


class TestCraftingNodeInit:
    """测试 CraftingNode 初始化"""

    def test_basic_init(self):
        """测试基本初始化"""
        node = CraftingNode("铁锭", 1.0)

        assert node.item_name == "铁锭"
        assert node.amount == 1.0

    def test_default_values(self):
        """测试默认值"""
        node = CraftingNode("物品", 1.0)

        assert node.recipe is None
        assert node.device_count == 0
        assert node.inputs == {}
        assert node.children == []
        assert node.parent is None

    def test_path_comparison_fields(self):
        """测试路径对比字段初始化"""
        node = CraftingNode("物品", 1.0)

        assert node.alternative_paths == []
        assert node.path_id == 0
        assert node.is_alternative is False

    def test_init_with_zero_amount(self):
        """测试零值初始化"""
        node = CraftingNode("物品", 0.0)

        assert node.amount == 0.0

    def test_init_with_negative_amount(self):
        """测试负数初始化"""
        node = CraftingNode("物品", -1.0)

        assert node.amount == -1.0


class TestCraftingNodeStr:
    """测试 __str__ 方法"""

    def test_str_representation(self):
        """测试字符串表示"""
        node = CraftingNode("铁锭", 1.0)
        node.device_count = 2.5

        result = str(node)

        assert "铁锭" in result
        assert "1.00" in result
        assert "2.50" in result

    def test_str_with_zero_device_count(self):
        """测试零设备数的字符串表示"""
        node = CraftingNode("物品", 1.0)

        result = str(node)

        assert "0.00" in result


class TestCraftingNodeToDict:
    """测试 to_dict 方法"""

    def test_basic_to_dict(self):
        """测试基本转换"""
        node = CraftingNode("铁锭", 1.0)

        result = node.to_dict()

        assert result["item_name"] == "铁锭"
        assert result["amount"] == 1.0
        assert result["device_count"] == 0
        assert result["recipe"] == {}
        assert result["inputs"] == {}
        assert result["children"] == []

    def test_to_dict_with_recipe(self):
        """测试带配方的转换"""
        node = CraftingNode("铁锭", 1.0)
        node.recipe = {
            "device": "熔炉",
            "inputs": {},
            "outputs": {}
        }

        result = node.to_dict()

        assert result["recipe"]["device"] == "熔炉"

    def test_to_dict_with_inputs(self):
        """测试带输入的转换"""
        node = CraftingNode("铁锭", 1.0)
        node.inputs = {"铁矿石": 2.0, "煤炭": 1.0}

        result = node.to_dict()

        assert result["inputs"]["铁矿石"] == 2.0
        assert result["inputs"]["煤炭"] == 1.0

    def test_to_dict_with_children(self):
        """测试带子节点的转换"""
        node = CraftingNode("铁锭", 1.0)
        child1 = CraftingNode("铁矿石", 2.0)
        child2 = CraftingNode("煤炭", 1.0)
        node.children = [child1, child2]

        result = node.to_dict()

        assert len(result["children"]) == 2
        assert result["children"][0]["item_name"] == "铁矿石"
        assert result["children"][1]["item_name"] == "煤炭"

    def test_to_dict_with_path_info(self):
        """测试带路径信息的转换"""
        node = CraftingNode("铁锭", 1.0)
        node.path_id = 1
        node.is_alternative = True
        node.alternative_paths = []

        result = node.to_dict()

        assert result["path_info"]["path_id"] == 1
        assert result["path_info"]["is_alternative"] is True
        assert result["path_info"]["alternative_count"] == 0

    def test_to_dict_with_alternative_paths(self):
        """测试带替代路径的转换"""
        node = CraftingNode("铁锭", 1.0)
        alt_node = CraftingNode("铜锭", 1.0)
        alt_node.path_id = 2
        alt_node.is_alternative = True
        node.alternative_paths = [[alt_node]]

        result = node.to_dict()

        assert len(result["alternative_paths"]) == 1
        assert result["alternative_paths"][0][0]["item_name"] == "铜锭"
        assert result["alternative_paths"][0][0]["path_id"] == 2

    def test_to_dict_recursive(self):
        """测试递归转换"""
        root = CraftingNode("钢板", 1.0)
        root.device_count = 0.5

        child1 = CraftingNode("铁锭", 2.5)
        child1.device_count = 0.5

        child2 = CraftingNode("铁矿石", 5.0)
        child2.device_count = 0.5

        child1.children = [child2]
        root.children = [child1]

        result = root.to_dict()

        assert result["item_name"] == "钢板"
        assert result["children"][0]["item_name"] == "铁锭"
        assert result["children"][0]["children"][0]["item_name"] == "铁矿石"


class TestCraftingNodeAttributes:
    """测试 CraftingNode 属性"""

    def test_parent_attribute(self):
        """测试父节点属性"""
        parent = CraftingNode("父节点", 1.0)
        child = CraftingNode("子节点", 1.0)
        child.parent = parent

        assert child.parent == parent

    def test_device_count_attribute(self):
        """测试设备数量属性"""
        node = CraftingNode("物品", 1.0)
        node.device_count = 3.5

        assert node.device_count == 3.5

    def test_inputs_attribute(self):
        """测试输入属性"""
        node = CraftingNode("物品", 1.0)
        node.inputs = {"原料A": 1.0, "原料B": 2.0}

        assert len(node.inputs) == 2
        assert node.inputs["原料A"] == 1.0

    def test_children_attribute(self):
        """测试子节点属性"""
        node = CraftingNode("父节点", 1.0)
        child1 = CraftingNode("子节点1", 1.0)
        child2 = CraftingNode("子节点2", 1.0)
        node.children = [child1, child2]

        assert len(node.children) == 2
        assert node.children[0].item_name == "子节点1"


class TestCraftingNodePathComparison:
    """测试路径对比功能"""

    def test_path_id_default(self):
        """测试默认 path_id"""
        node = CraftingNode("物品", 1.0)

        assert node.path_id == 0

    def test_path_id_assignment(self):
        """测试 path_id 赋值"""
        node = CraftingNode("物品", 1.0)
        node.path_id = 5

        assert node.path_id == 5

    def test_is_alternative_default(self):
        """测试默认 is_alternative"""
        node = CraftingNode("物品", 1.0)

        assert node.is_alternative is False

    def test_is_alternative_assignment(self):
        """测试 is_alternative 赋值"""
        node = CraftingNode("物品", 1.0)
        node.is_alternative = True

        assert node.is_alternative is True

    def test_alternative_paths_default(self):
        """测试默认 alternative_paths"""
        node = CraftingNode("物品", 1.0)

        assert node.alternative_paths == []

    def test_alternative_paths_assignment(self):
        """测试 alternative_paths 赋值"""
        node = CraftingNode("物品", 1.0)
        alt_path = [CraftingNode("替代物品", 1.0)]
        node.alternative_paths = [alt_path]

        assert len(node.alternative_paths) == 1
        assert node.alternative_paths[0][0].item_name == "替代物品"


class TestCraftingNodeEdgeCases:
    """测试边界情况"""

    def test_very_large_amount(self):
        """测试极大数值"""
        node = CraftingNode("物品", 1e10)

        assert node.amount == 1e10

    def test_very_small_amount(self):
        """测试极小数值"""
        node = CraftingNode("物品", 1e-10)

        assert node.amount == 1e-10

    def test_special_characters_in_name(self):
        """测试名称中的特殊字符"""
        node = CraftingNode("物品_名称", 1.0)

        assert node.item_name == "物品_名称"

    def test_unicode_in_name(self):
        """测试名称中的 Unicode 字符"""
        node = CraftingNode("物品名称", 1.0)

        assert node.item_name == "物品名称"

    def test_deeply_nested_structure(self):
        """测试深层嵌套结构"""
        root = CraftingNode("根节点", 1.0)
        current = root

        for i in range(10):
            child = CraftingNode(f"节点{i}", 1.0)
            current.children = [child]
            current = child

        result = root.to_dict()

        assert len(result["children"]) == 1
        assert result["children"][0]["children"][0]["children"][0]["children"][0]["children"][0]["item_name"] == "节点4"
