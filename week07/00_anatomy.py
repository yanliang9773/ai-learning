#!/usr/bin/env python3
"""祛魅演示：所谓「和大模型对话」，拆开就是 —— 一个列表 + 一个循环 + 一次 HTTP POST。

不需要 API key、不需要网络：这里用一个假模型 mock_model() 顶替真模型。
真模型（W7 你要接的）行为完全一样，只是把 mock_model 换成一次网络请求。

跑法：
    python week07\\00_anatomy.py            # 你亲手输入，观察每一轮
    python week07\\00_anatomy.py --auto     # 自动演示，预设三句话

观察重点（这个脚本的全部目的）：
  1. 每一轮请求，messages 列表是【整个重发】的，不是只发你刚打的那句
  2. 假模型"只能看到列表里的东西"——真模型也一样，它没有记忆
  3. 列表越来越长 = token 越花越多 = 上下文窗口迟早撑爆
"""
from __future__ import annotations

import json
import sys

# ── 第 1 件武器：历史列表。这就是"记忆"的全部真相 ──────────────────
messages: list[dict] = [
    {"role": "system", "content": "你是一个简洁的助手。"},   # 开场白，永远在列表第 0 位
]


def mock_model(history: list[dict]) -> str:
    """假装自己是 GPT。注意它的参数：只有 history，没有别的。

    它不知道你是谁、不知道上一轮之外的事、不会"记得"任何东西——
    它的全部世界 = 你这次发给它的那个列表。真模型分毫不差。
    """
    last_user_msg = history[-1]["content"]
    return f"收到「{last_user_msg}」。我只看得见你发来的这 {len(history)} 条消息，仅此而已。"


def show_request() -> None:
    """打印"即将发给模型服务的请求体"——这就是 API 调用的全部秘密。"""
    request_body = {"model": "某个大模型", "messages": messages}
    text = json.dumps(request_body, ensure_ascii=False, indent=2)
    print(f"\n── 本轮请求体（{len(messages)} 条消息，整包重发）" + "─" * 14)
    # 只展示前 600 字符，免得刷屏；完整版你可以自己看
    print(text[:600] + ("\n  ...（后面还有）" if len(text) > 600 else ""))
    print("─" * 52)


def one_round(user_text: str) -> None:
    """一轮对话 = 三步。W7 的真 CLI 就是这三步换了个发动机。"""
    # ① 把你的话追加进历史
    messages.append({"role": "user", "content": user_text})

    # ② 把【整个历史】发过去，拿回一段回复（真版本：一次 POST 请求）
    show_request()
    reply = mock_model(messages)

    # ③ 把回复也追加进历史（下一轮它才"看得见"自己说过什么）
    messages.append({"role": "assistant", "content": reply})
    print(f"AI > {reply}")


def main() -> None:
    auto = "--auto" in sys.argv
    print("=" * 52)
    print("  大模型对话解剖课 —— 共 3 轮，注意看每轮请求体的变化")
    print("=" * 52)

    for i in range(3):
        print(f"\n【第 {i + 1} 轮】")
        if auto:
            user_text = ["你好", "我叫小杨", "我叫什么？"][i]
            print(f"你 > {user_text}   （自动演示）")
        else:
            user_text = input("你 > ")
        one_round(user_text)

    total_chars = sum(len(m["content"]) for m in messages)
    print("\n" + "=" * 52)
    print(f"  结束。历史共 {len(messages)} 条、约 {total_chars} 字符。")
    print("  关键领悟：")
    print("  1. 模型无记忆——每轮都是把整个列表重新发一遍")
    print("  2. 所以聊天越久越贵（token 按整包计费）")
    print("  3. 所以有上下文窗口上限（列表塞不下为止）")
    print("  4. 所以 AI 应用的核心手艺 = 管理这个列表")
    print("     （截断？摘要？检索后只塞相关的？——W9 的 RAG 就是第 4 条的答案）")
    print("=" * 52)


if __name__ == "__main__":
    main()
