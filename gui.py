"""
PrivacyScope GUI v2 — 交互式隐私仪表盘
- 中性状态陈述，不恐吓
- 每个问题可修复 / 跳转系统设置 / 查看详情
- 撤销支持
"""
import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import os

from scanner import run_full_scan, CATEGORIES
from fixer import is_admin, fix_issue, fix_all, undo_fix
from undo_manager import UndoManager

FONT = ("Microsoft YaHei UI", 10)
FONT_BOLD = ("Microsoft YaHei UI", 10, "bold")
FONT_TITLE = ("Microsoft YaHei UI", 16, "bold")
FONT_SMALL = ("Microsoft YaHei UI", 8)
FONT_MONO = ("Consolas", 9)
FONT_MONO_SMALL = ("Consolas", 8)

BG = "#1e1e2e"
SURFACE = "#313244"
FG = "#cdd6f4"
ACCENT = "#89b4fa"
MUTED = "#6c7086"
BTN_FIX = "#a6e3a1"
BTN_UNDO = "#f9e2af"
BTN_SETTINGS = "#89b4fa"

UNDO_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "undo_history.json")


class PrivacyScopeGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("PrivacyScope — 隐私仪表盘")
        self.root.geometry("640x680")
        self.root.configure(bg=BG)
        self.root.minsize(500, 480)
        self.scan_result = None
        self.undo_mgr = UndoManager(UNDO_FILE)
        self._expanded = set()  # 已展开的 issue id

        self._build_ui()

    def _build_ui(self):
        # 顶部
        header = tk.Frame(self.root, bg=SURFACE)
        header.pack(fill=tk.X)

        tk.Label(
            header, text=" PrivacyScope", font=FONT_TITLE, bg=SURFACE, fg=ACCENT
        ).pack(side=tk.LEFT, padx=12, pady=8)

        if is_admin():
            undo_count = self.undo_mgr.count()
            undo_text = f"撤销({undo_count})" if undo_count > 0 else ""
            if undo_text:
                tk.Button(
                    header, text=undo_text, command=self._undo_last,
                    font=FONT_SMALL, bg=BTN_UNDO, fg=BG,
                    relief=tk.FLAT, bd=4, padx=8, cursor="hand2",
                ).pack(side=tk.RIGHT, padx=8, pady=6)
            tk.Label(
                header, text="管理员模式", font=FONT_SMALL, bg=SURFACE, fg=BTN_FIX,
            ).pack(side=tk.RIGHT, padx=4, pady=6)
        else:
            tk.Label(
                header, text="仅检测 — 右键以管理员身份运行可解锁修复",
                font=FONT_SMALL, bg=SURFACE, fg=MUTED,
            ).pack(side=tk.RIGHT, padx=8, pady=6)

        # 主区域
        self.main_area = tk.Frame(self.root, bg=BG)
        self.main_area.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        # 欢迎页
        self.welcome = tk.Frame(self.main_area, bg=BG)
        self.welcome.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            self.welcome, text="Windows 隐私仪表盘",
            font=FONT_TITLE, bg=BG, fg=FG,
        ).pack(pady=(60, 4))
        tk.Label(
            self.welcome,
            text="扫描系统设置，了解数据流向，你自己决定改变什么。",
            font=FONT, bg=BG, fg=MUTED,
        ).pack(pady=(0, 4))
        tk.Label(
            self.welcome,
            text="不给你的隐私打分。我们不替你判断什么是对的。",
            font=FONT_SMALL, bg=BG, fg=MUTED,
        ).pack(pady=(0, 20))

        tk.Button(
            self.welcome, text="开始扫描", command=self._run_scan,
            font=FONT_BOLD, bg=ACCENT, fg=BG, relief=tk.FLAT,
            bd=0, padx=32, pady=10, cursor="hand2",
        ).pack()

    def _clear_main(self):
        for w in self.main_area.winfo_children():
            w.destroy()

    def _run_scan(self):
        self._clear_main()
        self._expanded.clear()
        self.scan_result = run_full_scan()
        self._show_result()

    def _show_result(self):
        r = self.scan_result

        # 顶部摘要（中性）
        summary = tk.Frame(self.main_area, bg=SURFACE)
        summary.pack(fill=tk.X, pady=(0, 8))

        tk.Label(
            summary,
            text=f" 扫描完成 — 检测到 {r['total_issues']} 项设置",
            font=FONT_BOLD, bg=SURFACE, fg=FG,
        ).pack(side=tk.LEFT, padx=10, pady=8)

        fixable = r["fixable_count"]
        if fixable > 0 and is_admin():
            tk.Button(
                summary, text=f"一键修复 {fixable} 项", command=self._fix_all,
                font=FONT_BOLD, bg=BTN_FIX, fg=BG, relief=tk.FLAT,
                bd=4, padx=12, cursor="hand2",
            ).pack(side=tk.RIGHT, padx=10, pady=6)

        # 分类标签行
        cat_row = tk.Frame(self.main_area, bg=BG)
        cat_row.pack(fill=tk.X, pady=(0, 4))

        cat_colors = {
            "telemetry": "#cba6f7", "ads": "#fab387", "cortana": "#f9e2af",
            "location": "#a6e3a1", "apps": "#89b4fa", "updates": "#94e2d5",
            "network": "#f38ba8",
        }
        for cat_id, cat_data in r["categories"].items():
            if cat_data["count"] > 0:
                tk.Label(
                    cat_row,
                    text=f"  {cat_data['name']} {cat_data['count']}  ",
                    font=FONT_SMALL, bg=BG,
                    fg=cat_colors.get(cat_id, MUTED),
                ).pack(side=tk.LEFT, padx=1)

        # 问题列表
        self._build_issue_list()

        # 底部操作
        bottom = tk.Frame(self.main_area, bg=BG)
        bottom.pack(fill=tk.X, pady=(8, 0))
        tk.Button(
            bottom, text="重新扫描", command=self._run_scan,
            font=FONT, bg=SURFACE, fg=FG, relief=tk.FLAT, bd=4, padx=12,
        ).pack(side=tk.LEFT)

    def _build_issue_list(self):
        r = self.scan_result

        list_frame = tk.Frame(self.main_area, bg=BG)
        list_frame.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(list_frame, bg=BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=canvas.yview)
        issue_frame = tk.Frame(canvas, bg=BG)

        issue_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=issue_frame, anchor="nw", tags="issues")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.bind("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))
        canvas.bind("<Enter>", lambda e: canvas.focus_set())

        for issue in r["all_issues"]:
            self._add_issue_card(issue_frame, issue)

    def _add_issue_card(self, parent, issue):
        is_open = issue.id in self._expanded

        card = tk.Frame(parent, bg=SURFACE)
        card.pack(fill=tk.X, pady=2)

        # 标题行（可点击展开）
        header = tk.Frame(card, bg=SURFACE, cursor="hand2")
        header.pack(fill=tk.X, padx=8, pady=(6, 2))

        arrow = " " if is_open else " "
        cat_name = CATEGORIES.get(issue.category, issue.category)
        tk.Label(
            header, text=f"{arrow} {issue.title}",
            font=FONT_BOLD, bg=SURFACE, fg=FG, anchor=tk.W, cursor="hand2",
        ).pack(side=tk.LEFT)
        tk.Label(
            header, text=f"{cat_name}  ", font=FONT_SMALL, bg=SURFACE, fg=MUTED,
        ).pack(side=tk.RIGHT)
        tk.Label(
            header, text=f"当前: {issue.current_state}  ",
            font=FONT_SMALL, bg=SURFACE, fg=ACCENT,
        ).pack(side=tk.RIGHT)

        # 绑定点击展开/折叠
        for w in (header, header.winfo_children()[0]):
            w.bind("<Button-1>", lambda e, c=card, iid=issue.id: self._toggle_expand(c, iid))

        # 展开内容
        if is_open:
            self._build_expanded(card, issue)

    def _build_expanded(self, card, issue):
        detail = tk.Frame(card, bg=SURFACE)
        detail.pack(fill=tk.X, padx=16, pady=(0, 8))

        # 描述
        desc_text = issue.description
        if issue.options:
            desc_text += "\n\n可选设置："
            for opt in issue.options:
                desc_text += f"\n  + {opt}"

        tk.Label(
            detail, text=desc_text, font=FONT_SMALL, bg=SURFACE, fg=MUTED,
            anchor=tk.W, justify=tk.LEFT, wraplength=550,
        ).pack(fill=tk.X, pady=(0, 6))

        # 操作按钮行
        btn_row = tk.Frame(detail, bg=SURFACE)
        btn_row.pack(fill=tk.X)

        if issue.ms_settings_uri:
            tk.Button(
                btn_row, text="跳转到系统设置",
                command=lambda uri=issue.ms_settings_uri: subprocess.Popen(["start", uri], shell=True),
                font=FONT_SMALL, bg=BTN_SETTINGS, fg=BG,
                relief=tk.FLAT, bd=3, padx=8, cursor="hand2",
            ).pack(side=tk.LEFT, padx=(0, 6))

        if issue.fix_type == "registry_dword" and is_admin():
            btn_text = "修复此项"
            tk.Button(
                btn_row, text=btn_text,
                command=lambda i=issue, c=card: self._fix_single(i, c),
                font=FONT_SMALL, bg=BTN_FIX, fg=BG,
                relief=tk.FLAT, bd=3, padx=8, cursor="hand2",
            ).pack(side=tk.LEFT, padx=(0, 6))

        if issue.fix_type in ("manual", "ms_settings") and not issue.ms_settings_uri:
            tk.Label(
                btn_row, text="此项需在系统设置中手动调整",
                font=FONT_SMALL, bg=SURFACE, fg=MUTED,
            ).pack(side=tk.LEFT)

    def _toggle_expand(self, card, issue_id):
        if issue_id in self._expanded:
            self._expanded.discard(issue_id)
        else:
            self._expanded.add(issue_id)
        # 重建列表（简单直接的刷新方式）
        self._clear_main()
        self._show_result()

    def _fix_single(self, issue, card):
        if not messagebox.askyesno(
            "确认修改",
            f"将 {issue.title} 从「{issue.current_state}」修改为推荐设置。"
        ):
            return

        success = fix_issue(issue, self.undo_mgr)
        if success:
            messagebox.showinfo("已修改", f"{issue.title} 已更新。可点击右上角「撤销」恢复。")
            self._run_scan()
        else:
            messagebox.showerror("失败", f"无法修改 {issue.title}，可能权限不足。")

    def _fix_all(self):
        issues = [i for i in self.scan_result["all_issues"] if i.fix_type == "registry_dword"]
        if not issues:
            messagebox.showinfo("提示", "没有可自动修复的项目。")
            return
        if not messagebox.askyesno(
            "确认批量修复",
            f"将修改 {len(issues)} 项注册表设置。所有修改均可通过「撤销」按钮恢复。"
        ):
            return

        fixed, failed, skipped = fix_all(issues, self.undo_mgr)
        msg = f"已修改 {fixed} 项设置。"
        if failed > 0:
            msg += f"\n{failed} 项因权限不足未能修改。"
        msg += "\n\n可通过「撤销」按钮逐一恢复。"
        messagebox.showinfo("完成", msg)
        self._run_scan()

    def _undo_last(self):
        record = self.undo_mgr.undo_last()
        if not record:
            messagebox.showinfo("提示", "没有可撤销的操作。")
            return
        if messagebox.askyesno("撤销", f"将 {record.title} 恢复到修改前的状态。"):
            undo_fix(record, self.undo_mgr)
            self._run_scan()
