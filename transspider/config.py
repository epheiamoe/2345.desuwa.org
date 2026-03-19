# -*- coding: utf-8 -*-
"""
Scrapy 跨性别资源爬虫
仅爬取 2345.lgbt 导航站收录的网站
"""

import os
import json

# 项目根目录（自动检测）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 域名列表 - 优先使用 domains.json
DOMAINS_JSON = os.path.join(PROJECT_ROOT, "domains.json")

# Meilisearch 配置
MEILISEARCH_HOST = os.environ.get("MEILISEARCH_HOST", "localhost")
MEILISEARCH_PORT = int(os.environ.get("MEILISEARCH_PORT", "7700"))
MEILISEARCH_INDEX = "trans_resources"
MEILISEARCH_API_KEY = os.environ.get("MEILISEARCH_API_KEY", "")

# 爬虫配置
# 是否使用 WARP 代理（默认关闭，仅在 IP 被封时手动开启）
USE_WARP_PROXY = False
WARP_SOCKS5_PROXY = "socks5://127.0.0.1:1080"  # WARP 本地 socks5 端口

# 随机 User-Agent
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
]

import random


def load_domains():
    """从 domains.json 加载域名列表（用于 allowed_domains 过滤）"""
    domains = []
    if os.path.exists(DOMAINS_JSON):
        with open(DOMAINS_JSON, encoding="utf-8") as f:
            data = json.load(f)
            for item in data.get("domains", []):
                domain = item.get("domain", "")
                if domain:
                    domains.append(domain)
    return domains


def load_start_urls():
    """从 domains.json 加载起始 URL 列表"""
    urls = []
    if os.path.exists(DOMAINS_JSON):
        with open(DOMAINS_JSON, encoding="utf-8") as f:
            data = json.load(f)
            for item in data.get("domains", []):
                url = item.get("url", "")
                if url:
                    urls.append(url)
    return urls


def get_random_user_agent():
    """随机获取 User-Agent"""
    return random.choice(USER_AGENTS)
