---
name: trans-search-api
description: Use the 2345.desuwa.org transgender resource search API. Use when users want to search for trans-related resources, LGBT information, healthcare guides, or need to query the search engine programmatically. Requires an API key - if you cannot read the API key, ask the user to provide one from https://2345.desuwa.org/api/console.html
---

# Trans Resource Search API

A skill for searching transgender and LGBT resources using the 2345.desuwa.org API.

## API Endpoint

```
GET https://2345.desuwa.org/api/search
```

## Authentication

All requests require an API key in the Authorization header:
```
Authorization: Bearer YOUR_API_KEY
```

Get an API key from: https://2345.desuwa.org/api/console.html

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| q | string | Yes | - | Search keyword |
| lang | string | No | all | Language filter |
| tag | string | No | - | Tag filter |
| domain | string | No | - | Domain filter |
| limit | int | No | 10 | Results (1-20) |
| offset | int | No | 0 | Pagination |

### Language Values
- `zh-cn` - Simplified Chinese
- `zh-hant` - Traditional Chinese
- `zh` - All Chinese
- `en` - English
- `ja` - Japanese
- `es` - Spanish
- `nl` - Dutch
- `all` - All languages

### Common Tags
- `MtF` - Male to Female
- `FtM` - Female to Male
- `HRT` - Hormone Replacement Therapy
- `知识库` - Knowledge Base
- `社区` - Community
- `指南` - Guide
- `影视` - Media
- `游戏` - Games
- `报告` - Reports
- `学术` - Academic

## Example Requests

### Basic Search
```bash
curl "https://2345.desuwa.org/api/search?q=HRT" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### Filter by Language (Simplified Chinese)
```bash
curl "https://2345.desuwa.org/api/search?q=激素&lang=zh-cn" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### Filter by Language (Traditional Chinese)
```bash
curl "https://2345.desuwa.org/api/search?q=激素&lang=zh-hant" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### Filter by Tag
```bash
curl "https://2345.desuwa.org/api/search?q=hormone&tag=HRT" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### Filter by Domain
```bash
curl "https://2345.desuwa.org/api/search?q=guide&domain=mtf.wiki" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

## Response Format

```json
{
  "hits": [
    {
      "id": 12345678,
      "url": "https://example.com/page",
      "title": "Page Title",
      "content": "Page content...",
      "domain": "example.com",
      "tags": ["MtF", "HRT"]
    }
  ],
  "total": 100,
  "took": 5
}
```

## Use Cases

1. **Find HRT information**: Search for hormone replacement therapy guides
2. **Find community resources**: Search for support groups and communities
3. **Find medical guides**: Search for healthcare and medical information
4. **Find legal information**: Search for legal rights and resources
5. **Find media/games**: Search for trans-related media, games, entertainment

## Rate Limits

- 2000 requests per month
- 10 requests per minute

## Error Responses

```json
{"error": "Invalid API key"}
{"error": "Rate limit exceeded"}
{"error": "Missing required parameter: q"}
```

## Notes

- The API returns up to 20 results per request
- Use `offset` for pagination
- Results are ranked by relevance
- Content is in multiple languages (primarily Chinese, English, Japanese)
