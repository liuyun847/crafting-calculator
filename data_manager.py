"""
数据管理模块

该模块负责配方数据的加载、保存和管理，支持多个游戏配方文件的管理。
"""

import os
import json
from typing import Dict, List, Any, Optional, Tuple


class RecipeManager:
    """
    配方管理器，负责配方的加载、保存和管理
    """
    
    def __init__(self, recipes_dir: str = "recipes"):
        """
        初始化配方管理器
        
        Args:
            recipes_dir: 配方文件存储目录
        """
        self.recipes_dir = recipes_dir
        self.current_game = None
        self.recipes = {}
        
        # 确保配方目录存在
        if not os.path.exists(self.recipes_dir):
            os.makedirs(self.recipes_dir)
    
    def get_available_games(self) -> List[str]:
        """
        获取所有可用的游戏配方文件名
        
        Returns:
            游戏名称列表（不含扩展名）
        """
        games = []
        if os.path.exists(self.recipes_dir):
            for filename in os.listdir(self.recipes_dir):
                if filename.endswith(".json"):
                    game_name = os.path.splitext(filename)[0]
                    games.append(game_name)
        return sorted(games)
    
    def load_recipe_file(self, game_name: str) -> Dict[str, Any]:
        """
        加载指定游戏的配方文件
        
        Args:
            game_name: 游戏名称
            
        Returns:
            加载的配方字典
            
        Raises:
            FileNotFoundError: 当配方文件不存在时
            json.JSONDecodeError: 当配方文件格式错误时
        """
        filename = os.path.join(self.recipes_dir, f"{game_name}.json")
        
        with open(filename, "r", encoding="utf-8") as f:
            self.recipes = json.load(f)
        
        self.current_game = game_name
        return self.recipes
    
    def save_recipe_file(self, game_name: Optional[str] = None) -> None:
        """
        保存当前配方到文件
        
        Args:
            game_name: 游戏名称，如果为None则使用当前游戏
            
        Raises:
            ValueError: 当未指定游戏名称且当前未加载任何游戏时
        """
        if game_name is None:
            if self.current_game is None:
                # 如果没有当前游戏，不执行保存操作
                return
            game_name = self.current_game
        
        filename = os.path.join(self.recipes_dir, f"{game_name}.json")
        
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(self.recipes, f, indent=2, ensure_ascii=False)
        
        self.current_game = game_name
    
    def add_recipe(self, recipe_name: str, device_name: str, inputs: Dict[str, Any], outputs: Dict[str, Any]) -> None:
        """
        添加新配方
        
        Args:
            recipe_name: 配方名称，作为配方的唯一标识符
            device_name: 设备名称
            inputs: 输入物品字典，格式为 {物品名称: {"amount": 数量, "expression": 原始表达式}}
            outputs: 输出物品字典，格式为 {物品名称: {"amount": 数量, "expression": 原始表达式}}
        """
        if recipe_name in self.recipes:
            raise ValueError(f"配方 '{recipe_name}' 已存在")
        
        recipe = {
            "device": device_name,
            "inputs": inputs,
            "outputs": outputs
        }
        
        self.recipes[recipe_name] = recipe
        
        self.save_recipe_file()
    
    def update_recipe(self, recipe_name: str, device_name: str, inputs: Dict[str, Any], outputs: Dict[str, Any]) -> None:
        """
        更新现有配方
        
        Args:
            recipe_name: 配方名称，作为配方的唯一标识符
            device_name: 设备名称
            inputs: 输入物品字典
            outputs: 输出物品字典
            
        Raises:
            KeyError: 当配方不存在时
        """
        if recipe_name not in self.recipes:
            raise KeyError(f"配方 '{recipe_name}' 不存在")
        
        recipe = {
            "device": device_name,
            "inputs": inputs,
            "outputs": outputs
        }
        
        self.recipes[recipe_name] = recipe
        
        self.save_recipe_file()
    
    def delete_recipe(self, recipe_name: str) -> None:
        """
        删除配方
        
        Args:
            recipe_name: 配方名称，作为配方的唯一标识符
            
        Raises:
            KeyError: 当配方不存在时
        """
        if recipe_name not in self.recipes:
            raise KeyError(f"配方 '{recipe_name}' 不存在")
        
        del self.recipes[recipe_name]
        
        # 自动保存配方
        self.save_recipe_file()
    
    def get_recipe(self, recipe_name: str) -> Dict[str, Any]:
        """
        获取指定配方
        
        Args:
            recipe_name: 配方名称，作为配方的唯一标识符
            
        Returns:
            配方字典
            
        Raises:
            KeyError: 当配方不存在时
        """
        if recipe_name not in self.recipes:
            raise KeyError(f"配方 '{recipe_name}' 不存在")
        
        return self.recipes[recipe_name]
    
    def get_all_recipes(self) -> Dict[str, Any]:
        """
        获取所有配方
        
        Returns:
            所有配方字典
        """
        return self.recipes
    
    def search_recipes_by_item(self, item_name: str, search_inputs: bool = True, search_outputs: bool = True) -> List[Dict[str, Any]]:
        """
        根据物品名称搜索配方
        
        Args:
            item_name: 物品名称
            search_inputs: 是否在输入物品中搜索
            search_outputs: 是否在输出物品中搜索
            
        Returns:
            匹配的配方列表
        """
        matching_recipes = []
        stripped_item_name = item_name.strip()
        seen_recipes = set()
        
        for recipe_name, recipe in self.recipes.items():
            # 在输入物品中搜索，忽略空格
            if search_inputs:
                for input_item in recipe["inputs"].keys():
                    if input_item.strip() == stripped_item_name:
                        if recipe_name not in seen_recipes:
                            matching_recipes.append(recipe)
                            seen_recipes.add(recipe_name)
                        break
            
            # 在输出物品中搜索，忽略空格
            if search_outputs:
                for output_item in recipe["outputs"].keys():
                    if output_item.strip() == stripped_item_name:
                        if recipe_name not in seen_recipes:
                            matching_recipes.append(recipe)
                            seen_recipes.add(recipe_name)
                        break
        
        return matching_recipes
    
    def create_new_recipe_file(self, game_name: str) -> None:
        """
        创建新的配方文件
        
        Args:
            game_name: 游戏名称
            
        Raises:
            FileExistsError: 当配方文件已存在时
        """
        filename = os.path.join(self.recipes_dir, f"{game_name}.json")
        
        if os.path.exists(filename):
            raise FileExistsError(f"游戏 '{game_name}' 的配方文件已存在")
        
        # 创建空配方字典
        self.recipes = {}
        self.current_game = game_name
        
        # 保存空文件
        self.save_recipe_file(game_name)
    
    def validate_recipe(self, recipe: Dict[str, Any]) -> bool:
        """
        验证配方格式是否正确
        
        Args:
            recipe: 要验证的配方字典
            
        Returns:
            配方格式是否正确
        """
        # 基础必填字段
        required_fields = ["device", "inputs", "outputs"]
        
        # 检查必填字段
        for field in required_fields:
            if field not in recipe:
                return False
        
        # 检查输入输出格式
        for item_dict in [recipe["inputs"], recipe["outputs"]]:
            if not isinstance(item_dict, dict):
                return False
            for item_name, item_data in item_dict.items():
                if not isinstance(item_data, dict):
                    return False
                
                if "amount" not in item_data or "expression" not in item_data:
                    return False
                
                if not isinstance(item_data["amount"], (int, float)):
                    return False
                
                # 验证表达式格式
                if not self._validate_expression(item_data["expression"]):
                    return False
        
        return True
    
    def _validate_expression(self, expression: str) -> bool:
        """
        验证表达式格式是否正确

        Args:
            expression: 要验证的表达式

        Returns:
            表达式是否有效
        """
        try:
            from expression_parser import parse_expression
            parse_expression(expression)
            return True
        except Exception:
            return False

    def get_device_frequency(self) -> List[Tuple[str, int]]:
        """
        获取设备名称及其使用频率，按频率降序排序

        Returns:
            设备名称及其使用频率的列表，格式为 [(设备名称, 频率), ...]
        """
        device_freq = {}
        for recipe in self.recipes.values():
            device = recipe.get("device", "")
            if device:
                device_freq[device] = device_freq.get(device, 0) + 1

        sorted_devices = sorted(device_freq.items(), key=lambda x: x[1], reverse=True)
        return sorted_devices

    def get_item_frequency(self) -> List[Tuple[str, int]]:
        """
        获取物品名称及其使用频率，按频率降序排序

        Returns:
            物品名称及其使用频率的列表，格式为 [(物品名称, 频率), ...]
        """
        item_freq = {}
        for recipe in self.recipes.values():
            for item_name in recipe.get("inputs", {}).keys():
                item_freq[item_name] = item_freq.get(item_name, 0) + 1
            for item_name in recipe.get("outputs", {}).keys():
                item_freq[item_name] = item_freq.get(item_name, 0) + 1

        sorted_items = sorted(item_freq.items(), key=lambda x: x[1], reverse=True)
        return sorted_items


# 全局配方管理器实例
recipe_manager = RecipeManager()
