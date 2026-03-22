"""
PathComparisonEngine 类测试

测试 calculator 模块中的 PathComparisonEngine 类
"""
import pytest
from calculator import PathComparisonEngine, CraftingNode


class TestPathComparisonEngineInit:
    """测试 PathComparisonEngine 初始化"""

    def test_basic_init(self, path_comparison_engine):
        """测试基本初始化"""
        assert path_comparison_engine is not None
        assert path_comparison_engine._path_counter == 0


class TestFindMainPath:
    """测试 find_main_path 方法"""

    def test_single_path(self, path_comparison_engine):
        """测试单一路径"""
        path = [
            {"device": "熔炉", "outputs": {"铁锭": {"amount": 5.0}}},
            {"device": "采矿机", "outputs": {"铁矿石": {"amount": 1.0}}}
        ]

        result = path_comparison_engine.find_main_path([path])

        assert result == path

    def test_multiple_paths_select_min_devices(self, path_comparison_engine):
        """测试多条路径，选择设备数最少的"""
        path1 = [
            {"device": "熔炉", "outputs": {"铁锭": {"amount": 5.0}}},
            {"device": "采矿机", "outputs": {"铁矿石": {"amount": 1.0}}}
        ]
        path2 = [
            {"device": "高级熔炉", "outputs": {"铁锭": {"amount": 10.0}}},
            {"device": "采矿机", "outputs": {"铁矿石": {"amount": 1.0}}}
        ]

        result = path_comparison_engine.find_main_path([path1, path2])

        assert result == path2

    def test_same_device_count_select_fewer_recipes(self, path_comparison_engine):
        """测试设备数相同时，选择配方数少的"""
        path1 = [
            {"device": "熔炉", "outputs": {"铁锭": {"amount": 5.0}}},
            {"device": "采矿机", "outputs": {"铁矿石": {"amount": 1.0}}},
            {"device": "传送带", "outputs": {}}
        ]
        path2 = [
            {"device": "高级熔炉", "outputs": {"铁锭": {"amount": 5.0}}},
            {"device": "采矿机", "outputs": {"铁矿石": {"amount": 1.0}}}
        ]

        result = path_comparison_engine.find_main_path([path1, path2])

        assert result == path2

    def test_empty_paths(self, path_comparison_engine):
        """测试空路径列表"""
        result = path_comparison_engine.find_main_path([])

        assert result is None

    def test_all_same_paths(self, path_comparison_engine):
        """测试所有路径相同"""
        path = [
            {"device": "熔炉", "outputs": {"铁锭": {"amount": 5.0}}}
        ]

        result = path_comparison_engine.find_main_path([path, path, path])

        assert result == path


class TestFindAlternativePathsAtNode:
    """测试 find_alternative_paths_at_node 方法"""

    def test_single_alternative_path(self, path_comparison_engine):
        """测试单个替代路径"""
        main_node = CraftingNode("铁锭", 1.0)
        alt_node = CraftingNode("铁锭", 1.0)

        all_paths = [[main_node], [alt_node]]

        result = path_comparison_engine.find_alternative_paths_at_node(
            main_node, all_paths)

        assert len(result) == 1

    def test_multiple_alternative_paths(self, path_comparison_engine):
        """测试多个替代路径"""
        main_node = CraftingNode("铁锭", 1.0)
        alt_node1 = CraftingNode("铁锭", 1.0)
        alt_node2 = CraftingNode("铁锭", 1.0)

        all_paths = [[main_node], [alt_node1], [alt_node2]]

        result = path_comparison_engine.find_alternative_paths_at_node(
            main_node, all_paths)

        assert len(result) >= 1

    def test_no_alternative_paths(self, path_comparison_engine):
        """测试无替代路径"""
        node = CraftingNode("铁锭", 1.0)

        all_paths = [[node]]

        result = path_comparison_engine.find_alternative_paths_at_node(
            node, all_paths)

        assert len(result) == 0

    def test_different_recipes(self, path_comparison_engine):
        """测试不同配方的节点"""
        main_node = CraftingNode("铁锭", 1.0)
        main_node.recipe = {"device": "熔炉"}

        alt_node = CraftingNode("铁锭", 1.0)
        alt_node.recipe = {"device": "高级熔炉"}

        all_paths = [[main_node], [alt_node]]

        result = path_comparison_engine.find_alternative_paths_at_node(
            main_node, all_paths)

        assert len(result) >= 1


class TestIsDifferentPathChoice:
    """测试 _is_different_path_choice 方法"""

    def test_different_recipes(self, path_comparison_engine):
        """测试不同配方"""
        node1 = CraftingNode("铁锭", 1.0)
        node1.recipe = {"device": "熔炉"}

        node2 = CraftingNode("铁锭", 1.0)
        node2.recipe = {"device": "高级熔炉"}

        result = path_comparison_engine._is_different_path_choice(node1, node2)

        assert result is True

    def test_same_recipe_different_parent(self, path_comparison_engine):
        """测试相同配方不同父节点"""
        parent1 = CraftingNode("父节点1", 1.0)
        parent2 = CraftingNode("父节点2", 1.0)

        node1 = CraftingNode("铁锭", 1.0)
        node1.recipe = {"device": "熔炉"}
        node1.parent = parent1

        node2 = CraftingNode("铁锭", 1.0)
        node2.recipe = {"device": "熔炉"}
        node2.parent = parent2

        result = path_comparison_engine._is_different_path_choice(node1, node2)

        assert result is True

    def test_same_recipe_same_parent(self, path_comparison_engine):
        """测试相同配方相同父节点"""
        parent = CraftingNode("父节点", 1.0)

        node1 = CraftingNode("铁锭", 1.0)
        node1.recipe = {"device": "熔炉"}
        node1.parent = parent

        node2 = CraftingNode("铁锭", 1.0)
        node2.recipe = {"device": "熔炉"}
        node2.parent = parent

        result = path_comparison_engine._is_different_path_choice(node1, node2)

        assert result is False

    def test_both_no_parent(self, path_comparison_engine):
        """测试两个节点都没有父节点"""
        node1 = CraftingNode("铁锭", 1.0)
        node1.recipe = {"device": "熔炉"}

        node2 = CraftingNode("铁锭", 1.0)
        node2.recipe = {"device": "熔炉"}

        result = path_comparison_engine._is_different_path_choice(node1, node2)

        assert result is False

    def test_one_no_parent(self, path_comparison_engine):
        """测试一个节点没有父节点"""
        parent = CraftingNode("父节点", 1.0)

        node1 = CraftingNode("铁锭", 1.0)
        node1.recipe = {"device": "熔炉"}
        node1.parent = parent

        node2 = CraftingNode("铁锭", 1.0)
        node2.recipe = {"device": "熔炉"}

        result = path_comparison_engine._is_different_path_choice(node1, node2)

        assert result is True


class TestExtractSubPath:
    """测试 _extract_sub_path 方法"""

    def test_valid_start_node(self, path_comparison_engine):
        """测试有效起始节点"""
        node1 = CraftingNode("节点1", 1.0)
        node2 = CraftingNode("节点2", 1.0)
        node3 = CraftingNode("节点3", 1.0)

        path = [node1, node2, node3]

        result = path_comparison_engine._extract_sub_path(path, node2)

        assert len(result) == 2
        assert result[0] == node2
        assert result[1] == node3

    def test_invalid_start_node(self, path_comparison_engine):
        """测试无效起始节点"""
        node1 = CraftingNode("节点1", 1.0)
        node2 = CraftingNode("节点2", 1.0)

        path = [node1]

        result = path_comparison_engine._extract_sub_path(path, node2)

        assert result == []

    def test_start_at_first_node(self, path_comparison_engine):
        """测试从第一个节点开始"""
        node1 = CraftingNode("节点1", 1.0)
        node2 = CraftingNode("节点2", 1.0)

        path = [node1, node2]

        result = path_comparison_engine._extract_sub_path(path, node1)

        assert len(result) == 2
        assert result[0] == node1

    def test_start_at_last_node(self, path_comparison_engine):
        """测试从最后一个节点开始"""
        node1 = CraftingNode("节点1", 1.0)
        node2 = CraftingNode("节点2", 1.0)

        path = [node1, node2]

        result = path_comparison_engine._extract_sub_path(path, node2)

        assert len(result) == 1
        assert result[0] == node2


class TestBuildPathTreeWithMarkers:
    """测试 build_path_tree_with_markers 方法"""

    def test_build_with_main_path_only(self, path_comparison_engine):
        """测试仅主路径"""
        main_path = [CraftingNode("铁锭", 1.0)]

        result = path_comparison_engine.build_path_tree_with_markers(
            main_path, [], None)

        assert result is not None
        assert result.path_id == 0
        assert result.is_alternative is False

    def test_build_with_alternative_paths(self, path_comparison_engine):
        """测试带替代路径"""
        main_path = [CraftingNode("铁锭", 1.0)]
        alt_path = [CraftingNode("铁锭", 1.0)]

        result = path_comparison_engine.build_path_tree_with_markers(main_path, [
                                                                     alt_path], None)

        assert result is not None
        assert result.path_id == 0
        assert result.is_alternative is False

    def test_path_id_assignment(self, path_comparison_engine):
        """测试 path_id 分配"""
        main_path = [CraftingNode("铁锭", 1.0)]
        alt_path1 = [CraftingNode("铁锭", 1.0)]
        alt_path2 = [CraftingNode("铁锭", 1.0)]

        result = path_comparison_engine.build_path_tree_with_markers(
            main_path, [alt_path1, alt_path2], None
        )

        assert result.path_id == 0
        assert alt_path1[0].path_id == 1
        assert alt_path2[0].path_id == 2

    def test_empty_main_path(self, path_comparison_engine):
        """测试空主路径"""
        result = path_comparison_engine.build_path_tree_with_markers([], [
        ], None)

        assert result is None


class TestMarkAlternativePath:
    """测试 _mark_alternative_path 方法"""

    def test_mark_single_path(self, path_comparison_engine):
        """测试标记单条路径"""
        path = [CraftingNode("铁锭", 1.0)]

        path_comparison_engine._mark_alternative_path(path, 1)

        for node in path:
            assert node.path_id == 1
            assert node.is_alternative is True

    def test_mark_multiple_nodes(self, path_comparison_engine):
        """测试标记多个节点"""
        path = [
            CraftingNode("节点1", 1.0),
            CraftingNode("节点2", 1.0),
            CraftingNode("节点3", 1.0)
        ]

        path_comparison_engine._mark_alternative_path(path, 2)

        for node in path:
            assert node.path_id == 2
            assert node.is_alternative is True


class TestMarkMainPath:
    """测试 _mark_main_path 方法"""

    def test_mark_single_path(self, path_comparison_engine):
        """测试标记单条路径"""
        path = [CraftingNode("铁锭", 1.0)]

        path_comparison_engine._mark_main_path(path)

        for node in path:
            assert node.path_id == 0
            assert node.is_alternative is False

    def test_mark_multiple_nodes(self, path_comparison_engine):
        """测试标记多个节点"""
        path = [
            CraftingNode("节点1", 1.0),
            CraftingNode("节点2", 1.0),
            CraftingNode("节点3", 1.0)
        ]

        path_comparison_engine._mark_main_path(path)

        for node in path:
            assert node.path_id == 0
            assert node.is_alternative is False


class TestAttachAlternativePathsToMain:
    """测试 _attach_alternative_paths_to_main 方法"""

    def test_attach_single_alternative(self, path_comparison_engine):
        """测试附加单个替代路径"""
        root = CraftingNode("铁锭", 1.0)
        alt_path = [CraftingNode("铁锭", 1.0)]

        path_comparison_engine._attach_alternative_paths_to_main(root, [
                                                                 alt_path])

        assert len(root.alternative_paths) == 1

    def test_attach_multiple_alternatives(self, path_comparison_engine):
        """测试附加多个替代路径"""
        root = CraftingNode("铁锭", 1.0)
        alt_path1 = [CraftingNode("铁锭", 1.0)]
        alt_path2 = [CraftingNode("铁锭", 1.0)]

        path_comparison_engine._attach_alternative_paths_to_main(
            root, [alt_path1, alt_path2])

        assert len(root.alternative_paths) == 2

    def test_no_duplicate_paths(self, path_comparison_engine):
        """测试不添加重复路径"""
        root = CraftingNode("铁锭", 1.0)
        alt_path = [CraftingNode("铁锭", 1.0)]

        path_comparison_engine._attach_alternative_paths_to_main(root, [
                                                                 alt_path])
        path_comparison_engine._attach_alternative_paths_to_main(root, [
                                                                 alt_path])

        assert len(root.alternative_paths) == 1

    def test_attach_to_nested_structure(self, path_comparison_engine):
        """测试附加到嵌套结构"""
        root = CraftingNode("钢板", 1.0)
        child = CraftingNode("铁锭", 1.0)
        root.children = [child]

        alt_path = [CraftingNode("铁锭", 1.0)]

        path_comparison_engine._attach_alternative_paths_to_main(root, [
                                                                 alt_path])

        assert len(root.alternative_paths) == 0
        assert len(child.alternative_paths) == 1


class TestEdgeCases:
    """测试边界情况"""

    def test_empty_alternative_paths(self, path_comparison_engine):
        """测试空替代路径列表"""
        root = CraftingNode("铁锭", 1.0)

        path_comparison_engine._attach_alternative_paths_to_main(root, [])

        assert len(root.alternative_paths) == 0

    def test_complex_path_structure(self, path_comparison_engine):
        """测试复杂路径结构"""
        main_path = [
            CraftingNode("钢板", 1.0),
            CraftingNode("铁锭", 2.0),
            CraftingNode("铁矿石", 4.0)
        ]

        alt_path = [
            CraftingNode("钢板", 1.0),
            CraftingNode("铁锭", 2.0),
            CraftingNode("铁矿石", 4.0)
        ]

        result = path_comparison_engine.build_path_tree_with_markers(main_path, [
                                                                     alt_path], None)

        assert result is not None
        assert result.path_id == 0
