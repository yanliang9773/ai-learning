#!/usr/bin/env python3
r"""对齐原理演示 —— 把 01_check_env.py 里那三个函数的每一步拆开打印。

跑法：
    D:\Anaconda3\python.exe week01\04_align_demo.py

配合 01_check_env.py 的第 38-60 行一起看。
"""
from __future__ import annotations

import unicodedata


def show(title: str) -> None:
    print(f"\n{'=' * 66}\n{title}\n{'=' * 66}")


# ---------------------------------------------------------------
show("[1] 为什么 len() 不够用")
# ---------------------------------------------------------------
for text in ["版本", "方案A conda", "Python", "版本版本"]:
    print(f'  len("{text}") = {len(text):<3}  但终端里实际占 {sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in text)} 列')

print("\n  → 结论：一个中文字符 len 算 1，显示占 2。差一倍。")
print("  → 所以 f\"{x:<12}\" 是按 len 补空格的，遇到中文必然错位。")

# ---------------------------------------------------------------
show("[2] east_asian_width 给每个字符的宽度分类")
# ---------------------------------------------------------------
for ch in ["版", "A", " ", "（", "(", "✅", "→"]:
    cat = unicodedata.east_asian_width(ch)
    wide = cat in "WF"
    print(f'  {ch!r:<6} 分类={cat:<2} 是否双宽={wide!s:<5} 占 {2 if wide else 1} 列')

print("\n  分类含义：W=宽(全角) F=全角形式 → 都算 2 列")
print("            Na=窄  N=中性  A=歧义  H=半角 → 算 1 列")
print("  注意 ✅ 被归为 W，也算 2 列 —— 这就是为什么带 emoji 的行更难对齐。")
print("  而 → 是 A(歧义)，不同终端可能算 1 列也可能算 2 列，属于不可靠字符，尽量别用。")

# ---------------------------------------------------------------
show("[3] dwidth() 那一行代码，逐层拆开")
# ---------------------------------------------------------------
text = "方案A conda"
print(f'  输入 text = "{text}"\n')

step1 = [c for c in text]
print(f"  第0步 拆成字符        {step1}")

step2 = [(c, unicodedata.east_asian_width(c)) for c in text]
print(f"  第1步 每个字符的分类  {step2}")

step3 = [2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in text]
print(f"  第2步 分类换算成列数  {step3}")

print(f"  第3步 全部加起来      sum({step3}) = {sum(step3)}")
print(f"\n  合起来就是一行：sum(2 if ... else 1 for c in text) = {sum(step3)}")

# ---------------------------------------------------------------
show("[4] 三元表达式：if-else 写成一行")
# ---------------------------------------------------------------
n = 5
# 普通写法
if n > 3:
    big = "大于3"
else:
    big = "不大于3"
# 一行写法
big_inline = "大于3" if n > 3 else "不大于3"
print(f'  普通 if/else  -> "{big}"')
print(f'  一行三元写法  -> "{big_inline}"   ← 两者完全等价')
print("\n  语法：值A if 条件 else 值B    （条件成立取A，否则取B）")
print("  读法：从中间往两边读 —— 「如果条件成立，就是A，否则是B」")

# ---------------------------------------------------------------
show('[5] in "WF" 是什么')
# ---------------------------------------------------------------
print('  "WF" 就是一个长度为 2 的字符串，等价于 ["W", "F"] 的简写')
for cat in ["W", "F", "N", "A"]:
    print(f'  {cat!r} in "WF" -> {cat in "WF"}')
print("\n  等价于： cat == \"W\" or cat == \"F\"")

# ---------------------------------------------------------------
show("[6] pad() 为什么外面要套 max(..., 0)")
# ---------------------------------------------------------------


def dwidth(text: str) -> int:
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in text)


for target_w, label in [(11, "版本"), (11, "方案A conda"), (11, "超长超长超长超长标签")]:
    need = target_w - dwidth(label)
    if need < 0:
        note = f"   ⚠️ 负数！max({need}, 0) = {max(need, 0)} → 补 0 个，不会崩"
    else:
        note = f"   max({need}, 0) = {max(need, 0)}"
    print(f'  目标宽 {target_w}，"{label}" 宽 {dwidth(label)}  → 需要补 {need} 个空格{note}')
    print(f'     结果："{label + " " * max(need, 0)}"')

print("\n  → max(负数, 0) 是防御性写法：某行比目标宽度还长时，")
print("    需要补的空格是负数；虽然 \" \" * -9 也只是得到空字符串不报错，")
print("    但显式钳成 0 让意图清楚，也防止以后把 need 用到别的地方（比如切片）时出错。")

# ---------------------------------------------------------------
show("[7] print_rows() 的两步走：先量最宽，再统一补")
# ---------------------------------------------------------------
rows = [
    ("版本", "3.13.9  (64bit)"),
    ("可执行文件", "D:\\Anaconda3\\python.exe"),
    ("虚拟环境", "❌ 未激活"),
    ("方案A conda", "conda activate ai"),
    ("方案B venv", r".\.venv\Scripts\Activate.ps1"),
    ("判断依据", "命令行前面出现 (ai)"),
]

print("  第1步：遍历所有标签，找最宽的")
widths = [dwidth(label) for label, _ in rows]
for (label, _), w in zip(rows, widths):
    print(f"     {label:<14} -> {w}")
label_w = max(widths)
print(f"     max(...) = {label_w}  ← 这就是对齐基准")

print("\n  第2步：每个标签都补到", label_w, "列，再打印")
indent = "  "
for label, value in rows:
    padded = label + " " * max(label_w - dwidth(label), 0)
    print(f"     {indent}{padded}: {value}")

print("\n  对比：如果不用 label_w，而是写死 {label:<11}")
for label, value in rows:
    print(f"     {indent}{label:<11}: {value}")
print("  ↑ 看到没？中文行全歪了。因为 :<11 按 len 补，不知道中文占 2 列。")

# ---------------------------------------------------------------
show("[8] for label, _ in rows 里的下划线")
# ---------------------------------------------------------------
for label, _ in rows[:2]:
    print(f"  只取标签：{label}")
print("\n  _ 是约定：「这个位置的值我不用」。")
print("  写成 for label, value in rows 也能跑，但读的人不知道 value 到底用没用。")
print("  用 _ 等于在说：第二个元素我故意丢弃。")

# ---------------------------------------------------------------
show("[9] append 和 extend 的区别（check_interpreter 里两个都用了）")
# ---------------------------------------------------------------
demo = [("a", "1")]
demo.append(("b", "2"))
print(f"  append 加「一个元素」      -> {demo}")

demo.extend([("c", "3"), ("d", "4")])
print(f"  extend  加「一批元素」     -> {demo}")

wrong = [("x", "9")]
wrong.append([("y", "8")])
print(f"  ⚠️ extend 写成 append 会这样 -> {wrong}")
print("     多套了一层方括号，后面解包 for label, value in wrong 会直接报错。")

print("\n✅ 演示结束。把这里的数字和 01_check_env.py 的输出对照着看。")
