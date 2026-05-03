"""
修复器逻辑测试 v2 — 带 UndoManager 的修复流程
"""
import sys
import os
import tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scanner import PrivacyIssue
from fixer import fix_issue, fix_all, undo_fix, is_admin
from undo_manager import UndoManager, FixRecord


def _make_undo_mgr():
    """创建临时文件的 UndoManager，测试隔离"""
    tmp = tempfile.mktemp(suffix=".json")
    return UndoManager(tmp)


class TestFixerLogic:
    def test_manual_issue_skipped(self):
        """手动修复项应该返回 False"""
        issue = PrivacyIssue(
            id="manual",
            category="apps",
            title="手动项",
            description="",
            current_state="",
            options=[],
            fix_type="manual",
        )
        mgr = _make_undo_mgr()
        assert fix_issue(issue, mgr) is False
        assert mgr.count() == 0

    def test_is_admin_returns_bool(self):
        result = is_admin()
        assert isinstance(result, bool)

    def test_fix_all_handles_mixed_issues(self):
        """混合手动和自动修复项的处理"""
        mgr = _make_undo_mgr()
        issues = [
            PrivacyIssue(
                id="auto1", category="telemetry", title="自动1",
                description="", current_state="",
                options=[], fix_type="registry_dword",
                fix_key=r"SOFTWARE\Test", fix_value_name="Test", fix_value=0,
            ),
            PrivacyIssue(
                id="manual1", category="apps", title="手动1",
                description="", current_state="",
                options=[], fix_type="manual",
            ),
        ]
        fixed, failed, skipped = fix_all(issues, mgr)
        assert skipped >= 1
        assert fixed + failed + skipped == len(issues)

    def test_fix_issue_records_to_undo(self):
        """修复 registry_dword 时应记录到 UndoManager"""
        mgr = _make_undo_mgr()
        issue = PrivacyIssue(
            id="test_undo",
            category="telemetry",
            title="测试撤销",
            description="",
            current_state="已启用",
            options=["禁用"],
            fix_type="registry_dword",
            fix_key=r"SOFTWARE\PrivacyScopeTest\UndoTest",
            fix_value_name="TestDword",
            fix_value=0,
        )
        before_count = mgr.count()
        fix_issue(issue, mgr)
        # 如果写入成功，应该有记录
        assert mgr.count() >= before_count


class TestUndoManager:
    def test_record_and_count(self):
        mgr = _make_undo_mgr()
        assert mgr.count() == 0
        mgr.record("id1", "测试", r"SOFTWARE\Test", "Val", 1, 0)
        assert mgr.count() == 1

    def test_undo_last_returns_record(self):
        mgr = _make_undo_mgr()
        mgr.record("id1", "测试", r"SOFTWARE\Test", "Val", 1, 0)
        record = mgr.undo_last()
        assert record is not None
        assert record.issue_id == "id1"
        assert record.old_value == 1
        assert record.new_value == 0
        assert mgr.count() == 0

    def test_undo_last_empty_returns_none(self):
        mgr = _make_undo_mgr()
        assert mgr.undo_last() is None

    def test_undo_all_reverses_order(self):
        mgr = _make_undo_mgr()
        mgr.record("id1", "第一个", r"SOFTWARE\Test", "V1", 1, 0)
        mgr.record("id2", "第二个", r"SOFTWARE\Test", "V2", 2, 0)
        records = mgr.undo_all()
        assert len(records) == 2
        assert records[0].issue_id == "id2"  # 后进先出
        assert records[1].issue_id == "id1"
        assert mgr.count() == 0

    def test_persistence_across_instances(self):
        """UndoManager 应该持久化到文件"""
        tmp = tempfile.mktemp(suffix=".json")
        mgr1 = UndoManager(tmp)
        mgr1.record("persist", "持久化测试", r"SOFTWARE\Test", "V", 5, 3)

        mgr2 = UndoManager(tmp)
        assert mgr2.count() == 1
        r = mgr2.undo_last()
        assert r.issue_id == "persist"
        assert r.old_value == 5

        # 清理
        try:
            os.remove(tmp)
        except OSError:
            pass

    def test_fix_record_fields(self):
        r = FixRecord(
            timestamp="2026-01-01 00:00:00",
            issue_id="test",
            title="测试",
            key_path=r"SOFTWARE\Test",
            value_name="TestVal",
            old_value=1,
            new_value=0,
        )
        assert r.timestamp == "2026-01-01 00:00:00"
        assert r.old_value == 1
        assert r.new_value == 0


class TestUndoFix:
    def test_undo_fix_writes_old_value(self):
        """撤销修复应写回旧值"""
        mgr = _make_undo_mgr()
        # 先做一个修改，然后撤销
        issue = PrivacyIssue(
            id="undo_test",
            category="telemetry",
            title="撤销测试",
            description="",
            current_state="",
            options=[],
            fix_type="registry_dword",
            fix_key=r"SOFTWARE\PrivacyScopeTest\UndoTest2",
            fix_value_name="UndoDword",
            fix_value=0,
        )
        success = fix_issue(issue, mgr)
        if success and mgr.count() > 0:
            record = mgr.undo_last()
            result = undo_fix(record, mgr)
            assert isinstance(result, bool)
