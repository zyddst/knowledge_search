"""
知识库搜索 — 混合搜索引擎 (TF-IDF + BM25 + RRF)

用法:
    python search.py "你的问题或关键词"

架构:
    TF-IDF 余弦相似度 → rank
    BM25 关键词匹配   → rank
    RRF 倒数排名融合  → 最终排序
"""

import sys
import pickle
import re
import math
from pathlib import Path

from sklearn.metrics.pairwise import cosine_similarity
from config import VECTOR_DB_DIR, TOP_K, BM25_K1, BM25_B, RRF_K, MIN_RELEVANCE, MIN_TFIDF


# ────────────────────────────────────────────
# 分词
# ────────────────────────────────────────────

def tokenize(text: str) -> list[str]:
    """
    中文单字 + 英文词组分词

    输入: "开发环境 VS Code"
    输出: ["开", "发", "环", "境", "vs", "code"]

    中文按单字切（确保细粒度匹配），英文按词切（避免 "environment" 被拆散）。
    """
    tokens = []
    for m in re.finditer(r"[一-鿿]|[a-zA-Z]+|\d+", text.lower()):
        tokens.append(m.group())
    return tokens


# ────────────────────────────────────────────
# 索引加载
# ────────────────────────────────────────────

def load_index() -> tuple:
    """加载所有索引文件"""
    db_dir = Path(VECTOR_DB_DIR)
    if not db_dir.exists():
        print("[错误] 索引不存在，请先运行: python index_docs.py")
        sys.exit(1)

    with open(db_dir / "chunks.pkl", "rb") as f:
        chunks = pickle.load(f)
    with open(db_dir / "vectorizer.pkl", "rb") as f:
        vectorizer = pickle.load(f)
    with open(db_dir / "tfidf_matrix.pkl", "rb") as f:
        tfidf_matrix = pickle.load(f)

    bm25_path = db_dir / "bm25.pkl"
    bm25_index = None
    if bm25_path.exists():
        with open(bm25_path, "rb") as f:
            bm25_index = pickle.load(f)

    return chunks, vectorizer, tfidf_matrix, bm25_index


# ────────────────────────────────────────────
# BM25 评分
# ────────────────────────────────────────────

def bm25_score(query: str, bm25_index: dict) -> list[float]:
    """
    计算查询对所有文档块的 BM25 得分

    BM25(D, Q) = Σ IDF(qi) × f(qi,D) × (k1+1) / (f(qi,D) + k1 × (1-b + b×|D|/avgdl))

    返回: scores[chunk_idx] = BM25 分数
    """
    k1 = bm25_index["k1"]
    b = bm25_index["b"]
    total_docs = bm25_index["total_docs"]
    avgdl = bm25_index["avgdl"]
    doc_lengths = bm25_index["doc_lengths"]
    idf = bm25_index["idf"]
    postings = bm25_index["postings"]

    query_tokens = tokenize(query)
    scores = [0.0] * total_docs

    for token in query_tokens:
        token_idf = idf.get(token, 0)
        if token_idf == 0:
            continue
        for doc_idx, tf in postings.get(token, []):
            doc_len = doc_lengths[doc_idx]
            numerator = tf * (k1 + 1)
            denominator = tf + k1 * (1 - b + b * doc_len / avgdl)
            scores[doc_idx] += token_idf * numerator / denominator

    return scores


# ────────────────────────────────────────────
# 构建 BM25 索引（index_docs.py 调用）
# ────────────────────────────────────────────

def build_bm25_index(chunks: list[dict], k1: float = BM25_K1, b: float = BM25_B) -> dict:
    """
    为所有文档块构建 BM25 索引

    chunks: [{id, content, source, title}, ...]

    返回 BM25 索引 dict，供 pickle 持久化。
    """
    total_docs = len(chunks)

    # 1. 对所有 chunk 分词，统计词频
    postings: dict[str, list[tuple[int, int]]] = {}  # term → [(doc_idx, tf), ...]
    doc_lengths = []

    for doc_idx, chunk in enumerate(chunks):
        tokens = tokenize(chunk["content"])
        doc_lengths.append(len(tokens))

        # 词频统计
        tf = {}
        for t in tokens:
            tf[t] = tf.get(t, 0) + 1

        # 写入倒排索引
        for term, freq in tf.items():
            if term not in postings:
                postings[term] = []
            postings[term].append((doc_idx, freq))

    # 2. 计算 IDF
    avgdl = sum(doc_lengths) / total_docs if total_docs > 0 else 1.0
    idf = {}
    for term, posting_list in postings.items():
        df = len(posting_list)
        # BM25 IDF: log((N - df + 0.5) / (df + 0.5) + 1)
        idf[term] = math.log((total_docs - df + 0.5) / (df + 0.5) + 1)

    return {
        "k1": k1,
        "b": b,
        "total_docs": total_docs,
        "avgdl": avgdl,
        "doc_lengths": doc_lengths,
        "idf": idf,
        "postings": postings,
    }


# ────────────────────────────────────────────
# 混合搜索 (TF-IDF + BM25 + RRF)
# ────────────────────────────────────────────

def hybrid_search(
    query: str,
    chunks: list[dict],
    vectorizer,
    tfidf_matrix,
    bm25_index: dict | None,
    top_k: int = TOP_K,
    rrf_k: int = RRF_K,
) -> list[dict]:
    """
    混合搜索：TF-IDF + BM25，RRF 融合排序

    如果bm25_index为None（未构建），回退到纯 TF-IDF + 关键词命中加权。
    """
    n = len(chunks)

    # ── TF-IDF 得分 ──
    query_vec = vectorizer.transform([query])
    tfidf_scores = cosine_similarity(query_vec, tfidf_matrix).flatten()

    # 绝对相似度兜底：TF-IDF 太低说明查询与所有文档都不沾边，直接判不相关
    if max(tfidf_scores) < MIN_TFIDF:
        return []

    # ── 计算排名 ──
    if bm25_index is not None:
        # BM25 得分
        bm25_scores = bm25_score(query, bm25_index)

        # 排名：按得分降序，同分同排名（dense ranking）
        def ranks(values):
            unique = sorted(set(values), reverse=True)
            rank_map = {v: i + 1 for i, v in enumerate(unique)}
            return [rank_map[v] for v in values]

        tfidf_ranks = ranks(tfidf_scores)
        bm25_ranks = ranks(bm25_scores)

        # 零分块强制末位排名：dense ranking 下零分统一排第 2，需修正为 n
        for i in range(n):
            if tfidf_scores[i] == 0:
                tfidf_ranks[i] = n
            if bm25_scores[i] == 0:
                bm25_ranks[i] = n

        # RRF 融合: 1/(k + rank_tfidf) + 1/(k + rank_bm25)
        scores = [
            1.0 / (rrf_k + tfidf_ranks[i]) + 1.0 / (rrf_k + bm25_ranks[i])
            for i in range(n)
        ]
        # 归一化到 0~1：除以理论最大值（两个 ranker 都排第 1）
        max_score = 2.0 / (rrf_k + 1)
        scores = [s / max_score for s in scores]

        # BM25 兜底：如果所有块 BM25 都是 0，说明查询词汇在语料库中不存在，直接判不相关
        if max(bm25_scores) == 0:
            return []

        # 零分过滤：TF-IDF 绝对值为 0 的块与查询无任何文本重叠，强制排到末尾
        for i in range(n):
            if tfidf_scores[i] == 0:
                scores[i] = 0.0
    else:
        # 回退：TF-IDF + 简单关键词命中（兼容未构建 BM25 索引的情况）
        keywords = set(re.findall(r"[一-鿿]+|\w+", query.lower()))
        scores = []
        for i, chunk in enumerate(chunks):
            content_lower = chunk["content"].lower()
            title_lower = chunk["title"].lower()
            hits = sum(1 for kw in keywords if kw in content_lower)
            title_hits = sum(1 for kw in keywords if kw in title_lower)
            scores.append(float(tfidf_scores[i]) + hits * 0.05 + title_hits * 0.2)

    # ── 排序 + 去重 + Top-K + 相关度过滤 ──
    combined = sorted(
        [(scores[i], chunks[i]) for i in range(n)],
        key=lambda x: x[0],
        reverse=True,
    )

    seen = set()
    results = []
    for score, chunk in combined:
        src = chunk["source"]
        if src not in seen:
            seen.add(src)
            results.append({
                "title": chunk["title"],
                "source": chunk["source"],
                "snippet": chunk["content"][:200],
                "score": round(float(score), 4),
            })
        if len(results) >= top_k:
            break

    # 过滤低相关度结果
    relevant = [r for r in results if r["score"] >= MIN_RELEVANCE]
    return relevant


# ────────────────────────────────────────────
# CLI 入口
# ────────────────────────────────────────────

def search(query: str, top_k: int = TOP_K):
    """CLI 搜索入口"""
    print(f"搜索: {query}\n")

    chunks, vectorizer, tfidf_matrix, bm25_index = load_index()
    results = hybrid_search(query, chunks, vectorizer, tfidf_matrix,
                            bm25_index, top_k)

    if not results:
        print(f"{'─' * 60}")
        print(f"  未找到相关结果（相关度 < {MIN_RELEVANCE}）")
        print(f"  建议换个关键词试试")
        print(f"{'─' * 60}")
        return

    print(f"{'─' * 60}")
    for rank, r in enumerate(results, 1):
        preview = r["snippet"][:250] + ("..." if len(r["snippet"]) > 250 else "")
        print(f"#{rank}  [{r['title']}]  相关度: {r['score']:.4f}")
        print(f"    文件: {r['source']}")
        print(f"    {'─' * 50}")
        print(f"    {preview}")
        print()
    print(f"{'─' * 60}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python search.py \"关键词\"")
        sys.exit(1)
    search(" ".join(sys.argv[1:]))
