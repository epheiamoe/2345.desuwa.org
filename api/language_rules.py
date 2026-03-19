# -*- coding: utf-8 -*-
"""
语言检测规则配置

此文件定义了 URL 到语言的映射规则，用于搜索引擎的语言筛选功能。
规则按优先级排序，匹配即返回。

自部署者可以修改此文件来自定义语言检测规则。
"""

import re
from urllib.parse import urlparse

# 语言路径到语言的映射（最优先）
LANGUAGE_PATH_MAP = {
    "zh-cn": "zh-cn",
    "zh-hant": "zh-hant",
    "zh-tw": "zh-hant",
    "zh-hk": "zh-hant",
    "zh-sg": "zh-cn",
    "zh": "zh",
    "en": "en",
    "ja": "ja",
    "es": "es",
    "nl": "nl",
    "ko": "ko",
    "fr": "fr",
    "de": "de",
    "pl": "pl",
    "el": "el",
    "hu": "hu",
    "ru": "ru",
    "it": "it",
    "pt": "pt",
    "th": "th",
    "vi": "vi",
    "id": "id",
    "ms": "ms",
}

# 无语言路径的域名默认语言映射
DOMAIN_DEFAULT_LANG = {
    # 中文内容为主的域名
    "mtf.wiki": "zh-cn",
    "ftm.wiki": "zh-cn",
    "rle.wiki": "zh-cn",
    "tfsci.mtf.wiki": "zh-cn",
    "blog.project-trans.org": "zh-cn",
    "project-trans.org": "zh-cn",
    "docs.transonline.org.cn": "zh-cn",
    "transchinese.org": "zh-cn",
    "digital.transchinese.org": "zh-cn",
    "cnlgbtdata.com": "zh-cn",
    "aboutrans.info": "zh-cn",
    "transinacademia.org": "zh-cn",
    "viva-la-vita.org": "zh-cn",
    "oneamongus.ca": "zh-cn",
    "hub.mtf.party": "zh-cn",
    # 英文内容为主的域名
    "genderdysphoria.fyi": "en",
    "transmanhelper.com": "en",
    "mtf.party": "zh-cn",
    "knowsex.net": "zh-cn",
    # 其他
    "uniguide.oau.edu.kg": "en",
}

# URL 模式正则表达式到语言的映射
URL_PATTERN_RULES = [
    # 英文模式
    {"pattern": r"/tweets?/", "lang": "en", "weight": 10},
    {"pattern": r"/tweet/", "lang": "en", "weight": 10},
    {"pattern": r"/privacy\.html$", "lang": "en", "weight": 5},
    {"pattern": r"/about\.html$", "lang": "en", "weight": 5},
    {"pattern": r"/contact\.html$", "lang": "en", "weight": 5},
    # 中文模式
    {"pattern": r"/\bdocs\b/", "lang": "zh-cn", "weight": 3},
    {"pattern": r"/category/.+[\u4e00-\u9fff]", "lang": "zh-cn", "weight": 8},
    {"pattern": r"/tag/.+[\u4e00-\u9fff]", "lang": "zh-cn", "weight": 8},
    {"pattern": r"/\bposts?\b/", "lang": "zh-cn", "weight": 3},
]

# 中文Unicode范围
CHINESE_PATTERN = re.compile(r"[\u4e00-\u9fff]")


def detect_language_from_url(url):
    """
    从 URL 检测语言

    Args:
        url: 完整的 URL

    Returns:
        str: 语言代码 (zh-cn, zh-hant, en, ja, es, nl, ko, fr, de, pl, el, hu, ru, ...)
    """
    # 1. 首先检查 URL 路径中的语言路径
    for path, lang in LANGUAGE_PATH_MAP.items():
        if f"/{path}/" in url or url.endswith(f"/{path}"):
            return lang

    # 2. 检查 URL 模式规则
    best_match = None
    best_weight = 0

    for rule in URL_PATTERN_RULES:
        if re.search(rule["pattern"], url, re.IGNORECASE):
            if rule["weight"] > best_weight:
                best_weight = rule["weight"]
                best_match = rule["lang"]

    if best_match:
        return best_match

    # 3. 从域名判断默认语言
    parsed = urlparse(url)
    host = parsed.netloc

    # 移除 www. 前缀
    if host.startswith("www."):
        host = host[4:]

    if host in DOMAIN_DEFAULT_LANG:
        return DOMAIN_DEFAULT_LANG[host]

    # 4. 从路径中判断（检查中文字符）
    path = parsed.path
    if CHINESE_PATTERN.search(path):
        return "zh-cn"

    # 5. 默认返回空字符串
    return ""


def language_matches(url, selected_lang):
    """
    检测语言是否匹配用户选择的语言

    Args:
        url: 要检测的 URL
        selected_lang: 用户选择的语言筛选

    Returns:
        bool: 是否匹配
    """
    if not selected_lang or selected_lang == "all" or selected_lang == "全部":
        return True

    detected_lang = detect_language_from_url(url)

    # 特殊处理：zh 筛选器匹配所有中文
    if selected_lang == "zh":
        return detected_lang in ("zh-cn", "zh-hant", "zh", "")

    return detected_lang == selected_lang
