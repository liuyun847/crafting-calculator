"""
pytest 配置和 fixtures

提供全局测试配置和共享的测试 fixtures
"""
import pytest
import tempfile
import shutil
import os
import json
from typing import Dict, Any, List
from pathlib import Path


@pytest.fixture
def temp_dir():
    """
    创建临时目录用于测试文件操作
    
    Yields:
        str: 临时目录路径
    """
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def sample_recipes() -> Dict[str, Any]:
    """
    提供示例配方数据
    
    Returns:
        dict: 示例配方字典
    """
    return {
        "铁矿冶炼": {
            "device": "熔炉",
            "inputs": {
                "铁矿石": {"amount": 10.0, "expression": "10"},
                "煤炭": {"amount": 5.0, "expression": "5"}
            },
            "outputs": {
                "铁锭": {"amount": 5.0, "expression": "5"}
            }
        },
        "铜矿冶炼": {
            "device": "熔炉",
            "inputs": {
                "铜矿石": {"amount": 10.0, "expression": "10"},
                "煤炭": {"amount": 5.0, "expression": "5"}
            },
            "outputs": {
                "铜锭": {"amount": 5.0, "expression": "5"}
            }
        },
        "钢板制造": {
            "device": "组装机",
            "inputs": {
                "铁锭": {"amount": 5.0, "expression": "5"}
            },
            "outputs": {
                "钢板": {"amount": 2.0, "expression": "2"}
            }
        },
        "特殊配方_催化剂": {
            "device": "化学设备",
            "inputs": {
                "催化剂": {"amount": 1.0, "expression": "1"},
                "原料A": {"amount": 5.0, "expression": "5"}
            },
            "outputs": {
                "催化剂": {"amount": 1.0, "expression": "1"},
                "产品B": {"amount": 3.0, "expression": "3"}
            }
        },
        "电路板制造": {
            "device": "组装机",
            "inputs": {
                "铁锭": {"amount": 2.0, "expression": "2"},
                "铜锭": {"amount": 2.0, "expression": "2"}
            },
            "outputs": {
                "电路板": {"amount": 1.0, "expression": "1"}
            }
        }
    }


@pytest.fixture
def sample_config() -> Dict[str, Any]:
    """
    提供示例配置数据
    
    Returns:
        dict: 示例配置字典
    """
    return {
        "last_game": "example"
    }


@pytest.fixture
def recipe_manager(temp_dir, sample_recipes):
    """
    创建 RecipeManager 实例并加载示例配方
    
    Args:
        temp_dir: 临时目录路径
        sample_recipes: 示例配方数据
        
    Yields:
        RecipeManager: 配方管理器实例
    """
    from data_manager import RecipeManager
    
    manager = RecipeManager(recipes_dir=temp_dir)
    
    recipe_file = os.path.join(temp_dir, "test_game.json")
    with open(recipe_file, "w", encoding="utf-8") as f:
        json.dump(sample_recipes, f, indent=2, ensure_ascii=False)
    
    manager.load_recipe_file("test_game")
    
    yield manager


@pytest.fixture
def calculator(recipe_manager):
    """
    创建 CraftingCalculator 实例
    
    Args:
        recipe_manager: 配方管理器实例
        
    Yields:
        CraftingCalculator: 计算器实例
    """
    from calculator import CraftingCalculator
    
    calc = CraftingCalculator(recipe_manager)
    yield calc


@pytest.fixture
def crafting_node():
    """
    创建 CraftingNode 实例
    
    Yields:
        CraftingNode: 合成节点实例
    """
    from calculator import CraftingNode
    
    node = CraftingNode("铁锭", 1.0)
    yield node


@pytest.fixture
def path_comparison_engine():
    """
    创建 PathComparisonEngine 实例
    
    Yields:
        PathComparisonEngine: 路径对比引擎实例
    """
    from calculator import PathComparisonEngine
    
    engine = PathComparisonEngine()
    yield engine


@pytest.fixture
def terminal_io():
    """
    创建 TerminalIO 实例
    
    Yields:
        TerminalIO: 终端 IO 实例
    """
    from io_interface import TerminalIO
    
    io = TerminalIO()
    yield io


@pytest.fixture
def web_io():
    """
    创建 WebIO 实例
    
    Yields:
        WebIO: Web IO 实例
    """
    from io_interface import WebIO
    
    io = WebIO()
    yield io


@pytest.fixture
def sample_recipe_data():
    """
    提供单个配方数据
    
    Returns:
        dict: 配方数据
    """
    return {
        "device": "测试设备",
        "inputs": {
            "原料A": {"amount": 10.0, "expression": "10"},
            "原料B": {"amount": 5.0, "expression": "5"}
        },
        "outputs": {
            "产品X": {"amount": 3.0, "expression": "3"}
        }
    }


@pytest.fixture
def sample_recipe_file(temp_dir, sample_recipes):
    """
    创建示例配方文件
    
    Args:
        temp_dir: 临时目录路径
        sample_recipes: 示例配方数据
        
    Yields:
        str: 配方文件路径
    """
    recipe_file = os.path.join(temp_dir, "example.json")
    with open(recipe_file, "w", encoding="utf-8") as f:
        json.dump(sample_recipes, f, indent=2, ensure_ascii=False)
    
    yield recipe_file


@pytest.fixture
def sample_config_file(temp_dir, sample_config):
    """
    创建示例配置文件
    
    Args:
        temp_dir: 临时目录路径
        sample_config: 示例配置数据
        
    Yields:
        str: 配置文件路径
    """
    config_file = os.path.join(temp_dir, "config.json")
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(sample_config, f, indent=2, ensure_ascii=False)
    
    yield config_file


@pytest.fixture
def invalid_json_file(temp_dir):
    """
    创建无效的 JSON 文件
    
    Args:
        temp_dir: 临时目录路径
        
    Yields:
        str: 无效 JSON 文件路径
    """
    invalid_file = os.path.join(temp_dir, "invalid.json")
    with open(invalid_file, "w", encoding="utf-8") as f:
        f.write("{ invalid json content")
    
    yield invalid_file


@pytest.fixture
def empty_recipe_file(temp_dir):
    """
    创建空的配方文件
    
    Args:
        temp_dir: 临时目录路径
        
    Yields:
        str: 空配方文件路径
    """
    empty_file = os.path.join(temp_dir, "empty.json")
    with open(empty_file, "w", encoding="utf-8") as f:
        json.dump({}, f)
    
    yield empty_file


@pytest.fixture
def complex_recipes():
    """
    提供复杂的配方数据（用于测试多路径和复杂计算）
    
    Returns:
        dict: 复杂配方字典
    """
    return {
        "铁矿开采": {
            "device": "采矿机",
            "inputs": {},
            "outputs": {
                "铁矿石": {"amount": 1.0, "expression": "1"}
            }
        },
        "铜矿开采": {
            "device": "采矿机",
            "inputs": {},
            "outputs": {
                "铜矿石": {"amount": 1.0, "expression": "1"}
            }
        },
        "煤矿开采": {
            "device": "采矿机",
            "inputs": {},
            "outputs": {
                "煤炭": {"amount": 1.0, "expression": "1"}
            }
        },
        "铁矿冶炼": {
            "device": "熔炉",
            "inputs": {
                "铁矿石": {"amount": 10.0, "expression": "10"},
                "煤炭": {"amount": 5.0, "expression": "5"}
            },
            "outputs": {
                "铁锭": {"amount": 5.0, "expression": "5"}
            }
        },
        "铜矿冶炼": {
            "device": "熔炉",
            "inputs": {
                "铜矿石": {"amount": 10.0, "expression": "10"},
                "煤炭": {"amount": 5.0, "expression": "5"}
            },
            "outputs": {
                "铜锭": {"amount": 5.0, "expression": "5"}
            }
        },
        "钢板制造": {
            "device": "组装机",
            "inputs": {
                "铁锭": {"amount": 5.0, "expression": "5"}
            },
            "outputs": {
                "钢板": {"amount": 2.0, "expression": "2"}
            }
        },
        "铜板制造": {
            "device": "组装机",
            "inputs": {
                "铜锭": {"amount": 5.0, "expression": "5"}
            },
            "outputs": {
                "铜板": {"amount": 2.0, "expression": "2"}
            }
        },
        "电路板制造": {
            "device": "组装机",
            "inputs": {
                "铁锭": {"amount": 2.0, "expression": "2"},
                "铜锭": {"amount": 2.0, "expression": "2"}
            },
            "outputs": {
                "电路板": {"amount": 1.0, "expression": "1"}
            }
        },
        "高级电路板制造": {
            "device": "高级组装机",
            "inputs": {
                "电路板": {"amount": 2.0, "expression": "2"},
                "钢板": {"amount": 1.0, "expression": "1"}
            },
            "outputs": {
                "高级电路板": {"amount": 1.0, "expression": "1"}
            }
        }
    }
