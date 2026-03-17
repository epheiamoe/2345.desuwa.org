# -*- coding: utf-8 -*-
"""
Scrapy 跨性别资源爬虫
仅爬取 2345.lgbt 导航站收录的网站
"""

import os

# 项目根目录（自动检测）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 域名列表文件 - 使用相对于项目根目录的路径
# 先尝试 domains_test.txt（测试用），如果没有则使用 domains.txt
DOMAINS_FILE = os.path.join(PROJECT_ROOT, "domains_test.txt")
if not os.path.exists(DOMAINS_FILE):
    DOMAINS_FILE = os.path.join(PROJECT_ROOT, "domains.txt")

# Meilisearch 配置
MEILISEARCH_HOST = "localhost"
MEILISEARCH_PORT = 7700
MEILISEARCH_INDEX = "trans_resources"
MEILISEARCH_API_KEY = ""  # 本地开发无需密钥

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
import os


def load_domains():
    """从文件加载域名列表"""
    domains = []
    with open(DOMAINS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                domains.append(line)
    return domains


def get_random_user_agent():
    """随机获取 User-Agent"""
    return random.choice(USER_AGENTS)
