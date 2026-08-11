"""
自动化建造游戏通用合成计算器 - 主程序入口

该文件是应用程序的入口点，负责初始化和启动终端界面。
"""

import sys

from io_interface import TerminalIO
from application_controller import ApplicationController


USAGE = """\
用法: python main.py [-h]

自动化建造游戏通用合成计算器 - 终端交互式合成树计算器。

启动后进入交互式 REPL，可用命令包括:
  games                                列出所有配方文件
  use <文件名>                          选择配方文件
  game                                 显示当前配方文件
  calc <物品> <速度>                   计算生产链（主路径）
  alts <物品> <速度> <节点编号>        查看节点替代路径
  use-path <物品> <速度> <节点编号> <路径编号>  切换到指定替代路径
  items                                列出所有物品
  recipes [页码] [搜索词]              列出配方
  recipe <名称>                        查看配方详情
  recipe add/set-device/set-inputs/set-outputs/delete ...
  help                                 显示 REPL 内帮助
  quit                                 退出

速度支持表达式（如 15/min、8*3/2）。命令大小写不敏感。
"""


def main():
    """
    主函数，启动应用程序
    """
    args = sys.argv[1:]
    if any(a in ("-h", "--help") for a in args):
        print(USAGE)
        sys.exit(0)
    io = TerminalIO()
    controller = ApplicationController(io)
    controller.run()


if __name__ == "__main__":
    main()
