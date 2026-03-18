# -*- coding: utf-8 -*-
"""
Scrapy 中间件
包含：
1. 随机 User-Agent 中间件
2. WARP 代理中间件（可选）
"""

import random
import os
import sys

from scrapy import signals
from itemadapter import ItemAdapter

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入配置
from transspider.config import USE_WARP_PROXY, WARP_SOCKS5_PROXY


# 随机 User-Agent 列表
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
]


class RandomUserAgentMiddleware:
    """
    随机 User-Agent 中间件

    每次请求随机选择一个 User-Agent
    避免被目标网站识别为爬虫
    """

    @classmethod
    def from_crawler(cls, crawler):
        """从 Crawler 创建中间件"""
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_request(self, request, spider):
        """
        处理请求，设置随机 User-Agent
        """
        request.headers["User-Agent"] = random.choice(USER_AGENTS)

    def spider_opened(self, spider):
        """爬虫启动时记录"""
        spider.logger.info("RandomUserAgentMiddleware 已启用")


class ProxyMiddleware:
    """
    WARP 代理中间件（可选）

    从 config.py 读取配置，控制是否启用 WARP 代理
    """

    ENABLED = USE_WARP_PROXY
    PROXY = WARP_SOCKS5_PROXY

    @classmethod
    def from_crawler(cls, crawler):
        """从 Crawler 创建中间件"""
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_request(self, request, spider):
        """
        处理请求，添加代理

        仅在启用时添加代理
        """
        if self.ENABLED and self.PROXY:
            request.meta["proxy"] = self.PROXY
            spider.logger.info(f"使用代理: {self.PROXY}")

    def spider_opened(self, spider):
        """爬虫启动时记录"""
        if self.ENABLED:
            spider.logger.info(f"ProxyMiddleware 已启用，使用代理: {self.PROXY}")
        else:
            spider.logger.info("ProxyMiddleware 已安装但未启用（默认直连）")


class TransspiderSpiderMiddleware:
    """
    Spider 中间件基类
    """

    @classmethod
    def from_crawler(cls, crawler):
        """从 Crawler 创建中间件"""
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_spider_input(self, response, spider):
        """处理输入"""
        return None

    def process_spider_output(self, response, result, spider):
        """处理输出"""
        for i in result:
            yield i

    def process_spider_exception(self, response, exception, spider):
        """处理异常"""
        pass

    async def process_start(self, start):
        """处理启动"""
        async for item_or_request in start:
            yield item_or_request

    def spider_opened(self, spider):
        """爬虫启动"""
        spider.logger.info("Spider opened: %s" % spider.name)


class TransspiderDownloaderMiddleware:
    """
    下载器中间件基类
    """

    @classmethod
    def from_crawler(cls, crawler):
        """从 Crawler 创建中间件"""
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_request(self, request, spider):
        """处理请求"""
        return None

    def process_response(self, request, response, spider):
        """处理响应"""
        return response

    def process_exception(self, request, exception, spider):
        """处理异常"""
        pass

    def spider_opened(self, spider):
        """爬虫启动"""
        spider.logger.info("Spider opened: %s" % spider.name)
