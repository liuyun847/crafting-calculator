"""
公共工具函数模块
提供项目中多个模块共享的通用功能
"""
from typing import Dict, List, Any, Set, Optional, TypeVar, Callable

T = TypeVar('T')


def get_catalysts(recipe: Dict[str, Any]) -> Set[str]:
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


def calculate_net_output_for_item(recipe: Dict[str, Any], item: str) -> float:
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


def is_same_item_recipe(recipe: Dict[str, Any]) -> bool:
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


def get_net_consumption(recipe: Dict[str, Any]) -> Dict[str, float]:
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
    catalysts = get_catalysts(recipe)

    net_consumption = {}
    for item, data in inputs.items():
        if item in catalysts:
            # 催化剂：如果是同物品配方，计算净消耗；否则排除
            if is_same_item_recipe(recipe):
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


def get_net_production(recipe: Dict[str, Any]) -> Dict[str, float]:
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
    catalysts = get_catalysts(recipe)

    net_production = {}
    for item, data in outputs.items():
        output_amount = data.get("amount", 0.0)
        input_amount = inputs.get(item, {}).get("amount", 0.0)

        if item in catalysts:
            # 催化剂：如果是同物品配方，计算净产出；否则排除
            if is_same_item_recipe(recipe):
                net_amount = output_amount - input_amount
                if net_amount != 0.0:
                    net_production[item] = net_amount
        else:
            # 非催化剂，直接计入净产出
            net_production[item] = output_amount

    return net_production


def merge_nested_dict(base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
    """
    递归合并两个嵌套字典

    Args:
        base: 基础字典
        update: 要合并的更新字典

    Returns:
        合并后的新字典
    """
    result = base.copy()
    for key, value in update.items():
        if isinstance(value, dict) and key in result and isinstance(result[key], dict):
            result[key] = merge_nested_dict(result[key], value)
        else:
            result[key] = value
    return result


def safe_get_nested_value(data: Dict[str, Any], path: str, default: Any = None) -> Any:
    """
    安全获取嵌套字典中的值

    Args:
        data: 字典数据
        path: 点分隔的路径，例如 "outputs.iron.amount"
        default: 默认值，如果路径不存在返回

    Returns:
        路径对应的值或默认值
    """
    keys = path.split('.')
    current = data
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    return current


def traverse_tree(
    root: T,
    child_accessor: Callable[[T], List[T]],
    callback: Callable[[T], None],
    post_order: bool = False
) -> None:
    """
    通用树结构遍历工具

    Args:
        root: 树的根节点
        child_accessor: 获取节点子节点的函数
        callback: 处理每个节点的回调函数
        post_order: 是否使用后序遍历，默认前序
    """
    if not post_order:
        callback(root)
    
    for child in child_accessor(root):
        traverse_tree(child, child_accessor, callback, post_order)
    
    if post_order:
        callback(root)


def flatten_tree(
    root: T,
    child_accessor: Callable[[T], List[T]],
    visited: Optional[Set[str]] = None,
    key_extractor: Optional[Callable[[T], str]] = None
) -> List[T]:
    """
    将树结构扁平化为列表

    Args:
        root: 树的根节点
        child_accessor: 获取节点子节点的函数
        visited: 已访问节点的集合，用于避免循环
        key_extractor: 提取节点唯一标识的函数，用于去重

    Returns:
        扁平化的节点列表
    """
    if visited is None:
        visited = set()
    
    result = []
    
    def dfs(node: T) -> None:
        if key_extractor:
            key = key_extractor(node)
            if key in visited:
                return
            visited.add(key)
        
        result.append(node)
        for child in child_accessor(node):
            dfs(child)
    
    dfs(root)
    return result


def _format_precise_value(count: float) -> str:
    """
    格式化设备精确值：默认两位小数，两位会归零时自动提高精度

    2/4/6/10 位小数依次尝试，全部归零（数值 < 1e-10）时改用科学计数法兜底。

    Args:
        count: 设备数量

    Returns:
        格式化后的精确值字符串
    """
    for digits in (2, 4, 6, 10):
        formatted = f"{count:.{digits}f}"
        if float(formatted) != 0.0:
            return formatted
    return f"{count:.1e}"


def format_device_count(count: float) -> str:
    """
    格式化设备数量显示：向上取整值(精确值)

    示例：2.18 → "3(2.18)"；精确值为整数时只显示整数（如 3.0 → "3"）；
    精确值极小（两位小数归零）时自动提高精度，如 0.0005 → "1(0.0005)"。

    前置条件：count 为非负设备数（由 required_rate/output_rate 计算得出）。
    负数极少出现（损耗配方），此时仍按向上取整处理，如 -10.5 → "-10(-10.50)"。

    Args:
        count: 设备数量（可能是小数）

    Returns:
        格式化字符串，如 "3(2.18)" 或 "3"
    """
    import math

    if count == 0.0:
        return "0"

    # 浮点容差判定是否为整数
    nearest = round(count)
    if abs(count - nearest) < 1e-9:
        return str(nearest)

    ceil_value = math.ceil(count - 1e-9)
    return f"{ceil_value}({_format_precise_value(count)})"


def ensure_directory_exists(directory_path: str) -> None:
    """
    确保目录存在，如果不存在则创建

    Args:
        directory_path: 目录路径
    """
    import os
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)


def save_yaml_file(file_path: str, data: Any, indent: int = 2, allow_unicode: bool = True) -> None:
    """
    保存数据到YAML文件，自动处理编码和格式

    Args:
        file_path: 文件路径
        data: 要保存的数据
        indent: 缩进空格数
        allow_unicode: 是否允许Unicode字符（不转义中文）
    """
    import yaml
    with open(file_path, "w", encoding="utf-8") as f:
        yaml.dump(
            data,
            f,
            indent=indent,
            allow_unicode=allow_unicode,
            sort_keys=False,
            default_flow_style=False,
        )


def load_yaml_file(file_path: str, default: Optional[Any] = None) -> Any:
    """
    从YAML文件加载数据，自动处理编码和异常

    Args:
        file_path: 文件路径
        default: 文件不存在或加载失败时返回的默认值

    Returns:
        加载的数据或默认值
    """
    import os
    import yaml
    if not os.path.exists(file_path):
        return default

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except (yaml.YAMLError, IOError):
        return default


__all__ = [
    'get_catalysts',
    'calculate_net_output_for_item',
    'is_same_item_recipe',
    'get_net_consumption',
    'get_net_production',
    'merge_nested_dict',
    'safe_get_nested_value',
    'traverse_tree',
    'flatten_tree',
    'format_device_count',
    'ensure_directory_exists',
    'save_yaml_file',
    'load_yaml_file',
]
