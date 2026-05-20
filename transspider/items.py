"""跨性别资源搜索引擎 - Items 定义"""

import scrapy


class TransResourceItem(scrapy.Item):
    """跨性别资源数据模型

    字段：
    - url: 页面 URL
    - title: 页面标题
    - content: 正文内容（提取后）
    - html: 原始 HTML（用于提取 license）
    - domain: 域名
    - tags: 标签列表
    - license_type: 版权许可类型（标准化）
    - license_url: 版权许可 URL
    """

    url = scrapy.Field()
    title = scrapy.Field()
    content = scrapy.Field()
    html = scrapy.Field()
    domain = scrapy.Field()
    tags = scrapy.Field()
    license_type = scrapy.Field()
    license_url = scrapy.Field()
