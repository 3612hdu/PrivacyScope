"""
扫描器逻辑测试 v2 — 中性数据模型，无评分/等级
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scanner import PrivacyIssue, run_full_scan, CATEGORIES


class TestPrivacyIssue:
    def test_dataclass_fields(self):
        issue = PrivacyIssue(
            id="test_id",
            category="telemetry",
            title="测试标题",
            description="中性描述：这个设置做什么",
            current_state="已启用",
            options=["禁用", "启用"],
            ms_settings_uri="ms-settings:privacy-feedback",
            fix_type="registry_dword",
            fix_key=r"SOFTWARE\Test",
            fix_value_name="TestValue",
            fix_value=0,
            original_value=1,
        )
        assert issue.id == "test_id"
        assert issue.description == "中性描述：这个设置做什么"
        assert issue.current_state == "已启用"
        assert issue.options == ["禁用", "启用"]
        assert issue.ms_settings_uri == "ms-settings:privacy-feedback"
        assert issue.fix_type == "registry_dword"
        assert issue.fix_value_name == "TestValue"
        assert issue.original_value == 1

    def test_default_fix_type_is_manual(self):
        issue = PrivacyIssue(
            id="manual_issue",
            category="ads",
            title="需要手动处理",
            description="无法自动修复",
            current_state="N/A",
            options=["手动检查"],
        )
        assert issue.fix_type == "manual"
        assert issue.ms_settings_uri == ""
        assert issue.fix_key == ""
        assert issue.fix_value == 0
        assert issue.original_value is None

    def test_options_is_list(self):
        issue = PrivacyIssue(
            id="test",
            category="network",
            title="测试",
            description="",
            current_state="",
            options=["选项A", "选项B"],
        )
        assert isinstance(issue.options, list)
        assert len(issue.options) == 2


class TestScanResult:
    def test_result_has_required_fields(self):
        result = run_full_scan()
        required = ["timestamp", "total_issues", "fixable_count",
                    "manual_count", "categories", "all_issues"]
        for field in required:
            assert field in result, f"缺少字段: {field}"

    def test_no_score_or_grade(self):
        """v2 不应包含评分或等级字段"""
        result = run_full_scan()
        assert "score" not in result
        assert "grade" not in result
        assert "grade_color" not in result
        assert "grade_text" not in result
        assert "high" not in result
        assert "medium" not in result
        assert "low" not in result

    def test_counts_consistent(self):
        result = run_full_scan()
        assert result["fixable_count"] + result["manual_count"] == result["total_issues"]

    def test_all_categories_present(self):
        result = run_full_scan()
        # 只验证有 issue 的分类存在（不是所有 CATEGORIES 都有扫描项）
        found_cats = set(result["categories"].keys())
        assert found_cats, "至少应有一个分类"
        for cat_id in found_cats:
            assert cat_id in CATEGORIES, f"未知分类: {cat_id}"
            cat = result["categories"][cat_id]
            assert "name" in cat
            assert "count" in cat
            assert cat["count"] > 0
            assert "issues" in cat
            assert len(cat["issues"]) == cat["count"]

    def test_issues_well_formed(self):
        result = run_full_scan()
        for issue in result["all_issues"]:
            assert isinstance(issue, PrivacyIssue)
            assert issue.id
            assert issue.category in CATEGORIES
            assert issue.title
            assert isinstance(issue.description, str) and len(issue.description) > 0
            assert isinstance(issue.current_state, str)
            assert isinstance(issue.options, list)
            assert issue.fix_type in ("registry_dword", "ms_settings", "manual", "service")

    def test_issue_ids_unique(self):
        result = run_full_scan()
        ids = [i.id for i in result["all_issues"]]
        assert len(ids) == len(set(ids)), f"重复 ID: {[x for x in ids if ids.count(x) > 1]}"

    def test_issues_have_neutral_description(self):
        """描述应为中性状态陈述，不含恐吓性语言"""
        result = run_full_scan()
        fear_words = ["危险", "严重", "警告", "泄露", "攻击", "恶意"]
        for issue in result["all_issues"]:
            for word in fear_words:
                assert word not in issue.description, \
                    f"Issue {issue.id} 包含恐吓性词汇: {word}"

    def test_ms_settings_uri_populated_for_registry_issues(self):
        """registry_dword 类型的 issue 应该有 ms_settings_uri"""
        result = run_full_scan()
        for issue in result["all_issues"]:
            if issue.fix_type == "registry_dword":
                assert issue.ms_settings_uri, \
                    f"registry_dword issue {issue.id} 缺少 ms_settings_uri"
