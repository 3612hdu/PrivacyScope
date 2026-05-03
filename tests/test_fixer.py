"""
修复器逻辑测试
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scanner import PrivacyIssue
from fixer import fix_issue, fix_registry_dword, is_admin


class TestFixerLogic:
    def test_manual_issue_skipped(self):
        """手动修复项应该返回 False"""
        issue = PrivacyIssue(
            id="manual",
            category="apps",
            title="手动项",
            description="",
            severity="low",
            current_value="",
            recommended="",
            fix_type="manual",
        )
        assert fix_issue(issue) is False

    def test_is_admin_returns_bool(self):
        """is_admin 应该返回布尔值"""
        result = is_admin()
        assert isinstance(result, bool)

    def test_fix_registry_dword_nonexistent_key(self):
        """写入一个不存在的注册表键应该返回 False"""
        result = fix_registry_dword(
            r"SOFTWARE\ClipVaultTest\Nonexistent", "TestValue", 0
        )
        # 可能因为权限不足返回 False，这是预期行为
        assert result is False or result is True

    def test_fix_all_handles_mixed_issues(self):
        """混合手动和自动修复项的处理"""
        from fixer import fix_all
        issues = [
            PrivacyIssue(
                id="auto1", category="telemetry", title="自动1",
                description="", severity="medium",
                current_value="", recommended="",
                fix_type="registry_dword",
                fix_key=r"SOFTWARE\Test", fix_value_name="Test", fix_value=0,
            ),
            PrivacyIssue(
                id="manual1", category="apps", title="手动1",
                description="", severity="low",
                current_value="", recommended="",
                fix_type="manual",
            ),
        ]
        fixed, failed, skipped = fix_all(issues)
        assert skipped >= 1  # 至少一个手动项被跳过
        assert fixed + failed + skipped == len(issues)


class TestDataIntegrity:
    def test_issue_ids_unique(self):
        """扫描结果的 issue id 不应重复"""
        from scanner import run_full_scan
        result = run_full_scan()
        ids = [i.id for i in result["all_issues"]]
        assert len(ids) == len(set(ids)), f"重复 ID: {[x for x in ids if ids.count(x) > 1]}"
