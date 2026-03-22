"""
副产品池管理器测试模块

测试副产品池的核心功能，包括收集、消耗、溢出检测等。
"""
import pytest
from calculator import ByproductPool


@pytest.fixture
def byproduct_pool():
    """
    创建 ByproductPool 实例

    Yields:
        ByproductPool: 副产品池实例
    """
    pool = ByproductPool()
    yield pool
    pool.clear()


@pytest.fixture
def crude_oil_recipe():
    """
    提供原油炼制配方数据（多输出）

    Returns:
        dict: 配方数据
    """
    return {
        "device": "炼油厂",
        "inputs": {
            "原油": {"amount": 10.0, "expression": "10"}
        },
        "outputs": {
            "轻油": {"amount": 4.0, "expression": "4"},
            "重油": {"amount": 3.0, "expression": "3"},
            "石油气": {"amount": 3.0, "expression": "3"}
        }
    }


@pytest.mark.unit
def test_byproduct_collection(byproduct_pool, crude_oil_recipe):
    """
    测试副产品收集：多输出配方，目标产物轻油，收集重油和气到副产品池

    验证：
    1. 目标产物（轻油）不进入副产品池
    2. 非目标产物（重油、石油气）被正确收集到副产品池
    """
    recipe = crude_oil_recipe
    target_item = "轻油"
    device_count = 2.5  # 假设需要2.5个设备

    # 模拟生产过程，收集副产品
    for output_item, output_data in recipe["outputs"].items():
        if output_item != target_item:
            amount = output_data["amount"] * device_count
            byproduct_pool.add_byproduct(output_item, amount)

    # 验证副产品池中只有重油和石油气
    assert byproduct_pool.get_byproduct_amount("重油") == 7.5  # 3.0 * 2.5
    assert byproduct_pool.get_byproduct_amount("石油气") == 7.5  # 3.0 * 2.5
    assert byproduct_pool.get_byproduct_amount("轻油") == 0.0  # 目标产物不应在池中


@pytest.mark.unit
def test_priority_consume_byproduct(byproduct_pool):
    """
    测试优先消耗副产品：副产品池有重油=10/s，下游需要5/s，应完全由副产品满足

    验证：
    1. 实际消耗量等于需求量
    2. 剩余需求量为0
    3. 副产品池中剩余正确的数量
    """
    # 设置副产品池状态
    byproduct_pool.add_byproduct("重油", 10.0)

    # 下游需要5/s重油
    consumed, remaining = byproduct_pool.consume_byproduct("重油", 5.0)

    # 验证完全由副产品满足
    assert consumed == 5.0
    assert remaining == 0.0
    assert byproduct_pool.get_byproduct_amount("重油") == 5.0


@pytest.mark.unit
def test_insufficient_byproduct_supplement(byproduct_pool):
    """
    测试副产品不足补充：副产品池有重油=3/s，下游需要10/s，应补充生产7/s

    验证：
    1. 实际消耗量等于池中可用量
    2. 剩余需求量等于总需求减去池中可用量
    3. 副产品池被清空
    """
    # 设置副产品池状态
    byproduct_pool.add_byproduct("重油", 3.0)

    # 下游需要10/s重油
    consumed, remaining = byproduct_pool.consume_byproduct("重油", 10.0)

    # 验证消耗了池中所有可用量，剩余需要补充生产
    assert consumed == 3.0
    assert remaining == 7.0
    assert byproduct_pool.get_byproduct_amount("重油") == 0.0


@pytest.mark.unit
def test_byproduct_overflow_detection(byproduct_pool):
    """
    测试副产品溢出检测：副产品池有重油=100/s但无下游消耗，应检测为溢出

    验证：
    1. 超过阈值的副产品被检测为溢出
    2. 未超过阈值的副产品不被检测为溢出
    """
    # 设置副产品池状态（超过默认阈值100）
    byproduct_pool.add_byproduct("重油", 100.0)
    byproduct_pool.add_byproduct("石油气", 150.0)  # 超过阈值
    byproduct_pool.add_byproduct("轻油", 50.0)  # 未超过阈值

    # 检测溢出
    excess_items = byproduct_pool.get_excess_byproducts()

    # 验证溢出检测
    assert "石油气" in excess_items
    assert "重油" not in excess_items  # 等于阈值，不算溢出
    assert "轻油" not in excess_items


@pytest.mark.unit
def test_add_byproduct_accumulation(byproduct_pool):
    """
    测试副产品添加的累积效果

    验证多次添加同一副产品会正确累加
    """
    byproduct_pool.add_byproduct("重油", 5.0)
    byproduct_pool.add_byproduct("重油", 3.0)
    byproduct_pool.add_byproduct("重油", 2.0)

    assert byproduct_pool.get_byproduct_amount("重油") == 10.0


@pytest.mark.unit
def test_consume_byproduct_exact_amount(byproduct_pool):
    """
    测试精确消耗副产品

    验证当需求量等于池中数量时，池被清空
    """
    byproduct_pool.add_byproduct("石油气", 5.0)

    consumed, remaining = byproduct_pool.consume_byproduct("石油气", 5.0)

    assert consumed == 5.0
    assert remaining == 0.0
    assert byproduct_pool.get_byproduct_amount("石油气") == 0.0


@pytest.mark.unit
def test_consume_nonexistent_byproduct(byproduct_pool):
    """
    测试消耗不存在的副产品

    验证当副产品不存在时，消耗量为0，剩余需求等于总需求
    """
    consumed, remaining = byproduct_pool.consume_byproduct("不存在物品", 10.0)

    assert consumed == 0.0
    assert remaining == 10.0


@pytest.mark.unit
def test_clear_byproduct_pool(byproduct_pool):
    """
    测试清空副产品池

    验证清空后所有副产品数量为0
    """
    byproduct_pool.add_byproduct("重油", 10.0)
    byproduct_pool.add_byproduct("石油气", 20.0)

    byproduct_pool.clear()

    assert byproduct_pool.get_byproduct_amount("重油") == 0.0
    assert byproduct_pool.get_byproduct_amount("石油气") == 0.0
    assert byproduct_pool.get_all_byproducts() == {}


@pytest.mark.unit
def test_multiple_byproducts_management(byproduct_pool):
    """
    测试多种副产品的综合管理

    验证可以同时管理多种不同的副产品
    """
    # 添加多种副产品
    byproduct_pool.add_byproduct("重油", 10.0)
    byproduct_pool.add_byproduct("石油气", 20.0)
    byproduct_pool.add_byproduct("轻油", 5.0)

    # 消耗部分副产品
    consumed, remaining = byproduct_pool.consume_byproduct("重油", 3.0)

    # 验证状态
    assert consumed == 3.0
    assert remaining == 0.0
    assert byproduct_pool.get_byproduct_amount("重油") == 7.0
    assert byproduct_pool.get_byproduct_amount("石油气") == 20.0
    assert byproduct_pool.get_byproduct_amount("轻油") == 5.0


@pytest.mark.unit
def test_get_excess_byproducts_empty_pool(byproduct_pool):
    """
    测试空副产品池的溢出检测

    验证空池不会报告任何溢出
    """
    excess_items = byproduct_pool.get_excess_byproducts()
    assert excess_items == []


@pytest.mark.unit
def test_partial_consume_multiple_items(byproduct_pool):
    """
    测试部分消耗多种副产品

    验证可以独立消耗不同种类的副产品
    """
    byproduct_pool.add_byproduct("重油", 10.0)
    byproduct_pool.add_byproduct("石油气", 15.0)

    # 消耗重油
    consumed_oil, remaining_oil = byproduct_pool.consume_byproduct("重油", 8.0)
    assert consumed_oil == 8.0
    assert remaining_oil == 0.0

    # 消耗石油气
    consumed_gas, remaining_gas = byproduct_pool.consume_byproduct("石油气", 20.0)
    assert consumed_gas == 15.0
    assert remaining_gas == 5.0

    # 验证最终状态
    assert byproduct_pool.get_byproduct_amount("重油") == 2.0
    assert byproduct_pool.get_byproduct_amount("石油气") == 0.0
