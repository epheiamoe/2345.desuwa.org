"""跨性别资源搜索引擎爬虫 Spider

从 2345.lgbt 收录的网站爬取内容。
"""

import os
import sys
from collections.abc import Generator
from typing import Any

import scrapy
import trafilatura
from scrapy.http import Response

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from transspider.config import (
    PROJECT_ROOT,
    get_random_user_agent,
    load_domains,
    load_start_urls,
)
from transspider.items import TransResourceItem
from transspider.utils import is_valid_url, normalize_url


def load_domain_tags() -> tuple[dict, set]:
    """从 ``domains.json`` 加载域名对应的标签和 ``no_follow`` 标记。

    Returns:
        ``(tags_map, no_follow_domains)`` 元组。
        ``tags_map`` 为 ``domain -> tags`` 映射；
        ``no_follow_domains`` 为不跟进的域名集合。
    """
    tags_map: dict = {}
    no_follow_domains: set = set()
    domains_json = os.path.join(PROJECT_ROOT, "domains.json")
    if os.path.exists(domains_json):
        import json

        with open(domains_json, encoding="utf-8") as f:
            data = json.load(f)
            for item in data.get("domains", []):
                domain = item.get("domain", "")
                if domain:
                    tags_map[domain] = item.get("tags", [])
                if item.get("no_follow", False):
                    no_follow_domains.add(domain)
    return tags_map, no_follow_domains


class TransSpider(scrapy.Spider):
    """跨性别资源爬虫。

    特性：
    - 只爬取 ``allowed_domains`` 中定义的域名
    - 遵守 robots.txt
    - 随机延迟 1-3 秒
    - 随机 User-Agent
    - 使用 trafilatura 提取正文
    - 依赖 Scrapy 内置 ``RFPDupeFilter`` 去重，不维护手动集合
    """

    name = "trans"
    allowed_domains = load_domains()
    domain_tags, no_follow_domains = load_domain_tags()
    start_urls = load_start_urls()

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.page_count = 0
        self.max_pages = 10000

    def parse(self, response: Response) -> Generator:
        """解析页面主入口。

        执行流程：
        1. 检查全局页面数上限；
        2. 跳过非文本响应；
        3. 提取正文并构建 Item；
        4. 若域名允许，提取页面内链接并生成后续请求。

        Args:
            response: Scrapy Response 对象。

        Yields:
            ``TransResourceItem`` 或 ``scrapy.Request``。
        """
        url = response.url

        if self.page_count >= self.max_pages:
            self.logger.info("已达到最大页面数 %s，停止爬取", self.max_pages)
            return

        self.page_count += 1
        self.logger.info("爬取 %s/%s: %s", self.page_count, self.max_pages, url)

        if not self._is_text_response(response):
            return

        content = self._extract_content(response)
        item = self._build_item(response, content)
        if item is not None:
            yield item

        if self._should_follow(response):
            yield from self._extract_link_requests(response)

    def _is_text_response(self, response: Response) -> bool:
        """判断响应是否为可处理的文本类型。

        Args:
            response: Scrapy Response 对象。

        Returns:
            若 Content-Type 以 ``text/`` 或 ``application/xhtml`` 开头则返回 ``True``。
        """
        content_type = response.headers.get("Content-Type", b"").decode(
            "latin-1", "ignore"
        )
        if not content_type.startswith(("text/", "application/xhtml")):
            self.logger.warning(
                "跳过非文本内容: %s (Content-Type: %s)",
                response.url,
                content_type,
            )
            return False
        return True

    def _extract_content(self, response: Response) -> str:
        """使用 trafilatura 提取页面正文。

        Args:
            response: Scrapy Response 对象。

        Returns:
            提取到的正文文本；失败时返回空字符串。
        """
        try:
            extracted = trafilatura.extract(
                response.text,
                url=response.url,
                include_comments=False,
                include_tables=False,
            )
            return extracted or ""
        except (ValueError, TypeError, AttributeError) as exc:
            self.logger.warning("正文提取失败 %s: %s", response.url, exc)
            return ""

    def _build_item(self, response: Response, content: str) -> TransResourceItem | None:
        """根据响应与正文构建 ``TransResourceItem``。

        Args:
            response: Scrapy Response 对象。
            content: 已提取的正文。

        Returns:
            构建好的 Item；若标题为空则返回 ``None``。
        """
        url = response.url
        domain = self._extract_domain(url)

        try:
            title = (response.css("title::text").get() or "").strip()
        except (AttributeError, TypeError):
            title = ""

        if not title:
            self.logger.warning("页面缺少标题，跳过: %s", url)
            return None

        item = TransResourceItem()
        item["url"] = url
        item["title"] = title
        item["domain"] = domain
        item["content"] = content
        item["html"] = response.text
        item["tags"] = self.domain_tags.get(domain, [])
        return item

    def _should_follow(self, response: Response) -> bool:
        """判断当前页面是否需要继续提取链接跟进。

        Args:
            response: Scrapy Response 对象。

        Returns:
            若域名不在 ``no_follow_domains`` 且未达页面上限则返回 ``True``。
        """
        domain = self._extract_domain(response.url)
        return domain not in self.no_follow_domains and self.page_count < self.max_pages

    def _extract_link_requests(self, response: Response) -> Generator:
        """从页面中提取同域名链接并生成 ``scrapy.Request``。

        所有链接会先经 ``normalize_url`` 规范化，再经 ``is_valid_url`` 校验。
        URL 去重完全交由 Scrapy 内置的 ``RFPDupeFilter`` 处理，
        本方法不再维护独立的 ``seen_urls`` 集合。

        Args:
            response: Scrapy Response 对象。

        Yields:
            ``scrapy.Request`` 对象。
        """
        raw_links = response.css("a::attr(href)").getall()

        for link in raw_links:
            if not link or link.startswith("#"):
                continue

            absolute_url = response.urljoin(link)
            normalized = normalize_url(absolute_url)

            if not is_valid_url(normalized, self.allowed_domains):
                continue

            yield scrapy.Request(
                normalized,
                callback=self.parse,
                headers={"User-Agent": get_random_user_agent()},
            )

    @staticmethod
    def _extract_domain(url: str) -> str:
        """从 URL 中提取域名并去除 ``www.`` 前缀。

        Args:
            url: 页面 URL。

        Returns:
            小写域名（不含 ``www.`` 前缀）。
        """
        from urllib.parse import urlparse

        domain = urlparse(url).netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
