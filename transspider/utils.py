"""跨性别资源搜索引擎 - URL 工具函数

提供 URL 规范化与域名校验工具，确保爬虫内部 URL 表示的一致性，
降低因 URL 形式差异导致的重复爬取或 ID 冲突风险。
"""

from urllib.parse import parse_qs, urlencode, urlparse, urlunparse


def normalize_url(url: str) -> str:
    """规范化 URL。

    执行以下规范化操作：
    1. 去除 fragment（# 后的内容）
    2. 统一尾部斜杠（去除尾部斜杠，根路径 ``/`` 除外）
    3. 排序 query 参数（按键名排序，值列表内部也排序）
    4. 小写 scheme 和 netloc
    5. 去除 HTTP/HTTPS 默认端口（``:80``、``:443``）

    这些规则确保 ``https://example.com/path?b=2&a=1`` 与
    ``https://example.com/path/?a=1&b=2`` 被归一化为同一字符串，
    从而减少 Meilisearch 文档 ID 的伪冲突。

    Args:
        url: 原始 URL 字符串。

    Returns:
        规范化后的 URL 字符串。若输入为空字符串则返回空字符串。
    """
    if not url:
        return ""

    parsed = urlparse(url.strip())

    # 1. 小写 scheme 与 netloc
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()

    # 2. 去除默认端口
    if (scheme == "http" and netloc.endswith(":80")) or (
        scheme == "https" and netloc.endswith(":443")
    ):
        netloc = netloc.rsplit(":", 1)[0]

    # 3. 规范化路径：去除尾部斜杠（根路径除外）
    path = parsed.path
    if path and path != "/" and path.endswith("/"):
        path = path[:-1]

    # 4. 排序 query 参数
    query = ""
    if parsed.query:
        query_params = parse_qs(parsed.query, keep_blank_values=True)
        # 先按键名排序，再对每个值列表内部排序
        sorted_params = sorted((k, sorted(v)) for k, v in query_params.items())
        query = urlencode(sorted_params, doseq=True)

    # 5. 去除 fragment
    fragment = ""

    return urlunparse((scheme, netloc, path, "", query, fragment))


def is_valid_url(url: str, allowed_domains: list[str]) -> bool:
    """检查 URL 是否在允许的域名列表中。

    域名比较时会去除 ``www.`` 前缀并统一转为小写，
    与 ``allowed_domains`` 中预期的域名格式保持一致。

    Args:
        url: 待检查的 URL。
        allowed_domains: 允许的域名列表（通常不含 ``www.`` 前缀）。

    Returns:
        若 URL 的域名在允许列表中则返回 ``True``；空 URL 返回 ``False``。
    """
    if not url:
        return False

    parsed = urlparse(url)
    domain = parsed.netloc.lower()

    if domain.startswith("www."):
        domain = domain[4:]

    return domain in allowed_domains
