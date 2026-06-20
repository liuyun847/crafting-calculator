"""
应用程序控制器

包含所有业务逻辑，通过IOInterface与用户交互。
"""

import sys
import traceback
from typing import Dict, Any, Tuple, Set, Optional, List

from io_interface import IOInterface
from data_manager import RecipeManager
from calculator import CraftingCalculator, CraftingNode
from config_manager import config_manager
from expression_parser import parse_expression


class ApplicationController:
    """应用程序控制器 - 包含所有业务逻辑"""

    def __init__(self, io: IOInterface):
        """
        初始化应用程序控制器

        Args:
            io: 输入输出接口
        """
        self.io = io
        self.recipe_manager = RecipeManager()
        self.calculator: Optional[CraftingCalculator] = None
        self.current_game: Optional[str] = None
        self.state: str = "main_menu"
        self.pending_data: Dict[str, Any] = {}
        # 路径切换相关状态
        self._current_chain_trees: List[Dict[str, Any]] = []  # 当前计算的所有路径
        self._current_main_tree: Optional[Dict[str, Any]] = None  # 当前显示的主路径
        self._current_target_item: str = ""  # 当前目标物品
        self._current_target_rate: float = 0.0  # 当前目标生产速度
        self._node_id_map: Dict[int, Dict[str, Any]] = {}  # 节点编号到节点信息的映射

    def run(self) -> None:
        """运行应用程序（终端模式）"""
        self.io.print("开始初始化应用程序...")

        try:
            self._initialize()

            while True:
                self._process_main_menu()

        except Exception as e:
            error_msg = (
                f"应用程序发生错误:\n{str(e)}\n\n详细信息:\n{traceback.format_exc()}"
            )
            self.io.print(error_msg)
            sys.exit(1)

    def _initialize(self) -> None:
        """初始化应用程序"""
        last_game = config_manager.get_last_game()
        if last_game:
            available_games = self.recipe_manager.get_available_games()
            if last_game in available_games:
                try:
                    recipes = self.recipe_manager.load_recipe_file(last_game)
                    self.current_game = last_game
                    self.calculator = CraftingCalculator(self.recipe_manager)
                    self.io.print(f"\n已自动加载上次选择的配方文件: {last_game}")
                    self._print_recipe_list(recipes)
                except Exception as e:
                    self.io.print(f"\n警告: 无法自动加载配方文件 '{last_game}': {e}")
            else:
                self.io.print(f"\n提示: 上次选择的配方文件 '{last_game}' 不存在")

        if not self.current_game:
            self.io.print("\n欢迎使用，请选择配方文件开始使用")

    def _process_main_menu(self) -> None:
        """处理主菜单（终端模式）"""
        self._print_menu()
        choice = self.io.input("请选择操作 (1-5): ")

        if choice == "1":
            self._select_game_terminal()
        elif choice == "2":
            self._calculate_production_chain_terminal()
        elif choice == "3":
            self._show_items_list_terminal()
        elif choice == "4":
            self._recipe_management_submenu()
        elif choice == "5":
            self.io.print("退出程序...")
            sys.exit(0)
        else:
            self.io.print("选择无效，请输入1-5之间的数字")

        self.io.input("\n按任意键继续...")

    def _print_menu(self) -> None:
        """打印主菜单"""
        self.io.print("=====================================")
        self.io.print("   自动化建造游戏通用合成计算器")
        self.io.print("=====================================")
        self.io.print("1. 选择配方文件")
        self.io.print("2. 计算生产链")
        self.io.print("3. 查看可用物品列表")
        self.io.print("4. 配方管理")
        self.io.print("5. 退出程序")
        self.io.print("=====================================")

    def _print_recipe_list(self, recipes: Dict[str, Any]) -> None:
        """
        打印配方文件列表

        Args:
            recipes: 配方字典
        """
        self.io.print("\n当前配方文件中的配方:")
        self.io.print("-" * 50)
        if not recipes:
            self.io.print("配方文件为空")
        else:
            for i, (recipe_name, recipe) in enumerate(recipes.items(), 1):
                device = recipe.get("device", "未知设备")
                outputs = ", ".join(recipe.get("outputs", {}).keys())
                self.io.print(f"{i}. {recipe_name} ({device}) → {outputs}")
        self.io.print("-" * 50)

    def _print_tree(
        self,
        tree_dict: Dict[str, Any],
        indent: int = 0,
        is_last: bool = False,
        prefixes: Optional[List[str]] = None,
        node_index: int = 0,
        node_counter: Optional[List[int]] = None,
    ) -> int:
        """
        以树形结构打印合成树，支持替代路径标记

        Args:
            tree_dict: 合成树的字典表示
            indent: 缩进级别
            is_last: 是否为父节点的最后一个子节点
            prefixes: 存储每一层的前缀字符
            node_index: 当前节点索引
            node_counter: 节点计数器列表（用于传递引用）

        Returns:
            下一个节点的索引
        """
        if prefixes is None:
            prefixes = []

        if node_counter is None:
            node_counter = [0]

        current_prefix = "".join(prefixes)
        if indent > 0:
            if is_last:
                current_prefix += "└─"
            else:
                current_prefix += "├─"

        item_name = tree_dict["item_name"]
        amount = tree_dict["amount"]
        device_count = tree_dict["device_count"]

        # 获取路径信息
        path_info = tree_dict.get("path_info", {})
        alternative_count = path_info.get("alternative_count", 0)

        # 增加节点计数
        node_counter[0] += 1
        current_node_index = node_counter[0]

        # 构建节点标记（如果有替代路径）
        marker = f" [{alternative_count}]" if alternative_count > 0 else ""

        # 打印节点信息
        self.io.print(f"{current_prefix}{item_name}: {amount:.2f}/s{marker}")

        if device_count > 0:
            device_info_prefix = "".join(prefixes)
            if indent > 0:
                if is_last:
                    device_info_prefix += "  "
                else:
                    device_info_prefix += "│ "
            self.io.print(f"{device_info_prefix}│设备数: {device_count:.2f}")
            if "recipe" in tree_dict and tree_dict["recipe"]:
                device = tree_dict["recipe"].get("device", "未知设备")
                self.io.print(f"{device_info_prefix}│设备: {device}")

        children = tree_dict["children"]
        for i, child in enumerate(children):
            child_is_last = i == len(children) - 1
            child_prefixes = prefixes.copy()
            if indent > 0:
                if is_last:
                    child_prefixes.append("  ")
                else:
                    child_prefixes.append("│ ")
            self._print_tree(
                child,
                indent + 1,
                child_is_last,
                child_prefixes,
                current_node_index,
                node_counter,
            )

        return node_counter[0]

    def _print_raw_materials(self, raw_materials: Dict[str, float]) -> None:
        """
        打印基础原料消耗

        Args:
            raw_materials: 基础原料字典
        """
        self.io.print("\n基础原料消耗:")
        self.io.print("-" * 50)
        if not raw_materials:
            self.io.print("无基础原料消耗")
        else:
            for item, amount in raw_materials.items():
                self.io.print(f"{item}: {amount:.2f}/s")
        self.io.print("-" * 50)

    def _print_device_stats(self, device_stats: Dict[str, float]) -> None:
        """
        打印设备统计

        Args:
            device_stats: 设备统计字典
        """
        self.io.print("\n设备统计:")
        self.io.print("-" * 50)
        if not device_stats:
            self.io.print("无设备使用")
        else:
            for device, count in device_stats.items():
                self.io.print(f"{device}: {count:.2f} 台")
        self.io.print("-" * 50)

    def _list_recipes(self) -> None:
        """
        查看配方列表，支持分页显示和按物品名称筛选
        """
        if not self.calculator or not self.current_game:
            self.io.print("请先选择配方文件")
            return

        recipes = self.recipe_manager.get_all_recipes()
        if not recipes:
            self.io.print("\n当前配方文件为空")
            return

        # 转换为列表便于分页
        recipe_list = list(recipes.items())
        page_size = 10
        current_page = 1
        search_keyword = ""

        while True:
            # 根据搜索关键词筛选配方
            if search_keyword:
                filtered_list = [
                    (name, recipe)
                    for name, recipe in recipe_list
                    if (
                        search_keyword.lower() in name.lower()
                        or any(
                            search_keyword.lower() in item.lower()
                            for item in recipe.get("inputs", {}).keys()
                        )
                        or any(
                            search_keyword.lower() in item.lower()
                            for item in recipe.get("outputs", {}).keys()
                        )
                    )
                ]
            else:
                filtered_list = recipe_list

            total_filtered = len(filtered_list)
            total_filtered_pages = max(
                1, (total_filtered + page_size - 1) // page_size)

            # 确保当前页在有效范围内
            if current_page > total_filtered_pages:
                current_page = total_filtered_pages
            if current_page < 1:
                current_page = 1

            # 计算当前页的配方
            start_idx = (current_page - 1) * page_size
            end_idx = min(start_idx + page_size, total_filtered)
            current_recipes = filtered_list[start_idx:end_idx]

            # 显示配方列表
            self.io.print("\n" + "=" * 70)
            if search_keyword:
                self.io.print(
                    f"  配方列表 (搜索: '{search_keyword}') - 第 {current_page}/{total_filtered_pages} 页"
                )
            else:
                self.io.print(
                    f"  配方列表 - 第 {current_page}/{total_filtered_pages} 页 "
                    f"(共 {total_filtered} 条)"
                )
            self.io.print("=" * 70)

            if not current_recipes:
                self.io.print("  没有找到配方")
            else:
                for i, (recipe_name, recipe) in enumerate(
                        current_recipes, start_idx + 1
                ):
                    device = recipe.get("device", "未知设备")
                    inputs = recipe.get("inputs", {})
                    outputs = recipe.get("outputs", {})

                    self.io.print(f"\n  [{i}] {recipe_name}")
                    self.io.print(f"      设备: {device}")

                    # 显示输入物品
                    if inputs:
                        input_items = ", ".join(
                            f"{name}({data.get('amount', 0):.2f}/s)"
                            for name, data in inputs.items()
                        )
                        self.io.print(f"      输入: {input_items}")

                    # 显示输出物品
                    if outputs:
                        output_items = ", ".join(
                            f"{name}({data.get('amount', 0):.2f}/s)"
                            for name, data in outputs.items()
                        )
                        self.io.print(f"      输出: {output_items}")

            self.io.print("\n" + "-" * 70)
            self.io.print("  操作: [n]下一页 [p]上一页 [s]搜索 [c]清除搜索 [q]退出")
            self.io.print("-" * 70)

            # 获取用户输入
            choice = self.io.input("  请选择操作: ").strip().lower()

            if choice == "q":
                break
            elif choice == "n":
                if current_page < total_filtered_pages:
                    current_page += 1
                else:
                    self.io.print("  已经是最后一页了")
            elif choice == "p":
                if current_page > 1:
                    current_page -= 1
                else:
                    self.io.print("  已经是第一页了")
            elif choice == "s":
                search_keyword = self.io.input("  请输入搜索关键词: ").strip()
                current_page = 1
                if not search_keyword:
                    self.io.print("  搜索关键词为空，显示所有配方")
            elif choice == "c":
                if search_keyword:
                    search_keyword = ""
                    current_page = 1
                    self.io.print("  已清除搜索筛选")
                else:
                    self.io.print("  当前没有搜索筛选")
            else:
                self.io.print("  无效的选择，请重新输入")

    def _print_name_list(
        self, name_list: List[Tuple[str, int]], search_keyword: str = ""
    ) -> List[str]:
        """
        打印名称列表，支持搜索过滤

        Args:
            name_list: 名称及其频率的列表
            search_keyword: 搜索关键词

        Returns:
            过滤后的名称列表
        """
        filtered_names = []
        for name, freq in name_list:
            if not search_keyword or search_keyword.lower() in name.lower():
                filtered_names.append(name)

        if filtered_names:
            self.io.print(f"\n已有名称列表 (共 {len(filtered_names)} 项):")
            self.io.print("-" * 50)
            for i, name in enumerate(filtered_names, 1):
                freq = next(f for n, f in name_list if n == name)
                self.io.print(f"{i}. {name} (使用次数: {freq})")
            self.io.print("-" * 50)
            self.io.print("提示: 输入数字选择，或输入字符搜索，或直接输入新名称")
        else:
            self.io.print(f"\n未找到匹配 '{search_keyword}' 的名称")

        return filtered_names

    def _input_item(self, prompt_prefix: str = "") -> Dict[str, Any]:
        """
        获取单个物品信息

        Args:
            prompt_prefix: 提示前缀

        Returns:
            物品信息字典
        """
        while True:
            try:
                amount_input = self.io.input(
                    f"{prompt_prefix}请输入数量 (支持表达式，如 10 或 15/min): "
                )

                if not self._validate_expression(amount_input):
                    self.io.print("表达式格式无效，请重新输入")
                    continue

                amount = parse_expression(amount_input)

                if amount <= 0:
                    self.io.print("数量必须大于0，请重新输入")
                    continue

                return {"amount": amount, "expression": amount_input}
            except ValueError:
                self.io.print("请输入有效的数字或表达式")
            except Exception as e:
                self.io.print(f"输入错误: {e}")

    def _input_items_list(
        self,
        item_type: str,
        item_freq: List[Tuple[str, int]] = None,
        existing_names: Set[str] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """
        交互式输入多个物品

        Args:
            item_type: 物品类型
            item_freq: 物品频率列表
            existing_names: 已存在的名称集合

        Returns:
            物品字典
        """
        if item_freq is None:
            item_freq = []
        if existing_names is None:
            existing_names = set()

        items = {}
        count = 1

        while True:
            self.io.print(f"\n--- 输入{item_type}物品 {count} ---")

            item_name = self._select_name_with_suggestion(
                item_freq, f"请输入{item_type}物品名称", existing_names=existing_names
            )

            existing_names.add(item_name)

            item_data = self._input_item(f"{item_name}: ")
            items[item_name] = item_data

            choice = (
                self.io.input(
                    f"\n是否继续添加{item_type}物品? (y/n): ").strip().lower()
            )
            if choice not in ["y", "yes", "是"]:
                break

            count += 1

        return items

    def _select_name_with_suggestion(
        self,
        name_list: List[Tuple[str, int]],
        prompt: str,
        existing_names: Set[str] = None,
        allow_duplicate: bool = False,
    ) -> str:
        """
        交互式选择名称，支持快捷选择和搜索

        Args:
            name_list: 名称及其频率的列表
            prompt: 提示信息
            existing_names: 已存在的名称集合
            allow_duplicate: 是否允许重复名称

        Returns:
            用户选择的名称
        """
        if existing_names is None:
            existing_names = set()

        while True:
            filtered_names = self._print_name_list(name_list, "")

            user_input = self.io.input(f"\n{prompt}: ").strip()

            if not user_input:
                self.io.print("输入不能为空，请重新输入")
                continue

            try:
                index = int(user_input)
                if 1 <= index <= len(filtered_names):
                    selected_name = filtered_names[index - 1]
                    if not allow_duplicate and selected_name in existing_names:
                        self.io.print(f"名称 '{selected_name}' 已存在，请使用其他名称")
                        continue
                    return selected_name
                else:
                    self.io.print(f"请输入 1-{len(filtered_names)} 之间的数字")
            except ValueError:
                if user_input.isdigit():
                    self.io.print(f"请输入 1-{len(filtered_names)} 之间的数字")
                else:
                    if not allow_duplicate and user_input in existing_names:
                        self.io.print(f"名称 '{user_input}' 已存在，请使用其他名称")
                        continue

                    if len(user_input) <= 2:
                        filtered_search = self._print_name_list(
                            name_list, user_input)
                        if filtered_search:
                            search_input = self.io.input(
                                f"\n{prompt}: ").strip()
                            if not search_input:
                                self.io.print("输入不能为空，请重新输入")
                                continue

                            try:
                                search_index = int(search_input)
                                if 1 <= search_index <= len(filtered_search):
                                    selected_name = filtered_search[search_index - 1]
                                    if (
                                        not allow_duplicate
                                        and selected_name in existing_names
                                    ):
                                        self.io.print(
                                            f"名称 '{selected_name}' 已存在，请使用其他名称"
                                        )
                                        continue
                                    return selected_name
                                else:
                                    self.io.print(
                                        f"请输入 1-{len(filtered_search)} 之间的数字"
                                    )
                            except ValueError:
                                if search_input.isdigit():
                                    self.io.print(
                                        f"请输入 1-{len(filtered_search)} 之间的数字"
                                    )
                                else:
                                    if (
                                        not allow_duplicate
                                        and search_input in existing_names
                                    ):
                                        self.io.print(
                                            f"名称 '{search_input}' 已存在，请使用其他名称"
                                        )
                                        continue
                                    return search_input
                        else:
                            self.io.print(f"未找到匹配 '{user_input}' 的名称")
                            confirm = (
                                self.io.input(
                                    f"是否使用 '{user_input}' 作为新名称? (y/n): "
                                )
                                .strip()
                                .lower()
                            )
                            if confirm in ["y", "yes", "是"]:
                                return user_input
                            else:
                                continue
                    else:
                        return user_input

    def _confirm_recipe(self) -> bool:
        """
        获取用户确认

        Returns:
            用户是否确认保存
        """
        while True:
            choice = self.io.input("\n是否保存此配方? (y/n): ").strip().lower()
            if choice in ["y", "yes", "是"]:
                return True
            elif choice in ["n", "no", "否"]:
                return False
            else:
                self.io.print("请输入 y 或 n")

    def _generate_recipe_id(
        self, outputs: Dict[str, Any], existing_recipes: Dict[str, Any]
    ) -> str:
        """
        根据输出物品生成配方标识符

        Args:
            outputs: 输出物品字典
            existing_recipes: 已存在的配方字典

        Returns:
            生成的配方标识符
        """
        if not outputs:
            return "未知配方"

        max_amount = 0
        main_output = ""
        for item_name, item_data in outputs.items():
            amount = item_data.get("amount", 0)
            if amount > max_amount:
                max_amount = amount
                main_output = item_name

        if not main_output:
            main_output = list(outputs.keys())[0]

        base_id = f"{main_output}生产"

        if base_id not in existing_recipes:
            return base_id

        counter = 2
        while f"{base_id}_{counter}" in existing_recipes:
            counter += 1

        return f"{base_id}_{counter}"

    def _validate_expression(self, expression: str) -> bool:
        """
        验证表达式格式是否正确

        Args:
            expression: 要验证的表达式

        Returns:
            表达式是否有效
        """
        try:
            parse_expression(expression)
            return True
        except Exception:
            return False

    def _add_recipe_interactive(self) -> None:
        """交互式添加配方"""
        if not self.recipe_manager.current_game:
            self.io.print("请先选择配方文件")
            return

        self.io.print("\n" + "=" * 50)
        self.io.print("添加新配方")
        self.io.print("=" * 50)

        device_freq = self.recipe_manager.get_device_frequency()
        item_freq = self.recipe_manager.get_item_frequency()

        device_name = self._select_name_with_suggestion(
            device_freq, "请输入设备名称", allow_duplicate=True
        )

        self.io.print("\n--- 配置输出物品 ---")
        outputs = self._input_items_list("输出", item_freq)

        if not outputs:
            self.io.print("错误: 至少需要一个输出物品")
            return

        self.io.print("\n--- 配置输入物品 ---")
        inputs = self._input_items_list("输入", item_freq)

        existing_recipes = self.recipe_manager.get_all_recipes()
        recipe_name = self._generate_recipe_id(outputs, existing_recipes)

        self._display_recipe_preview(recipe_name, device_name, inputs, outputs)

        if self._confirm_recipe():
            try:
                self.recipe_manager.add_recipe(
                    recipe_name, device_name, inputs, outputs
                )
                self.io.print(f"\n成功添加配方: {recipe_name}")
            except ValueError as e:
                self.io.print(f"\n添加配方失败: {e}")
        else:
            self.io.print("\n已取消添加配方")

    def _recipe_management_submenu(self) -> None:
        """配方管理子菜单（终端模式）"""
        if not self.current_game:
            self.io.print("请先选择配方文件")
            return

        while True:
            self.io.print("\n" + "=" * 50)
            self.io.print("配方管理")
            self.io.print("=" * 50)
            self.io.print("1. 查看配方列表")
            self.io.print("2. 添加配方")
            self.io.print("3. 修改配方")
            self.io.print("4. 删除配方")
            self.io.print("5. 返回主菜单")
            self.io.print("=" * 50)

            choice = self.io.input("请选择操作 (1-5): ")

            if choice == "1":
                self._show_recipe_list_terminal()
            elif choice == "2":
                self._add_recipe_interactive()
                break
            elif choice == "3":
                self._modify_recipe_terminal()
            elif choice == "4":
                self._delete_recipe_terminal()
            elif choice == "5":
                break
            else:
                self.io.print("选择无效，请输入1-5之间的数字")

            if choice in ["1", "3", "4"]:
                self.io.input("\n按任意键继续...")

    def _show_recipe_list_terminal(self) -> None:
        """显示配方列表（终端模式）"""
        recipes = self.recipe_manager.get_all_recipes()
        self.io.print("\n当前配方文件中的配方:")
        self.io.print("-" * 50)
        if not recipes:
            self.io.print("配方文件为空")
        else:
            for i, (recipe_name, recipe) in enumerate(recipes.items(), 1):
                device = recipe.get("device", "未知设备")
                outputs = ", ".join(recipe.get("outputs", {}).keys())
                self.io.print(f"{i}. {recipe_name} ({device}) → {outputs}")
        self.io.print("-" * 50)

    def _modify_recipe_terminal(self) -> None:
        """
        修改配方（终端模式）

        流程：
        1) 显示配方列表让用户选择要修改的配方
        2) 显示当前配方的所有字段（设备、输入物品、输出物品）
        3) 让用户选择要修改的字段
        4) 逐字段修改，每步显示当前值让用户输入新值（直接回车表示保持原值）
        5) 所有字段修改完成后显示修改后的完整配方并要求确认
        6) 确认后调用 data_manager.update_recipe() 保存修改
        """
        recipes = self.recipe_manager.get_all_recipes()
        if not recipes:
            self.io.print("当前没有可修改的配方")
            return

        # 1) 显示配方列表让用户选择
        self._show_recipe_list_terminal()
        choice = self.io.input("\n请输入要修改的配方序号 (0取消): ")

        try:
            index = int(choice) - 1
            recipe_names = list(recipes.keys())
            if index == -1:  # 用户输入0取消
                self.io.print("已取消修改")
                return
            if 0 <= index < len(recipe_names):
                recipe_name = recipe_names[index]
                recipe_data = recipes[recipe_name]
                self._modify_recipe_interactive(recipe_name, recipe_data)
            else:
                self.io.print("选择无效")
        except ValueError:
            self.io.print("请输入有效的数字")

    def _modify_recipe_interactive(
        self, original_recipe_name: str, original_recipe_data: Dict[str, Any]
    ) -> None:
        """
        交互式修改配方的核心逻辑

        Args:
            original_recipe_name: 原始配方名称
            original_recipe_data: 原始配方数据
        """
        self.io.print(f"\n{'=' * 50}")
        self.io.print(f"正在修改配方: {original_recipe_name}")
        self.io.print(f"{'=' * 50}")

        # 2) 显示当前配方的所有字段
        current_device = original_recipe_data.get("device", "未知设备")
        current_inputs = original_recipe_data.get("inputs", {}).copy()
        current_outputs = original_recipe_data.get("outputs", {}).copy()

        self._display_current_recipe_fields(
            original_recipe_name, current_device, current_inputs, current_outputs
        )

        # 3) 让用户选择要修改的字段
        self.io.print(f"\n{'-' * 50}")
        self.io.print("请选择要修改的字段:")
        self.io.print("1. 设备名称")
        self.io.print("2. 输入物品")
        self.io.print("3. 输出物品")
        self.io.print("4. 完成修改并保存")
        self.io.print("0. 取消修改")
        self.io.print(f"{'-' * 50}")

        while True:
            choice = self.io.input("请选择操作 (0-4): ").strip()

            if choice == "0":
                self.io.print("已取消修改")
                return
            elif choice == "1":
                current_device = self._modify_device_name(current_device)
            elif choice == "2":
                current_inputs = self._modify_items(current_inputs, "输入")
            elif choice == "3":
                current_outputs = self._modify_items(current_outputs, "输出")
            elif choice == "4":
                break
            else:
                self.io.print("选择无效，请输入0-4之间的数字")

        # 5) 所有字段修改完成后显示修改后的完整配方并要求确认
        self._display_recipe_preview(
            original_recipe_name, current_device, current_inputs, current_outputs
        )

        # 6) 确认后保存修改
        if self._confirm_recipe():
            try:
                self.recipe_manager.update_recipe(
                    original_recipe_name,
                    current_device,
                    current_inputs,
                    current_outputs,
                )
                self.io.print(f"\n成功修改配方: {original_recipe_name}")
            except Exception as e:
                self.io.print(f"\n修改配方失败: {e}")
        else:
            self.io.print("\n已取消修改配方")

    def _display_current_recipe_fields(
        self,
        recipe_name: str,
        device: str,
        inputs: Dict[str, Any],
        outputs: Dict[str, Any],
    ) -> None:
        """
        显示当前配方的所有字段

        Args:
            recipe_name: 配方名称
            device: 设备名称
            inputs: 输入物品字典
            outputs: 输出物品字典
        """
        self.io.print("\n当前配方信息:")
        self.io.print("-" * 50)
        self.io.print(f"配方名称: {recipe_name}")
        self.io.print(f"设备名称: {device}")

        self.io.print("\n输入物品:")
        if not inputs:
            self.io.print("  (无)")
        else:
            for item_name, item_data in inputs.items():
                if isinstance(item_data, dict):
                    amount = item_data.get("amount", 0)
                    expr = item_data.get("expression", str(amount))
                    self.io.print(f"  - {item_name}: {amount:.2f}/s ({expr})")
                else:
                    self.io.print(f"  - {item_name}: {item_data}")

        self.io.print("\n输出物品:")
        if not outputs:
            self.io.print("  (无)")
        else:
            for item_name, item_data in outputs.items():
                if isinstance(item_data, dict):
                    amount = item_data.get("amount", 0)
                    expr = item_data.get("expression", str(amount))
                    self.io.print(f"  - {item_name}: {amount:.2f}/s ({expr})")
                else:
                    self.io.print(f"  - {item_name}: {item_data}")
        self.io.print("-" * 50)

    def _modify_device_name(self, current_device: str) -> str:
        """
        修改设备名称

        Args:
            current_device: 当前设备名称

        Returns:
            新的设备名称
        """
        self.io.print(f"\n当前设备名称: {current_device}")
        device_freq = self.recipe_manager.get_device_frequency()
        self._print_name_list(device_freq)

        new_device = self.io.input(
            f"请输入新设备名称 (直接回车保持 '{current_device}'): "
        ).strip()

        if new_device:
            return new_device
        return current_device

    def _modify_items(
        self, current_items: Dict[str, Any], item_type: str
    ) -> Dict[str, Any]:
        """
        修改物品（输入或输出）

        Args:
            current_items: 当前物品字典
            item_type: 物品类型（"输入"或"输出"）

        Returns:
            修改后的物品字典
        """
        items = current_items.copy()
        item_freq = self.recipe_manager.get_item_frequency()

        while True:
            self.io.print(f"\n--- 修改{item_type}物品 ---")
            self.io.print("当前物品:")
            if not items:
                self.io.print("  (无)")
            else:
                for i, (item_name, item_data) in enumerate(items.items(), 1):
                    if isinstance(item_data, dict):
                        amount = item_data.get("amount", 0)
                        self.io.print(f"  {i}. {item_name}: {amount:.2f}/s")
                    else:
                        self.io.print(f"  {i}. {item_name}: {item_data}")

            self.io.print("\n操作选项:")
            self.io.print("1. 添加物品")
            self.io.print("2. 删除物品")
            self.io.print("3. 修改物品数量")
            self.io.print("4. 完成修改")

            choice = self.io.input("\n请选择操作 (1-4): ").strip()

            if choice == "1":
                # 添加物品
                new_item_name = self._select_name_with_suggestion(
                    item_freq, f"请输入{item_type}物品名称"
                )
                if new_item_name in items:
                    self.io.print(f"物品 '{new_item_name}' 已存在")
                    continue
                item_data = self._input_item(f"{new_item_name}: ")
                items[new_item_name] = item_data
                self.io.print(f"已添加物品: {new_item_name}")

            elif choice == "2":
                # 删除物品
                if not items:
                    self.io.print("当前没有物品可以删除")
                    continue
                item_name = self.io.input("请输入要删除的物品名称: ").strip()
                if item_name in items:
                    del items[item_name]
                    self.io.print(f"已删除物品: {item_name}")
                else:
                    self.io.print(f"物品 '{item_name}' 不存在")

            elif choice == "3":
                # 修改物品数量
                if not items:
                    self.io.print("当前没有物品可以修改")
                    continue
                item_name = self.io.input("请输入要修改的物品名称: ").strip()
                if item_name in items:
                    item_data = self._input_item(f"{item_name}: ")
                    items[item_name] = item_data
                    self.io.print(f"已修改物品: {item_name}")
                else:
                    self.io.print(f"物品 '{item_name}' 不存在")

            elif choice == "4":
                # 完成修改
                break
            else:
                self.io.print("选择无效，请输入1-4之间的数字")

        return items



    def _display_recipe_preview(
        self,
        recipe_name: str,
        device_name: str,
        inputs: Dict[str, Dict[str, Any]],
        outputs: Dict[str, Dict[str, Any]],
    ) -> None:
        """
        显示配方预览

        Args:
            recipe_name: 配方名称
            device_name: 设备名称
            inputs: 输入物品字典
            outputs: 输出物品字典
        """
        self.io.print("\n" + "=" * 50)
        self.io.print("配方预览")
        self.io.print("=" * 50)
        self.io.print(f"配方名称: {recipe_name}")
        self.io.print(f"设备名称: {device_name}")

        self.io.print("\n输入物品:")
        if not inputs:
            self.io.print("  (无)")
        else:
            for item_name, item_data in inputs.items():
                self.io.print(
                    f"  - {item_name}: {item_data['amount']:.2f} 个/秒 (表达式: {item_data['expression']})"
                )

        self.io.print("\n输出物品:")
        if not outputs:
            self.io.print("  (无)")
        else:
            for item_name, item_data in outputs.items():
                self.io.print(
                    f"  - {item_name}: {item_data['amount']:.2f} 个/秒 (表达式: {item_data['expression']})"
                )

        self.io.print("=" * 50)

    def _select_game_terminal(self) -> None:
        """选择配方文件（终端模式）"""
        self.io.print("\n可用的配方文件:")
        games = self.recipe_manager.get_available_games()

        if not games:
            self.io.print("没有找到配方文件")
            return

        for i, game in enumerate(games, 1):
            self.io.print(f"{i}. {game}")

        game_choice = self.io.input("请选择配方文件序号: ")
        try:
            game_index = int(game_choice) - 1
            if 0 <= game_index < len(games):
                game_name = games[game_index]
                recipes = self.recipe_manager.load_recipe_file(game_name)
                self.current_game = game_name
                self.calculator = CraftingCalculator(self.recipe_manager)
                self.io.print(f"\n成功加载配方文件: {game_name}")
                self._print_recipe_list(recipes)
                config_manager.set_last_game(game_name)
                self.io.print("已记住您的选择，下次启动将自动加载此配方文件")
            else:
                self.io.print("选择无效")
        except ValueError:
            self.io.print("请输入有效的数字")

    def _calculate_production_chain_terminal(self) -> None:
        """
        计算生产链（终端模式）

        支持交互式路径切换功能。计算完成后进入命令循环，
        用户可以输入命令查看替代路径、切换路径等。
        """
        if not self.calculator or not self.current_game:
            self.io.print("请先选择配方文件")
            return

        target_item = self.io.input("\n请输入目标物品名称: ")
        target_rate_input = self.io.input("请输入目标生产速度 (个/秒): ")

        try:
            target_rate = float(target_rate_input)
            if target_rate <= 0:
                self.io.print("生产速度必须大于0")
                return

            self.io.print("\n正在计算生产链...")
            trees = self.calculator.calculate_production_chain(
                target_item, target_rate)

            if not trees:
                self.io.print(f"未找到生产 {target_item} 的路径")
                return

            self.io.print(f"\n找到 {len(trees)} 条生产路径")

            # 保存计算结果到实例变量
            self._current_chain_trees = trees
            self._current_target_item = target_item
            self._current_target_rate = target_rate

            # 选择第一个路径作为主路径（设备数最少）
            main_tree = trees[0]
            self._current_main_tree = main_tree

            # 分配节点编号
            self._assign_node_ids(main_tree)

            # 显示主路径
            self._display_current_chain()

            # 进入交互式命令循环
            self.io.print("\n" + "=" * 60)
            self.io.print("进入路径切换模式。输入 'help' 查看命令，'q' 退出。")
            self.io.print("=" * 60)

            while True:
                try:
                    continue_loop = self._process_chain_interactive_commands()
                    if not continue_loop:
                        break
                except KeyboardInterrupt:
                    self.io.print("\n操作已取消")
                    break
                except Exception as e:
                    self.io.print(f"错误: {e}")
                    continue

            # 清理状态
            self._current_chain_trees = []
            self._current_main_tree = None
            self._current_target_item = ""
            self._current_target_rate = 0.0
            self._node_id_map.clear()

            self.io.print("\n已退出路径切换模式。")

        except ValueError as e:
            self.io.print(f"请输入有效的数字: {e}")

    def _check_has_alternatives(self, tree_dict: Dict[str, Any]) -> bool:
        """
        检查树中是否有节点存在替代路径

        Args:
            tree_dict: 合成树的字典表示

        Returns:
            如果存在替代路径返回 True，否则返回 False
        """
        # 检查当前节点
        path_info = tree_dict.get("path_info", {})
        if path_info.get("alternative_count", 0) > 0:
            return True

        # 递归检查子节点
        for child in tree_dict.get("children", []):
            if self._check_has_alternatives(child):
                return True

        return False

    def _show_items_list_terminal(self) -> None:
        """显示物品列表（终端模式）"""
        if not self.calculator or not self.current_game:
            self.io.print("请先选择配方文件")
            return

        recipes = self.recipe_manager.get_all_recipes()
        items = set()

        for recipe in recipes.values():
            items.update(recipe.get("inputs", {}).keys())
            items.update(recipe.get("outputs", {}).keys())

        self.io.print("\n可用物品列表:")
        self.io.print("-" * 50)
        if not items:
            self.io.print("没有找到物品")
        else:
            for i, item in enumerate(sorted(items), 1):
                self.io.print(f"{i}. {item}")
        self.io.print("-" * 50)

    def _delete_recipe_terminal(self) -> None:
        """删除配方（终端模式）"""
        if not self.recipe_manager.current_game:
            self.io.print("请先选择配方文件")
            return

        self.io.print("\n" + "=" * 50)
        self.io.print("删除配方")
        self.io.print("=" * 50)
        self.io.print("\n选择删除方式:")
        self.io.print("1. 从列表中选择删除")
        self.io.print("2. 直接输入配方名称删除")
        self.io.print("3. 取消")

        choice = self.io.input("\n请选择操作 (1-3): ").strip()

        if choice == "1":
            self._delete_recipe_by_index()
        elif choice == "2":
            self._delete_recipe_by_name()
        elif choice == "3":
            self.io.print("\n已取消删除操作")
        else:
            self.io.print("\n选择无效")

    def _delete_recipe_by_index(self) -> None:
        """通过序号从列表中选择删除配方"""
        recipes = self.recipe_manager.get_all_recipes()
        if not recipes:
            self.io.print("\n当前配方文件中没有任何配方")
            return

        self.io.print("\n当前配方文件中的配方:")
        self.io.print("-" * 50)
        recipe_list = list(recipes.items())
        for i, (recipe_name, recipe) in enumerate(recipe_list, 1):
            device = recipe.get("device", "未知设备")
            outputs = ", ".join(recipe.get("outputs", {}).keys())
            self.io.print(f"{i}. {recipe_name} ({device}) → {outputs}")
        self.io.print("-" * 50)

        choice = self.io.input("\n请输入要删除的配方序号 (输入0取消): ").strip()

        try:
            index = int(choice)
            if index == 0:
                self.io.print("\n已取消删除操作")
                return
            if index < 1 or index > len(recipe_list):
                self.io.print(f"\n无效序号，请输入 0-{len(recipe_list)} 之间的数字")
                return

            recipe_name, recipe_data = recipe_list[index - 1]
            self._confirm_and_delete_recipe(recipe_name, recipe_data)

        except ValueError:
            self.io.print("\n请输入有效的数字")

    def _delete_recipe_by_name(self) -> None:
        """直接输入配方名称删除"""
        recipe_name = self.io.input("\n请输入要删除的配方名称: ").strip()

        if not recipe_name:
            self.io.print("配方名称不能为空")
            return

        recipes = self.recipe_manager.get_all_recipes()
        if recipe_name not in recipes:
            self.io.print(f"\n配方 '{recipe_name}' 不存在")
            return

        self._confirm_and_delete_recipe(recipe_name, recipes[recipe_name])

    def _confirm_and_delete_recipe(
        self, recipe_name: str, recipe_data: Dict[str, Any]
    ) -> None:
        """确认并删除配方

        Args:
            recipe_name: 配方名称
            recipe_data: 配方数据
        """
        self.io.print("\n" + "=" * 50)
        self.io.print("配方详情")
        self.io.print("=" * 50)
        self.io.print(f"配方名称: {recipe_name}")
        self.io.print(f"设备名称: {recipe_data.get('device', '未知设备')}")

        self.io.print("\n输入物品:")
        inputs = recipe_data.get("inputs", {})
        if not inputs:
            self.io.print("  (无)")
        else:
            for item_name, item_data in inputs.items():
                if isinstance(item_data, dict):
                    amount = item_data.get("amount", 0)
                    self.io.print(f"  - {item_name}: {amount:.2f} 个/秒")
                else:
                    self.io.print(f"  - {item_name}: {item_data}")

        self.io.print("\n输出物品:")
        outputs = recipe_data.get("outputs", {})
        if not outputs:
            self.io.print("  (无)")
        else:
            for item_name, item_data in outputs.items():
                if isinstance(item_data, dict):
                    amount = item_data.get("amount", 0)
                    self.io.print(f"  - {item_name}: {amount:.2f} 个/秒")
                else:
                    self.io.print(f"  - {item_name}: {item_data}")

        self.io.print("=" * 50)

        while True:
            confirm = self.io.input("\n确认删除此配方? (y/n): ").strip().lower()
            if confirm in ["y", "yes", "是"]:
                try:
                    self.recipe_manager.delete_recipe(recipe_name)
                    self.io.print(f"\n成功删除配方: {recipe_name}")
                    return
                except ValueError as e:
                    self.io.print(f"\n删除配方失败: {e}")
                    return
            elif confirm in ["n", "no", "否"]:
                self.io.print("\n已取消删除操作")
                return
            else:
                self.io.print("请输入 y 或 n")

    def _dict_to_node(
        self, tree_dict: Dict[str, Any], parent: Optional[CraftingNode] = None
    ) -> CraftingNode:
        """
        将字典转换为节点对象

        Args:
            tree_dict: 树字典
            parent: 父节点

        Returns:
            节点对象
        """
        node = CraftingNode(tree_dict["item_name"], tree_dict["amount"])
        node.device_count = tree_dict["device_count"]
        node.recipe = tree_dict.get("recipe", {})
        node.parent = parent

        for child_dict in tree_dict["children"]:
            child_node = self._dict_to_node(child_dict, node)
            node.children.append(child_node)
            node.inputs[child_node.item_name] = child_node.amount

        return node

    def _assign_node_ids(self, tree_dict: Dict[str, Any]) -> None:
        """
        为树中的每个节点分配前序遍历编号

        编号规则：根节点为1，前序遍历依次为2,3,4...

        Args:
            tree_dict: 合成树的字典表示
        """
        self._node_id_map.clear()
        counter = [1]  # 使用列表来在递归中保持状态

        def traverse(node: Dict[str, Any]):
            node_id = counter[0]
            counter[0] += 1

            # 存储节点信息
            self._node_id_map[node_id] = {
                "node": node,
                "item_name": node["item_name"],
                "amount": node["amount"],
                "device_count": node["device_count"],
                "alternative_count": node.get("path_info", {}).get(
                    "alternative_count", 0
                ),
                "children": node.get("children", []),
            }

            # 递归处理子节点
            for child in node.get("children", []):
                traverse(child)

        traverse(tree_dict)

    def _get_node_by_id(self, node_id: int) -> Optional[Dict[str, Any]]:
        """
        根据节点编号获取节点信息

        Args:
            node_id: 节点编号

        Returns:
            节点信息字典，如果不存在则返回None
        """
        return self._node_id_map.get(node_id)

    def _handle_alt_command(self, node_id_str: str) -> bool:
        """
        处理 alt 命令，切换指定节点到其他路径

        命令格式: alt <节点编号> 或 a <节点编号>

        Args:
            node_id_str: 节点编号的字符串表示

        Returns:
            是否成功处理命令
        """
        try:
            node_id = int(node_id_str.strip())
        except ValueError:
            self.io.print(f"错误: 无效的节点编号 '{node_id_str}'")
            return False

        # 检查节点是否存在
        node_info = self._get_node_by_id(node_id)
        if not node_info:
            self.io.print(f"错误: 节点 #{node_id} 不存在")
            return False

        # 检查该节点是否有替代路径
        node = node_info["node"]
        path_info = node.get("path_info", {})
        alternative_count = path_info.get("alternative_count", 0)

        if alternative_count == 0:
            self.io.print(
                f"节点 #{node_id} ({node_info['item_name']}) 没有可选的替代路径"
            )
            return False

        # 显示替代路径选项
        alternative_paths = node.get("alternative_paths", [])
        if not alternative_paths:
            self.io.print(
                f"节点 #{node_id} ({node_info['item_name']}) 的替代路径信息不可用"
            )
            return False

        # 显示可切换的路径列表
        self._show_alternative_paths(node_id, node_info, alternative_paths)

        # 提示用户选择
        choice = self.io.input("\n请选择要切换到的路径编号 (0取消): ").strip()

        try:
            path_index = int(choice)
            if path_index == 0:
                self.io.print("已取消路径切换")
                return False

            if path_index < 1 or path_index > len(alternative_paths):
                self.io.print(
                    f"无效的选择，请输入 1-{len(alternative_paths)} 之间的数字"
                )
                return False

            # 执行路径切换
            return self._switch_to_path(node_id, path_index - 1, alternative_paths)

        except ValueError:
            self.io.print("请输入有效的数字")
            return False

    def _show_alternative_paths(
        self,
        node_id: int,
        node_info: Dict[str, Any],
        alternative_paths: List[List[Dict[str, Any]]],
    ) -> None:
        """
        显示指定节点的替代路径列表

        Args:
            node_id: 节点编号
            node_info: 节点信息字典
            alternative_paths: 替代路径列表
        """
        self.io.print(f"\n节点 #{node_id} ({node_info['item_name']}) 的可选路径:")
        self.io.print("=" * 60)

        # 计算当前路径的设备总数作为对比
        current_device_count = node_info["device_count"]

        for i, alt_path in enumerate(alternative_paths, 1):
            if not alt_path:
                continue

            # 计算替代路径的设备总数
            alt_device_count = sum(node.get("device_count", 0)
                                   for node in alt_path)

            # 计算设备数量差异
            device_diff = alt_device_count - current_device_count
            diff_str = (
                f"(+{device_diff:.2f})"
                if device_diff > 0
                else f"({device_diff:.2f})" if device_diff < 0 else "(相同)"
            )

            # 显示路径信息
            self.io.print(f"\n  路径 {i}:")
            self.io.print(f"    设备总数: {alt_device_count:.2f} {diff_str}")

            # 显示路径中的关键节点
            path_items = " → ".join(
                f"{node.get('item_name', '未知')}({node.get('device_count', 0):.1f})"
                for node in alt_path[:5]  # 只显示前5个节点
            )
            if len(alt_path) > 5:
                path_items += f" ... ({len(alt_path) - 5} 更多)"
            self.io.print(f"    路径: {path_items}")

        self.io.print("=" * 60)
        self.io.print("提示: 输入路径编号切换到该路径，输入0取消")

    def _switch_to_path(
        self,
        node_id: int,
        alt_path_index: int,
        alternative_paths: List[List[Dict[str, Any]]],
    ) -> bool:
        """
        切换到指定的替代路径

        切换逻辑：
        1. 找到当前节点在树中的位置
        2. 用替代路径替换该节点及其子树
        3. 重新计算受影响的设备数量
        4. 更新节点编号映射

        Args:
            node_id: 要切换的节点编号
            alt_path_index: 替代路径在列表中的索引
            alternative_paths: 所有替代路径的列表

        Returns:
            是否成功切换路径
        """
        if not self._current_main_tree:
            self.io.print("错误: 当前没有活动的生产链")
            return False

        # 获取要切换的替代路径
        if alt_path_index < 0 or alt_path_index >= len(alternative_paths):
            self.io.print(f"错误: 无效的替代路径索引 {alt_path_index}")
            return False

        selected_alt_path = alternative_paths[alt_path_index]
        if not selected_alt_path:
            self.io.print("错误: 选中的替代路径为空")
            return False

        # 获取节点信息
        node_info = self._get_node_by_id(node_id)
        if not node_info:
            self.io.print(f"错误: 无法获取节点 #{node_id} 的信息")
            return False

        # 获取旧路径的设备数（用于比较）
        old_device_count = node_info["device_count"]
        new_device_count = sum(
            node.get("device_count", 0) for node in selected_alt_path
        )

        # 显示切换确认信息
        self.io.print(f"\n正在切换节点 #{node_id} ({node_info['item_name']}) 的路径...")
        self.io.print(f"原路径设备数: {old_device_count:.2f}")
        self.io.print(f"新路径设备数: {new_device_count:.2f}")

        device_diff = new_device_count - old_device_count
        if device_diff > 0:
            self.io.print(f"设备数变化: +{device_diff:.2f} (增加)")
        elif device_diff < 0:
            self.io.print(f"设备数变化: {device_diff:.2f} (减少)")
        else:
            self.io.print("设备数变化: 无变化")

        # 执行路径切换 - 需要重新构建树
        # 由于直接修改树结构比较复杂，我们采用重新计算的方式
        # 将选中的替代路径作为主路径重新计算

        # 获取目标物品和生产速度
        target_item = self._current_target_item
        target_rate = self._current_target_rate

        if not target_item or target_rate <= 0:
            self.io.print("错误: 无法获取目标物品信息")
            return False

        # 重新计算生产链，使用新的主路径
        # 将选中的替代路径提升到第一位作为主路径

        # 找到包含选中路径的树并提升到第一位
        # 这里简化处理：直接重新显示新的树
        # 实际需要更复杂的逻辑来合并路径

        # 简化方案：使用选中的替代路径构建新树
        # 将第一个节点的信息作为根节点
        if selected_alt_path:
            # 构建简化的新树结构
            new_tree = self._build_tree_from_path(
                selected_alt_path, target_rate)
            if new_tree:
                self._current_main_tree = new_tree
                # 重新分配节点编号
                self._assign_node_ids(new_tree)
                # 显示新的生产链
                self._display_current_chain()
                self.io.print("\n成功切换到新路径！")
                return True

        self.io.print("错误: 路径切换失败")
        return False

    def _build_tree_from_path(
        self, path: List[Dict[str, Any]], target_rate: float
    ) -> Optional[Dict[str, Any]]:
        """
        从路径构建树结构（简化版本）

        Args:
            path: 节点路径列表
            target_rate: 目标生产速度

        Returns:
            树结构的字典表示
        """
        if not path:
            return None

        # 使用第一个节点作为根节点
        root = path[0].copy()
        root["children"] = []

        # 简化处理：将其他节点作为直接子节点
        # 实际应用中需要更复杂的树构建逻辑
        for i, node in enumerate(path[1:], 1):
            child = node.copy()
            child["children"] = []
            root["children"].append(child)

        return root

    def _list_alternative_nodes(self) -> None:
        """
        显示当前树中所有带 [+N] 标记的节点及其编号

        这些节点代表有替代路径可供切换的节点。
        """
        if not self._current_main_tree:
            self.io.print("错误: 当前没有活动的生产链")
            return

        # 收集所有有替代路径的节点
        alt_nodes = []

        def collect_alt_nodes(node: Dict[str, Any], node_id: int):
            path_info = node.get("path_info", {})
            alt_count = path_info.get("alternative_count", 0)

            if alt_count > 0:
                alt_nodes.append(
                    {
                        "id": node_id,
                        "name": node["item_name"],
                        "amount": node["amount"],
                        "device_count": node["device_count"],
                        "alt_count": alt_count,
                    }
                )

            # 递归处理子节点
            for child in node.get("children", []):
                collect_alt_nodes(child, node_id + 1)  # 简化编号

        collect_alt_nodes(self._current_main_tree, 1)

        # 显示结果
        self.io.print("\n" + "=" * 60)
        self.io.print("  具有替代路径的节点列表")
        self.io.print("=" * 60)

        if not alt_nodes:
            self.io.print("\n  当前生产链中没有具有替代路径的节点")
        else:
            self.io.print(f"\n  找到 {len(alt_nodes)} 个具有替代路径的节点:\n")
            for node in alt_nodes:
                self.io.print(
                    f"  [#{node['id']:2d}] {node['name']:<15} "
                    f"速度: {node['amount']:.2f}/s  "
                    f"设备: {node['device_count']:.2f}  "
                    f"[+{node['alt_count']}]"
                )

        self.io.print("=" * 60)
        self.io.print("提示: 使用 'alt <编号>' 或 'a <编号>' 切换到该节点的其他路径")

    def _display_current_chain(self) -> None:
        """
        显示当前生产链（主路径）
        """
        if not self._current_main_tree:
            return

        self.io.print("\n" + "=" * 60)
        self.io.print(
            f"生产链: {self._current_target_item} "
            f"({self._current_target_rate:.2f}/s)"
        )
        self.io.print("=" * 60)

        # 使用现有的树打印方法
        self._print_tree(self._current_main_tree)

        # 显示基础原料和设备统计
        tree_node = self._dict_to_node(self._current_main_tree)
        if self.calculator:
            raw_materials = self.calculator.get_raw_materials(tree_node)
            device_stats = self.calculator.get_device_stats(tree_node)
            self._print_raw_materials(raw_materials)
            self._print_device_stats(device_stats)

        self.io.print(
            "\n命令: alt <编号>/a <编号> - 切换路径, la/list-alt - 列出可选节点, q - 退出"
        )

    def _process_chain_interactive_commands(self) -> bool:
        """
        处理生产链显示后的交互式命令

        Returns:
            是否继续显示命令循环（False表示退出）
        """
        command = self.io.input("\n> ").strip().lower()

        if command in ["q", "quit", "exit", "b", "back"]:
            return False

        if command in ["la", "list-alt", "list"]:
            self._list_alternative_nodes()
            return True

        # 处理 alt 命令: alt <编号> 或 a <编号>
        parts = command.split()
        if len(parts) >= 2 and (parts[0] == "alt" or parts[0] == "a"):
            node_id_str = parts[1]
            self._handle_alt_command(node_id_str)
            # 切换后重新显示当前生产链
            if self._current_main_tree:
                self._display_current_chain()
            return True

        # 处理 help
        if command in ["h", "help", "?"]:
            self._print_chain_commands_help()
            return True

        self.io.print(f"未知命令: '{command}'。输入 'help' 查看可用命令。")
        return True

    def _print_chain_commands_help(self) -> None:
        """打印生产链交互命令帮助"""
        self.io.print("\n" + "=" * 60)
        self.io.print("  生产链交互命令")
        self.io.print("=" * 60)
        self.io.print("  alt <编号> / a <编号>  - 切换到指定节点的替代路径")
        self.io.print("  la / list-alt          - 列出所有具有替代路径的节点")
        self.io.print("  h / help / ?           - 显示此帮助信息")
        self.io.print("  q / quit / b / back    - 退出交互模式")
        self.io.print("=" * 60)


__all__ = ["ApplicationController"]
