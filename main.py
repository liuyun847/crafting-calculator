"""
自动化建造游戏通用合成计算器 - 主程序入口

该文件是应用程序的入口点，负责初始化和启动终端界面。
"""

from io_interface import TerminalIO
from application_controller import ApplicationController


def main():
    """
    主函数，启动应用程序
    """
    io = TerminalIO()
    controller = ApplicationController(io)
    controller.run()


if __name__ == "__main__":
    main()
