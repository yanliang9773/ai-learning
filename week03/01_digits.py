#!/usr/bin/env python3
"""W3 实验②：手写数字识别 —— 从"拟合曲线"毕业到"真正的机器学习任务"。

任务：给模型看 8×8 像素的手写数字照片（1435 张），让它学会认 0~9。
这是 sklearn 的"hello world"，但五脏俱全：
  数据 → 拆考卷 → 训练 → 考核 → 看错在哪 → 玩旋钮制造过拟合/欠拟合

跑法：
    python week03\\01_digits.py            # 完整跑（约 10 秒）

观察重点在输出最后，先跑再看解释。
"""
from __future__ import annotations
import matplotlib.pyplot as plt
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

import numpy as np
from sklearn.datasets import load_digits
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import classification_report, confusion_matrix

# ── 1. 数据长什么样 ──────────────────────────────────────────
digits = load_digits()
X, y = digits.data, digits.target          # X: (1797, 64)  y: (1797,)
print(f"数据形状：X={X.shape}（1797 张图 × 64 像素）  y={y.shape}（每张的标签 0~9）")

print("\n一张'数字 0'的原始像素（0=黑 15=白）——所谓'照片'就这么寒酸：")
img = X[0]                                 # 第 0 张，标签是 0
for r in range(8):
    row = "".join(" .:*#@"[int(v) // 3] for v in img[r * 8:(r + 1) * 8])
    print(f"    {row}      ← 标签 = {y[0]}")

# ── 2. 拆考卷：75% 练习册 + 25% 考场 ─────────────────────────
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.25, random_state=42)
print(f"\n训练集 {len(X_train)} 张，测试集 {len(X_test)} 张（模型没见过）")

# ── 3. 基线模型：KNN，k=5 ────────────────────────────────────
# KNN 原理一句话：新图进来，找和它"像素距离"最近的 k 张练习册图，
# 谁多听谁的（投票）。没有参数可"背"，但 k 这个旋钮决定它是
# "只听 1 个邻居的偏听狂"还是"和稀泥的多数派"。
model = KNeighborsClassifier(n_neighbors=5)
model.fit(X_train, y_train)
acc = model.score(X_test, y_test)
print(f"\n★ 基线准确率（k=5）：{acc:.4f}")

# ── 4. 错在哪：报告 + 混淆矩阵 ───────────────────────────────
print("\n每个数字的考核明细（precision=报它时准不准 recall=它来时认出多少）：")
print(classification_report(y_test, model.predict(X_test), digits=3))

cm = confusion_matrix(y_test, model.predict(X_test))
print("混淆矩阵（行=真实 列=模型判的，非零处=认错）：")
print("      " + "".join(f"{j:>5}" for j in range(10)))
for i, row in enumerate(cm):
    marks = "".join(f"{v:>5}" if v else "    ·" for v in row)
    print(f"  {i:>3}  {marks}")
# 找最严重的一对
worst = (0, 0, 0)
for i in range(10):
    for j in range(10):
        if i != j and cm[i][j] > worst[0]:
            worst = (cm[i][j], i, j)
print(f"\n认错最多的一对：真 {worst[1]} 被判成 {worst[2]}，共 {worst[0]} 次")

# ── 5. 旋钮实验：k 从小到大扫一遍，画准确率曲线 ──────────────
print("\nk 值扫描（同一份考卷，只改 k）：")
print(f"{'k':>4} {'训练准确率':>10} {'测试准确率':>10}  判词")
print("-" * 58)
for k in (1, 3, 5, 15, 50, 150):
    m = KNeighborsClassifier(n_neighbors=k)
    m.fit(X_train, y_train)
    tr, te = m.score(X_train, y_train), m.score(X_test, y_test)
    if k == 1:
        v = "偏听狂：一个邻居定生死（训练100%是背题的症状）"
    elif k >= 150:
        v = "和稀泥：谁票多听谁→干脆全认'多数派数字'（欠拟合）"
    else:
        v = ""
    print(f"{k:>4} {tr:>10.4f} {te:>10.4f}  {v}")


ks = list(range(1, 151, 10))
train_scores, test_scores = [], []
for k in ks:
    m = KNeighborsClassifier(n_neighbors=k)
    m.fit(X_train, y_train)
    tr = m.score(X_train, y_train)
    te = m.score(X_test, y_test)
    train_scores.append(tr)                            # 空1：把 tr 装进篮子 
    test_scores.append(te)                             # 空2：把 te 装进篮子               
    
    
# 空3：两条 plt.plot（想想 label 和 marker 怎么写）
plt.plot(ks,train_scores , marker="o", label="训练")
plt.plot(ks,test_scores, marker="s", label="测试")

# 空4：legend/title/savefig 三件套
plt.xlabel("k（邻居数）")
plt.ylabel("准确率")
plt.title("KNN 的 k 扫描：训练 vs 测试")
plt.savefig("k扫描.png", dpi=130)



print("""
════════ 今天的四个问题（答案都在上面的输出里，用笔记写）════════
 Q1  k=1 时训练准确率是不是 1.0？为什么它反而是"背题"的？
     （提示：新图进来只问 1 个最像的练习册邻居——邻居本身可能带错/噪声）
 Q2  k=150 训练和测试一起变差 —— 对照昨天的 U 型，这叫什么？
 Q3  混淆矩阵里最严重那对（大概率 4↔9 或 1↔7/3↔8）：
     把那两个数字的像素图想象一下，为什么机器分不清、人却分得清？
 Q4  测试集 449 张（=1797×0.25），比昨天过拟合实验的 6 个点大多了。
     现在 0.96x 这种小数点后的差距，可信度变高了吗？为什么？

════════ 动手任务（做完 commit）════════
 A. 把 test_size 改成 0.01 重跑：分数波动剧烈了吗？（考卷又小了）
 B. 自己加一个旋钮实验：把某张训练图的标签人为改错
    （比如 X_train[0] 的 y_train[0] 从 5 改成 3），k=1 和 k=5 谁扛住了？
    —— 这就是"离群点/脏标签"对模型的危害，W1 数据清洗思想的 ML 版
 C. 把 k 扫描的结果画成折线图（x=k, y=训练/测试准确率，两条线）
    —— matplotlib 你早就会了，自己写，卡住别问，先猜
""")
