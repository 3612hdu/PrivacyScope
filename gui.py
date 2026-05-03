"""
PrivacyScope GUI - 隐私仪表盘
"""
import tkinter as tk
from tkinter import ttk, messagebox
from scanner import run_full_scan
from fixer import fix_all, is_admin

FONT = ("Microsoft YaHei UI", 10)
FONT_BOLD = ("Microsoft YaHei UI", 10, "bold")
FONT_TITLE = ("Microsoft YaHei UI", 20, "bold")
FONT_SCORE = ("Microsoft YaHei UI", 48, "bold")
FONT_SMALL = ("Microsoft YaHei UI", 8)

BG = "#1e1e2e"
SURFACE = "#313244"
FG = "#cdd6f4"
ACCENT = "#89b4fa"
GREEN = "#a6e3a1"
YELLOW = "#f9e2af"
ORANGE = "#fab387"
RED = "#f38ba8"
MUTED = "#6c7086"


class PrivacyScopeGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("PrivacyScope - Windows 隐私仪表盘")
        self.root.geometry("560x640")
        self.root.configure(bg=BG)
        self.root.minsize(440, 480)
        self.scan_result = None

        self._build_ui()

    def _build_ui(self):
        # 顶部栏
        header = tk.Frame(self.root, bg=SURFACE)
        header.pack(fill=tk.X)

        tk.Label(
            header, text=" PrivacyScope", font=FONT_TITLE, bg=SURFACE, fg=ACCENT
        ).pack(side=tk.LEFT, padx=12, pady=8)

        admin_text = "(管理员模式)" if is_admin() else "(仅检测)"
        tk.Label(
            header, text=admin_text, font=FONT_SMALL, bg=SURFACE, fg=MUTED
        ).pack(side=tk.RIGHT, padx=12, pady=8)

        # 主区域
        self.main_area = tk.Frame(self.root, bg=BG)
        self.main_area.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        # 初始状态 — 欢迎页
        self.welcome_frame = tk.Frame(self.main_area, bg=BG)
        self.welcome_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            self.welcome_frame,
            text=" Windows",
            font=FONT_TITLE,
            bg=BG,
            fg=FG,
        ).pack(pady=(60, 4))
        tk.Label(
            self.welcome_frame,
            text="隐私仪表盘",
            font=FONT_TITLE,
            bg=BG,
            fg=FG,
        ).pack(pady=(0, 16))
        tk.Label(
            self.welcome_frame,
            text="扫描你的 Windows 隐私设置\n检查遥测、广告追踪、位置、搜索等 7 大类隐私项",
            font=FONT,
            bg=BG,
            fg=MUTED,
            justify=tk.CENTER,
        ).pack(pady=(0, 24))

        scan_btn = tk.Button(
            self.welcome_frame,
            text="开始扫描",
            command=self._run_scan,
            font=FONT_BOLD,
            bg=ACCENT,
            fg=BG,
            relief=tk.FLAT,
            bd=0,
            padx=32,
            pady=10,
            cursor="hand2",
        )
        scan_btn.pack()

        self.result_frame = None

    def _clear_main(self):
        for w in self.main_area.winfo_children():
            w.destroy()

    def _run_scan(self):
        self._clear_main()
        self.scan_result = run_full_scan()
        self._show_result()

    def _show_result(self):
        r = self.scan_result

        # 评分卡片
        score_card = tk.Frame(self.main_area, bg=SURFACE)
        score_card.pack(fill=tk.X, pady=(0, 10))

        score_left = tk.Frame(score_card, bg=SURFACE)
        score_left.pack(side=tk.LEFT, padx=16, pady=12)

        tk.Label(
            score_left, text=str(r["score"]), font=FONT_SCORE, bg=SURFACE,
            fg=r["grade_color"]
        ).pack()
        tk.Label(
            score_left, text=f"等级 {r['grade']}", font=FONT_BOLD, bg=SURFACE,
            fg=r["grade_color"]
        ).pack()

        score_right = tk.Frame(score_card, bg=SURFACE)
        score_right.pack(side=tk.RIGHT, padx=16, pady=12, fill=tk.Y)

        tk.Label(
            score_right, text=r["grade_text"], font=FONT, bg=SURFACE, fg=FG
        ).pack(anchor=tk.E)
        tk.Label(
            score_right,
            text=f"发现 {r['total_issues']} 个问题： {r['high']}高 {r['medium']}中 {r['low']}低",
            font=FONT_SMALL, bg=SURFACE, fg=MUTED,
        ).pack(anchor=tk.E, pady=(4, 0))

        # 分类统计
        stats_frame = tk.Frame(self.main_area, bg=BG)
        stats_frame.pack(fill=tk.X, pady=(0, 6))

        cat_colors = {
            "telemetry": "#f38ba8", "ads": "#fab387", "cortana": "#f9e2af",
            "location": "#a6e3a1", "apps": "#89b4fa", "updates": "#cba6f7",
            "network": "#94e2d5",
        }
        for cat_id, cat_data in r["categories"].items():
            if cat_data["count"] > 0:
                cat_frame = tk.Frame(stats_frame, bg=BG)
                cat_frame.pack(side=tk.LEFT, padx=4)
                color = cat_colors.get(cat_id, MUTED)
                tk.Label(
                    cat_frame,
                    text=f" {cat_data['name']} {cat_data['count']}" if cat_data["count"] > 0 else "",
                    font=FONT_SMALL, bg=BG, fg=color,
                ).pack()

        # 问题列表
        list_frame = tk.Frame(self.main_area, bg=BG)
        list_frame.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(list_frame, bg=BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=canvas.yview)
        issues_frame = tk.Frame(canvas, bg=BG)

        issues_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=issues_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.bind("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

        severity_order = {"high": 0, "medium": 1, "low": 2}
        sorted_issues = sorted(r["all_issues"], key=lambda i: severity_order.get(i.severity, 99))

        for issue in sorted_issues:
            self._add_issue_row(issues_frame, issue)

        # 底部操作栏
        action_frame = tk.Frame(self.main_area, bg=BG)
        action_frame.pack(fill=tk.X, pady=(8, 0))

        tk.Button(
            action_frame, text="重新扫描", command=self._run_scan,
            font=FONT, bg=SURFACE, fg=FG, relief=tk.FLAT, bd=4, padx=12,
        ).pack(side=tk.LEFT)

        if is_admin() and r["total_issues"] > 0:
            tk.Button(
                action_frame, text="一键修复全部", command=self._fix_all,
                font=FONT_BOLD, bg=GREEN, fg=BG, relief=tk.FLAT, bd=4, padx=12,
                cursor="hand2",
            ).pack(side=tk.RIGHT)
        elif not is_admin():
            tk.Label(
                action_frame,
                text="需要管理员权限才能修复",
                font=FONT_SMALL, bg=BG, fg=RED,
            ).pack(side=tk.RIGHT)

    def _add_issue_row(self, parent, issue):
        sev_colors = {"high": RED, "medium": ORANGE, "low": YELLOW}
        sev_icons = {"high": "  ", "medium": "  ", "low": "  "}
        color = sev_colors.get(issue.severity, MUTED)
        icon = sev_icons.get(issue.severity, "")

        row = tk.Frame(parent, bg=SURFACE)
        row.pack(fill=tk.X, pady=2, padx=2)

        left = tk.Frame(row, bg=SURFACE)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8, pady=4)

        tk.Label(
            left, text=f"{icon} {issue.title}", font=FONT_BOLD, bg=SURFACE, fg=color,
            anchor=tk.W, justify=tk.LEFT,
        ).pack(fill=tk.X)

        detail = f"当前: {issue.current_value} → {issue.recommended}"
        tk.Label(
            left, text=detail, font=FONT_SMALL, bg=SURFACE, fg=MUTED,
            anchor=tk.W, justify=tk.LEFT,
        ).pack(fill=tk.X)

    def _fix_all(self):
        if not self.scan_result:
            return

        issues = [i for i in self.scan_result["all_issues"] if i.fix_type != "manual"]
        if not issues:
            messagebox.showinfo("修复完成", "没有需要自动修复的项目。")
            return

        if not messagebox.askyesno("确认修复", f"将修复 {len(issues)} 项隐私设置，是否继续？"):
            return

        fixed, failed, skipped = fix_all(issues)

        msg = f"修复完成：成功 {fixed} 项"
        if failed > 0:
            msg += f"，失败 {failed} 项（可能因权限不足）"
        if skipped > 0:
            msg += f"，跳过 {skipped} 项（需手动处理）"

        messagebox.showinfo("修复结果", msg)
        self._run_scan()  # 重新扫描
