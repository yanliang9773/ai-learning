import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

key = os.getenv("OPENAI_API_KEY", "")
# 关键：永远不要打印完整密钥！只显示前 8 位和后 4 位
print(f"读到了吗: {bool(key)}")
print(f"密钥样子: {key[:8]}...{key[-4:]}" if len(key) > 12 else "（还没填）")
print(f"Base URL: {os.getenv('OPENAI_BASE_URL')}")
print(f"模型名:   {os.getenv('MODEL_NAME')}")
