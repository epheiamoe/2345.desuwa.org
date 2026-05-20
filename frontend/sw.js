/**
 * Service Worker - 渐进式缓存策略
 *
 * 采用 Stale-While-Revalidate 策略：
 * 1. 优先返回缓存内容（快速响应）
 * 2. 后台发起网络请求更新缓存（保持新鲜）
 * 3. 限制缓存大小，防止无限增长
 *
 * @version 2
 */

const CACHE_VERSION = 2;
const CACHE_NAME = 'trans-search-v' + CACHE_VERSION;

// 核心资源：安装时预缓存
const CORE_URLS = [
    '/',
    '/index.php',
    '/style.css',
    '/search.js',
    '/manifest.json',
    '/icon-192.png',
    '/icon-512.png'
];

// 缓存大小限制（条目数）
const MAX_CACHE_ENTRIES = 100;

/**
 * 安装阶段：预缓存核心资源
 */
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {
                console.log('[SW] Pre-caching core assets');
                return cache.addAll(CORE_URLS);
            })
            .then(() => self.skipWaiting())
            .catch(err => {
                console.warn('[SW] Pre-cache failed:', err);
            })
    );
});

/**
 * 激活阶段：清理旧版本缓存
 */
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.map(cacheName => {
                    if (cacheName !== CACHE_NAME) {
                        console.log('[SW] Deleting old cache:', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        }).then(() => self.clients.claim())
    );
});

/**
 * 清理缓存，限制条目数量
 * 采用 LRU 策略：删除最旧的条目
 *
 * @param {Cache} cache 缓存对象
 * @param {number} maxEntries 最大条目数
 */
async function trimCache(cache, maxEntries) {
    const keys = await cache.keys();
    if (keys.length <= maxEntries) {
        return;
    }

    // 删除最旧的条目
    const entriesToDelete = keys.length - maxEntries;
    const deletePromises = keys.slice(0, entriesToDelete).map(request => {
        console.log('[SW] Trimming cache:', request.url);
        return cache.delete(request);
    });

    await Promise.all(deletePromises);
}

/**
 * 判断请求是否应该被缓存
 *
 * @param {Request} request 请求对象
 * @returns {boolean}
 */
function shouldCache(request) {
    // 只缓存 GET 请求
    if (request.method !== 'GET') {
        return false;
    }

    // 跳过 API 请求
    if (request.url.includes('/api/')) {
        return false;
    }

    // 跳过外部请求
    if (!request.url.startsWith(self.location.origin)) {
        return false;
    }

    return true;
}

/**
 * Stale-While-Revalidate 策略：
 * 1. 立即返回缓存（如果存在）
 * 2. 后台更新缓存（网络请求）
 * 3. 如果缓存未命中，等待网络响应
 */
self.addEventListener('fetch', event => {
    if (!shouldCache(event.request)) {
        return;
    }

    event.respondWith(
        caches.open(CACHE_NAME).then(async cache => {
            const cachedResponse = await cache.match(event.request);

            // 发起后台网络请求更新缓存
            const fetchPromise = fetch(event.request).then(networkResponse => {
                if (networkResponse && networkResponse.status === 200 && networkResponse.type === 'basic') {
                    const responseToCache = networkResponse.clone();
                    cache.put(event.request, responseToCache).then(() => {
                        // 更新后检查缓存大小
                        trimCache(cache, MAX_CACHE_ENTRIES);
                    });
                }
                return networkResponse;
            }).catch(err => {
                console.warn('[SW] Network fetch failed:', err);
                return null;
            });

            // 优先返回缓存，否则等待网络
            if (cachedResponse) {
                // 返回缓存，同时后台更新
                return cachedResponse;
            }

            // 缓存未命中，等待网络响应
            return fetchPromise.then(networkResponse => {
                if (networkResponse) {
                    return networkResponse;
                }
                // 网络也失败了，返回离线页面（导航请求）
                if (event.request.mode === 'navigate') {
                    return caches.match('/');
                }
                return new Response('Network error', { status: 408 });
            });
        })
    );
});

/**
 * 处理来自客户端的消息
 */
self.addEventListener('message', event => {
    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
});
