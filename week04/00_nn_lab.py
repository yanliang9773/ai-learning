#!/usr/bin/env python3
"""W4 实验①：亲手训练第一个神经网络（PyTorch 版 digits 识别）。

和周三 KNN 的本质区别：
  KNN：不学习，靠"翻练习册找相似"（k 是唯一旋钮）
  神经网络：真的在"调几十万个旋钮"——训练过程 = 四步循环 × 很多轮

训练循环四步（本文件的心脏，背下来）：
  ① 前向传播：x 进网络 → 得到预测 y_hat
  ② 算损失：  y_hat 和真实 y 差多远（loss）
  ③ 反向传播：自动算出"每个旋钮该往哪拧多少"（梯度）
  ④ 更新参数：optimizer 真的去拧一下
  ... 回到 ①，直到 loss 不再明显下降

跑法（先装好 torch）：
    python week04\\00_nn_lab.py

产出：每轮 loss + 最终测试准确率 + nn训练曲线.png + 存盘的模型文件
"""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader
from sklearn.datasets import load_digits
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

BASE = Path(__file__).resolve().parent
torch.manual_seed(42)                      # 你已懂：固定随机=实验可复现

# ── 1. 数据：和周三同一份，但形状要喂成 PyTorch 的样子 ─────────
digits = load_digits()
X, y = digits.data, digits.target
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.25, random_state=42)

Xt = torch.tensor(X_train, dtype=torch.float32)
yt = torch.tensor(y_train, dtype=torch.long)
Xe = torch.tensor(X_test, dtype=torch.float32)
ye = torch.tensor(y_test, dtype=torch.long)

loader = DataLoader(TensorDataset(Xt, yt), batch_size=64, shuffle=True)
print(f"数据：训练 {len(Xt)} 张 / 测试 {len(Xe)} 张，batch=64 → 每轮 {len(loader)} 个批次")

# ── 2. 网络：64 输入 → 32 隐藏 → 10 输出，总共 2410 个旋钮 ─────
net = nn.Sequential(
    nn.Linear(64, 32),     # 第 1 层：64 个像素 → 32 个特征
    nn.ReLU(),             # 非线性开关：没有它，两层等于一层
    nn.Linear(32, 10),     # 第 2 层：32 个特征 → 10 个数字的打分
)
n_params = sum(p.numel() for p in net.parameters())
print(f"网络参数量：{n_params} 个 —— 训练就是在调这 {n_params} 个旋钮")

# ── 3. 损失函数 + 优化器 ──────────────────────────────────────
loss_fn = nn.CrossEntropyLoss()             # 分类标配：输出打分→概率→对错
opt = torch.optim.Adam(net.parameters(), lr=0.5)   # lr=每次拧多大，重要旋钮！

# ── 4. 训练循环：四步的心脏在这里 ─────────────────────────────
EPOCHS = 30
history = []                                 # 篮子（你已会）
t0 = time.time()

for epoch in range(1, EPOCHS + 1):
    total = 0.0
    for xb, yb in loader:                    # 一批一批喂（64 张一起算）
        y_hat = net(xb)                      # ① 前向传播
        loss = loss_fn(y_hat, yb)            # ② 算损失
        opt.zero_grad()                      # （清掉上一轮的梯度，必做！）
        loss.backward()                      # ③ 反向传播：算梯度
        opt.step()                           # ④ 更新参数：拧旋钮
        total += loss.item() * len(xb)
    avg = total / len(Xt)
    history.append(avg)
    if epoch == 1 or epoch % 5 == 0 or epoch == EPOCHS:
        print(f"  第 {epoch:>2} 轮  loss = {avg:.4f}")

print(f"\n训练完成，用时 {time.time()-t0:.1f} 秒")

# ── 5. 考核：测试集上打分（模型没见过）────────────────────────
net.eval()                                    # 切换成"考试模式"
with torch.no_grad():                         # 考试不算梯度，省内存
    preds = net(Xe).argmax(dim=1)
acc = (preds == ye).float().mean().item()
print(f"★ 测试准确率：{acc:.4f}   （KNN 基线是 0.9933，谁强？）")
print("\n每类明细（周三的老朋友）：")
print(classification_report(ye.numpy(), preds.numpy(), digits=3))

# ── 6. 存模型：训练成果第一次变成可带走的文件 ──────────────────
ckpt = BASE / "digits_net.pt"
torch.save(net.state_dict(), ckpt)
print(f"✅ 模型已存盘：{ckpt}（{ckpt.stat().st_size/1024:.0f} KB，{n_params} 个旋钮的最终位置）")

# 现场复活验证：新建一个网络，灌入存档，准确率必须和刚才一致
net2 = nn.Sequential(nn.Linear(64, 32), nn.ReLU(), nn.Linear(32, 10))
net2.load_state_dict(torch.load(ckpt, weights_only=True))
net2.eval()
with torch.no_grad():
    acc2 = (net2(Xe).argmax(dim=1) == ye).float().mean().item()
print(f"✅ 复活验证：新网络灌入存档后准确率 {acc2:.4f} —— 和上面一致 = 存/读无损")

# ── 7. loss 曲线图：你见过的 U 型换了个面孔 ────────────────────
fig, ax = plt.subplots(figsize=(9, 5))
ax.plot(range(1, EPOCHS + 1), history, marker="o", ms=4, color="#2F6EA5", label="训练 loss")
ax.set_xlabel("轮数 epoch")
ax.set_ylabel("loss（平均）")
ax.set_title("第一次亲手训练：loss 从 ~2.3 掉下来的全过程")
ax.grid(alpha=0.3)
ax.legend()
fig.tight_layout()
out = BASE / "nn训练曲线2.png"
fig.savefig(out, dpi=130)
print(f"✅ 曲线已存：{out}")

print(f"""
════════ 观察与思考（写进 notes\\W4.md）════════
 1. 起点 loss≈2.3：瞎猜 10 个数字的期望损失是 ln(10)=2.30 —— 训练开始时
    模型真的在瞎猜。loss 掉到 0.0x = 几乎确定地答对。
 2. 曲线前几轮掉得猛、后面变平缓 —— 为什么？（旋钮快拧到最优点了）
 3. 把 lr=0.01 改成 0.5 重跑：loss 可能不降反升/震荡 —— 旋钮一次拧过头。
    再改成 0.0001：几乎不动。lr 是训练里最重要的旋钮，你已亲手摸过两端。
 4. 把 nn.Linear(64, 32) 的 32 改成 2：参数量暴跌，准确率会怎样？
    —— 这就是"模型容量"旋钮，周一的 k、昨天的 32，同一个幽灵。
 5. opt.zero_grad() 那行删掉试试（然后加回来）：为什么必须清梯度？
    —— 梯度是"累加"的，不清就是拿旧账一起拧。

════════ 今天的交付 ════════
 python week04\\00_nn_lab.py 跑通 → 打开 nn训练曲线.png
 → 做完思考 3（lr 两端实验）→ commit + push
""")
