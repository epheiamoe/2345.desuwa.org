# Scrapy settings for transspider project
# 跨性别资源搜索引擎爬虫配置

BOT_NAME = "transspider"

SPIDER_MODULES = ["transspider.spiders"]
NEWSPIDER_MODULE = "transspider.spiders"

# ============================================================================
# 去重配置
# ============================================================================
# 使用 Scrapy 内置 RFPDupeFilter，URL 去重由框架负责，Spider 不再维护 seen_urls
DUPEFILTER_CLASS = "scrapy.dupefilters.RFPDupeFilter"

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
