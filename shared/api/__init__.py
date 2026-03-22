"""
公共API模块
提供跨Web应用的共享会话管理、配方API、计算API等功能
"""

# 会话管理
from .session import (
    BaseWebSession,
    get_session,
    save_session,
    get_current_game,
)

# 配方API
from .recipe_api import (
    get_games_api,
    select_game_api,
    get_items_api,
    get_recipes_api,
    get_recipe_api,
    create_recipe_api,
    update_recipe_api,
    delete_recipe_api,
)

# 计算API
from .calculation_api import (
    calculate_api,
    get_alternatives_api,
    compare_paths_api,
    clear_api_cache,
    get_api_cache_stats,
)

__all__ = [
    # 会话管理
    "BaseWebSession",
    "get_session",
    "save_session",
    "get_current_game",
    
    # 配方API
    "get_games_api",
    "select_game_api",
    "get_items_api",
    "get_recipes_api",
    "get_recipe_api",
    "create_recipe_api",
    "update_recipe_api",
    "delete_recipe_api",
    
    # 计算API
    "calculate_api",
    "get_alternatives_api",
    "compare_paths_api",
    "clear_api_cache",
    "get_api_cache_stats",
]
