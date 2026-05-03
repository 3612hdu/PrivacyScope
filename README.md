# PrivacyScope

**Windows 隐私设置仪表盘 — 让你看见数据流向，自己决定改什么。**

Windows 默认会将设备运行数据、活动历史、搜索词、位置信息等通过遥测系统上传给 Microsoft，同时生成广告 ID 供第三方应用追踪。大多数用户不知道这些开关在哪，也不知道关了多少。

PrivacyScope 扫描你的 Windows 隐私设置，用**中性语言**告诉你每项设置做什么、当前值是什么、有哪些可选值，然后——**把决定权交给你**。

---

## 能扫什么

| 类别 | 扫描项 | 说明 |
|------|--------|------|
| 遥测与诊断数据 | 诊断数据级别、活动历史记录 | 控制 Windows 向 Microsoft 发送多少设备使用数据 |
| 广告标识符 | 广告 ID、量身定制的体验 | 控制跨应用行为追踪和个性化广告 |
| 搜索与 Cortana | Web 搜索集成 | 控制开始菜单搜索是否同时查询 Bing |
| 位置服务 | 系统定位权限 | 控制应用能否获取你的精确地理位置 |
| 网络与共享 | Wi-Fi Sense | 控制是否与联系人共享 Wi-Fi 密码 |
| 应用权限与启动 | 开机自启程序 | 列出所有启动项，指引你去任务管理器审查 |

---

## 使用方法

```bash
# 安装依赖
pip install pywin32

# 普通扫描（查看所有设置）
python main.py

# 如需修复，右键 → 以管理员身份运行
```

### 操作指南

1. **开始扫描** — 点击按钮，扫描 6 大类 Windows 隐私设置
2. **查看详情** — 点击任意项目展开，阅读该项设置的中性描述
3. **跳转系统设置** — 点击「跳转到系统设置」直接打开对应 Windows 设置页面，手动调整
4. **一键修复**（管理员模式）— 点击「修复此项」自动修改注册表
5. **撤销** — 所有修改均可通过右上角「撤销」按钮一键恢复

---

## 原理

### 数据来源

所有设置均读取自 Windows 注册表。PrivacyScope 同时检查 `HKEY_LOCAL_MACHINE` 和 `HKEY_CURRENT_USER`，后者优先级更高（与 Windows 行为一致）。

### 扫描路径

| 设置 | 注册表路径 |
|------|-----------|
| 诊断数据级别 | `HKLM\SOFTWARE\Policies\Microsoft\Windows\DataCollection\AllowTelemetry` |
| 活动历史记录 | `HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System\PublishUserActivities` |
| 广告标识符 | `HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\AdvertisingInfo\Enabled` |
| 量身定制的体验 | `HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Privacy\TailoredExperiencesWithDiagnosticDataEnabled` |
| Web 搜索集成 | `HKLM\SOFTWARE\Policies\Microsoft\Windows\Windows Search\ConnectedSearchUseWeb` |
| 位置服务 | `HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\location\Value` |
| Wi-Fi Sense | `HKLM\SOFTWARE\Microsoft\PolicyManager\default\WiFi\AllowWiFiHotSpotReporting\value` |
| 开机自启程序 | `HKLM` + `HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Run` |

### 修复机制

修复操作使用 `winreg.SetValueEx` 写入注册表 DWORD 值。每次写入前记录原始值到 `undo_history.json`，撤销时通过 `winreg.DeleteValue`（键原本不存在）或写回旧值来恢复。

### Windows 设置跳转

每个扫描项对应一个 `ms-settings:` URI，通过 `subprocess.Popen(["start", uri], shell=True)` 打开 Windows 设置对应页面。所有 URI 均来自 [Microsoft 官方文档](https://docs.microsoft.com/en-us/windows/uwp/launch-resume/launch-settings-app)。

---

## 架构

```
privacyscope/
├── main.py              # 入口
├── scanner.py           # 注册表扫描，生成 PrivacyIssue 列表
├── fixer.py             # 注册表写入 + 撤销逻辑
├── undo_manager.py      # 修改记录持久化，支持回滚
├── gui.py               # tkinter 交互界面
├── undo_history.json    # 撤销记录（运行时生成）
├── tests/
│   ├── conftest.py
│   ├── test_scanner.py  # 数据模型 + 扫描结果测试
│   ├── test_fixer.py    # 修复逻辑 + UndoManager 测试
│   └── test_integration.py  # 完整工作流集成测试
└── README.md
```

### 数据模型

```python
@dataclass
class PrivacyIssue:
    id: str                # 唯一标识
    category: str          # 分类: telemetry/ads/cortana/location/apps/network
    title: str             # 设置名称
    description: str       # 中性描述：这个设置做什么
    current_state: str     # 当前值
    options: list[str]     # 可选的其他设置
    ms_settings_uri: str   # Windows 设置页面跳转链接
    fix_type: str          # registry_dword / ms_settings / manual
    fix_key: str           # 注册表路径
    fix_value_name: str    # 值名
    fix_value: int         # 推荐值
    original_value: int    # 原始值（撤销用）
```

### 设计原则

- **不评判**：不给用户打分、不分级、不标红黄绿。工具提供信息，用户做决定。
- **可逆**：每次修改记录原始值，支持一键撤销。
- **可验证**：所有代码可审计，MIT 开源。零网络请求，数据不出设备。
- **中立描述**：每项设置只说它做什么、有什么选项，不说"你该关掉它"。

---

## 开发

```bash
# 运行测试
python -m pytest tests/ -v

# 24 个测试覆盖：
# - 数据模型字段完整性
# - 扫描结果结构正确性
# - 中性描述（无恐吓词汇）
# - 修复逻辑 + 撤销回滚
# - UndoManager 持久化
# - 完整工作流集成测试
```

---

## 常见问题

**Q: 为什么有些设置显示「此项需在系统设置中手动调整」？**

A: 因为部分设置无法通过注册表直接控制（如开机自启程序），或涉及到需要用户自行判断的选择。我们提供跳转链接，帮你快速打开对应设置页面。

**Q: 修改注册表有风险吗？**

A: 所有修改仅涉及隐私相关的 DWORD 值，不涉及系统关键路径。每次修改记录原始值，可随时撤销。但始终建议在修改前了解每项设置的含义（这也是为什么我们写中性描述）。

**Q: 为什么不做成服务/常驻后台？**

A: PrivacyScope 是一次性扫描工具。你的隐私设置改好后就生效了，不需要持续运行。

---

## 延伸阅读

- [Windows 11 隐私深度解析](https://github.com/3612hdu/windows-privacy-guide) — 每项设置到底什么意思？数据去哪了？不含代码的知识整合。

## License

MIT
