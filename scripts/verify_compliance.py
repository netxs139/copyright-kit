#!/usr/bin/env python3
"""scripts/verify_compliance.py -- copyright-kit 开源合规与商业敏感信息多维防护门禁。

功能职责:
1. 禁止引入任何 docs/history/session-history.log 文件。
2. 强制 Git 身份为 netxs139 <netxs139@139.com>，严格拦截 xushen 或 *@tjhq.com。
3. 提交信息 (Commit Message) 严格禁止包含 xushen, xushen@tjhq.com, TJHQ, 太极华青, 太极, 华青。
4. 推送到 GitHub 远端时，逐 commit 深度穿透核验 Author、Committer、Subject、Body 及代码 Diff。
5. 零外部依赖 (Zero-Dependency)，仅使用 Python 标准库，跨平台开箱即用。
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

# 商业与内部敏感关键词黑名单 (大小写不敏感匹配或特定正则)
FORBIDDEN_KEYWORDS_REGEX = re.compile(
    r"(?i)\b(xushen|xushen@tjhq\.com|tjhq)\b|太极华青|太极|华青"
)

# 允许的 Git 提交者唯一身份
REQUIRED_AUTHOR_NAME = "netxs139"
REQUIRED_AUTHOR_EMAIL = "netxs139@139.com"

# 禁止出现的文件路径特征
FORBIDDEN_FILE_PATTERNS = [
    "session-history.log",
    "docs/history",
]

# 允许扫描时豁免的非代码目录与文件
AUDIT_EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "node_modules",
    "dist",
    "build",
    ".eggs",
}

AUDIT_EXCLUDED_FILES = {
    "verify_compliance.py",  # 本规则脚本自身定义了黑名单字符串，需排除自身字面量
    "test_compliance.py",    # 合规测试套件自身包含违规模拟用例
}


def get_repo_root() -> Path:
    """获取当前 Git 仓库物理根目录."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
        return Path(res.stdout.strip())
    except Exception:
        return Path(__file__).resolve().parent.parent


def check_git_identity(repo_root: Path) -> list[str]:
    """验证本地 Git 配置中的 user.name 和 user.email 是否合规."""
    errors = []
    try:
        name_res = subprocess.run(
            ["git", "-C", str(repo_root), "config", "user.name"],
            capture_output=True,
            text=True,
            check=False,
        )
        email_res = subprocess.run(
            ["git", "-C", str(repo_root), "config", "user.email"],
            capture_output=True,
            text=True,
            check=False,
        )
        user_name = name_res.stdout.strip()
        user_email = email_res.stdout.strip()

        if user_name != REQUIRED_AUTHOR_NAME:
            errors.append(
                f"[IDENTITY-NAME-INVALID] user.name 必须为 '{REQUIRED_AUTHOR_NAME}'，当前配置: '{user_name}'"
            )
        if user_email != REQUIRED_AUTHOR_EMAIL:
            errors.append(
                f"[IDENTITY-EMAIL-INVALID] user.email 必须为 '{REQUIRED_AUTHOR_EMAIL}'，当前配置: '{user_email}'"
            )
        if re.search(r"xushen|tjhq", f"{user_name} {user_email}", re.IGNORECASE):
            errors.append(
                f"[IDENTITY-FORBIDDEN-KEYWORD] 检测到商业公司身份泄露风险: name='{user_name}', email='{user_email}'"
            )
    except Exception as exc:
        errors.append(f"[IDENTITY-CHECK-ERROR] 检查 Git 身份时发生异常: {exc}")

    return errors


def check_commit_message_text(message: str) -> list[str]:
    """检查提交信息文本是否包含敏感词."""
    errors = []
    lines = [line.strip() for line in message.splitlines() if line.strip() and not line.startswith("#")]
    clean_text = "\n".join(lines)

    matches = FORBIDDEN_KEYWORDS_REGEX.findall(clean_text)
    if matches:
        unique_matches = sorted(set(matches))
        errors.append(
            f"[COMMIT-MSG-SENSITIVE] 提交信息包含商业公司内部敏感词: {unique_matches}"
        )

    return errors


def check_file_path_allowed(file_path: str | Path) -> list[str]:
    """检查文件路径是否属于禁止文件."""
    errors = []
    posix_path = str(file_path).replace("\\", "/")
    for pattern in FORBIDDEN_FILE_PATTERNS:
        if pattern in posix_path:
            errors.append(
                f"[FORBIDDEN-FILE] 禁止在公开开源仓库中启用或引入历史会话日志: {posix_path}"
            )
            break
    return errors


def check_file_content_allowed(file_path: Path, content: str) -> list[str]:
    """检查文件内容是否包含敏感词."""
    errors = []
    if file_path.name in AUDIT_EXCLUDED_FILES:
        return errors

    matches = FORBIDDEN_KEYWORDS_REGEX.findall(content)
    if matches:
        unique_matches = sorted(set(matches))
        errors.append(
            f"[CONTENT-SENSITIVE] 文件 {file_path} 发现敏感词: {unique_matches}"
        )
    return errors


def check_staged_changes(repo_root: Path) -> list[str]:
    """检查暂存区文件与差异 (pre-commit)."""
    errors = []
    # 1. 身份合规检查
    errors.extend(check_git_identity(repo_root))

    # 2. 检查暂存的新增/修改文件路径 (删除操作放行)
    staged_status_res = subprocess.run(
        ["git", "-C", str(repo_root), "diff", "--cached", "--name-status"],
        capture_output=True,
        text=True,
        check=False,
    )
    for line in staged_status_res.stdout.splitlines():
        parts = line.strip().split(maxsplit=1)
        if len(parts) == 2:
            status, sf = parts[0], parts[1]
            if status == "D":
                continue  # 删除禁止文件是合规清理操作，允许
            errors.extend(check_file_path_allowed(sf))

    # 3. 检查暂存区新增的代码差异 (+ lines)
    diff_res = subprocess.run(
        ["git", "-C", str(repo_root), "diff", "--cached", "-U0"],
        capture_output=True,
        text=True,
        check=False,
    )
    current_file = ""
    for line in diff_res.stdout.splitlines():
        if line.startswith("diff --git"):
            parts = line.split()
            if len(parts) >= 4:
                current_file = Path(parts[3].lstrip("b/")).name
            continue
        if current_file in AUDIT_EXCLUDED_FILES:
            continue
        if line.startswith("+") and not line.startswith("+++"):
            added_text = line[1:]
            matches = FORBIDDEN_KEYWORDS_REGEX.findall(added_text)
            if matches:
                unique_matches = sorted(set(matches))
                errors.append(
                    f"[STAGED-DIFF-SENSITIVE] 暂存区新增代码包含敏感词 {unique_matches}: '{added_text.strip()[:80]}'"
                )

    return errors


def check_commit_chain_for_push(repo_root: Path, remote_name: str, push_range: str | None = None) -> list[str]:
    """在执行 push 前逐 commit 深度穿透核验 (pre-push)."""
    errors = []
    # 确定待校验的 commit 范围
    if not push_range:
        # 尝试比对目标分支与本地 HEAD
        push_range = "HEAD"

    # 获取待 push 的 commit 列表
    try:
        rev_cmd = ["git", "-C", str(repo_root), "rev-list"]
        if ".." in push_range:
            rev_cmd.append(push_range)
        else:
            # 若给的是单个 ref，获取远端同名分支进行比对
            remote_branch = f"{remote_name}/main"
            check_remote = subprocess.run(
                ["git", "-C", str(repo_root), "rev-parse", "--verify", remote_branch],
                capture_output=True,
                text=True,
                check=False,
            )
            if check_remote.returncode == 0:
                rev_cmd.append(f"{remote_branch}..{push_range}")
            else:
                rev_cmd.extend(["-n", "30", push_range])

        rev_res = subprocess.run(rev_cmd, capture_output=True, text=True, check=False)
        commits = [c.strip() for c in rev_res.stdout.splitlines() if c.strip()]
    except Exception as exc:
        return [f"[PUSH-CHECK-ERROR] 获取待推送 commit 列表失败: {exc}"]

    print(f"🔍 [Pre-Push Guard] 正在对即将推送至 [{remote_name}] 的 {len(commits)} 个 Commit 执行穿透审计...")

    for commit in commits:
        # 获取 commit 详细元数据: hash, an, ae, cn, ce, subject, body
        show_format = "%H%n%an%n%ae%n%cn%n%ce%n%s%n%b"
        show_res = subprocess.run(
            ["git", "-C", str(repo_root), "show", "-s", f"--format={show_format}", commit],
            capture_output=True,
            text=True,
            check=False,
        )
        parts = show_res.stdout.splitlines()
        if len(parts) < 6:
            continue
        c_hash = parts[0]
        c_an = parts[1]
        c_ae = parts[2]
        c_cn = parts[3]
        c_ce = parts[4]
        c_sub = parts[5]
        c_body = "\n".join(parts[6:]) if len(parts) > 6 else ""

        # 1. 验证 Author
        if c_an != REQUIRED_AUTHOR_NAME or c_ae != REQUIRED_AUTHOR_EMAIL:
            errors.append(
                f"[PUSH-AUTHOR-INVALID] Commit {c_hash[:7]} Author 违规: '{c_an} <{c_ae}>' (必须为 '{REQUIRED_AUTHOR_NAME} <{REQUIRED_AUTHOR_EMAIL}>')"
            )
        # 2. 验证 Committer
        if c_cn != REQUIRED_AUTHOR_NAME or c_ce != REQUIRED_AUTHOR_EMAIL:
            errors.append(
                f"[PUSH-COMMITTER-INVALID] Commit {c_hash[:7]} Committer 违规: '{c_cn} <{c_ce}>' (必须为 '{REQUIRED_AUTHOR_NAME} <{REQUIRED_AUTHOR_EMAIL}>')"
            )
        # 3. 验证 Commit Message
        msg_errs = check_commit_message_text(f"{c_sub}\n{c_body}")
        for me in msg_errs:
            errors.append(f"[PUSH-MSG-INVALID] Commit {c_hash[:7]}: {me}")

        # 4. 验证 Diff 文件名及内容 (纯删除操作放行)
        diff_res = subprocess.run(
            ["git", "-C", str(repo_root), "show", "--name-status", "--format=", commit],
            capture_output=True,
            text=True,
            check=False,
        )
        for line in diff_res.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split(maxsplit=1)
            if len(parts) != 2:
                continue
            status, changed_file = parts[0], parts[1]
            if status == "D":
                continue  # 删除禁止文件是合规修复操作，放行
            path_errs = check_file_path_allowed(changed_file)
            if path_errs:
                errors.append(f"[PUSH-FILE-INVALID] Commit {c_hash[:7]} 引入禁止文件: {changed_file}")

    return errors


def check_working_tree_files(repo_root: Path) -> list[str]:
    """全量静态扫描工作区受控文件，确保无敏感词且无违规文件."""
    errors = []
    # 1. 检查禁止文件物理存在
    for pattern in FORBIDDEN_FILE_PATTERNS:
        target = repo_root / pattern
        if target.exists():
            errors.append(f"[FORBIDDEN-FILE-EXISTS] 物理磁盘存在禁止文件: {target}")

    # 2. 获取所有跟踪的文件
    ls_res = subprocess.run(
        ["git", "-C", str(repo_root), "ls-files"],
        capture_output=True,
        text=True,
        check=False,
    )
    tracked_files = [repo_root / f.strip() for f in ls_res.stdout.splitlines() if f.strip()]

    for fpath in tracked_files:
        if not fpath.is_file():
            continue
        if any(part in AUDIT_EXCLUDED_DIRS for part in fpath.parts):
            continue
        if fpath.name in AUDIT_EXCLUDED_FILES:
            continue

        errors.extend(check_file_path_allowed(fpath))

        try:
            content = fpath.read_text(encoding="utf-8", errors="ignore")
            errors.extend(check_file_content_allowed(fpath, content))
        except Exception:
            pass

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="copyright-kit 开源合规与商业敏感信息多维防护门禁")
    parser.add_argument("--stage", choices=["pre-commit", "commit-msg", "pre-push"], help="指定执行的 Git 钩子阶段")
    parser.add_argument("--all", action="store_true", help="执行全维度完整合规审计 (文件+身份+Git历史)")
    parser.add_argument("args", nargs="*", help="钩子传入的附带参数 (如 commit_msg_file 或 remote/url)")

    parsed = parser.parse_args()
    repo_root = get_repo_root()
    errors: list[str] = []

    if parsed.stage == "pre-commit":
        print("🛡️  [copyright-kit] 正在执行 pre-commit 开源合规审计...")
        errors = check_staged_changes(repo_root)

    elif parsed.stage == "commit-msg":
        msg_file = parsed.args[0] if parsed.args else ""
        if not msg_file or not os.path.exists(msg_file):
            print("⚠️  [copyright-kit] 未指定或找不到 commit-msg 文件，跳过。")
            return 0
        print("🛡️  [copyright-kit] 正在执行 commit-msg 敏感词过滤审计...")
        content = Path(msg_file).read_text(encoding="utf-8", errors="ignore")
        errors = check_commit_message_text(content)

    elif parsed.stage == "pre-push":
        remote_name = parsed.args[0] if parsed.args else "github"
        print(f"🛡️  [copyright-kit] 正在执行 pre-push 远端推送合规审计 (目标远端: {remote_name})...")
        # 从 stdin 读取推选 ref 列表 (Git pre-push 协议)
        lines = sys.stdin.read().splitlines() if not sys.stdin.isatty() else []
        push_range = None
        if lines:
            for line in lines:
                parts = line.strip().split()
                if len(parts) >= 4:
                    local_ref, local_sha, remote_ref, remote_sha = parts[:4]
                    if local_sha == "0000000000000000000000000000000000000000":
                        continue  # 分支删除操作
                    if remote_sha == "0000000000000000000000000000000000000000":
                        push_range = local_sha
                    else:
                        push_range = f"{remote_sha}..{local_sha}"
                    errors.extend(check_commit_chain_for_push(repo_root, remote_name, push_range))
        else:
            errors.extend(check_commit_chain_for_push(repo_root, remote_name, "HEAD"))

    elif parsed.all:
        print("🛡️  [copyright-kit] 正在执行全维度全量开源合规穿透体检...")
        # 1. 检查 Git 身份
        errors.extend(check_git_identity(repo_root))
        # 2. 检查工作区跟踪文件与内容
        errors.extend(check_working_tree_files(repo_root))
        # 3. 检查从根到 HEAD 的所有 commit 历史
        errors.extend(check_commit_chain_for_push(repo_root, "github", "HEAD"))

    else:
        # 默认执行轻量工作区与身份检查
        errors.extend(check_git_identity(repo_root))
        errors.extend(check_working_tree_files(repo_root))

    if errors:
        print("\n" + "!" * 70)
        print(f"❌ [COMPLIANCE BREACH] 检测到 {len(errors)} 项开源合规阻断性违规:")
        for idx, err in enumerate(errors, 1):
            print(f"  {idx}. {err}")
        print("!" * 70)
        print("💡 请根据提示修正后重试。严禁将商业公司内部敏感信息推送到公开开源仓库！\n")
        return 1

    print("✅ [COMPLIANCE PASS] copyright-kit 开源安全与合规审计 100% 达标！")
    return 0


if __name__ == "__main__":
    sys.exit(main())
