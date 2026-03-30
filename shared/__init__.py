"""
共享模块
包含跨应用的公共API、工具函数等
"""

__version__ = "1.0.0"

from .security import get_flask_secret_key

__all__ = ["get_flask_secret_key"]
