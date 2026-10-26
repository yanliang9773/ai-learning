#!/usr/bin/env python3
"""第 7 周交付物：命令行多轮对话程序（带流式输出、记忆、成本统计）。

这是你第一个真正的「AI 应用」。它比任何网课都更能让你理解大模型是怎么用的。

准备工作（只需一次）：
    1. 复制 .env.example 为 .env
    2. 用记事本打开 .env，填入你的 API Key 和 Base URL
    3. pip install openai python-dotenv

用法：
    python week07\\01_chat_cli.py
    python week07\\01_chat_cli.py --system "你是一位严格的中文校对编辑"

对话中的命令：
    /reset   清空历史，重新开始
    /cost    查看本次会话累计 token 与花费
    /history 查看当前上下文里有几条消息
    /help    显示帮助
    exit     退出

知识点：messages 结构、system/user/assistant 角色、流式响应、token 计费、环境变量
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

# 让 python-dotenv 去项目根目录找 .env，不管你从哪个文件夹运行
ROOT = Path(__file__).resolve().parent.parent
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    print("⚠️  没装 python-dotenv，将只读取系统环境变量")

try:
    from openai import OpenAI
except ImportError:
    sys.exit("❌ 缺少 openai 库。执行：pip install openai python-dotenv")


# 粗略价格表（美元/百万 token）。真实价格去服务商控制台查，这里只为让你有成本意识。
PRICE = {"prompt": 2.50, "completion": 10.00}


class ChatSession:
    """一次会话：管上下文、管 token 统计。

    理解这个类 = 理解「多轮对话」的真相：模型本身没有记忆，
    是我们每次把完整历史都发过去，它才「看起来」记得。
    """

    def __init__(self, client: OpenAI, model: str, system: str) -> None:
        self.client = client
        self.model = model
        self.messages: list[dict] = [{"role": "system", "content": system}]
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.calls = 0

    def ask(self, text: str, stream: bool = True) -> str:
        """发一轮对话。stream=True 时逐字打印，体验上「响应快很多」。"""
        self.messages.append({"role": "user", "content": text})
        self.calls += 1

        try:
            if stream:
                return self._ask_stream()
            return self._ask_blocking()
        except Exception as exc:                       # noqa: BLE001
            # 请求失败时把刚才加进去的用户消息撤掉，否则上下文会被脏数据污染
            self.messages.pop()
            return f"❌ 调用失败：{type(exc).__name__}: {exc}"

    def _ask_stream(self) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=self.messages,
            stream=True,
            # 让服务端在最后一个数据包里带上 token 用量
            stream_options={"include_usage": True},
        )
        parts: list[str] = []
        for chunk in resp:
            if chunk.usage:                            # 最后一个 chunk 才有用量
                self.prompt_tokens += chunk.usage.prompt_tokens
                self.completion_tokens += chunk.usage.completion_tokens
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta.content
            if delta:
                parts.append(delta)
                print(delta, end="", flush=True)       # 关键：flush=True 才会立刻显示
        print()
        answer = "".join(parts)
        self.messages.append({"role": "assistant", "content": answer})
        return answer

    def _ask_blocking(self) -> str:
        resp = self.client.chat.completions.create(model=self.model, messages=self.messages)
        usage = resp.usage
        if usage:
            self.prompt_tokens += usage.prompt_tokens
            self.completion_tokens += usage.completion_tokens
        answer = resp.choices[0].message.content or ""
        print(answer)
        self.messages.append({"role": "assistant", "content": answer})
        return answer

    def cost_usd(self) -> float:
        return (self.prompt_tokens / 1e6 * PRICE["prompt"]
                + self.completion_tokens / 1e6 * PRICE["completion"])

    def reset(self) -> None:
        sys_text = self.messages[0]["content"]
        self.messages = [{"role": "system", "content": sys_text}]
        print("  （历史已清空，累计花费保留）")

    def report(self) -> str:
        ctx = len(self.messages)
        return (f"  调用次数 : {self.calls}\n"
                f"  输入 token: {self.prompt_tokens:,}\n"
                f"  输出 token: {self.completion_tokens:,}\n"
                f"  累计花费  : ${self.cost_usd():.4f}（按 {PRICE['prompt']}/{PRICE['completion']} 每百万 token 估算）\n"
                f"  上下文条数: {ctx} 条（含 system）")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="命令行多轮对话")
    parser.add_argument("--model", default=os.getenv("MODEL_NAME", "gpt-4o-mini"),
                        help="模型名，默认读 .env 的 MODEL_NAME")
    parser.add_argument("--system", default="你是一个简洁、准确的中文助手。不确定就说不确定。",
                        help="系统提示词")
    parser.add_argument("--no-stream", action="store_true", help="关闭流式输出")
    args = parser.parse_args(argv)

    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    if not api_key or "替换" in api_key:
        print("❌ 还没有配置 API Key")
        print("   1) 复制 .env.example 为 .env")
        print("   2) 编辑 .env 填入真实密钥")
        print("   注意：.env 已在 .gitignore 里，不会被提交")
        return 1

    client = OpenAI(
        api_key=api_key,
        base_url=os.getenv("OPENAI_BASE_URL"),   # None 时自动用官方地址；国内兼容服务改这里
    )

    s = ChatSession(client, args.model, args.system)
    print("=" * 66)
    print(f"  模型: {args.model}")
    print(f"  端点: {os.getenv('OPENAI_BASE_URL') or '（官方默认）'}")
    print("  命令: /reset 清空  /cost 花费  /history 上下文  /help 帮助  exit 退出")
    print("=" * 66)

    while True:
        try:
            text = input("\n你 > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n" + s.report())
            return 0

        if not text:
            continue
        low = text.lower()
        if low in {"exit", "quit", "q"}:
            print(s.report())
            return 0
        if low == "/reset":
            s.reset(); continue
        if low == "/cost":
            print(s.report()); continue
        if low == "/help":
            print("  /reset /cost /history /help exit"); continue
        if low == "/history":
            for i, m in enumerate(s.messages):
                preview = m["content"][:60].replace("\n", " ")
                print(f"  [{i}] {m['role']:<9} {preview}")
            continue

        t0 = time.time()
        print("AI > ", end="", flush=True)
        s.ask(text, stream=not args.no_stream)
        print(f"  ⏱ {time.time() - t0:.1f}s")


if __name__ == "__main__":
    raise SystemExit(main())
