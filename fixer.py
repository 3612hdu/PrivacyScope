"""
PrivacyScope Fixer v2 — 带撤销支持的注册表修复
"""
import winreg
import ctypes
import os
from scanner import PrivacyIssue
from undo_manager import UndoManager


def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def _set_registry_dword(fix_key: str, value_name: str, value: int) -> int | None:
    """
    写入注册表 DWORD，返回旧值。
    如果键不存在，返回 None（视为旧值=不存在）。
    """
    from scanner import _read_reg_dword
    old_value = _read_reg_dword(fix_key, value_name)

    for root in [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]:
        try:
            key = winreg.OpenKey(root, fix_key, 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, value_name, 0, winreg.REG_DWORD, value)
            winreg.CloseKey(key)
            return old_value
        except PermissionError:
            continue
        except FileNotFoundError:
            try:
                key = winreg.CreateKey(root, fix_key)
                winreg.SetValueEx(key, value_name, 0, winreg.REG_DWORD, value)
                winreg.CloseKey(key)
                return old_value
            except Exception:
                continue
    return None


def fix_issue(issue: PrivacyIssue, undo_mgr: UndoManager) -> bool:
    """修复单个问题，记录到 UndoManager"""
    if issue.fix_type != "registry_dword":
        return False

    old_value = _set_registry_dword(issue.fix_key, issue.fix_value_name, issue.fix_value)
    if old_value is not None:
        issue.original_value = old_value
        undo_mgr.record(
            issue_id=issue.id,
            title=issue.title,
            key_path=issue.fix_key,
            value_name=issue.fix_value_name,
            old_value=old_value if old_value is not None else -1,
            new_value=issue.fix_value,
        )
        return True

    # 如果 old_value 为 None（键不存在），尝试直接创建
    result = _set_registry_dword(issue.fix_key, issue.fix_value_name, issue.fix_value)
    if result is not None:
        undo_mgr.record(
            issue_id=issue.id,
            title=issue.title,
            key_path=issue.fix_key,
            value_name=issue.fix_value_name,
            old_value=-1,
            new_value=issue.fix_value,
        )
        return True
    return False


def fix_all(issues: list[PrivacyIssue], undo_mgr: UndoManager) -> tuple[int, int, int]:
    """批量修复，返回(成功, 失败, 跳过)"""
    fixed = 0
    failed = 0
    skipped = 0
    for issue in issues:
        if issue.fix_type == "manual" or issue.fix_type == "ms_settings":
            skipped += 1
            continue
        if fix_issue(issue, undo_mgr):
            fixed += 1
        else:
            failed += 1
    return fixed, failed, skipped


def undo_fix(record, undo_mgr) -> bool:
    """撤销单个修复"""
    if record.old_value == -1:
        # 键原本不存在，删除它
        for root in [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]:
            try:
                key = winreg.OpenKey(root, record.key_path, 0,
                                     winreg.KEY_SET_VALUE)
                winreg.DeleteValue(key, record.value_name)
                winreg.CloseKey(key)
                return True
            except (FileNotFoundError, PermissionError):
                continue
        return False
    result = _set_registry_dword(record.key_path, record.value_name, record.old_value)
    return result is not None
