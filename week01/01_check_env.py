#!/usr/bin/env python3
"""环境体检脚本 —— 第 1 周第一件事就是跑它。

它会明确告诉你四件事：
  1. Python 是不是来自你的虚拟环境（.venv）
  2. pandas / openpyxl / requests 这些必需的包装好了没
  3. 桌面路径、当前工作目录这类容易搞混的位置
  4. 一个真实的小计算，证明解释器能正常工作

对应知识点：sys.prefix / sys.executable、importlib.metadata、pathlib、f-string、类型注解
"""
from __future__ import annotations

import sys
import platform
import importlib
import unicodedata
from pathlib import Path
from importlib import metadata

# 这个包是你后面每一步都要用的。
# 注意「导入名」和「安装名」经常不一样：pip install python-dotenv，但 import dotenv。
# 所以正确做法是先试着 import，再用安装名去查版本号。
REQUIRED: dict[str, tuple[str, str, str]] = {  # REQUIRED 变量名 全大写代表是常量   dict 是字典
    "pandas": ("pandas", "pandas", "数据处理，W2 起必用"),
    "openpyxl": ("openpyxl", "openpyxl", "读写 Excel 的唯一依赖"),
    "requests": ("requests", "requests", "调用网络接口"),
    "matplotlib": ("matplotlib", "matplotlib", "画图"),
    "dotenv": ("dotenv", "python-dotenv", "从 .env 读取密钥，W3 起必用"),
}


def line(char: str = "-", width: int = 68) -> None:
    """打印一条分隔线。"""
    print(char * width)


def dwidth(text: str) -> int:
    """算出字符串在终端里占几「列」。

    为什么需要这个函数：len("方案A") 是 3，但终端里它占 6 列（中文是双宽字符）。
    所以 f"{x:<12}" 对中英混排的文本永远对不齐 —— 必须自己按显示宽度补空格。
    """
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in text)


def pad(text: str, width: int) -> str:
    """按显示宽度右侧补空格，让中英混排的几行能对齐。"""
    return text + " " * max(width - dwidth(text), 0)


def print_rows(rows: list[tuple[str, str]], indent: str = "  ") -> None:
    """把 (标签, 值) 列表按「显示宽度」对齐打印。

    中英混排对齐的正确做法：不要手敲空格数，用 pad() 算出来。
    标签里不要自带冒号，统一在这里加，宽度才算得准。
    """
    label_w = max(dwidth(label) for label, _ in rows)
    for label, value in rows:
        print(f"{indent}{pad(label, label_w)}: {value}")


def check_interpreter() -> bool:
    """确认 Python 来自虚拟环境。返回 True 表示正常。"""
    print("\n[1] 解释器")
    line()

    in_venv = sys.prefix != sys.base_prefix
    rows: list[tuple[str, str]] = [
        ("版本", f"{platform.python_version()}  ({platform.architecture()[0]})"),
        ("可执行文件", sys.executable),
    ]

    if in_venv:
        rows.append(("虚拟环境", f"✅ 已激活 -> {sys.prefix}"))
        print_rows(rows)
        return True

    rows.extend([
        ("虚拟环境", "❌ 未激活！你现在用的是系统全局 Python"),
        ("方案A conda", "conda activate ai"),
        ("方案B venv", r".\.venv\Scripts\Activate.ps1"),
        ("判断依据", "命令行前面出现 (ai) 或 (.venv)，且本行变成 ✅"),
    ])
    print_rows(rows)
    return False


def check_packages() -> int:
    """检查依赖包，返回缺失的数量。

    先 import（判断能不能用），再查版本（判断装的是哪个包）。
    """
    print("\n[2] 依赖包")
    line()
    missing = 0
    for import_name, (mod, dist, why) in REQUIRED.items():
        try:
            importlib.import_module(mod)
        except ImportError:
            print(f"  ❌ {import_name:<12} {'未安装':<12} {why}")
            missing += 1
            continue
        try:
            ver = metadata.version(dist)
        except metadata.PackageNotFoundError:
            ver = "版本未知"
        print(f"  ✅ {import_name:<12} {ver:<12} {why}")

    if missing:
        print("\n  一条命令补齐（清华镜像，国内快）：")
        print("    pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple")
    return missing


def check_paths() -> None:
    """打印几个关键位置，避免以后路径搞混。"""
    print("\n[3] 关键路径")
    line()
    here = Path(__file__).resolve()
    print(f"  当前目录    : {Path.cwd()}")
    print(f"  脚本自身    : {here}")
    print(f"  项目根目录  : {here.parent.parent}")
    print(f"  用户主目录  : {Path.home()}")
    # 桌面可能被 OneDrive 接管，两个位置都试一下
    candidates = [Path.home() / "Desktop", Path.home() / "OneDrive" / "Desktop"]
    found = next((c for c in candidates if c.is_dir()), None)
    print(f"  桌面目录    : {found if found else '❌ 两个常见位置都没找到'}")

    # pathlib 的优势：像拼句子一样拼路径，跨平台不用管斜杠方向
    sample = here.parent / "data"
    print(f"  示例数据目录: {sample}  ({'存在' if sample.is_dir() else '不存在'})")


def sanity_calc() -> None:
    """一个真实的小计算，证明解释器能干活。"""
    print("\n[4] 计算自检")
    line()
    prices = [12.5, 48.0, 7.25, 99.9]                      # 列表
    total = sum(prices)                                     # 内置函数
    # 列表推导式：现代 Python 最常用的一行写法
    with_tax = [round(p * 1.13, 2) for p in prices]
    print(f"  原始价格     : {prices}")
    print(f"  合计         : {total:.2f}")
    print(f"  含税(13%)    : {with_tax}")
    print(f"  平均值       : {total / len(prices):.2f}")
    print("  ✅ 计算正常")


def main() -> int:
    """主流程：跑所有检查，返回退出码（0 = 一切正常）。"""
    print("=" * 68)
    print("  AI 学习上手包 · 环境体检")
    print("=" * 68)

    ok_env = check_interpreter()
    missing = check_packages()
    check_paths()
    sanity_calc()

    print("\n" + "=" * 68)
    if ok_env and missing == 0:
        print("  ✅ 环境 OK —— 可以去跑 week01\\02_merge_csv.py 了")
        return 0
    print("  ⚠️  还有问题需要解决，见上面的 ❌ 项")
    print("     顺序：先激活虚拟环境 -> 再装依赖 -> 再重跑本脚本")
    print("=" * 68)
    return 1


if __name__ == "__main__":
    # sys.exit 会把返回值变成命令行退出码，以后写自动化脚本靠这个判断成败
    raise SystemExit(main())
