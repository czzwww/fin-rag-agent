import numpy as np
from rank_bm25 import BM25Okapi
import jieba
from app.embedding import get_embedder
from app import store

class Retriever:
    def __init__(self):
        self.embedder = get_embedder()
        self.index = store.load_index(self.embedder.dim)
        self.id_map = store.load_id_map()          # faiss_id(str) -> chunk_id
        self.chunk_ids = list(self.id_map.values())
        self.chunks = store.get_chunks(self.chunk_ids)
        self.corpus = [self.chunks[c]["text"] for c in self.chunk_ids]
        self.bm25 = BM25Okapi([list(jieba.cut(t)) for t in self.corpus])

    def _vector_search(self, query, k):
        q = np.array(self.embedder.embed([query]), dtype="float32")
        D, I = self.index.search(q, k)
        return [self.id_map[str(i)] for i in I[0] if str(i) in self.id_map], D[0]

    def _bm25_search(self, query, k):
        scores = self.bm25.get_scores(list(jieba.cut(query)))
        order = np.argsort(scores)[::-1][:k]
        return [self.chunk_ids[i] for i in order]

    def search(self, query, k=5, recall=20, use_rerank=True):
        v_ids, _ = self._vector_search(query, recall)
        b_ids = self._bm25_search(query, recall)
        # RRF 融合
        rrf = {}
        for rank, cid in enumerate(v_ids):
            rrf[cid] = rrf.get(cid, 0) + 1 / (60 + rank)
        for rank, cid in enumerate(b_ids):
            rrf[cid] = rrf.get(cid, 0) + 1 / (60 + rank)
        fused = [c for c, _ in sorted(rrf.items(), key=lambda x: -x[1])][:recall]
        if use_rerank:
            fused = self._rerank(query, fused, k)
        return fused[:k]

    def _rerank(self, query, cand_ids, k):
        """MVP：用向量余弦重排；进阶可换 BGE-reranker / 智谱 rerank API"""
        q = np.array(self.embedder.embed([query])[0])
        scored = []
        for cid in cand_ids:
            v = np.array(self.embedder.embed([self.chunks[cid]["text"]])[0])
            cos = float(q @ v / (np.linalg.norm(q) * np.linalg.norm(v) + 1e-9))
            scored.append((cid, cos))
        return [c for c, _ in sorted(scored, key=lambda x: -x[1])][:k]