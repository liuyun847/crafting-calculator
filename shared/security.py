"""
安全配置共享模块
提供 Flask 应用的安全配置功能，包括 Secret Key 管理等
"""
import os
import warnings
from typing import Optional


def get_flask_secret_key(app_name: str = "default") -> str:
    """
    获取 Flask 应用的 Secret Key

    优先级：
    1. 环境变量 FLASK_SECRET_KEY（生产环境必须设置）
    2. 固定的开发密钥（仅用于开发环境）

    Args:
        app_name: 应用名称，用于生成开发密钥的后缀

    Returns:
        Secret Key 字符串
    """
    key = os.environ.get("FLASK_SECRET_KEY")

    if key is None:
        # 开发环境使用固定密钥（便于调试和测试）
        key = f"dev-secret-key-for-{app_name}"
        # 在生产环境警告用户设置环境变量
        if os.environ.get("FLASK_ENV") == "production":
            warnings.warn(
                "生产环境应设置环境变量 FLASK_SECRET_KEY 以确保安全！",
                UserWarning,
                stacklevel=2,
            )

    return key
