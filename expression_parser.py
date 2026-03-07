"""
表达式解析模块

该模块负责解析用户输入的复杂表达式，包括数学表达式和时间单位转换，
最终将所有产量数据统一转换为标准单位：个/秒。
"""

import re
import math
from typing import Union


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
    expression = expression.replace(' ', '')
    
    # 定义支持的时间单位
    supported_units = {'s', 'sec', 'second', 'm', 'min', 'minute', 'h', 'hour'}
    
    # 检查是否包含时间单位
    if '/' in expression:
        # 查找最后一个斜杠，作为数值和时间单位的分隔符
        last_slash_index = expression.rfind('/')
        
        # 解析时间单位部分
        time_unit = expression[last_slash_index+1:]
        
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
    
    Args:
        expression: 数学表达式字符串，支持 +, -, *, /, (), 数字和小数点
        
    Returns:
        表达式计算结果
        
    Raises:
        ValueError: 当表达式格式错误或无法计算时
    """
    # 移除空格，标准化输入
    expression = expression.replace(' ', '')
    
    # 验证表达式格式，允许字母函数名
    if not re.match(r'^[0-9a-zA-Z+\-*/().,]+$', expression):
        raise ValueError(f"无效的数学表达式: {expression}")
    
    try:
        # 使用eval计算表达式，注意：这里仅用于计算数学表达式，确保安全
        # 限制可用函数和变量，仅允许数学计算
        allowed_names = {
            'pi': math.pi,
            'e': math.e,
            'sin': math.sin,
            'cos': math.cos,
            'tan': math.tan,
            'asin': math.asin,
            'acos': math.acos,
            'atan': math.atan,
            'sqrt': math.sqrt,
            'pow': math.pow,
            'abs': abs,
            'round': round
        }
        
        result = eval(expression, {'__builtins__': {}}, allowed_names)
        return float(result)
    except Exception as e:
        raise ValueError(f"无法计算表达式 '{expression}': {str(e)}")


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
        's': 1,
        'sec': 1,
        'second': 1,
        'm': 60,
        'min': 60,
        'minute': 60,
        'h': 3600,
        'hour': 3600
    }
    
    if time_unit in unit_conversion:
        # 转换为个/秒
        return value / unit_conversion[time_unit]
    else:
        raise ValueError(f"不支持的时间单位: {time_unit}")


if __name__ == "__main__":
    # 测试示例
    test_cases = [
        "8*3/2",
        "15/min",
        "5*2/3/min",
        "(10+5)*2/60",
        "2.5*3.14/h"
    ]
    
    for test in test_cases:
        try:
            result = parse_expression(test)
            print(f"{test} -> {result} 个/秒")
        except ValueError as e:
            print(f"{test} -> 错误: {e}")
