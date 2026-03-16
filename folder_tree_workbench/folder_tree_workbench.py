#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
个人工作台（Folder Tree Workbench）

一个可扩展、轻量、默认安全的本地工作台：
1. 扫描文件夹并在 UI 中预览节点树。
2. 双击节点打开对应文件/文件夹。
3. 右键收藏节点，收藏后可快速载入子树。
4. 导出为 XMind 可导入的 Markdown 结构。
5. 根据 XMind/Markdown 结构，在目标目录“生长”出新的文件夹系统。

设计原则：
- 单文件、标准库、无第三方依赖
- 默认安全：只读浏览；创建结构时只创建不删除不覆盖
- 为后续扩展预留分层：数据层 / 解析层 / UI 层 / 收藏层
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import subprocess
import sys
import traceback
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
except Exception:  # pragma: no cover
    tk = None
    filedialog = None
    messagebox = None
    ttk = None

APP_NAME = "个人工作台"
APP_VERSION = "2.0.0"
APP_SUBTITLE = "文件树梳理 · XMind Markdown · 收藏节点 · 安全生长"
DEFAULT_ENCODING = "utf-8"
INVALID_CHARS_WIN = set('<>:"\\|?*')
RESERVED_NAMES_WIN = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}
FAVORITES_DIR = Path.home() / ".folder_tree_workbench"
FAVORITES_FILE = FAVORITES_DIR / "favorites.json"
SETTINGS_FILE = FAVORITES_DIR / "settings.json"


# -----------------------------
# Data models
# -----------------------------
@dataclass
class FsNode:
    name: str
    path: Path
    is_dir: bool
    children: List["FsNode"] = field(default_factory=list)


@dataclass
class NodeSpec:
    name: str
    is_dir: bool
    level: int


@dataclass
class BuildStats:
    created_dirs: int = 0
    existing_dirs: int = 0
    created_files: int = 0
    existing_files: int = 0
    skipped_nodes: int = 0


@dataclass
class Favorite:
    name: str
    path: str
    is_dir: bool
    note: str = ""
    created_at: str = ""


class TreeFormatError(ValueError):
    pass


# -----------------------------
# Utility functions
# -----------------------------
def now_text() -> str:
    return _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def normalize_path(p: str | Path) -> Path:
    return Path(p).expanduser().resolve()


def is_hidden(path: Path) -> bool:
    return path.name.startswith(".")


def validate_node_name(name: str) -> Tuple[bool, str]:
    stripped = name.strip().rstrip("/")
    if not stripped:
        return False, "名称为空"
    if stripped in {".", ".."}:
        return False, "名称不能为 . 或 .."
    if any(sep in stripped for sep in ["/", "\\"]):
        return False, "名称中不能包含路径分隔符"
    if os.name == "nt":
        if any(ch in INVALID_CHARS_WIN for ch in stripped):
            return False, f"名称包含 Windows 非法字符: {stripped}"
        if stripped.upper() in RESERVED_NAMES_WIN:
            return False, f"名称是 Windows 保留字: {stripped}"
        if stripped.endswith(" ") or stripped.endswith("."):
            return False, "Windows 下名称不能以空格或句点结尾"
    return True, ""


def safe_display_name(path: Path, is_dir: bool) -> str:
    return path.name + ("/" if is_dir else "")


def open_path(path: Path) -> None:
    path = normalize_path(path)
    if not path.exists():
        raise FileNotFoundError(f"路径不存在：{path}")

    if sys.platform.startswith("win"):
        os.startfile(str(path))  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.run(["open", str(path)], check=False)
    else:
        subprocess.run(["xdg-open", str(path)], check=False)


def open_parent(path: Path) -> None:
    path = normalize_path(path)
    target = path if path.is_dir() else path.parent
    open_path(target)


def ensure_storage() -> None:
    FAVORITES_DIR.mkdir(parents=True, exist_ok=True)


# -----------------------------
# File scanning
# -----------------------------
def iter_children_sorted(root: Path, include_hidden: bool) -> Iterable[Path]:
    try:
        children = list(root.iterdir())
    except (PermissionError, OSError):
        return []
    if not include_hidden:
        children = [p for p in children if not is_hidden(p)]
    children.sort(key=lambda p: (not p.is_dir(), p.name.lower()))
    return children


def scan_fs_tree(
    root: Path,
    include_files: bool = True,
    include_hidden: bool = False,
    max_depth: Optional[int] = None,
) -> FsNode:
    root = normalize_path(root)
    if not root.exists():
        raise FileNotFoundError(f"路径不存在：{root}")
    if not root.is_dir():
        raise NotADirectoryError(f"不是文件夹：{root}")

    def walk(current: Path, depth: int) -> FsNode:
        node = FsNode(name=current.name, path=current, is_dir=True)
        if max_depth is not None and depth >= max_depth:
            return node
        for child in iter_children_sorted(current, include_hidden):
            try:
                is_dir = child.is_dir()
            except OSError:
                is_dir = False
            if child.is_symlink():
                continue
            if is_dir:
                node.children.append(walk(child, depth + 1))
            elif include_files:
                node.children.append(FsNode(name=child.name, path=child, is_dir=False))
        return node

    return walk(root, 0)


def flatten_fs_tree(root: FsNode) -> List[FsNode]:
    items: List[FsNode] = []

    def walk(node: FsNode) -> None:
        items.append(node)
        for child in node.children:
            walk(child)

    walk(root)
    return items


# -----------------------------
# XMind-compatible Markdown export
# -----------------------------
def fs_tree_to_xmind_lines(root: FsNode) -> List[str]:
    """
    导出规则：
    - 第一行始终是 # 根节点
    - 根节点的直接子节点使用 ##
    - 更深层使用无序列表缩进

    这样既符合 XMind 官方导入规则，也比纯列表结构更清晰。
    """
    lines: List[str] = [f"# {safe_display_name(root.path, True)}"]

    def write_bullets(nodes: List[FsNode], indent: int) -> None:
        prefix = "  " * indent + "- "
        for node in nodes:
            lines.append(prefix + safe_display_name(node.path, node.is_dir))
            if node.is_dir and node.children:
                write_bullets(node.children, indent + 1)

    for child in root.children:
        lines.append(f"## {safe_display_name(child.path, child.is_dir)}")
        if child.is_dir and child.children:
            write_bullets(child.children, 0)
    return lines


def export_tree_to_xmind_markdown(
    source_dir: Path,
    output_md: Path,
    include_files: bool = True,
    include_hidden: bool = False,
    max_depth: Optional[int] = None,
) -> None:
    tree = scan_fs_tree(
        root=source_dir,
        include_files=include_files,
        include_hidden=include_hidden,
        max_depth=max_depth,
    )
    output_md = normalize_path(output_md)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text("\n".join(fs_tree_to_xmind_lines(tree)) + "\n", encoding=DEFAULT_ENCODING)


# -----------------------------
# XMind-compatible Markdown parser
# -----------------------------
_heading_re = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_bullet_re = re.compile(r"^([ \t]*)([-*+])\s+(.+?)\s*$")


def _normalize_md_name(raw: str) -> Tuple[str, bool]:
    name = raw.strip()
    is_dir = name.endswith("/")
    if is_dir:
        name = name[:-1]
    ok, reason = validate_node_name(name)
    if not ok:
        raise TreeFormatError(f"名称非法：{name}；原因：{reason}")
    return name, is_dir


def parse_xmind_markdown(md_text: str) -> List[NodeSpec]:
    lines = [line.rstrip("\n") for line in md_text.splitlines() if line.strip()]
    if not lines:
        raise TreeFormatError("Markdown 为空。")

    nodes: List[NodeSpec] = []
    current_heading_level = 0
    indent_unit: Optional[int] = None

    for idx, raw in enumerate(lines, start=1):
        head = _heading_re.match(raw)
        if head:
            hashes, body = head.groups()
            level = len(hashes) - 1
            name, is_dir = _normalize_md_name(body)
            nodes.append(NodeSpec(name=name, is_dir=is_dir, level=level))
            current_heading_level = level
            continue

        bullet = _bullet_re.match(raw)
        if bullet:
            indent_str, _marker, body = bullet.groups()
            spaces = 0
            for ch in indent_str:
                spaces += 2 if ch == "\t" else 1
            if spaces > 0:
                if indent_unit is None:
                    indent_unit = spaces
                    if indent_unit <= 0:
                        raise TreeFormatError("无效的缩进宽度。")
                if spaces % indent_unit != 0:
                    raise TreeFormatError(f"第 {idx} 行缩进不一致：{raw}")
                indent_depth = spaces // indent_unit
            else:
                indent_depth = 0
            name, is_dir = _normalize_md_name(body)
            level = current_heading_level + 1 + indent_depth
            nodes.append(NodeSpec(name=name, is_dir=is_dir, level=level))
            continue

        raise TreeFormatError(f"第 {idx} 行不是支持的 XMind Markdown 结构：{raw}")

    if not nodes:
        raise TreeFormatError("未找到任何节点。")
    if nodes[0].level != 0:
        raise TreeFormatError("Markdown 必须以 # 根节点开头。")

    prev = 0
    for i, node in enumerate(nodes[1:], start=2):
        if node.level > prev + 1:
            raise TreeFormatError(f"第 {i} 行层级跳跃过大：{node.name}")
        prev = node.level

    return nodes


def read_xmind_markdown(path: Path) -> List[NodeSpec]:
    path = normalize_path(path)
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Markdown 文件不存在：{path}")
    return parse_xmind_markdown(path.read_text(encoding=DEFAULT_ENCODING))


# -----------------------------
# Build structure from Markdown
# -----------------------------
def preview_build_from_nodes(nodes: Sequence[NodeSpec], target_root: Path, create_files: bool = False) -> List[str]:
    target_root = normalize_path(target_root)
    planned: List[str] = []
    stack: List[Path] = []

    for node in nodes:
        while len(stack) > node.level:
            stack.pop()
        if node.level == 0:
            dest = target_root / node.name
            stack = [dest]
        else:
            if not stack:
                raise TreeFormatError("层级结构错误，未找到父节点。")
            parent = stack[-1]
            dest = parent / node.name
            if len(stack) == node.level:
                stack.append(dest)
            else:
                stack[node.level] = dest
                stack[:] = stack[: node.level + 1]

        if node.is_dir or create_files:
            planned.append(str(dest) + ("/" if node.is_dir else ""))

    return planned


def create_structure_from_nodes(
    nodes: Sequence[NodeSpec],
    target_root: Path,
    create_files: bool = False,
) -> BuildStats:
    target_root = normalize_path(target_root)
    target_root.mkdir(parents=True, exist_ok=True)
    stats = BuildStats()
    stack: List[Path] = []

    for node in nodes:
        while len(stack) > node.level:
            stack.pop()
        if node.level == 0:
            dest = target_root / node.name
            stack = [dest]
        else:
            if not stack:
                raise TreeFormatError("层级结构错误，未找到父节点。")
            parent = stack[-1]
            dest = parent / node.name
            if len(stack) == node.level:
                stack.append(dest)
            else:
                stack[node.level] = dest
                stack[:] = stack[: node.level + 1]

        if node.is_dir:
            if dest.exists():
                if dest.is_dir():
                    stats.existing_dirs += 1
                else:
                    stats.skipped_nodes += 1
                continue
            dest.mkdir(parents=True, exist_ok=True)
            stats.created_dirs += 1
        else:
            if not create_files:
                stats.skipped_nodes += 1
                continue
            if dest.exists():
                if dest.is_file():
                    stats.existing_files += 1
                else:
                    stats.skipped_nodes += 1
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.touch(exist_ok=False)
            stats.created_files += 1
    return stats


def build_tree_from_nodes(nodes: Sequence[NodeSpec], fake_root_path: Optional[Path] = None) -> FsNode:
    if not nodes:
        raise TreeFormatError("节点为空。")
    root_path = fake_root_path or Path(nodes[0].name)
    root = FsNode(name=nodes[0].name, path=root_path, is_dir=nodes[0].is_dir)
    stack: List[FsNode] = [root]

    for node in nodes[1:]:
        while len(stack) > node.level:
            stack.pop()
        parent = stack[-1]
        child_path = parent.path / node.name
        child = FsNode(name=node.name, path=child_path, is_dir=node.is_dir)
        parent.children.append(child)
        if node.is_dir:
            if len(stack) == node.level:
                stack.append(child)
            else:
                if len(stack) > node.level:
                    stack[node.level] = child
                    stack[:] = stack[: node.level + 1]
                else:
                    stack.append(child)
    return root


# -----------------------------
# Favorites persistence
# -----------------------------
class FavoritesStore:
    def __init__(self, file_path: Path = FAVORITES_FILE):
        self.file_path = file_path
        ensure_storage()

    def load(self) -> List[Favorite]:
        if not self.file_path.exists():
            return []
        try:
            raw = json.loads(self.file_path.read_text(encoding=DEFAULT_ENCODING))
            result = []
            for item in raw:
                result.append(Favorite(**item))
            return result
        except Exception:
            return []

    def save(self, favorites: List[Favorite]) -> None:
        ensure_storage()
        self.file_path.write_text(
            json.dumps([asdict(x) for x in favorites], ensure_ascii=False, indent=2),
            encoding=DEFAULT_ENCODING,
        )


class SettingsStore:
    def __init__(self, file_path: Path = SETTINGS_FILE):
        self.file_path = file_path
        ensure_storage()

    def load(self) -> Dict[str, str]:
        if not self.file_path.exists():
            return {}
        try:
            return json.loads(self.file_path.read_text(encoding=DEFAULT_ENCODING))
        except Exception:
            return {}

    def save(self, data: Dict[str, str]) -> None:
        ensure_storage()
        self.file_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding=DEFAULT_ENCODING)


# -----------------------------
# GUI application
# -----------------------------
class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"{APP_NAME} v{APP_VERSION}")
        self.root.geometry("1420x880")
        self.root.minsize(1180, 760)

        self.favorites_store = FavoritesStore()
        self.settings_store = SettingsStore()
        self.favorites: List[Favorite] = self.favorites_store.load()
        self.settings = self.settings_store.load()

        self.current_root: Optional[Path] = None
        self.current_tree: Optional[FsNode] = None
        self.current_index: List[FsNode] = []
        self.current_item_paths: Dict[str, Path] = {}
        self.search_matches: List[str] = []
        self.search_cursor: int = -1

        self.md_preview_nodes: List[NodeSpec] = []
        self.md_item_paths: Dict[str, Path] = {}

        self.workspace_root_var = tk.StringVar(value=self.settings.get("last_root", ""))
        self.search_var = tk.StringVar()
        self.status_var = tk.StringVar(value="就绪")
        self.export_source_var = tk.StringVar(value=self.settings.get("last_root", ""))
        self.export_output_var = tk.StringVar()
        self.include_files_var = tk.BooleanVar(value=True)
        self.include_hidden_var = tk.BooleanVar(value=False)
        self.max_depth_var = tk.StringVar(value="")
        self.md_file_var = tk.StringVar()
        self.target_root_var = tk.StringVar()
        self.create_files_var = tk.BooleanVar(value=False)

        self._apply_theme()
        self._build_ui()
        self._load_favorites_to_ui()
        self._bind_events()

    # ---------- theme ----------
    def _apply_theme(self) -> None:
        style = ttk.Style()
        try:
            if "clam" in style.theme_names():
                style.theme_use("clam")
        except Exception:
            pass

        bg = "#0f172a"
        panel = "#111827"
        panel2 = "#1f2937"
        surface = "#f8fafc"
        muted = "#cbd5e1"
        text = "#e5e7eb"
        accent = "#3b82f6"
        accent2 = "#2563eb"
        success = "#10b981"

        self.colors = {
            "bg": bg,
            "panel": panel,
            "panel2": panel2,
            "surface": surface,
            "muted": muted,
            "text": text,
            "accent": accent,
            "accent2": accent2,
            "success": success,
        }

        self.root.configure(bg=bg)
        default_font = ("Microsoft YaHei UI", 10)
        heading_font = ("Microsoft YaHei UI", 11, "bold")
        title_font = ("Microsoft YaHei UI", 18, "bold")
        small_font = ("Microsoft YaHei UI", 9)
        mono_font = ("Consolas", 10)

        style.configure("Root.TFrame", background=bg)
        style.configure("Sidebar.TFrame", background=panel)
        style.configure("Panel.TFrame", background=panel2)
        style.configure("Content.TFrame", background=surface)
        style.configure("Header.TFrame", background=bg)
        style.configure("HeaderTitle.TLabel", background=bg, foreground="white", font=title_font)
        style.configure("HeaderSub.TLabel", background=bg, foreground=muted, font=default_font)
        style.configure("SidebarTitle.TLabel", background=panel, foreground="white", font=heading_font)
        style.configure("SidebarSub.TLabel", background=panel, foreground=muted, font=small_font)
        style.configure("CardTitle.TLabel", background=surface, foreground="#0f172a", font=heading_font)
        style.configure("Text.TLabel", background=surface, foreground="#0f172a", font=default_font)
        style.configure("Muted.TLabel", background=surface, foreground="#64748b", font=small_font)
        style.configure("Status.TLabel", background=panel, foreground=muted, font=small_font)
        style.configure("TNotebook", background=surface, borderwidth=0)
        style.configure("TNotebook.Tab", padding=(16, 8), font=default_font)
        style.map("TNotebook.Tab", background=[("selected", "#e2e8f0")], foreground=[("selected", "#0f172a")])
        style.configure("TButton", font=default_font, padding=(10, 6))
        style.configure("Accent.TButton", font=default_font, padding=(12, 8), background=accent, foreground="white")
        style.map("Accent.TButton", background=[("active", accent2), ("pressed", accent2)], foreground=[("active", "white")])
        style.configure("Treeview", font=default_font, rowheight=28)
        style.configure("Treeview.Heading", font=heading_font)
        style.configure("TLabelframe", background=surface)
        style.configure("TLabelframe.Label", background=surface, foreground="#0f172a", font=heading_font)
        style.configure("TCheckbutton", background=surface, foreground="#0f172a", font=default_font)
        style.configure("TEntry", font=default_font)
        self.fonts = {"mono": mono_font}

    # ---------- layout ----------
    def _build_ui(self) -> None:
        main = ttk.Frame(self.root, style="Root.TFrame")
        main.pack(fill="both", expand=True)

        self._build_header(main)

        body = ttk.Frame(main, style="Root.TFrame")
        body.pack(fill="both", expand=True, padx=14, pady=(0, 14))

        paned = ttk.Panedwindow(body, orient="horizontal")
        paned.pack(fill="both", expand=True)

        sidebar = ttk.Frame(paned, style="Sidebar.TFrame", width=290)
        content = ttk.Frame(paned, style="Content.TFrame")
        paned.add(sidebar, weight=0)
        paned.add(content, weight=1)

        self._build_sidebar(sidebar)
        self._build_content(content)
        self._build_statusbar(main)

    def _build_header(self, parent: ttk.Frame) -> None:
        header = ttk.Frame(parent, style="Header.TFrame")
        header.pack(fill="x", padx=14, pady=(14, 10))
        ttk.Label(header, text=APP_NAME, style="HeaderTitle.TLabel").pack(anchor="w")
        ttk.Label(header, text=APP_SUBTITLE, style="HeaderSub.TLabel").pack(anchor="w", pady=(2, 0))

    def _build_sidebar(self, parent: ttk.Frame) -> None:
        parent.pack_propagate(False)
        top = ttk.Frame(parent, style="Sidebar.TFrame")
        top.pack(fill="both", expand=True, padx=14, pady=14)

        ttk.Label(top, text="收藏节点", style="SidebarTitle.TLabel").pack(anchor="w")
        ttk.Label(top, text="双击收藏可直接载入子树；如果是文件，会打开文件并定位其父目录。", style="SidebarSub.TLabel", wraplength=240).pack(anchor="w", pady=(4, 10))

        fav_frame = ttk.Frame(top, style="Sidebar.TFrame")
        fav_frame.pack(fill="both", expand=True)

        self.favorites_list = tk.Listbox(
            fav_frame,
            bg="#0b1220",
            fg="#e5e7eb",
            selectbackground="#2563eb",
            selectforeground="white",
            relief="flat",
            highlightthickness=0,
            font=("Microsoft YaHei UI", 10),
        )
        self.favorites_list.pack(side="left", fill="both", expand=True)
        fav_scroll = ttk.Scrollbar(fav_frame, orient="vertical", command=self.favorites_list.yview)
        fav_scroll.pack(side="right", fill="y")
        self.favorites_list.configure(yscrollcommand=fav_scroll.set)

        btns = ttk.Frame(top, style="Sidebar.TFrame")
        btns.pack(fill="x", pady=(10, 0))
        ttk.Button(btns, text="打开并载入", command=self.open_selected_favorite).pack(fill="x", pady=4)
        ttk.Button(btns, text="从收藏中移除", command=self.remove_selected_favorite).pack(fill="x", pady=4)
        ttk.Button(btns, text="打开收藏路径", command=self.open_favorite_only).pack(fill="x", pady=4)

        tip = tk.Text(
            top,
            height=8,
            bg="#0b1220",
            fg="#cbd5e1",
            relief="flat",
            highlightthickness=0,
            wrap="word",
            font=("Microsoft YaHei UI", 9),
        )
        tip.pack(fill="x", pady=(12, 0))
        tip.insert(
            "1.0",
            "推荐工作流：\n"
            "1）先载入共享盘或个人工作区节点。\n"
            "2）在中间预览树中右键收藏常用深层路径。\n"
            "3）导出为 XMind Markdown，在 XMind 中重新梳理。\n"
            "4）再从 Markdown 生长新的目录体系。\n"
            "5）整个过程默认只读，不会误删原文件。"
        )
        tip.configure(state="disabled")

    def _build_content(self, parent: ttk.Frame) -> None:
        notebook = ttk.Notebook(parent)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.workspace_tab = ttk.Frame(notebook, style="Content.TFrame")
        self.export_tab = ttk.Frame(notebook, style="Content.TFrame")
        self.build_tab = ttk.Frame(notebook, style="Content.TFrame")
        self.help_tab = ttk.Frame(notebook, style="Content.TFrame")
        notebook.add(self.workspace_tab, text="工作台")
        notebook.add(self.export_tab, text="导出 XMind Markdown")
        notebook.add(self.build_tab, text="从 Markdown 生长")
        notebook.add(self.help_tab, text="说明")

        self._build_workspace_tab(self.workspace_tab)
        self._build_export_tab(self.export_tab)
        self._build_build_tab(self.build_tab)
        self._build_help_tab(self.help_tab)

    def _build_statusbar(self, parent: ttk.Frame) -> None:
        bar = ttk.Frame(parent, style="Sidebar.TFrame")
        bar.pack(fill="x", padx=14, pady=(0, 12))
        ttk.Label(bar, textvariable=self.status_var, style="Status.TLabel").pack(anchor="w", padx=10, pady=8)

    def _build_workspace_tab(self, parent: ttk.Frame) -> None:
        frm = ttk.Frame(parent, style="Content.TFrame")
        frm.pack(fill="both", expand=True, padx=14, pady=14)
        frm.columnconfigure(1, weight=1)
        frm.rowconfigure(3, weight=1)

        ttk.Label(frm, text="当前工作根目录", style="CardTitle.TLabel").grid(row=0, column=0, sticky="w")
        path_row = ttk.Frame(frm, style="Content.TFrame")
        path_row.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(8, 10))
        path_row.columnconfigure(0, weight=1)
        ttk.Entry(path_row, textvariable=self.workspace_root_var).grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ttk.Button(path_row, text="浏览", command=self.pick_workspace_root).grid(row=0, column=1, padx=4)
        ttk.Button(path_row, text="读取结构", style="Accent.TButton", command=self.load_workspace_tree).grid(row=0, column=2, padx=4)
        ttk.Button(path_row, text="打开当前根目录", command=self.open_current_root).grid(row=0, column=3, padx=4)
        ttk.Button(path_row, text="刷新", command=self.reload_current_tree).grid(row=0, column=4, padx=4)

        search_row = ttk.Frame(frm, style="Content.TFrame")
        search_row.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(0, 10))
        search_row.columnconfigure(1, weight=1)
        ttk.Label(search_row, text="快速定位", style="Text.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 8))
        search_entry = ttk.Entry(search_row, textvariable=self.search_var)
        search_entry.grid(row=0, column=1, sticky="ew")
        ttk.Button(search_row, text="查找", command=self.search_in_current_tree).grid(row=0, column=2, padx=4)
        ttk.Button(search_row, text="下一个", command=self.goto_next_match).grid(row=0, column=3, padx=4)
        ttk.Button(search_row, text="上一个", command=self.goto_prev_match).grid(row=0, column=4, padx=4)

        tree_frame = ttk.Frame(frm, style="Content.TFrame")
        tree_frame.grid(row=3, column=0, columnspan=3, sticky="nsew")
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        columns = ("type", "path")
        self.workspace_tree = ttk.Treeview(tree_frame, columns=columns, show="tree headings")
        self.workspace_tree.heading("#0", text="名称")
        self.workspace_tree.heading("type", text="类型")
        self.workspace_tree.heading("path", text="完整路径")
        self.workspace_tree.column("#0", width=320, anchor="w")
        self.workspace_tree.column("type", width=90, anchor="center")
        self.workspace_tree.column("path", width=700, anchor="w")
        self.workspace_tree.grid(row=0, column=0, sticky="nsew")
        yscroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.workspace_tree.yview)
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.workspace_tree.xview)
        xscroll.grid(row=1, column=0, sticky="ew")
        self.workspace_tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)

        detail = tk.Text(frm, height=5, wrap="word", relief="flat", highlightthickness=1, bd=0, font=("Microsoft YaHei UI", 9))
        detail.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(10, 0))
        detail.insert("1.0", "节点详情会显示在这里。双击节点可直接打开，右键节点可收藏。")
        detail.configure(state="disabled")
        self.workspace_detail = detail

        self.workspace_menu = tk.Menu(self.root, tearoff=0)
        self.workspace_menu.add_command(label="打开节点", command=self.menu_open_selected_tree_path)
        self.workspace_menu.add_command(label="打开所在位置", command=self.menu_open_selected_parent)
        self.workspace_menu.add_separator()
        self.workspace_menu.add_command(label="收藏该节点", command=self.menu_favorite_selected_node)

    def _build_export_tab(self, parent: ttk.Frame) -> None:
        frm = ttk.Frame(parent, style="Content.TFrame")
        frm.pack(fill="both", expand=True, padx=14, pady=14)
        frm.columnconfigure(1, weight=1)
        frm.rowconfigure(5, weight=1)

        ttk.Label(frm, text="从现有文件夹导出为 XMind 可导入 Markdown", style="CardTitle.TLabel").grid(row=0, column=0, columnspan=3, sticky="w")
        ttk.Label(frm, text="导出的文件将以 # 根节点开头，符合 XMind 桌面版 Markdown 导入要求。", style="Muted.TLabel").grid(row=1, column=0, columnspan=3, sticky="w", pady=(4, 12))

        ttk.Label(frm, text="源文件夹", style="Text.TLabel").grid(row=2, column=0, sticky="w", pady=6)
        ttk.Entry(frm, textvariable=self.export_source_var).grid(row=2, column=1, sticky="ew", pady=6)
        ttk.Button(frm, text="浏览", command=self.pick_export_source).grid(row=2, column=2, padx=6)

        ttk.Label(frm, text="输出 Markdown 文件", style="Text.TLabel").grid(row=3, column=0, sticky="w", pady=6)
        ttk.Entry(frm, textvariable=self.export_output_var).grid(row=3, column=1, sticky="ew", pady=6)
        ttk.Button(frm, text="保存到", command=self.pick_export_output).grid(row=3, column=2, padx=6)

        opts = ttk.LabelFrame(frm, text="导出选项")
        opts.grid(row=4, column=0, columnspan=3, sticky="ew", pady=8)
        ttk.Checkbutton(opts, text="包含文件", variable=self.include_files_var).grid(row=0, column=0, sticky="w", padx=8, pady=8)
        ttk.Checkbutton(opts, text="包含隐藏项", variable=self.include_hidden_var).grid(row=0, column=1, sticky="w", padx=8, pady=8)
        ttk.Label(opts, text="最大深度（留空=不限）", style="Text.TLabel").grid(row=0, column=2, sticky="e", padx=8)
        ttk.Entry(opts, textvariable=self.max_depth_var, width=8).grid(row=0, column=3, sticky="w", padx=8)

        btns = ttk.Frame(frm, style="Content.TFrame")
        btns.grid(row=5, column=0, columnspan=3, sticky="nw", pady=(4, 10))
        ttk.Button(btns, text="使用当前工作根目录", command=self.use_current_root_for_export).pack(side="left", padx=(0, 8))
        ttk.Button(btns, text="自动生成输出文件名", command=self.auto_fill_export_output).pack(side="left", padx=(0, 8))
        ttk.Button(btns, text="开始导出", style="Accent.TButton", command=self.do_export).pack(side="left")

        self.export_log = tk.Text(frm, wrap="word", relief="flat", highlightthickness=1, bd=0, font=("Microsoft YaHei UI", 9))
        self.export_log.grid(row=6, column=0, columnspan=3, sticky="nsew")
        self._set_text(self.export_log, "导出日志会显示在这里。")
        frm.rowconfigure(6, weight=1)

    def _build_build_tab(self, parent: ttk.Frame) -> None:
        frm = ttk.Frame(parent, style="Content.TFrame")
        frm.pack(fill="both", expand=True, padx=14, pady=14)
        frm.columnconfigure(1, weight=1)
        frm.rowconfigure(5, weight=1)

        ttk.Label(frm, text="根据 XMind/Markdown 生长新结构", style="CardTitle.TLabel").grid(row=0, column=0, columnspan=3, sticky="w")
        ttk.Label(frm, text="默认只创建文件夹，不删除任何现有文件，不覆盖现有内容。", style="Muted.TLabel").grid(row=1, column=0, columnspan=3, sticky="w", pady=(4, 12))

        ttk.Label(frm, text="Markdown 文件", style="Text.TLabel").grid(row=2, column=0, sticky="w", pady=6)
        ttk.Entry(frm, textvariable=self.md_file_var).grid(row=2, column=1, sticky="ew", pady=6)
        ttk.Button(frm, text="浏览", command=self.pick_md_file).grid(row=2, column=2, padx=6)

        ttk.Label(frm, text="目标根目录", style="Text.TLabel").grid(row=3, column=0, sticky="w", pady=6)
        ttk.Entry(frm, textvariable=self.target_root_var).grid(row=3, column=1, sticky="ew", pady=6)
        ttk.Button(frm, text="浏览", command=self.pick_target_root).grid(row=3, column=2, padx=6)

        opts = ttk.LabelFrame(frm, text="创建选项")
        opts.grid(row=4, column=0, columnspan=3, sticky="ew", pady=8)
        ttk.Checkbutton(opts, text="同时创建空文件（默认关闭，更安全）", variable=self.create_files_var).grid(row=0, column=0, sticky="w", padx=8, pady=8)

        btns = ttk.Frame(frm, style="Content.TFrame")
        btns.grid(row=5, column=0, columnspan=3, sticky="nw", pady=(4, 10))
        ttk.Button(btns, text="载入并预览 Markdown", command=self.load_markdown_preview).pack(side="left", padx=(0, 8))
        ttk.Button(btns, text="预览将创建的路径", command=self.preview_build_paths).pack(side="left", padx=(0, 8))
        ttk.Button(btns, text="开始创建", style="Accent.TButton", command=self.do_build).pack(side="left")

        mid = ttk.Panedwindow(frm, orient="horizontal")
        mid.grid(row=6, column=0, columnspan=3, sticky="nsew")
        frm.rowconfigure(6, weight=1)

        left = ttk.Frame(mid, style="Content.TFrame")
        right = ttk.Frame(mid, style="Content.TFrame")
        mid.add(left, weight=1)
        mid.add(right, weight=1)

        left.columnconfigure(0, weight=1)
        left.rowconfigure(1, weight=1)
        ttk.Label(left, text="Markdown 树预览", style="CardTitle.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 8))
        self.md_tree = ttk.Treeview(left, columns=("type", "path"), show="tree headings")
        self.md_tree.heading("#0", text="名称")
        self.md_tree.heading("type", text="类型")
        self.md_tree.heading("path", text="虚拟路径")
        self.md_tree.column("#0", width=260, anchor="w")
        self.md_tree.column("type", width=80, anchor="center")
        self.md_tree.column("path", width=500, anchor="w")
        self.md_tree.grid(row=1, column=0, sticky="nsew")
        md_scroll = ttk.Scrollbar(left, orient="vertical", command=self.md_tree.yview)
        md_scroll.grid(row=1, column=1, sticky="ns")
        self.md_tree.configure(yscrollcommand=md_scroll.set)

        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)
        ttk.Label(right, text="日志 / 路径预览", style="CardTitle.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 8))
        self.build_log = tk.Text(right, wrap="word", relief="flat", highlightthickness=1, bd=0, font=("Consolas", 10))
        self.build_log.grid(row=1, column=0, sticky="nsew")
        self._set_text(self.build_log, "先载入 Markdown，即可在左侧预览节点树。")

    def _build_help_tab(self, parent: ttk.Frame) -> None:
        text = tk.Text(parent, wrap="word", relief="flat", highlightthickness=0, bd=0, font=("Microsoft YaHei UI", 10), padx=20, pady=18)
        text.pack(fill="both", expand=True)
        text.insert(
            "1.0",
            f"{APP_NAME} v{APP_VERSION}\n\n"
            "这个版本的核心变化：\n"
            "1）导出格式改成 XMind 兼容 Markdown，更适合先在 XMind 梳理、再回到软件生长目录。\n"
            "2）加入文件树工作台，支持树状预览、双击打开节点。\n"
            "3）加入右键收藏节点，收藏后可一键直达深层目录。\n"
            "4）整体代码结构按“扫描 / 导出 / 解析 / 收藏 / UI”拆层，后续加功能更容易。\n\n"
            "XMind 兼容格式说明：\n"
            "# 根目录/\n"
            "## 一级分类/\n"
            "- 二级分类/\n"
            "  - 三级分类/\n"
            "    - 文件.docx\n\n"
            "推荐做法：\n"
            "A. 先读取共享盘或个人工作区，右键收藏高频深层节点。\n"
            "B. 导出为 Markdown，在 XMind 中梳理出新的结构。\n"
            "C. 再把 XMind 导出的 Markdown 导回这里，预览后生长新结构。\n"
            "D. 默认只创建，不删除原数据。\n\n"
            "后续容易扩展的方向：\n"
            "- 节点标签、颜色、备注\n"
            "- 收藏分组\n"
            "- 文件模板挂接\n"
            "- 一键打开常用工作组合\n"
            "- 接入 AI 的只读分析工作区\n"
            "- 导入导出更多格式（OPML、JSON、CSV）\n"
        )
        text.configure(state="disabled")

    # ---------- helpers ----------
    def _bind_events(self) -> None:
        self.workspace_tree.bind("<Double-1>", self.on_tree_double_click)
        self.workspace_tree.bind("<Button-3>", self.on_tree_right_click)
        self.workspace_tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        self.favorites_list.bind("<Double-1>", lambda _e: self.open_selected_favorite())
        self.search_var.trace_add("write", lambda *_args: self._reset_search())

    def _reset_search(self) -> None:
        self.search_matches = []
        self.search_cursor = -1

    def _set_text(self, text_widget: tk.Text, value: str) -> None:
        text_widget.configure(state="normal")
        text_widget.delete("1.0", "end")
        text_widget.insert("1.0", value)
        text_widget.configure(state="disabled")

    def log_status(self, msg: str) -> None:
        self.status_var.set(msg)

    def _append_log(self, text_widget: tk.Text, message: str) -> None:
        text_widget.configure(state="normal")
        text_widget.insert("end", f"[{now_text()}] {message}\n")
        text_widget.see("end")
        text_widget.configure(state="disabled")

    def _parse_max_depth(self) -> Optional[int]:
        raw = self.max_depth_var.get().strip()
        if not raw:
            return None
        value = int(raw)
        if value < 1:
            raise ValueError("最大深度必须 >= 1")
        return value

    # ---------- favorites ----------
    def _load_favorites_to_ui(self) -> None:
        self.favorites_list.delete(0, "end")
        for fav in self.favorites:
            mark = "📁" if fav.is_dir else "📄"
            self.favorites_list.insert("end", f"{mark} {fav.name}")

    def _save_favorites(self) -> None:
        self.favorites_store.save(self.favorites)
        self._load_favorites_to_ui()

    def add_favorite(self, path: Path) -> None:
        path = normalize_path(path)
        if any(normalize_path(f.path) == path for f in self.favorites):
            self.log_status("该节点已在收藏中。")
            return
        fav = Favorite(
            name=path.name or str(path),
            path=str(path),
            is_dir=path.is_dir(),
            created_at=now_text(),
        )
        self.favorites.append(fav)
        self._save_favorites()
        self.log_status(f"已收藏：{path}")

    def remove_selected_favorite(self) -> None:
        sel = self.favorites_list.curselection()
        if not sel:
            messagebox.showwarning(APP_NAME, "请先选中一个收藏节点。")
            return
        idx = sel[0]
        fav = self.favorites[idx]
        if not messagebox.askyesno(APP_NAME, f"确认从收藏中移除？\n\n{fav.path}"):
            return
        del self.favorites[idx]
        self._save_favorites()
        self.log_status("已移除收藏。")

    def get_selected_favorite(self) -> Optional[Favorite]:
        sel = self.favorites_list.curselection()
        if not sel:
            return None
        return self.favorites[sel[0]]

    def open_favorite_only(self) -> None:
        fav = self.get_selected_favorite()
        if not fav:
            messagebox.showwarning(APP_NAME, "请先选择一个收藏节点。")
            return
        try:
            open_path(Path(fav.path))
        except Exception as exc:
            messagebox.showerror(APP_NAME, f"打开失败：\n{exc}")

    def open_selected_favorite(self) -> None:
        fav = self.get_selected_favorite()
        if not fav:
            messagebox.showwarning(APP_NAME, "请先选择一个收藏节点。")
            return
        target = normalize_path(fav.path)
        if not target.exists():
            messagebox.showerror(APP_NAME, f"路径不存在：\n{target}")
            return
        if target.is_dir():
            self.workspace_root_var.set(str(target))
            self.load_workspace_tree()
            try:
                open_path(target)
            except Exception:
                pass
        else:
            try:
                open_path(target)
            except Exception:
                pass
            parent = target.parent
            self.workspace_root_var.set(str(parent))
            self.load_workspace_tree(select_path=target)

    # ---------- workspace actions ----------
    def pick_workspace_root(self) -> None:
        path = filedialog.askdirectory(title="选择工作根目录")
        if path:
            self.workspace_root_var.set(path)

    def load_workspace_tree(self, select_path: Optional[Path] = None) -> None:
        raw = self.workspace_root_var.get().strip()
        if not raw:
            messagebox.showwarning(APP_NAME, "请先选择工作根目录。")
            return
        try:
            root_path = normalize_path(raw)
            tree = scan_fs_tree(root_path, include_files=True, include_hidden=False, max_depth=None)
            self.current_root = root_path
            self.current_tree = tree
            self.current_index = flatten_fs_tree(tree)
            self._render_fs_tree(self.workspace_tree, tree, self.current_item_paths)
            self.settings["last_root"] = str(root_path)
            self.settings_store.save(self.settings)
            self.export_source_var.set(str(root_path))
            self.log_status(f"已载入：{root_path}")
            self._set_text(self.workspace_detail, f"当前根目录：\n{root_path}\n\n节点总数：{len(self.current_index)}")
            if select_path:
                self.select_tree_item_by_path(select_path)
        except Exception as exc:
            messagebox.showerror(APP_NAME, f"读取结构失败：\n{exc}")
            self.log_status(f"读取失败：{exc}")

    def reload_current_tree(self) -> None:
        if not self.current_root:
            self.load_workspace_tree()
            return
        self.workspace_root_var.set(str(self.current_root))
        self.load_workspace_tree()

    def open_current_root(self) -> None:
        raw = self.workspace_root_var.get().strip()
        if not raw:
            messagebox.showwarning(APP_NAME, "请先选择工作根目录。")
            return
        try:
            open_path(Path(raw))
        except Exception as exc:
            messagebox.showerror(APP_NAME, f"打开失败：\n{exc}")

    def _render_fs_tree(self, tree_widget: ttk.Treeview, root: FsNode, path_map: Dict[str, Path]) -> None:
        tree_widget.delete(*tree_widget.get_children())
        path_map.clear()

        def add_node(parent_id: str, node: FsNode) -> str:
            icon = "📁" if node.is_dir else "📄"
            item_id = tree_widget.insert(
                parent_id,
                "end",
                text=f"{icon} {node.name}",
                values=("文件夹" if node.is_dir else "文件", str(node.path)),
                open=False,
            )
            path_map[item_id] = node.path
            for child in node.children:
                add_node(item_id, child)
            return item_id

        root_id = add_node("", root)
        tree_widget.item(root_id, open=True)

    def select_tree_item_by_path(self, target: Path) -> None:
        target = normalize_path(target)
        for item_id, path in self.current_item_paths.items():
            if path == target:
                self._reveal_item(self.workspace_tree, item_id)
                break

    def _reveal_item(self, tree_widget: ttk.Treeview, item_id: str) -> None:
        parent = tree_widget.parent(item_id)
        while parent:
            tree_widget.item(parent, open=True)
            parent = tree_widget.parent(parent)
        tree_widget.selection_set(item_id)
        tree_widget.focus(item_id)
        tree_widget.see(item_id)

    def on_tree_select(self, _event=None) -> None:
        item = self.workspace_tree.focus()
        if not item:
            return
        path = self.current_item_paths.get(item)
        if not path:
            return
        typ = "文件夹" if path.is_dir() else "文件"
        info = f"名称：{path.name}\n类型：{typ}\n路径：{path}"
        if path.exists():
            try:
                stat = path.stat()
                info += f"\n大小：{stat.st_size} 字节\n修改时间：{_dt.datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')}"
            except Exception:
                pass
        self._set_text(self.workspace_detail, info)

    def on_tree_double_click(self, _event=None) -> None:
        item = self.workspace_tree.focus()
        if not item:
            return
        path = self.current_item_paths.get(item)
        if not path:
            return
        try:
            open_path(path)
            self.log_status(f"已打开：{path}")
        except Exception as exc:
            messagebox.showerror(APP_NAME, f"打开失败：\n{exc}")

    def on_tree_right_click(self, event) -> None:
        item = self.workspace_tree.identify_row(event.y)
        if item:
            self.workspace_tree.selection_set(item)
            self.workspace_tree.focus(item)
            self.workspace_menu.tk_popup(event.x_root, event.y_root)

    def menu_open_selected_tree_path(self) -> None:
        item = self.workspace_tree.focus()
        if not item:
            return
        path = self.current_item_paths.get(item)
        if not path:
            return
        try:
            open_path(path)
        except Exception as exc:
            messagebox.showerror(APP_NAME, f"打开失败：\n{exc}")

    def menu_open_selected_parent(self) -> None:
        item = self.workspace_tree.focus()
        if not item:
            return
        path = self.current_item_paths.get(item)
        if not path:
            return
        try:
            open_parent(path)
        except Exception as exc:
            messagebox.showerror(APP_NAME, f"打开所在位置失败：\n{exc}")

    def menu_favorite_selected_node(self) -> None:
        item = self.workspace_tree.focus()
        if not item:
            return
        path = self.current_item_paths.get(item)
        if not path:
            return
        self.add_favorite(path)

    def search_in_current_tree(self) -> None:
        keyword = self.search_var.get().strip().lower()
        if not keyword:
            messagebox.showwarning(APP_NAME, "请输入要查找的关键词。")
            return
        self.search_matches = [
            item_id for item_id, path in self.current_item_paths.items()
            if keyword in path.name.lower() or keyword in str(path).lower()
        ]
        if not self.search_matches:
            self.search_cursor = -1
            self.log_status("未找到匹配节点。")
            return
        self.search_cursor = 0
        self._reveal_item(self.workspace_tree, self.search_matches[0])
        self.log_status(f"找到 {len(self.search_matches)} 个匹配，已定位第 1 个。")

    def goto_next_match(self) -> None:
        if not self.search_matches:
            self.search_in_current_tree()
            return
        self.search_cursor = (self.search_cursor + 1) % len(self.search_matches)
        self._reveal_item(self.workspace_tree, self.search_matches[self.search_cursor])
        self.log_status(f"已定位第 {self.search_cursor + 1}/{len(self.search_matches)} 个匹配。")

    def goto_prev_match(self) -> None:
        if not self.search_matches:
            self.search_in_current_tree()
            return
        self.search_cursor = (self.search_cursor - 1) % len(self.search_matches)
        self._reveal_item(self.workspace_tree, self.search_matches[self.search_cursor])
        self.log_status(f"已定位第 {self.search_cursor + 1}/{len(self.search_matches)} 个匹配。")

    # ---------- export actions ----------
    def pick_export_source(self) -> None:
        path = filedialog.askdirectory(title="选择要导出的源文件夹")
        if path:
            self.export_source_var.set(path)

    def pick_export_output(self) -> None:
        path = filedialog.asksaveasfilename(
            title="保存 Markdown 文件",
            defaultextension=".md",
            filetypes=[("Markdown 文件", "*.md"), ("所有文件", "*.*")],
        )
        if path:
            self.export_output_var.set(path)

    def use_current_root_for_export(self) -> None:
        if self.current_root:
            self.export_source_var.set(str(self.current_root))
            self.log_status("已填入当前工作根目录。")
        else:
            messagebox.showwarning(APP_NAME, "当前还没有载入工作根目录。")

    def auto_fill_export_output(self) -> None:
        raw = self.export_source_var.get().strip()
        if not raw:
            messagebox.showwarning(APP_NAME, "请先选择源文件夹。")
            return
        src = normalize_path(raw)
        ts = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        out = src.parent / f"{src.name}_XMind结构_{ts}.md"
        self.export_output_var.set(str(out))

    def do_export(self) -> None:
        src = self.export_source_var.get().strip()
        out = self.export_output_var.get().strip()
        if not src:
            messagebox.showwarning(APP_NAME, "请选择源文件夹。")
            return
        if not out:
            messagebox.showwarning(APP_NAME, "请选择输出 Markdown 文件。")
            return
        try:
            max_depth = self._parse_max_depth()
            export_tree_to_xmind_markdown(
                source_dir=Path(src),
                output_md=Path(out),
                include_files=self.include_files_var.get(),
                include_hidden=self.include_hidden_var.get(),
                max_depth=max_depth,
            )
            self._append_log(self.export_log, f"导出成功：{out}")
            self.log_status(f"导出完成：{out}")
            messagebox.showinfo(APP_NAME, f"导出成功：\n{out}")
        except Exception as exc:
            self._append_log(self.export_log, f"导出失败：{exc}")
            messagebox.showerror(APP_NAME, f"导出失败：\n{exc}")

    # ---------- markdown build actions ----------
    def pick_md_file(self) -> None:
        path = filedialog.askopenfilename(
            title="选择 Markdown 文件",
            filetypes=[("Markdown 文件", "*.md"), ("所有文件", "*.*")],
        )
        if path:
            self.md_file_var.set(path)

    def pick_target_root(self) -> None:
        path = filedialog.askdirectory(title="选择目标根目录")
        if path:
            self.target_root_var.set(path)

    def load_markdown_preview(self) -> None:
        raw = self.md_file_var.get().strip()
        if not raw:
            messagebox.showwarning(APP_NAME, "请先选择 Markdown 文件。")
            return
        try:
            nodes = read_xmind_markdown(Path(raw))
            self.md_preview_nodes = nodes
            root = build_tree_from_nodes(nodes)
            self._render_fs_tree(self.md_tree, root, self.md_item_paths)
            self._set_text(self.build_log, f"已载入 Markdown：\n{raw}\n\n根节点：{nodes[0].name}\n节点数：{len(nodes)}")
            self.log_status("Markdown 预览已载入。")
        except Exception as exc:
            messagebox.showerror(APP_NAME, f"载入 Markdown 失败：\n{exc}")
            self.log_status(f"Markdown 载入失败：{exc}")

    def preview_build_paths(self) -> None:
        md = self.md_file_var.get().strip()
        target = self.target_root_var.get().strip()
        if not md or not target:
            messagebox.showwarning(APP_NAME, "请先选择 Markdown 文件和目标根目录。")
            return
        try:
            nodes = self.md_preview_nodes or read_xmind_markdown(Path(md))
            planned = preview_build_from_nodes(nodes, Path(target), create_files=self.create_files_var.get())
            self._set_text(self.build_log, "将要创建的路径：\n\n" + "\n".join(planned) + f"\n\n合计：{len(planned)} 个节点")
            self.log_status(f"已预览 {len(planned)} 个将创建的节点。")
        except Exception as exc:
            messagebox.showerror(APP_NAME, f"预览失败：\n{exc}")

    def do_build(self) -> None:
        md = self.md_file_var.get().strip()
        target = self.target_root_var.get().strip()
        if not md or not target:
            messagebox.showwarning(APP_NAME, "请先选择 Markdown 文件和目标根目录。")
            return
        confirm_text = (
            "本操作默认只创建，不删除，不覆盖。\n"
            "现有文件或文件夹若已存在，会跳过。\n\n"
            "是否继续创建？"
        )
        if not messagebox.askyesno(APP_NAME, confirm_text):
            return
        try:
            nodes = self.md_preview_nodes or read_xmind_markdown(Path(md))
            stats = create_structure_from_nodes(nodes, Path(target), create_files=self.create_files_var.get())
            summary = (
                f"创建完成。\n\n"
                f"新建文件夹：{stats.created_dirs}\n"
                f"已存在文件夹：{stats.existing_dirs}\n"
                f"新建文件：{stats.created_files}\n"
                f"已存在文件：{stats.existing_files}\n"
                f"跳过节点：{stats.skipped_nodes}"
            )
            self._append_log(self.build_log, summary.replace("\n", "；"))
            self.log_status("目录结构创建完成。")
            messagebox.showinfo(APP_NAME, summary)
        except Exception as exc:
            self._append_log(self.build_log, f"创建失败：{exc}")
            messagebox.showerror(APP_NAME, f"创建失败：\n{exc}")


# -----------------------------
# CLI
# -----------------------------
def build_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=f"{APP_NAME} v{APP_VERSION}")
    sub = parser.add_subparsers(dest="command")

    p_export = sub.add_parser("export", help="导出文件夹为 XMind Markdown")
    p_export.add_argument("source_dir", help="源文件夹")
    p_export.add_argument("output_md", help="输出 Markdown 文件")
    p_export.add_argument("--dirs-only", action="store_true", help="只导出文件夹")
    p_export.add_argument("--include-hidden", action="store_true", help="包含隐藏项")
    p_export.add_argument("--max-depth", type=int, default=None, help="最大深度")

    p_build = sub.add_parser("build", help="根据 XMind Markdown 创建新结构")
    p_build.add_argument("markdown_file", help="Markdown 文件")
    p_build.add_argument("target_root", help="目标根目录")
    p_build.add_argument("--create-files", action="store_true", help="同时创建空文件")
    p_build.add_argument("--preview", action="store_true", help="只预览将创建的路径")

    sub.add_parser("gui", help="启动图形界面")
    return parser


def run_gui() -> int:
    if tk is None:
        print("当前环境缺少 tkinter，无法启动图形界面。", file=sys.stderr)
        return 2
    root = tk.Tk()
    App(root)
    root.mainloop()
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_cli_parser()
    args = parser.parse_args(argv)

    if not args.command or args.command == "gui":
        return run_gui()

    try:
        if args.command == "export":
            export_tree_to_xmind_markdown(
                source_dir=Path(args.source_dir),
                output_md=Path(args.output_md),
                include_files=not args.dirs_only,
                include_hidden=args.include_hidden,
                max_depth=args.max_depth,
            )
            print(f"导出成功：{args.output_md}")
            return 0

        if args.command == "build":
            nodes = read_xmind_markdown(Path(args.markdown_file))
            if args.preview:
                planned = preview_build_from_nodes(nodes, Path(args.target_root), create_files=args.create_files)
                print("将要创建的路径：")
                for item in planned:
                    print(item)
                print(f"合计：{len(planned)} 个节点")
                return 0

            stats = create_structure_from_nodes(nodes, Path(args.target_root), create_files=args.create_files)
            print(
                "创建完成：\n"
                f"  新建文件夹：{stats.created_dirs}\n"
                f"  已存在文件夹：{stats.existing_dirs}\n"
                f"  新建文件：{stats.created_files}\n"
                f"  已存在文件：{stats.existing_files}\n"
                f"  跳过节点：{stats.skipped_nodes}"
            )
            return 0

        parser.print_help()
        return 1
    except Exception as exc:
        print(f"错误：{exc}", file=sys.stderr)
        if os.environ.get("WORKBENCH_DEBUG") == "1":
            traceback.print_exc()
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
