# -*- coding: utf-8 -*-
"""
跨性别资源搜索引擎 - Pipeline
负责：
1. 用 trafilatura 提取页面正文
2. 推送到 Meilisearch
"""

import json
import sys
import os
from datetime import datetime

import scrapy
from scrapy.pipelines.files import FilesPipeline
from itemadapter import ItemAdapter
import meilisearch

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from transspider.config import (
    MEILISEARCH_HOST,
    MEILISEARCH_PORT,
    MEILISEARCH_INDEX,
    MEILISEARCH_API_KEY,
    USE_WARP_PROXY,
)


class ContentExtractionPipeline:
    """
    内容提取 Pipeline

    使用 trafilatura 提取页面正文
    trafilatura 对中文支持非常好
    """

    def process_item(self, item, spider):
        """
        处理每个 Item

        注意：这里只提取 meta 信息，
        完整正文需要通过 Response 对象提取
        """
        return item


class MeilisearchPipeline:
    """
    Meilisearch 推送 Pipeline

    将爬取的页面推送到 Meilisearch 索引
    """

    def __init__(self):
        """初始化 Meilisearch 客户端"""
        self.client = meilisearch.Client(
            f"http://{MEILISEARCH_HOST}:{MEILISEARCH_PORT}", MEILISEARCH_API_KEY
        )
        self.index = None
        self.items_buffer = []
        self.batch_size = 100  # 批量推送大小

    def open_spider(self, spider):
        """
        爬虫启动时执行

        确保 Meilisearch 索引存在
        """
        spider.logger.info(
            f"初始化 Meilisearch 连接到 {MEILISEARCH_HOST}:{MEILISEARCH_PORT}"
        )

        try:
            # 获取或创建索引
            try:
                self.index = self.client.get_index(MEILISEARCH_INDEX)
                spider.logger.info(f"使用已有索引: {MEILISEARCH_INDEX}")
            except meilisearch.errors.MeilisearchApiError:
                self.index = self.client.create_index(
                    MEILISEARCH_INDEX, {"primaryKey": "url"}
                )
                spider.logger.info(f"创建新索引: {MEILISEARCH_INDEX}")

            # 配置索引可搜索属性
            self.index.update_searchable_attributes(["title", "content", "domain"])

            # 配置筛选属性
            self.index.update_filterable_attributes(["domain"])

            # 配置排序属性
            self.index.update_sortable_attributes(["url"])

            spider.logger.info("Meilisearch 索引配置完成")

        except Exception as e:
            spider.logger.error(f"Meilisearch 初始化失败: {e}")
            self.index = None

    def process_item(self, item, spider):
        """
        处理每个 Item

        将数据推送到 Meilisearch
        """
        if self.index is None:
            spider.logger.warning("Meilisearch 未初始化，跳过推送")
            return item

        # 提取有用信息
        doc = {
            "url": item.get("url", ""),
            "title": item.get("title", "").strip(),
            "content": item.get("content", "").strip(),
            "domain": item.get("domain", ""),
            "crawled_at": datetime.now().isoformat(),
        }

        # 跳过空标题或无效 URL
        if not doc["title"] or not doc["url"]:
            return item

        # 添加到缓冲区
        self.items_buffer.append(doc)

        # 达到批量大小时推送
        if len(self.items_buffer) >= self.batch_size:
            self._flush_items(spider)

        return item

    def _flush_items(self, spider):
        """
        推送缓冲区中的数据到 Meilisearch
        """
        if not self.items_buffer:
            return

        try:
            task = self.index.add_documents(self.items_buffer)
            spider.logger.info(f"已推送 {len(self.items_buffer)} 个文档到 Meilisearch")
            self.items_buffer = []  # 清空缓冲区
        except Exception as e:
            spider.logger.error(f"推送文档到 Meilisearch 失败: {e}")

    def close_spider(self, spider):
        """
        爬虫关闭时执行

        推送剩余的数据
        """
        if self.items_buffer:
            self._flush_items(spider)
        spider.logger.info("Meilisearch Pipeline 关闭")


class TrafilaturaPipeline:
    """
    Trafilatura 正文提取 Pipeline

    需要在请求时获取完整的 Response
    """

    def __init__(self):
        """初始化"""
        self.items_buffer = []
        self.batch_size = 50

    @classmethod
    def from_crawler(cls, crawler):
        """从 Crawler 创建 Pipeline"""
        return cls()

    def process_item(self, item, spider):
        """
        处理 Item

        注意：这里只能处理已有的 content 字段
        完整实现需要在 Spider 中提取 Response
        """
        return item
