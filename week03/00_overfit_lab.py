#!/usr/bin/env python3
"""W3 实验①：过拟合实验室 —— 亲手制造一次"训练满分、考试零分"。

原理预告（先读这段再跑）：
  模型训练 = 调参数让"训练数据"上的误差变小。
  但我们要的从来不是"背住训练数据"，而是"对新数据也准"（泛化）。
  模型能力（容量）太大 + 数据太少太噪 = 开始背题 = 过拟合。
  背题的代价：训练误差一路走低，新数据误差先降后升——那条 U 型曲线
  就是机器学习里最重要的一条曲线。

本实验：真规律是一条正弦曲线，撒 30 个带噪声的采样点，
让 1 次 ~ 15 次的多项式去拟合它，看谁在背题。

跑之前先装依赖（只需一次）：
    pip install scikit-learn -i https://mirrors.aliyun.com/pypi/simple

跑法：
    python week03\\00_overfit_lab.py

产出：终端一张"次数 vs 训练误差 vs 测试误差"表 + 过拟合实验室.png
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import make_pipeline
from sklearn.metrics import mean_squared_error

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

OUT_PNG = Path(__file__).resolve().parent / "过拟合实验室.png"
RNG = np.random.default_rng(42)      # 固定随机种子：结果可复现（重要习惯）

# ── 1. 造数据：真规律 sin(x)，加噪声，共 30 个点 ─────────────
X = np.sort(RNG.uniform(0, 2 * np.pi, 30))
y = np.sin(X) + RNG.normal(0, 0.35, size=30)

# ── 2. 拆考卷：24 个用于训练，6 个藏起来当"新题" ──────────────
#     train_test_split 默认会打乱再拆——藏起来的 6 个点模型永远见不到，
#     它们在测试时的表现才叫"泛化"。shuffle=True 是默认值。
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=0)

# ── 3. 不同"次数"（=模型容量）各训一个，记录两种误差 ──────────
degrees = [1, 2, 3, 6, 9, 12, 15]
train_errs, test_errs, models = [], [], {}

for d in degrees:
    # pipeline = 两步流水：先做多项式特征(x→x,x²,...,x^d)，再线性回归
    model = make_pipeline(PolynomialFeatures(degree=d), LinearRegression())
    model.fit(X_train.reshape(-1, 1), y_train)          # 学习
    models[d] = model
    train_errs.append(mean_squared_error(y_train, model.predict(X_train.reshape(-1, 1))))
    test_errs.append(mean_squared_error(y_test, model.predict(X_test.reshape(-1, 1))))

# ── 4. 成绩单 ────────────────────────────────────────────────
print(f"{'次数':>4} {'训练误差MSE':>12} {'测试误差MSE':>12}   判词")
print("-" * 56)
for d, tr, te in zip(degrees, train_errs, test_errs):
    if d == 1:
        verdict = "欠拟合：直线根本弯不过来（连题都看不懂）"
    elif tr == min(train_errs):
        verdict = "背题冠军：训练误差最低，但测试误差呢？"
    elif te == min(test_errs):
        verdict = "★ 甜点位：测试误差最低 = 该选这个模型"
    else:
        verdict = ""
    print(f"{d:>4} {tr:>12.4f} {te:>12.4f}   {verdict}")

best = degrees[int(np.argmin(test_errs))]
print(f"\n结论：训练误差一路下降（模型越来越会背），"
      f"\n但测试误差在 次数={best} 处最低，之后反弹 —— 这条 U 型就是过拟合。")
print("选模型的标准从来不是'训练得多好'，是'对新数据多好'。")

# ── 5. 画图：三格对比 欠拟合 / 甜点位 / 过拟合 ─────────────────
fig, axes = plt.subplots(1, 3, figsize=(15, 4.6), sharey=True)
xx = np.linspace(0, 2 * np.pi, 300)
titles = {1: "欠拟合（次数=1）：连规律都装不下",
          best: f"甜点位（次数={best}）：测试误差最低",
          15: "过拟合（次数=15）：把噪声都背下来了"}
for ax, d in zip(axes, [1, best, 15]):
    pred = models[d].predict(xx.reshape(-1, 1))
    ax.scatter(X_train, y_train, s=30, color="#C55A11", label="训练点(带噪声)")
    ax.scatter(X_test, y_test, s=30, color="#548235", marker="s", label="测试点(藏起来的)")
    ax.plot(xx, np.sin(xx), "k--", lw=1, alpha=0.6, label="真规律 sin(x)")
    ax.plot(xx, pred, color="#2F6EA5", lw=2, label=f"{d} 次拟合")
    ax.set_title(titles[d], fontsize=10)
    ax.set_ylim(-2.5, 2.5)
    ax.legend(fontsize=8)
axes[0].set_ylabel("y")
fig.suptitle("同一个数据，三种模型容量 —— 过拟合不是玄学，是这条 U 型曲线")
fig.tight_layout()
fig.savefig(OUT_PNG, dpi=130)
print(f"\n✅ 图已保存：{OUT_PNG}")

# ── 6. 留三个观察任务（看图回答，答案都在图里）───────────────
print("""
观察任务：
 1. 次数=15 那条蓝线，为了穿过每个训练点，在点之间做了什么动作？
    （真规律 sin 有这么扭吗？）
 2. 绿色方块（测试点）离蓝线远不远？这说明"训练误差"和"对新数据的表现"
    是什么关系？
 3. 把数据量从 30 改成 300（第 33 行 size=30 → 300，两处 30 都要改）重跑，
    过拟合还这么严重吗？—— 这是治过拟合的第一味药：加数据。
""")
