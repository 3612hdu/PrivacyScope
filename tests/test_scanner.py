"""
扫描器逻辑测试 — 数据结构、评分算法、输出格式
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
            description="测试描述",
            severity="high",
            current_value="启用",
            recommended="禁用",
            fix_type="registry_dword",
            fix_key=r"SOFTWARE\Test",
            fix_value_name="TestValue",
            fix_value=0,
        )
        assert issue.id == "test_id"
        assert issue.severity == "high"
        assert issue.fix_type == "registry_dword"
        assert issue.fix_value_name == "TestValue"

    def test_default_fix_type_is_manual(self):
        issue = PrivacyIssue(
            id="manual_issue",
            category="ads",
            title="需要手动处理",
            description="无法自动修复",
            severity="low",
            current_value="N/A",
            recommended="手动检查",
        )
        assert issue.fix_type == "manual"


class TestScanResult:
    def test_result_has_required_fields(self):
        result = run_full_scan()
        required = ["timestamp", "score", "grade", "grade_color", "grade_text",
                    "total_issues", "high", "medium", "low", "categories", "all_issues"]
        for field in required:
            assert field in result, f"缺少字段: {field}"

    def test_score_range(self):
        result = run_full_scan()
        assert 0 <= result["score"] <= 100, f"评分超出范围: {result['score']}"

    def test_grade_matches_score(self):
        result = run_full_scan()
        score = result["score"]
        if score >= 80:
            assert result["grade"] == "A"
        elif score >= 60:
            assert result["grade"] == "B"
        elif score >= 40:
            assert result["grade"] == "C"
        elif score >= 20:
            assert result["grade"] == "D"
        else:
            assert result["grade"] == "F"

    def test_counts_consistent(self):
        result = run_full_scan()
        assert result["high"] + result["medium"] + result["low"] == result["total_issues"]

    def test_all_categories_present(self):
        result = run_full_scan()
        for cat_id in CATEGORIES:
            assert cat_id in result["categories"], f"缺少分类: {cat_id}"
            cat = result["categories"][cat_id]
            assert "name" in cat
            assert "count" in cat
            assert "issues" in cat

    def test_issues_well_formed(self):
        result = run_full_scan()
        for issue in result["all_issues"]:
            assert isinstance(issue, PrivacyIssue)
            assert issue.id
            assert issue.category in CATEGORIES
            assert issue.severity in ("high", "medium", "low")
            assert issue.title
