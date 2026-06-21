"""
IO 接口测试

测试 io_interface 模块的所有功能
"""
import pytest
from io_interface import IOInterface, TerminalIO


class TestIOInterface:
    """测试 IOInterface 抽象类"""

    def test_abstract_methods(self):
        """测试抽象方法定义"""
        assert hasattr(IOInterface, 'print')
        assert hasattr(IOInterface, 'input')
        assert hasattr(IOInterface, 'clear')

    def test_cannot_instantiate(self):
        """测试不能实例化抽象类"""
        with pytest.raises(TypeError):
            IOInterface()


class TestTerminalIO:
    """测试 TerminalIO 类"""

    def test_basic_init(self, terminal_io):
        """测试基本初始化"""
        assert terminal_io is not None

    def test_print(self, terminal_io, capsys):
        """测试输出"""
        terminal_io.print("测试消息")

        captured = capsys.readouterr()
        assert "测试消息" in captured.out

    def test_print_multiple_lines(self, terminal_io, capsys):
        """测试多行输出"""
        terminal_io.print("第一行")
        terminal_io.print("第二行")
        terminal_io.print("第三行")

        captured = capsys.readouterr()
        assert "第一行" in captured.out
        assert "第二行" in captured.out
        assert "第三行" in captured.out

    def test_print_empty_string(self, terminal_io, capsys):
        """测试输出空字符串"""
        terminal_io.print("")

        captured = capsys.readouterr()
        assert captured.out.endswith("\n")

    def test_print_special_characters(self, terminal_io, capsys):
        """测试输出特殊字符"""
        terminal_io.print("特殊字符: !@#$%^&*()")

        captured = capsys.readouterr()
        assert "特殊字符: !@#$%^&*()" in captured.out

    def test_print_unicode(self, terminal_io, capsys):
        """测试输出 Unicode 字符"""
        terminal_io.print("中文测试")
        terminal_io.print("日本語テスト")
        terminal_io.print("한국어 테스트")

        captured = capsys.readouterr()
        assert "中文测试" in captured.out
        assert "日本語テスト" in captured.out
        assert "한국어 테스트" in captured.out

    def test_clear(self, terminal_io):
        """测试清空"""
        terminal_io.clear()

        pass

    def test_input(self, terminal_io, monkeypatch):
        """测试输入"""
        monkeypatch.setattr('builtins.input', lambda _: "测试输入")

        result = terminal_io.input("请输入: ")

        assert result == "测试输入"

    def test_input_empty(self, terminal_io, monkeypatch):
        """测试空输入"""
        monkeypatch.setattr('builtins.input', lambda _: "")

        result = terminal_io.input("请输入: ")

        assert result == ""
