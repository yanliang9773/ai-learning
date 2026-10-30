#!/usr/bin/env python3
"""try/except 机制演示 —— 每个例子都是"先猜后跑"的设计。

跑法：python week02\\00_try_except_demo.py
每个实验后停下来想想"为什么是这个结果"，再往下看。
"""
from __future__ import annotations


def sep(t: str) -> None:
    print(f"\n{'=' * 56}\n{t}\n{'=' * 56}")


# ────────────────────────────────────────────────
sep("实验 1｜没有 try 的世界：一炸全停")
# ────────────────────────────────────────────────
print("  这段代码跑到 int('abc') 会当场死亡，第 3 行打印永远执行不到：")
data = ["10", "20", "abc", "40"]
try:
    total = 0
    for s in data:
        total += int(s)          # 到 "abc" 时 ValueError，程序当场死亡
    print(total)                 # ← 永远到不了这行
except ValueError as e:
    print(f"  ☠️ 程序已炸（异常：{type(e).__name__}: {e}）")
    print("  真实世界里如果没有这个 except，到这里整个脚本就结束了。")
    print("  下面用 try 的正确姿势重做一遍 ↓")

# ────────────────────────────────────────────────
sep("实验 2｜最小可用形态：try 出事，except 接住")
# ────────────────────────────────────────────────
total = 0
skipped = []
for s in data:
    try:
        total += int(s)
    except ValueError:
        skipped.append(s)
print(f"  能转的加起来 = {total}，转不了的 = {skipped}")
print("  → 程序没死，坏数据被单独记账。这就是 read_one_csv 的雏形。")

# ────────────────────────────────────────────────
sep("实验 3｜控制流：except 之后，try 里剩下的代码全跳过")
# ────────────────────────────────────────────────
print("  预测：下面打印哪几行？（1 和 3？还是 1、2、3？）")
try:
    print("  ① try 里的第一行")
    x = 1 / 0                    # ZeroDivisionError 在这里炸
    print("  ② 这行还执行吗？")   # ← 不执行！爆炸点之后的 try 内容全部作废
except ZeroDivisionError:
    print("  ③ except 里执行")
print("  ④ 接住了，程序继续往下走")

# ────────────────────────────────────────────────
sep("实验 4｜多个 except = 不同死法不同处理（顺序：从具体到宽泛）")
# ────────────────────────────────────────────────
cases = ["abc", None, "10"]
for c in cases:
    try:
        n = int(c)
    except TypeError:                      # c 是 None：压根不是字符串
        print(f"  {c!r:<6} → 类型都不对（None 不能转数字）")
    except ValueError:                     # c 是 "abc"：类型对但内容转不了
        print(f"  {c!r:<6} → 类型对，但内容不是数字")
    else:                                  # ← 一行新面孔：try 没出事才执行
        print(f"  {c!r:<6} → 成功，得到 {n}")
print("  → 对照 fetch()：Timeout / HTTPError / JSONDecodeError / RequestException")
print("    四个 except 就是这个结构的工业版。")

# ────────────────────────────────────────────────
sep("实验 5｜as e：把异常对象抓下来看细节")
# ────────────────────────────────────────────────
try:
    int("99元")
except ValueError as e:
    print(f"  异常类名: {type(e).__name__}")
    print(f"  异常信息: {e}")
print("  → fetch() 70 行的 type(exc).__name__ 就是这个用法。")

# ────────────────────────────────────────────────
sep("实验 6｜raise：自己往外抛（except 处理完还可以再扔）")
# ────────────────────────────────────────────────
def parse_amount(s: str) -> float:
    try:
        return float(s)
    except ValueError as e:
        # 我不处理，包装成更有业务含义的错误，扔给调用者
        raise ValueError(f"金额字段解析失败：{s!r}") from e

try:
    parse_amount("￥abc")
except ValueError as e:
    print(f"  调用者收到的错误: {e}")
    print(f"  原始错误还挂着吗: {e.__cause__!r}")
print("  → raise = '这事我管不了/不该我管，往上传'。")
print("    fetch() 66 行的 raise ... from exc：4xx 不重试，直接判死刑传给 main。")

# ────────────────────────────────────────────────
sep("实验 7｜反面教材：这三种写法都别用")
# ────────────────────────────────────────────────
print("""
  ❌ 写法1 裸 except：
      try: ...
      except: pass          ← 连 KeyboardInterrupt（Ctrl+C）都接住，
         程序想停都停不了；还把真正的 bug 藏起来

  ❌ 写法2 吞掉不吭声：
      except Exception:
          pass              ← 出错了世界却不知道，排障时无影无踪

  ❌ 写法3 try 包太大：
      try:
          读文件(); 转数字(); 写报表(); 发邮件()   ← 20 行全塞 try 里
      except Exception as e:
          print(e)          ← 炸了只知道"这一大坨里某处"，定位靠猜

  ✅ 正确姿势（你已见过的）：
      · try 只包"那一下可能炸的动作"（一次 int()、一次网络请求）
      · except 写具体类型，从窄到宽
      · 接住了就记录/降级/上报，别静默
      · 处理不了的 raise 上去，让有全局视野的人（main）决定
""")

# ────────────────────────────────────────────────
sep("实验 8｜finally：无论如何都要执行的收尾（了解即可）")
# ────────────────────────────────────────────────
try:
    print("  干活中...")
    raise RuntimeError("突然事故")
except RuntimeError as e:
    print(f"  接住：{e}")
finally:
    print("  关文件/断连接等收尾动作放这里，出事与否都执行")
print("  （你其实早就在用更优雅的它：with open(...) —— with 就是自动版 finally）")

print("\n✅ 全部演示结束。核心一句话：")
print("   try = 预言这里可能出事并圈出范围；except = 按事故类型分别处置；")
print("   处置选项只有三种：就地解决、降级继续、raise 上报。静默 pass 是第四种——禁。")
