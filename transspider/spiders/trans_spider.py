# -*- coding: utf-8 -*-
"""
跨性别资源搜索引擎爬虫 Spider
从 2345.lgbt 收录的网站爬取内容
"""

import scrapy
from urllib.parse import urlparse
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from transspider.config import load_domains, get_random_user_agent


class TransSpider(CrawlSpider):
    """
    跨性别资源爬虫

    特性：
    - 只爬取 allowed_domains 中定义的域名
    - 遵守 robots.txt
    - 随机延迟 1-3 秒
    - 随机 User-Agent
    """

    name = "trans"
    allowed_domains = load_domains()

    # 从域名生成起始 URL
    start_urls = [f"https://{domain}/" for domain in allowed_domains]

    # 允许的链接提取规则：只 follow 同域链接
    rules = (
        Rule(
            LinkExtractor(
                allow_domains=allowed_domains,
                deny_extensions=[
                    "jpg",
                    "jpeg",
                    "png",
                    "gif",
                    "pdf",
                    "zip",
                    "mp3",
                    "mp4",
                    "avi",
                ],
            ),
            callback="parse_item",
            follow=True,
        ),
    )

    def __init__(self, *args, **kwargs):
        """初始化爬虫"""
        super(TransSpider, self).__init__(*args, **kwargs)
        self.custom_settings = {
            "USER_AGENT": get_random_user_agent(),
        }

    def start_requests(self):
        """
        重写起始请求，添加随机 User-Agent
        """
        for url in self.start_urls:
            yield scrapy.Request(
                url,
                callback=self.parse_start_url,
                headers={"User-Agent": get_random_user_agent()},
            )

    def parse_start_url(self, response):
        """
        处理起始 URL
        """
        return self.parse_item(response)

    def parse_item(self, response):
        """
        解析页面内容

        提取：
        - URL
        - 标题
        - 正文内容（通过 Pipeline 处理）
        - 域名
        """
        # 提取域名
        domain = urlparse(response.url).netloc
        if domain.startswith("www."):
            domain = domain[4:]

        # 创建 Item
        item = {
            "url": response.url,
            "title": response.css("title::text").get() or "",
            "domain": domain,
            "content": "",  # 正文由 Pipeline 提取
        }

        return item

    def _set_user_agent(self, request, spider):
        """
        中间件回调：设置随机 User-Agent
        """
        request.headers["User-Agent"] = get_random_user_agent()
