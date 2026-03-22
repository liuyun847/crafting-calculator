"""
表达式解析器测试

测试 expression_parser 模块的所有功能
"""
import pytest
import math
from expression_parser import parse_expression, evaluate_math_expression, convert_time_unit


class TestParseExpression:
    """测试 parse_expression 函数"""

    def test_parse_expression_basic_math(self):
        """测试基础数学表达式"""
        assert parse_expression("8*3/2") == 12.0
        assert parse_expression("10+5") == 15.0
        assert parse_expression("20-8") == 12.0
        assert parse_expression("6*7") == 42.0
        assert parse_expression("15/3") == 5.0

    def test_parse_expression_complex_math(self):
        """测试复杂数学表达式"""
        assert parse_expression("(10+5)*2/60") == 0.5
        assert parse_expression("2.5*3.14") == pytest.approx(7.85)
        assert parse_expression("(-5+3)*2") == -4.0
        assert parse_expression("3+4*2/(1-5)") == pytest.approx(1.0)

    def test_parse_expression_time_units_second(self):
        """测试秒单位转换"""
        assert parse_expression("15/s") == 15.0
        assert parse_expression("15/sec") == 15.0
        assert parse_expression("15/second") == 15.0

    def test_parse_expression_time_units_minute(self):
        """测试分钟单位转换"""
        assert parse_expression("15/min") == 0.25
        assert parse_expression("15/m") == 0.25
        assert parse_expression("15/minute") == 0.25

    def test_parse_expression_time_units_hour(self):
        """测试小时单位转换"""
        assert parse_expression("15/h") == pytest.approx(0.004166666666666667)
        assert parse_expression(
            "15/hour") == pytest.approx(0.004166666666666667)

    def test_parse_expression_complex_with_time(self):
        """测试复合表达式和时间单位"""
        assert parse_expression(
            "5*2/3/min") == pytest.approx(0.05555555555555555)
        assert parse_expression(
            "2.5*3.14/h") == pytest.approx(0.0021805555555555556)
        assert parse_expression(
            "(10+5)*2/60/min") == pytest.approx(0.008333333333333333)

    def test_parse_expression_math_functions(self):
        """测试数学函数"""
        assert parse_expression("sin(pi/2)") == pytest.approx(1.0)
        assert parse_expression("cos(0)") == pytest.approx(1.0)
        assert parse_expression("sqrt(16)") == 4.0
        assert parse_expression("pow(2, 3)") == 8.0
        assert parse_expression("abs(-5)") == 5.0
        assert parse_expression("round(3.7)") == 4.0

    def test_parse_expression_constants(self):
        """测试数学常量"""
        assert parse_expression("pi") == pytest.approx(math.pi)
        assert parse_expression("e") == pytest.approx(math.e)

    def test_parse_expression_whitespace(self):
        """测试空格处理"""
        assert parse_expression("8 * 3 / 2") == 12.0
        assert parse_expression(" 15 / min ") == 0.25
        assert parse_expression(" ( 10 + 5 ) * 2 / 60 ") == 0.5

    def test_parse_expression_invalid_expression(self):
        """测试无效表达式"""
        with pytest.raises(ValueError):
            parse_expression("abc")

        with pytest.raises(ValueError):
            parse_expression("15/day")

        with pytest.raises(ValueError):
            parse_expression("5/0")

        with pytest.raises(ValueError):
            parse_expression("")

        with pytest.raises(ValueError):
            parse_expression("8@3")


class TestEvaluateMathExpression:
    """测试 evaluate_math_expression 函数"""

    def test_evaluate_basic_operations(self):
        """测试基础运算"""
        assert evaluate_math_expression("8*3/2") == 12.0
        assert evaluate_math_expression("10+5") == 15.0
        assert evaluate_math_expression("20-8") == 12.0
        assert evaluate_math_expression("6*7") == 42.0
        assert evaluate_math_expression("15/3") == 5.0

    def test_evaluate_parentheses(self):
        """测试括号优先级"""
        assert evaluate_math_expression("(10+5)*2") == 30.0
        assert evaluate_math_expression("10+(5*2)") == 20.0
        assert evaluate_math_expression("((2+3)*4)/5") == 4.0

    def test_evaluate_functions(self):
        """测试函数调用"""
        assert evaluate_math_expression("sin(pi/2)") == pytest.approx(1.0)
        assert evaluate_math_expression("sqrt(16)") == 4.0
        assert evaluate_math_expression("pow(2, 3)") == 8.0

    def test_evaluate_constants(self):
        """测试常量使用"""
        assert evaluate_math_expression("pi") == pytest.approx(math.pi)
        assert evaluate_math_expression("e") == pytest.approx(math.e)
        assert evaluate_math_expression("pi*2") == pytest.approx(math.pi * 2)

    def test_evaluate_invalid_expression(self):
        """测试无效表达式"""
        with pytest.raises(ValueError):
            evaluate_math_expression("abc")

        with pytest.raises(ValueError):
            evaluate_math_expression("8@3")

        with pytest.raises(ValueError):
            evaluate_math_expression("")

        with pytest.raises(ValueError):
            evaluate_math_expression("5/0")


class TestConvertTimeUnit:
    """测试 convert_time_unit 函数"""

    def test_convert_second(self):
        """测试秒单位转换"""
        assert convert_time_unit(15, "s") == 15.0
        assert convert_time_unit(15, "sec") == 15.0
        assert convert_time_unit(15, "second") == 15.0

    def test_convert_minute(self):
        """测试分钟单位转换"""
        assert convert_time_unit(15, "m") == 0.25
        assert convert_time_unit(15, "min") == 0.25
        assert convert_time_unit(15, "minute") == 0.25

    def test_convert_hour(self):
        """测试小时单位转换"""
        assert convert_time_unit(
            15, "h") == pytest.approx(0.004166666666666667)
        assert convert_time_unit(
            15, "hour") == pytest.approx(0.004166666666666667)

    def test_convert_zero(self):
        """测试零值"""
        assert convert_time_unit(0, "s") == 0.0
        assert convert_time_unit(0, "min") == 0.0
        assert convert_time_unit(0, "h") == 0.0

    def test_convert_negative(self):
        """测试负数"""
        assert convert_time_unit(-15, "s") == -15.0
        assert convert_time_unit(-15, "min") == -0.25

    def test_convert_invalid_unit(self):
        """测试不支持的时间单位"""
        with pytest.raises(ValueError):
            convert_time_unit(15, "day")

        with pytest.raises(ValueError):
            convert_time_unit(15, "week")

        with pytest.raises(ValueError):
            convert_time_unit(15, "ms")


class TestEdgeCases:
    """测试边界情况"""

    def test_very_large_numbers(self):
        """测试极大数值"""
        result = parse_expression("1e10/min")
        assert result == pytest.approx(166666666.66666666)

    def test_very_small_numbers(self):
        """测试极小数值"""
        result = parse_expression("1e-10/s")
        assert result == pytest.approx(1e-10)

    def test_decimal_precision(self):
        """测试小数精度"""
        result = parse_expression("1/3")
        assert result == pytest.approx(0.3333333333333333)

    def test_nested_parentheses(self):
        """测试嵌套括号"""
        result = parse_expression("(((1+2)*3)/2)")
        assert result == 4.5

    def test_multiple_operations(self):
        """测试多个运算"""
        result = parse_expression("1+2+3+4+5")
        assert result == 15.0

        result = parse_expression("10-2-3-1")
        assert result == 4.0


class TestRealWorldExamples:
    """测试实际应用场景"""

    def test_production_rate_examples(self):
        """测试生产速度示例"""
        assert parse_expression("15/min") == 0.25
        assert parse_expression("60/min") == 1.0
        assert parse_expression("120/min") == 2.0
        assert parse_expression("3600/h") == 1.0

    def test_complex_production_rate(self):
        """测试复杂生产速度"""
        assert parse_expression(
            "5*2/3/min") == pytest.approx(0.05555555555555555)
        assert parse_expression(
            "(10+5)*2/60/min") == pytest.approx(0.008333333333333333)
        assert parse_expression(
            "2.5*3.14/h") == pytest.approx(0.0021805555555555556)

    def test_factorio_style(self):
        """测试异星工厂风格的表达式"""
        assert parse_expression("15/s") == 15.0
        assert parse_expression("60/min") == 1.0
        assert parse_expression("3600/h") == 1.0
