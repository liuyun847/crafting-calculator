"""
输入输出抽象接口

提供统一的输入输出接口，支持终端交互方式。
"""

from abc import ABC, abstractmethod


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


__all__ = ["IOInterface", "TerminalIO"]
