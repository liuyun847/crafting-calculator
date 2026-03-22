"""
IO 接口测试

测试 io_interface 模块的所有功能
"""
import pytest
from io_interface import IOInterface, TerminalIO, WebIO


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


class TestWebIO:
    """测试 WebIO 类"""

    def test_basic_init(self, web_io):
        """测试基本初始化"""
        assert web_io is not None
        assert web_io.output_buffer == []
        assert web_io.input_queue == []

    def test_print(self, web_io):
        """测试输出到缓冲区"""
        web_io.print("测试消息")

        assert len(web_io.output_buffer) == 1
        assert web_io.output_buffer[0] == "测试消息"

    def test_print_multiple(self, web_io):
        """测试多次输出"""
        web_io.print("第一行")
        web_io.print("第二行")
        web_io.print("第三行")

        assert len(web_io.output_buffer) == 3
        assert web_io.output_buffer[0] == "第一行"
        assert web_io.output_buffer[1] == "第二行"
        assert web_io.output_buffer[2] == "第三行"

    def test_print_empty_string(self, web_io):
        """测试输出空字符串"""
        web_io.print("")

        assert len(web_io.output_buffer) == 1
        assert web_io.output_buffer[0] == ""

    def test_get_output(self, web_io):
        """测试获取所有输出"""
        web_io.print("第一行")
        web_io.print("第二行")

        output = web_io.get_output()

        assert output == "第一行\n第二行"

    def test_get_output_empty(self, web_io):
        """测试获取空输出"""
        output = web_io.get_output()

        assert output == ""

    def test_has_output(self, web_io):
        """测试检查输出"""
        assert web_io.has_output() is False

        web_io.print("测试")

        assert web_io.has_output() is True

    def test_set_input(self, web_io):
        """测试设置输入"""
        web_io.set_input("测试输入")

        assert len(web_io.input_queue) == 1
        assert web_io.input_queue[0] == "测试输入"

    def test_set_multiple_inputs(self, web_io):
        """测试设置多个输入"""
        web_io.set_input("输入1")
        web_io.set_input("输入2")
        web_io.set_input("输入3")

        assert len(web_io.input_queue) == 3
        assert web_io.input_queue[0] == "输入1"
        assert web_io.input_queue[1] == "输入2"
        assert web_io.input_queue[2] == "输入3"

    def test_input(self, web_io):
        """测试获取输入"""
        web_io.set_input("测试输入")

        result = web_io.input("提示: ")

        assert result == "测试输入"
        assert len(web_io.input_queue) == 0

    def test_input_multiple(self, web_io):
        """测试多次获取输入"""
        web_io.set_input("输入1")
        web_io.set_input("输入2")
        web_io.set_input("输入3")

        result1 = web_io.input("提示1: ")
        result2 = web_io.input("提示2: ")
        result3 = web_io.input("提示3: ")

        assert result1 == "输入1"
        assert result2 == "输入2"
        assert result3 == "输入3"
        assert len(web_io.input_queue) == 0

    def test_input_empty_queue(self, web_io):
        """测试空队列输入"""
        with pytest.raises(ValueError):
            web_io.input("提示: ")

    def test_has_input(self, web_io):
        """测试检查输入"""
        assert web_io.has_input() is False

        web_io.set_input("测试")

        assert web_io.has_input() is True

    def test_clear(self, web_io):
        """测试清空缓冲区"""
        web_io.print("第一行")
        web_io.print("第二行")

        assert len(web_io.output_buffer) == 2

        web_io.clear()

        assert len(web_io.output_buffer) == 0
        assert web_io.has_output() is False

    def test_clear_does_not_affect_input(self, web_io):
        """测试清空不影响输入队列"""
        web_io.set_input("输入1")
        web_io.set_input("输入2")

        web_io.clear()

        assert len(web_io.input_queue) == 2
        assert web_io.has_input() is True

    def test_print_and_get_output_cycle(self, web_io):
        """测试输出和获取循环"""
        web_io.print("消息1")
        output1 = web_io.get_output()

        web_io.clear()  # 清空缓冲区后再输出第二条
        web_io.print("消息2")
        output2 = web_io.get_output()

        assert output1 == "消息1"
        assert output2 == "消息2"

    def test_input_and_set_input_cycle(self, web_io):
        """测试输入和设置循环"""
        web_io.set_input("输入1")
        result1 = web_io.input("提示1: ")

        web_io.set_input("输入2")
        result2 = web_io.input("提示2: ")

        assert result1 == "输入1"
        assert result2 == "输入2"


class TestWebIOEdgeCases:
    """测试 WebIO 边界情况"""

    def test_very_long_output(self, web_io):
        """测试超长输出"""
        long_text = "A" * 10000
        web_io.print(long_text)

        assert len(web_io.output_buffer) == 1
        assert web_io.output_buffer[0] == long_text

    def test_special_characters_in_output(self, web_io):
        """测试输出中的特殊字符"""
        special_text = "特殊字符: \n\t\r\\\"'"
        web_io.print(special_text)

        assert web_io.output_buffer[0] == special_text

    def test_unicode_in_output(self, web_io):
        """测试输出中的 Unicode"""
        unicode_text = "中文 日本語 한국어 Ελληνικά العربية"
        web_io.print(unicode_text)

        assert web_io.output_buffer[0] == unicode_text

    def test_empty_input_string(self, web_io):
        """测试空输入字符串"""
        web_io.set_input("")

        result = web_io.input("提示: ")

        assert result == ""

    def test_whitespace_input(self, web_io):
        """测试空白输入"""
        web_io.set_input("   ")

        result = web_io.input("提示: ")

        assert result == "   "

    def test_multiple_clear_operations(self, web_io):
        """测试多次清空操作"""
        web_io.print("消息1")
        web_io.print("消息2")

        web_io.clear()
        web_io.clear()
        web_io.clear()

        assert len(web_io.output_buffer) == 0

    def test_interleaved_print_and_input(self, web_io):
        """测试交替输出和输入"""
        web_io.print("输出1")
        web_io.set_input("输入1")
        web_io.print("输出2")
        web_io.set_input("输入2")

        output = web_io.get_output()
        input1 = web_io.input("提示1: ")
        input2 = web_io.input("提示2: ")

        assert "输出1" in output
        assert "输出2" in output
        assert input1 == "输入1"
        assert input2 == "输入2"


class TestWebIOIntegration:
    """测试 WebIO 集成场景"""

    def test_full_output_cycle(self, web_io):
        """测试完整输出循环"""
        messages = ["消息1", "消息2", "消息3"]

        for msg in messages:
            web_io.print(msg)

        output = web_io.get_output()

        for msg in messages:
            assert msg in output

    def test_full_input_cycle(self, web_io):
        """测试完整输入循环"""
        inputs = ["输入1", "输入2", "输入3"]

        for inp in inputs:
            web_io.set_input(inp)

        results = []
        while web_io.has_input():
            results.append(web_io.input("提示: "))

        assert results == inputs

    def test_mixed_io_cycle(self, web_io):
        """测试混合输入输出循环"""
        web_io.print("输出1")
        web_io.set_input("输入1")
        web_io.print("输出2")
        web_io.set_input("输入2")
        web_io.print("输出3")

        output = web_io.get_output()
        input1 = web_io.input("提示1: ")
        input2 = web_io.input("提示2: ")

        assert "输出1" in output
        assert "输出2" in output
        assert "输出3" in output
        assert input1 == "输入1"
        assert input2 == "输入2"
