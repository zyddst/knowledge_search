"""
知识库索引工具

把指定目录（或多个目录）下的所有 .md 文件做分块、TF-IDF 向量化，存到本地。

用法:
    python index_docs.py                    # 索引 docs/ + fetched_docs/
    python index_docs.py --fetch             # 先抓取外部文档，再索引
    python index_docs.py /path/to/custom     # 索引指定目录（兼容旧用法）
"""

import sys
import pickle
import hashlib
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from config import DOCS_DIR, FETCHED_DOCS_DIR, VECTOR_DB_DIR, CHUNK_SIZE, CHUNK_OVERLAP


def collect_markdown_files(dirs: list[Path]) -> list[Path]:
    """
    从多个目录收集所有 .md 文件

    dirs: 目录路径列表
    返回去重后的文件路径列表，按路径排序。
    """
    seen = set()
    files = []
    for d in dirs:
        if not d.exists():
            print(f"  [跳过] 目录不存在: {d}")
            continue
        for f in sorted(d.rglob("*.md")):
            # 用 resolve 后的路径做去重
            key = str(f.resolve())
            if key not in seen:
                seen.add(key)
                files.append(f)
    return files


def chunk_markdown(filepath: Path, chunk_size: int = CHUNK_SIZE,
                   overlap: int = CHUNK_OVERLAP) -> list[dict]:
    """
    将 Markdown 文件分块

    filepath:   文件路径
    chunk_size: 每块最大字符数
    overlap:    滑动窗口重叠量

    返回块列表，每项包含 id, content, source, title。
    """
    text = filepath.read_text(encoding="utf-8", errors="replace")
    title = filepath.stem

    # 从文件内容中提取第一个一级标题作为 title
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("# ") and not stripped.startswith("## "):
            title = stripped[2:].strip()
            break

    # 按段落分块
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
        # source 用相对于项目根目录的路径，更简洁
        source = str(filepath)
        results.append({
            "id": chunk_id,
            "content": chunk,
            "source": source,
            "title": title,
        })
    return results


def build_index(dirs: list[Path] | None = None, do_fetch: bool = False):
    """
    构建 TF-IDF 索引

    dirs:    要索引的目录列表；None 则使用 docs/ + fetched_docs/
    do_fetch: 是否在索引前先抓取外部文档
    """
    # 抓取外部文档（如果指定 --fetch）
    if do_fetch:
        from fetcher import fetch_all
        print("[0/4] 抓取外部文档...")
        fetch_all()
        print()

    # 确定索引目录
    if dirs is None:
        dirs = [Path(DOCS_DIR)]
        fetched = Path(FETCHED_DOCS_DIR)
        if fetched.exists():
            dirs.append(fetched)

    print(f"[1/4] 扫描文档目录:")
    for d in dirs:
        print(f"       {d}")
    files = collect_markdown_files(dirs)

    if not files:
        print("       [错误] 没有找到任何 .md 文件")
        sys.exit(1)
    print(f"       共 {len(files)} 个 .md 文件")

    print(f"[2/4] 分块 + 构建 TF-IDF 索引...")
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

    print(f"[3/4] 保存索引...")
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
        f.write(f"dirs={','.join(str(d) for d in dirs)}\n")
        f.write(f"files={len(files)}\n")
        f.write(f"chunks={len(all_chunks)}\n")

    # 统计各目录文档数
    print(f"\n[4/4] 索引完成!")
    for d in dirs:
        count = sum(1 for fp in files if str(d) in str(fp))
        print(f"       {d}: {count} 个文件")
    print(f"       总计: {len(files)} 个文件 → {len(all_chunks)} 个块")
    print(f"       索引库: {db_dir.resolve()}")
    print()
    print(f"       搜索: python search.py \"关键词\"")


if __name__ == "__main__":
    do_fetch = "--fetch" in sys.argv

    # 过滤掉标志参数
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if args:
        # 兼容旧用法：指定单个目录
        build_index([Path(args[0])], do_fetch=do_fetch)
    else:
        build_index(do_fetch=do_fetch)
