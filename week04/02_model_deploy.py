#!/usr/bin/env python3
"""W4 实验③：模型部署日 —— 把训练成果当成"产品零件"用。

前情：周一训练并存了 digits_net.pt（32宽网络，测试 0.9756）。
今天不训练！扮演"拿到别人交付的模型的工程师"：
  ① 加载存档 → 复现准确率（验收交付物）
  ② 把错例揪出来看（错误分析 —— 一切优化的起点）
  ③ 给图片加噪声/平移，看准确率怎么崩（鲁棒性 = 产品的抗打击能力）
  ④ 把模型包成一个 predict_one() 函数（这就是"API 的雏形"）

跑法：python week04\\02_model_deploy.py   （需要先有 week04\\digits_net.pt，
                                          没有就先跑一遍 00_nn_lab.py 生成）
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from sklearn.datasets import load_digits
from sklearn.model_selection import train_test_split

BASE = Path(__file__).resolve().parent
CKPT = BASE / "digits_net.pt"
if not CKPT.is_file():
    raise SystemExit(f"❌ 找不到 {CKPT}，先跑：python week04\\00_nn_lab.py")

# ── ① 加载存档：结构和参数缺一不可 ────────────────────────────
net = nn.Sequential(nn.Linear(64, 32), nn.ReLU(), nn.Linear(32, 10))  # 结构必须和训练时一致
net.load_state_dict(torch.load(CKPT, weights_only=True))
net.eval()
print(f"✅ 已加载模型：{CKPT}（{CKPT.stat().st_size/1024:.0f} KB）")

# ── 复现验收：和训练那天对比，误差应为 0 ──────────────────────
d = load_digits()
X_tr, X_te, y_tr, y_te = train_test_split(d.data, d.target, test_size=0.25, random_state=42)
Xe = torch.tensor(X_te, dtype=torch.float32)
ye = torch.tensor(y_te, dtype=torch.long)
with torch.no_grad():
    acc = (net(Xe).argmax(1) == ye).float().mean().item()
print(f"① 验收：测试准确率 = {acc:.4f}（训练那天是 0.9756，一致 = 交付无损）")

# ── ② 错误分析：把 11 个错例的"脸"挖出来看 ────────────────────
with torch.no_grad():
    scores = net(Xe)
    preds = scores.argmax(1)
wrong = (preds != ye).nonzero().flatten().tolist()
print(f"\n② 错误分析：{len(Xe)} 张里错了 {len(wrong)} 张")
for idx in wrong[:6]:
    img = X_te[idx]
    truth, pred = int(y_te[idx]), int(preds[idx])
    conf = torch.softmax(scores[idx], dim=0)[pred].item()
    print(f"\n  第{idx:>3}张：真={truth} 判={pred}（模型对这个错误答案的自信度 {conf:.0%}）")
    for r in range(8):
        print("    " + "".join(" .:*#@"[int(v) // 3] for v in img[r * 8:(r + 1) * 8]))

print("""
  看的时候想两件事：
  a) 这些图在人眼里"像什么"？（有些手写体确实暧昧——错误不全是模型的锅）
  b) 自信度 90%+ 的错 vs 40% 的错，处理策略该一样吗？
     —— 后者其实可以"我不确定，请人工看"，这就是产品里的「置信度阈值」
""")

# ── ③ 鲁棒性：给输入搞破坏，看模型还能不能活 ─────────────────
rng = np.random.default_rng(0)
print("③ 鲁棒性测试（同一批 450 张考卷）：")

# 基线
print(f"  干净图片          准确率 = {acc:.4f}")

# 加高斯噪声
Xn = X_te + rng.normal(0, 1.0, X_te.shape)
with torch.no_grad():
    acc_n = (net(torch.tensor(Xn, dtype=torch.float32)).argmax(1) == ye).float().mean().item()
print(f"  加噪声(σ=1.0)     准确率 = {acc_n:.4f}")

# 平移 1 像素
Xs = np.roll(X_te, 1, axis=1).reshape(-1, 8, 8)
Xs = Xs.reshape(-1, 64)
with torch.no_grad():
    acc_s = (net(torch.tensor(Xs, dtype=torch.float32)).argmax(1) == ye).float().mean().item()
print(f"  右移1像素         准确率 = {acc_s:.4f}")

print("""
  解读：
  · 噪声掉一点 = 正常（模型学的是"笔画模式"，一点雪花顶得住）
  · 平移掉很多 = 重大发现！这个网络只认"位置"不认"形状"——
    它学到的是"第23号像素亮=3"这种死记硬背，而不是"上面有个圈"。
    真实图像识别为什么必须用卷积网络(CNN)？今天你亲手摸到了答案的一半。
    （另一半：数据增强，让模型见过平移过的图——W5 预告）
""")

# ── 置信度阈值实验 ──────────────────────────────────────────
with torch.no_grad():
    probs = torch.softmax(net(Xe), dim=1)          # 每张图 10 个类的概率
    conf, pred = probs.max(dim=1)                  # 取最高概率 = 置信度

threshold = 0.9
answered = conf >= threshold                        # 布尔数组：True=愿意答
abstained = ~answered                               # 放弃

n_abstain = int(abstained.sum())
correct_in_abstain = int((pred[abstained] == ye[abstained]).sum())
wrong_in_answer = int((pred[answered] != ye[answered]).sum())
n_answer = int(answered.sum())

print(f"\n阈值 0.9 实验：")
print(f"  主动放弃 {n_abstain} 张（占 {n_abstain/len(ye):.1%}）")
print(f"  放弃堆里有 {correct_in_abstain} 张本来是对的（＝白放弃了）")
print(f"  回答的 {n_answer} 张里错 {wrong_in_answer} 张")
print(f"  回答部分的准确率 = {(n_answer-wrong_in_answer)/n_answer:.4f}（原始 {acc:.4f}）")
print("\n")

# ── ④ 封装成函数：模型的"API 化" ─────────────────────────────
def predict_one(flat_pixels: list[float]) -> tuple[int, float]:
    """输入 64 个像素值，返回 (预测数字, 置信度)。这就是一个最小'模型API'。"""
    x = torch.tensor([flat_pixels], dtype=torch.float32)
    with torch.no_grad():
        s = torch.softmax(net(x), dim=1)[0]
    p = int(s.argmax())
    return p, float(s[p])

# 用它接单张图
p, c = predict_one(X_te[0].tolist())
print(f"④ predict_one 测试：第0张 → 预测 {p}（置信度 {c:.0%}），真实 {y_te[0]}")

print("""
════════ 观察与思考（写进 notes\\W4.md）════════
 1. 错例里挑一张你觉得"人也会犹豫"的，和一张"明显是模型瞎了"的，
    分别贴 ASCII 图。
 2. 平移实验掉了多少分？用一句话向朋友解释"为什么这个模型怕挪位置"。
 3. 如果把置信度阈值设成 0.9：低于 0.9 就回答"我不确定"——
    算一下：450 张里模型会主动放弃多少张？放弃的那部分里有多少本来
    是错的？（提示：这就是 precision/recall 的工程用法，W13 正式登场）
 4. 今天全程没有训练。体会一下"用模型"和"训模型"是两种完全不同的
    工作——周四开始你连'用'的都是别人的（大模型），这个角色转换
    正是 AI 应用工程师的日常。

════════ 今天的交付 ════════
 跑通 → 思考 3 的数字算出来 → commit + push
""")
