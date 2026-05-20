# -*- coding: utf-8 -*-
"""
跨性别资源搜索引擎 - Pipeline

负责：
1. 内容提取占位（实际在 Spider 层完成）
2. 批量推送到 Meilisearch
"""

import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import meilisearch
from scrapy import Spider

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from transspider.config import (
    MEILISEARCH_API_KEY,
    MEILISEARCH_HOST,
    MEILISEARCH_INDEX,
    MEILISEARCH_PORT,
)
from transspider.utils import normalize_url


def normalize_license(value: str) -> Optional[Dict[str, str]]:
    """
    将原始 license 值标准化为统一格式。

    支持 Creative Commons 系列的标准化映射，其他 license 保留原始信息。

    Args:
        value: 原始 license 值（URL 或标识符）。

    Returns:
        标准化后的字典，包含 type、url、name；无法识别时返回 None。
    """
    if not value:
        return None

    value_stripped = value.strip()
    value_lower = value_stripped.lower()

    # Creative Commons 标准映射
    cc_patterns = {
        "https://creativecommons.org/licenses/by/4.0/": "CC-BY-4.0",
        "https://creativecommons.org/licenses/by-sa/4.0/": "CC-BY-SA-4.0",
        "https://creativecommons.org/licenses/by-nc/4.0/": "CC-BY-NC-4.0",
        "https://creativecommons.org/licenses/by-nc-sa/4.0/": "CC-BY-NC-SA-4.0",
        "https://creativecommons.org/licenses/by-nd/4.0/": "CC-BY-ND-4.0",
        "https://creativecommons.org/licenses/by-nc-nd/4.0/": "CC-BY-NC-ND-4.0",
        "cc-by-4.0": "CC-BY-4.0",
        "cc-by-sa-4.0": "CC-BY-SA-4.0",
        "cc-by-nc-4.0": "CC-BY-NC-4.0",
        "cc by 4.0": "CC-BY-4.0",
        "cc by-sa 4.0": "CC-BY-SA-4.0",
        "cc by-nc 4.0": "CC-BY-NC-4.0",
    }

    for pattern, license_type in cc_patterns.items():
        if pattern in value_lower or value_lower == pattern:
            return {
                "type": license_type,
                "url": value_stripped
                if value_stripped.startswith("http")
                else f"https://creativecommons.org/licenses/{license_type.lower().replace('cc-', '')}/4.0/",
                "name": f"Creative Commons {license_type.replace('CC-', '').replace('-', ' ')} 4.0",
            }

    # 非 CC license：提取域名作为 type
    if value_stripped.startswith("http"):
        domain = urlparse(value_stripped).netloc
        return {"type": domain, "url": value_stripped, "name": domain}

    # 其他标识符直接保留
    return {"type": value_stripped, "url": "", "name": value_stripped}


def extract_license(html_text: Optional[str]) -> Optional[Dict[str, str]]:
    """
    从 HTML 响应中提取版权许可信息。

    检查顺序（按优先级）：
    1. <meta name="license" content="...">
    2. <a rel="license" href="...">
    3. JSON-LD schema.org 中的 license 字段
    4. 页面文本中的 "Licensed under..." 模式（备选）

    Args:
        html_text: 页面原始 HTML 文本。

    Returns:
        {"type": "CC-BY-SA-4.0", "url": "...", "name": "..."} 或 None。
    """
    if not html_text:
        return None

    # 1. meta 标签
    meta_patterns = [
        r'<meta[^>]*name=["\']license["\'][^>]*content=["\']([^"\']+)["\']',
        r'<meta[^>]*content=["\']([^"\']+)["\'][^>]*name=["\']license["\']',
    ]
    for pattern in meta_patterns:
        match = re.search(pattern, html_text, re.IGNORECASE)
        if match:
            result = normalize_license(match.group(1))
            if result:
                return result

    # 2. a[rel="license"]
    a_patterns = [
        r'<a[^>]*rel=["\']license["\'][^>]*href=["\']([^"\']+)["\']',
        r'<a[^>]*href=["\']([^"\']+)["\'][^>]*rel=["\']license["\']',
    ]
    for pattern in a_patterns:
        match = re.search(pattern, html_text, re.IGNORECASE)
        if match:
            result = normalize_license(match.group(1))
            if result:
                return result

    # 3. JSON-LD
    jsonld_pattern = re.compile(
        r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        re.DOTALL | re.IGNORECASE,
    )
    for match in jsonld_pattern.finditer(html_text):
        try:
            data = json.loads(match.group(1))
            targets = data if isinstance(data, list) else [data]
            for item in targets:
                if not isinstance(item, dict):
                    continue
                license_url = item.get("license") or item.get(
                    "http://schema.org/license"
                )
                if license_url and isinstance(license_url, str):
                    result = normalize_license(license_url)
                    if result:
                        return result
        except (json.JSONDecodeError, ValueError):
            continue

    # 4. 页面文本中的 "Licensed under..." 模式
    text_match = re.search(
        r'licensed under ([^<\n]+)', html_text, re.IGNORECASE
    )
    if text_match:
        result = normalize_license(text_match.group(1).strip())
        if result:
            return result

    return None


class ContentExtractionPipeline:
    """
    内容提取 Pipeline（占位）。

    当前项目中正文提取已在 ``TransSpider`` 中通过
    ``trafilatura`` 完成，本 Pipeline 仅透传 Item。
    """

    def process_item(self, item: Any, spider: Spider) -> Any:
        """透传 Item。"""
        return item


class MeilisearchPipeline:
    """
    Meilisearch 推送 Pipeline。

    将爬取的页面批量推送到 Meilisearch 索引。
    使用 SHA-256 前 16 位生成文档 ID，并提供批量推送的指数退避重试。
    """

    # 批量推送配置
    BATCH_SIZE: int = 100
    MAX_RETRIES: int = 3
    BASE_BACKOFF_SECONDS: float = 2.0

    def __init__(self) -> None:
        """初始化 Meilisearch 客户端与内部缓冲区。"""
        api_key = MEILISEARCH_API_KEY if MEILISEARCH_API_KEY else None
        self.client = meilisearch.Client(
            f"http://{MEILISEARCH_HOST}:{MEILISEARCH_PORT}", api_key
        )
        self.index: Optional[Any] = None
        self.items_buffer: List[Dict[str, Any]] = []

    @staticmethod
    def setup_index(
        host: str = MEILISEARCH_HOST,
        port: int = MEILISEARCH_PORT,
        index_name: str = MEILISEARCH_INDEX,
        api_key: Optional[str] = None,
    ) -> None:
        """
        部署时调用：创建索引并配置可搜索/可筛选/可排序属性。

        该操作只需在索引首次创建或需要变更配置时执行，
        不应在每次爬虫启动时重复调用，避免不必要的 API 开销。

        Args:
            host: Meilisearch 主机地址。
            port: Meilisearch 端口。
            index_name: 索引名称。
            api_key: API 密钥（可选）。
        """
        client = meilisearch.Client(f"http://{host}:{port}", api_key)
        try:
            index = client.get_index(index_name)
        except Exception:
            index = client.create_index(index_name, {"primaryKey": "id"})

        index.update_searchable_attributes(["title", "content", "domain", "tags"])
        index.update_filterable_attributes(["domain", "tags", "license_type"])
        index.update_sortable_attributes(["url"])

    def open_spider(self, spider: Spider) -> None:
        """
        爬虫启动时执行。

        仅获取或创建索引，不做属性配置。
        索引配置应在部署时通过 ``setup_index`` 完成。
        """
        spider.logger.info(
            "初始化 Meilisearch 连接到 %s:%s", MEILISEARCH_HOST, MEILISEARCH_PORT
        )

        try:
            self.index = self.client.get_index(MEILISEARCH_INDEX)
            spider.logger.info("使用已有索引: %s", MEILISEARCH_INDEX)
        except Exception as exc:
            spider.logger.warning("索引获取失败，尝试创建: %s", exc)
            try:
                self.index = self.client.create_index(
                    MEILISEARCH_INDEX, {"primaryKey": "id"}
                )
                spider.logger.info("创建新索引: %s", MEILISEARCH_INDEX)
            except Exception as create_exc:
                spider.logger.error("Meilisearch 索引创建失败: %s", create_exc)
                self.index = None

    def process_item(self, item: Any, spider: Spider) -> Any:
        """
        处理每个 Item。

        将数据写入内部缓冲区，满批后触发刷新。
        若检测到 ID 冲突（SHA-256 前 16 位极小概率事件），
        自动追加额外哈希片段解决。

        Args:
            item: Scrapy Item。
            spider: 当前 Spider 实例。

        Returns:
            传入的 Item（供后续 Pipeline 处理）。
        """
        if self.index is None:
            spider.logger.warning("Meilisearch 未初始化，跳过推送")
            return item

        url = item.get("url", "")
        doc_id = self._generate_doc_id(url)
        doc_id = self._resolve_id_conflict(doc_id, url, spider)

        doc: Dict[str, Any] = {
            "id": doc_id,
            "url": url,
            "title": item.get("title", "").strip(),
            "content": item.get("content", "").strip()[:5000],
            "domain": item.get("domain", ""),
            "tags": item.get("tags", []),
            "crawled_at": datetime.now().isoformat(),
        }

        # Extract license information from HTML
        license_info = extract_license(item.get("html", ""))
        if license_info:
            doc["license_type"] = license_info["type"]
            doc["license_url"] = license_info["url"]

        if not doc["title"] or not doc["url"]:
            spider.logger.warning("跳过空标题或无效 URL: %s", url)
            return item

        self.items_buffer.append(doc)

        if len(self.items_buffer) >= self.BATCH_SIZE:
            self._flush_items(spider)

        return item

    def close_spider(self, spider: Spider) -> None:
        """
        爬虫关闭时执行。

        推送缓冲区中剩余的数据。
        """
        if self.items_buffer:
            self._flush_items(spider)
        spider.logger.info("Meilisearch Pipeline 关闭")

    def _generate_doc_id(self, url: str) -> str:
        """
        生成文档唯一 ID。

        使用 SHA-256 前 16 位（64 位十六进制），
        对于 1 亿条文档冲突概率约 10^-9，工程上可接受。

        Args:
            url: 页面 URL（建议已规范化）。

        Returns:
            16 位十六进制字符串。
        """
        normalized = normalize_url(url)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]

    def _resolve_id_conflict(
        self, doc_id: str, url: str, spider: Spider
    ) -> str:
        """
        检测并解决文档 ID 冲突。

        若 Meilisearch 中已存在相同 ID 但 URL 不同，
        追加额外哈希片段生成唯一 ID。

        Args:
            doc_id: 候选文档 ID。
            url: 当前文档 URL。
            spider: 当前 Spider 实例（用于日志记录）。

        Returns:
            无冲突的文档 ID。
        """
        try:
            existing = self.index.get_document(doc_id)
            if existing and existing.get("url") != url:
                extra = hashlib.sha256(url.encode("utf-8")).hexdigest()[16:24]
                resolved = f"{doc_id}_{extra}"
                spider.logger.warning(
                    "检测到 ID 冲突 (%s)，已解析为 %s", doc_id, resolved
                )
                return resolved
        except Exception:
            pass
        return doc_id

    def _flush_items(self, spider: Spider) -> None:
        """
        将缓冲区中的文档批量推送到 Meilisearch。

        采用指数退避重试机制（最多 ``MAX_RETRIES`` 次）。
        全部失败后丢弃该批次并清空缓冲区，避免阻塞后续爬取。
        """
        if not self.items_buffer:
            return

        last_exception: Optional[Exception] = None

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                self.index.add_documents(self.items_buffer)
                spider.logger.info(
                    "已推送 %d 个文档到 Meilisearch", len(self.items_buffer)
                )
                self.items_buffer = []
                return
            except Exception as exc:
                last_exception = exc
                wait_time = self.BASE_BACKOFF_SECONDS * (2 ** (attempt - 1))
                spider.logger.warning(
                    "第 %d/%d 次推送失败: %s，%.1f 秒后重试",
                    attempt,
                    self.MAX_RETRIES,
                    exc,
                    wait_time,
                )
                time.sleep(wait_time)

        spider.logger.error(
            "批量推送最终失败（%d 次重试）: %s，丢弃 %d 个文档",
            self.MAX_RETRIES,
            last_exception,
            len(self.items_buffer),
        )
        self.items_buffer = []


class TrafilaturaPipeline:
    """
    Trafilatura 正文提取 Pipeline（占位）。

    当前项目中正文提取在 ``TransSpider`` 中完成，
    本 Pipeline 仅透传 Item。
    """

    def __init__(self) -> None:
        """初始化。"""
        self.items_buffer: List[Any] = []
        self.batch_size: int = 50

    @classmethod
    def from_crawler(cls, crawler: Any) -> "TrafilaturaPipeline":
        """从 Crawler 创建 Pipeline。"""
        return cls()

    def process_item(self, item: Any, spider: Spider) -> Any:
        """透传 Item。"""
        return item
