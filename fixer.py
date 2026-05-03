"""
PrivacyScope Fixer - 修复 Windows 隐私设置
"""
import winreg
import ctypes
from scanner import PrivacyIssue


def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def fix_registry_dword(fix_key: str, value_name: str, value: int) -> bool:
    for root in [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]:
        try:
            key = winreg.OpenKey(root, fix_key, 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, value_name, 0, winreg.REG_DWORD, value)
            winreg.CloseKey(key)
            return True
        except PermissionError:
            continue
        except FileNotFoundError:
            try:
                key = winreg.CreateKey(root, fix_key)
                winreg.SetValueEx(key, value_name, 0, winreg.REG_DWORD, value)
                winreg.CloseKey(key)
                return True
            except Exception:
                continue
    return False


def fix_issue(issue: PrivacyIssue) -> bool:
    if issue.fix_type == "registry_dword":
        return fix_registry_dword(issue.fix_key, issue.fix_value_name, issue.fix_value)
    return False


def fix_all(issues: list[PrivacyIssue]) -> tuple[int, int, int]:
    """返回 (成功, 失败, 跳过)"""
    fixed = 0
    failed = 0
    skipped = 0
    for issue in issues:
        if issue.fix_type == "manual":
            skipped += 1
            continue
        if fix_issue(issue):
            fixed += 1
        else:
            failed += 1
    return fixed, failed, skipped
