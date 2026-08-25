"""
合成节点模块

定义合成树的数据节点 CraftingNode，
支持路径对比功能的标记（主路径/替代路径、path_id 等）。
"""

from typing import Any, Dict, List

from shared.utils import format_device_count


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
            f"{self.item_name}: {self.amount:.2f}/s "
            f"(设备数: {format_device_count(self.device_count)})"
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