# -*- coding: utf-8 -*-
"""
跨性别资源搜索引擎爬虫 Spider
从 2345.lgbt 收录的网站爬取内容
"""

import scrapy
from urllib.parse import urlparse, urljoin
import trafilatura
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from transspider.config import load_domains, get_random_user_agent, PROJECT_ROOT


def load_domain_tags():
    """从 domains.json 加载域名对应的标签"""
    tags_map = {}
    domains_json = os.path.join(PROJECT_ROOT, "domains.json")
    if os.path.exists(domains_json):
        with open(domains_json, encoding="utf-8") as f:
            data = json.load(f)
            for item in data.get("domains", []):
                domain = item.get("domain", "")
                tags = item.get("tags", [])
                if domain:
                    tags_map[domain] = tags
    return tags_map


class TransSpider(scrapy.Spider):
    """
    跨性别资源爬虫

    特性：
    - 只爬取 allowed_domains 中定义的域名
    - 遵守 robots.txt
    - 随机延迟 1-3 秒
    - 随机 User-Agent
    - 使用 trafilatura 提取正文
    - 手动管理待爬队列
    """

    name = "trans"
    allowed_domains = load_domains()
    start_urls = [f"https://{domain}/" for domain in allowed_domains]
    domain_tags = load_domain_tags()  # 加载域名标签映射

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.seen_urls = set()
        self.page_count = 0
        self.max_pages = 100  # 最多爬取 100 个页面

    def parse(self, response):
        """解析页面"""
        url = response.url

        # 跳过已爬过的 URL
        if url in self.seen_urls:
            return
        self.seen_urls.add(url)

        # 检查是否超过最大页面数
        if self.page_count >= self.max_pages:
            self.logger.info(f"已达到最大页面数 {self.max_pages}，停止爬取")
            return

        self.page_count += 1
        self.logger.info(f"爬取 {self.page_count}/{self.max_pages}: {url}")

        # 提取域名
        domain = urlparse(url).netloc
        if domain.startswith("www."):
            domain = domain[4:]

        # 使用 trafilatura 提取正文
        content = ""
        try:
            content = trafilatura.extract(
                response.text,
                url=url,
                include_comments=False,
                include_tables=False,
            )
        except Exception as e:
            self.logger.warning(f"正文提取失败 {url}: {e}")

        # 创建 Item
        item = {
            "url": url,
            "title": response.css("title::text").get() or "",
            "domain": domain,
            "content": content or "",
            "tags": self.domain_tags.get(domain, []),  # 从 domains.json 获取标签
        }

        # 返回 item 用于 Pipeline 处理
        yield item

        # 提取更多链接
        if self.page_count < self.max_pages:
            # 从页面中提取链接
            links = response.css("a::attr(href)").getall()

            for link in links:
                # 跳过空链接和锚点
                if not link or link.startswith("#"):
                    continue

                # 处理相对路径
                if not link.startswith("http"):
                    link = urljoin(response.url, link)

                # 只爬取同域名的链接
                parsed = urlparse(link)
                link_domain = parsed.netloc
                if link_domain.startswith("www."):
                    link_domain = link_domain[4:]

                # 只爬取 allowed_domains 中的域名
                if link_domain in self.allowed_domains and link not in self.seen_urls:
                    yield scrapy.Request(
                        link,
                        callback=self.parse,
                        headers={"User-Agent": get_random_user_agent()},
                    )
