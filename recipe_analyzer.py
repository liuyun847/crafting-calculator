"""
配方分析模块

负责识别配方类型（普通/倍增/损耗/催化剂/无效），
计算配方的净产出、净消耗和设备数量。
"""

from enum import Enum
from typing import Any, Dict, Set

from shared.utils import (
    get_catalysts,
    calculate_net_output_for_item,
    is_same_item_recipe,
    get_net_consumption,
    get_net_production,
)


class RecipeType(Enum):
    """配方类型枚举"""

    NORMAL = "normal"  # 普通配方
    DOUBLING = "doubling"  # 倍增配方（产出 > 投入）
    LOSSY = "lossy"  # 损耗配方（产出 < 投入）
    CATALYST = "catalyst"  # 催化剂配方（有催化剂）
    INVALID = "invalid"  # 无效配方（净产出 <= 0）


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
        return get_catalysts(recipe)

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
        return calculate_net_output_for_item(recipe, item)

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
        return is_same_item_recipe(recipe)

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
        return get_net_consumption(recipe)

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
        return get_net_production(recipe)

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

        for item in set(inputs.keys()) | set(outputs.keys()):
            net_output = self.calculate_net_output_for_item(recipe, item)
            if net_output != 0.0:
                net_outputs[item] = net_output
                if net_output > 0:
                    has_positive_output = True

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