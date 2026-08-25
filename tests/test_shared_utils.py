"""
共享工具函数测试

测试 shared/utils 模块中的格式化与工具函数。
"""

import pytest

from shared.utils import format_device_count
from shared.utils import _format_precise_value


class TestFormatDeviceCount:
    """测试设备数量格式化"""

    def test_zero(self):
        """零设备数"""
        assert format_device_count(0.0) == "0"

    def test_integer_value(self):
        """整数精确值只显示整数，不冗余显示括号"""
        assert format_device_count(1.0) == "1"
        assert format_device_count(3.0) == "3"
        assert format_device_count(1000.0) == "1000"

    def test_normal_decimal(self):
        """常规小数显示 向上取整值(精确值)"""
        assert format_device_count(2.18) == "3(2.18)"
        assert format_device_count(2.5) == "3(2.50)"
        assert format_device_count(1.5) == "2(1.50)"

    def test_small_value_precision(self):
        """两位小数会归零时自动提高精度"""
        assert format_device_count(0.025) == "1(0.03)"
        assert format_device_count(0.0005) == "1(0.0005)"

    def test_extremely_small_value(self):
        """极小值（大于容差）：自动提高精度到不归零为止"""
        assert format_device_count(1e-7) == "1(0.0000001000)"

    def test_float_tolerance_boundary(self):
        """浮点容差：1e-9 内的偏差视为整数（防浮点噪声误判）"""
        assert format_device_count(1.0000000001) == "1"
        assert format_device_count(1.9999999999) == "2"
        # 小于容差的极小值近似为 0（1e-15 台设备物理上不可达）
        assert format_device_count(1e-15) == "0"

    def test_negative_values(self):
        """负数按向上取整处理（损耗配方场景）"""
        assert format_device_count(-10.0) == "-10"
        assert format_device_count(-10.5) == "-10(-10.50)"


class TestFormatPreciseValue:
    """测试精确值格式化内部函数"""

    def test_two_digits_default(self):
        """默认两位小数"""
        assert _format_precise_value(2.18) == "2.18"

    def test_auto_upgrade_precision(self):
        """两位归零自动升级精度"""
        assert _format_precise_value(0.025) == "0.03"
        assert _format_precise_value(0.0005) == "0.0005"

    def test_scientific_fallback(self):
        """10 位小数仍归零时用科学计数法"""
        assert _format_precise_value(1e-15) == "1.0e-15"