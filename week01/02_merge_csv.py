#!/usr/bin/env python3
"""第 1 周交付物：合并一个目录下所有 CSV，清洗后导出成多 sheet 的 Excel。

这就是「读 CSV -> 处理 -> 写回 Excel」的完整闭环，也是 W2 调接口的同一套骨架。

用法：
    python week01\\02_merge_csv.py                       # 默认处理 week01\\data
    python week01\\02_merge_csv.py D:\\我的报表            # 处理自己的目录
    python week01\\02_merge_csv.py --out 汇总.xlsx         # 指定输出文件名

知识点：argparse、pathlib.glob、pandas 清洗链、openpyxl 多 sheet 写入、异常处理
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

# 可能遇到的编码，按顺序试。中文 CSV 在国内几乎必踩这个坑。
ENCODINGS = ["utf-8-sig", "utf-8", "gbk", "gb18030"]

# 需要清洗的数值列（列名 -> 要干掉的脏字符）。国内导出的表常带千分位逗号和货币符号。
NUMERIC_CLEAN = {"金额": ",￥$ ", "数量": " "}


def read_one_csv(path: Path) -> pd.DataFrame | None:
    """读一个 CSV：自动试编码；遇到字段数不对的坏行则跳过该行而不是放弃整个文件。

    真实世界导出的表经常有格式坏掉的行。直接报错让整批任务失败是很糟的体验，
    所以策略是：先严格读，读不动就降级成「跳过坏行」再读，并把坏行号打出来。
    """
    last_err: Exception | None = None
    for enc in ENCODINGS:
        try:
            df = pd.read_csv(path, encoding=enc)
            df.attrs["encoding"] = enc
            return df
        except (UnicodeDecodeError, UnicodeError):
            continue                      # 编码不对，换下一个试
        except pd.errors.ParserError as exc:
            # 字段数不对：降级为跳过坏行，这样一条烂记录不会带走整张表
            last_err = exc
            try:
                df = pd.read_csv(path, encoding=enc, on_bad_lines="skip")
                df.attrs["encoding"] = enc
                print(f"  ⚠️  {path.name} 有坏行已跳过（原始错误：{str(exc).split(',')[0]}）")
                return df
            except (UnicodeDecodeError, UnicodeError):
                continue
            except Exception as exc2:     # noqa: BLE001
                last_err = exc2
        except Exception as exc:          # noqa: BLE001
            last_err = exc
    print(f"  ⚠️  {path.name} 读取失败，已跳过：{last_err}")
    return None


def clean(df: pd.DataFrame, source_name: str) -> pd.DataFrame:
    """标准清洗链：去空行、去空格、统一列名、类型转换、加来源列。"""
    df = df.copy()

    # 1. 列名两端空格、全角空格，顺手统一成小写
    df.columns = [str(c).strip().replace("\u3000", "") for c in df.columns]

    # 2. 整行都是空值的，丢掉
    before = len(df)
    df = df.dropna(how="all")

    # 3. 关键列有空值的丢掉（没有日期或金额的记录基本没法用）
    for key_col in ("日期", "金额"):
        if key_col in df.columns:
            df = df.dropna(subset=[key_col])

    # 4. 文本列两端空格清掉
    #    pandas 2.x 的文本列是 object，pandas 3.x 是 string，两种都要覆盖
    text_cols = [c for c in df.columns if pd.api.types.is_string_dtype(df[c]) or df[c].dtype == object]
    for col in text_cols:
        df[col] = df[col].dropna().astype(str).str.strip()

    # 5. 数值列：把 "￥1,200" 这种字符串变成真正的数字
    for col, strip_chars in NUMERIC_CLEAN.items():
        if col in df.columns:
            df[col] = (
                df[col]
                .astype(str)
                .str.strip()
                .str.replace(f"[{strip_chars}]", "", regex=True)
                .replace({"": None, "nan": None, "None": None})
            )
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # 5b. 转完数字后金额仍为空 = 原文是 "abc元" 这类解析不出来的脏值，删。
    #     必须放在 to_numeric 之后：第 3 步只能删"格子本来就空"的行，
    #     删不掉"有字但转不成数字"的——那时它还穿着字符串的皮，coerce 之后才现形。
    #     （和 97 行删假日期是同一个道理：空值鬼和假值鬼要分两拨抓。）
    if "金额" in df.columns:
        df = df.dropna(subset=["金额"])

    # 6. 日期列转成真正的日期类型（Excel 里才能排序、做透视）
    if "日期" in df.columns:
        df["日期"] = pd.to_datetime(df["日期"], errors="coerce")
        df = df.dropna(subset=["日期"])

    # 7. 加一列来源，合并之后还能追溯到原始文件 —— 这是好习惯
    df.insert(0, "来源文件", source_name)

    dropped = before - len(df)
    if dropped:
        print(f"     {source_name}: 原始 {before} 行 -> 有效 {len(df)} 行（剔除 {dropped} 行脏数据）")
    else:
        print(f"     {source_name}: {len(df)} 行，数据干净")
    return df


def summarize(merged: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """生成几张汇总表，作为 Excel 的额外 sheet。"""
    tables: dict[str, pd.DataFrame] = {}
    if "日期" in merged.columns and "金额" in merged.columns:
        m = merged.assign(月份=merged["日期"].dt.to_period("M").astype(str))
        tables["按月份汇总"] = (
            m.groupby("月份", as_index=False)
             .agg(记录数=("金额", "size"), 总金额=("金额", "sum"), 平均金额=("金额", "mean"))
             .round({"平均金额": 2})
        )
    if "地区" in merged.columns and "金额" in merged.columns:
        tables["按地区汇总"] = (
            merged.groupby("地区", as_index=False)
                  .agg(记录数=("金额", "size"), 总金额=("金额", "sum"))
                  .sort_values("总金额", ascending=False)
        )
    if "类别" in merged.columns and "金额" in merged.columns:
        tables["按类别汇总"] = (
            merged.groupby("类别", as_index=False)
                  .agg(记录数=("金额", "size"), 总金额=("金额", "sum"))
                  .sort_values("总金额", ascending=False)
        )
    if "来源文件" in merged.columns:
        tables["按来源文件"] = (
            merged.groupby("来源文件", as_index=False)
                  .agg(记录数=("金额", "size"), 总金额=("金额", "sum"))
        )
    return tables


def export_excel(merged: pd.DataFrame, tables: dict[str, pd.DataFrame], out_path: Path) -> None:
    """写多 sheet Excel，并自动调整列宽 + 冻结表头 + 数字格式。"""
    with pd.ExcelWriter(out_path, engine="openpyxl", datetime_format="yyyy-mm-dd") as writer:
        merged.to_excel(writer, sheet_name="明细", index=False)
        for name, tdf in tables.items():
            tdf.to_excel(writer, sheet_name=name[:31], index=False)

        # 回头用 openpyxl 做美化：openpyxl 是控制 Excel 细节的底层库
        from openpyxl.styles import Alignment, Font, PatternFill
        from openpyxl.utils import get_column_letter

        wb = writer.book
        for ws in wb.worksheets:
            ws.freeze_panes = "A2"
            for cell in ws[1]:
                cell.font = Font(bold=True, color="FFFFFF", name="Microsoft YaHei")
                cell.fill = PatternFill("solid", fgColor="2F6EA5")
                cell.alignment = Alignment(horizontal="center")
            for idx, col in enumerate(ws.iter_cols(min_row=1, max_row=min(ws.max_row, 200)), 1):
                width = max((len(str(c.value)) for c in col if c.value is not None), default=8)
                # 中文按 2 个字符宽度估算
                zh = sum(1 for c in col if c.value and any("\u4e00" <= ch <= "\u9fff" for ch in str(c.value)))
                ws.column_dimensions[get_column_letter(idx)].width = min(width + zh * 0.6 + 3, 42)

            # 金额列加千分位格式，数量列整数格式，日期列只显示到年月日
            header = [c.value for c in ws[1]]
            for j, h in enumerate(header, 1):
                if h in ("金额", "总金额", "平均金额"):
                    for r in range(2, ws.max_row + 1):
                        ws.cell(row=r, column=j).number_format = "#,##0.00"
                elif h in ("数量", "记录数"):
                    for r in range(2, ws.max_row + 1):
                        ws.cell(row=r, column=j).number_format = "#,##0"
                elif h == "日期":
                    for r in range(2, ws.max_row + 1):
                        ws.cell(row=r, column=j).number_format = "yyyy-mm-dd"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="合并目录下所有 CSV 并导出成多 sheet Excel",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("folder", nargs="?", default=None, help="要扫描的目录（默认 week01\\data）")
    parser.add_argument("--out", default="合并结果.xlsx", help="输出的 Excel 文件名")
    args = parser.parse_args(argv)

    # 路径解析：没有显式给目录就用脚本旁边的 data 目录
    if args.folder:
        folder = Path(args.folder).expanduser().resolve()
    else:
        folder = Path(__file__).resolve().parent / "data"

    if not folder.is_dir():
        print(f"❌ 目录不存在：{folder}")
        return 1

    csv_files = sorted(folder.glob("*.csv"))
    if not csv_files:
        print(f"❌ 目录里没有 CSV 文件：{folder}")
        print("   把你的 .csv 文件放进去，或者用命令行参数指定别的目录")
        return 1

    print(f"扫描目录：{folder}")
    print(f"发现 {len(csv_files)} 个 CSV：")
    for f in csv_files:
        print(f"  - {f.name}")

    frames: list[pd.DataFrame] = []
    for f in csv_files:
        df = read_one_csv(f)
        if df is None:
            continue
        frames.append(clean(df, f.name))

    if not frames:
        print("❌ 没有任何文件能成功读取")
        return 1

    # concat：把结构相同的表上下叠起来。ignore_index 让行号重新排
    merged = pd.concat(frames, ignore_index=True, sort=False)
    print(f"\n合并后：{len(merged)} 行 × {len(merged.columns)} 列")
    print(f"列名：{list(merged.columns)}")

    tables = summarize(merged)
    print(f"生成汇总表 {len(tables)} 张：{list(tables.keys())}")

    out_path = Path(args.out).resolve()
    export_excel(merged, tables, out_path)
    print(f"\n✅ 已导出：{out_path}")
    print("   打开看看：明细 + 几张汇总表，表头已冻结、金额已加千分位")

    # 顺手打印前几行，方便肉眼核对
    print("\n前 5 行预览：")
    with pd.option_context("display.max_columns", None, "display.width", 200):
        print(merged.head().to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
