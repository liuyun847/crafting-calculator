"""
配置管理模块

该模块负责应用程序配置的加载和保存，包括用户偏好设置等。
"""

import json
import os
from typing import Optional, Dict, Any


class ConfigManager:
    """
    配置管理器，负责配置文件的读写
    """
    
    def __init__(self, config_file: str = "config.json"):
        """
        初始化配置管理器
        
        Args:
            config_file: 配置文件路径，默认为项目根目录下的 config.json
        """
        self.config_file = config_file
        self.config: Dict[str, Any] = {}
        
        # 尝试加载配置文件
        self.load_config()
    
    def load_config(self) -> None:
        """
        加载配置文件
        
        如果配置文件不存在或格式错误，使用默认配置
        """
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"警告: 配置文件加载失败，使用默认配置: {e}")
            self.config = {}
    
    def save_config(self) -> None:
        """
        保存配置文件
        
        Raises:
            IOError: 当无法写入配置文件时
        """
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"错误: 无法保存配置文件: {e}")
            raise
    
    def get_last_game(self) -> Optional[str]:
        """
        获取上次选择的配方文件
        
        Returns:
            上次选择的配方文件名，如果不存在则返回 None
        """
        return self.config.get("last_game")
    
    def set_last_game(self, game_name: str) -> None:
        """
        设置上次选择的配方文件
        
        Args:
            game_name: 配方文件名
        """
        self.config["last_game"] = game_name
        self.save_config()


# 全局配置管理器实例
config_manager = ConfigManager()
