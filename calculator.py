"""
计算引擎模块

该模块负责合成树构建、多路径选择和设备数量计算，支持特殊配方处理。
"""

from typing import Dict, List, Any, Optional, Set, Tuple
from data_manager import RecipeManager
from enum import Enum


class RecipeType(Enum):
    """配方类型枚举"""

    NORMAL = "normal"  # 普通配方
    DOUBLING = "doubling"  # 倍增配方（产出 > 投入）
    LOSSY = "lossy"  # 损耗配方（产出 < 投入）
    CATALYST = "catalyst"  # 催化剂配方（有催化剂）
    INVALID = "invalid"  # 无效配方（净产出 <= 0）


class ByproductPool:
    """
    副产品池管理器

    管理生产过程中产生的副产品，支持收集、消耗和溢出检测。
    """

    def __init__(self, excess_threshold: float = 100.0):
        """
        初始化副产品池

        Args:
            excess_threshold: 溢出阈值，超过此值的副产品被视为溢出
        """
        self._pool: Dict[str, float] = {}
        self._excess_threshold: float = excess_threshold

    def add_byproduct(self, item: str, amount: float) -> None:
        """
        添加副产品到池中

        Args:
            item: 物品名称
            amount: 数量（个/秒）
        """
        if item in self._pool:
            self._pool[item] += amount
        else:
            self._pool[item] = amount

    def consume_byproduct(self, item: str, amount: float) -> Tuple[float, float]:
        """
        从池中消耗副产品

        Args:
            item: 物品名称
            amount: 需要消耗的数量

        Returns:
            Tuple[实际消耗量, 剩余需求量]
        """
        available = self._pool.get(item, 0.0)
        consumed = min(available, amount)
        remaining = amount - consumed

        if item in self._pool:
            self._pool[item] -= consumed
            if self._pool[item] <= 0:
                del self._pool[item]

        return (consumed, remaining)

    def get_byproduct_amount(self, item: str) -> float:
        """
        获取副产品的当前数量

        Args:
            item: 物品名称

        Returns:
            当前数量
        """
        return self._pool.get(item, 0.0)

    def get_excess_byproducts(self) -> List[str]:
        """
        获取溢出的副产品列表

        Returns:
            溢出物品名称列表
        """
        return [
            item
            for item, amount in self._pool.items()
            if amount > self._excess_threshold
        ]

    def get_all_byproducts(self) -> Dict[str, float]:
        """
        获取所有副产品

        Returns:
            副产品字典 {物品名称: 数量}
        """
        return self._pool.copy()

    def clear(self) -> None:
        """清空副产品池"""
        self._pool.clear()


class RecipeAnalyzer:
    """
    配方分析器，负责计算配方的净产出、净消耗和设备数量

    主要功能：
    1. 计算特定物品的净产出（输出 - 输入）
    2. 计算基于净产出的设备数量
    3. 获取净消耗（排除催化剂）
    4. 获取净产出（排除催化剂）
    """

    def __init__(self):
        """
        初始化配方分析器
        """
        pass

    def _get_catalysts(self, recipe: Dict[str, Any]) -> Set[str]:
        """
        识别配方中的催化剂（输入输出都有的物品）

        Args:
            recipe: 配方数据

        Returns:
            催化剂物品名称集合
        """
        inputs = recipe.get("inputs", {})
        outputs = recipe.get("outputs", {})
        return set(inputs.keys()) & set(outputs.keys())

    def calculate_net_output_for_item(self, recipe: Dict[str, Any], item: str) -> float:
        """
        计算特定物品的净产出

        净产出 = 输出量 - 输入量

        Args:
            recipe: 配方数据
            item: 物品名称

        Returns:
            净产出量（负值表示净消耗）
        """
        inputs = recipe.get("inputs", {})
        outputs = recipe.get("outputs", {})

        input_amount = inputs.get(item, {}).get("amount", 0.0)
        output_amount = outputs.get(item, {}).get("amount", 0.0)

        return output_amount - input_amount

    def calculate_device_count(
        self, recipe: Dict[str, Any], target_item: str, target_rate: float
    ) -> float:
        """
        基于净产出计算设备数量

        设备数 = 目标产出率 / 净产出率

        Args:
            recipe: 配方数据
            target_item: 目标产物名称
            target_rate: 目标生产速度（个/秒）

        Returns:
            所需设备数量
        """
        if target_rate == 0.0:
            return 0.0

        net_output = self.calculate_net_output_for_item(recipe, target_item)

        if net_output == 0.0:
            return 0.0

        return target_rate / net_output

    def _is_same_item_recipe(self, recipe: Dict[str, Any]) -> bool:
        """
        判断是否为同物品配方（输入输出包含相同物品）

        同物品配方是指输入和输出都包含同一物品的配方，
        如倍增配方 a->2*a 或损耗配方 2*a->a

        Args:
            recipe: 配方数据

        Returns:
            如果是同物品配方返回True
        """
        inputs = recipe.get("inputs", {})
        outputs = recipe.get("outputs", {})

        # 检查是否有物品同时存在于输入和输出中
        common_items = set(inputs.keys()) & set(outputs.keys())
        return len(common_items) > 0

    def get_net_consumption(self, recipe: Dict[str, Any]) -> Dict[str, float]:
        """
        获取净消耗（排除催化剂）

        对于同物品配方，返回输入量
        对于普通配方，净消耗 = 输入量（催化剂除外）

        Args:
            recipe: 配方数据

        Returns:
            净消耗字典，{物品名称: 消耗量}
        """
        inputs = recipe.get("inputs", {})
        outputs = recipe.get("outputs", {})
        catalysts = self._get_catalysts(recipe)

        net_consumption = {}
        for item, data in inputs.items():
            if item in catalysts:
                # 催化剂：如果是同物品配方，计算净消耗；否则排除
                if self._is_same_item_recipe(recipe):
                    # 同物品配方，计算实际净消耗（输入 - 输出）
                    input_amount = data.get("amount", 0.0)
                    output_amount = outputs.get(item, {}).get("amount", 0.0)
                    net_amount = input_amount - output_amount
                    if net_amount > 0:
                        net_consumption[item] = net_amount
            else:
                # 非催化剂，直接计入净消耗
                net_consumption[item] = data.get("amount", 0.0)

        return net_consumption

    def get_net_production(self, recipe: Dict[str, Any]) -> Dict[str, float]:
        """
        获取净产出（排除催化剂）

        对于同物品配方，净产出 = 输出量 - 输入量
        对于普通配方，净产出 = 输出量（催化剂除外）

        Args:
            recipe: 配方数据

        Returns:
            净产出字典，{物品名称: 净产出量}
        """
        inputs = recipe.get("inputs", {})
        outputs = recipe.get("outputs", {})
        catalysts = self._get_catalysts(recipe)

        net_production = {}
        for item, data in outputs.items():
            output_amount = data.get("amount", 0.0)
            input_amount = inputs.get(item, {}).get("amount", 0.0)

            if item in catalysts:
                # 催化剂：如果是同物品配方，计算净产出；否则排除
                if self._is_same_item_recipe(recipe):
                    net_amount = output_amount - input_amount
                    if net_amount != 0.0:
                        net_production[item] = net_amount
            else:
                # 非催化剂，直接计入净产出
                net_production[item] = output_amount

        return net_production

    def analyze_recipe(self, recipe: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析配方类型和特性

        识别配方类型（普通、倍增、损耗、催化剂、无效）并返回分析结果

        Args:
            recipe: 配方数据

        Returns:
            分析结果字典，包含：
            - type: RecipeType 枚举值
            - catalysts: 催化剂列表
            - net_outputs: 净产出字典
            - is_valid: 是否为有效生产配方
        """
        inputs = recipe.get("inputs", {})
        outputs = recipe.get("outputs", {})
        catalysts = self._get_catalysts(recipe)

        # 计算净产出
        net_outputs = {}
        has_positive_output = False
        has_negative_output = False

        for item in set(inputs.keys()) | set(outputs.keys()):
            net_output = self.calculate_net_output_for_item(recipe, item)
            if net_output != 0.0:
                net_outputs[item] = net_output
                if net_output > 0:
                    has_positive_output = True
                else:
                    has_negative_output = True

        # 确定配方类型
        recipe_type = RecipeType.NORMAL

        # 检查是否是同物品配方（输入输出有相同物品）
        is_same_item = self._is_same_item_recipe(recipe)

        if is_same_item:
            # 同物品配方：检查催化剂物品的净产出
            catalyst_has_nonzero_net = False
            for item in catalysts:
                net = net_outputs.get(item, 0.0)
                if net > 0:
                    recipe_type = RecipeType.DOUBLING
                    catalyst_has_nonzero_net = True
                    break
                elif net < 0:
                    recipe_type = RecipeType.LOSSY
                    catalyst_has_nonzero_net = True
                    break

            if not catalyst_has_nonzero_net:
                # 催化剂净产出为0，这是催化剂配方
                if catalysts:
                    recipe_type = RecipeType.CATALYST
                else:
                    # 没有催化剂但有同物品（理论上不应发生）
                    for item in net_outputs:
                        if item in inputs and item in outputs:
                            if net_outputs[item] > 0:
                                recipe_type = RecipeType.DOUBLING
                            else:
                                recipe_type = RecipeType.LOSSY
                            break
        elif catalysts:
            # 有催化剂但不是同物品配方
            recipe_type = RecipeType.CATALYST

        # 如果没有正产出且不是损耗配方，则为无效配方
        if not has_positive_output and recipe_type != RecipeType.LOSSY:
            recipe_type = RecipeType.INVALID

        return {
            "type": recipe_type,
            "catalysts": list(catalysts),
            "net_outputs": net_outputs,
            "is_valid": has_positive_output,
        }

    def is_valid_production_recipe(self, recipe: Dict[str, Any]) -> bool:
        """
        验证配方是否为有效的生产配方

        有效生产配方必须至少有一个正净产出

        Args:
            recipe: 配方数据

        Returns:
            如果是有效生产配方返回True
        """
        analysis = self.analyze_recipe(recipe)
        return analysis["is_valid"]


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
                        total_devices += 1.0 / max(first_output["amount"], 0.001)

            return (total_devices, len(path))

        # 按评分排序，选择最优路径
        sorted_paths = sorted(production_paths, key=calculate_path_score)
        return sorted_paths[0]

    def find_alternative_paths_at_node(
        self,
        node: "CraftingNode",
        all_paths: List[List["CraftingNode"]],
        current_path_id: int = 0,
    ) -> List[List["CraftingNode"]]:
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
        self, node1: "CraftingNode", node2: "CraftingNode"
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
        self, full_path: List["CraftingNode"], start_node: "CraftingNode"
    ) -> List["CraftingNode"]:
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
        main_path: List["CraftingNode"],
        alternative_paths: List[List["CraftingNode"]],
        calculator: "CraftingCalculator",
    ) -> "CraftingNode":
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

    def _mark_alternative_path(self, path: List["CraftingNode"], path_id: int):
        """
        标记替代路径上的节点

        Args:
            path: 替代路径节点列表
            path_id: 路径ID
        """
        for node in path:
            node.path_id = path_id
            node.is_alternative = True

    def _mark_main_path(self, path: List["CraftingNode"]):
        """
        标记主路径上的节点

        Args:
            path: 主路径节点列表
        """
        for node in path:
            node.path_id = 0
            node.is_alternative = False

    def _attach_alternative_paths_to_main(
        self, root: "CraftingNode", alternative_paths: List[List["CraftingNode"]]
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


class CraftingNode:
    """
    合成节点类，代表合成树中的一个节点

    支持路径对比功能，可以标记主路径和替代路径，存储路径标识信息。
    """

    def __init__(self, item_name: str, amount: float):
        """
        初始化合成节点

        Args:
            item_name: 物品名称
            amount: 生产速度（个/秒）
        """
        self.item_name = item_name
        self.amount = amount
        self.recipe = None  # 用于生产该物品的配方
        self.device_count = 0  # 需要的设备数量
        self.inputs = {}  # 输入物品字典，{物品名称: 数量}
        self.children = []  # 子节点列表（用于生产该物品的输入物品）
        self.parent = None  # 父节点

        # 路径对比相关字段
        self.alternative_paths: List[List["CraftingNode"]] = []  # 该节点的其他可选路径
        self.path_id: int = 0  # 路径唯一标识，0表示主路径
        self.is_alternative: bool = False  # 是否是替代路径上的节点

    def __str__(self):
        return (
            f"{self.item_name}: {self.amount:.2f}/s (设备数: {self.device_count:.2f})"
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式，方便JSON序列化

        Returns:
            节点的字典表示（包含路径对比信息）
        """
        # 序列化替代路径（只保存基本信息，避免循环引用）
        serialized_alternatives = []
        for alt_path in self.alternative_paths:
            serialized_path = [
                {
                    "item_name": node.item_name,
                    "amount": node.amount,
                    "device_count": node.device_count,
                    "path_id": node.path_id,
                    "is_alternative": node.is_alternative,
                }
                for node in alt_path
            ]
            serialized_alternatives.append(serialized_path)

        return {
            "item_name": self.item_name,
            "amount": self.amount,
            "device_count": self.device_count,
            "recipe": self.recipe if self.recipe else {},
            "inputs": self.inputs,
            "children": [child.to_dict() for child in self.children],
            "path_info": {
                "path_id": self.path_id,
                "is_alternative": self.is_alternative,
                "alternative_count": len(self.alternative_paths),
            },
            "alternative_paths": serialized_alternatives,
        }


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

    def calculate_production_chain(
        self, target_item: str, target_rate: float
    ) -> List[Dict[str, Any]]:
        """
        计算生产链

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

    def _item_exists(self, item_name: str) -> bool:
        """
        检查物品是否存在于任何配方的输入或输出中

        Args:
            item_name: 物品名称

        Returns:
            如果物品存在于任何配方中返回True
        """
        for recipe in self.recipes.values():
            # 检查输入物品
            for input_item in recipe.get("inputs", {}).keys():
                if input_item.strip() == item_name:
                    return True
            # 检查输出物品
            for output_item in recipe.get("outputs", {}).keys():
                if output_item.strip() == item_name:
                    return True
        return False

    def find_production_paths(
        self, target_item: str, visited: Optional[Set[str]] = None
    ) -> List[List[Dict[str, Any]]]:
        """
        查找所有可能的生产路径

        Args:
            target_item: 目标产物名称
            visited: 已访问的物品集合，用于避免循环

        Returns:
            生产路径列表，每条路径是配方的列表
        """
        if visited is None:
            visited = set()

        # 避免循环
        if target_item in visited:
            return []

        visited.add(target_item)

        # 获取最新配方
        self.recipes = self.recipe_manager.get_all_recipes()

        # 查找所有能生产该物品的配方
        producing_recipes = self.recipe_manager.search_recipes_by_item(
            target_item, search_inputs=False, search_outputs=True
        )

        # 如果没有找到配方，说明是基础原料
        if not producing_recipes:
            visited.remove(target_item)
            return [[]]

        all_paths = []

        # 遍历所有能生产该物品的配方
        for recipe in producing_recipes:
            # 查找配方输入物品的所有可能路径
            input_paths_list = []

            # 检查每个输入物品是否有生产路径
            valid_inputs = True
            for input_item in recipe["inputs"]:
                input_paths = self.find_production_paths(input_item, visited.copy())
                if not input_paths:
                    # 某个输入物品无法生产，将其视为基础原料
                    # 继续处理其他输入物品，不中断循环
                    input_paths_list.append([[]])  # 基础原料，路径为空列表
                else:
                    input_paths_list.append(input_paths)

            if not input_paths_list:
                continue

            # 生成所有可能的组合路径
            combined_paths = self._combine_paths(input_paths_list)

            # 将当前配方添加到每条路径的开头
            for path in combined_paths:
                path.insert(0, recipe)
                all_paths.append(path)

        visited.remove(target_item)
        return all_paths

    def _combine_paths(
        self, paths_list: List[List[List[Dict[str, Any]]]]
    ) -> List[List[Dict[str, Any]]]:
        """
        组合多条路径列表，生成所有可能的路径组合

        Args:
            paths_list: 路径列表的列表

        Returns:
            组合后的路径列表
        """
        if not paths_list:
            return [[]]

        result = []
        first_paths = paths_list[0]
        remaining_paths = paths_list[1:]

        for first_path in first_paths:
            for rest_path in self._combine_paths(remaining_paths):
                result.append(first_path + rest_path)

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

        def traverse(node: CraftingNode) -> None:
            # 基础原料：没有配方且没有子节点的叶子节点
            if not node.recipe and not node.children:
                if node.item_name in raw_materials:
                    raw_materials[node.item_name] += node.amount
                else:
                    raw_materials[node.item_name] = node.amount
                return

            # 遍历子节点
            for child in node.children:
                traverse(child)

        traverse(tree)
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

        def traverse(node: CraftingNode):
            if node.recipe:
                device_name = node.recipe["device"]
                if device_name in device_stats:
                    device_stats[device_name] += node.device_count
                else:
                    device_stats[device_name] = node.device_count

            # 遍历子节点
            for child in node.children:
                traverse(child)

        traverse(tree)
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
                temp_root = self.build_crafting_tree(target_item, target_rate, path)
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
        path = []
        visited = set()

        def dfs(node: CraftingNode):
            if node.item_name in visited:
                return
            visited.add(node.item_name)
            path.append(node)
            for child in node.children:
                dfs(child)

        dfs(root)
        return path

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
        print(f"总设备数: {calculator._count_total_devices(tree_dict):.2f}")

        def print_tree(node_dict, indent=0):
            prefix = "  " * indent
            print(
                f"{prefix}{node_dict['item_name']}: {node_dict['amount']:.2f}/s (设备数: {node_dict['device_count']:.2f})"
            )
            for child in node_dict["children"]:
                print_tree(child, indent + 1)

        print_tree(tree_dict)
