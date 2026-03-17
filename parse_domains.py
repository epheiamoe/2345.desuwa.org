#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
解析 domains.md 提取域名和标签
生成 domains.json 供爬虫使用
"""

import re
import json

# 读取 domains.md
with open("domains.md", "r", encoding="utf-8") as f:
    content = f.read()

# 提取所有链接的正则
link_pattern = re.compile(r"\[([^\]]+)\]\((https?://[^)]+)\)")

# 标签映射
tag_mapping = {
    "MtF": ["MtF", "mtf", "Mtf"],
    "FtM": ["FtM", "ftm", "Ftm"],
    "社区": ["社区"],
    "性": ["性"],
    "知识库": ["知识库"],
    "HRT": ["HRT", "hrt"],
    "医疗": ["医疗", "指南", "HRT"],
    "学术": ["学术", "研究"],
    "法律": ["法律"],
    "报告": ["报告"],
    "影视": ["影视", "小说", "电影", "游戏", "音乐"],
    "公众号": ["微信", "公众号"],
}


def extract_tags(line):
    """从行中提取标签"""
    tags = []
    line_lower = line.lower()

    # 检测 MtF/FtM
    if "mtf" in line_lower or "mtF" in line:
        tags.append("MtF")
    if "ftm" in line_lower or "ftM" in line:
        tags.append("FtM")

    # 检测其他标签
    for tag, keywords in tag_mapping.items():
        for kw in keywords:
            if kw.lower() in line_lower:
                if tag not in tags:
                    tags.append(tag)
                break

    return tags


# 提取域名
domains = []
seen_domains = set()

# 按行解析
lines = content.split("\n")
for line in lines:
    # 跳过标题行
    if line.startswith("#"):
        continue

    # 提取链接
    matches = link_pattern.findall(line)
    for text, url in matches:
        # 提取域名
        match = re.search(r"https?://([^/]+)", url)
        if match:
            domain = match.group(1).lower()
            # 移除 www. 前缀
            if domain.startswith("www."):
                domain = domain[4:]

            # 跳过已存在的域名
            if domain in seen_domains:
                continue
            seen_domains.add(domain)

            # 提取标签
            tags = extract_tags(line)

            # 清理 URL（移除结尾的斜杠）
            url = url.rstrip("/")

            domains.append(
                {"domain": domain, "url": url, "name": text.strip(), "tags": tags}
            )

# 保存为 JSON
output = {
    "description": "2345.desuwa.org 域名列表",
    "domains": domains,
    "all_tags": list(set([tag for d in domains for tag in d["tags"]])),
}

with open("domains.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"提取了 {len(domains)} 个域名")
print(f"标签: {output['all_tags']}")

# 生成简单的域名列表（仅域名）
with open("domains.txt", "w", encoding="utf-8") as f:
    for d in domains:
        f.write(d["domain"] + "\n")

print(f"已保存到 domains.json 和 domains.txt")
