"""
知识库索引工具
用法: python index_docs.py [docs_dir]
  把指定目录下的所有 .md 文件做分块、TF-IDF 向量化，存到本地。
  纯 Python + sklearn，零原生依赖，Windows 上直接跑。
"""

import sys
import pickle
import hashlib
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from config import DOCS_DIR, VECTOR_DB_DIR, CHUNK_SIZE, CHUNK_OVERLAP


def find_markdown_files(docs_dir: str) -> list[Path]:
    root = Path(docs_dir)
    if not root.exists():
        print(f"[错误] 文档目录不存在: {docs_dir}")
        print(f"  请创建该目录并把 .md 文件放进去，或运行: python index_docs.py /path/to/your/docs")
        sys.exit(1)
    files = sorted(root.rglob("*.md"))
    if not files:
        print(f"[错误] 在 {docs_dir} 中没有找到 .md 文件")
        sys.exit(1)
    return files


def chunk_markdown(filepath: Path, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[dict]:
    text = filepath.read_text(encoding="utf-8", errors="replace")
    title = filepath.stem
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("# ") and not stripped.startswith("## "):
            title = stripped[2:].strip()
            break

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    current = ""
    for p in paragraphs:
        if len(current) + len(p) <= chunk_size:
            current = (current + "\n\n" + p).strip() if current else p
        else:
            if current:
                chunks.append(current)
            if len(p) > chunk_size:
                start = 0
                while start < len(p):
                    end = min(start + chunk_size, len(p))
                    chunks.append(p[start:end])
                    start += chunk_size - overlap
            else:
                current = p
    if current:
        chunks.append(current)

    results = []
    for i, chunk in enumerate(chunks):
        chunk_id = hashlib.md5(f"{filepath}:{i}".encode()).hexdigest()[:12]
        results.append({
            "id": chunk_id,
            "content": chunk,
            "source": str(filepath),
            "title": title,
        })
    return results


def build_index(docs_dir: str = DOCS_DIR):
    docs_dir = Path(docs_dir).resolve()
    print(f"[1/3] 扫描文档: {docs_dir}")
    files = find_markdown_files(str(docs_dir))
    print(f"       找到 {len(files)} 个 .md 文件")

    print(f"[2/3] 分块 + 构建 TF-IDF 索引...")
    all_chunks = []
    for fp in files:
        all_chunks.extend(chunk_markdown(fp))
    print(f"       生成 {len(all_chunks)} 个文本块")

    contents = [c["content"] for c in all_chunks]
    vectorizer = TfidfVectorizer(
        analyzer="char_wb",
        ngram_range=(2, 4),
        max_features=10000,
    )
    tfidf_matrix = vectorizer.fit_transform(contents)

    print(f"[3/3] 保存索引...")
    db_dir = Path(VECTOR_DB_DIR)
    db_dir.mkdir(parents=True, exist_ok=True)

    with open(db_dir / "chunks.pkl", "wb") as f:
        pickle.dump(all_chunks, f)
    with open(db_dir / "vectorizer.pkl", "wb") as f:
        pickle.dump(vectorizer, f)
    with open(db_dir / "tfidf_matrix.pkl", "wb") as f:
        pickle.dump(tfidf_matrix, f)

    # 写 meta
    with open(db_dir / "meta.txt", "w", encoding="utf-8") as f:
        f.write(f"docs_dir={docs_dir}\n")
        f.write(f"files={len(files)}\n")
        f.write(f"chunks={len(all_chunks)}\n")

    print(f"\n  索引完成!")
    print(f"  文档数: {len(files)}")
    print(f"  文本块: {len(all_chunks)}")
    print(f"  索引库: {db_dir}")
    print(f"")
    print(f"  搜索: python search.py \"关键词\"")


if __name__ == "__main__":
    docs = sys.argv[1] if len(sys.argv) > 1 else DOCS_DIR
    build_index(docs)
