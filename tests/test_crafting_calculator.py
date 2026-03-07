"""
CraftingCalculator 类测试

测试 calculator 模块中的 CraftingCalculator 类
"""
import pytest
from calculator import CraftingCalculator, CraftingNode


class TestCraftingCalculatorInit:
    """测试 CraftingCalculator 初始化"""
    
    def test_basic_init(self, calculator):
        """测试基本初始化"""
        assert calculator.recipe_manager is not None
        assert calculator.recipes is not None
        assert calculator.path_engine is not None
    
    def test_recipes_loaded(self, calculator, sample_recipes):
        """测试配方已加载"""
        assert len(calculator.recipes) > 0


class TestCalculateProductionChain:
    """测试 calculate_production_chain 方法"""
    
    def test_simple_chain(self, calculator):
        """测试简单生产链"""
        trees = calculator.calculate_production_chain("铁锭", 1.0)
        
        assert len(trees) > 0
        assert trees[0]["item_name"] == "铁锭"
    
    def test_complex_chain(self, calculator):
        """测试复杂生产链"""
        trees = calculator.calculate_production_chain("钢板", 1.0)
        
        assert len(trees) > 0
        assert trees[0]["item_name"] == "钢板"
    
    def test_sorted_by_device_count(self, calculator):
        """测试按设备数排序"""
        trees = calculator.calculate_production_chain("电路板", 1.0)
        
        if len(trees) > 1:
            device_counts = [calculator._count_total_devices(tree) for tree in trees]
            for i in range(len(device_counts) - 1):
                assert device_counts[i] <= device_counts[i+1]
    
    def test_raw_material_chain(self, calculator):
        """测试基础原料生产链"""
        trees = calculator.calculate_production_chain("铁矿石", 1.0)
        
        assert len(trees) > 0
        assert trees[0]["item_name"] == "铁矿石"


class TestFindProductionPaths:
    """测试 find_production_paths 方法"""
    
    def test_single_path(self, calculator):
        """测试单一路径"""
        paths = calculator.find_production_paths("铁锭")
        
        assert len(paths) > 0
    
    def test_multiple_paths(self, calculator):
        """测试多条路径"""
        paths = calculator.find_production_paths("电路板")
        
        assert len(paths) >= 1
    
    def test_raw_material_path(self, calculator):
        """测试基础原料路径"""
        paths = calculator.find_production_paths("铁矿石")
        
        assert len(paths) == 1
        assert paths[0] == []
    
    def test_circular_dependency_handling(self, calculator):
        """测试循环依赖处理"""
        paths = calculator.find_production_paths("铁锭")
        
        assert len(paths) > 0


class TestCombinePaths:
    """测试 _combine_paths 方法"""

    def test_empty_paths_list(self, calculator):
        """测试空路径列表"""
        result = calculator._combine_paths([])

        assert result == [[]]

    def test_single_path_list(self, calculator):
        """测试单一路径列表 - 格式为 List[List[List[Dict]]]"""
        # 每个元素是一个路径选项列表，每个路径选项是配方列表
        paths_list = [
            [[{"recipe": "A"}]]  # 第一个物品只有一个路径选项
        ]

        result = calculator._combine_paths(paths_list)

        assert len(result) == 1
        assert result[0] == [{"recipe": "A"}]

    def test_multiple_path_lists(self, calculator):
        """测试多路径列表 - 格式为 List[List[List[Dict]]]"""
        # 每个物品可能有多个路径选项
        paths_list = [
            [[{"recipe": "A1"}], [{"recipe": "A2"}]],  # 第一个物品有2个路径选项
            [[{"recipe": "B1"}], [{"recipe": "B2"}]]   # 第二个物品有2个路径选项
        ]

        result = calculator._combine_paths(paths_list)

        # 2 x 2 = 4 种组合
        assert len(result) == 4

    def test_nested_combination(self, calculator):
        """测试嵌套组合 - 格式为 List[List[List[Dict]]]"""
        paths_list = [
            [[{"recipe": "A"}]],           # 第一个物品只有1个路径选项
            [[{"recipe": "B1"}], [{"recipe": "B2"}]],  # 第二个物品有2个路径选项
            [[{"recipe": "C"}]]            # 第三个物品只有1个路径选项
        ]

        result = calculator._combine_paths(paths_list)

        # 1 x 2 x 1 = 2 种组合
        assert len(result) == 2


class TestBuildCraftingTree:
    """测试 build_crafting_tree 方法"""
    
    def test_simple_tree(self, calculator):
        """测试简单树"""
        path = calculator.find_production_paths("铁锭")[0]
        tree = calculator.build_crafting_tree("铁锭", 1.0, path)
        
        assert tree is not None
        assert tree.item_name == "铁锭"
        assert tree.amount == 1.0
    
    def test_complex_tree(self, calculator):
        """测试复杂树"""
        path = calculator.find_production_paths("钢板")[0]
        tree = calculator.build_crafting_tree("钢板", 1.0, path)
        
        assert tree is not None
        assert tree.item_name == "钢板"
        assert len(tree.children) > 0
    
    def test_device_count_calculation(self, calculator):
        """测试设备数量计算"""
        path = calculator.find_production_paths("铁锭")[0]
        tree = calculator.build_crafting_tree("铁锭", 1.0, path)
        
        assert tree.device_count > 0
    
    def test_input_item_handling(self, calculator):
        """测试输入物品处理"""
        path = calculator.find_production_paths("铁锭")[0]
        tree = calculator.build_crafting_tree("铁锭", 1.0, path)
        
        assert len(tree.inputs) > 0
    
    def test_raw_material_handling(self, calculator):
        """测试基础原料处理"""
        path = []
        tree = calculator.build_crafting_tree("铁矿石", 1.0, path)
        
        assert tree is not None
        assert tree.recipe is None


class TestCountTotalDevices:
    """测试 _count_total_devices 方法"""
    
    def test_single_node(self, calculator):
        """测试单节点"""
        tree_dict = {
            "item_name": "铁锭",
            "device_count": 2.5,
            "children": []
        }
        
        total = calculator._count_total_devices(tree_dict)
        
        assert total == 2.5
    
    def test_multiple_nodes(self, calculator):
        """测试多节点"""
        tree_dict = {
            "item_name": "钢板",
            "device_count": 0.5,
            "children": [
                {
                    "item_name": "铁锭",
                    "device_count": 0.5,
                    "children": []
                }
            ]
        }
        
        total = calculator._count_total_devices(tree_dict)
        
        assert total == 1.0
    
    def test_deeply_nested(self, calculator):
        """测试深层嵌套"""
        tree_dict = {
            "item_name": "根节点",
            "device_count": 1.0,
            "children": [
                {
                    "item_name": "子节点1",
                    "device_count": 1.0,
                    "children": [
                        {
                            "item_name": "孙节点",
                            "device_count": 1.0,
                            "children": []
                        }
                    ]
                }
            ]
        }
        
        total = calculator._count_total_devices(tree_dict)
        
        assert total == 3.0


class TestAnalyzeSpecialRecipes:
    """测试 analyze_special_recipes 方法"""
    
    def test_catalyst_identification(self, calculator):
        """测试催化剂识别"""
        recipe = {
            "device": "化学设备",
            "inputs": {
                "催化剂": {"amount": 1.0, "expression": "1"},
                "原料A": {"amount": 5.0, "expression": "5"}
            },
            "outputs": {
                "催化剂": {"amount": 1.0, "expression": "1"},
                "产品B": {"amount": 3.0, "expression": "3"}
            }
        }
        
        result = calculator.analyze_special_recipes(recipe)
        
        assert "催化剂" in result["catalysts"]
    
    def test_net_output_calculation(self, calculator):
        """测试净产出计算"""
        recipe = {
            "device": "设备",
            "inputs": {
                "原料": {"amount": 5.0, "expression": "5"}
            },
            "outputs": {
                "产品": {"amount": 3.0, "expression": "3"}
            }
        }
        
        result = calculator.analyze_special_recipes(recipe)
        
        assert "产品" in result["outputs"]
        assert "原料" in result["inputs"]
    
    def test_net_input_calculation(self, calculator):
        """测试净消耗计算"""
        recipe = {
            "device": "设备",
            "inputs": {
                "原料A": {"amount": 5.0, "expression": "5"},
                "原料B": {"amount": 3.0, "expression": "3"}
            },
            "outputs": {
                "产品": {"amount": 3.0, "expression": "3"}
            }
        }
        
        result = calculator.analyze_special_recipes(recipe)
        
        assert "原料A" in result["inputs"]
        assert "原料B" in result["inputs"]
        assert "产品" in result["outputs"]
    
    def test_catalyst_in_inputs(self, calculator):
        """测试催化剂保留在输入中"""
        recipe = {
            "device": "化学设备",
            "inputs": {
                "催化剂": {"amount": 1.0, "expression": "1"},
                "原料": {"amount": 5.0, "expression": "5"}
            },
            "outputs": {
                "催化剂": {"amount": 1.0, "expression": "1"},
                "产品": {"amount": 3.0, "expression": "3"}
            }
        }
        
        result = calculator.analyze_special_recipes(recipe)
        
        assert "催化剂" in result["inputs"]
        assert result["inputs"]["催化剂"]["is_catalyst"] is True


class TestGetRawMaterials:
    """测试 get_raw_materials 方法"""
    
    def test_simple_tree(self, calculator):
        """测试简单树"""
        root = CraftingNode("铁锭", 1.0)
        child = CraftingNode("铁矿石", 2.0)
        child.recipe = None
        root.children = [child]
        
        materials = calculator.get_raw_materials(root)
        
        assert "铁矿石" in materials
        assert materials["铁矿石"] == 2.0
    
    def test_complex_tree(self, calculator):
        """测试复杂树"""
        root = CraftingNode("钢板", 1.0)
        child1 = CraftingNode("铁锭", 2.5)
        child2 = CraftingNode("铁矿石", 5.0)
        child2.recipe = None
        child1.children = [child2]
        root.children = [child1]
        
        materials = calculator.get_raw_materials(root)
        
        assert "铁矿石" in materials
    
    def test_multiple_raw_materials(self, calculator):
        """测试多个基础原料"""
        root = CraftingNode("电路板", 1.0)
        child1 = CraftingNode("铁锭", 2.0)
        child2 = CraftingNode("铁矿石", 4.0)
        child3 = CraftingNode("铜锭", 2.0)
        child4 = CraftingNode("铜矿石", 4.0)
        
        child2.recipe = None
        child4.recipe = None
        
        child1.children = [child2]
        child3.children = [child4]
        root.children = [child1, child3]
        
        materials = calculator.get_raw_materials(root)
        
        assert "铁矿石" in materials
        assert "铜矿石" in materials


class TestGetDeviceStats:
    """测试 get_device_stats 方法"""
    
    def test_single_device(self, calculator):
        """测试单种设备"""
        root = CraftingNode("铁锭", 1.0)
        root.recipe = {"device": "熔炉"}
        root.device_count = 0.5
        
        stats = calculator.get_device_stats(root)
        
        assert "熔炉" in stats
        assert stats["熔炉"] == 0.5
    
    def test_multiple_devices(self, calculator):
        """测试多种设备"""
        root = CraftingNode("钢板", 1.0)
        root.recipe = {"device": "组装机"}
        root.device_count = 0.5
        
        child = CraftingNode("铁锭", 2.5)
        child.recipe = {"device": "熔炉"}
        child.device_count = 0.5
        
        root.children = [child]
        
        stats = calculator.get_device_stats(root)
        
        assert "组装机" in stats
        assert "熔炉" in stats
    
    def test_device_aggregation(self, calculator):
        """测试设备数量聚合"""
        root = CraftingNode("电路板", 1.0)
        root.recipe = {"device": "组装机"}
        root.device_count = 1.0
        
        child1 = CraftingNode("铁锭", 2.0)
        child1.recipe = {"device": "熔炉"}
        child1.device_count = 0.4
        
        child2 = CraftingNode("铜锭", 2.0)
        child2.recipe = {"device": "熔炉"}
        child2.device_count = 0.4
        
        root.children = [child1, child2]
        
        stats = calculator.get_device_stats(root)
        
        assert stats["熔炉"] == 0.8


class TestBuildCraftingTreeWithAlternatives:
    """测试 build_crafting_tree_with_alternatives 方法"""
    
    def test_main_path_building(self, calculator):
        """测试主路径构建"""
        main_path = calculator.find_production_paths("铁锭")[0]
        all_paths = calculator.find_production_paths("铁锭")
        
        tree = calculator.build_crafting_tree_with_alternatives(
            "铁锭", 1.0, main_path, all_paths
        )
        
        assert tree is not None
        assert tree.path_id == 0
    
    def test_alternative_path_identification(self, calculator):
        """测试替代路径识别"""
        main_path = calculator.find_production_paths("电路板")[0]
        all_paths = calculator.find_production_paths("电路板")
        
        tree = calculator.build_crafting_tree_with_alternatives(
            "电路板", 1.0, main_path, all_paths
        )
        
        assert tree is not None
    
    def test_path_marking(self, calculator):
        """测试路径标记"""
        main_path = calculator.find_production_paths("铁锭")[0]
        all_paths = calculator.find_production_paths("铁锭")
        
        tree = calculator.build_crafting_tree_with_alternatives(
            "铁锭", 1.0, main_path, all_paths
        )
        
        assert tree.path_id == 0
        assert tree.is_alternative is False


class TestFlattenTreeToPath:
    """测试 _flatten_tree_to_path 方法"""
    
    def test_simple_tree(self, calculator):
        """测试简单树"""
        root = CraftingNode("节点1", 1.0)
        child = CraftingNode("节点2", 1.0)
        root.children = [child]
        
        path = calculator._flatten_tree_to_path(root)
        
        assert len(path) == 2
        assert path[0].item_name == "节点1"
        assert path[1].item_name == "节点2"
    
    def test_complex_tree(self, calculator):
        """测试复杂树"""
        root = CraftingNode("节点1", 1.0)
        child1 = CraftingNode("节点2", 1.0)
        child2 = CraftingNode("节点3", 1.0)
        
        child1.children = [child2]
        root.children = [child1]
        
        path = calculator._flatten_tree_to_path(root)
        
        assert len(path) == 3
    
    def test_depth_first_traversal(self, calculator):
        """测试深度优先遍历"""
        root = CraftingNode("节点1", 1.0)
        child1 = CraftingNode("节点2", 1.0)
        child2 = CraftingNode("节点3", 1.0)
        child3 = CraftingNode("节点4", 1.0)
        
        child1.children = [child2]
        root.children = [child1, child3]
        
        path = calculator._flatten_tree_to_path(root)
        
        assert path[0].item_name == "节点1"
        assert path[1].item_name == "节点2"
        assert path[2].item_name == "节点3"


class TestMarkPathInfo:
    """测试 _mark_path_info 方法"""
    
    def test_root_marking(self, calculator):
        """测试根节点标记"""
        root = CraftingNode("铁锭", 1.0)
        
        calculator._mark_path_info(root)
        
        assert root.path_id == 0
        assert root.is_alternative is False
    
    def test_bfs_traversal(self, calculator):
        """测试 BFS 遍历"""
        root = CraftingNode("节点1", 1.0)
        child1 = CraftingNode("节点2", 1.0)
        child2 = CraftingNode("节点3", 1.0)
        
        root.children = [child1, child2]
        
        calculator._mark_path_info(root)
        
        assert root.path_id == 0
        assert child1.path_id == 0
        assert child2.path_id == 0
    
    def test_empty_tree(self, calculator):
        """测试空树"""
        calculator._mark_path_info(None)
        
        pass


class TestEdgeCases:
    """测试边界情况"""
    
    def test_zero_production_rate(self, calculator):
        """测试零生产速度"""
        trees = calculator.calculate_production_chain("铁锭", 0.0)
        
        assert len(trees) > 0
    
    def test_very_high_production_rate(self, calculator):
        """测试极高生产速度"""
        trees = calculator.calculate_production_chain("铁锭", 1000.0)
        
        assert len(trees) > 0
    
    def test_nonexistent_item(self, calculator):
        """测试不存在的物品"""
        trees = calculator.calculate_production_chain("不存在的物品", 1.0)
        
        assert len(trees) == 0
    
    def test_negative_production_rate(self, calculator):
        """测试负生产速度"""
        trees = calculator.calculate_production_chain("铁锭", -1.0)
        
        assert len(trees) > 0
