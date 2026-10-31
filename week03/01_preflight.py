#!/usr/bin/env python3
"""第 3 周：仓库合规自查。在你 push 到 GitHub 之前跑它。

检查四件事：
  1. Git 装好了吗、身份配置了吗
  2. 有没有 .gitignore，.venv 会不会被误提交
  3. 有没有明文密钥被写进代码里（最严重的问题）
  4. README 是否存在

用法：
    python week03\\01_preflight.py

知识点：subprocess、re 正则、Path.rglob、退出码约定
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent   # 项目根目录

# 明文密钥的常见长相。命中就报警 —— 这是第 3 周最重要的一个习惯。
SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_\-]{16,}"),                 # OpenAI / 兼容接口
    re.compile(r"sk-ant-[A-Za-z0-9_\-]{16,}"),             # Anthropic
    re.compile(r"(api_key|apikey|secret|token|password)\s*=\s*['\"][^'\"]{12,}['\"]", re.I),
    re.compile(r"Bearer\s+[A-Za-z0-9_\-\.]{20,}"),
]

# 不该被提交的东西
MUST_IGNORE = [".env", ".venv", "__pycache__", "*.pyc"]

problems = 0


def ok(msg: str) -> None:
    print(f"  ✅ {msg}")


def warn(msg: str, fix: str = "") -> None:
    global problems
    problems += 1
    print(f"  ❌ {msg}")
    if fix:
        print(f"     修复：{fix}")


def run(cmd: list[str]) -> tuple[int, str]:
    """执行外部命令。捕获输出而不是让它直接打到屏幕上。"""
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=15, encoding="utf-8", errors="replace")
        return p.returncode, (p.stdout or p.stderr).strip()
    except FileNotFoundError:
        return 127, "命令不存在"
    except subprocess.TimeoutExpired:
        return 124, "命令超时"


def check_git() -> None:
    print("\n[1] Git 环境")
    code, ver = run(["git", "--version"])
    if code == 0:
        ok(ver)
    else:
        warn("找不到 git 命令", "装 Git for Windows 并把 git 加入 PATH")
        return

    for key, sample in (("user.name", "张三"), ("user.email", "you@example.com")):
        code, val = run(["git", "config", "--global", key])
        if code == 0 and val:
            ok(f"{key} = {val}")
        else:
            warn(f"未配置全局 {key}", f'git config --global {key} "{sample}"')

    code, out = run(["git", "rev-parse", "--is-inside-work-tree"])
    if code == 0:
        ok("当前目录已在 Git 仓库内")
    else:
        warn("还不是 Git 仓库", "cd 到项目根目录后执行 git init")


def check_gitignore() -> None:
    print("\n[2] .gitignore")
    gi = ROOT / ".gitignore"
    if not gi.is_file():
        warn("缺少 .gitignore", "创建它，至少包含 .env / .venv / __pycache__/")
        return
    text = gi.read_text(encoding="utf-8", errors="replace").lower()
    ok(f"存在：{gi}")
    for pat in MUST_IGNORE:
        if pat.rstrip("/") in text:
            ok(f"已忽略 {pat}")
        else:
            warn(f"没有忽略 {pat}", f"在 .gitignore 里加一行 {pat}")


def check_secrets() -> None:
    print("\n[3] 明文密钥扫描（最重要）")
    hits: list[tuple[Path, int, str]] = []
    for f in ROOT.rglob("*"):
        if not f.is_file():
            continue
        parts = {p.lower() for p in f.parts}
        # 跳过虚拟环境和 git 内部目录，否则扫出几万行没意义的东西
        if {".venv", ".git", "__pycache__", "site-packages", "node_modules"} & parts:
            continue
        if f.suffix not in {".py", ".md", ".txt", ".json", ".yaml", ".yml", ".ipynb", ".ps1"}:
            continue
        if f.name == "01_preflight.py":          # 本文件自带正则字符串，跳过自己
            continue
        try:
            for lineno, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                for pat in SECRET_PATTERNS:
                    if m := pat.search(line):
                        hits.append((f, lineno, m.group()[:24]))
                        break
        except (UnicodeDecodeError, OSError):
            continue

    if hits:
        for f, lineno, frag in hits:
            warn(f"{f.relative_to(ROOT)}:{lineno} 疑似明文密钥 -> {frag}...",
                 "改成从 .env 读取：os.environ['XXX']，并把 .env 加入 .gitignore")
    else:
        ok("没有发现明文密钥")

    env_file = ROOT / ".env"
    if env_file.is_file():
        ok("存在 .env 文件（密钥放这里是对的）")
        gi = ROOT / ".gitignore"
        if gi.is_file() and ".env" in gi.read_text(encoding="utf-8"):
            ok(".env 已被 .gitignore 屏蔽")
        else:
            warn(".env 没有被 gitignore！", "在 .gitignore 加一行 .env")
    else:
        warn("还没有 .env 文件", "复制 .env.example 为 .env，再填入你的密钥")


def check_readme() -> None:
    print("\n[4] README")
    readme = ROOT / "README.md"
    if readme.is_file():
        n = len(readme.read_text(encoding="utf-8").splitlines())
        if n >= 15:
            ok(f"README.md 存在（{n} 行）")
        else:
            warn(f"README.md 太短（{n} 行）", "至少写清：项目做什么、怎么装、怎么跑")
    else:
        warn("缺少 README.md", "在项目根目录创建 README.md")


def main() -> int:
    print("=" * 68)
    print("  仓库合规自查 · push 到 GitHub 之前必跑")
    print("=" * 68)
    check_git()
    check_gitignore()
    check_secrets()
    check_readme()

    print("\n" + "=" * 68)
    if problems == 0:
        print("  ✅ 全部通过 —— 可以放心 git push 了")
        return 0
    print(f"  ⚠️  发现 {problems} 个问题，按上面的「修复」提示逐条处理")
    print("      特别注意：密钥一旦 push 到公开仓库就视为已泄露，")
    print("      光删文件没用，必须去服务商后台吊销并重新生成。")
    print("=" * 68)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
