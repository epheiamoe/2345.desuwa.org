# -*- coding: utf-8 -*-
"""
Scrapy 跨性别资源爬虫配置

配置加载策略（优先级从高到低）：
1. 环境变量（生产环境推荐）
2. 共享 ``config.json``（与前端/API 共用同一配置源）
3. 内置默认值

仅爬取 2345.lgbt 导航站收录的网站。
"""

import json
import os
import random

# 项目根目录（自动检测）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 配置文件路径
CONFIG_JSON = os.path.join(PROJECT_ROOT, "config.json")
DOMAINS_JSON = os.path.join(PROJECT_ROOT, "domains.json")

# 共享配置缓存，避免重复读取磁盘
_shared_config: dict = {}
_domains_data: dict = {}


def _load_shared_config() -> dict:
    """加载共享 ``config.json``，结果缓存在模块级别。"""
    global _shared_config
    if not _shared_config and os.path.exists(CONFIG_JSON):
        with open(CONFIG_JSON, encoding="utf-8") as f:
            _shared_config = json.load(f)
    return _shared_config


def _load_domains_json() -> dict:
    """加载 ``domains.json``，结果缓存在模块级别。"""
    global _domains_data
    if not _domains_data and os.path.exists(DOMAINS_JSON):
        with open(DOMAINS_JSON, encoding="utf-8") as f:
            _domains_data = json.load(f)
    return _domains_data


# ---------------------------------------------------------------------------
# Meilisearch 配置（优先环境变量，回退到共享 config.json，最后硬编码默认值）
# ---------------------------------------------------------------------------
_cfg = _load_shared_config()
_meili_cfg = _cfg.get("meilisearch", {})
_search_cfg = _cfg.get("search", {})

MEILISEARCH_HOST: str = os.environ.get(
    "MEILISEARCH_HOST", _meili_cfg.get("host", "localhost")
)
MEILISEARCH_PORT: int = int(
    os.environ.get("MEILISEARCH_PORT", _meili_cfg.get("port", 7700))
)
MEILISEARCH_INDEX: str = os.environ.get(
    "MEILISEARCH_INDEX", _search_cfg.get("index_name", "trans_resources")
)
MEILISEARCH_API_KEY: str = os.environ.get("MEILISEARCH_API_KEY", "")

# ---------------------------------------------------------------------------
# 爬虫行为配置
# ---------------------------------------------------------------------------
# 是否使用 WARP 代理（默认关闭，仅在 IP 被封时手动开启）
USE_WARP_PROXY: bool = os.environ.get("USE_WARP_PROXY", "false").lower() == "true"
WARP_SOCKS5_PROXY: str = os.environ.get("WARP_SOCKS5_PROXY", "socks5://127.0.0.1:1080")

# 随机 User-Agent 池
USER_AGENTS: list[str] = [
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) "
        "Gecko/20100101 Firefox/121.0"
    ),
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/17.1 Safari/605.1.15"
    ),
]


# ---------------------------------------------------------------------------
# 配置加载函数
# ---------------------------------------------------------------------------


def load_domains() -> list[str]:
    """
    从 ``domains.json`` 加载域名列表（用于 ``allowed_domains`` 过滤）。

    Returns:
        域名字符串列表。若文件不存在则返回空列表。
    """
    data = _load_domains_json()
    domains: list[str] = []
    for item in data.get("domains", []):
        domain = item.get("domain", "")
        if domain:
            domains.append(domain)
    return domains


def load_start_urls() -> list[str]:
    """
    从 ``domains.json`` 加载起始 URL 列表。

    Returns:
        URL 字符串列表。若文件不存在则返回空列表。
    """
    data = _load_domains_json()
    urls: list[str] = []
    for item in data.get("domains", []):
        url = item.get("url", "")
        if url:
            urls.append(url)
    return urls


def get_random_user_agent() -> str:
    """
    从预定义池中随机选择一个 User-Agent。

    Returns:
        User-Agent 字符串。
    """
    return random.choice(USER_AGENTS)
