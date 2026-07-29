"""
应用程序控制器

包含所有业务逻辑，通过IOInterface与用户交互。

无状态单步命令模式：会话进程内存不保存任何业务状态，
所有状态通过命令参数传递或持久化到 config.yaml。
每条命令独立执行，命令间不共享内存状态。
"""

import sys
from typing import Dict, Any, Tuple, Optional, List

from io_interface import IOInterface
from data_manager import RecipeManager
from calculator import CraftingCalculator, CraftingNode
from config_manager import config_manager
from expression_parser import parse_expression


class ApplicationController:
    """应用程序控制器 - 无状态单步命令模式"""

    def __init__(self, io: IOInterface):
        """
        初始化应用程序控制器

        Args:
            io: 输入输出接口
        """
        self.io = io
        self.recipe_manager = RecipeManager()

    # ==================================================================
    # REPL 主循环
    # ==================================================================

    def run(self) -> None:
        """运行应用程序（无状态 REPL）"""
        self._print_welcome()
        while True:
            try:
                line = self.io.input("\n> ").strip()
                if not line:
                    continue
                self._dispatch(line)
            except KeyboardInterrupt:
                self.io.print("\n退出程序...")
                sys.exit(0)
            except SystemExit:
                raise
            except Exception as e:
                self.io.print(f"错误: {e}")

    def _print_welcome(self) -> None:
        """打印欢迎信息（从 config.yaml 读取当前配方文件，不保存到内存）"""
        self.io.print("=" * 50)
        self.io.print("  自动化建造游戏通用合成计算器")
        self.io.print("=" * 50)
        game = config_manager.get_last_game()
        if game:
            available = self.recipe_manager.get_available_games()
            if game in available:
                self.io.print(f"当前配方文件: {game}")
            else:
                self.io.print(
                    f"上次选择的配方文件 '{game}' 不存在，请使用 'use <文件名>' 选择"
                )
        else:
            self.io.print("未选择配方文件，使用 'use <文件名>' 选择")
        self.io.print("输入 'help' 查看可用命令")

    def _dispatch(self, line: str) -> None:
        """
        解析并分发命令

        Args:
            line: 用户输入的完整命令行
        """
        parts = line.split()
        if not parts:
            return
        cmd = parts[0].lower()
        args = parts[1:]

        if cmd in ("quit", "exit", "q"):
            self.io.print("退出程序...")
            sys.exit(0)
        elif cmd in ("help", "?"):
            self._cmd_help(args)
        elif cmd == "games":
            self._cmd_games(args)
        elif cmd == "use":
            self._cmd_use(args)
        elif cmd == "game":
            self._cmd_game(args)
        elif cmd == "calc":
            self._cmd_calc(args)
        elif cmd == "alts":
            self._cmd_alts(args)
        elif cmd == "use-path":
            self._cmd_use_path(args)
        elif cmd == "items":
            self._cmd_items(args)
        elif cmd == "recipes":
            self._cmd_recipes(args)
        elif cmd == "recipe":
            self._cmd_recipe(args)
        else:
            self.io.print(f"未知命令: '{cmd}'。输入 'help' 查看可用命令。")

    # ==================================================================
    # 上下文获取（每次命令从 config.yaml 读取，不缓存）
    # ==================================================================

    def _require_game(self) -> Optional[Tuple[str, CraftingCalculator]]:
        """
        读取当前配方文件并构建计算器（每次命令重新加载，不缓存）

        Returns:
            (game_name, calculator) 元组，失败时返回 None
        """
        game = config_manager.get_last_game()
        if not game:
            self.io.print("请先选择配方文件（使用 'use <文件名>'）")
            return None
        available = self.recipe_manager.get_available_games()
        if game not in available:
            self.io.print(
                f"配方文件 '{game}' 不存在，请使用 'use <文件名>' 重新选择"
            )
            return None
        try:
            self.recipe_manager.load_recipe_file(game)
        except Exception as e:
            self.io.print(f"加载配方文件 '{game}' 失败: {e}")
            return None
        calc = CraftingCalculator(self.recipe_manager)
        return game, calc

    # ==================================================================
    # 参数解析辅助
    # ==================================================================

    def _parse_rate(self, s: str) -> float:
        """解析速度表达式（支持 15/min、8*3/2 等）"""
        return parse_expression(s)

    def _parse_item_list(self, s: str) -> Dict[str, Dict[str, Any]]:
        """
        解析物品列表字符串为配方数据结构

        格式: 物品A:表达式,物品B:表达式 （如 铁矿石:10,煤:5）
        表达式可省略，默认为 "1"
        """
        result: Dict[str, Dict[str, Any]] = {}
        if not s:
            return result
        for entry in s.split(","):
            entry = entry.strip()
            if not entry:
                continue
            if ":" in entry:
                name, expr = entry.split(":", 1)
                name = name.strip()
                expr = expr.strip()
            else:
                name = entry
                expr = "1"
            amount = parse_expression(expr)
            result[name] = {"amount": amount, "expression": expr}
        return result

    def _parse_flags(self, args: List[str]) -> Dict[str, str]:
        """解析 --key value 形式的标志参数"""
        flags: Dict[str, str] = {}
        i = 0
        while i < len(args):
            if args[i].startswith("--"):
                key = args[i][2:]
                if i + 1 < len(args):
                    flags[key] = args[i + 1]
                    i += 2
                else:
                    flags[key] = ""
                    i += 1
            else:
                i += 1
        return flags

    # ==================================================================
    # 命令实现
    # ==================================================================

    def _cmd_help(self, args: List[str]) -> None:
        """显示所有命令"""
        self.io.print("可用命令:")
        self.io.print("  games                                - 列出所有配方文件")
        self.io.print("  use <文件名>                         - 选择配方文件")
        self.io.print("  game                                 - 显示当前配方文件")
        self.io.print("  calc <物品> <速度>                   - 计算生产链（主路径）")
        self.io.print("  alts <物品> <速度> <节点编号>        - 查看节点替代路径")
        self.io.print("  use-path <物品> <速度> <节点编号> <路径编号> - 切换到指定替代路径")
        self.io.print("  items                                - 列出所有物品")
        self.io.print("  recipes [页码] [搜索词]              - 列出配方")
        self.io.print("  recipe <名称>                        - 查看配方详情")
        self.io.print("  recipe add <名称> --device <设备> --inputs <列表> --outputs <列表>")
        self.io.print("  recipe set-device <名称> <设备>      - 修改设备")
        self.io.print("  recipe set-inputs <名称> <列表>      - 修改输入")
        self.io.print("  recipe set-outputs <名称> <列表>     - 修改输出")
        self.io.print("  recipe delete <名称>                 - 删除配方")
        self.io.print("  help                                 - 显示此帮助")
        self.io.print("  quit                                 - 退出")
        self.io.print("")
        self.io.print("速度支持表达式（如 15/min、8*3/2）")
        self.io.print("物品列表格式: 物品A:表达式,物品B:表达式（如 铁矿石:10,煤:5）")

    def _cmd_games(self, args: List[str]) -> None:
        """列出所有可用配方文件"""
        games = self.recipe_manager.get_available_games()
        if not games:
            self.io.print("没有找到配方文件")
            return
        self.io.print("可用配方文件:")
        for i, g in enumerate(games, 1):
            self.io.print(f"  {i}. {g}")

    def _cmd_use(self, args: List[str]) -> None:
        """选择配方文件（持久化到 config.yaml）"""
        if not args:
            self.io.print("用法: use <文件名>")
            return
        game_name = args[0]
        available = self.recipe_manager.get_available_games()
        if game_name not in available:
            self.io.print(
                f"配方文件 '{game_name}' 不存在。可用: "
                f"{', '.join(available) if available else '无'}"
            )
            return
        try:
            recipes = self.recipe_manager.load_recipe_file(game_name)
        except Exception as e:
            self.io.print(f"加载配方文件失败: {e}")
            return
        config_manager.set_last_game(game_name)
        self.io.print(f"已选择配方文件: {game_name}")
        self._print_recipe_list(recipes)

    def _cmd_game(self, args: List[str]) -> None:
        """显示当前配方文件（从 config.yaml 读取）"""
        game = config_manager.get_last_game()
        if game:
            self.io.print(f"当前配方文件: {game}")
        else:
            self.io.print("未选择配方文件（使用 'use <文件名>' 选择）")

    def _cmd_calc(self, args: List[str]) -> None:
        """计算生产链主路径（每次重新计算，不缓存）"""
        if len(args) < 2:
            self.io.print("用法: calc <物品> <速度>")
            return
        target_item = args[0]
        try:
            target_rate = self._parse_rate(args[1])
        except Exception as e:
            self.io.print(f"无效的速度表达式: {e}")
            return
        if target_rate <= 0:
            self.io.print("生产速度必须大于0")
            return

        ctx = self._require_game()
        if not ctx:
            return
        _, calc = ctx

        trees = calc.calculate_production_chain(target_item, target_rate)
        if not trees:
            self.io.print(f"未找到生产 {target_item} 的路径")
            return

        self.io.print(f"找到 {len(trees)} 条生产路径，显示主路径:")
        main_tree = trees[0]
        node_id_map = self._assign_node_ids(main_tree)
        self._display_chain(main_tree, node_id_map, target_item, target_rate, calc)

    def _cmd_alts(self, args: List[str]) -> None:
        """查看指定节点的替代路径（重新计算，不依赖前序命令）"""
        if len(args) < 3:
            self.io.print("用法: alts <物品> <速度> <节点编号>")
            return
        target_item = args[0]
        try:
            target_rate = self._parse_rate(args[1])
            node_id = int(args[2])
        except ValueError:
            self.io.print("节点编号必须是整数")
            return
        except Exception as e:
            self.io.print(f"无效参数: {e}")
            return

        ctx = self._require_game()
        if not ctx:
            return
        _, calc = ctx

        trees = calc.calculate_production_chain(target_item, target_rate)
        if not trees:
            self.io.print(f"未找到生产 {target_item} 的路径")
            return

        main_tree = trees[0]
        node_id_map = self._assign_node_ids(main_tree)
        if node_id not in node_id_map:
            self.io.print(f"节点 #{node_id} 不存在")
            return

        info = node_id_map[node_id]
        if info["alternative_count"] == 0:
            self.io.print(
                f"节点 #{node_id} ({info['item_name']}) 没有替代路径"
            )
            return

        self._show_alternative_paths(node_id, info, info["alternative_paths"])
        self.io.print(
            "使用 'use-path <物品> <速度> <节点编号> <路径编号>' 切换到指定路径"
        )

    def _cmd_use_path(self, args: List[str]) -> None:
        """切换到指定替代路径（重新计算并构建新树，不缓存）"""
        if len(args) < 4:
            self.io.print(
                "用法: use-path <物品> <速度> <节点编号> <路径编号>"
            )
            return
        target_item = args[0]
        try:
            target_rate = self._parse_rate(args[1])
            node_id = int(args[2])
            path_index = int(args[3]) - 1  # 用户输入 1-based
        except ValueError:
            self.io.print("节点编号和路径编号必须是整数")
            return
        except Exception as e:
            self.io.print(f"无效参数: {e}")
            return

        if path_index < 0:
            self.io.print("路径编号必须大于0")
            return

        ctx = self._require_game()
        if not ctx:
            return
        _, calc = ctx

        trees = calc.calculate_production_chain(target_item, target_rate)
        if not trees:
            self.io.print(f"未找到生产 {target_item} 的路径")
            return

        main_tree = trees[0]
        node_id_map = self._assign_node_ids(main_tree)
        if node_id not in node_id_map:
            self.io.print(f"节点 #{node_id} 不存在")
            return

        info = node_id_map[node_id]
        alt_paths = info["alternative_paths"]
        if not alt_paths:
            self.io.print(
                f"节点 #{node_id} ({info['item_name']}) 没有替代路径"
            )
            return
        if path_index >= len(alt_paths):
            self.io.print(f"路径编号超出范围，可用 1-{len(alt_paths)}")
            return

        selected = alt_paths[path_index]
        if not selected:
            self.io.print("选中的替代路径为空")
            return

        new_tree = self._build_tree_from_path(selected, target_rate)
        if not new_tree:
            self.io.print("路径切换失败")
            return

        old_device = info["device_count"]
        new_device = sum(n.get("device_count", 0) for n in selected)
        self.io.print(
            f"\n切换节点 #{node_id} ({info['item_name']}) 到路径 {path_index + 1}"
        )
        self.io.print(
            f"原设备数: {old_device:.2f} → 新设备数: {new_device:.2f}"
        )

        new_id_map = self._assign_node_ids(new_tree)
        self._display_chain(new_tree, new_id_map, target_item, target_rate, calc)

    def _cmd_items(self, args: List[str]) -> None:
        """列出所有物品"""
        ctx = self._require_game()
        if not ctx:
            return
        _, _ = ctx
        recipes = self.recipe_manager.get_all_recipes()
        items = set()
        for recipe in recipes.values():
            items.update(recipe.get("inputs", {}).keys())
            items.update(recipe.get("outputs", {}).keys())
        self.io.print("可用物品列表:")
        if not items:
            self.io.print("  没有物品")
            return
        for i, item in enumerate(sorted(items), 1):
            self.io.print(f"  {i}. {item}")

    def _cmd_recipes(self, args: List[str]) -> None:
        """列出配方（单次输出指定页，无分页循环）"""
        ctx = self._require_game()
        if not ctx:
            return
        _, _ = ctx
        recipes = self.recipe_manager.get_all_recipes()
        if not recipes:
            self.io.print("当前配方文件为空")
            return

        page = 1
        search = ""
        for a in args:
            if a.isdigit():
                page = int(a)
            else:
                search = a

        page_size = 10
        recipe_list = list(recipes.items())
        if search:
            recipe_list = [
                (name, r)
                for name, r in recipe_list
                if search.lower() in name.lower()
                or any(
                    search.lower() in i.lower()
                    for i in r.get("inputs", {})
                )
                or any(
                    search.lower() in i.lower()
                    for i in r.get("outputs", {})
                )
            ]

        total = len(recipe_list)
        total_pages = max(1, (total + page_size - 1) // page_size)
        if page < 1:
            page = 1
        if page > total_pages:
            page = total_pages
        start = (page - 1) * page_size
        end = min(start + page_size, total)

        header = f"配方列表 - 第 {page}/{total_pages} 页 (共 {total} 条)"
        if search:
            header += f" 搜索:'{search}'"
        self.io.print(header)

        for i, (name, r) in enumerate(recipe_list[start:end], start + 1):
            device = r.get("device", "未知设备")
            outputs = ", ".join(r.get("outputs", {}).keys())
            self.io.print(f"  [{i}] {name} ({device}) → {outputs}")
        if total_pages > 1:
            self.io.print("使用 'recipes <页码> [搜索词]' 查看其他页")

    def _cmd_recipe(self, args: List[str]) -> None:
        """配方管理子命令分发"""
        if not args:
            self.io.print(
                "用法: recipe <名称> | recipe add <名称> --device <设备> "
                "--inputs <列表> --outputs <列表> | "
                "recipe set-device <名称> <设备> | "
                "recipe set-inputs <名称> <列表> | "
                "recipe set-outputs <名称> <列表> | "
                "recipe delete <名称>"
            )
            return
        sub = args[0]
        rest = args[1:]
        if sub == "add":
            self._cmd_recipe_add(rest)
        elif sub == "set-device":
            self._cmd_recipe_set_device(rest)
        elif sub == "set-inputs":
            self._cmd_recipe_set_inputs(rest)
        elif sub == "set-outputs":
            self._cmd_recipe_set_outputs(rest)
        elif sub == "delete":
            self._cmd_recipe_delete(rest)
        elif sub == "show":
            if not rest:
                self.io.print("用法: recipe show <名称>")
                return
            self._cmd_recipe_show(rest)
        else:
            # 当作配方名查看详情
            self._cmd_recipe_show(args)

    def _cmd_recipe_show(self, args: List[str]) -> None:
        """查看配方详情"""
        name = " ".join(args)
        ctx = self._require_game()
        if not ctx:
            return
        _, _ = ctx
        recipes = self.recipe_manager.get_all_recipes()
        if name not in recipes:
            self.io.print(f"配方 '{name}' 不存在")
            return
        r = recipes[name]
        self.io.print(f"配方: {name}")
        self.io.print(f"设备: {r.get('device', '未知设备')}")
        self.io.print("输入:")
        inputs = r.get("inputs", {})
        if not inputs:
            self.io.print("  (无)")
        else:
            for n, d in inputs.items():
                amt = d.get("amount", 0) if isinstance(d, dict) else d
                self.io.print(f"  - {n}: {amt:.2f}/s")
        self.io.print("输出:")
        outputs = r.get("outputs", {})
        if not outputs:
            self.io.print("  (无)")
        else:
            for n, d in outputs.items():
                amt = d.get("amount", 0) if isinstance(d, dict) else d
                self.io.print(f"  - {n}: {amt:.2f}/s")

    def _cmd_recipe_add(self, args: List[str]) -> None:
        """添加配方（单步命令，参数完整传入）"""
        if not args:
            self.io.print(
                "用法: recipe add <名称> --device <设备> "
                "--inputs <列表> --outputs <列表>"
            )
            return
        name = args[0]
        flags = self._parse_flags(args[1:])
        device = flags.get("device", "未知设备")
        inputs_str = flags.get("inputs", "")
        outputs_str = flags.get("outputs", "")
        if not outputs_str:
            self.io.print("错误: 至少需要 --outputs <列表>")
            return
        try:
            inputs = self._parse_item_list(inputs_str) if inputs_str else {}
            outputs = self._parse_item_list(outputs_str)
        except Exception as e:
            self.io.print(f"解析物品列表失败: {e}")
            return

        ctx = self._require_game()
        if not ctx:
            return
        _, _ = ctx
        try:
            self.recipe_manager.add_recipe(name, device, inputs, outputs)
            self.io.print(f"成功添加配方: {name}")
        except ValueError as e:
            self.io.print(f"添加配方失败: {e}")

    def _cmd_recipe_set_device(self, args: List[str]) -> None:
        """修改配方的设备字段"""
        if len(args) < 2:
            self.io.print("用法: recipe set-device <名称> <设备>")
            return
        name, device = args[0], args[1]
        ctx = self._require_game()
        if not ctx:
            return
        _, _ = ctx
        recipes = self.recipe_manager.get_all_recipes()
        if name not in recipes:
            self.io.print(f"配方 '{name}' 不存在")
            return
        r = recipes[name]
        try:
            self.recipe_manager.update_recipe(
                name, device, r.get("inputs", {}), r.get("outputs", {})
            )
            self.io.print(f"已修改配方 {name} 的设备为 {device}")
        except Exception as e:
            self.io.print(f"修改失败: {e}")

    def _cmd_recipe_set_inputs(self, args: List[str]) -> None:
        """修改配方的输入字段"""
        if len(args) < 2:
            self.io.print("用法: recipe set-inputs <名称> <列表>")
            return
        name, inputs_str = args[0], args[1]
        try:
            inputs = self._parse_item_list(inputs_str)
        except Exception as e:
            self.io.print(f"解析物品列表失败: {e}")
            return
        ctx = self._require_game()
        if not ctx:
            return
        _, _ = ctx
        recipes = self.recipe_manager.get_all_recipes()
        if name not in recipes:
            self.io.print(f"配方 '{name}' 不存在")
            return
        r = recipes[name]
        try:
            self.recipe_manager.update_recipe(
                name, r.get("device", "未知设备"), inputs, r.get("outputs", {})
            )
            self.io.print(f"已修改配方 {name} 的输入")
        except Exception as e:
            self.io.print(f"修改失败: {e}")

    def _cmd_recipe_set_outputs(self, args: List[str]) -> None:
        """修改配方的输出字段"""
        if len(args) < 2:
            self.io.print("用法: recipe set-outputs <名称> <列表>")
            return
        name, outputs_str = args[0], args[1]
        try:
            outputs = self._parse_item_list(outputs_str)
        except Exception as e:
            self.io.print(f"解析物品列表失败: {e}")
            return
        ctx = self._require_game()
        if not ctx:
            return
        _, _ = ctx
        recipes = self.recipe_manager.get_all_recipes()
        if name not in recipes:
            self.io.print(f"配方 '{name}' 不存在")
            return
        r = recipes[name]
        try:
            self.recipe_manager.update_recipe(
                name, r.get("device", "未知设备"), r.get("inputs", {}), outputs
            )
            self.io.print(f"已修改配方 {name} 的输出")
        except Exception as e:
            self.io.print(f"修改失败: {e}")

    def _cmd_recipe_delete(self, args: List[str]) -> None:
        """删除配方"""
        if not args:
            self.io.print("用法: recipe delete <名称>")
            return
        name = args[0]
        ctx = self._require_game()
        if not ctx:
            return
        _, _ = ctx
        recipes = self.recipe_manager.get_all_recipes()
        if name not in recipes:
            self.io.print(f"配方 '{name}' 不存在")
            return
        try:
            self.recipe_manager.delete_recipe(name)
            self.io.print(f"已删除配方: {name}")
        except Exception as e:
            self.io.print(f"删除失败: {e}")

    # ==================================================================
    # 纯输出/转换辅助方法（无状态，参数化）
    # ==================================================================

    def _print_recipe_list(self, recipes: Dict[str, Any]) -> None:
        """打印配方文件中的配方列表"""
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
        node_counter: Optional[List[int]] = None,
    ) -> None:
        """
        以树形结构打印合成树，节点带前序遍历编号和替代路径标记

        编号与 _assign_node_ids 一致（前序遍历：根=1，子节点递增）
        """
        if prefixes is None:
            prefixes = []
        if node_counter is None:
            node_counter = [0]

        current_prefix = "".join(prefixes)
        if indent > 0:
            current_prefix += "└─" if is_last else "├─"

        item_name = tree_dict["item_name"]
        amount = tree_dict["amount"]
        device_count = tree_dict["device_count"]
        path_info = tree_dict.get("path_info", {})
        alternative_count = path_info.get("alternative_count", 0)

        node_counter[0] += 1
        current_node_index = node_counter[0]
        marker = f" [+{alternative_count}]" if alternative_count > 0 else ""
        self.io.print(
            f"{current_prefix}#{current_node_index} {item_name}: {amount:.2f}/s{marker}"
        )

        if device_count > 0:
            device_info_prefix = "".join(prefixes)
            if indent > 0:
                device_info_prefix += "  " if is_last else "│ "
            self.io.print(f"{device_info_prefix}│设备数: {device_count:.2f}")
            if tree_dict.get("recipe"):
                device = tree_dict["recipe"].get("device", "未知设备")
                self.io.print(f"{device_info_prefix}│设备: {device}")

        children = tree_dict.get("children", [])
        for i, child in enumerate(children):
            child_is_last = i == len(children) - 1
            child_prefixes = prefixes.copy()
            if indent > 0:
                child_prefixes.append("  " if is_last else "│ ")
            self._print_tree(
                child, indent + 1, child_is_last, child_prefixes, node_counter
            )

    def _print_raw_materials(self, raw_materials: Dict[str, float]) -> None:
        """打印基础原料消耗"""
        self.io.print("\n基础原料消耗:")
        self.io.print("-" * 50)
        if not raw_materials:
            self.io.print("无基础原料消耗")
        else:
            for item, amount in raw_materials.items():
                self.io.print(f"{item}: {amount:.2f}/s")
        self.io.print("-" * 50)

    def _print_device_stats(self, device_stats: Dict[str, float]) -> None:
        """打印设备统计"""
        self.io.print("\n设备统计:")
        self.io.print("-" * 50)
        if not device_stats:
            self.io.print("无设备使用")
        else:
            for device, count in device_stats.items():
                self.io.print(f"{device}: {count:.2f} 台")
        self.io.print("-" * 50)

    def _dict_to_node(
        self, tree_dict: Dict[str, Any], parent: Optional[CraftingNode] = None
    ) -> CraftingNode:
        """将字典转换为节点对象"""
        node = CraftingNode(tree_dict["item_name"], tree_dict["amount"])
        node.device_count = tree_dict["device_count"]
        node.recipe = tree_dict.get("recipe", {})
        node.parent = parent
        for child_dict in tree_dict.get("children", []):
            child_node = self._dict_to_node(child_dict, node)
            node.children.append(child_node)
            node.inputs[child_node.item_name] = child_node.amount
        return node

    def _assign_node_ids(
        self, tree_dict: Dict[str, Any]
    ) -> Dict[int, Dict[str, Any]]:
        """
        为树中的每个节点分配前序遍历编号（局部变量，不写实例字段）

        编号规则：根节点为1，前序遍历依次为2,3,4...
        """
        node_id_map: Dict[int, Dict[str, Any]] = {}
        counter = [1]

        def traverse(node: Dict[str, Any]) -> None:
            node_id = counter[0]
            counter[0] += 1
            node_id_map[node_id] = {
                "node": node,
                "item_name": node["item_name"],
                "amount": node["amount"],
                "device_count": node["device_count"],
                "alternative_count": node.get("path_info", {}).get(
                    "alternative_count", 0
                ),
                "alternative_paths": node.get("alternative_paths", []),
                "children": node.get("children", []),
            }
            for child in node.get("children", []):
                traverse(child)

        traverse(tree_dict)
        return node_id_map

    def _display_chain(
        self,
        tree: Dict[str, Any],
        node_id_map: Dict[int, Dict[str, Any]],
        target_item: str,
        target_rate: float,
        calc: CraftingCalculator,
    ) -> None:
        """显示完整生产链（主路径 + 基础原料 + 设备统计 + 替代路径节点列表）"""
        self.io.print("\n" + "=" * 60)
        self.io.print(f"生产链: {target_item} ({target_rate:.2f}/s)")
        self.io.print("=" * 60)
        self._print_tree(tree)

        tree_node = self._dict_to_node(tree)
        raw_materials = calc.get_raw_materials(tree_node)
        device_stats = calc.get_device_stats(tree_node)
        self._print_raw_materials(raw_materials)
        self._print_device_stats(device_stats)

        alt_nodes = [
            (nid, info)
            for nid, info in node_id_map.items()
            if info["alternative_count"] > 0
        ]
        if alt_nodes:
            self.io.print("\n带替代路径的节点:")
            for nid, info in alt_nodes:
                self.io.print(
                    f"  [#{nid}] {info['item_name']} [+{info['alternative_count']}]"
                )
            self.io.print(
                "使用 'alts <物品> <速度> <节点编号>' 查看替代路径"
            )

    def _show_alternative_paths(
        self,
        node_id: int,
        node_info: Dict[str, Any],
        alternative_paths: List[List[Dict[str, Any]]],
    ) -> None:
        """显示指定节点的替代路径列表"""
        self.io.print(
            f"\n节点 #{node_id} ({node_info['item_name']}) 的可选路径:"
        )
        self.io.print("=" * 60)
        current_device_count = node_info["device_count"]
        for i, alt_path in enumerate(alternative_paths, 1):
            if not alt_path:
                continue
            alt_device_count = sum(
                node.get("device_count", 0) for node in alt_path
            )
            device_diff = alt_device_count - current_device_count
            if device_diff > 0:
                diff_str = f"(+{device_diff:.2f})"
            elif device_diff < 0:
                diff_str = f"({device_diff:.2f})"
            else:
                diff_str = "(相同)"
            self.io.print(f"\n  路径 {i}:")
            self.io.print(f"    设备总数: {alt_device_count:.2f} {diff_str}")
            path_items = " → ".join(
                f"{node.get('item_name', '未知')}"
                f"({node.get('device_count', 0):.1f})"
                for node in alt_path[:5]
            )
            if len(alt_path) > 5:
                path_items += f" ... ({len(alt_path) - 5} 更多)"
            self.io.print(f"    路径: {path_items}")
        self.io.print("=" * 60)

    def _build_tree_from_path(
        self, path: List[Dict[str, Any]], target_rate: float
    ) -> Optional[Dict[str, Any]]:
        """从路径构建树结构（简化版本，保持原有实现）"""
        if not path:
            return None
        root = path[0].copy()
        root["children"] = []
        for node in path[1:]:
            child = node.copy()
            child["children"] = []
            root["children"].append(child)
        return root

    def _check_has_alternatives(self, tree_dict: Dict[str, Any]) -> bool:
        """检查树中是否有节点存在替代路径"""
        path_info = tree_dict.get("path_info", {})
        if path_info.get("alternative_count", 0) > 0:
            return True
        for child in tree_dict.get("children", []):
            if self._check_has_alternatives(child):
                return True
        return False

    def _validate_expression(self, expression: str) -> bool:
        """验证表达式格式是否正确"""
        try:
            parse_expression(expression)
            return True
        except Exception:
            return False

    def _generate_recipe_id(
        self, outputs: Dict[str, Any], existing_recipes: Dict[str, Any]
    ) -> str:
        """根据输出物品生成配方标识符"""
        if not outputs:
            return "未知配方"
        max_amount = 0
        main_output = ""
        for item_name, item_data in outputs.items():
            amount = item_data.get("amount", 0) if isinstance(item_data, dict) else 0
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


__all__ = ["ApplicationController"]
