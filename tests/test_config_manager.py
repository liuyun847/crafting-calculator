"""
配置管理器测试

测试 config_manager 模块的所有功能
"""
import pytest
import json
import os
from config_manager import ConfigManager


class TestConfigManagerInit:
    """测试 ConfigManager 初始化"""
    
    def test_default_init(self, temp_dir):
        """测试默认初始化"""
        config_file = os.path.join(temp_dir, "config.json")
        manager = ConfigManager(config_file=config_file)
        
        assert manager.config_file == config_file
        assert manager.config == {}
    
    def test_init_with_existing_config(self, sample_config_file):
        """测试使用现有配置文件初始化"""
        manager = ConfigManager(config_file=sample_config_file)
        
        assert manager.config == {"last_game": "example"}
    
    def test_init_with_invalid_json(self, invalid_json_file):
        """测试使用无效 JSON 文件初始化"""
        manager = ConfigManager(config_file=invalid_json_file)
        
        assert manager.config == {}
    
    def test_init_with_nonexistent_file(self, temp_dir):
        """测试使用不存在的文件初始化"""
        config_file = os.path.join(temp_dir, "nonexistent.json")
        manager = ConfigManager(config_file=config_file)
        
        assert manager.config == {}


class TestLoadConfig:
    """测试 load_config 方法"""
    
    def test_load_existing_config(self, sample_config_file):
        """测试加载存在的配置"""
        manager = ConfigManager(config_file=sample_config_file)
        manager.load_config()
        
        assert manager.config == {"last_game": "example"}
    
    def test_load_nonexistent_config(self, temp_dir):
        """测试加载不存在的配置"""
        config_file = os.path.join(temp_dir, "nonexistent.json")
        manager = ConfigManager(config_file=config_file)
        manager.load_config()
        
        assert manager.config == {}
    
    def test_load_invalid_json(self, invalid_json_file):
        """测试加载无效 JSON"""
        manager = ConfigManager(config_file=invalid_json_file)
        manager.load_config()
        
        assert manager.config == {}
    
    def test_load_complex_config(self, temp_dir):
        """测试加载复杂配置"""
        config_file = os.path.join(temp_dir, "complex.json")
        complex_config = {
            "last_game": "example",
            "theme": "dark",
            "language": "zh-CN",
            "settings": {
                "auto_save": True,
                "max_history": 100
            }
        }
        
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(complex_config, f)
        
        manager = ConfigManager(config_file=config_file)
        manager.load_config()
        
        assert manager.config == complex_config


class TestSaveConfig:
    """测试 save_config 方法"""
    
    def test_save_new_config(self, temp_dir):
        """测试保存新配置"""
        config_file = os.path.join(temp_dir, "new_config.json")
        manager = ConfigManager(config_file=config_file)
        
        manager.config = {"last_game": "test_game"}
        manager.save_config()
        
        with open(config_file, "r", encoding="utf-8") as f:
            saved_config = json.load(f)
        
        assert saved_config == {"last_game": "test_game"}
    
    def test_save_existing_config(self, sample_config_file):
        """测试更新现有配置"""
        manager = ConfigManager(config_file=sample_config_file)
        
        manager.config["last_game"] = "updated_game"
        manager.save_config()
        
        with open(sample_config_file, "r", encoding="utf-8") as f:
            saved_config = json.load(f)
        
        assert saved_config == {"last_game": "updated_game"}
    
    def test_save_complex_config(self, temp_dir):
        """测试保存复杂配置"""
        config_file = os.path.join(temp_dir, "complex.json")
        manager = ConfigManager(config_file=config_file)
        
        complex_config = {
            "last_game": "example",
            "theme": "dark",
            "language": "zh-CN",
            "settings": {
                "auto_save": True,
                "max_history": 100
            }
        }
        
        manager.config = complex_config
        manager.save_config()
        
        with open(config_file, "r", encoding="utf-8") as f:
            saved_config = json.load(f)
        
        assert saved_config == complex_config


class TestGetLastGame:
    """测试 get_last_game 方法"""
    
    def test_get_last_game_exists(self, sample_config_file):
        """测试获取存在的 last_game"""
        manager = ConfigManager(config_file=sample_config_file)
        
        last_game = manager.get_last_game()
        
        assert last_game == "example"
    
    def test_get_last_game_not_exists(self, temp_dir):
        """测试获取不存在的 last_game"""
        config_file = os.path.join(temp_dir, "empty.json")
        manager = ConfigManager(config_file=config_file)
        
        last_game = manager.get_last_game()
        
        assert last_game is None
    
    def test_get_last_game_empty_value(self, temp_dir):
        """测试获取空值的 last_game"""
        config_file = os.path.join(temp_dir, "empty_value.json")
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump({"last_game": ""}, f)
        
        manager = ConfigManager(config_file=config_file)
        
        last_game = manager.get_last_game()
        
        assert last_game == ""


class TestSetLastGame:
    """测试 set_last_game 方法"""
    
    def test_set_last_game_new(self, temp_dir):
        """测试设置新的 last_game"""
        config_file = os.path.join(temp_dir, "new.json")
        manager = ConfigManager(config_file=config_file)
        
        manager.set_last_game("test_game")
        
        assert manager.config["last_game"] == "test_game"
        
        with open(config_file, "r", encoding="utf-8") as f:
            saved_config = json.load(f)
        
        assert saved_config == {"last_game": "test_game"}
    
    def test_set_last_game_update(self, sample_config_file):
        """测试更新 last_game"""
        manager = ConfigManager(config_file=sample_config_file)
        
        manager.set_last_game("updated_game")
        
        assert manager.config["last_game"] == "updated_game"
        
        with open(sample_config_file, "r", encoding="utf-8") as f:
            saved_config = json.load(f)
        
        assert saved_config == {"last_game": "updated_game"}
    
    def test_set_last_game_multiple_times(self, temp_dir):
        """测试多次设置 last_game"""
        config_file = os.path.join(temp_dir, "multiple.json")
        manager = ConfigManager(config_file=config_file)
        
        manager.set_last_game("game1")
        assert manager.config["last_game"] == "game1"
        
        manager.set_last_game("game2")
        assert manager.config["last_game"] == "game2"
        
        manager.set_last_game("game3")
        assert manager.config["last_game"] == "game3"
        
        with open(config_file, "r", encoding="utf-8") as f:
            saved_config = json.load(f)
        
        assert saved_config == {"last_game": "game3"}


class TestEdgeCases:
    """测试边界情况"""
    
    def test_config_with_special_characters(self, temp_dir):
        """测试包含特殊字符的配置"""
        config_file = os.path.join(temp_dir, "special.json")
        manager = ConfigManager(config_file=config_file)
        
        manager.config = {
            "last_game": "游戏名称",
            "path": "C:\\路径\\文件.json",
            "unicode": "中文测试"
        }
        manager.save_config()
        
        with open(config_file, "r", encoding="utf-8") as f:
            saved_config = json.load(f)
        
        assert saved_config == manager.config
    
    def test_config_with_numbers(self, temp_dir):
        """测试包含数字的配置"""
        config_file = os.path.join(temp_dir, "numbers.json")
        manager = ConfigManager(config_file=config_file)
        
        manager.config = {
            "last_game": "game1",
            "count": 100,
            "ratio": 0.5,
            "is_active": True
        }
        manager.save_config()
        
        with open(config_file, "r", encoding="utf-8") as f:
            saved_config = json.load(f)
        
        assert saved_config == manager.config
    
    def test_config_with_nested_structure(self, temp_dir):
        """测试嵌套结构配置"""
        config_file = os.path.join(temp_dir, "nested.json")
        manager = ConfigManager(config_file=config_file)
        
        manager.config = {
            "last_game": "example",
            "settings": {
                "display": {
                    "theme": "dark",
                    "font_size": 14
                },
                "behavior": {
                    "auto_save": True,
                    "max_history": 100
                }
            }
        }
        manager.save_config()
        
        with open(config_file, "r", encoding="utf-8") as f:
            saved_config = json.load(f)
        
        assert saved_config == manager.config
    
    def test_config_with_empty_values(self, temp_dir):
        """测试包含空值的配置"""
        config_file = os.path.join(temp_dir, "empty_values.json")
        manager = ConfigManager(config_file=config_file)
        
        manager.config = {
            "last_game": "",
            "settings": {},
            "items": []
        }
        manager.save_config()
        
        with open(config_file, "r", encoding="utf-8") as f:
            saved_config = json.load(f)
        
        assert saved_config == manager.config


class TestIntegration:
    """测试集成场景"""
    
    def test_full_config_lifecycle(self, temp_dir):
        """测试完整的配置生命周期"""
        config_file = os.path.join(temp_dir, "lifecycle.json")
        manager = ConfigManager(config_file=config_file)
        
        assert manager.get_last_game() is None
        
        manager.set_last_game("game1")
        assert manager.get_last_game() == "game1"
        
        manager.set_last_game("game2")
        assert manager.get_last_game() == "game2"
        
        new_manager = ConfigManager(config_file=config_file)
        assert new_manager.get_last_game() == "game2"
    
    def test_multiple_managers_same_file(self, sample_config_file):
        """测试多个管理器操作同一文件"""
        manager1 = ConfigManager(config_file=sample_config_file)
        manager2 = ConfigManager(config_file=sample_config_file)
        
        assert manager1.get_last_game() == "example"
        assert manager2.get_last_game() == "example"
        
        manager1.set_last_game("game1")
        assert manager1.get_last_game() == "game1"
        
        manager2.load_config()
        assert manager2.get_last_game() == "game1"
