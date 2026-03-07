"""
数据管理器测试

测试 data_manager 模块的所有功能
"""
import pytest
import json
import os
from data_manager import RecipeManager


class TestRecipeManagerInit:
    """测试 RecipeManager 初始化"""
    
    def test_default_init(self, temp_dir):
        """测试默认初始化"""
        manager = RecipeManager(recipes_dir=temp_dir)
        
        assert manager.recipes_dir == temp_dir
        assert manager.current_game is None
        assert manager.recipes == {}
    
    def test_init_creates_directory(self, temp_dir):
        """测试初始化时自动创建目录"""
        new_dir = os.path.join(temp_dir, "new_recipes")
        assert not os.path.exists(new_dir)
        
        manager = RecipeManager(recipes_dir=new_dir)
        
        assert os.path.exists(new_dir)
        assert manager.recipes_dir == new_dir


class TestGetAvailableGames:
    """测试 get_available_games 方法"""
    
    def test_empty_directory(self, temp_dir):
        """测试空目录"""
        manager = RecipeManager(recipes_dir=temp_dir)
        games = manager.get_available_games()
        
        assert games == []
    
    def test_single_file(self, temp_dir):
        """测试单个文件"""
        with open(os.path.join(temp_dir, "game1.json"), "w", encoding="utf-8") as f:
            json.dump({}, f)
        
        manager = RecipeManager(recipes_dir=temp_dir)
        games = manager.get_available_games()
        
        assert games == ["game1"]
    
    def test_multiple_files(self, temp_dir):
        """测试多个文件"""
        for name in ["game1", "game2", "game3"]:
            with open(os.path.join(temp_dir, f"{name}.json"), "w", encoding="utf-8") as f:
                json.dump({}, f)
        
        manager = RecipeManager(recipes_dir=temp_dir)
        games = manager.get_available_games()
        
        assert games == ["game1", "game2", "game3"]
    
    def test_sorted_results(self, temp_dir):
        """测试排序结果"""
        for name in ["zebra", "alpha", "beta"]:
            with open(os.path.join(temp_dir, f"{name}.json"), "w", encoding="utf-8") as f:
                json.dump({}, f)
        
        manager = RecipeManager(recipes_dir=temp_dir)
        games = manager.get_available_games()
        
        assert games == ["alpha", "beta", "zebra"]
    
    def test_ignores_non_json_files(self, temp_dir):
        """测试忽略非 JSON 文件"""
        with open(os.path.join(temp_dir, "game1.json"), "w", encoding="utf-8") as f:
            json.dump({}, f)
        with open(os.path.join(temp_dir, "readme.txt"), "w", encoding="utf-8") as f:
            f.write("readme")
        with open(os.path.join(temp_dir, "data.dat"), "w", encoding="utf-8") as f:
            f.write("data")
        
        manager = RecipeManager(recipes_dir=temp_dir)
        games = manager.get_available_games()
        
        assert games == ["game1"]


class TestLoadRecipeFile:
    """测试 load_recipe_file 方法"""
    
    def test_load_existing_file(self, temp_dir, sample_recipes):
        """测试加载存在的文件"""
        recipe_file = os.path.join(temp_dir, "test_game.json")
        with open(recipe_file, "w", encoding="utf-8") as f:
            json.dump(sample_recipes, f)
        
        manager = RecipeManager(recipes_dir=temp_dir)
        loaded_recipes = manager.load_recipe_file("test_game")
        
        assert loaded_recipes == sample_recipes
        assert manager.current_game == "test_game"
    
    def test_load_nonexistent_file(self, temp_dir):
        """测试加载不存在的文件"""
        manager = RecipeManager(recipes_dir=temp_dir)
        
        with pytest.raises(FileNotFoundError):
            manager.load_recipe_file("nonexistent")
    
    def test_load_invalid_json(self, temp_dir):
        """测试加载无效 JSON"""
        invalid_file = os.path.join(temp_dir, "invalid.json")
        with open(invalid_file, "w", encoding="utf-8") as f:
            f.write("{ invalid json")
        
        manager = RecipeManager(recipes_dir=temp_dir)
        
        with pytest.raises(json.JSONDecodeError):
            manager.load_recipe_file("invalid")


class TestSaveRecipeFile:
    """测试 save_recipe_file 方法"""
    
    def test_save_to_current_game(self, temp_dir, sample_recipes):
        """测试保存到当前游戏"""
        manager = RecipeManager(recipes_dir=temp_dir)
        manager.recipes = sample_recipes
        manager.current_game = "test_game"
        
        manager.save_recipe_file()
        
        recipe_file = os.path.join(temp_dir, "test_game.json")
        with open(recipe_file, "r", encoding="utf-8") as f:
            saved_recipes = json.load(f)
        
        assert saved_recipes == sample_recipes
    
    def test_save_to_specified_game(self, temp_dir, sample_recipes):
        """测试保存到指定游戏"""
        manager = RecipeManager(recipes_dir=temp_dir)
        manager.recipes = sample_recipes
        
        manager.save_recipe_file("new_game")
        
        assert manager.current_game == "new_game"
        
        recipe_file = os.path.join(temp_dir, "new_game.json")
        with open(recipe_file, "r", encoding="utf-8") as f:
            saved_recipes = json.load(f)
        
        assert saved_recipes == sample_recipes
    
    def test_save_without_current_game(self, temp_dir):
        """测试无当前游戏时的保存"""
        manager = RecipeManager(recipes_dir=temp_dir)
        manager.recipes = {"test": {}}
        manager.current_game = None
        
        manager.save_recipe_file()
        
        assert manager.current_game is None


class TestAddRecipe:
    """测试 add_recipe 方法"""
    
    def test_add_new_recipe(self, temp_dir, sample_recipe_data):
        """测试添加新配方"""
        manager = RecipeManager(recipes_dir=temp_dir)
        manager.current_game = "test_game"
        
        manager.add_recipe("新配方", "设备", sample_recipe_data["inputs"], sample_recipe_data["outputs"])
        
        assert "新配方" in manager.recipes
        assert manager.recipes["新配方"]["device"] == "设备"
        
        recipe_file = os.path.join(temp_dir, "test_game.json")
        with open(recipe_file, "r", encoding="utf-8") as f:
            saved_recipes = json.load(f)
        
        assert "新配方" in saved_recipes
    
    def test_add_duplicate_recipe(self, temp_dir, sample_recipe_data):
        """测试添加重复配方"""
        manager = RecipeManager(recipes_dir=temp_dir)
        manager.current_game = "test_game"
        
        manager.add_recipe("配方1", "设备", sample_recipe_data["inputs"], sample_recipe_data["outputs"])
        
        with pytest.raises(ValueError):
            manager.add_recipe("配方1", "设备", sample_recipe_data["inputs"], sample_recipe_data["outputs"])


class TestGetRecipe:
    """测试 get_recipe 方法"""
    
    def test_get_existing_recipe(self, temp_dir, sample_recipe_data):
        """测试获取存在的配方"""
        manager = RecipeManager(recipes_dir=temp_dir)
        manager.recipes["配方1"] = sample_recipe_data
        
        recipe = manager.get_recipe("配方1")
        
        assert recipe == sample_recipe_data
    
    def test_get_nonexistent_recipe(self, temp_dir):
        """测试获取不存在的配方"""
        manager = RecipeManager(recipes_dir=temp_dir)
        
        with pytest.raises(KeyError):
            manager.get_recipe("不存在的配方")


class TestUpdateRecipe:
    """测试 update_recipe 方法"""
    
    def test_update_existing_recipe(self, temp_dir, sample_recipe_data):
        """测试更新存在的配方"""
        manager = RecipeManager(recipes_dir=temp_dir)
        manager.current_game = "test_game"
        manager.recipes["配方1"] = sample_recipe_data
        
        new_inputs = {"新原料": {"amount": 20.0, "expression": "20"}}
        manager.update_recipe("配方1", "新设备", new_inputs, sample_recipe_data["outputs"])
        
        assert manager.recipes["配方1"]["device"] == "新设备"
        assert manager.recipes["配方1"]["inputs"] == new_inputs
    
    def test_update_nonexistent_recipe(self, temp_dir, sample_recipe_data):
        """测试更新不存在的配方"""
        manager = RecipeManager(recipes_dir=temp_dir)
        
        with pytest.raises(KeyError):
            manager.update_recipe("不存在的配方", "设备", sample_recipe_data["inputs"], sample_recipe_data["outputs"])


class TestDeleteRecipe:
    """测试 delete_recipe 方法"""
    
    def test_delete_existing_recipe(self, temp_dir, sample_recipe_data):
        """测试删除存在的配方"""
        manager = RecipeManager(recipes_dir=temp_dir)
        manager.current_game = "test_game"
        manager.recipes["配方1"] = sample_recipe_data
        
        manager.delete_recipe("配方1")
        
        assert "配方1" not in manager.recipes
    
    def test_delete_nonexistent_recipe(self, temp_dir):
        """测试删除不存在的配方"""
        manager = RecipeManager(recipes_dir=temp_dir)
        
        with pytest.raises(KeyError):
            manager.delete_recipe("不存在的配方")


class TestGetAllRecipes:
    """测试 get_all_recipes 方法"""
    
    def test_get_empty_recipes(self, temp_dir):
        """测试获取空配方集"""
        manager = RecipeManager(recipes_dir=temp_dir)
        
        recipes = manager.get_all_recipes()
        
        assert recipes == {}
    
    def test_get_multiple_recipes(self, temp_dir, sample_recipe_data):
        """测试获取多个配方"""
        manager = RecipeManager(recipes_dir=temp_dir)
        manager.recipes["配方1"] = sample_recipe_data
        manager.recipes["配方2"] = sample_recipe_data
        
        recipes = manager.get_all_recipes()
        
        assert len(recipes) == 2
        assert "配方1" in recipes
        assert "配方2" in recipes


class TestSearchRecipesByItem:
    """测试 search_recipes_by_item 方法"""
    
    def test_search_in_inputs(self, temp_dir, sample_recipes):
        """测试在输入中搜索"""
        manager = RecipeManager(recipes_dir=temp_dir)
        manager.recipes = sample_recipes
        
        results = manager.search_recipes_by_item("铁矿石", search_inputs=True, search_outputs=False)
        
        assert len(results) == 1
        assert results[0]["device"] == "熔炉"
    
    def test_search_in_outputs(self, temp_dir, sample_recipes):
        """测试在输出中搜索"""
        manager = RecipeManager(recipes_dir=temp_dir)
        manager.recipes = sample_recipes
        
        results = manager.search_recipes_by_item("铁锭", search_inputs=False, search_outputs=True)
        
        assert len(results) == 1
        assert results[0]["device"] == "熔炉"
    
    def test_search_in_both(self, temp_dir, sample_recipes):
        """测试同时在输入和输出中搜索"""
        manager = RecipeManager(recipes_dir=temp_dir)
        manager.recipes = sample_recipes
        
        results = manager.search_recipes_by_item("铁锭", search_inputs=True, search_outputs=True)
        
        assert len(results) == 3
    
    def test_search_with_whitespace(self, temp_dir, sample_recipes):
        """测试空格处理"""
        manager = RecipeManager(recipes_dir=temp_dir)
        manager.recipes = sample_recipes
        
        results = manager.search_recipes_by_item(" 铁锭 ", search_inputs=True, search_outputs=True)
        
        assert len(results) == 3
    
    def test_search_nonexistent_item(self, temp_dir, sample_recipes):
        """测试搜索不存在的物品"""
        manager = RecipeManager(recipes_dir=temp_dir)
        manager.recipes = sample_recipes
        
        results = manager.search_recipes_by_item("不存在的物品")
        
        assert results == []
    
    def test_search_multiple_matches(self, temp_dir, sample_recipes):
        """测试多个匹配结果"""
        manager = RecipeManager(recipes_dir=temp_dir)
        manager.recipes = sample_recipes
        
        results = manager.search_recipes_by_item("煤炭", search_inputs=True, search_outputs=True)
        
        assert len(results) == 2


class TestValidateRecipe:
    """测试 validate_recipe 方法"""
    
    def test_valid_recipe(self, sample_recipe_data):
        """测试有效配方"""
        manager = RecipeManager()
        
        assert manager.validate_recipe(sample_recipe_data) is True
    
    def test_missing_required_fields(self):
        """测试缺少必填字段"""
        manager = RecipeManager()
        
        invalid_recipe = {"device": "设备"}
        assert manager.validate_recipe(invalid_recipe) is False
    
    def test_invalid_inputs_format(self):
        """测试无效输入格式"""
        manager = RecipeManager()
        
        invalid_recipe = {
            "device": "设备",
            "inputs": "invalid",
            "outputs": {}
        }
        assert manager.validate_recipe(invalid_recipe) is False
    
    def test_invalid_amount_type(self):
        """测试无效 amount 类型"""
        manager = RecipeManager()
        
        invalid_recipe = {
            "device": "设备",
            "inputs": {"原料": {"amount": "invalid", "expression": "1"}},
            "outputs": {}
        }
        assert manager.validate_recipe(invalid_recipe) is False
    
    def test_invalid_expression(self):
        """测试无效表达式"""
        manager = RecipeManager()
        
        invalid_recipe = {
            "device": "设备",
            "inputs": {"原料": {"amount": 1.0, "expression": "invalid"}},
            "outputs": {}
        }
        assert manager.validate_recipe(invalid_recipe) is False


class TestCreateNewRecipeFile:
    """测试 create_new_recipe_file 方法"""
    
    def test_create_new_file(self, temp_dir):
        """测试创建新文件"""
        manager = RecipeManager(recipes_dir=temp_dir)
        
        manager.create_new_recipe_file("new_game")
        
        assert manager.current_game == "new_game"
        assert manager.recipes == {}
        
        recipe_file = os.path.join(temp_dir, "new_game.json")
        assert os.path.exists(recipe_file)
    
    def test_create_existing_file(self, temp_dir):
        """测试创建已存在的文件"""
        manager = RecipeManager(recipes_dir=temp_dir)
        
        with open(os.path.join(temp_dir, "existing.json"), "w", encoding="utf-8") as f:
            json.dump({}, f)
        
        with pytest.raises(FileExistsError):
            manager.create_new_recipe_file("existing")


class TestGetDeviceFrequency:
    """测试 get_device_frequency 方法"""
    
    def test_empty_recipes(self):
        """测试空配方集"""
        manager = RecipeManager()
        
        freq = manager.get_device_frequency()
        
        assert freq == []
    
    def test_multiple_devices(self, sample_recipes):
        """测试多个设备"""
        manager = RecipeManager()
        manager.recipes = sample_recipes
        
        freq = manager.get_device_frequency()
        
        assert len(freq) > 0
        device_names = [name for name, count in freq]
        assert "熔炉" in device_names
        assert "组装机" in device_names
    
    def test_sorted_by_frequency(self, sample_recipes):
        """测试按频率排序"""
        manager = RecipeManager()
        manager.recipes = sample_recipes
        
        freq = manager.get_device_frequency()
        
        for i in range(len(freq) - 1):
            assert freq[i][1] >= freq[i+1][1]


class TestGetItemFrequency:
    """测试 get_item_frequency 方法"""
    
    def test_empty_recipes(self):
        """测试空配方集"""
        manager = RecipeManager()
        
        freq = manager.get_item_frequency()
        
        assert freq == []
    
    def test_multiple_items(self, sample_recipes):
        """测试多个物品"""
        manager = RecipeManager()
        manager.recipes = sample_recipes
        
        freq = manager.get_item_frequency()
        
        assert len(freq) > 0
        item_names = [name for name, count in freq]
        assert "铁矿石" in item_names
        assert "铁锭" in item_names
    
    def test_sorted_by_frequency(self, sample_recipes):
        """测试按频率排序"""
        manager = RecipeManager()
        manager.recipes = sample_recipes
        
        freq = manager.get_item_frequency()
        
        for i in range(len(freq) - 1):
            assert freq[i][1] >= freq[i+1][1]


class TestEdgeCases:
    """测试边界情况"""
    
    def test_recipe_with_special_characters(self, temp_dir):
        """测试包含特殊字符的配方"""
        manager = RecipeManager(recipes_dir=temp_dir)
        manager.current_game = "test_game"
        
        special_recipe = {
            "device": "设备",
            "inputs": {"原料A": {"amount": 1.0, "expression": "1"}},
            "outputs": {"产品B": {"amount": 1.0, "expression": "1"}}
        }
        
        manager.add_recipe("特殊配方", special_recipe["device"], special_recipe["inputs"], special_recipe["outputs"])
        
        assert "特殊配方" in manager.recipes
    
    def test_recipe_with_multiple_inputs_outputs(self, temp_dir):
        """测试多个输入输出的配方"""
        manager = RecipeManager(recipes_dir=temp_dir)
        manager.current_game = "test_game"
        
        multi_recipe = {
            "device": "设备",
            "inputs": {
                "原料A": {"amount": 1.0, "expression": "1"},
                "原料B": {"amount": 2.0, "expression": "2"},
                "原料C": {"amount": 3.0, "expression": "3"}
            },
            "outputs": {
                "产品X": {"amount": 1.0, "expression": "1"},
                "产品Y": {"amount": 2.0, "expression": "2"}
            }
        }
        
        manager.add_recipe("多配方", multi_recipe["device"], multi_recipe["inputs"], multi_recipe["outputs"])
        
        assert len(manager.recipes["多配方"]["inputs"]) == 3
        assert len(manager.recipes["多配方"]["outputs"]) == 2
