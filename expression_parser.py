"""
表达式解析模块

该模块负责解析用户输入的复杂表达式，包括数学表达式和时间单位转换，
最终将所有产量数据统一转换为标准单位：个/秒。
"""

import re
import math
import ast
from typing import Any


class SafeExpressionEvaluator:
    """
    安全的数学表达式求值器

    使用 AST 解析表达式，只允许白名单中的操作，防止代码注入攻击。
    """

    # 允许的数学函数
    ALLOWED_FUNCTIONS = {
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "asin": math.asin,
        "acos": math.acos,
        "atan": math.atan,
        "sqrt": math.sqrt,
        "pow": math.pow,
        "abs": abs,
        "round": round,
    }

    # 允许的常量
    ALLOWED_CONSTANTS = {
        "pi": math.pi,
        "e": math.e,
    }

    # 允许的二元运算符
    ALLOWED_OPERATORS = {
        ast.Add: lambda x, y: x + y,
        ast.Sub: lambda x, y: x - y,
        ast.Mult: lambda x, y: x * y,
        ast.Div: lambda x, y: x / y,
        ast.Pow: lambda x, y: x**y,
        ast.FloorDiv: lambda x, y: x // y,
        ast.Mod: lambda x, y: x % y,
    }

    # 允许的一元运算符
    ALLOWED_UNARY_OPERATORS = {
        ast.UAdd: lambda x: +x,
        ast.USub: lambda x: -x,
    }

    def __init__(self) -> None:
        """初始化安全表达式求值器"""
        pass

    def evaluate(self, expression: str) -> float:
        """
        安全地计算数学表达式

        Args:
            expression: 数学表达式字符串

        Returns:
            表达式计算结果

        Raises:
            ValueError: 当表达式包含不允许的操作或无法计算时
        """
        try:
            # 解析表达式为 AST
            tree = ast.parse(expression, mode="eval")
            # 遍历 AST 并计算结果
            result = self._visit(tree.body)
            return float(result)
        except ZeroDivisionError:
            raise ValueError(f"除零错误: '{expression}'")
        except (SyntaxError, TypeError, KeyError) as e:
            raise ValueError(f"无效的表达式 '{expression}': {str(e)}")

    def _visit(self, node: ast.AST) -> Any:
        """
        遍历 AST 节点并计算

        Args:
            node: AST 节点

        Returns:
            节点计算结果

        Raises:
            ValueError: 当遇到不允许的节点类型时
        """
        # 数字常量
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError(f"不支持的常量类型: {type(node.value).__name__}")

        # 二元运算
        if isinstance(node, ast.BinOp):
            if type(node.op) not in self.ALLOWED_OPERATORS:
                raise ValueError(f"不支持的运算符: {type(node.op).__name__}")
            left = self._visit(node.left)
            right = self._visit(node.right)
            return self.ALLOWED_OPERATORS[type(node.op)](left, right)

        # 一元运算（正负号）
        if isinstance(node, ast.UnaryOp):
            if type(node.op) not in self.ALLOWED_UNARY_OPERATORS:
                raise ValueError(f"不支持的一元运算符: {type(node.op).__name__}")
            operand = self._visit(node.operand)
            return self.ALLOWED_UNARY_OPERATORS[type(node.op)](operand)

        # 变量名（常量）
        if isinstance(node, ast.Name):
            if node.id in self.ALLOWED_CONSTANTS:
                return self.ALLOWED_CONSTANTS[node.id]
            raise ValueError(f"未知的变量名: {node.id}")

        # 函数调用
        if isinstance(node, ast.Call):
            # 只允许调用白名单中的函数
            if not isinstance(node.func, ast.Name):
                raise ValueError("只允许调用简单函数名，不允许属性访问")

            func_name = node.func.id
            if func_name not in self.ALLOWED_FUNCTIONS:
                raise ValueError(f"不支持的函数: {func_name}")

            # 计算所有参数
            args = [self._visit(arg) for arg in node.args]
            # 不支持关键字参数
            if node.keywords:
                raise ValueError("不支持关键字参数")

            return self.ALLOWED_FUNCTIONS[func_name](*args)

        # 括号表达式（实际上是 Expr 节点，但在 eval 模式下直接处理内部表达式）
        if isinstance(node, ast.Expression):
            return self._visit(node.body)

        # 拒绝所有其他节点类型
        raise ValueError(f"不允许的操作: {type(node).__name__}")


def parse_expression(expression: str) -> float:
    """
    解析复杂表达式，转换为标准单位（个/秒）

    Args:
        expression: 用户输入的表达式，如 '8*3/2'、'15/min'、'5*2/3/min'

    Returns:
        转换后的标准单位值（个/秒）

    Raises:
        ValueError: 当表达式格式错误或无法解析时
    """
    # 移除空格，标准化输入
    expression = expression.replace(" ", "")

    # 定义支持的时间单位
    supported_units = {"s", "sec", "second", "m", "min", "minute", "h", "hour"}

    # 检查是否包含时间单位
    if "/" in expression:
        # 查找最后一个斜杠，作为数值和时间单位的分隔符
        last_slash_index = expression.rfind("/")

        # 解析时间单位部分
        time_unit = expression[last_slash_index + 1 :]

        # 只有当时间单位是支持的单位时，才进行时间转换
        if time_unit in supported_units:
            # 解析数值部分
            value_part = expression[:last_slash_index]
            value = evaluate_math_expression(value_part)
            value = convert_time_unit(value, time_unit)
        else:
            # 否则将整个表达式作为纯数学表达式处理
            value = evaluate_math_expression(expression)
    else:
        # 纯数学表达式
        value = evaluate_math_expression(expression)

    return value


def evaluate_math_expression(expression: str) -> float:
    """
    评估数学表达式的值

    使用 AST 解析器安全地计算表达式，只允许基本数学运算、
    括号、数字、数学函数和常量。

    Args:
        expression: 数学表达式字符串，支持 +, -, *, /, **, //, %, (), 数字和小数点

    Returns:
        表达式计算结果

    Raises:
        ValueError: 当表达式格式错误或无法计算时
    """
    # 移除空格，标准化输入
    expression = expression.replace(" ", "")

    # 空表达式检查
    if not expression:
        raise ValueError("表达式不能为空")

    # 验证表达式格式，允许字母函数名
    if not re.match(r"^[0-9a-zA-Z+\-*/().,]+$", expression):
        raise ValueError(f"无效的数学表达式: {expression}")

    # 使用安全求值器计算表达式
    evaluator = SafeExpressionEvaluator()
    return evaluator.evaluate(expression)


def convert_time_unit(value: float, time_unit: str) -> float:
    """
    将不同时间单位转换为秒

    Args:
        value: 数值部分
        time_unit: 时间单位，支持 's', 'sec', 'second', 'm', 'min', 'minute', 'h', 'hour'

    Returns:
        转换为个/秒的值

    Raises:
        ValueError: 当时间单位不支持时
    """
    # 定义时间单位转换系数（秒）
    unit_conversion = {
        "s": 1,
        "sec": 1,
        "second": 1,
        "m": 60,
        "min": 60,
        "minute": 60,
        "h": 3600,
        "hour": 3600,
    }

    if time_unit in unit_conversion:
        # 转换为个/秒
        return value / unit_conversion[time_unit]
    else:
        raise ValueError(f"不支持的时间单位: {time_unit}")


if __name__ == "__main__":
    # 测试示例
    test_cases = ["8*3/2", "15/min", "5*2/3/min", "(10+5)*2/60", "2.5*3.14/h"]

    for test in test_cases:
        try:
            result = parse_expression(test)
            print(f"{test} -> {result} 个/秒")
        except ValueError as e:
            print(f"{test} -> 错误: {e}")
