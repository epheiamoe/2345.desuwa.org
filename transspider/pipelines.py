# -*- coding: utf-8 -*-
"""
跨性别资源搜索引擎 - Pipeline

负责：
1. 内容提取占位（实际在 Spider 层完成）
2. 批量推送到 Meilisearch
"""

import hashlib
import os
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

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
        index.update_filterable_attributes(["domain", "tags"])
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
