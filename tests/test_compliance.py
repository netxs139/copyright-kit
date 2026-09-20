"""tests/test_compliance.py -- copyright-kit 开源合规与敏感信息拦截引擎单元测试。"""

from __future__ import annotations

from pathlib import Path
from scripts.verify_compliance import (
    REQUIRED_AUTHOR_EMAIL,
    REQUIRED_AUTHOR_NAME,
    check_commit_message_text,
    check_file_content_allowed,
    check_file_path_allowed,
    check_git_identity,
)


def test_allowed_commit_message():
    valid_msgs = [
        "feat(core): add docx export support",
        "fix(audit): resolve line counting discrepancy in header",
        "docs(readme): update installation guide and badges",
        "refactor(cli): simplify command-line argument parsing",
    ]
    for msg in valid_msgs:
        errs = check_commit_message_text(msg)
        assert len(errs) == 0, f"Expected valid message, but got errors: {errs}"


def test_forbidden_commit_message_keywords():
    bad_msgs = [
        "chore: update xushen profile",
        "fix: contact xushen@tjhq.com for details",
        "feat: integrate with TJHQ backend",
        "docs: 整理太极华青相关材料",
        "style: 修正太极样式",
        "refactor: 华青微服务改造",
    ]
    for msg in bad_msgs:
        errs = check_commit_message_text(msg)
        assert len(errs) > 0, f"Expected forbidden message to trigger error: {msg}"
        assert any("COMMIT-MSG-SENSITIVE" in e for e in errs)


def test_forbidden_file_paths():
    bad_paths = [
        "docs/history/session-history.log",
        "session-history.log",
        "docs/history/test.txt",
    ]
    for path in bad_paths:
        errs = check_file_path_allowed(path)
        assert len(errs) > 0, f"Expected forbidden path to trigger error: {path}"
        assert any("FORBIDDEN-FILE" in e for e in errs)

    good_paths = [
        "scripts/export_copyright_source.py",
        "README.md",
        "pyproject.toml",
        "templates/user_manual_template.md",
    ]
    for path in good_paths:
        errs = check_file_path_allowed(path)
        assert len(errs) == 0, f"Expected allowed path, but got errors: {errs}"


def test_clean_file_content():
    dummy_file = Path("test_dummy.py")
    clean_code = """
def calculate_sloc(lines: list[str]) -> int:
    return len([line for line in lines if line.strip() and not line.startswith('#')])
"""
    errs = check_file_content_allowed(dummy_file, clean_code)
    assert len(errs) == 0


def test_sensitive_file_content():
    dummy_file = Path("test_dummy.py")
    sensitive_code = """
# Author: xushen <xushen@tjhq.com>
# TJHQ Corporation All Rights Reserved.
# 太极华青开源组件
"""
    errs = check_file_content_allowed(dummy_file, sensitive_code)
    assert len(errs) > 0
    assert any("CONTENT-SENSITIVE" in e for e in errs)


def test_current_git_identity():
    repo_root = Path(__file__).resolve().parent.parent
    errs = check_git_identity(repo_root)
    assert len(errs) == 0, f"Git identity must be clean: {errs}"
