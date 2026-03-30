"""
配方管理公共API模块
提供跨应用的配方CRUD、物品查询、分页搜索等通用功能
"""
import re
from typing import Dict, Any, List, Tuple
from flask import request, jsonify
from urllib.parse import unquote
from .session import get_session


def validate_recipe_name(name: str) -> Tuple[bool, str]:
    """
    验证配方名称是否安全，防止路径遍历攻击
    
    Args:
        name: 待验证的配方名称
        
    Returns:
        元组 (是否有效, 错误信息)
        - 有效时返回 (True, "")
        - 无效时返回 (False, "错误原因")
    """
    if not name:
        return False, "配方名称不能为空"
    
    if len(name) > 100:
        return False, "配方名称过长（最多100个字符）"
    
    # 检查 null byte 和控制字符
    if '\x00' in name:
        return False, "配方名称包含非法字符（null byte）"
    
    for char in name:
        if ord(char) < 32 and char not in '\t':
            return False, "配方名称包含非法控制字符"
    
    # 检查路径遍历相关字符
    dangerous_chars = ['/', '\\', '..']
    for char in dangerous_chars:
        if char in name:
            return False, f"配方名称不能包含路径分隔符或父目录引用"
    
    # 只允许：字母、数字、中文、下划线、连字符
    # \w 匹配 [a-zA-Z0-9_]
    # \u4e00-\u9fff 匹配中文基本区
    if not re.match(r'^[\w\u4e00-\u9fff\-]+$', name):
        return False, "配方名称只能包含字母、数字、中文、下划线和连字符"
    
    return True, ""


def get_games_api():
    """
    获取配方文件列表API
    
    Returns:
        JSON响应，包含游戏列表
    """
    web_session = get_session()
    games = web_session.controller.recipe_manager.get_available_games()
    return jsonify({"success": True, "games": games})


def select_game_api():
    """
    选择配方文件API
    
    Returns:
        JSON响应，包含选择结果
    """
    data = request.get_json()
    game_name = data.get("game", "")

    web_session = get_session()
    games = web_session.controller.recipe_manager.get_available_games()

    if game_name not in games:
        return jsonify({"success": False, "error": "配方文件不存在"}), 404

    try:
        web_session.controller.recipe_manager.load_recipe_file(game_name)
        web_session.controller.current_game = game_name
        from calculator import CraftingCalculator
        web_session.controller.calculator = CraftingCalculator(
            web_session.controller.recipe_manager
        )
        
        # 尝试更新配置（如果有config_manager）
        try:
            from config_manager import config_manager
            config_manager.set_last_game(game_name)
        except ImportError:
            pass

        return jsonify({
            "success": True,
            "message": f"已切换到配方文件: {game_name}",
            "game": game_name
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


def get_items_api():
    """
    获取物品列表API
    
    Returns:
        JSON响应，包含物品列表
    """
    web_session = get_session()
    controller = web_session.controller

    if not controller.calculator:
        return jsonify({"success": False, "error": "请先选择配方文件"}), 400

    recipes = controller.recipe_manager.get_all_recipes()
    items = set()
    for recipe in recipes.values():
        items.update(recipe.get("inputs", {}).keys())
        items.update(recipe.get("outputs", {}).keys())

    return jsonify({"success": True, "items": sorted(list(items))})


def get_recipes_api():
    """
    获取配方列表API（支持分页、搜索）
    
    Returns:
        JSON响应，包含分页后的配方列表
    """
    web_session = get_session()
    recipe_manager = web_session.controller.recipe_manager

    # 解析分页参数
    try:
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 20))
    except ValueError:
        return jsonify({"success": False, "error": "分页参数必须是整数"}), 400

    if page < 1:
        return jsonify({"success": False, "error": "页码必须大于0"}), 400
    if per_page < 1 or per_page > 100:
        return jsonify({"success": False, "error": "每页数量必须在1-100之间"}), 400

    # 获取所有配方
    all_recipes = recipe_manager.get_all_recipes()

    # 搜索过滤
    search = request.args.get("search", "").strip().lower()
    if search:
        filtered_recipes = {}
        for name, recipe in all_recipes.items():
            # 搜索配方名称
            if search in name.lower():
                filtered_recipes[name] = recipe
                continue
            # 搜索设备名称
            if search in recipe.get("device", "").lower():
                filtered_recipes[name] = recipe
                continue
            # 搜索物品名称
            inputs = recipe.get("inputs", {})
            outputs = recipe.get("outputs", {})
            for item_name in list(inputs.keys()) + list(outputs.keys()):
                if search in item_name.lower():
                    filtered_recipes[name] = recipe
                    break
        all_recipes = filtered_recipes

    # 计算分页
    total = len(all_recipes)
    total_pages = (total + per_page - 1) // per_page

    # 确保页码不超过最大页数
    if total > 0 and page > total_pages:
        page = total_pages

    # 获取当前页的数据
    start = (page - 1) * per_page
    end = start + per_page
    recipe_items = list(all_recipes.items())[start:end]

    # 构建返回的配方列表
    recipes = []
    for name, recipe in recipe_items:
        recipes.append({
            "name": name,
            "device": recipe.get("device", ""),
            "inputs": recipe.get("inputs", {}),
            "outputs": recipe.get("outputs", {}),
        })

    return jsonify({
        "success": True,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
        "recipes": recipes,
    })


def get_recipe_api(recipe_name: str):
    """
    获取单个配方详情API
    
    Args:
        recipe_name: 配方名称（URL编码）
    
    Returns:
        JSON响应，包含配方详情
    """
    # 解码URL编码的配方名称
    decoded_name = unquote(recipe_name)
    
    # 验证配方名称安全性
    is_valid, error_msg = validate_recipe_name(decoded_name)
    if not is_valid:
        return jsonify({"success": False, "error": error_msg}), 400

    web_session = get_session()
    recipe_manager = web_session.controller.recipe_manager

    try:
        recipe = recipe_manager.get_recipe(decoded_name)
        return jsonify({
            "success": True,
            "name": decoded_name,
            "device": recipe.get("device", ""),
            "inputs": recipe.get("inputs", {}),
            "outputs": recipe.get("outputs", {}),
        })
    except KeyError:
        return jsonify({"success": False, "error": f"配方 '{decoded_name}' 不存在"}), 404


def create_recipe_api():
    """
    创建新配方API
    
    Returns:
        JSON响应，包含创建结果
    """
    web_session = get_session()
    recipe_manager = web_session.controller.recipe_manager

    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "请求体不能为空"}), 400

    # 验证必填字段
    required_fields = ["name", "device", "inputs", "outputs"]
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return jsonify(
            {
                "success": False,
                "error": f"缺少必填字段: {', '.join(missing_fields)}",
            }
        ), 400

    recipe_name = data["name"]
    device_name = data["device"]
    inputs = data["inputs"]
    outputs = data["outputs"]

    # 验证配方名称安全性
    is_valid, error_msg = validate_recipe_name(recipe_name)
    if not is_valid:
        return jsonify({"success": False, "error": error_msg}), 400

    # 验证inputs和outputs格式
    if not isinstance(inputs, dict):
        return jsonify({"success": False, "error": "inputs必须是对象"}), 400
    if not isinstance(outputs, dict):
        return jsonify({"success": False, "error": "outputs必须是对象"}), 400

    # 验证每个物品的格式
    for item_type, items in [("inputs", inputs), ("outputs", outputs)]:
        for item_name, item_data in items.items():
            if not isinstance(item_data, dict):
                return jsonify(
                    {
                        "success": False,
                        "error": f"{item_type}中的'{item_name}'格式错误",
                    }
                ), 400
            if "amount" not in item_data:
                return jsonify(
                    {
                        "success": False,
                        "error": f"{item_type}中的'{item_name}'缺少amount字段",
                    }
                ), 400
            try:
                float(item_data["amount"])
            except (ValueError, TypeError):
                return jsonify(
                    {
                        "success": False,
                        "error": f"{item_type}中的'{item_name}'的amount必须是数字",
                    }
                ), 400
            # 如果没有expression，使用amount作为默认值
            if "expression" not in item_data:
                item_data["expression"] = str(item_data["amount"])

    # 检查配方是否已存在
    if recipe_name in recipe_manager.get_all_recipes():
        return jsonify({"success": False, "error": f"配方 '{recipe_name}' 已存在"}), 409

    # 添加配方
    try:
        recipe_manager.add_recipe(recipe_name, device_name, inputs, outputs)
        return jsonify(
            {
                "success": True,
                "message": f"配方 '{recipe_name}' 创建成功",
                "recipe": {
                    "name": recipe_name,
                    "device": device_name,
                    "inputs": inputs,
                    "outputs": outputs,
                },
            }
        ), 201
    except Exception as e:
        return jsonify({"success": False, "error": f"创建配方失败: {str(e)}"}), 500


def update_recipe_api(recipe_name: str):
    """
    更新现有配方API（支持部分更新）
    
    Args:
        recipe_name: 配方名称（URL编码）
    
    Returns:
        JSON响应，包含更新结果
    """
    # 解码URL编码的配方名称
    decoded_name = unquote(recipe_name)
    
    # 验证配方名称安全性
    is_valid, error_msg = validate_recipe_name(decoded_name)
    if not is_valid:
        return jsonify({"success": False, "error": error_msg}), 400

    web_session = get_session()
    recipe_manager = web_session.controller.recipe_manager

    # 检查配方是否存在
    if decoded_name not in recipe_manager.get_all_recipes():
        return jsonify({"success": False, "error": f"配方 '{decoded_name}' 不存在"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "请求体不能为空"}), 400

    # 获取现有配方数据
    existing_recipe = recipe_manager.get_recipe(decoded_name)

    # 准备更新后的数据
    device_name = data.get("device", existing_recipe.get("device", ""))
    inputs = data.get("inputs", existing_recipe.get("inputs", {}))
    outputs = data.get("outputs", existing_recipe.get("outputs", {}))

    # 验证inputs和outputs格式
    if "inputs" in data:
        if not isinstance(inputs, dict):
            return jsonify({"success": False, "error": "inputs必须是对象"}), 400
        # 验证每个物品的格式
        for item_name, item_data in inputs.items():
            if not isinstance(item_data, dict):
                return jsonify(
                    {"success": False, "error": f"inputs中的'{item_name}'格式错误"}
                ), 400
            if "amount" not in item_data:
                return jsonify(
                    {
                        "success": False,
                        "error": f"inputs中的'{item_name}'缺少amount字段",
                    }
                ), 400
            try:
                float(item_data["amount"])
            except (ValueError, TypeError):
                return jsonify(
                    {
                        "success": False,
                        "error": f"inputs中的'{item_name}'的amount必须是数字",
                    }
                ), 400
            if "expression" not in item_data:
                item_data["expression"] = str(item_data["amount"])

    if "outputs" in data:
        if not isinstance(outputs, dict):
            return jsonify({"success": False, "error": "outputs必须是对象"}), 400
        # 验证每个物品的格式
        for item_name, item_data in outputs.items():
            if not isinstance(item_data, dict):
                return jsonify(
                    {"success": False, "error": f"outputs中的'{item_name}'格式错误"}
                ), 400
            if "amount" not in item_data:
                return jsonify(
                    {
                        "success": False,
                        "error": f"outputs中的'{item_name}'缺少amount字段",
                    }
                ), 400
            try:
                float(item_data["amount"])
            except (ValueError, TypeError):
                return jsonify(
                    {
                        "success": False,
                        "error": f"outputs中的'{item_name}'的amount必须是数字",
                    }
                ), 400
            if "expression" not in item_data:
                item_data["expression"] = str(item_data["amount"])

    # 更新配方
    try:
        recipe_manager.update_recipe(
            decoded_name, device_name, inputs, outputs)
        return jsonify(
            {
                "success": True,
                "message": f"配方 '{decoded_name}' 更新成功",
                "recipe": {
                    "name": decoded_name,
                    "device": device_name,
                    "inputs": inputs,
                    "outputs": outputs,
                },
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": f"更新配方失败: {str(e)}"}), 500


def delete_recipe_api(recipe_name: str):
    """
    删除配方API
    
    Args:
        recipe_name: 配方名称（URL编码）
    
    Returns:
        JSON响应，包含删除结果
    """
    # 解码URL编码的配方名称
    decoded_name = unquote(recipe_name)
    
    # 验证配方名称安全性
    is_valid, error_msg = validate_recipe_name(decoded_name)
    if not is_valid:
        return jsonify({"success": False, "error": error_msg}), 400

    web_session = get_session()
    recipe_manager = web_session.controller.recipe_manager

    # 检查配方是否存在
    if decoded_name not in recipe_manager.get_all_recipes():
        return jsonify({"success": False, "error": f"配方 '{decoded_name}' 不存在"}), 404

    # 删除配方
    try:
        recipe_manager.delete_recipe(decoded_name)
        return jsonify({"success": True, "message": f"配方 '{decoded_name}' 删除成功"})
    except Exception as e:
        return jsonify({"success": False, "error": f"删除配方失败: {str(e)}"}), 500
