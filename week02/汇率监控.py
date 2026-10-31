#!/usr/bin/env python3
"""第 2 周：从公开 API 拉一段汇率时间序列（欧洲央行官方数据，免费无需密钥）。

演示四件必须会的事：
  1. 超时（不设超时，程序会永远挂着 —— 新手最常见的「卡死」原因）
  2. 失败重试 + 指数退避（网络偶发失败是常态，不是异常）
  3. 多数据源回退（一个源不通自动换下一个）
  4. JSON 结构探查（拿到数据先打印结构，别瞎猜字段名）

用法：
    python week02\\01_api_fetch.py
    python week02\\01_api_fetch.py --base USD --targets CNY EUR JPY --days 90

知识点：requests、Session、异常分层、退避重试、argparse
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import requests

import math

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
OUT_DIR = BASE_DIR / "data"
OUT_JSON = OUT_DIR / "rates_live.json"
SAMPLE_JSON = OUT_DIR / "rates_sample.json"


def build_urls(base: str, targets: list[str], days: int) -> list[tuple[str, str]]:
    """按优先级构造候选数据源 URL。第一个是历史序列，最后两个是当日快照兜底。"""
    end = date.today()
    start = end - timedelta(days=days)
    t = ",".join(targets)
    return [
        ("ECB 历史序列",
         f"https://api.frankfurter.app/{start}..{end}?from={base}&to={t}"),
        ("ECB 历史序列(备用域名)",
         f"https://api.frankfurter.dev/v1/{start}..{end}?base={base}&symbols={t}"),
        ("ER-API 当日快照",
         f"https://open.er-api.com/v6/latest/{base}"),
    ]


def fetch(url: str, timeout: float = 12.0, retries: int = 3) -> dict:
    """带超时与指数退避重试的 GET，返回解析后的 JSON。失败抛 RuntimeError。"""
    last_err: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, timeout=timeout,
                                headers={"User-Agent": "learning-script/1.0"})
            resp.raise_for_status()          # 4xx/5xx 转成异常，否则你会拿到 HTML 还以为成功了
            return resp.json()
        except requests.Timeout:
            last_err = RuntimeError(f"超时（>{timeout}s）")
        except requests.HTTPError as exc:
            code = exc.response.status_code
            last_err = RuntimeError(f"HTTP {code}")
            # 4xx 是请求本身写错了，重试没有意义，立刻放弃这个源
            if code < 500:
                raise last_err from exc
        except requests.exceptions.JSONDecodeError:
            last_err = RuntimeError("返回的不是合法 JSON（可能被网关拦截了）")
        except requests.RequestException as exc:
            last_err = RuntimeError(f"{type(exc).__name__}: {exc}")

        if attempt < retries:
            wait = 0.8 * attempt              # 退避：越试等越久，别疯狂敲对方服务器
            print(f"     ⚠️  {last_err}  ->  {wait:.1f}s 后第 {attempt + 1} 次重试")
            time.sleep(wait)

    raise RuntimeError(f"{retries} 次尝试都失败：{last_err}")


def to_rows(payload: dict, base: str, targets: list[str]) -> list[dict]:
    """统一两种响应结构 -> [{date, CNY, EUR, ...}, ...]。

    这就是「适配层」：数据源结构变了，只改这一个函数，上层分析代码不用动。
    """
    rows: list[dict] = []
    raw_rates = payload.get("rates", {})

    if not raw_rates:
        return rows

    # 历史序列：{"2026-08-25": {"CNY": 6.71, ...}, ...}
    if all(isinstance(v, dict) for v in raw_rates.values()):
        for d in sorted(raw_rates):
            rec = {"date": d}
            rec.update({k: float(v) for k, v in raw_rates[d].items() if k in targets})
            if len(rec) > 1:
                rows.append(rec)
    else:
        # 当日快照：{"CNY": 6.7, "EUR": 0.89, ...}
        rec = {"date": payload.get("date") or str(date.today())}
        rec.update({k: float(v) for k, v in raw_rates.items() if k in targets})
        if len(rec) > 1:
            rows.append(rec)

    return rows


def probe(payload: dict) -> None:
    """打印 JSON 结构 —— 拿到任何新 API 都先干这一步，别凭想象写字段名。"""
    print("\n  🔍 结构探查")
    for k, v in payload.items():
        if isinstance(v, dict):
            preview = f"dict，{len(v)} 个键，示例 {list(v)[:3]}"
        elif isinstance(v, list):
            preview = f"list，{len(v)} 个元素，第 1 个长这样：{str(v[0])[:50] if v else '（空）'}"
        else:
            preview = str(v)[:60]
        print(f"     {k:<12} -> {preview}")





"""第 2 周：把汇率数据变成分析结果 + 图表 + Excel。

先跑 week02\\01_api_fetch.py 生成 rates_live.json（失败时会自动用离线样本）。
本脚本兼容两种结构（实时接口结果 / 离线样本序列）。

知识点：pd.DataFrame 构造、时序重采样 resample、滚动窗口 rolling、matplotlib 中文、Excel 多 sheet
"""


BASE_DIR = Path(__file__).resolve().parent
LIVE = BASE_DIR / "data" / "rates_live.json"
SAMPLE = BASE_DIR / "data" / "rates_sample.json"
OUT_XLSX = BASE_DIR / "汇率分析.xlsx"
OUT_PNG = BASE_DIR / "汇率趋势.png"

def modify_frame(rows:list[dict]) ->pd.DataFrame:
    df = pd.DataFrame(rows)
    df["日期"] = pd.to_datetime(df["date"])
    df = df.drop(columns=["date"]).set_index("日期").sort_index()
    return df

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






def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="拉取汇率时间序列并保存为 JSON",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--base", default="USD", help="基准货币")
    parser.add_argument("--targets", nargs="+", default=["CNY", "EUR", "JPY", "GBP", "KRW"],
                        help="要查询的目标货币")
    parser.add_argument("--days", type=int, default=60, help="回看多少天")
    args = parser.parse_args(argv)

    print(f"基准：{args.base}   目标：{', '.join(args.targets)}   回看：{args.days} 天")

    for name, url in build_urls(args.base, args.targets, args.days):
        print(f"\n[{name}]\n  {url}")
        try:
            payload = fetch(url)
        except RuntimeError as exc:
            print(f"     ❌ {exc} -> 换下一个源")
            continue

        probe(payload)
        rows = to_rows(payload, args.base, args.targets)
        if not rows:
            print("     ❌ 拿到数据但没有需要的币种，换下一个源")
            continue

        print(f"\n     ✅ 成功：{len(rows)} 个交易日 × {len(args.targets)} 个币种")
        print("     最早一天：", json.dumps(rows[0], ensure_ascii=False))
        print("     最新一天：", json.dumps(rows[-1], ensure_ascii=False))
        break
    else:
        # 所有在线源都挂了：降级用离线样本，继续走完分析流程
        print("\n⚠️  所有在线源都失败了（多半是网络/代理问题，不是你代码写错了）")
        if SAMPLE_JSON.is_file():
            rows = json.loads(SAMPLE_JSON.read_text(encoding="utf-8"))["series"]
            missing = [t for t in args.targets if t not in rows[0]]
            if missing:
                print(f"   ⚠️ 样本里没有：{missing}，这些币种本次无数据")
            print(f"   ⚠️ 已降级为离线样本：{len(rows)} 个交易日（数据可能过期）")
        else:
            print("   连离线样本都没有，无法继续")
            return 1

   
    df = modify_frame(rows)
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
    print("  1. 给这个程序加 --no-fetch 开关")
    print("  2. 把 --targets 换成 泰铢 THB、新元 SGD 再跑一次")
    print("  3. 自己加一个 30 日均线，看看曲线有什么变化")
    print("  4. 把 03_organize.py 或这个脚本改 5 行，做成你自己的东西，然后 commit")
    return 0



if __name__ == "__main__":
    raise SystemExit(main())
