# -*- coding: utf-8 -*-
"""
跨性别资源搜索引擎 - Items 定义
"""

import scrapy


class TransResourceItem(scrapy.Item):
    """
    跨性别资源数据模型

    字段：
    - url: 页面 URL
    - title: 页面标题
    - content: 正文内容（提取后）
    - domain: 域名
    - tags: 标签列表
    """

    url = scrapy.Field()
    title = scrapy.Field()
    content = scrapy.Field()
    domain = scrapy.Field()
    tags = scrapy.Field()
