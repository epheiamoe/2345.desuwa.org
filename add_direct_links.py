#!/usr/bin/env python3
"""
将 direct_urls 列表中的链接直接添加到索引（不爬取）
用法: python add_direct_links.py
"""

import os
import sys
import json
import hashlib

# Meilisearch 配置
MEILISEARCH_HOST = os.environ.get("MEILISEARCH_HOST", "localhost")
MEILISEARCH_PORT = os.environ.get("MEILISEARCH_PORT", "7700")
MEILISEARCH_INDEX = os.environ.get("MEILISEARCH_INDEX", "trans_resources")

try:
    import meilisearch
except ImportError:
    print("请先安装 meilisearch: pip install meilisearch")
    sys.exit(1)


def get_doc_id(url):
    """生成文档 ID"""
    return int(hashlib.md5(url.encode()).hexdigest()[:8], 16)


def main():
    # 查找 domains.json
    script_dir = os.path.dirname(os.path.abspath(__file__))
    domains_json = os.path.join(script_dir, "domains.json")

    if not os.path.exists(domains_json):
        print(f"错误: {domains_json} 不存在")
        sys.exit(1)

    with open(domains_json, encoding="utf-8") as f:
        data = json.load(f)

    direct_urls = data.get("direct_urls", [])

    if not direct_urls:
        print("没有 direct_urls 需要添加")
        return

    # 解析域名
    from urllib.parse import urlparse

    documents = []
    for item in direct_urls:
        url = item.get("url", "")
        if not url:
            continue

        parsed = urlparse(url)
        domain = parsed.netloc
        if domain.startswith("www."):
            domain = domain[4:]

        doc = {
            "id": get_doc_id(url),
            "url": url,
            "title": item.get("title", ""),
            "content": item.get("title", ""),
            "domain": domain,
            "tags": item.get("tags", []),
        }
        documents.append(doc)

    if not documents:
        print("没有有效链接")
        return

    print(f"添加 {len(documents)} 个直接链接到索引...")

    client = meilisearch.Client(f"http://{MEILISEARCH_HOST}:{MEILISEARCH_PORT}")
    index = client.index(MEILISEARCH_INDEX)

    task = index.add_documents(documents)
    print(f"任务已提交: {task.task_uid}")

    client.wait_for_task(task.task_uid)
    print("完成!")


if __name__ == "__main__":
    main()
