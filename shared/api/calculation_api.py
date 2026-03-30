"""
生产链计算公共API模块
提供跨应用的生产链计算、路径对比、替代路径查询等通用功能
"""
import json
import time
import hashlib
import threading
from typing import Dict, Any, List, Optional
from functools import wraps
from flask import request, jsonify
from urllib.parse import unquote
from .session import get_session
from expression_parser import parse_expression

# API层全局缓存
# 结构: {cache_key: {"data": response_data, "timestamp": created_time, "expire_seconds": expire_seconds}}
_api_cache: Dict[str, Dict[str, Any]] = {}
# 缓存操作线程锁，防止竞态条件
_cache_lock = threading.Lock()
# 缓存最大数量
_MAX_API_CACHE_SIZE = 256
# 默认缓存过期时间（秒）
_DEFAULT_CACHE_EXPIRE_SECONDS = 3600


def _get_cached(key: str, expire_seconds: int) -> Optional[Dict[str, Any]]:
    """
    获取缓存数据，检查是否过期

    Args:
        key: 缓存键
        expire_seconds: 过期时间（秒）

    Returns:
        缓存数据，如果不存在或已过期返回None
    """
    with _cache_lock:
        if key not in _api_cache:
            return None

        cached = _api_cache[key]
        # 检查是否过期
        if time.time() - cached["timestamp"] >= expire_seconds:
            # 过期则删除
            del _api_cache[key]
            return None

        return cached["data"]


def _set_cached(key: str, data: Dict[str, Any], expire_seconds: int) -> None:
    """
    设置缓存数据

    Args:
        key: 缓存键
        data: 缓存数据
        expire_seconds: 过期时间（秒）
    """
    with _cache_lock:
        if len(_api_cache) >= _MAX_API_CACHE_SIZE:
            # 清理过期缓存
            _cleanup_expired_cache_unlocked()
            # 如果仍然满了，清理最旧的缓存
            if len(_api_cache) >= _MAX_API_CACHE_SIZE:
                oldest_key = min(_api_cache.keys(), key=lambda k: _api_cache[k]["timestamp"])
                del _api_cache[oldest_key]

        _api_cache[key] = {
            "data": data,
            "timestamp": time.time(),
            "expire_seconds": expire_seconds
        }


def _cleanup_expired_cache() -> int:
    """
    清理过期的缓存

    Returns:
        清理的缓存数量
    """
    with _cache_lock:
        return _cleanup_expired_cache_unlocked()


def _cleanup_expired_cache_unlocked() -> int:
    """
    清理过期的缓存（内部方法，调用前需已持有锁）

    Returns:
        清理的缓存数量
    """
    current_time = time.time()
    expired_keys = [
        key for key, cached in _api_cache.items()
        if current_time - cached["timestamp"] >= cached["expire_seconds"]
    ]
    for key in expired_keys:
        del _api_cache[key]
    return len(expired_keys)

def cache_api_response(expire_seconds: int = 3600):
    """
    API响应缓存装饰器
    根据请求参数生成唯一缓存键，缓存JSON响应

    Args:
        expire_seconds: 缓存过期时间（秒），默认3600秒（1小时）
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 生成缓存键：请求路径 + 请求参数的哈希
            if request.method == 'POST':
                params = request.get_json(silent=True) or {}
            else:
                params = request.args.to_dict()
            
            # 生成唯一键
            key_data = {
                'path': request.path,
                'params': params,
                'method': request.method
            }
            cache_key = hashlib.md5(json.dumps(key_data, sort_keys=True).encode('utf-8')).hexdigest()
            
            # 检查缓存是否存在且未过期
            cached_data = _get_cached(cache_key, expire_seconds)
            if cached_data is not None:
                return jsonify(cached_data)
            
            # 执行原函数
            response = f(*args, **kwargs)
            
            # 缓存响应（仅缓存成功的响应）
            if response.status_code == 200:
                try:
                    # 尝试解析响应数据
                    response_data = response.get_json()
                    if response_data and response_data.get('success', False):
                        _set_cached(cache_key, response_data, expire_seconds)
                except Exception:
                    pass
            
            return response
        return decorated_function
    return decorator

def clear_api_cache() -> None:
    """清除所有API层缓存"""
    global _api_cache
    _api_cache.clear()


def get_api_cache_stats() -> Dict[str, Any]:
    """
    获取API缓存统计信息

    Returns:
        包含缓存大小、最大大小和过期缓存数量的字典
    """
    current_time = time.time()
    expired_count = sum(
        1 for cached in _api_cache.values()
        if current_time - cached["timestamp"] >= cached["expire_seconds"]
    )
    return {
        'cache_size': len(_api_cache),
        'max_cache_size': _MAX_API_CACHE_SIZE,
        'expired_count': expired_count,
        'default_expire_seconds': _DEFAULT_CACHE_EXPIRE_SECONDS
    }


@cache_api_response()
def calculate_api(include_alternatives: bool = True):
    """
    计算生产链API
    
    Args:
        include_alternatives: 是否包含替代路径信息
    
    Returns:
        JSON响应，包含计算结果
    """
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "请求体不能为空"}), 400

    # 获取参数
    target_item = data.get("target_item", "")
    target_rate = data.get("target_rate", 0)
    game_name = data.get("game_name", "")
    options = data.get("options", {})

    # 验证必填参数
    if not target_item:
        return jsonify({"success": False, "error": "target_item不能为空"}), 400
    if not target_rate:
        return jsonify({"success": False, "error": "target_rate不能为空"}), 400

    # 获取会话
    web_session = get_session()

    # 如果指定了game_name，先切换到该游戏
    if game_name:
        if not web_session.load_game(game_name):
            return jsonify({"success": False, "error": f"配方文件 '{game_name}' 不存在"}), 404

    # 检查计算器是否可用
    if not web_session.controller.calculator:
        return jsonify({"success": False, "error": "请先选择配方文件"}), 400

    # 解析目标生产速度
    try:
        target_rate_value = parse_expression(str(target_rate))
    except Exception as e:
        return jsonify({"success": False, "error": f"无法解析目标生产速度: {str(e)}"}), 400

    try:
        calculator = web_session.controller.calculator

        # 查找所有生产路径
        production_paths = calculator.find_production_paths(target_item)

        # 使用路径对比引擎选择主路径
        main_path_recipes = calculator.path_engine.find_main_path(
            production_paths)

        # 构建主路径合成树
        main_tree = calculator.build_crafting_tree(
            target_item, target_rate_value, main_path_recipes or []
        )

        if not main_tree:
            return jsonify({"success": False, "error": "无法构建合成树"}), 500

        # 查找所有完整路径的节点列表（用于替代路径识别）
        all_node_paths = []
        for path_recipes in production_paths:
            try:
                temp_tree = calculator.build_crafting_tree(
                    target_item, target_rate_value, path_recipes
                )
                if temp_tree:
                    node_path = calculator._flatten_tree_to_path(temp_tree)
                    all_node_paths.append(node_path)
            except Exception:
                continue

        # 在主路径上查找替代路径
        alternative_paths = []
        marked_nodes = []

        if include_alternatives and options.get("compare_paths", True):
            def find_alternatives(node):
                # 查找当前节点的替代路径
                alts = calculator.path_engine.find_alternative_paths_at_node(
                    node, all_node_paths, node.path_id
                )
                if alts:
                    node.alternative_paths = alts
                    marked_nodes.append({
                        "item_name": node.item_name,
                        "amount": node.amount,
                        "alternative_count": len(alts),
                    })

                # 递归处理子节点
                for child in node.children:
                    find_alternatives(child)

            find_alternatives(main_tree)

            # 收集替代路径（序列化）
            if not options.get("show_main_path_only", False):
                def collect_alternatives(node):
                    for alt_path in node.alternative_paths:
                        serialized = [
                            {
                                "item_name": n.item_name,
                                "amount": n.amount,
                                "device_count": n.device_count,
                                "recipe": n.recipe,
                            }
                            for n in alt_path
                        ]
                        if serialized not in alternative_paths:
                            alternative_paths.append(serialized)
                    for child in node.children:
                        collect_alternatives(child)

                collect_alternatives(main_tree)

        # 计算统计数据
        total_devices = calculator._count_total_devices(main_tree.to_dict())
        raw_materials = calculator.get_raw_materials(main_tree)
        device_stats = calculator.get_device_stats(main_tree)

        # 准备返回结果
        result = {
            "success": True,
            "main_path": main_tree.to_dict(),
            "marked_nodes": marked_nodes if options.get("mark_alternatives", True) else [],
            "total_devices": total_devices,
            "raw_materials": raw_materials,
            "device_stats": device_stats,
            "target_item": target_item,
            "target_rate": target_rate_value,
        }

        # 如果需要返回替代路径
        if alternative_paths:
            result["alternative_paths"] = alternative_paths

        return jsonify(result)

    except Exception as e:
        return jsonify({"success": False, "error": f"计算失败: {str(e)}"}), 500


@cache_api_response()
def get_alternatives_api():
    """
    获取节点的可选路径列表API
    
    Returns:
        JSON响应，包含替代路径列表
    """
    # 获取查询参数
    game_name = request.args.get("game_name", "")
    target_item = request.args.get("target_item", "")
    target_rate = request.args.get("target_rate", "")
    node_item = request.args.get("node_item", "")

    # 验证参数
    if not game_name:
        return jsonify({"success": False, "error": "game_name参数不能为空"}), 400
    if not target_item:
        return jsonify({"success": False, "error": "target_item参数不能为空"}), 400
    if not target_rate:
        return jsonify({"success": False, "error": "target_rate参数不能为空"}), 400
    if not node_item:
        return jsonify({"success": False, "error": "node_item参数不能为空"}), 400

    # 解析目标生产速度
    try:
        target_rate_value = parse_expression(str(target_rate))
    except Exception as e:
        return jsonify({"success": False, "error": f"无法解析target_rate: {str(e)}"}), 400

    # 获取会话
    web_session = get_session()

    # 切换到指定游戏
    if not web_session.load_game(game_name):
        return jsonify({"success": False, "error": f"配方文件 '{game_name}' 不存在"}), 404

    calculator = web_session.controller.calculator

    try:
        # 查找所有生产路径
        production_paths = calculator.find_production_paths(target_item)

        # 查找目标节点所在的替代路径
        alternatives = []
        path_id_counter = 1

        for path_recipes in production_paths:
            # 为每条路径构建临时树
            try:
                temp_tree = calculator.build_crafting_tree(
                    target_item, target_rate_value, path_recipes
                )
                if not temp_tree:
                    continue

                # 检查该路径是否包含目标节点
                def find_node(node):
                    if node.item_name == node_item:
                        return node
                    for child in node.children:
                        result = find_node(child)
                        if result:
                            return result
                    return None

                target_node = find_node(temp_tree)
                if not target_node:
                    continue

                # 计算该路径的设备数
                def count_devices(node):
                    total = node.device_count
                    for child in node.children:
                        total += count_devices(child)
                    return total

                device_count = count_devices(temp_tree)

                # 获取配方名称
                recipe_name = ""
                if target_node.recipe:
                    # 从配方管理器查找配方名称
                    recipes = calculator.recipe_manager.get_all_recipes()
                    for name, recipe in recipes.items():
                        if recipe == target_node.recipe:
                            recipe_name = name
                            break

                # 计算效率分数（基于设备数的倒数，归一化到0-1）
                efficiency_score = min(
                    1.0, max(0.0, 1.0 / (1.0 + device_count * 0.1)))

                # 构建节点链
                node_chain = []
                current = target_node
                while current:
                    node_chain.append({
                        "item_name": current.item_name,
                        "amount": current.amount,
                        "device_count": current.device_count,
                        "recipe_name": recipe_name if current == target_node else "",
                    })
                    if current.children:
                        current = current.children[0]
                    else:
                        break

                alternatives.append({
                    "path_id": path_id_counter,
                    "node_chain": node_chain,
                    "device_count": device_count,
                    "efficiency_score": efficiency_score,
                    "recipe_name": recipe_name,
                })

                path_id_counter += 1

            except Exception:
                # 跳过构建失败的路径
                continue

        # 按设备数排序
        alternatives.sort(key=lambda x: x["device_count"])

        # 重新分配path_id
        for i, alt in enumerate(alternatives):
            alt["path_id"] = i + 1

        return jsonify({
            "success": True,
            "node_item": node_item,
            "target_item": target_item,
            "target_rate": target_rate_value,
            "alternatives_count": len(alternatives),
            "alternatives": alternatives,
        })

    except Exception as e:
        return jsonify({"success": False, "error": f"获取替代路径失败: {str(e)}"}), 500


@cache_api_response()
def compare_paths_api():
    """
    对比多条路径API
    
    Returns:
        JSON响应，包含路径对比结果
    """
    # 获取查询参数
    game_name = request.args.get("game_name", "")
    target_item = request.args.get("target_item", "")
    target_rate = request.args.get("target_rate", "")
    path_indices_str = request.args.get("path_indices", "")

    # 验证参数
    if not game_name:
        return jsonify({"success": False, "error": "game_name参数不能为空"}), 400
    if not target_item:
        return jsonify({"success": False, "error": "target_item参数不能为空"}), 400
    if not target_rate:
        return jsonify({"success": False, "error": "target_rate参数不能为空"}), 400

    # 解析path_indices
    try:
        path_indices = [
            int(x.strip()) for x in path_indices_str.split(",") if x.strip()
        ]
        if not path_indices:
            path_indices = [0, 1, 2]  # 默认对比前3条路径
    except ValueError:
        path_indices = [0, 1, 2]

    # 解析目标生产速度
    try:
        target_rate_value = parse_expression(str(target_rate))
    except Exception as e:
        return jsonify({"success": False, "error": f"无法解析target_rate: {str(e)}"}), 400

    # 获取会话
    web_session = get_session()

    # 切换到指定游戏
    if not web_session.load_game(game_name):
        return jsonify({"success": False, "error": f"配方文件 '{game_name}' 不存在"}), 404

    calculator = web_session.controller.calculator

    try:
        # 查找所有生产路径
        production_paths = calculator.find_production_paths(target_item)

        if not production_paths:
            return jsonify({"success": False, "error": "未找到生产路径"}), 404

        # 过滤有效的path_indices
        valid_indices = [i for i in path_indices if 0 <= i < len(production_paths)]
        if not valid_indices:
            valid_indices = [0]

        # 对比每条路径
        comparisons = []

        for idx in valid_indices:
            path_recipes = production_paths[idx]

            # 构建合成树
            tree = calculator.build_crafting_tree(
                target_item, target_rate_value, path_recipes
            )
            if not tree:
                continue

            tree_dict = tree.to_dict()

            # 计算统计信息
            total_devices = calculator._count_total_devices(tree_dict)
            raw_materials = calculator.get_raw_materials(tree)
            device_stats = calculator.get_device_stats(tree)

            # 计算效率分数（基于设备数的倒数）
            efficiency_score = min(
                1.0, max(0.0, 1.0 / (1.0 + total_devices * 0.1)))

            # 分析优缺点
            strengths = []
            weaknesses = []

            # 设备数量评价
            if total_devices < 5:
                strengths.append("设备数量很少")
            elif total_devices < 10:
                strengths.append("设备数量较少")
            elif total_devices > 30:
                weaknesses.append("设备数量较多")

            # 基础原料评价
            if len(raw_materials) <= 2:
                strengths.append("原料种类简单")
            elif len(raw_materials) >= 5:
                weaknesses.append("原料种类复杂")

            # 设备种类评价
            if len(device_stats) <= 2:
                strengths.append("设备种类简单")
            elif len(device_stats) >= 4:
                weaknesses.append("设备种类较多")

            comparisons.append({
                "path_index": idx,
                "total_devices": total_devices,
                "total_inputs": len(raw_materials),
                "device_type_count": len(device_stats),
                "efficiency_score": efficiency_score,
                "raw_materials": raw_materials,
                "device_stats": device_stats,
                "strengths": strengths,
                "weaknesses": weaknesses,
            })

        # 按效率分数排序
        comparisons.sort(key=lambda x: x["efficiency_score"], reverse=True)

        return jsonify({
            "success": True,
            "target_item": target_item,
            "target_rate": target_rate_value,
            "comparisons_count": len(comparisons),
            "comparisons": comparisons,
        })

    except Exception as e:
        return jsonify({"success": False, "error": f"路径对比失败: {str(e)}"}), 500
