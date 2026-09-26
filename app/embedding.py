from app import config
import requests

class ZhipuEmbedder:
    def __init__(self):
        self.model = config.EMBED_MODEL
        self.model_name = config.EMBED_MODEL
        self.dim = 1024
        self.url = "https://open.bigmodel.cn/api/paas/v4/embeddings"

    def embed(self, texts, batch_size: int = 64):
        # 直连智谱，避免 openai SDK 注入 encoding_format（智谱不认 → 1210）
        # 单次 input 不得超过 64 条，故分批调用
        headers = {"Authorization": f"Bearer {config.ZHIPU_API_KEY}",
                   "Content-Type": "application/json"}
        results = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            resp = requests.post(self.url, headers=headers,
                                 json={"model": self.model, "input": batch}, timeout=60)
            resp.raise_for_status()
            results.extend([d["embedding"] for d in resp.json()["data"]])
        return results

class BGEEmbedder:
    """离线备选：uv add sentence-transformers 后启用"""
    def __init__(self, model_name="BAAI/bge-m3"):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(model_name)
        self.model_name = model_name   # 供入库时记录/比对版本
        self.dim = self.model.get_sentence_embedding_dimension()

    def embed(self, texts):
        return self.model.encode(texts, normalize_embeddings=True).tolist()

def get_embedder():
    if config.EMBED_PROVIDER == "bge":
        return BGEEmbedder()
    return ZhipuEmbedder()