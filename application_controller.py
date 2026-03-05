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

    def run(self) -> None:
        """运行应用程序（终端模式）"""
        self.io.print("开始初始化应用程序...")

        try:
            self._initialize()

            while True:
                self._process_main_menu()

        except Exception as e:
            error_msg = f"应用程序发生错误:\n{str(e)}\n\n详细信息:\n{traceback.format_exc()}"
            self.io.print(error_msg)
            sys.exit(1)

    def process_command(self, command: str) -> Dict[str, Any]:
        """
        处理命令（Web模式）

        Args:
            command: 用户输入的命令

        Returns:
            包含output和prompt的字典
        """
        command = command.strip()

        if self.state == "main_menu":
            return self._handle_main_menu(command)
        elif self.state == "select_game":
            return self._handle_select_game(command)
        elif self.state == "calculate_item":
            return self._handle_calculate_item(command)
        elif self.state == "calculate_rate":
            return self._handle_calculate_rate(command)
        elif self.state == "add_recipe_device":
            return self._handle_add_recipe_device(command)
        elif self.state == "add_recipe_device_search":
            return self._handle_add_recipe_device_search(command)
        elif self.state == "add_recipe_outputs":
            return self._handle_add_recipe_outputs(command)
        elif self.state == "add_recipe_output_search":
            return self._handle_add_recipe_output_search(command)
        elif self.state == "add_recipe_output_amount":
            return self._handle_add_recipe_output_amount(command)
        elif self.state == "add_recipe_more_outputs":
            return self._handle_add_recipe_more_outputs(command)
        elif self.state == "add_recipe_inputs":
            return self._handle_add_recipe_inputs(command)
        elif self.state == "add_recipe_input_search":
            return self._handle_add_recipe_input_search(command)
        elif self.state == "add_recipe_input_amount":
            return self._handle_add_recipe_input_amount(command)
        elif self.state == "add_recipe_more_inputs":
            return self._handle_add_recipe_more_inputs(command)
        elif self.state == "add_recipe_confirm":
            return self._handle_add_recipe_confirm(command)
        else:
            self.state = "main_menu"
            return {"output": "状态错误，已返回主菜单", "prompt": "请选择操作 (1-5): "}

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
            self._add_recipe_interactive()
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
        self.io.print("4. 添加配方")
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

    def _print_tree(self, tree_dict: Dict[str, Any], indent: int = 0, is_last: bool = False, prefixes: Optional[List[str]] = None) -> None:
        """
        以树形结构打印合成树

        Args:
            tree_dict: 合成树的字典表示
            indent: 缩进级别
            is_last: 是否为父节点的最后一个子节点
            prefixes: 存储每一层的前缀字符
        """
        if prefixes is None:
            prefixes = []

        current_prefix = "".join(prefixes)
        if indent > 0:
            if is_last:
                current_prefix += "└─"
            else:
                current_prefix += "├─"

        item_name = tree_dict["item_name"]
        amount = tree_dict["amount"]
        device_count = tree_dict["device_count"]

        self.io.print(f"{current_prefix}{item_name}: {amount:.2f}/s")

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
            self._print_tree(child, indent + 1, child_is_last, child_prefixes)

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

    def _print_name_list(self, name_list: List[Tuple[str, int]], search_keyword: str = "") -> List[str]:
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
                amount_input = self.io.input(f"{prompt_prefix}请输入数量 (支持表达式，如 10 或 15/min): ")

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

    def _input_items_list(self, item_type: str, item_freq: List[Tuple[str, int]] = None, existing_names: Set[str] = None) -> Dict[str, Dict[str, Any]]:
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

            choice = self.io.input(f"\n是否继续添加{item_type}物品? (y/n): ").strip().lower()
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
                        filtered_search = self._print_name_list(name_list, user_input)
                        if filtered_search:
                            search_input = self.io.input(f"\n{prompt}: ").strip()
                            if not search_input:
                                self.io.print("输入不能为空，请重新输入")
                                continue

                            try:
                                search_index = int(search_input)
                                if 1 <= search_index <= len(filtered_search):
                                    selected_name = filtered_search[search_index - 1]
                                    if not allow_duplicate and selected_name in existing_names:
                                        self.io.print(f"名称 '{selected_name}' 已存在，请使用其他名称")
                                        continue
                                    return selected_name
                                else:
                                    self.io.print(f"请输入 1-{len(filtered_search)} 之间的数字")
                            except ValueError:
                                if search_input.isdigit():
                                    self.io.print(f"请输入 1-{len(filtered_search)} 之间的数字")
                                else:
                                    if not allow_duplicate and search_input in existing_names:
                                        self.io.print(f"名称 '{search_input}' 已存在，请使用其他名称")
                                        continue
                                    return search_input
                        else:
                            self.io.print(f"未找到匹配 '{user_input}' 的名称")
                            confirm = self.io.input(f"是否使用 '{user_input}' 作为新名称? (y/n): ").strip().lower()
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

    def _generate_recipe_id(self, outputs: Dict[str, Any], existing_recipes: Dict[str, Any]) -> str:
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
        inputs = self._input_items_list("输入", item_freq, existing_names=set(outputs.keys()))

        existing_recipes = self.recipe_manager.get_all_recipes()
        recipe_name = self._generate_recipe_id(outputs, existing_recipes)

        self._display_recipe_preview(recipe_name, device_name, inputs, outputs)

        if self._confirm_recipe():
            try:
                self.recipe_manager.add_recipe(recipe_name, device_name, inputs, outputs)
                self.io.print(f"\n成功添加配方: {recipe_name}")
            except ValueError as e:
                self.io.print(f"\n添加配方失败: {e}")
        else:
            self.io.print("\n已取消添加配方")

    def _display_recipe_preview(self, recipe_name: str, device_name: str, inputs: Dict[str, Dict[str, Any]], outputs: Dict[str, Dict[str, Any]]) -> None:
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
                self.io.print(f"  - {item_name}: {item_data['amount']:.2f} 个/秒 (表达式: {item_data['expression']})")

        self.io.print("\n输出物品:")
        if not outputs:
            self.io.print("  (无)")
        else:
            for item_name, item_data in outputs.items():
                self.io.print(f"  - {item_name}: {item_data['amount']:.2f} 个/秒 (表达式: {item_data['expression']})")

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
        """计算生产链（终端模式）"""
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
            trees = self.calculator.calculate_production_chain(target_item, target_rate)

            if not trees:
                self.io.print(f"未找到生产 {target_item} 的路径")
                return

            self.io.print(f"\n找到 {len(trees)} 条生产路径")

            for i, tree_dict in enumerate(trees, 1):
                self.io.print(f"\n路径 {i}:")
                self.io.print("=" * 50)
                self._print_tree(tree_dict)
                self.io.print("=" * 50)

                tree_node = self._dict_to_node(tree_dict)
                raw_materials = self.calculator.get_raw_materials(tree_node)
                device_stats = self.calculator.get_device_stats(tree_node)

                self._print_raw_materials(raw_materials)
                self._print_device_stats(device_stats)

        except ValueError:
            self.io.print("请输入有效的数字")

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

    def _dict_to_node(self, tree_dict: Dict[str, Any], parent: Optional[CraftingNode] = None) -> CraftingNode:
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

    def _handle_main_menu(self, command: str) -> Dict[str, Any]:
        """处理主菜单命令（Web模式）"""
        if command in ["help", "?"]:
            return {"output": self._print_help(), "prompt": "请选择操作 (1-5): "}

        if command in ["5", "exit", "quit"]:
            self._reset()
            return {"output": "会话已重置", "prompt": "请选择操作 (1-5): "}

        if command == "reset":
            self._reset()
            return {"output": "会话已重置", "prompt": "请选择操作 (1-5): "}

        if command == "1" or command.startswith("1 "):
            parts = command.split(maxsplit=1)
            if len(parts) == 2:
                return self._select_game_by_index(parts[1])
            else:
                return self._show_game_list()

        if command == "2" or command.startswith("2 "):
            if not self.calculator or not self.current_game:
                return {"output": "请先选择配方文件", "prompt": "请选择操作 (1-5): "}

            parts = command.split(maxsplit=2)
            if len(parts) == 3:
                return self._calculate_direct(parts[1], parts[2])
            else:
                self.state = "calculate_item"
                return {"output": "", "prompt": "请输入目标物品名称: "}

        if command == "3":
            return self._show_items_list()

        if command == "4":
            if not self.current_game:
                return {"output": "请先选择配方文件", "prompt": "请选择操作 (1-5): "}
            self.state = "add_recipe_device"
            self.pending_data = {"inputs": {}, "outputs": {}}
            device_freq = self.recipe_manager.get_device_frequency()
            output = "\n" + "=" * 50 + "\n添加新配方\n" + "=" * 50
            output += self._print_name_list_to_string(device_freq)
            return {"output": output, "prompt": "请输入设备名称: "}

        return {"output": "选择无效，请输入1-5之间的数字", "prompt": "请选择操作 (1-5): "}

    def _print_help(self) -> str:
        """返回帮助信息"""
        return """可用命令:
  1          - 选择配方文件（显示列表）
  1 <序号>   - 直接选择指定配方文件
  2          - 计算生产链（进入交互流程）
  2 <物品> <速度> - 直接计算生产链
  3          - 查看可用物品列表
  4          - 添加配方（进入交互流程）
  5/exit/quit - 退出/重置会话
  help       - 显示帮助信息
  reset      - 重置会话状态"""

    def _reset(self) -> None:
        """重置会话状态"""
        self.recipe_manager = RecipeManager()
        self.calculator = None
        self.current_game = None
        self.state = "main_menu"
        self.pending_data = {}

    def _show_game_list(self) -> Dict[str, Any]:
        """显示配方文件列表"""
        games = self.recipe_manager.get_available_games()
        if not games:
            return {"output": "没有找到配方文件", "prompt": "请选择操作 (1-5): "}

        lines = ["\n可用的配方文件:"]
        for i, game in enumerate(games, 1):
            lines.append(f"{i}. {game}")

        self.pending_data["games"] = games
        self.state = "select_game"
        return {"output": "\n".join(lines), "prompt": "请选择配方文件序号: "}

    def _select_game_by_index(self, index_str: str) -> Dict[str, Any]:
        """通过序号选择配方文件"""
        games = self.recipe_manager.get_available_games()
        try:
            index = int(index_str) - 1
            if 0 <= index < len(games):
                return self._load_game(games[index])
            else:
                return {"output": "选择无效", "prompt": "请选择操作 (1-5): "}
        except ValueError:
            return {"output": "请输入有效的数字", "prompt": "请选择操作 (1-5): "}

    def _handle_select_game(self, command: str) -> Dict[str, Any]:
        """处理选择配方文件"""
        games = self.pending_data.get("games", [])
        try:
            index = int(command) - 1
            if 0 <= index < len(games):
                result = self._load_game(games[index])
                self.state = "main_menu"
                return result
            else:
                return {"output": "选择无效", "prompt": "请选择配方文件序号: "}
        except ValueError:
            return {"output": "请输入有效的数字", "prompt": "请选择配方文件序号: "}

    def _load_game(self, game_name: str) -> Dict[str, Any]:
        """加载配方文件"""
        try:
            recipes = self.recipe_manager.load_recipe_file(game_name)
            self.current_game = game_name
            self.calculator = CraftingCalculator(self.recipe_manager)
            config_manager.set_last_game(game_name)
            output = f"\n成功加载配方文件: {game_name}\n"
            output += self._print_recipe_list_to_string(recipes)
            output += "\n已记住您的选择，下次启动将自动加载此配方文件"
            return {"output": output, "prompt": "请选择操作 (1-5): "}
        except Exception as e:
            return {"output": f"加载配方文件失败: {e}", "prompt": "请选择操作 (1-5): "}

    def _handle_calculate_item(self, command: str) -> Dict[str, Any]:
        """处理输入目标物品"""
        if not command:
            return {"output": "物品名称不能为空", "prompt": "请输入目标物品名称: "}

        self.pending_data["target_item"] = command.strip()
        self.state = "calculate_rate"
        return {"output": "", "prompt": "请输入目标生产速度 (个/秒): "}

    def _handle_calculate_rate(self, command: str) -> Dict[str, Any]:
        """处理输入生产速度"""
        try:
            target_rate = float(command)
            if target_rate <= 0:
                return {"output": "生产速度必须大于0", "prompt": "请输入目标生产速度 (个/秒): "}

            target_item = self.pending_data.get("target_item", "")
            result = self._calculate_direct(target_item, str(target_rate))
            self.state = "main_menu"
            self.pending_data = {}
            return result
        except ValueError:
            return {"output": "请输入有效的数字", "prompt": "请输入目标生产速度 (个/秒): "}

    def _calculate_direct(self, item: str, rate_str: str) -> Dict[str, Any]:
        """直接计算生产链"""
        try:
            target_rate = float(rate_str)
            if target_rate <= 0:
                return {"output": "生产速度必须大于0", "prompt": "请选择操作 (1-5): "}
            return self._do_calculate(item, target_rate)
        except ValueError:
            return {"output": "请输入有效的数字", "prompt": "请选择操作 (1-5): "}

    def _do_calculate(self, target_item: str, target_rate: float) -> Dict[str, Any]:
        """执行计算"""
        if not self.calculator:
            return {"output": "请先选择配方文件", "prompt": "请选择操作 (1-5): "}

        trees = self.calculator.calculate_production_chain(target_item, target_rate)

        if not trees:
            return {"output": f"未找到生产 {target_item} 的路径", "prompt": "请选择操作 (1-5): "}

        output = f"\n正在计算生产链...\n\n找到 {len(trees)} 条生产路径"

        for i, tree_dict in enumerate(trees, 1):
            output += f"\n\n路径 {i}:"
            output += "\n" + "=" * 50
            output += "\n" + self._print_tree_to_string(tree_dict)
            output += "\n" + "=" * 50

            tree_node = self._dict_to_node(tree_dict)
            raw_materials = self.calculator.get_raw_materials(tree_node)
            device_stats = self.calculator.get_device_stats(tree_node)

            output += "\n" + self._print_raw_materials_to_string(raw_materials)
            output += "\n" + self._print_device_stats_to_string(device_stats)

        return {"output": output, "prompt": "请选择操作 (1-5): "}

    def _show_items_list(self) -> Dict[str, Any]:
        """显示物品列表"""
        if not self.calculator or not self.current_game:
            return {"output": "请先选择配方文件", "prompt": "请选择操作 (1-5): "}

        recipes = self.recipe_manager.get_all_recipes()
        items = set()

        for recipe in recipes.values():
            items.update(recipe.get("inputs", {}).keys())
            items.update(recipe.get("outputs", {}).keys())

        lines = ["\n可用物品列表:", "-" * 50]
        if not items:
            lines.append("没有找到物品")
        else:
            for i, item in enumerate(sorted(items), 1):
                lines.append(f"{i}. {item}")
        lines.append("-" * 50)

        return {"output": "\n".join(lines), "prompt": "请选择操作 (1-5): "}

    def _handle_add_recipe_device(self, command: str) -> Dict[str, Any]:
        """处理输入设备名称"""
        if not command.strip():
            return {"output": "设备名称不能为空", "prompt": "请输入设备名称: "}

        device_freq = self.recipe_manager.get_device_frequency()
        self.pending_data["device_freq"] = device_freq

        try:
            index = int(command.strip())
            if 1 <= index <= len(device_freq):
                device_name = device_freq[index - 1][0]
                self.pending_data["device"] = device_name
                self.pending_data["item_freq"] = self.recipe_manager.get_item_frequency()
                self.pending_data["existing_items"] = set()
                self.state = "add_recipe_outputs"
                return {"output": "\n--- 配置输出物品 ---", "prompt": "请输入输出物品名称: "}
            else:
                return {"output": f"请输入 1-{len(device_freq)} 之间的数字", "prompt": "请输入设备名称: "}
        except ValueError:
            if command.strip().isdigit():
                return {"output": f"请输入 1-{len(device_freq)} 之间的数字", "prompt": "请输入设备名称: "}
            elif len(command.strip()) <= 2:
                self.pending_data["device_search_keyword"] = command.strip()
                self.state = "add_recipe_device_search"
                output = self._print_name_list_to_string(device_freq, command.strip())
                return {"output": output, "prompt": "请输入设备名称: "}
            else:
                self.pending_data["device"] = command.strip()
                self.pending_data["item_freq"] = self.recipe_manager.get_item_frequency()
                self.pending_data["existing_items"] = set()
                self.state = "add_recipe_outputs"
                return {"output": "\n--- 配置输出物品 ---", "prompt": "请输入输出物品名称: "}

    def _handle_add_recipe_device_search(self, command: str) -> Dict[str, Any]:
        """处理设备名称搜索"""
        device_freq = self.pending_data.get("device_freq", [])
        search_keyword = self.pending_data.get("device_search_keyword", "")

        if not command.strip():
            return {"output": "输入不能为空，请重新输入", "prompt": "请输入设备名称: "}

        try:
            index = int(command.strip())
            filtered_names = [name for name, freq in device_freq if search_keyword.lower() in name.lower()]
            if 1 <= index <= len(filtered_names):
                device_name = filtered_names[index - 1]
                self.pending_data["device"] = device_name
                self.pending_data["item_freq"] = self.recipe_manager.get_item_frequency()
                self.pending_data["existing_items"] = set()
                self.state = "add_recipe_outputs"
                return {"output": "\n--- 配置输出物品 ---", "prompt": "请输入输出物品名称: "}
            else:
                return {"output": f"请输入 1-{len(filtered_names)} 之间的数字", "prompt": "请输入设备名称: "}
        except ValueError:
            if command.strip().isdigit():
                filtered_names = [name for name, freq in device_freq if search_keyword.lower() in name.lower()]
                return {"output": f"请输入 1-{len(filtered_names)} 之间的数字", "prompt": "请输入设备名称: "}
            else:
                self.pending_data["device"] = command.strip()
                self.pending_data["item_freq"] = self.recipe_manager.get_item_frequency()
                self.pending_data["existing_items"] = set()
                self.state = "add_recipe_outputs"
                return {"output": "\n--- 配置输出物品 ---", "prompt": "请输入输出物品名称: "}

    def _handle_add_recipe_outputs(self, command: str) -> Dict[str, Any]:
        """处理输入输出物品名称"""
        if not command.strip():
            return {"output": "物品名称不能为空", "prompt": "请输入输出物品名称: "}

        item_freq = self.pending_data.get("item_freq", [])
        existing_items = self.pending_data.get("existing_items", set())

        try:
            index = int(command.strip())
            if 1 <= index <= len(item_freq):
                item_name = item_freq[index - 1][0]
                if item_name in self.pending_data["outputs"]:
                    return {"output": f"物品 '{item_name}' 已存在，请使用其他名称", "prompt": "请输入输出物品名称: "}
                self.pending_data["current_item"] = item_name
                self.state = "add_recipe_output_amount"
                return {"output": "", "prompt": f"请输入 {item_name} 的数量 (支持表达式，如 10 或 15/min): "}
            else:
                return {"output": f"请输入 1-{len(item_freq)} 之间的数字", "prompt": "请输入输出物品名称: "}
        except ValueError:
            if command.strip().isdigit():
                return {"output": f"请输入 1-{len(item_freq)} 之间的数字", "prompt": "请输入输出物品名称: "}
            elif len(command.strip()) <= 2:
                self.pending_data["output_search_keyword"] = command.strip()
                self.state = "add_recipe_output_search"
                output = self._print_name_list_to_string(item_freq, command.strip())
                return {"output": output, "prompt": "请输入输出物品名称: "}
            else:
                item_name = command.strip()
                if item_name in self.pending_data["outputs"]:
                    return {"output": f"物品 '{item_name}' 已存在，请使用其他名称", "prompt": "请输入输出物品名称: "}
                self.pending_data["current_item"] = item_name
                self.state = "add_recipe_output_amount"
                return {"output": "", "prompt": f"请输入 {item_name} 的数量 (支持表达式，如 10 或 15/min): "}

    def _handle_add_recipe_output_search(self, command: str) -> Dict[str, Any]:
        """处理输出物品名称搜索"""
        item_freq = self.pending_data.get("item_freq", [])
        search_keyword = self.pending_data.get("output_search_keyword", "")

        if not command.strip():
            return {"output": "输入不能为空，请重新输入", "prompt": "请输入输出物品名称: "}

        try:
            index = int(command.strip())
            filtered_names = [name for name, freq in item_freq if search_keyword.lower() in name.lower()]
            if 1 <= index <= len(filtered_names):
                item_name = filtered_names[index - 1]
                if item_name in self.pending_data["outputs"]:
                    return {"output": f"物品 '{item_name}' 已存在，请使用其他名称", "prompt": "请输入输出物品名称: "}
                self.pending_data["current_item"] = item_name
                self.state = "add_recipe_output_amount"
                return {"output": "", "prompt": f"请输入 {item_name} 的数量 (支持表达式，如 10 或 15/min): "}
            else:
                return {"output": f"请输入 1-{len(filtered_names)} 之间的数字", "prompt": "请输入输出物品名称: "}
        except ValueError:
            if command.strip().isdigit():
                filtered_names = [name for name, freq in item_freq if search_keyword.lower() in name.lower()]
                return {"output": f"请输入 1-{len(filtered_names)} 之间的数字", "prompt": "请输入输出物品名称: "}
            else:
                item_name = command.strip()
                if item_name in self.pending_data["outputs"]:
                    return {"output": f"物品 '{item_name}' 已存在，请使用其他名称", "prompt": "请输入输出物品名称: "}
                self.pending_data["current_item"] = item_name
                self.state = "add_recipe_output_amount"
                return {"output": "", "prompt": f"请输入 {item_name} 的数量 (支持表达式，如 10 或 15/min): "}

    def _handle_add_recipe_output_amount(self, command: str) -> Dict[str, Any]:
        """处理输入输出物品数量"""
        try:
            amount = parse_expression(command.strip())
            if amount <= 0:
                return {"output": "数量必须大于0，请重新输入", "prompt": f"请输入 {self.pending_data['current_item']} 的数量: "}

            item_name = self.pending_data["current_item"]
            self.pending_data["outputs"][item_name] = {"amount": amount, "expression": command.strip()}
            existing_items = self.pending_data.get("existing_items", set())
            existing_items.add(item_name)
            self.pending_data["existing_items"] = existing_items
            self.pending_data["show_item_list"] = True
            self.state = "add_recipe_more_outputs"
            return {"output": "", "prompt": "是否继续添加输出物品? (y/n): "}
        except Exception as e:
            return {"output": f"表达式格式无效: {e}", "prompt": f"请输入 {self.pending_data['current_item']} 的数量: "}

    def _handle_add_recipe_more_outputs(self, command: str) -> Dict[str, Any]:
        """处理是否继续添加输出物品"""
        if command.strip().lower() in ["y", "yes", "是"]:
            item_freq = self.pending_data.get("item_freq", [])
            output = "\n--- 配置输出物品 ---"
            output += self._print_name_list_to_string(item_freq)
            self.state = "add_recipe_outputs"
            return {"output": output, "prompt": "请输入输出物品名称: "}
        else:
            if not self.pending_data["outputs"]:
                return {"output": "错误: 至少需要一个输出物品", "prompt": "请选择操作 (1-5): "}

            item_freq = self.pending_data.get("item_freq", [])
            output = "\n--- 配置输入物品 ---"
            output += self._print_name_list_to_string(item_freq)
            self.pending_data["show_item_list"] = True
            self.state = "add_recipe_inputs"
            return {"output": output, "prompt": "请输入输入物品名称: "}

    def _handle_add_recipe_inputs(self, command: str) -> Dict[str, Any]:
        """处理输入物品名称"""
        if not command.strip():
            return {"output": "物品名称不能为空", "prompt": "请输入输入物品名称: "}

        item_freq = self.pending_data.get("item_freq", [])
        existing_items = self.pending_data.get("existing_items", set())
        existing_items.update(self.pending_data["outputs"].keys())

        try:
            index = int(command.strip())
            if 1 <= index <= len(item_freq):
                item_name = item_freq[index - 1][0]
                if item_name in self.pending_data["inputs"]:
                    return {"output": f"物品 '{item_name}' 已存在，请使用其他名称", "prompt": "请输入输入物品名称: "}
                self.pending_data["current_item"] = item_name
                self.state = "add_recipe_input_amount"
                return {"output": "", "prompt": f"请输入 {item_name} 的数量 (支持表达式，如 10 或 15/min): "}
            else:
                return {"output": f"请输入 1-{len(item_freq)} 之间的数字", "prompt": "请输入输入物品名称: "}
        except ValueError:
            if command.strip().isdigit():
                return {"output": f"请输入 1-{len(item_freq)} 之间的数字", "prompt": "请输入输入物品名称: "}
            elif len(command.strip()) <= 2:
                self.pending_data["input_search_keyword"] = command.strip()
                self.state = "add_recipe_input_search"
                output = self._print_name_list_to_string(item_freq, command.strip())
                return {"output": output, "prompt": "请输入输入物品名称: "}
            else:
                item_name = command.strip()
                if item_name in self.pending_data["inputs"]:
                    return {"output": f"物品 '{item_name}' 已存在，请使用其他名称", "prompt": "请输入输入物品名称: "}
                self.pending_data["current_item"] = item_name
                self.state = "add_recipe_input_amount"
                return {"output": "", "prompt": f"请输入 {item_name} 的数量 (支持表达式，如 10 或 15/min): "}

    def _handle_add_recipe_input_search(self, command: str) -> Dict[str, Any]:
        """处理输入物品名称搜索"""
        item_freq = self.pending_data.get("item_freq", [])
        search_keyword = self.pending_data.get("input_search_keyword", "")

        if not command.strip():
            return {"output": "输入不能为空，请重新输入", "prompt": "请输入输入物品名称: "}

        try:
            index = int(command.strip())
            filtered_names = [name for name, freq in item_freq if search_keyword.lower() in name.lower()]
            if 1 <= index <= len(filtered_names):
                item_name = filtered_names[index - 1]
                if item_name in self.pending_data["inputs"]:
                    return {"output": f"物品 '{item_name}' 已存在，请使用其他名称", "prompt": "请输入输入物品名称: "}
                self.pending_data["current_item"] = item_name
                self.state = "add_recipe_input_amount"
                return {"output": "", "prompt": f"请输入 {item_name} 的数量 (支持表达式，如 10 或 15/min): "}
            else:
                return {"output": f"请输入 1-{len(filtered_names)} 之间的数字", "prompt": "请输入输入物品名称: "}
        except ValueError:
            if command.strip().isdigit():
                filtered_names = [name for name, freq in item_freq if search_keyword.lower() in name.lower()]
                return {"output": f"请输入 1-{len(filtered_names)} 之间的数字", "prompt": "请输入输入物品名称: "}
            else:
                item_name = command.strip()
                if item_name in self.pending_data["inputs"]:
                    return {"output": f"物品 '{item_name}' 已存在，请使用其他名称", "prompt": "请输入输入物品名称: "}
                self.pending_data["current_item"] = item_name
                self.state = "add_recipe_input_amount"
                return {"output": "", "prompt": f"请输入 {item_name} 的数量 (支持表达式，如 10 或 15/min): "}

    def _handle_add_recipe_input_amount(self, command: str) -> Dict[str, Any]:
        """处理输入物品数量"""
        try:
            amount = parse_expression(command.strip())
            if amount <= 0:
                return {"output": "数量必须大于0，请重新输入", "prompt": f"请输入 {self.pending_data['current_item']} 的数量: "}

            item_name = self.pending_data["current_item"]
            self.pending_data["inputs"][item_name] = {"amount": amount, "expression": command.strip()}
            existing_items = self.pending_data.get("existing_items", set())
            existing_items.add(item_name)
            self.pending_data["existing_items"] = existing_items
            self.state = "add_recipe_more_inputs"
            return {"output": "", "prompt": "是否继续添加输入物品? (y/n): "}
        except Exception as e:
            return {"output": f"表达式格式无效: {e}", "prompt": f"请输入 {self.pending_data['current_item']} 的数量: "}

    def _handle_add_recipe_more_inputs(self, command: str) -> Dict[str, Any]:
        """处理是否继续添加输入物品"""
        if command.strip().lower() in ["y", "yes", "是"]:
            item_freq = self.pending_data.get("item_freq", [])
            output = "\n--- 配置输入物品 ---"
            output += self._print_name_list_to_string(item_freq)
            self.state = "add_recipe_inputs"
            return {"output": output, "prompt": "请输入输入物品名称: "}
        else:
            return self._show_recipe_preview()

    def _show_recipe_preview(self) -> Dict[str, Any]:
        """显示配方预览"""
        outputs = self.pending_data["outputs"]
        existing_recipes = self.recipe_manager.get_all_recipes()
        recipe_name = self._generate_recipe_id(outputs, existing_recipes)
        self.pending_data["recipe_name"] = recipe_name

        output = "\n" + "=" * 50
        output += "\n配方预览"
        output += "\n" + "=" * 50
        output += f"\n配方名称: {recipe_name}"
        output += f"\n设备名称: {self.pending_data['device']}"

        output += "\n\n输入物品:"
        if not self.pending_data["inputs"]:
            output += "\n  (无)"
        else:
            for item_name, item_data in self.pending_data["inputs"].items():
                output += f"\n  - {item_name}: {item_data['amount']:.2f} 个/秒 (表达式: {item_data['expression']})"

        output += "\n\n输出物品:"
        for item_name, item_data in outputs.items():
            output += f"\n  - {item_name}: {item_data['amount']:.2f} 个/秒 (表达式: {item_data['expression']})"

        output += "\n" + "=" * 50

        self.state = "add_recipe_confirm"
        return {"output": output, "prompt": "是否保存此配方? (y/n): "}

    def _handle_add_recipe_confirm(self, command: str) -> Dict[str, Any]:
        """处理确认保存配方"""
        if command.strip().lower() in ["y", "yes", "是"]:
            try:
                self.recipe_manager.add_recipe(
                    self.pending_data["recipe_name"],
                    self.pending_data["device"],
                    self.pending_data["inputs"],
                    self.pending_data["outputs"]
                )
                self.state = "main_menu"
                recipe_name = self.pending_data.get("recipe_name", "")
                self.pending_data = {}
                return {"output": f"\n成功添加配方: {recipe_name}", "prompt": "请选择操作 (1-5): "}
            except ValueError as e:
                self.state = "main_menu"
                return {"output": f"\n添加配方失败: {e}", "prompt": "请选择操作 (1-5): "}
        else:
            self.state = "main_menu"
            self.pending_data = {}
            return {"output": "\n已取消添加配方", "prompt": "请选择操作 (1-5): "}

    def _print_name_list_to_string(self, name_list: List[Tuple[str, int]], search_keyword: str = "") -> str:
        """
        返回名称列表文本，支持搜索过滤

        Args:
            name_list: 名称及其频率的列表
            search_keyword: 搜索关键词

        Returns:
            名称列表文本
        """
        filtered_names = []
        for name, freq in name_list:
            if not search_keyword or search_keyword.lower() in name.lower():
                filtered_names.append(name)

        lines = []
        if filtered_names:
            lines.append(f"\n已有名称列表 (共 {len(filtered_names)} 项):")
            lines.append("-" * 50)
            for i, name in enumerate(filtered_names, 1):
                freq = next(f for n, f in name_list if n == name)
                lines.append(f"{i}. {name} (使用次数: {freq})")
            lines.append("-" * 50)
            lines.append("提示: 输入数字选择，或输入字符搜索，或直接输入新名称")
        else:
            lines.append(f"\n未找到匹配 '{search_keyword}' 的名称")

        return "\n".join(lines)

    def _print_recipe_list_to_string(self, recipes: Dict[str, Any]) -> str:
        """
        返回配方列表文本

        Args:
            recipes: 配方字典

        Returns:
            配方列表文本
        """
        lines = ["\n当前配方文件中的配方:", "-" * 50]
        if not recipes:
            lines.append("配方文件为空")
        else:
            for i, (recipe_name, recipe) in enumerate(recipes.items(), 1):
                device = recipe.get("device", "未知设备")
                outputs = ", ".join(recipe.get("outputs", {}).keys())
                lines.append(f"{i}. {recipe_name} ({device}) → {outputs}")
        lines.append("-" * 50)
        return "\n".join(lines)

    def _print_tree_to_string(self, tree_dict: Dict[str, Any], indent: int = 0, is_last: bool = False, prefixes: Optional[List[str]] = None) -> str:
        """
        返回树形结构文本

        Args:
            tree_dict: 合成树的字典表示
            indent: 缩进级别
            is_last: 是否为父节点的最后一个子节点
            prefixes: 存储每一层的前缀字符

        Returns:
            树形结构文本
        """
        if prefixes is None:
            prefixes = []

        lines = []
        current_prefix = "".join(prefixes)
        if indent > 0:
            if is_last:
                current_prefix += "└─"
            else:
                current_prefix += "├─"

        item_name = tree_dict["item_name"]
        amount = tree_dict["amount"]
        device_count = tree_dict["device_count"]

        lines.append(f"{current_prefix}{item_name}: {amount:.2f}/s")

        if device_count > 0:
            device_info_prefix = "".join(prefixes)
            if indent > 0:
                if is_last:
                    device_info_prefix += "  "
                else:
                    device_info_prefix += "│ "
            lines.append(f"{device_info_prefix}│设备数: {device_count:.2f}")
            if "recipe" in tree_dict and tree_dict["recipe"]:
                device = tree_dict["recipe"].get("device", "未知设备")
                lines.append(f"{device_info_prefix}│设备: {device}")

        children = tree_dict["children"]
        for i, child in enumerate(children):
            child_is_last = i == len(children) - 1
            child_prefixes = prefixes.copy()
            if indent > 0:
                if is_last:
                    child_prefixes.append("  ")
                else:
                    child_prefixes.append("│ ")
            lines.append(self._print_tree_to_string(child, indent + 1, child_is_last, child_prefixes))

        return "\n".join(lines)

    def _print_raw_materials_to_string(self, raw_materials: Dict[str, float]) -> str:
        """
        返回基础原料消耗文本

        Args:
            raw_materials: 基础原料字典

        Returns:
            基础原料消耗文本
        """
        lines = ["\n基础原料消耗:", "-" * 50]
        if not raw_materials:
            lines.append("无基础原料消耗")
        else:
            for item, amount in raw_materials.items():
                lines.append(f"{item}: {amount:.2f}/s")
        lines.append("-" * 50)
        return "\n".join(lines)

    def _print_device_stats_to_string(self, device_stats: Dict[str, float]) -> str:
        """
        返回设备统计文本

        Args:
            device_stats: 设备统计字典

        Returns:
            设备统计文本
        """
        lines = ["\n设备统计:", "-" * 50]
        if not device_stats:
            lines.append("无设备使用")
        else:
            for device, count in device_stats.items():
                lines.append(f"{device}: {count:.2f} 台")
        lines.append("-" * 50)
        return "\n".join(lines)


__all__ = ["ApplicationController"]
