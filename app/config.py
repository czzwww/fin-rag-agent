import os   # 导入 os 模块，用于访问环境变量。
from dotenv import load_dotenv # dotenv是一个库，用于在 Python 中使用环境变量。

load_dotenv()

def get(key: str, default: str = "") -> str:
    return os.getenv(key, default)

OPENAI_API_KEY = get("OPENAI_API_KEY")
OPENAI_BASE_URL = get("OPENAI_BASE_URL", "https://api.deepseek.com")
CHAT_MODEL = "deepseek-chat"
ZHIPU_API_KEY = get("ZHIPU_API_KEY")
EMBED_PROVIDER = get("EMBED_PROVIDER", "zhipu")
EMBED_MODEL = get("EMBED_MODEL", "embedding-2")
