# Scrapy settings for transspider project
# 跨性别资源搜索引擎爬虫配置

BOT_NAME = "transspider"

SPIDER_MODULES = ["transspider.spiders"]
NEWSPIDER_MODULE = "transspider.spiders"

# 启用自动提取插件
ADDONS = {
    "scrapy_addons.content_extractor.Addon": 500,
}

# ============================================================================
# 用户代理配置
# ============================================================================
import random

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

# ============================================================================
# robots.txt 和爬虫规则
# ============================================================================
ROBOTSTXT_OBEY = True

# ============================================================================
# 并发和限速配置
# ============================================================================
CONCURRENT_REQUESTS_PER_DOMAIN = 1
DOWNLOAD_DELAY = 2  # 默认 2 秒延迟
RANDOMIZE_DOWNLOAD_DELAY = True  # 随机化延迟（1-3秒）

# ============================================================================
# 下载器中间件配置
# ============================================================================
DOWNLOADER_MIDDLEWARES = {
    "transspider.middlewares.RandomUserAgentMiddleware": 400,
    "transspider.middlewares.ProxyMiddleware": 410,  # WARP 代理中间件（可选）
}

# ============================================================================
# Item Pipeline 配置
# ============================================================================
ITEM_PIPELINES = {
    "transspider.pipelines.MeilisearchPipeline": 300,
}

# ============================================================================
# 其他配置
# ============================================================================
# 禁用 Telnet
TELNETCONSOLE_ENABLED = False

# 编码
FEED_EXPORT_ENCODING = "utf-8"

# 请求超时
DOWNLOAD_TIMEOUT = 30

# 自动限流（可选）
# AUTOTHROTTLE_ENABLED = True
# AUTOTHROTTLE_START_DELAY = 2
# AUTOTHROTTLE_MAX_DELAY = 10
