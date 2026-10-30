#!/usr/bin/env python3
"""plot() 解剖课 —— 把「按量级分桶画图」的每一步打印出来，并画两张对比图。

跑法：python week02\\03_plot_anatomy.py
产出：对比_错误画法.png（全挤一个子图）+ 对比_正确画法.png（分桶）
      终端里会打印分桶的每一步计算。
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

BASE = Path(__file__).resolve().parent
df = pd.DataFrame(json.loads((BASE / "data" / "rates_live.json").read_text(encoding="utf-8"))["series"])
df["日期"] = pd.to_datetime(df["date"])
df = df.drop(columns=["date"]).set_index("日期").sort_index()

print("=" * 60)
print("第 1 步：每个币种的平均值 → log10 → 取整，就是分桶的全过程")
print("=" * 60)
print(f"{'币种':<6}{'平均值':>10}{'log10':>10}{'floor(对)':>10}{'int(错)':>10}")
for col in df.columns:
    m = float(df[col].mean())
    lg = math.log10(m)
    print(f"{col:<6}{m:>10.3f}{lg:>10.3f}{math.floor(lg):>10}{int(lg):>10}")
print("\n  注意看 EUR/GBP：log10 是负数(-0.05 左右)，")
print("  floor 给 -1（正确：它们和 0.x 同量级），int 给 0（错误：和 CNY 混进同桶）")

# ── 两种分桶方式 ─────────────────────────────────
def make_buckets(use_floor: bool) -> dict[int, list[str]]:
    buckets: dict[int, list[str]] = {}
    for col in df.columns:
        m = float(df[col].mean())
        key = math.floor(math.log10(m)) if use_floor else int(math.log10(m))
        buckets.setdefault(key, []).append(col)
    return buckets

right = make_buckets(True)
wrong = make_buckets(False)
print(f"\n正确分桶（floor）: {right}")
print(f"错误分桶（int）  : {wrong}")

# ── 图 1：最错误的画法 —— 全部挤一个子图 ────────
fig, ax = plt.subplots(figsize=(11, 5))
for col in df.columns:
    ax.plot(df.index, df[col], label=col)
ax.set_title("错误示范：5 个币种挤同一个 y 轴")
ax.legend()
ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig(BASE / "对比_错误画法.png", dpi=120)
plt.close(fig)

# ── 图 2：int() 的错误分桶（0.89 和 6.7 同桶）───
def draw(buckets: dict, title: str, out: str) -> None:
    n = len(buckets)
    fig, axes = plt.subplots(n, 1, figsize=(11, 3.2 * n + 1), sharex=True)
    axes = [axes] if n == 1 else list(axes)
    for ax, cols in zip(axes, buckets.values()):
        for col in cols:
            ax.plot(df.index, df[col], marker="o", ms=3, label=col)
        ax.set_ylabel(" / ".join(cols))
        ax.legend(loc="best")
        ax.grid(alpha=0.3)
    axes[0].set_title(title)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(BASE / out, dpi=120)
    plt.close(fig)

draw(wrong, "int() 的错误分桶：EUR/GBP 被 CNY 压成贴地直线", "对比_int错误分桶.png")
draw(right, "floor 的正确分桶（02_analyze_chart.py 现在用的）", "对比_正确分桶.png")

print("\n✅ 三张图已生成，按顺序打开对比：")
for f in ["对比_错误画法.png", "对比_int错误分桶.png", "对比_正确分桶.png"]:
    print(f"   {BASE / f}")
print("\n看图的三个问题（答案就在图里）：")
print("  1. 错误画法图里，除了 KRW，其它线还能看出走势吗？")
print("  2. int 错误分桶图的第一格里，EUR 那条线是什么形态？为什么？")
print("  3. 正确分桶图里每个子图的 y 轴刻度范围，和它桶里币种的关系是？")
