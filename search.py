"""
知识库搜索
用法: python search.py "你的问题或关键词"
  纯 Python TF-IDF 方案，零原生依赖。
"""

import sys
import pickle
import re
from pathlib import Path

from sklearn.metrics.pairwise import cosine_similarity
from config import VECTOR_DB_DIR, TOP_K


def load_index() -> tuple[list[dict], any, any]:
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
    return chunks, vectorizer, tfidf_matrix


def search(query: str, top_k: int = TOP_K):
    """搜索知识库"""
    print(f"搜索: {query}\n")

    chunks, vectorizer, tfidf_matrix = load_index()

    # TF-IDF 向量相似度
    query_vec = vectorizer.transform([query])
    tfidf_scores = cosine_similarity(query_vec, tfidf_matrix).flatten()

    # 关键词命中加分
    keywords = set(re.findall(r"[一-鿿]+|\w+", query.lower()))
    keyword_scores = []
    for chunk in chunks:
        content_lower = chunk["content"].lower()
        title_lower = chunk["title"].lower()
        hits = sum(1 for kw in keywords if kw in content_lower)
        title_hits = sum(1 for kw in keywords if kw in title_lower)
        keyword_scores.append(hits * 0.05 + title_hits * 0.2)

    # 综合排序
    combined = []
    for i, chunk in enumerate(chunks):
        score = tfidf_scores[i] + keyword_scores[i]
        combined.append((score, chunk))

    combined.sort(key=lambda x: x[0], reverse=True)

    # 去重相邻相似块
    seen_sources = set()
    results = []
    for score, chunk in combined:
        source = chunk["source"]
        if source not in seen_sources:
            seen_sources.add(source)
            results.append((score, chunk))
        if len(results) >= top_k:
            break

    print(f"{'─' * 60}")
    for rank, (score, chunk) in enumerate(results, 1):
        doc = chunk["content"]
        preview = doc[:250] + ("..." if len(doc) > 250 else "")
        print(f"#{rank}  [{chunk['title']}]  相关度: {score:.2f}")
        print(f"    文件: {chunk['source']}")
        print(f"    {'─' * 50}")
        print(f"    {preview}")
        print()
    print(f"{'─' * 60}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python search.py \"关键词\"")
        sys.exit(1)
    search(" ".join(sys.argv[1:]))
