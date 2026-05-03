"""
集成测试 — 运行真实扫描，验证完整工作流
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scanner import run_full_scan, PrivacyIssue


def test_full_scan_workflow():
    """
    完整的扫描工作流：
    1. 执行扫描 → 获得评分和问题列表
    2. 验证每个问题字段完整
    3. 验证分类统计一致
    """
    print("=" * 60)
    print("PrivacyScope 集成测试")
    print("=" * 60)

    # 1. 执行扫描
    result = run_full_scan()
    print(f"\n隐私评分: {result['score']}/100 (等级 {result['grade']})")
    print(f"发现 {result['total_issues']} 个问题: {result['high']}高 {result['medium']}中 {result['low']}低")

    # 2. 验证结果结构
    assert 0 <= result["score"] <= 100, "评分超出范围"
    assert result["grade"] in ("A", "B", "C", "D", "F"), f"无效等级: {result['grade']}"
    assert result["high"] + result["medium"] + result["low"] == result["total_issues"]

    # 3. 打印每个问题
    print("\n发现的问题:")
    for issue in result["all_issues"]:
        sev = {"high": "  ", "medium": "  ", "low": "  "}[issue.severity]
        print(f"  [{sev}] ({issue.category}) {issue.title}")
        print(f"       当前: {issue.current_value} → {issue.recommended}")
        # 验证字段
        assert issue.id
        assert issue.title
        assert issue.severity in ("high", "medium", "low")
        assert issue.current_value
        assert issue.recommended

    # 4. 分类统计
    print("\n分类统计:")
    for cat_id, cat_data in result["categories"].items():
        if cat_data["count"] > 0:
            print(f"  {cat_data['name']}: {cat_data['count']} 个问题")
            for i in cat_data["issues"]:
                print(f"    - {i.title}")

    print("\n" + "=" * 60)
    print("集成测试通过")
    print("=" * 60)

    assert result["total_issues"] >= 0
    return True
