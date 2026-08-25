"""
计算引擎主模块（CraftingCalculator）

负责合成树构建、设备数量计算和基础原料/设备统计。
相关类已拆分为独立模块：
- CraftingNode      → crafting_node.py（合成树节点）
- PathComparisonEngine → path_engine.py（多路径对比）
- RecipeAnalyzer    → recipe_analyzer.py（配方分析）
- ByproductPool     → byproduct_pool.py（副产品池）
"""

from typing import Dict, List, Any, Optional, FrozenSet
from functools import lru_cache
from data_manager import RecipeManager
from crafting_node import CraftingNode
from path_engine import PathComparisonEngine
from shared.utils import (
    traverse_tree,
    flatten_tree,
    format_device_count,
)


class CraftingCalculator:
    """
    合成计算器，负责构建合成树和计算设备数量

    支持路径对比功能，可以识别和标记多条生产路径。
    """

    def __init__(self, recipe_manager: RecipeManager):
        """
        初始化合成计算器

        Args:
            recipe_manager: 配方管理器实例
        """
        self.recipe_manager = recipe_manager
        self.recipes = recipe_manager.get_all_recipes()
        self.path_engine = PathComparisonEngine()  # 路径对比引擎

    def clear_cache(self) -> None:
        """
        清除所有缓存的计算结果

        在配方数据发生变化后调用此方法，以确保获取最新的计算结果。
        同时更新内部的 recipes 引用，确保后续计算使用最新的配方数据。
        """
        self.find_production_paths.cache_clear()
        self._item_exists.cache_clear()
        self.calculate_production_chain.cache_clear()
        # 更新 recipes 引用，确保使用最新的配方数据
        self.recipes = self.recipe_manager.get_all_recipes()

    @lru_cache(maxsize=128)
    def calculate_production_chain(
        self, target_item: str, target_rate: float
    ) -> List[Dict[str, Any]]:
        """
        计算生产链（已缓存）

        Args:
            target_item: 目标产物名称
            target_rate: 目标生产速度（个/秒）

        Returns:
            合成树列表，每个元素代表一种可能的生产路径
        """
        # 首先检查物品是否存在于任何配方中
        if not self._item_exists(target_item):
            return []

        # 查找所有可能的生产路径
        paths = self.find_production_paths(target_item)

        # 为每条路径构建合成树并计算设备数量
        result_trees = []
        for path in paths:
            tree = self.build_crafting_tree(target_item, target_rate, path)
            if tree:
                result_trees.append(tree.to_dict())

        # 根据设备数量排序，设备数少的排在前面
        result_trees.sort(key=lambda x: self._count_total_devices(x))

        return result_trees

    @lru_cache(maxsize=256)
    def _item_exists(self, item_name: str) -> bool:
        """
        检查物品是否存在于任何配方的输入或输出中（已缓存）

        Args:
            item_name: 物品名称

        Returns:
            如果物品存在于任何配方中返回True
        """
        # 每次调用都获取最新配方，确保缓存时数据是最新的
        recipes = self.recipe_manager.get_all_recipes()
        for recipe in recipes.values():
            # 检查输入物品
            for input_item in recipe.get("inputs", {}).keys():
                if input_item.strip() == item_name:
                    return True
            # 检查输出物品
            for output_item in recipe.get("outputs", {}).keys():
                if output_item.strip() == item_name:
                    return True
        return False

    @lru_cache(maxsize=128)
    def find_production_paths(
        self, target_item: str, visited: FrozenSet[str] = frozenset()
    ) -> List[List[Dict[str, Any]]]:
        """
        查找所有可能的生产路径（已缓存）

        Args:
            target_item: 目标产物名称
            visited: 已访问的物品集合，用于避免循环

        Returns:
            生产路径列表，每条路径是配方的列表
        """

        # 避免循环
        if target_item in visited:
            return []

        # 转换为可变集合进行操作
        visited_set = set(visited)
        visited_set.add(target_item)
        new_visited = frozenset(visited_set)

        # 查找所有能生产该物品的配方
        producing_recipes = self.recipe_manager.search_recipes_by_item(
            target_item, search_inputs=False, search_outputs=True
        )

        # 如果没有找到配方，说明是基础原料
        if not producing_recipes:
            return [[]]

        all_paths = []

        # 遍历所有能生产该物品的配方
        for recipe in producing_recipes:
            # 查找配方输入物品的所有可能路径
            input_paths_list = []

            # 检查每个输入物品是否有生产路径
            for input_item in recipe["inputs"]:
                input_paths = self.find_production_paths(
                    input_item, new_visited)
                if not input_paths:
                    # 某个输入物品无法生产，将其视为基础原料
                    # 继续处理其他输入物品，不中断循环
                    input_paths_list.append([[]])  # 基础原料，路径为空列表
                else:
                    input_paths_list.append(input_paths)

            if not input_paths_list:
                continue

            # 生成所有可能的组合路径（添加优化参数）
            combined_paths = self._combine_paths(
                input_paths_list,
                max_path_length=50
            )

            # 将当前配方添加到每条路径的开头
            for path in combined_paths:
                path.insert(0, recipe)
                all_paths.append(path)

        return all_paths

    def _combine_paths(
        self, paths_list: List[List[List[Dict[str, Any]]]],
        max_paths: Optional[int] = None, max_path_length: int = 50
    ) -> List[List[Dict[str, Any]]]:
        """
        组合多条路径列表，生成所有可能的路径组合（优化版）
        采用迭代实现替代递归，添加剪枝和去重机制，避免指数级爆炸

        Args:
            paths_list: 路径列表的列表
            max_paths: 最大返回路径数量，超过时提前终止，None 表示无限制
            max_path_length: 单条路径最大长度，超过时剪枝

        Returns:
            组合后的路径列表
        """
        if not paths_list:
            return [[]]

        # 迭代实现，避免递归栈溢出
        result: List[List[Dict[str, Any]]] = [[]]
        seen_paths = set()

        for path_group in paths_list:
            temp = []
            for existing in result:
                for path in path_group:
                    new_path = existing + path

                    # 路径长度剪枝
                    if len(new_path) > max_path_length:
                        continue

                    # 路径去重：通过配方ID组合生成唯一标识
                    # 空路径（基础原料）不需要去重
                    if new_path:
                        path_key = tuple(recipe.get("id", id(recipe)) for recipe in new_path)
                        if path_key in seen_paths:
                            continue
                        seen_paths.add(path_key)
                    temp.append(new_path)

                    # 提前终止：达到最大路径数量（仅当设置了 max_paths 时）
                    if max_paths is not None and len(temp) >= max_paths:
                        break
                if max_paths is not None and len(temp) >= max_paths:
                    break

            result = temp
            if not result:
                break

        return result

    def build_crafting_tree(
        self, target_item: str, target_rate: float, path: List[Dict[str, Any]]
    ) -> Optional[CraftingNode]:
        """
        构建合成树

        Args:
            target_item: 目标产物名称
            target_rate: 目标生产速度
            path: 生产路径，包含所有需要的配方

        Returns:
            合成树的根节点
        """
        # 创建根节点
        root = CraftingNode(target_item, target_rate)

        # 使用队列进行广度优先搜索构建树
        queue = [(root, target_rate)]
        processed_items = set()

        while queue:
            node, required_rate = queue.pop(0)

            # 如果是基础原料，跳过
            if node.item_name in processed_items:
                continue

            # 查找用于生产该物品的配方
            recipe = None
            for r in path:
                if node.item_name in r["outputs"]:
                    recipe = r
                    break

            if not recipe:
                # 基础原料，不需要进一步处理
                processed_items.add(node.item_name)
                continue

            node.recipe = recipe

            # 计算设备数量
            output_rate = recipe["outputs"][node.item_name]["amount"]
            node.device_count = required_rate / output_rate

            # 处理输入物品
            for input_item, input_data in recipe["inputs"].items():
                # 计算需要的输入速度
                input_rate = input_data["amount"] * node.device_count

                # 创建子节点
                child_node = CraftingNode(input_item, input_rate)
                child_node.parent = node
                node.children.append(child_node)
                node.inputs[input_item] = input_rate

                # 将子节点加入队列
                queue.append((child_node, input_rate))

            processed_items.add(node.item_name)

        return root

    def _count_total_devices(self, tree_dict: Dict[str, Any]) -> float:
        """
        计算合成树中总设备数量

        Args:
            tree_dict: 合成树的字典表示

        Returns:
            总设备数量
        """
        total = tree_dict["device_count"]
        for child in tree_dict["children"]:
            total += self._count_total_devices(child)
        return total

    def analyze_special_recipes(self, recipe: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析特殊配方，处理自循环、倍增和催化剂情况

        Args:
            recipe: 原始配方

        Returns:
            处理后的配方
        """
        inputs = recipe["inputs"]
        outputs = recipe["outputs"]

        # 识别催化剂（输入输出都有的物品）
        catalysts = set(inputs.keys()) & set(outputs.keys())

        # 识别净产出物品（仅在输出中的物品）
        net_outputs = set(outputs.keys()) - catalysts

        # 识别净消耗物品（仅在输入中的物品）
        net_inputs = set(inputs.keys()) - catalysts

        # 计算净产出率
        processed_recipe = {
            "device": recipe["device"],
            "inputs": {},
            "outputs": {},
            "catalysts": list(catalysts),
        }

        # 处理净消耗物品
        for item in net_inputs:
            processed_recipe["inputs"][item] = inputs[item]

        # 处理净产出物品
        for item in net_outputs:
            processed_recipe["outputs"][item] = outputs[item]

        # 处理催化剂（保留在输入中，但注明是催化剂）
        for item in catalysts:
            processed_recipe["inputs"][item] = inputs[item]
            processed_recipe["inputs"][item]["is_catalyst"] = True

        return processed_recipe

    def get_raw_materials(self, tree: CraftingNode) -> Dict[str, float]:
        """
        获取合成树中所有基础原料的消耗速度

        基础原料定义为：没有配方(recipe为None)且没有子节点的叶子节点

        Args:
            tree: 合成树的根节点

        Returns:
            基础原料消耗速度字典，{物品名称: 总消耗速度}
        """
        raw_materials: Dict[str, float] = {}

        def collect_raw_materials(node: CraftingNode) -> None:
            # 基础原料：没有配方且没有子节点的叶子节点
            if not node.recipe and not node.children:
                if node.item_name in raw_materials:
                    raw_materials[node.item_name] += node.amount
                else:
                    raw_materials[node.item_name] = node.amount

        traverse_tree(
            tree,
            child_accessor=lambda node: node.children,
            callback=collect_raw_materials
        )

        return raw_materials

    def get_device_stats(self, tree: CraftingNode) -> Dict[str, float]:
        """
        获取合成树中设备使用统计

        Args:
            tree: 合成树的根节点

        Returns:
            设备使用统计字典
        """
        device_stats = {}

        def collect_device_stats(node: CraftingNode):
            if node.recipe:
                device_name = node.recipe["device"]
                if device_name in device_stats:
                    device_stats[device_name] += node.device_count
                else:
                    device_stats[device_name] = node.device_count

        traverse_tree(
            tree,
            child_accessor=lambda node: node.children,
            callback=collect_device_stats
        )

        return device_stats

    def build_crafting_tree_with_alternatives(
        self,
        target_item: str,
        target_rate: float,
        main_path: List[Dict[str, Any]],
        all_available_paths: List[List[Dict[str, Any]]],
    ) -> Optional[CraftingNode]:
        """
        构建带有替代路径信息的合成树

        该方法增强基本的树构建逻辑，在构建主路径的同时：
        1. 识别每个节点处可能的替代路径
        2. 标记主路径和替代路径
        3. 将替代路径信息附加到对应的节点

        Args:
            target_item: 目标产物名称
            target_rate: 目标生产速度
            main_path: 选中的主生产路径（配方列表）
            all_available_paths: 所有可用的生产路径（用于识别替代路径）

        Returns:
            带有替代路径标记的合成树根节点
        """
        # 第一步：构建基本的合成树
        root = self.build_crafting_tree(target_item, target_rate, main_path)
        if not root:
            return None

        # 第二步：使用路径对比引擎标记路径
        # 将所有路径转换为节点列表进行比较
        all_node_paths = []
        for path in all_available_paths:
            # 为每条路径构建临时树以获取节点路径
            try:
                temp_root = self.build_crafting_tree(
                    target_item, target_rate, path)
                if temp_root:
                    node_path = self._flatten_tree_to_path(temp_root)
                    all_node_paths.append(node_path)
            except Exception:
                # 如果构建失败，跳过这条路径
                continue

        # 第三步：在主路径的每个节点上查找替代路径
        def attach_alternatives(node: CraftingNode):
            """递归地为每个节点附加替代路径"""
            if node.recipe:  # 只对非基础原料节点
                # 查找此节点处的替代路径
                alternatives = self.path_engine.find_alternative_paths_at_node(
                    node, all_node_paths, node.path_id
                )
                # 存储到节点的 alternative_paths 字段
                node.alternative_paths = alternatives

            # 递归处理子节点
            for child in node.children:
                attach_alternatives(child)

        # 执行附加替代路径
        attach_alternatives(root)

        # 第四步：标记路径信息
        self._mark_path_info(root)

        return root

    def _flatten_tree_to_path(self, root: CraftingNode) -> List[CraftingNode]:
        """
        将树结构扁平化为路径列表（深度优先遍历）

        Args:
            root: 树的根节点

        Returns:
            按遍历顺序排列的节点列表
        """
        return flatten_tree(
            root,
            child_accessor=lambda node: node.children,
            key_extractor=lambda node: node.item_name
        )

    def _mark_path_info(self, root: CraftingNode):
        """
        标记路径信息，设置 path_id 和 is_alternative

        使用广度优先遍历，确保所有节点都有正确的路径标记

        Args:
            root: 合成树根节点
        """
        if not root:
            return

        # 根节点总是主路径的一部分
        root.path_id = 0
        root.is_alternative = False

        # BFS遍历
        queue = [root]
        visited = {root.item_name}

        while queue:
            node = queue.pop(0)

            for child in node.children:
                if child.item_name not in visited:
                    visited.add(child.item_name)
                    # 继承父节点的路径标记
                    if child.path_id == 0 and not child.is_alternative:
                        child.path_id = node.path_id
                        child.is_alternative = node.is_alternative
                    queue.append(child)


if __name__ == "__main__":
    # 测试示例
    from data_manager import recipe_manager

    # 创建测试配方
    test_recipe = {
        "device": "熔炉",
        "inputs": {
            "矿石": {"amount": 1.0, "expression": "1"},
            "煤炭": {"amount": 0.5, "expression": "0.5"},
        },
        "outputs": {"铁锭": {"amount": 1.0, "expression": "1"}},
    }

    # 添加测试配方
    recipe_manager.create_new_recipe_file("test")
    recipe_manager.add_recipe(
        "熔炼",
        "熔炉",
        {
            "矿石": {"amount": 1.0, "expression": "1"},
            "煤炭": {"amount": 0.5, "expression": "0.5"},
        },
        {"铁锭": {"amount": 1.0, "expression": "1"}},
    )

    # 创建计算器并测试
    calculator = CraftingCalculator(recipe_manager)
    trees = calculator.calculate_production_chain("铁锭", 1.0)

    print("计算结果:")
    for i, tree_dict in enumerate(trees):
        print(f"\n路径 {i+1}:")
        print(f"总设备数: {format_device_count(calculator._count_total_devices(tree_dict))}")

        def print_tree(node_dict, indent=0):
            prefix = "  " * indent
            print(
                f"{prefix}{node_dict['item_name']}: {node_dict['amount']:.2f}/s "
                f"(设备数: {format_device_count(node_dict['device_count'])})"
            )
            for child in node_dict["children"]:
                print_tree(child, indent + 1)

        print_tree(tree_dict)