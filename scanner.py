"""
PrivacyScope Scanner — 扫描 Windows 隐私设置
v2: 中性状态陈述 + Windows 设置跳转 + 无评分恐吓
"""
import winreg
import os
import subprocess
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class PrivacyIssue:
    id: str
    category: str
    title: str
    description: str                    # 中性描述：这个设置做什么
    current_state: str                  # 当前值
    options: list[str]                  # 可选的其他设置
    ms_settings_uri: str = ""          # Windows 设置页面跳转
    fix_type: str = "manual"            # registry_dword, ms_settings, service
    fix_key: str = ""
    fix_value_name: str = ""
    fix_value: int = 0
    original_value: int | None = None   # 撤销用


CATEGORIES = {
    "telemetry":     "遥测与诊断数据",
    "ads":           "广告标识符",
    "cortana":       "搜索与 Cortana",
    "location":      "位置服务",
    "apps":          "应用权限与启动",
    "updates":       "更新与传递优化",
    "network":       "网络与共享",
}


def _read_reg_dword(key_path: str, value_name: str) -> int | None:
    try:
        for root in [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]:
            try:
                key = winreg.OpenKey(root, key_path, 0, winreg.KEY_READ)
                value, _ = winreg.QueryValueEx(key, value_name)
                winreg.CloseKey(key)
                return value
            except FileNotFoundError:
                continue
        return None
    except Exception:
        return None


def _read_reg_string(key_path: str, value_name: str) -> str | None:
    try:
        for root in [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]:
            try:
                key = winreg.OpenKey(root, key_path, 0, winreg.KEY_READ)
                value, _ = winreg.QueryValueEx(key, value_name)
                winreg.CloseKey(key)
                return str(value)
            except FileNotFoundError:
                continue
        return None
    except Exception:
        return None


def scan_telemetry() -> list[PrivacyIssue]:
    issues = []
    path = r"SOFTWARE\Policies\Microsoft\Windows\DataCollection"

    telemetry = _read_reg_dword(path, "AllowTelemetry")
    if telemetry is None:
        telemetry = _read_reg_dword(
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\DataCollection",
            "AllowTelemetry",
        )
    telemetry = telemetry if telemetry is not None else 3

    levels = {0: "安全性(0)", 1: "基本(1)", 2: "增强(2)", 3: "完整(3)"}
    telemetry_explanations = {
        0: "仅发送安全相关数据（企业版独有选项）。",
        1: "发送基本设备数据：系统配置、是否正常运行、错误报告。不包含应用使用数据或浏览历史。",
        2: "在基本数据基础上，额外发送应用使用频率、联网状况等增强数据。",
        3: "在增强数据基础上，额外发送访问过的网站、应用使用详情等。这是默认设置。",
    }
    current_level_name = levels.get(telemetry, f"未知({telemetry})")

    issues.append(PrivacyIssue(
        id="telemetry_level",
        category="telemetry",
        title="诊断数据级别",
        description=f"Windows 会将设备运行数据发送给 Microsoft。当前设置为{current_level_name}。{telemetry_explanations.get(telemetry, '')}",
        current_state=current_level_name,
        options=["基本(1) — 仅发送安全数据与错误报告", "增强(2) — 额外发送使用统计", "完整(3) — 包含浏览和应用使用详情"],
        ms_settings_uri="ms-settings:privacy-feedback",
        fix_type="registry_dword",
        fix_key=r"SOFTWARE\Policies\Microsoft\Windows\DataCollection",
        fix_value_name="AllowTelemetry",
        fix_value=1,
        original_value=telemetry,
    ))

    # 活动历史
    activity = _read_reg_dword(
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System",
        "PublishUserActivities",
    )
    issues.append(PrivacyIssue(
        id="activity_history",
        category="telemetry",
        title="活动历史记录",
        description="Windows 会记录你打开过的应用、文件，并可跨设备同步这些活动历史。关闭后，历史记录仅存储在本地设备上，不会上传至 Microsoft 账户。",
        current_state="已启用" if activity == 1 else ("已禁用" if activity == 0 else "默认(启用)"),
        options=["禁用 — 活动历史仅保留在本地", "启用 — 可跨设备同步活动历史"],
        ms_settings_uri="ms-settings:privacy-activityhistory",
        fix_type="registry_dword",
        fix_key=r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System",
        fix_value_name="PublishUserActivities",
        fix_value=0,
        original_value=activity,
    ))

    return issues


def scan_advertising() -> list[PrivacyIssue]:
    issues = []
    path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\AdvertisingInfo"
    ad_id = _read_reg_dword(path, "Enabled")

    issues.append(PrivacyIssue(
        id="advertising_id",
        category="ads",
        title="广告标识符",
        description="Windows 为你的设备生成一个唯一的广告 ID。应用可以读取这个 ID 向你投放个性化广告。关闭后应用仍可能展示广告，但不再能跨应用追踪你的行为偏好。",
        current_state="已启用" if ad_id in (None, 1) else "已禁用",
        options=["禁用 — 停止跨应用广告追踪", "启用 — 允许个性化广告"],
        ms_settings_uri="ms-settings:privacy-general",
        fix_type="registry_dword",
        fix_key=path,
        fix_value_name="Enabled",
        fix_value=0,
        original_value=ad_id,
    ))

    # 量身定制的体验
    tailored = _read_reg_dword(
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Privacy",
        "TailoredExperiencesWithDiagnosticDataEnabled",
    )
    issues.append(PrivacyIssue(
        id="tailored_experiences",
        category="ads",
        title="量身定制的体验",
        description="Microsoft 会根据你的设备使用数据，在 Windows 提示、通知和建议中展示定制化内容。不涉及第三方广告，但会使用你的诊断数据。",
        current_state="已启用" if tailored in (None, 1) else "已禁用",
        options=["禁用 — 不根据使用数据定制系统建议", "启用 — 允许 Microsoft 提供定制建议"],
        ms_settings_uri="ms-settings:privacy-feedback",
        fix_type="registry_dword",
        fix_key=r"SOFTWARE\Microsoft\Windows\CurrentVersion\Privacy",
        fix_value_name="TailoredExperiencesWithDiagnosticDataEnabled",
        fix_value=0,
        original_value=tailored,
    ))

    return issues


def scan_cortana() -> list[PrivacyIssue]:
    issues = []
    path = r"SOFTWARE\Policies\Microsoft\Windows\Windows Search"
    cloud_search = _read_reg_dword(path, "ConnectedSearchUseWeb")

    issues.append(PrivacyIssue(
        id="cloud_search",
        category="cortana",
        title="Web 搜索集成",
        description="在开始菜单或搜索框中输入内容时，Windows 会同时将你的搜索词发送到 Bing。如果只希望搜索本地文件和应用，可以关闭此功能。",
        current_state="已启用" if cloud_search in (None, 1) else "已禁用",
        options=["禁用 — 搜索仅限本机文件和应用", "启用 — 搜索时同时查询 Bing 云端"],
        ms_settings_uri="ms-settings:search-permissions",
        fix_type="registry_dword",
        fix_key=path,
        fix_value_name="ConnectedSearchUseWeb",
        fix_value=0,
        original_value=cloud_search,
    ))

    return issues


def scan_location() -> list[PrivacyIssue]:
    issues = []
    path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\location"
    let_apps = _read_reg_dword(path, "Value")
    location_enabled = let_apps is None or let_apps != "Deny"

    issues.append(PrivacyIssue(
        id="location_service",
        category="location",
        title="位置服务",
        description="允许 Windows 和应用访问设备的精确地理位置（GPS 或基于 IP/WiFi 的定位）。部分应用（如天气、地图）依赖此功能。关闭后这些应用将使用默认位置或无法定位。",
        current_state="已启用" if location_enabled else "已禁用",
        options=["禁用 — 所有应用无法获取你的精确位置", "启用 — 允许应用请求位置权限"],
        ms_settings_uri="ms-settings:privacy-location",
        fix_type="registry_dword",
        fix_key=path,
        fix_value_name="Value",
        fix_value=0,
        original_value=let_apps,
    ))

    return issues


def scan_wifi_sense() -> list[PrivacyIssue]:
    issues = []
    wifi_sense = _read_reg_dword(
        r"SOFTWARE\Microsoft\PolicyManager\default\WiFi\AllowWiFiHotSpotReporting",
        "value",
    )

    issues.append(PrivacyIssue(
        id="wifi_sense",
        category="network",
        title="Wi-Fi Sense",
        description="Wi-Fi Sense 可与你的 Outlook、Skype 和 Facebook 联系人共享你连接过的 Wi-Fi 网络密码，同时自动连接他们分享的网络。",
        current_state="可能已启用" if wifi_sense in (None, 1) else "已禁用",
        options=["禁用 — 不自动共享 Wi-Fi 密码", "启用 — 与联系人共享密码并自动连接"],
        ms_settings_uri="ms-settings:network-wifi",
        fix_type="registry_dword",
        fix_key=r"SOFTWARE\Microsoft\PolicyManager\default\WiFi\AllowWiFiHotSpotReporting",
        fix_value_name="value",
        fix_value=0,
        original_value=wifi_sense,
    ))

    return issues


def scan_startup() -> list[PrivacyIssue]:
    issues = []
    path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
    count = 0

    try:
        for root in [winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE]:
            try:
                key = winreg.OpenKey(root, path, 0, winreg.KEY_READ)
                i = 0
                while True:
                    try:
                        winreg.EnumValue(key, i)
                        count += 1
                        i += 1
                    except OSError:
                        break
                winreg.CloseKey(key)
            except Exception:
                pass
    except Exception:
        pass

    issues.append(PrivacyIssue(
        id="startup_programs",
        category="apps",
        title="开机自启程序",
        description=f"当前检测到 {count} 个程序在系统启动时自动运行。较多的自启程序会延长开机时间并消耗后台资源。",
        current_state=f"{count} 个启动项",
        options=[f"通过任务管理器审查这 {count} 个程序", "每个程序都可以独立禁用"],
        ms_settings_uri="ms-settings:startupapps",
        fix_type="ms_settings",
    ))

    return issues


def run_full_scan() -> dict:
    """执行完整隐私扫描，返回中性状态报告"""
    all_issues = []
    all_issues.extend(scan_telemetry())
    all_issues.extend(scan_advertising())
    all_issues.extend(scan_cortana())
    all_issues.extend(scan_location())
    all_issues.extend(scan_wifi_sense())
    all_issues.extend(scan_startup())

    by_category = {}
    for issue in all_issues:
        if issue.category not in by_category:
            by_category[issue.category] = {"name": CATEGORIES.get(issue.category, issue.category), "count": 0, "issues": []}
        by_category[issue.category]["count"] += 1
        by_category[issue.category]["issues"].append(issue)

    total = len(all_issues)
    fixable = sum(1 for i in all_issues if i.fix_type == "registry_dword")

    return {
        "timestamp": datetime.now().isoformat(),
        "total_issues": total,
        "fixable_count": fixable,
        "manual_count": total - fixable,
        "categories": by_category,
        "all_issues": all_issues,
    }
