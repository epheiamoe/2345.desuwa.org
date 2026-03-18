# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.1.0] - 2026-03-18

### Added
- Language field in Meilisearch documents for efficient language filtering
- SITE_URL environment variable for OAuth callback configuration
- MEILISEARCH_API_KEY support for API and crawler

### Changed
- Language filtering now pushed to Meilisearch layer instead of post-filtering
- Filter logic changed from OR to AND for tags and domain

### Fixed
- ProxyMiddleware now reads configuration from config.py instead of hardcoded values
- Credits persistence - now saves to db.json on each search
- Filter injection vulnerability - filter values are now escaped
- ADMIN_USERS whitespace issue - now trims whitespace
- Rate limiting IP detection behind reverse proxy
- Domain filter lost on pagination in frontend
- Spider now uses TransResourceItem instead of plain dict

## [1.0.0] - 2026-03-17

### Added
- Multi-language search support (zh-cn, zh-hant, zh, en, ja, es, nl)
- Tag filtering for search results
- Domain filtering
- GitHub OAuth authentication for API
- Free API with 2000 credits/month, 10 requests/minute
- API console for key management
- Admin panel for user management (ban/unban)
- Privacy policy, terms, and disclaimer documents
- API documentation
- Self-hosting support with detailed README

### Fixed
- Duplicate indexing issue (using URL hash as document ID)
- Language detection from URL path
- Nginx proxy configuration
- Flask environment variable loading

### Changed
- Meilisearch as search backend
- Scrapy for web crawling
- Simple PHP frontend

## [0.1.0] - 2026-01-01

### Added
- Initial project setup
- Basic search functionality
- Domain list from 2345.lgbt

---

For older releases, please refer to the git history.
