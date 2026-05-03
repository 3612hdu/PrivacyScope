"""
PrivacyScope Scanner - 扫描 Windows 隐私设置
读取注册表、服务状态、启动项，生成隐私评分报告。
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
    description: str
    severity: str  # high, medium, low
    current_value: str
    recommended: str
    fix_type: str = "manual"  # registry_dword, registry_delete, manual
    fix_key: str = ""
    fix_value_name: str = ""
    fix_value: int = 0


CATEGORIES = {
    "telemetry": "遥测与数据收集",
    "ads": "广告与追踪",
    "cortana": "Cortana 与搜索",
    "location": "位置服务",
    "apps": "应用权限",
    "updates": "更新与共享",
    "network": "网络与共享",
}


def _read_reg_dword(key_path: str, value_name: str) -> int | None:
    """读取注册表 DWORD 值"""
    try:
        hkey = winreg.HKEY_LOCAL_MACHINE
        # 也尝试 CURRENT_USER
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
    """读取注册表字符串值"""
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
    """扫描遥测与数据收集设置"""
    issues = []
    path = r"SOFTWARE\Policies\Microsoft\Windows\DataCollection"

    telemetry = _read_reg_dword(path, "AllowTelemetry")
    if telemetry is None:
        telemetry = _read_reg_dword(
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\DataCollection",
            "AllowTelemetry",
        )
    telemetry = telemetry if telemetry is not None else 3  # 默认=3 完全

    levels = {0: "安全(仅企业)", 1: "基本", 2: "增强", 3: "完整"}
    if telemetry >= 2:
        issues.append(PrivacyIssue(
            id="telemetry_level",
            category="telemetry",
            title="遥测级别过高",
            description=f"当前遥测级别: {levels.get(telemetry, '未知')}。Microsoft 会收集应用使用数据、浏览历史等。",
            severity="high" if telemetry == 3 else "medium",
            current_value=levels.get(telemetry, str(telemetry)),
            recommended="基本(1) — 仅发送安全数据",
            fix_type="registry_dword",
            fix_key=r"SOFTWARE\Policies\Microsoft\Windows\DataCollection",
            fix_value_name="AllowTelemetry",
            fix_value=1,
        ))

    # 允许发送设备数据给 Microsoft
    allow_device = _read_reg_dword(
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\DataCollection",
        "AllowDeviceNameInTelemetry",
    )
    if allow_device == 1 or allow_device is None:
        issues.append(PrivacyIssue(
            id="device_name_telemetry",
            category="telemetry",
            title="设备名称包含在遥测中",
            description="Microsoft 会收到你的设备名称作为遥测数据的一部分。",
            severity="low",
            current_value="允许" if allow_device == 1 else "默认(允许)",
            recommended="禁用",
            fix_type="registry_dword",
            fix_key=r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\DataCollection",
            fix_value_name="AllowDeviceNameInTelemetry",
            fix_value=0,
        ))

    return issues


def scan_advertising() -> list[PrivacyIssue]:
    """扫描广告与追踪设置"""
    issues = []
    path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\AdvertisingInfo"

    ad_id = _read_reg_dword(path, "Enabled")
    if ad_id is None or ad_id == 1:
        issues.append(PrivacyIssue(
            id="advertising_id",
            category="ads",
            title="广告 ID 已启用",
            description="Windows 使用广告 ID 跨应用追踪你的行为以投放个性化广告。",
            severity="medium",
            current_value="已启用" if ad_id == 1 else "默认(启用)",
            recommended="禁用 — 停止跨应用广告追踪",
            fix_type="registry_dword",
            fix_key=path,
            fix_value_name="Enabled",
            fix_value=0,
        ))

    # 应用启动追踪
    launch_tracking = _read_reg_dword(
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
        "Start_TrackProgs",
    )
    if launch_tracking is None or launch_tracking == 1:
        issues.append(PrivacyIssue(
            id="launch_tracking",
            category="ads",
            title="应用启动追踪已启用",
            description="Windows 会追踪你启动应用的频率和时间。",
            severity="low",
            current_value="已启用" if launch_tracking == 1 else "默认(启用)",
            recommended="禁用",
            fix_type="registry_dword",
            fix_key=r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
            fix_value_name="Start_TrackProgs",
            fix_value=0,
        ))

    # 量身定制的体验
    tailored = _read_reg_dword(
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Privacy",
        "TailoredExperiencesWithDiagnosticDataEnabled",
    )
    if tailored is None or tailored == 1:
        issues.append(PrivacyIssue(
            id="tailored_experiences",
            category="ads",
            title="量身定制的体验已启用",
            description="Microsoft 使用诊断数据向你展示定制建议和广告。",
            severity="medium",
            current_value="已启用" if tailored == 1 else "默认(启用)",
            recommended="禁用",
            fix_type="registry_dword",
            fix_key=r"SOFTWARE\Microsoft\Windows\CurrentVersion\Privacy",
            fix_value_name="TailoredExperiencesWithDiagnosticDataEnabled",
            fix_value=0,
        ))

    return issues


def scan_cortana() -> list[PrivacyIssue]:
    """扫描 Cortana 与搜索"""
    issues = []
    path = r"SOFTWARE\Policies\Microsoft\Windows\Windows Search"

    allow_search = _read_reg_dword(path, "AllowCortana")
    if allow_search is None:
        allow_search = _read_reg_dword(path, "AllowSearchToUseLocation")

    allow_cloud_search = _read_reg_dword(path, "ConnectedSearchUseWeb")
    if allow_cloud_search is None or allow_cloud_search == 1:
        issues.append(PrivacyIssue(
            id="cloud_search",
            category="cortana",
            title="云端搜索已启用",
            description="本地搜索会将你的查询发送到 Bing 云端。",
            severity="medium",
            current_value="已启用" if allow_cloud_search == 1 else "默认(启用)",
            recommended="禁用 — 仅本地搜索",
            fix_type="registry_dword",
            fix_key=path,
            fix_value_name="ConnectedSearchUseWeb",
            fix_value=0,
        ))

    return issues


def scan_location() -> list[PrivacyIssue]:
    """扫描位置服务"""
    issues = []

    path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\location"
    allow_location = _read_reg_dword(path, "Value")

    location_enabled = allow_location != "Deny"

    # 允许应用访问位置
    let_apps = _read_reg_dword(
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\location",
        "Value",
    )
    if let_apps != "Deny":
        issues.append(PrivacyIssue(
            id="location_service",
            category="location",
            title="位置服务已启用",
            description="Windows 和应用可以访问你的精确地理位置。",
            severity="high",
            current_value="允许" if location_enabled else "已禁用",
            recommended="禁用（除非你明确需要）",
            fix_type="registry_dword",
            fix_key=path,
            fix_value_name="Value",
            fix_value=0,
        ))

    return issues


def scan_startup() -> list[PrivacyIssue]:
    """扫描启动项/后台应用"""
    issues = []
    path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"

    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_READ)
        i = 0
        count = 0
        while True:
            try:
                winreg.EnumValue(key, i)
                count += 1
                i += 1
            except OSError:
                break
        winreg.CloseKey(key)

        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path, 0, winreg.KEY_READ)
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

        if count > 5:
            issues.append(PrivacyIssue(
                id="startup_programs",
                category="apps",
                title=f"启动项较多 ({count} 个)",
                description="较多的开机自启程序可能降低系统速度并增加隐私风险。",
                severity="medium" if count > 8 else "low",
                current_value=f"{count} 个启动项",
                recommended="审查并禁用不必要的启动项",
                fix_type="manual",
            ))
    except Exception:
        pass

    return issues


def scan_wifi_sense() -> list[PrivacyIssue]:
    """扫描 WiFi Sense 与网络共享"""
    issues = []

    wifi_sense = _read_reg_dword(
        r"SOFTWARE\Microsoft\PolicyManager\default\WiFi\AllowWiFiHotSpotReporting",
        "value",
    )
    if wifi_sense is None or wifi_sense == 1:
        issues.append(PrivacyIssue(
            id="wifi_sense",
            category="network",
            title="WiFi Sense 可能已启用",
            description="WiFi Sense 会与你的联系人共享 WiFi 密码。",
            severity="medium",
            current_value="可能启用",
            recommended="禁用 WiFi Sense",
            fix_type="registry_dword",
            fix_key=r"SOFTWARE\Microsoft\PolicyManager\default\WiFi\AllowWiFiHotSpotReporting",
            fix_value_name="value",
            fix_value=0,
        ))

    return issues


def scan_activity_history() -> list[PrivacyIssue]:
    """扫描活动历史记录"""
    issues = []

    activity = _read_reg_dword(
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System",
        "PublishUserActivities",
    )

    upload_activities = _read_reg_dword(
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System",
        "UploadUserActivities",
    )

    if activity is None or activity == 1:
        issues.append(PrivacyIssue(
            id="activity_history",
            category="telemetry",
            title="活动历史记录已启用",
            description="Windows 会记录你的应用使用活动，并可跨设备同步。",
            severity="medium",
            current_value="已启用" if activity == 1 else "默认(启用)",
            recommended="禁用",
            fix_type="registry_dword",
            fix_key=r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System",
            fix_value_name="PublishUserActivities",
            fix_value=0,
        ))

    return issues


def run_full_scan() -> dict:
    """执行完整隐私扫描"""
    all_issues = []
    all_issues.extend(scan_telemetry())
    all_issues.extend(scan_advertising())
    all_issues.extend(scan_cortana())
    all_issues.extend(scan_location())
    all_issues.extend(scan_startup())
    all_issues.extend(scan_wifi_sense())
    all_issues.extend(scan_activity_history())

    # 计算评分
    high = sum(1 for i in all_issues if i.severity == "high")
    medium = sum(1 for i in all_issues if i.severity == "medium")
    low = sum(1 for i in all_issues if i.severity == "low")

    # 满分 100，扣分制
    score = 100
    score -= high * 20
    score -= medium * 10
    score -= low * 3
    score = max(0, score)

    if score >= 80:
        grade, grade_color, grade_text = "A", "#a6e3a1", "优秀 — 你的隐私保护做得很好"
    elif score >= 60:
        grade, grade_color, grade_text = "B", "#f9e2af", "良好 — 仍有改进空间"
    elif score >= 40:
        grade, grade_color, grade_text = "C", "#fab387", "一般 — 建议优化"
    elif score >= 20:
        grade, grade_color, grade_text = "D", "#f38ba8", "较差 — 存在明显隐私风险"
    else:
        grade, grade_color, grade_text = "F", "#f38ba8", "危险 — 大量隐私数据在流出"

    return {
        "timestamp": datetime.now().isoformat(),
        "score": score,
        "grade": grade,
        "grade_color": grade_color,
        "grade_text": grade_text,
        "total_issues": len(all_issues),
        "high": high,
        "medium": medium,
        "low": low,
        "categories": {
            cat_id: {
                "name": cat_name,
                "count": sum(1 for i in all_issues if i.category == cat_id),
                "issues": [i for i in all_issues if i.category == cat_id],
            }
            for cat_id, cat_name in CATEGORIES.items()
        },
        "all_issues": all_issues,
    }


if __name__ == "__main__":
    result = run_full_scan()
    print(f"隐私评分: {result['score']}/100 (等级 {result['grade']})")
    print(f"发现 {result['total_issues']} 个问题: {result['high']}高 {result['medium']}中 {result['low']}低")
    print()
    for issue in result["all_issues"]:
        flag = {"high": "  ", "medium": "  ", "low": "  "}[issue.severity]
        print(f"  [{flag}] {issue.title}")
        print(f"      当前: {issue.current_value} → 建议: {issue.recommended}")
