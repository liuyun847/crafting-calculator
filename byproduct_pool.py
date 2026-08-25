"""
副产品池模块

管理生产过程中产生的副产品，支持收集、消耗和溢出检测。
"""

from typing import Dict, List, Tuple


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