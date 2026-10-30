#!/usr/bin/env python3
"""按文件类型批量整理文件夹的小工具。

⚠️ 安全设计：默认是「预览模式」，只打印计划，不移动任何文件。
   确认预览没问题后，加 --apply 才真正执行。
   以后你写任何「会改数据/删文件」的脚本，都要养成这个习惯。

用法：
    python week01\\03_organize.py C:\\Users\\yan\\Downloads          # 预览
    python week01\\03_organize.py C:\\Users\\yan\\Downloads --apply   # 真的整理

知识点：pathlib、shutil.move、命名冲突处理、dry-run 模式、f-string
"""
from __future__ import annotations

import argparse
import shutil
import sys
from collections import Counter
from pathlib import Path

# 扩展名 -> 归类文件夹。按需要自己加。
RULES: dict[str, tuple[str, ...]] = {
    "图片": (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg", ".heic"),
    "文档": (".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".md", ".csv"),
    "压缩包": (".zip", ".rar", ".7z", ".tar", ".gz"),
    "安装包": (".exe", ".msi", ".apk"),
    "音视频": (".mp3", ".mp4", ".mkv", ".avi", ".wav", ".mov"),
    "代码": (".py", ".js", ".ts", ".json", ".html", ".css", ".ipynb"),
    "数据": (".parquet", ".feather"),
}

# 反向查表：扩展名 -> 类别
EXT_TO_CATEGORY: dict[str, str] = {
    ext: cat for cat, exts in RULES.items() for ext in exts
}


def unique_dest(dest_dir: Path, filename: str) -> Path:
    """目标重名时自动加 _1、_2 后缀，绝不覆盖已有文件。"""
    dest = dest_dir / filename
    if not dest.exists():
        return dest
    stem, suffix = Path(filename).stem, Path(filename).suffix
    n = 1
    while (candidate := dest_dir / f"{stem}_{n}{suffix}").exists():
        n += 1
    return candidate


def plan_moves(root: Path) -> list[tuple[Path, Path]]:
    """生成移动计划 [(源, 目标), ...]，不执行任何操作。"""
    plans: list[tuple[Path, Path]] = []
    for item in sorted(root.iterdir()):
        # 只要普通文件；跳过子目录（含本脚本生成的分类文件夹）
        if not item.is_file():
            continue
        # 别把这个脚本自己搬走了
        if item.resolve() == Path(__file__).resolve():
            continue
        ext = item.suffix.lower()
        category = EXT_TO_CATEGORY.get(ext, "其他")
        dest_dir = root / category
        plans.append((item, unique_dest(dest_dir, item.name)))
    return plans


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="按文件类型整理一个文件夹")
    parser.add_argument("folder", help="要整理的文件夹路径")
    parser.add_argument("--apply", action="store_true",
                        help="真正执行移动。不加此参数只预览，不改动任何文件")
    args = parser.parse_args(argv)

    root = Path(args.folder).expanduser().resolve()
    if not root.is_dir():
        print(f"❌ 不是一个存在的目录：{root}")
        return 1

    plans = plan_moves(root)
    if not plans:
        print(f"目录里没有可整理的文件：{root}")
        return 0

    counts = Counter(dest.parent.name for _, dest in plans)
    mode = "🔧 执行模式" if args.apply else "👀 预览模式（不会改动任何文件）"
    print(f"目标目录：{root}")
    print(f"发现 {len(plans)} 个文件，{mode}\n")

    for src, dest in plans:
        rel_dest = Path(dest.parent.name) / dest.name
        flag = "移动" if args.apply else "将移动"
        print(f"  {flag}: {src.name:<42} -> {rel_dest}")

    print("\n分类统计：")
    for cat, n in counts.most_common():
        print(f"  {cat:<8} {n} 个")

    if not args.apply:
        print("\n✅ 预览完成，你的文件一个都没动。")
        print(f"   确认无误后执行：python {Path(__file__).name} \"{args.folder}\" --apply")
        return 0

    # 真正执行：先建目录，再移动
    for dest_dir in {dest.parent for _, dest in plans}:
        dest_dir.mkdir(exist_ok=True)
    done = 0
    for src, dest in plans:
        try:
            shutil.move(str(src), str(dest))
            done += 1
        except (PermissionError, OSError) as exc:
            print(f"  ❌ 跳过 {src.name}（文件被占用或权限不足）：{exc}")

    print(f"\n✅ 已整理 {done}/{len(plans)} 个文件到 {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
