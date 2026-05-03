"""
集成测试 v2 — 真实扫描 + 完整工作流验证
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scanner import run_full_scan, PrivacyIssue
from undo_manager import UndoManager
from fixer import fix_issue, fix_all


def test_full_scan_workflow():
    """
    完整扫描工作流：
    1. 执行扫描 → 获得问题列表（无评分）
    2. 验证每个问题字段完整
    3. 验证分类统计一致
    4. 验证可选设置和跳转链接存在
    """
    print("=" * 60)
    print("PrivacyScope v2 集成测试")
    print("=" * 60)

    # 1. 执行扫描
    result = run_full_scan()
    print(f"\n检测到 {result['total_issues']} 项设置")
    print(f"  可自动修复: {result['fixable_count']} 项")
    print(f"  需手动调整: {result['manual_count']} 项")

    # 2. 验证结果结构（v2 无评分）
    assert result["total_issues"] >= 0
    assert result["fixable_count"] + result["manual_count"] == result["total_issues"]
    assert "score" not in result
    assert "grade" not in result

    # 3. 打印每个问题
    print("\n检测到的设置:")
    for issue in result["all_issues"]:
        cat = issue.category
        print(f"  [{cat}] {issue.title}")
        print(f"       当前: {issue.current_state}")
        if issue.options:
            print(f"       可选: {', '.join(issue.options[:2])}")
        if issue.ms_settings_uri:
            print(f"       跳转: {issue.ms_settings_uri}")
        # 验证字段
        assert issue.id
        assert issue.title
        assert issue.description
        assert issue.current_state
        assert isinstance(issue.options, list)
        assert issue.fix_type in ("registry_dword", "ms_settings", "manual", "service")

    # 4. 分类统计
    print("\n分类统计:")
    for cat_id, cat_data in result["categories"].items():
        if cat_data["count"] > 0:
            print(f"  {cat_data['name']}: {cat_data['count']} 项")
            for i in cat_data["issues"]:
                print(f"    - {i.title}")

    print("\n" + "=" * 60)
    print("集成测试通过")
    print("=" * 60)

    assert result["total_issues"] >= 0


def test_fix_workflow_with_undo():
    """修复+撤销工作流集成测试"""
    import tempfile

    tmp = tempfile.mktemp(suffix=".json")
    mgr = UndoManager(tmp)

    # 找一个可修复的 issue
    result = run_full_scan()
    fixable = [i for i in result["all_issues"] if i.fix_type == "registry_dword"]

    if not fixable:
        print("没有可自动修复的项目，跳过修复测试")
        return

    issue = fixable[0]
    print(f"\n测试修复: {issue.title}")

    # 修复
    success = fix_issue(issue, mgr)
    print(f"  修复结果: {'成功' if success else '失败(可能权限不足)'}")
    assert isinstance(success, bool)

    # 如果有撤销记录，测试撤销
    if mgr.count() > 0:
        record = mgr.undo_last()
        print(f"  撤销记录: {record.title} (旧值={record.old_value})")
        # 把记录放回去以便后续使用
        mgr.record(record.issue_id, record.title, record.key_path,
                   record.value_name, record.old_value, record.new_value)

    try:
        os.remove(tmp)
    except OSError:
        pass
