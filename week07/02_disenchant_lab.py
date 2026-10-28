#!/usr/bin/env python3
"""祛魅实验室 —— 4 个离线小实验，把大模型的四个"魔法"拆成普通代码。

跑法（一次一个，推荐按顺序）：
    python week07\\02_disenchant_lab.py 1     # token 与流式输出
    python week07\\02_disenchant_lab.py 2     # temperature 到底是什么
    python week07\\02_disenchant_lab.py 3     # 上下文窗口撑爆会发生什么
    python week07\\02_disenchant_lab.py 4     # 迷你 RAG：检索决定列表里放什么
    python week07\\02_disenchant_lab.py all   # 全跑一遍

不需要 API key、不需要网络。每个实验里的"假模型"都是普通 Python，
真模型的行为结构和它们一模一样，只是参数是几千亿个数而已。
"""
from __future__ import annotations

import random
import sys
import time
import unicodedata


def banner(title: str, sub: str = "") -> None:
    print("\n" + "=" * 56)
    print(f"  {title}")
    if sub:
        print(f"  {sub}")
    print("=" * 56)


# ─────────────────────────────────────────────────────────────
# 实验 1：token —— 模型眼里没有"字"，只有编号
# ─────────────────────────────────────────────────────────────
def demo1_tokens() -> None:
    banner("实验 1｜token 与流式输出", "模型不认识中文英文，只认识一串编号")

    text = "我叫小杨，I like AI 学习。"
    # 真实分词很复杂（BPE 算法），这里用官方文档给的经验值近似：
    # 中文约 1 字 ≈ 1~1.5 token；英文约 4 个字母 ≈ 1 token；标点各算 1
    zh = sum(1 for c in text if unicodedata.east_asian_width(c) == "W")
    ascii_letters = sum(1 for c in text if c.isascii() and c.isalpha())
    punct = sum(1 for c in text if not c.isalnum() and unicodedata.east_asian_width(c) != "W")
    est = int(zh * 1.2 + ascii_letters / 4 + punct)

    print(f'\n  原句："{text}"')
    print(f"  字符数：{len(text)}")
    print(f"  估算 token 数：约 {est}"
          f"  （{zh} 个中文字×1.2 + {ascii_letters} 个字母÷4 + {punct} 个标点）")
    print("\n  → 领悟①：计费、窗口上限，单位都是 token 不是字。")
    print("    中文比英文'费'：同样一句话，中文 token 数通常更多。")

    print("\n  —— 流式输出模拟 ——")
    reply = "模型生成回答时，是一次吐一个 token，不是一次吐一整句。"
    print("  AI>", end=" ", flush=True)
    for ch in reply:
        print(ch, end="", flush=True)   # 真 CLI 里这里收到的是网络数据包
        time.sleep(0.06)
    print()
    print("  → 领悟②：流式不是'打字快'，是生成一个就发一个。")
    print("    你 W7 的 CLI 里那个 for chunk in resp 就是在接这些碎片。")


# ─────────────────────────────────────────────────────────────
# 实验 2：temperature —— 不是"创造力旋钮"，是抽样随机度
# ─────────────────────────────────────────────────────────────
def demo2_temperature() -> None:
    banner("实验 2｜temperature 是什么", "同一个问题问 5 次，看输出变不变")

    # 假想模型对"今天天气真___"的候选词和它们的"倾向度"（真实模型是概率，这里同构）
    candidates = [("好", 60), ("差", 15), ("冷", 15), ("妙", 8), ("糟", 2)]

    def sample(temp: float) -> str:
        """按 temperature 调整倾向度后随机抽一个。

        temp=0 → 永远取最高分（贪心）
        temp 越大 → 分数差距被压平，冷门词越有机会
        """
        if temp == 0:
            return max(candidates, key=lambda x: x[1])[0]
        weights = [score ** (1 / temp) for _, score in candidates]
        return random.choices([w for w, _ in candidates], weights=weights, k=1)[0]

    for temp in (0, 1, 2):
        outs = [sample(temp) for _ in range(5)]
        same = "全部相同" if len(set(outs)) == 1 else f"出现了 {len(set(outs))} 种结果"
        print(f"  temperature={temp}  五次输出：{' '.join(outs)}   ← {same}")

    print("\n  → 领悟③：模型每步都在'挑下一个 token'，temperature 只控制")
    print("    挑得保守还是随机。它没有心情，0.9 不是'更兴奋'，是数学上的压平。")
    print("    实务：抽取/分类/写代码用低温；头脑风暴/文案用高温。W8 你会调它。")


# ─────────────────────────────────────────────────────────────
# 实验 3：窗口撑爆 —— "AI 忘事"的机制演示
# ─────────────────────────────────────────────────────────────
def demo3_window() -> None:
    banner("实验 3｜上下文窗口撑爆", "窗口=列表的字符预算，超了就得扔纸条")

    BUDGET = 120          # 假想模型的窗口预算（真模型是 8k~200k token）
    messages: list[dict] = [{"role": "system", "content": "你是助手。"}]

    # 模拟一段越来越长的对话，每轮 40 字左右
    for i in range(1, 5):
        user = f"第{i}轮闲聊" + "，填充内容" * 4          # 约 40+ 字符
        bot = f"好的收到第{i}轮" + "，回复内容" * 4
        messages += [{"role": "user", "content": user},
                     {"role": "assistant", "content": bot}]
        used = sum(len(m["content"]) for m in messages)
        status = "OK" if used <= BUDGET else f"💥 超了 {used - BUDGET}"
        print(f"  第 {i} 轮后：已用 {used}/{BUDGET} 字符   {status}")
        if used > BUDGET:
            break

    print(f"\n  现在列表共 {len(messages)} 条，超预算了。三种活法：")

    # 策略 A：截断——扔最旧的（多数聊天软件的做法）
    trimmed = [messages[0]] + messages[-4:]
    lost = len(messages) - len(trimmed)
    print(f"\n  A. 截断：保 system + 最近 4 条，扔掉 {lost} 条最旧的")
    print("     → 后果：你第 1 轮说的'我叫小杨，对花生过敏'被扔了。")
    print("       之后问'我过敏原是什么'，模型看不见那张纸条，答不出来——")
    print("       这就是'AI 忘事'的全部机制：不是忘了，是纸条没递给它。")

    # 策略 B：摘要——把旧消息压缩成一条
    summary = {"role": "system", "content": "【前情摘要】用户叫小杨，对花生过敏，聊过 4 轮。"}
    print("\n  B. 摘要：旧消息压成一条'前情摘要'塞在开头（真产品会再调一次模型来压缩）")
    print("     → 省空间，但压缩有损，细节可能丢。")

    print("\n  C. 检索：不存全部，需要时只捞相关的塞进去 —— 这就是实验 4，RAG")


# ─────────────────────────────────────────────────────────────
# 实验 4：迷你 RAG —— 上下文工程的本质：决定列表里放什么
# ─────────────────────────────────────────────────────────────
def demo4_mini_rag() -> None:
    banner("实验 4｜迷你 RAG", "不微调、不重训，只靠'往列表里塞对的东西'让模型答对")

    # 假想"你的私有资料库"（真 RAG 里是你的 PDF/笔记/文档）
    knowledge = [
        "小杨对花生和芒果过敏，严重时会休克。",
        "项目预算上限是 5 万元，超支需总监审批。",
        "服务器密码策略：90 天强制更换，禁弱口令。",
        "团队周会固定在每周三下午 3 点，会议室 B。",
    ]

    def toy_embed(text: str) -> set[str]:
        """假 embedding。真版本：模型把文本映射成 1024 维向量。

        这里用'字符集合'近似——只要两句话共享的字多，就算语义近。
        糙，但'按相似度找最相关的几段'这个机制是真的。
        """
        return {c for c in text if unicodedata.east_asian_width(c) == "W"}

    def retrieve(query: str, k: int = 2) -> list[str]:
        """检索：给每段资料打分（交集大小），取前 k 段。"""
        q = toy_embed(query)
        scored = sorted(knowledge, key=lambda d: len(q & toy_embed(d)), reverse=True)
        return scored[:k]

    query = "我能吃花生酱吗？"
    print(f"\n  用户提问：{query}")
    hits = retrieve(query)
    print(f"  检索命中 {len(hits)} 段资料：")
    for h in hits:
        print(f"    · {h}")

    # 组装发给模型的列表 —— RAG 的全部动作就这一步
    rag_messages = [
        {"role": "system", "content": "根据【资料】回答，资料里没有就说不知道。"},
        {"role": "user", "content": f"【资料】\n" + "\n".join(hits) + f"\n\n问题：{query}"},
    ]
    print("\n  组装后的请求列表（2 条）：")
    for m in rag_messages:
        print(f"    [{m['role']:<7}] {m['content'][:46]}...")

    answer = "不能。资料明确记载你对花生过敏，严重时会休克。" if "花生" in hits[0] else "不知道。"
    print(f"\n  模型回答：{answer}")

    print("\n  → 领悟④：模型从没'学过'小杨的过敏史（它不可能知道）。")
    print("    答对纯粹因为：正确的纸条在正确的时机被塞进了列表。")
    print("    这就是 RAG：不重训模型，靠检索做上下文工程。")
    print("    W9 你要做的事和这 40 行完全同构，只是：")
    print("      字符集合 → 真 embedding 模型；4 段话 → 几千个文档块；")
    print("      交集大小 → 向量余弦相似度；print → 真的 HTTP 调用。")


DEMOS = {"1": demo1_tokens, "2": demo2_temperature,
         "3": demo3_window, "4": demo4_mini_rag}


def main() -> None:
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    if arg == "all":
        for fn in DEMOS.values():
            fn()
        print("\n✅ 四个实验结束。合起来一句话：")
        print("   大模型 = 只认列表的函数；AI 应用 = 管理那个列表的工程。")
        return
    if arg in DEMOS:
        DEMOS[arg]()
        return
    print(__doc__)


if __name__ == "__main__":
    main()
