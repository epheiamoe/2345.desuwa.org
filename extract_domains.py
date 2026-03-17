#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
域名提取脚本
从 2345.LGBT 仓库的所有 Markdown 文件中提取链接的域名
"""

import os
import re
from pathlib import Path
from urllib.parse import urlparse

# 项目根目录
PROJECT_ROOT = Path(__file__).parent
REPO_DIR = PROJECT_ROOT / "2345-lgbt-repo"

# 存储提取到的域名
domains = set()

# 正则表达式匹配 Markdown 链接 [text](url)
link_pattern = re.compile(r"\[([^\]]*)\]\((https?://[^)]+)\)")


def extract_domains_from_file(file_path):
    """从单个 Markdown 文件中提取域名"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 查找所有链接
        matches = link_pattern.findall(content)

        for text, url in matches:
            try:
                parsed = urlparse(url)
                domain = parsed.netloc.lower()
                # 移除 www. 前缀
                if domain.startswith("www."):
                    domain = domain[4:]
                if domain:
                    domains.add(domain)
            except Exception:
                continue
    except Exception as e:
        print(f"读取文件失败 {file_path}: {e}")


def scan_directory(dir_path):
    """递归扫描目录下所有 Markdown 文件"""
    for root, dirs, files in os.walk(dir_path):
        # 跳过 .git 目录
        if ".git" in root:
            continue
        for file in files:
            if file.endswith(".md"):
                file_path = os.path.join(root, file)
                extract_domains_from_file(file_path)


def main():
    print(f"开始扫描目录: {REPO_DIR}")

    if not REPO_DIR.exists():
        print(f"错误: 仓库目录不存在: {REPO_DIR}")
        return

    # 扫描所有 content 目录
    scan_directory(REPO_DIR / "content.zh-cn")
    scan_directory(REPO_DIR / "content.zh-tw")
    scan_directory(REPO_DIR / "content.zh-hk")
    scan_directory(REPO_DIR / "content.en")
    scan_directory(REPO_DIR / "content.ja")
    scan_directory(REPO_DIR / "content.nl")

    # 排序并保存
    domains_list = sorted(list(domains))

    output_file = PROJECT_ROOT / "domains.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        for domain in domains_list:
            f.write(domain + "\n")

    print(f"\n共提取到 {len(domains_list)} 个域名")
    print(f"已保存到: {output_file}")
    print("\n域名列表:")
    for d in domains_list:
        print(f"  - {d}")


if __name__ == "__main__":
    main()
