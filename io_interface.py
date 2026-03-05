"""
输入输出抽象接口

提供统一的输入输出接口，支持终端和Web两种实现方式。
"""

from abc import ABC, abstractmethod
from typing import List


class IOInterface(ABC):
    """输入输出抽象接口"""

    @abstractmethod
    def print(self, text: str) -> None:
        """
        输出文本

        Args:
            text: 要输出的文本
        """
        pass

    @abstractmethod
    def input(self, prompt: str) -> str:
        """
        获取用户输入

        Args:
            prompt: 提示信息

        Returns:
            用户输入的文本
        """
        pass

    @abstractmethod
    def clear(self) -> None:
        """清空输出（可选）"""
        pass


class TerminalIO(IOInterface):
    """终端输入输出实现"""

    def print(self, text: str) -> None:
        """
        输出文本到终端

        Args:
            text: 要输出的文本
        """
        print(text)

    def input(self, prompt: str) -> str:
        """
        从终端获取用户输入

        Args:
            prompt: 提示信息

        Returns:
            用户输入的文本
        """
        return input(prompt)

    def clear(self) -> None:
        """清空输出（终端不需要清空）"""
        pass


class WebIO(IOInterface):
    """Web输入输出实现"""

    def __init__(self):
        """初始化WebIO"""
        self.output_buffer: List[str] = []
        self.input_queue: List[str] = []

    def print(self, text: str) -> None:
        """
        输出文本到缓冲区

        Args:
            text: 要输出的文本
        """
        self.output_buffer.append(text)

    def input(self, prompt: str) -> str:
        """
        从输入队列获取用户输入

        Args:
            prompt: 提示信息（Web模式下不显示）

        Returns:
            用户输入的文本

        Raises:
            ValueError: 当输入队列为空时
        """
        if not self.input_queue:
            raise ValueError("No input available")
        return self.input_queue.pop(0)

    def clear(self) -> None:
        """清空输出缓冲区"""
        self.output_buffer.clear()

    def get_output(self) -> str:
        """
        获取所有输出文本

        Returns:
            所有输出的文本，用换行符连接
        """
        return "\n".join(self.output_buffer)

    def set_input(self, text: str) -> None:
        """
        设置用户输入

        Args:
            text: 用户输入的文本
        """
        self.input_queue.append(text)

    def has_output(self) -> bool:
        """
        检查是否有输出

        Returns:
            是否有输出
        """
        return len(self.output_buffer) > 0

    def has_input(self) -> bool:
        """
        检查是否有输入

        Returns:
            是否有输入
        """
        return len(self.input_queue) > 0


__all__ = ["IOInterface", "TerminalIO", "WebIO"]
