"""
路径对比引擎模块

负责分析、比较和标记多条生产路径：
1. 根据设备数量选择主路径
2. 在每个节点找到所有其他可能的替代路径
3. 构建带有路径标记的合成树
"""

from typing import Any, Dict, List, Optional, Tuple

from crafting_node import CraftingNode


class PathComparisonEngine:
    """
    路径对比引擎，负责分析、比较和标记多条生产路径

    主要功能：
    1. 根据设备数量选择主路径
    2. 在每个节点找到所有其他可能的替代路径
    3. 构建带有路径标记的合成树
    """

    def __init__(self):
        """
        初始化路径对比引擎
        """
        self._path_counter = 0  # 路径计数器，用于生成唯一path_id

    def find_main_path(
        self, production_paths: List[List[Dict[str, Any]]]
    ) -> Optional[List[Dict[str, Any]]]:
        """
        根据设备数量选择主路径

        选择标准：
        1. 总设备数量最少的路径作为主路径
        2. 如果设备数相同，选择配方数量更少的路径
        3. 如果仍然相同，选择第一个

        Args:
            production_paths: 所有可能的生产路径列表

        Returns:
            选中的主路径，如果路径列表为空则返回None
        """
        if not production_paths:
            return None

        if len(production_paths) == 1:
            return production_paths[0]

        def calculate_path_score(path: List[Dict[str, Any]]) -> Tuple[float, int]:
            """
            计算路径的评分（设备数，配方数）
            评分越低越好
            """
            # 估算设备数量（基于配方输出量）
            total_devices = 0.0
            for recipe in path:
                if recipe and "outputs" in recipe and recipe["outputs"]:
                    # 使用第一个输出的amount作为参考
                    first_output = list(recipe["outputs"].values())[0]
                    if isinstance(first_output, dict) and "amount" in first_output:
                        # 设备数与产出率成反比
                        total_devices += 1.0 / \
                            max(first_output["amount"], 0.001)

            return (total_devices, len(path))

        # 按评分排序，选择最优路径
        sorted_paths = sorted(production_paths, key=calculate_path_score)
        return sorted_paths[0]

    def find_alternative_paths_at_node(
        self,
        node: CraftingNode,
        all_paths: List[List[CraftingNode]],
        current_path_id: int = 0,
    ) -> List[List[CraftingNode]]:
        """
        找到指定节点处所有其他可能的路径

        算法逻辑：
        1. 找到所有包含该物品的完整路径
        2. 排除包含当前节点对象的路径（这是当前路径，不是替代路径）
        3. 收集其他路径在该节点的不同子树

        Args:
            node: 当前节点
            all_paths: 所有完整的路径列表（每个路径是CraftingNode列表）
            current_path_id: 当前路径的ID

        Returns:
            替代路径列表，每条路径是一个CraftingNode列表
        """
        alternative_paths = []

        # 找到所有包含该物品的其他路径
        for path in all_paths:
            # 跳过包含当前节点对象的路径（这是当前路径，不是替代路径）
            if node in path:
                continue

            # 找到路径中对应此物品的节点
            matching_nodes = [n for n in path if n.item_name == node.item_name]

            for match_node in matching_nodes:
                # 检查是否是不同的路径选择，或者是不同路径中的相同节点
                # 如果是不同对象（位于不同路径中），则认为是替代路径
                if node is not match_node:
                    # 提取从该节点开始的子路径
                    sub_path = self._extract_sub_path(path, match_node)
                    if sub_path and sub_path not in alternative_paths:
                        alternative_paths.append(sub_path)

        return alternative_paths

    def _is_different_path_choice(
        self, node1: CraftingNode, node2: CraftingNode
    ) -> bool:
        """
        判断两个节点是否代表不同的路径选择

        判断标准：
        1. 如果是同一个对象，则不是不同的路径选择
        2. 使用的配方不同，则是不同的路径
        3. 父节点不同（一个是None一个不是，或父节点不是同一个对象），则是不同的路径
        4. 父节点是同一个对象且配方相同，则不是不同的路径选择

        Args:
            node1: 第一个节点
            node2: 第二个节点

        Returns:
            如果是不同的路径选择返回True
        """
        # 如果是同一个对象，则不是不同的路径选择
        if node1 is node2:
            return False

        # 如果配方不同，则是不同的路径
        if node1.recipe != node2.recipe:
            return True

        # 如果父节点不同（一个是None一个不是），则是不同的路径
        if (node1.parent is None) != (node2.parent is None):
            return True

        # 如果都有父节点，但父节点不是同一个对象，则是不同的路径
        if node1.parent is not None and node2.parent is not None:
            if node1.parent is not node2.parent:
                return True

        # 配方相同且父节点相同（或都为None），不是不同的路径选择
        return False

    def _extract_sub_path(
        self, full_path: List[CraftingNode], start_node: CraftingNode
    ) -> List[CraftingNode]:
        """
        从完整路径中提取从指定节点开始的子路径

        Args:
            full_path: 完整的节点路径
            start_node: 起始节点

        Returns:
            从起始节点开始的子路径
        """
        try:
            start_idx = full_path.index(start_node)
            return full_path[start_idx:]
        except ValueError:
            return []

    def build_path_tree_with_markers(
        self,
        main_path: List[CraftingNode],
        alternative_paths: List[List[CraftingNode]],
        calculator: "CraftingCalculator",
    ) -> CraftingNode:
        """
        构建带有替代路径标记的合成树

        构建逻辑：
        1. 为主路径分配 path_id=0
        2. 为每个替代路径分配递增的 path_id
        3. 标记替代路径上的节点 is_alternative=True
        4. 在主路径的每个节点上存储 alternative_paths 信息

        Args:
            main_path: 主路径节点列表
            alternative_paths: 替代路径列表
            calculator: 用于获取配方的计算器实例

        Returns:
            带有路径标记的合成树根节点
        """
        if not main_path:
            return None

        # 获取根节点
        root = main_path[0]

        # 为每个替代路径分配ID
        self._path_counter = 1
        for alt_path in alternative_paths:
            self._mark_alternative_path(alt_path, self._path_counter)
            self._path_counter += 1

        # 标记主路径
        self._mark_main_path(main_path)

        # 将替代路径信息附加到主路径的对应节点
        self._attach_alternative_paths_to_main(root, alternative_paths)

        return root

    def _mark_alternative_path(self, path: List[CraftingNode], path_id: int):
        """
        标记替代路径上的节点

        Args:
            path: 替代路径节点列表
            path_id: 路径ID
        """
        for node in path:
            node.path_id = path_id
            node.is_alternative = True

    def _mark_main_path(self, path: List[CraftingNode]):
        """
        标记主路径上的节点

        Args:
            path: 主路径节点列表
        """
        for node in path:
            node.path_id = 0
            node.is_alternative = False

    def _attach_alternative_paths_to_main(
        self, root: CraftingNode, alternative_paths: List[List[CraftingNode]]
    ):
        """
        将替代路径信息附加到主路径的对应节点

        Args:
            root: 主路径根节点
            alternative_paths: 替代路径列表
        """
        # 构建从物品名称到主路径节点的映射
        main_nodes = {}

        def collect_main_nodes(node: CraftingNode):
            if node.item_name not in main_nodes:
                main_nodes[node.item_name] = node
            for child in node.children:
                collect_main_nodes(child)

        collect_main_nodes(root)

        # 将替代路径附加到对应的主路径节点
        for alt_path in alternative_paths:
            if not alt_path:
                continue

            # 找到替代路径的根物品
            root_item = alt_path[0].item_name

            # 如果主路径中有这个物品，附加替代路径
            if root_item in main_nodes:
                main_node = main_nodes[root_item]
                # 避免重复添加相同的替代路径
                if alt_path not in main_node.alternative_paths:
                    main_node.alternative_paths.append(alt_path)