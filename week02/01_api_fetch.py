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

跑完会生成 week02\\data\\rates_live.json，给 02_analyze_chart.py 使用。

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
        preview = f"dict，{len(v)} 个键，示例 {list(v)[:3]}" if isinstance(v, dict) else str(v)[:60]
        print(f"     {k:<12} -> {preview}")


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

        OUT_DIR.mkdir(exist_ok=True)
        record = {
            "source": name,
            "base": args.base,
            "targets": args.targets,
            "requested_days": args.days,
            "fetched_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "series": rows,
        }
        OUT_JSON.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n✅ 已保存：{OUT_JSON}")
        print("   下一步：python week02\\02_analyze_chart.py")
        return 0

    # 所有在线源都挂了：用离线样本，保证第 2 周不被网络卡死
    print("\n⚠️  所有在线源都失败了（多半是网络/代理问题，不是你代码写错了）")
    if SAMPLE_JSON.is_file():
        OUT_DIR.mkdir(exist_ok=True)
        OUT_JSON.write_text(SAMPLE_JSON.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"   已用离线样本生成：{OUT_JSON}")
        print("   可以照常运行：python week02\\02_analyze_chart.py")
        return 0
    print("   连离线样本都没有")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
