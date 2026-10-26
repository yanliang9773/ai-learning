#!/usr/bin/env python3
"""第 2 周：把汇率数据变成分析结果 + 图表 + Excel。

先跑 week02\\01_api_fetch.py 生成 rates_live.json（失败时会自动用离线样本）。
本脚本兼容两种结构（实时接口结果 / 离线样本序列）。

知识点：pd.DataFrame 构造、时序重采样 resample、滚动窗口 rolling、matplotlib 中文、Excel 多 sheet
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
LIVE = BASE_DIR / "data" / "rates_live.json"
SAMPLE = BASE_DIR / "data" / "rates_sample.json"
OUT_XLSX = BASE_DIR / "汇率分析.xlsx"
OUT_PNG = BASE_DIR / "汇率趋势.png"


def load_series() -> pd.DataFrame:
    """把 JSON 变成一张长 60 行、按日期索引的宽表。"""
    for src in (LIVE, SAMPLE):
        if not src.is_file():
            continue
        data = json.loads(src.read_text(encoding="utf-8"))

        if "series" in data:                      # 时间序列（历史接口 / 离线样本都是这个结构）
            df = pd.DataFrame(data["series"])
            df["日期"] = pd.to_datetime(df["date"])
            df = df.drop(columns=["date"]).set_index("日期").sort_index()
            tag = data.get("source", "未知来源")
            print(f"数据来源：{src.name}（{tag}，{len(df)} 个交易日）")
            return df

        if "rates" in data:                        # 实时接口：只有一天，补一列标记
            df = pd.DataFrame([data["rates"]])
            df["日期"] = pd.to_datetime(data.get("date") or pd.Timestamp.now().date())
            df = df.set_index("日期")
            print(f"数据来源：{src.name}（实时，{len(df)} 天）")
            return df

    sys.exit("❌ 找不到数据文件，请先运行：python week02\\01_api_fetch.py")


def analyze(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """统计描述 + 涨跌幅 + 波动率。这几个指标以后做 AI 数据分析天天用。"""
    if len(df) < 2:
        print("⚠️  只有 1 天数据，波动分析跳过（涨跌幅需要至少 2 天）")
        return {"统计描述": df.describe().T.round(4)}

    stats = pd.DataFrame({
        "期初": df.iloc[0],
        "期末": df.iloc[-1],
        "最高": df.max(),
        "最低": df.min(),
        "平均": df.mean().round(4),
        "涨跌幅%": ((df.iloc[-1] / df.iloc[0] - 1) * 100).round(3),
        "日波动率%": (df.std() / df.mean() * 100).round(3),
    })

    # 环比变化：pct_change 是时序分析里最常用的一个方法
    change = df.pct_change().mul(100).round(3)
    change.columns = [f"{c}_日涨跌%" for c in change.columns]

    # 7 日滚动均值：把噪声抹平，看趋势
    roll = df.rolling(window=7, min_periods=1).mean().round(4)
    roll.columns = [f"{c}_7日均线" for c in roll.columns]

    # 月度重采样：resample 是按时间聚合的核心 API
    monthly = df.resample("ME").agg(["mean", "max", "min"]).round(4)
    monthly.columns = [f"{cur}_{agg}" for cur, agg in monthly.columns]

    print("\n核心指标：")
    with pd.option_context("display.width", 200, "display.max_columns", None):
        print(stats.to_string())

    return {"核心指标": stats, "每日数据": df, "日涨跌%": change, "7日均线": roll, "月度统计": monthly}


def plot(df: pd.DataFrame) -> None:
    """画趋势图。

    两个必须会的坑：
      1) Windows 下 matplotlib 中文乱码 -> 显式指定字体
      2) 量级差太大的两条线画在同一个 y 轴上，小的会被压成直线
         -> 这里按数量级自动分组，每组一个子图
    """
    import matplotlib
    matplotlib.use("Agg")                        # 无界面环境下保存图片
    import matplotlib.pyplot as plt

    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False   # 修复负号显示成方框

    # 按数量级分桶，保证同一个子图里的线量级接近
    # 注意：必须用 math.floor，不能用 int()。int(-0.05) 会得到 0（向零截断），
    # 于是 0.89 和 6.7 被误判成同一数量级，画在一张图里小的就被压成直线了。
    buckets: dict[int, list[str]] = {}
    for col in df.columns:
        mean_val = float(df[col].mean())
        if mean_val <= 0:
            continue
        buckets.setdefault(math.floor(math.log10(mean_val)), []).append(col)

    n = len(buckets)
    fig, axes = plt.subplots(n, 1, figsize=(11, 3.2 * n + 1), sharex=True)
    axes = [axes] if n == 1 else list(axes)

    colors = ["#2F6EA5", "#C55A11", "#548235", "#7030A0", "#BF9000"]
    for ax, cols in zip(axes, buckets.values()):
        for i, col in enumerate(cols):
            ax.plot(df.index, df[col], marker="o", ms=3, lw=1.4,
                    color=colors[i % len(colors)], label=col)
            if len(df) >= 7:
                ax.plot(df.index, df[col].rolling(7, min_periods=1).mean(),
                        ls="--", lw=1.1, alpha=0.75, color=colors[i % len(colors)])
        ax.set_ylabel(" / ".join(cols))
        ax.legend(loc="best")
        ax.grid(alpha=0.3)

    axes[0].set_title("汇率走势（实线=每日值，虚线=7 日均线）")
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=130)
    plt.close(fig)
    print(f"\n✅ 图表已保存：{OUT_PNG}（{n} 个子图，按量级分组）")


def main() -> int:
    df = load_series()
    tables = analyze(df)

    with pd.ExcelWriter(OUT_XLSX, engine="openpyxl") as writer:
        for name, t in tables.items():
            t.to_excel(writer, sheet_name=name)
        print(f"\n✅ Excel 已保存：{OUT_XLSX}（{len(tables)} 个 sheet）")

    try:
        plot(df)
    except Exception as exc:                       # noqa: BLE001
        print(f"⚠️  画图失败（不影响 Excel 结果）：{exc}")

    print("\n本周练习（做完才算过关）：")
    print("  1. 打开 汇率分析.xlsx，看「日涨跌%」那一列，找出波动最大的那一天")
    print("  2. 把 --targets 换成 泰铢 THB、新元 SGD 再跑一次")
    print("  3. 自己加一个 30 日均线，看看曲线有什么变化")
    print("  4. 把 03_organize.py 或这个脚本改 5 行，做成你自己的东西，然后 commit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
