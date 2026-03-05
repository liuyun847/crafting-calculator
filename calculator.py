"""
计算引擎模块

该模块负责合成树构建、多路径选择和设备数量计算，支持特殊配方处理。
"""

from typing import Dict, List, Any, Optional, Set, Tuple
from data_manager import RecipeManager


class CraftingNode:
    """
    合成节点类，代表合成树中的一个节点
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
    
    def __str__(self):
        return f"{self.item_name}: {self.amount:.2f}/s (设备数: {self.device_count:.2f})"
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式，方便JSON序列化
        
        Returns:
            节点的字典表示
        """
        return {
            "item_name": self.item_name,
            "amount": self.amount,
            "device_count": self.device_count,
            "recipe": self.recipe if self.recipe else {},
            "inputs": self.inputs,
            "children": [child.to_dict() for child in self.children]
        }


class CraftingCalculator:
    """
    合成计算器，负责构建合成树和计算设备数量
    """
    
    def __init__(self, recipe_manager: RecipeManager):
        """
        初始化合成计算器
        
        Args:
            recipe_manager: 配方管理器实例
        """
        self.recipe_manager = recipe_manager
        self.recipes = recipe_manager.get_all_recipes()
    
    def calculate_production_chain(self, target_item: str, target_rate: float) -> List[Dict[str, Any]]:
        """
        计算生产链
        
        Args:
            target_item: 目标产物名称
            target_rate: 目标生产速度（个/秒）
            
        Returns:
            合成树列表，每个元素代表一种可能的生产路径
        """
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
    
    def find_production_paths(self, target_item: str, visited: Optional[Set[str]] = None) -> List[List[Dict[str, Any]]]:
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
        producing_recipes = self.recipe_manager.search_recipes_by_item(target_item, search_inputs=False, search_outputs=True)
        
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
    
    def _combine_paths(self, paths_list: List[List[List[Dict[str, Any]]]]) -> List[List[Dict[str, Any]]]:
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
    
    def build_crafting_tree(self, target_item: str, target_rate: float, path: List[Dict[str, Any]]) -> Optional[CraftingNode]:
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
            "catalysts": list(catalysts)
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
        
        Args:
            tree: 合成树的根节点
            
        Returns:
            基础原料消耗速度字典
        """
        raw_materials = {}
        
        def traverse(node: CraftingNode):
            # 如果是基础原料（没有配方）
            if not node.recipe:
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


if __name__ == "__main__":
    # 测试示例
    from data_manager import recipe_manager
    
    # 创建测试配方
    test_recipe = {
        "device": "熔炉",
        "inputs": {
            "矿石": {"amount": 1.0, "expression": "1"},
            "煤炭": {"amount": 0.5, "expression": "0.5"}
        },
        "outputs": {
            "铁锭": {"amount": 1.0, "expression": "1"}
        }
    }
    
    # 添加测试配方
    recipe_manager.create_new_recipe_file("test")
    recipe_manager.add_recipe(
        "熔炼",
        "熔炉",
        {"矿石": {"amount": 1.0, "expression": "1"}, "煤炭": {"amount": 0.5, "expression": "0.5"}},
        {"铁锭": {"amount": 1.0, "expression": "1"}}
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
            print(f"{prefix}{node_dict['item_name']}: {node_dict['amount']:.2f}/s (设备数: {node_dict['device_count']:.2f})")
            for child in node_dict['children']:
                print_tree(child, indent + 1)
        
        print_tree(tree_dict)
