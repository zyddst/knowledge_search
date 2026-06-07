"""
外部文档抓取模块

从指定 URL 抓取网页内容，提取正文，转换为 Markdown，缓存到本地。
支持 CSS 选择器精准提取，也支持自动提取正文。

用法:
    python fetcher.py           # 抓取 config.EXTERNAL_SOURCES 中的所有源
    python fetcher.py --no-fetch  # 跳过抓取，只打印已缓存的文件
"""

import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup, Tag

from config import EXTERNAL_SOURCES, FETCHED_DOCS_DIR


# 请求头（模拟浏览器避免被拒）
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
}

# 默认要移除的标签（脚本、样式、导航等）
DEFAULT_EXCLUDE = [
    "script", "style", "nav", "footer", "header",
    "noscript", "iframe", "svg",
]

# 块级标签自动换行
BLOCK_TAGS = {
    "p", "div", "section", "article", "main", "aside",
    "header", "footer", "nav", "li", "blockquote", "pre",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "table", "tr", "ul", "ol", "dl", "dt", "dd",
    "form", "fieldset", "figure", "figcaption",
}


def _slugify(text: str) -> str:
    """将文本转为安全的文件名"""
    text = text.strip().lower()
    text = re.sub(r"[^\w一-鿿]+", "_", text)
    return text.strip("_")[:60]


def _extract_text(tag: Tag, depth: int = 0) -> str:
    """递归提取 HTML 标签内的文本，转换为 Markdown 格式"""
    if tag.name in ("script", "style", "noscript"):
        return ""

    # 处理文本节点
    lines = []
    for child in tag.children:
        if isinstance(child, str):
            text = child.strip()
            if text:
                lines.append(text)
        elif isinstance(child, Tag):
            name = child.name.lower()

            # 标题
            if name in ("h1", "h2", "h3", "h4", "h5", "h6"):
                level = int(name[1])
                inner = _extract_text(child, depth + 1).strip()
                if inner:
                    lines.append(f"\n{'#' * level} {inner}\n")

            # 段落
            elif name == "p":
                inner = _extract_text(child, depth + 1).strip()
                if inner:
                    lines.append(f"\n{inner}\n")

            # 链接
            elif name == "a":
                href = child.get("href", "")
                inner = _extract_text(child, depth + 1).strip()
                if href and inner:
                    if href.startswith("/"):
                        lines.append(inner)
                    else:
                        lines.append(f"[{inner}]({href})")
                elif inner:
                    lines.append(inner)

            # 无序列表
            elif name == "li":
                inner = _extract_text(child, depth + 1).strip()
                if inner:
                    lines.append(f"- {inner}")

            # 代码块
            elif name in ("pre", "code"):
                code_text = child.get_text().strip()
                if code_text:
                    lines.append(f"\n```\n{code_text}\n```\n")

            # 图片
            elif name == "img":
                alt = child.get("alt", "")
                src = child.get("src", "")
                if alt or src:
                    lines.append(f"![{alt}]({src})")

            # 表格
            elif name == "table":
                rows = child.find_all("tr")
                for row in rows:
                    cells = row.find_all(["td", "th"])
                    row_text = " | ".join(c.get_text().strip() for c in cells)
                    if row_text:
                        lines.append(row_text)
                lines.append("")

            # 其他块级标签
            elif name in BLOCK_TAGS:
                inner = _extract_text(child, depth + 1).strip()
                if inner:
                    lines.append(f"\n{inner}\n")

            # 内联标签
            else:
                inner = _extract_text(child, depth + 1).strip()
                if inner:
                    lines.append(inner)

    result = " ".join(line for line in lines if line)
    # 清理多余空行
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result


def fetch_page(url: str, content_selector: str | None = None,
               exclude_selectors: list[str] | None = None,
               timeout: int = 15) -> str:
    """
    抓取单个页面，返回 Markdown 格式的正文文本

    url:               页面 URL
    content_selector:  CSS 选择器，指定正文区域（None 则使用整个 body）
    exclude_selectors: 要移除的元素 CSS 选择器列表
    timeout:           请求超时秒数

    返回 Markdown 文本；抓取失败返回空字符串。
    """
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or "utf-8"
    except Exception as e:
        print(f"  [错误] 抓取失败: {url} — {e}")
        return ""

    soup = BeautifulSoup(resp.text, "html.parser")

    # 移除不需要的元素
    for sel in (exclude_selectors or []) + DEFAULT_EXCLUDE:
        for el in soup.select(sel):
            el.decompose()

    # 提取正文区域
    if content_selector:
        content = soup.select_one(content_selector)
        if not content:
            print(f"  [警告] 未找到 content_selector「{content_selector}」，回退到 body")
            content = soup.body or soup
    else:
        # 自动选择：优先 article > main > body
        content = (soup.find("article") or soup.find("main") or soup.body or soup)

    if not content:
        return ""

    # 1. 提取页面标题
    title_tag = soup.find("title")
    title = title_tag.get_text().strip() if title_tag else urlparse(url).path.strip("/")

    # 2. 转换为 Markdown
    body = _extract_text(content)

    # 3. 组装最终文档
    markdown = f"# {title}\n\n> 来源: {url}\n> 抓取时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n{body}"
    return markdown.strip()


def fetch_source(source: dict, output_dir: Path) -> int:
    """
    抓取一个外部源的所有 URL，保存到指定目录

    source:  EXTERNAL_SOURCES 中的一项
    output_dir: 保存目录（fetched_docs/<name>/）

    返回成功抓取的页面数。
    """
    name = source["name"]
    urls = source.get("urls", [])
    content_selector = source.get("content_selector")
    exclude_selectors = source.get("exclude_selectors", [])

    print(f"[{name}] 共 {len(urls)} 个 URL")

    count = 0
    for url in urls:
        print(f"  抓取: {url}")
        markdown = fetch_page(url, content_selector, exclude_selectors)

        if not markdown:
            continue

        # 用 URL 路径生成文件名
        path = urlparse(url).path.strip("/")
        filename = _slugify(path) if path else "index"
        filepath = output_dir / f"{filename}.md"

        filepath.write_text(markdown, encoding="utf-8")
        print(f"  保存: {filepath}")
        count += 1

        # 礼貌间隔
        time.sleep(0.5)

    return count


def fetch_all(no_fetch: bool = False) -> int:
    """
    遍历所有外部源，抓取并缓存

    no_fetch: True 则跳过抓取，只列出已缓存文件
    返回成功抓取/已缓存的页面总数。
    """
    if not EXTERNAL_SOURCES:
        print("未配置外部文档源（config.EXTERNAL_SOURCES 为空），跳过。")
        return 0

    base_dir = Path(FETCHED_DOCS_DIR)
    total = 0

    for source in EXTERNAL_SOURCES:
        output_dir = base_dir / _slugify(source["name"])
        output_dir.mkdir(parents=True, exist_ok=True)

        if no_fetch:
            files = sorted(output_dir.rglob("*.md"))
            print(f"[{source['name']}] 已缓存 {len(files)} 个文件")
            total += len(files)
        else:
            total += fetch_source(source, output_dir)

    if not no_fetch:
        print(f"\n抓取完成，共 {total} 个页面 → {base_dir}")
    return total


if __name__ == "__main__":
    no_fetch = "--no-fetch" in sys.argv
    fetch_all(no_fetch=no_fetch)
