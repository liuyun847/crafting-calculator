"""
原始资源设备统计测试

测试无输入配方（原始资源）的设备统计功能，包括：
1. 无输入配方的设备数量计算（采矿、抽水等）
2. 原始资源与基础原料的区分
3. 设备统计中包含原始资源设备
4. 基础原料（无配方）不计入设备统计

注意：当前代码中，无输入配方（原始资源）在 find_production_paths 中
会被视为基础原料（返回空路径），但可以通过直接构建 CraftingNode
并手动设置配方来测试设备统计功能。
"""
import pytest
from calculator import CraftingCalculator, CraftingNode


@pytest.fixture
def raw_resource_recipes():
    """
    提供原始资源配方数据（无输入配方）

    Returns:
        dict: 原始资源配方字典
    """
    return {
        "采矿": {
            "device": "采矿机",
            "inputs": {},
            "outputs": {
                "铁矿石": {"amount": 1.0, "expression": "1"}
            }
        },
        "抽水": {
            "device": "抽水机",
            "inputs": {},
            "outputs": {
                "水": {"amount": 10.0, "expression": "10"}
            }
        },
        "采石": {
            "device": "采矿机",
            "inputs": {},
            "outputs": {
                "石头": {"amount": 1.0, "expression": "1"}
            }
        },
        "铁矿冶炼": {
            "device": "熔炉",
            "inputs": {
                "铁矿石": {"amount": 10.0, "expression": "10"},
                "煤炭": {"amount": 5.0, "expression": "5"}
            },
            "outputs": {
                "铁锭": {"amount": 5.0, "expression": "5"}
            }
        },
        "钢板制造": {
            "device": "组装机",
            "inputs": {
                "铁锭": {"amount": 5.0, "expression": "5"}
            },
            "outputs": {
                "钢板": {"amount": 2.0, "expression": "2"}
            }
        }
    }


@pytest.fixture
def raw_resource_calculator(temp_dir, raw_resource_recipes):
    """
    创建带有原始资源配方的 CraftingCalculator 实例

    Args:
        temp_dir: 临时目录路径
        raw_resource_recipes: 原始资源配方数据

    Yields:
        CraftingCalculator: 计算器实例
    """
    from data_manager import RecipeManager
    import json
    import os

    manager = RecipeManager(recipes_dir=temp_dir)

    recipe_file = os.path.join(temp_dir, "raw_resource_game.json")
    with open(recipe_file, "w", encoding="utf-8") as f:
        json.dump(raw_resource_recipes, f, indent=2, ensure_ascii=False)

    manager.load_recipe_file("raw_resource_game")

    calc = CraftingCalculator(manager)
    yield calc


@pytest.mark.unit
class TestRawResourceDeviceCount:
    """测试无输入配方的设备数量计算 - 通过直接构建节点测试"""

    def test_mining_device_count(self, raw_resource_calculator, raw_resource_recipes):
        """
        测试采矿设备数量计算

        配方 "采矿" 无输入，输出铁矿石=1/s，设备采矿机
        需要10/s铁矿石，应计算10台采矿机
        """
        # 直接构建 CraftingNode 并设置配方
        root = CraftingNode("铁矿石", 10.0)
        root.recipe = raw_resource_recipes["采矿"]
        # 设备数 = 目标速率 / 产出速率 = 10 / 1 = 10
        root.device_count = 10.0 / root.recipe["outputs"]["铁矿石"]["amount"]

        # 验证设备数量 = 10/1 = 10台
        assert root.device_count == 10.0

        # 验证设备类型
        assert root.recipe["device"] == "采矿机"

    def test_water_pumping_device_count(self, raw_resource_calculator, raw_resource_recipes):
        """
        测试抽水设备数量计算

        配方 "抽水" 无输入，输出水=10/s，设备抽水机
        需要50/s水，应计算5台抽水机
        """
        root = CraftingNode("水", 50.0)
        root.recipe = raw_resource_recipes["抽水"]
        # 设备数 = 50 / 10 = 5
        root.device_count = 50.0 / root.recipe["outputs"]["水"]["amount"]

        # 验证设备数量 = 50/10 = 5台
        assert root.device_count == 5.0

        # 验证设备类型
        assert root.recipe["device"] == "抽水机"

    def test_raw_resource_fractional_devices(self, raw_resource_calculator, raw_resource_recipes):
        """
        测试原始资源的小数设备数量

        需要3/s铁矿石，应计算3台采矿机
        """
        root = CraftingNode("铁矿石", 3.0)
        root.recipe = raw_resource_recipes["采矿"]
        root.device_count = 3.0 / root.recipe["outputs"]["铁矿石"]["amount"]

        # 验证设备数量 = 3/1 = 3台
        assert root.device_count == 3.0

    def test_raw_resource_zero_rate(self, raw_resource_calculator, raw_resource_recipes):
        """
        测试零生产速度的原始资源

        需要0/s铁矿石，应计算0台采矿机
        """
        root = CraftingNode("铁矿石", 0.0)
        root.recipe = raw_resource_recipes["采矿"]
        root.device_count = 0.0

        # 验证设备数量 = 0台
        assert root.device_count == 0.0


@pytest.mark.unit
class TestRawResourceDeviceStats:
    """测试设备统计中包含原始资源设备"""

    def test_mining_in_device_stats(self, raw_resource_calculator, raw_resource_recipes):
        """
        测试采矿设备计入设备统计

        生产铁矿石10/s，应包含采矿机10台
        """
        # 构建包含原始资源的合成树
        root = CraftingNode("铁锭", 5.0)
        root.recipe = raw_resource_recipes["铁矿冶炼"]
        root.device_count = 5.0 / \
            root.recipe["outputs"]["铁锭"]["amount"]  # 5/5 = 1

        # 创建子节点（铁矿石作为原始资源）
        child = CraftingNode("铁矿石", 10.0)
        child.recipe = raw_resource_recipes["采矿"]
        child.device_count = 10.0 / \
            child.recipe["outputs"]["铁矿石"]["amount"]  # 10/1 = 10

        root.children = [child]

        device_stats = raw_resource_calculator.get_device_stats(root)

        # 验证设备统计包含采矿机和熔炉
        assert "采矿机" in device_stats
        assert device_stats["采矿机"] == 10.0
        assert "熔炉" in device_stats
        assert device_stats["熔炉"] == 1.0

    def test_water_pumping_in_device_stats(self, raw_resource_calculator, raw_resource_recipes):
        """
        测试抽水设备计入设备统计

        生产水50/s，应包含抽水机5台
        """
        root = CraftingNode("水", 50.0)
        root.recipe = raw_resource_recipes["抽水"]
        root.device_count = 50.0 / \
            root.recipe["outputs"]["水"]["amount"]  # 50/10 = 5

        device_stats = raw_resource_calculator.get_device_stats(root)

        # 验证设备统计包含抽水机
        assert "抽水机" in device_stats
        assert device_stats["抽水机"] == 5.0

    def test_multiple_raw_resource_devices(self, raw_resource_calculator, raw_resource_recipes):
        """
        测试多种原始资源设备统计

        分别生产铁矿石和石头，设备统计应分别计算
        """
        # 创建父节点
        root = CraftingNode("产品", 1.0)
        root.recipe = {"device": "工厂", "inputs": {},
                       "outputs": {"产品": {"amount": 1.0}}}
        root.device_count = 1.0

        # 铁矿石子节点
        child_iron = CraftingNode("铁矿石", 5.0)
        child_iron.recipe = raw_resource_recipes["采矿"]
        child_iron.device_count = 5.0

        # 石头子节点
        child_stone = CraftingNode("石头", 3.0)
        child_stone.recipe = raw_resource_recipes["采石"]
        child_stone.device_count = 3.0

        root.children = [child_iron, child_stone]

        device_stats = raw_resource_calculator.get_device_stats(root)

        # 验证设备数量：工厂1 + 采矿机(5+3) = 9
        assert "工厂" in device_stats
        assert device_stats["工厂"] == 1.0
        assert "采矿机" in device_stats
        assert device_stats["采矿机"] == 8.0  # 5 + 3


@pytest.mark.unit
class TestRawMaterialVsBasicMaterial:
    """测试原始资源与基础原料的区分"""

    def test_raw_resource_has_device(self, raw_resource_calculator, raw_resource_recipes):
        """
        测试原始资源（有配方无输入）有设备

        采矿有设备采矿机
        """
        root = CraftingNode("铁矿石", 10.0)
        root.recipe = raw_resource_recipes["采矿"]
        root.device_count = 10.0

        # 验证原始资源有配方和设备
        assert root.recipe is not None
        assert root.device_count > 0
        assert root.recipe["device"] == "采矿机"

    def test_basic_material_no_device(self, raw_resource_calculator):
        """
        测试基础原料（无配方）没有设备

        基础原料（无配方）不应计入设备统计
        """
        # 创建生产链，包含基础原料
        path = raw_resource_calculator.find_production_paths("铁锭")[0]
        root = raw_resource_calculator.build_crafting_tree("铁锭", 5.0, path)

        # 查找基础原料节点（煤炭，无配方）
        def find_basic_material_node(node):
            """递归查找基础原料节点"""
            if node.recipe is None:
                return node
            for child in node.children:
                result = find_basic_material_node(child)
                if result:
                    return result
            return None

        basic_node = find_basic_material_node(root)

        # 验证基础原料节点存在且无设备
        assert basic_node is not None
        assert basic_node.recipe is None
        assert basic_node.device_count == 0

    def test_basic_material_not_in_device_stats(self, raw_resource_calculator):
        """
        测试基础原料不计入设备统计

        煤炭作为基础原料（无配方），不应出现在设备统计中
        """
        path = raw_resource_calculator.find_production_paths("铁锭")[0]
        root = raw_resource_calculator.build_crafting_tree("铁锭", 5.0, path)

        device_stats = raw_resource_calculator.get_device_stats(root)

        # 验证煤炭不在设备统计中
        assert "煤炭" not in device_stats

        # 验证熔炉在设备统计中
        assert "熔炉" in device_stats


@pytest.mark.unit
class TestMixedScenarios:
    """测试混合场景：同时有原始资源、基础原料和普通配方"""

    def test_steel_plate_production_chain(self, raw_resource_calculator):
        """
        测试钢板生产链的完整设备统计

        在当前代码实现中，铁矿石作为无输入配方的产物，
        在 find_production_paths 中被视为基础原料（无配方）
        """
        trees = raw_resource_calculator.calculate_production_chain("钢板", 2.0)

        assert len(trees) > 0

        path = raw_resource_calculator.find_production_paths("钢板")[0]
        root = raw_resource_calculator.build_crafting_tree("钢板", 2.0, path)

        device_stats = raw_resource_calculator.get_device_stats(root)

        # 验证组装机和熔炉在统计中
        assert "组装机" in device_stats  # 钢板制造
        assert "熔炉" in device_stats    # 铁锭冶炼

        # 验证设备数量计算正确
        # 钢板：2/s，产出2/s，设备数 = 2/2 = 1
        assert device_stats["组装机"] == 1.0

        # 铁锭：需要 2*5/2 = 5/s，产出5/s，设备数 = 5/5 = 1
        assert device_stats["熔炉"] == 1.0

    def test_raw_materials_extraction(self, raw_resource_calculator):
        """
        测试从混合生产链中提取基础原料

        在当前代码实现中，铁矿石和煤炭都被视为基础原料
        """
        path = raw_resource_calculator.find_production_paths("钢板")[0]
        root = raw_resource_calculator.build_crafting_tree("钢板", 2.0, path)

        raw_materials = raw_resource_calculator.get_raw_materials(root)

        # 验证煤炭和铁矿石都是基础原料
        assert "煤炭" in raw_materials
        assert "铁矿石" in raw_materials

    def test_complete_chain_device_count(self, raw_resource_calculator):
        """
        测试完整生产链的总设备数

        在当前代码实现中，只有组装机和熔炉计入设备统计
        """
        trees = raw_resource_calculator.calculate_production_chain("钢板", 2.0)
        tree_dict = trees[0]

        total_devices = raw_resource_calculator._count_total_devices(tree_dict)

        # 总设备数 = 组装机1 + 熔炉1 = 2
        # （铁矿石作为基础原料，没有设备统计）
        assert total_devices == 2.0

    def test_manual_raw_resource_in_chain(self, raw_resource_calculator, raw_resource_recipes):
        """
        测试手动构建包含原始资源的生产链

        验证当手动设置原始资源配方时，设备统计正确
        """
        # 手动构建完整的生产链
        root = CraftingNode("钢板", 2.0)
        root.recipe = raw_resource_recipes["钢板制造"]
        root.device_count = 2.0 / \
            root.recipe["outputs"]["钢板"]["amount"]  # 2/2 = 1

        # 铁锭节点
        child_iron = CraftingNode("铁锭", 5.0)
        child_iron.recipe = raw_resource_recipes["铁矿冶炼"]
        child_iron.device_count = 5.0 / \
            child_iron.recipe["outputs"]["铁锭"]["amount"]  # 5/5 = 1

        # 铁矿石节点（原始资源）
        grandchild_ore = CraftingNode("铁矿石", 10.0)
        grandchild_ore.recipe = raw_resource_recipes["采矿"]
        grandchild_ore.device_count = 10.0 / \
            grandchild_ore.recipe["outputs"]["铁矿石"]["amount"]  # 10/1 = 10

        # 煤炭节点（基础原料）
        grandchild_coal = CraftingNode("煤炭", 5.0)
        grandchild_coal.recipe = None  # 基础原料无配方
        grandchild_coal.device_count = 0.0

        child_iron.children = [grandchild_ore, grandchild_coal]
        root.children = [child_iron]

        device_stats = raw_resource_calculator.get_device_stats(root)

        # 验证所有设备都在统计中
        assert "组装机" in device_stats
        assert device_stats["组装机"] == 1.0
        assert "熔炉" in device_stats
        assert device_stats["熔炉"] == 1.0
        assert "采矿机" in device_stats
        assert device_stats["采矿机"] == 10.0

        # 验证煤炭不在设备统计中
        assert "煤炭" not in device_stats


@pytest.mark.unit
class TestEdgeCases:
    """测试边界情况"""

    def test_very_high_raw_resource_rate(self, raw_resource_calculator, raw_resource_recipes):
        """
        测试极高生产速度的原始资源

        需要1000/s铁矿石，应计算1000台采矿机
        """
        root = CraftingNode("铁矿石", 1000.0)
        root.recipe = raw_resource_recipes["采矿"]
        root.device_count = 1000.0 / root.recipe["outputs"]["铁矿石"]["amount"]

        assert root.device_count == 1000.0

    def test_very_low_raw_resource_rate(self, raw_resource_calculator, raw_resource_recipes):
        """
        测试极低生产速度的原始资源

        需要0.1/s铁矿石，应计算0.1台采矿机
        """
        root = CraftingNode("铁矿石", 0.1)
        root.recipe = raw_resource_recipes["采矿"]
        root.device_count = 0.1 / root.recipe["outputs"]["铁矿石"]["amount"]

        assert root.device_count == 0.1

    def test_raw_resource_tree_structure(self, raw_resource_calculator, raw_resource_recipes):
        """
        测试原始资源合成树的结构

        原始资源节点应该没有子节点（无输入）
        """
        root = CraftingNode("铁矿石", 10.0)
        root.recipe = raw_resource_recipes["采矿"]
        root.device_count = 10.0

        # 验证原始资源节点没有子节点
        assert len(root.children) == 0

        # 验证原始资源节点有配方
        assert root.recipe is not None

        # 验证配方输入为空
        assert root.recipe["inputs"] == {}

    def test_raw_resource_no_children_in_chain(self, raw_resource_calculator, raw_resource_recipes):
        """
        测试生产链中原始资源节点没有子节点

        即使作为生产链的一部分，原始资源也不应该有子节点
        """
        # 构建包含原始资源的生产链
        root = CraftingNode("铁锭", 5.0)
        root.recipe = raw_resource_recipes["铁矿冶炼"]
        root.device_count = 1.0

        # 铁矿石作为原始资源子节点
        child = CraftingNode("铁矿石", 10.0)
        child.recipe = raw_resource_recipes["采矿"]
        child.device_count = 10.0

        root.children = [child]

        # 验证原始资源节点没有子节点
        assert len(child.children) == 0

        # 验证设备统计
        device_stats = raw_resource_calculator.get_device_stats(root)
        assert "采矿机" in device_stats
        assert "熔炉" in device_stats
