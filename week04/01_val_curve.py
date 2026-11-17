#!/usr/bin/env python3
"""W4 实验②：验证集 + 深网络 —— 让 U 型曲线在神经网络身上显形。

今天两个升级：
  ① 数据拆三份：练习册(train) 75% + 模拟考(valid) 12.5% + 高考(test) 12.5%
     —— 模拟考用来"边训练边观察 + 调旋钮选模型"，高考只在最后用一次。
     为什么不能拿高考当模拟考？因为你会不自觉按高考分数挑模型，
     高考就变成"提前见过的题"，分数失真。三份拆法是 ML 的标准姿势。
  ② 网络加深：64→32→32→10（两个隐藏层，旋钮 2730 个）
     训练时每一轮同时记录 train loss 和 valid loss ——
     周一过拟合实验的 U 型，今天将原样出现在真神经网络身上。

跑法：python week04\\01_val_curve.py
产出：U型曲线.png + 一段"最佳轮数"报告
"""
from __future__ import annotations

from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader
from sklearn.datasets import load_digits
from sklearn.model_selection import train_test_split
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

BASE = Path(__file__).resolve().parent
torch.manual_seed(42)

# ── 1. 数据拆三份 ────────────────────────────────────────────
d = load_digits()
# 先切出 25% 当高考卷
X_tr, X_te, y_tr, y_te = train_test_split(d.data, d.target, test_size=0.25, random_state=42)
# 剩下的再切 1/3 当模拟考（即总量的 25%）
X_tr2, X_va, y_tr2, y_va = train_test_split(X_tr, y_tr, test_size=1/3, random_state=42)
print(f"练习册 {len(X_tr2)} 张 | 模拟考 {len(X_va)} 张 | 高考 {len(X_te)} 张")

Xt = torch.tensor(X_tr2, dtype=torch.float32); yt = torch.tensor(y_tr2, dtype=torch.long)
Xv = torch.tensor(X_va, dtype=torch.float32);  yv = torch.tensor(y_va, dtype=torch.long)
Xe = torch.tensor(X_te, dtype=torch.float32);  ye = torch.tensor(y_te, dtype=torch.long)
loader = DataLoader(TensorDataset(Xt, yt), batch_size=64, shuffle=True)

# ── 2. 更深一点的网络（今天的主角之一）────────────────────────
net = nn.Sequential(
    nn.Linear(64, 128), nn.ReLU(),
    nn.Linear(128, 128), nn.ReLU(),      # ← 新加的隐藏层
    nn.Linear(128, 10),
)
print(f"参数量：{sum(p.numel() for p in net.parameters())} 个（昨天是 2410）")

loss_fn = nn.CrossEntropyLoss()
opt = torch.optim.Adam(net.parameters(), lr=0.01)

# ── 3. 训练 + 每轮双记录 ──────────────────────────────────────
EPOCHS = 80
train_losses, valid_losses, valid_accs = [], [], []

for epoch in range(1, EPOCHS + 1):
    # --- 训练阶段（四步循环，昨天已熟）---
    net.train()
    total = 0.0
    for xb, yb in loader:
        loss = loss_fn(net(xb), yb)
        opt.zero_grad(); loss.backward(); opt.step()
        total += loss.item() * len(xb)
    train_losses.append(total / len(Xt))

    # --- 模拟考阶段：只答题，不改旋钮 ---
    net.eval()
    with torch.no_grad():
        vloss = loss_fn(net(Xv), yv).item()
        vacc = (net(Xv).argmax(1) == yv).float().mean().item()
    valid_losses.append(vloss)
    valid_accs.append(vacc)

    if epoch % 10 == 0 or epoch == 1:
        print(f"  第{epoch:>3}轮  train={train_losses[-1]:.4f}  valid={vloss:.4f}  模拟考准确率={vacc:.4f}")

# ── 4. 找 U 型的谷底 + 早停点 ─────────────────────────────────
best_epoch = int(torch.tensor(valid_losses).argmin().item()) + 1
print(f"\n★ valid loss 最低点在第 {best_epoch} 轮（{valid_losses[best_epoch-1]:.4f}）")
print(f"  此后 train 继续降、valid 回升 —— 两线分岔 = 模型开始背练习册了")

# ── 5. 高考：用"模拟考最佳轮"的模型去考，才算真成绩 ───────────
# 简化做法：重新训练到 best_epoch 就停（真实项目用"存档最佳模型"的做法）
torch.manual_seed(42)
net2 = nn.Sequential(nn.Linear(64,128), nn.ReLU(), nn.Linear(128,128), nn.ReLU(), nn.Linear(128,10))
opt2 = torch.optim.Adam(net2.parameters(), lr=0.01)
for epoch in range(1, best_epoch + 1):
    net2.train()
    for xb, yb in loader:
        loss = loss_fn(net2(xb), yb)
        opt2.zero_grad(); loss.backward(); opt2.step()
net2.eval()
with torch.no_grad():
    final_acc = (net2(Xe).argmax(1) == ye).float().mean().item()
print(f"\n★ 高考准确率（只训到第 {best_epoch} 轮就停）：{final_acc:.4f}")
net.eval()
with torch.no_grad():
    full_epochs_acc = (net(Xe).argmax(1) == ye).float().mean().item()
print(f"★ 高考准确率（傻训满 {EPOCHS} 轮）：{full_epochs_acc:.4f}")

# ── 6. 画图：两条 loss 线 + 谷底标注 ──────────────────────────
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
ax1.plot(train_losses, label="train loss（练习册）", color="#2F6EA5")
ax1.plot(valid_losses, label="valid loss（模拟考）", color="#C55A11")
ax1.axvline(best_epoch, ls="--", color="gray", alpha=0.7, label=f"谷底=第{best_epoch}轮")
ax1.set_xlabel("轮数"); ax1.set_ylabel("loss")
ax1.set_title("神经网络身上的完整 U 型：分岔之后各自去哪")
ax1.legend()
ax2.plot(valid_accs, label="模拟考准确率", color="#548235")
ax2.axvline(best_epoch, ls="--", color="gray", alpha=0.7)
ax2.set_xlabel("轮数"); ax2.set_ylabel("准确率")
ax2.set_title("准确率最高点 ≈ loss 谷底（同一件事两张脸）")
ax2.legend()
fig.tight_layout()
out = BASE / "U型曲线3.png"
fig.savefig(out, dpi=130)
print(f"\n✅ 图已存：{out}")

print(f"""
════════ 观察与思考（写进 notes\\W4.md）════════
 1. 两线在第几轮开始分岔？分岔前它们贴得紧吗？为什么前期能同步？
 2. 训满 {EPOCHS} 轮 vs 只训到第 {best_epoch} 轮，高考分谁高？
    —— 这就是「早停(early stopping)」：不是练得越久越好，
    在"还在进步"的时候收手，才是最优解。
 3. 把隐藏层从 32 改成 128（两处都改），重跑：分岔点提前还是推后？
    容量↑ = 背题能力↑ = 更早过拟合 —— 昨天的幽灵换了张脸回来。
 4. 数据只有 1122 张练习册。如果把它砍到 100 张（train_test_split 加
    参数或用 X_tr2[:100]），U 型会长成什么样？—— 这就是「数据量 vs
    容量」三角关系的第三味药：加数据能推迟分岔。

════════ 今天的交付 ════════
 跑通 → 打开 U型曲线.png → 做完思考 2 和 3 → commit + push
""")
