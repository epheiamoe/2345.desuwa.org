<?php

declare(strict_types=1);

/**
 * 搜索逻辑模块
 *
 * 封装与 Meilisearch 的通信、速率限制、过滤条件构建等核心搜索逻辑。
 *
 * @package TransSearch
 * @license MIT
 */

if (!defined('TRANS_SEARCH')) {
    define('TRANS_SEARCH', true);
}

/**
 * 获取真实客户端 IP（支持反向代理）
 *
 * 按优先级读取 X-Forwarded-For、X-Real-IP、REMOTE_ADDR。
 *
 * @return string IP 地址
 */
function get_real_ip(): string {
    $ip = '';
    if (!empty($_SERVER['HTTP_X_FORWARDED_FOR'])) {
        $ips = explode(',', $_SERVER['HTTP_X_FORWARDED_FOR']);
        $ip  = trim($ips[0]);
    } elseif (!empty($_SERVER['HTTP_X_REAL_IP'])) {
        $ip = $_SERVER['HTTP_X_REAL_IP'];
    } elseif (!empty($_SERVER['REMOTE_ADDR'])) {
        $ip = $_SERVER['REMOTE_ADDR'];
    }
    return $ip ?: '127.0.0.1';
}

/**
 * 获取 Meilisearch 索引统计信息
 *
 * @param string $host Meilisearch 主机地址
 * @param string $port Meilisearch 端口
 * @param string $index 索引名称
 * @param string $api_key API 密钥
 * @return array 统计信息数组，至少包含 numberOfDocuments
 */
function get_index_stats(string $host, string $port, string $index, string $api_key): array {
    $stats_url = "http://{$host}:{$port}/indexes/{$index}/stats";
    $ch = curl_init($stats_url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    if ($api_key) {
        curl_setopt($ch, CURLOPT_HTTPHEADER, ["Authorization: Bearer {$api_key}"]);
    }
    curl_setopt($ch, CURLOPT_TIMEOUT, 5);
    $stats_json = curl_exec($ch);
    $http_code  = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);

    if ($http_code === 200 && $stats_json) {
        $stats = json_decode($stats_json, true);
        if (is_array($stats)) {
            return $stats;
        }
    }

    return ['numberOfDocuments' => 0];
}

/**
 * 检查并更新速率限制
 *
 * 基于 IP 地址，每分钟最多 20 次搜索请求。
 *
 * @param string $ip 客户端 IP 地址
 * @return string 错误信息，空字符串表示未超限
 */
function check_rate_limit(string $ip): string {
    $rate_limit_file = sys_get_temp_dir() . '/search_rate_' . md5($ip);
    $now = time();

    // 使用文件锁保护读写操作，防止并发竞态条件
    $fp = @fopen($rate_limit_file, 'c+');
    if (!$fp) {
        // 无法打开文件时允许请求（fail open）
        return '';
    }

    if (!flock($fp, LOCK_EX)) {
        fclose($fp);
        return '';
    }

    $content = '';
    $size = filesize($rate_limit_file);
    if ($size !== false && $size > 0) {
        $content = fread($fp, $size);
    }

    $error = '';
    $rate_data = json_decode($content, true);

    if ($rate_data && ($now - $rate_data['time']) < 60) {
        if ($rate_data['count'] >= 20) {
            $error = '搜索次数超限，请稍后再试';
        } else {
            $rate_data['count']++;
            ftruncate($fp, 0);
            rewind($fp);
            fwrite($fp, json_encode($rate_data));
        }
    } else {
        ftruncate($fp, 0);
        rewind($fp);
        fwrite($fp, json_encode(['time' => $now, 'count' => 1]));
    }

    flock($fp, LOCK_UN);
    fclose($fp);

    return $error;
}

/**
 * 构建 Meilisearch 过滤条件
 *
 * 对标签进行白名单校验，对站点进行域名格式校验。
 *
 * @param array $selected_tags 用户选中的标签
 * @param string $selected_site 用户选中的站点域名
 * @param array $available_tags 系统允许的标签白名单
 * @return string 过滤条件字符串，空字符串表示无过滤
 */
function build_filter(array $selected_tags, string $selected_site, array $available_tags): string {
    $filters = [];

    if (!empty($selected_tags)) {
        foreach ($selected_tags as $tag) {
            if (in_array($tag, $available_tags, true)) {
                $filters[] = "tags = '{$tag}'";
            }
        }
    }

    if (!empty($selected_site) && preg_match('/^[a-zA-Z0-9][a-zA-Z0-9.-]{1,253}[a-zA-Z0-9]$/', $selected_site)) {
        $site_filter = "domain = '{$selected_site}'";
        if (!empty($filters)) {
            return '(' . implode(' OR ', $filters) . ') AND ' . $site_filter;
        }
        return $site_filter;
    }

    if (!empty($filters)) {
        return implode(' OR ', $filters);
    }

    return '';
}

/**
 * 执行 Meilisearch 搜索请求
 *
 * @param string $query 搜索关键词
 * @param int $page 页码（从 1 开始）
 * @param int $limit 每页结果数
 * @param array $selected_tags 选中的标签
 * @param string $selected_site 选中的站点
 * @param string $selected_lang 选中的语言
 * @param array $available_tags 可用标签白名单
 * @param string $host Meilisearch 主机
 * @param string $port Meilisearch 端口
 * @param string $index 索引名称
 * @param string $api_key API 密钥
 * @return array 四元组：[results, total_hits, search_time, error]
 */
function search_meilisearch(
    string $query,
    int $page,
    int $limit,
    array $selected_tags,
    string $selected_site,
    string $selected_lang,
    array $available_tags,
    string $host,
    string $port,
    string $index,
    string $api_key
): array {
    $offset      = ($page - 1) * $limit;
    $results     = [];
    $total_hits  = 0;
    $search_time = 0;
    $error       = '';

    $rate_error = check_rate_limit(get_real_ip());
    if ($rate_error) {
        return [$results, $total_hits, $search_time, $rate_error];
    }

    $url = "http://{$host}:{$port}/indexes/{$index}/search";

    $search_params = [
        'q'                     => $query,
        'limit'                 => $limit,
        'offset'                => $offset,
        'attributesToRetrieve'  => ['*'],
        'attributesToHighlight' => ['title', 'content'],
        'highlightPreTag'       => '<em>',
        'highlightPostTag'      => '</em>',
        'attributesToCrop'      => ['content'],
        'cropLength'            => 200,
    ];

    $filter = build_filter($selected_tags, $selected_site, $available_tags);
    if ($filter) {
        $search_params['filter'] = $filter;
    }

    $post_data = json_encode($search_params);

    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, $post_data);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    $headers = ['Content-Type: application/json'];
    if ($api_key) {
        $headers[] = "Authorization: Bearer {$api_key}";
    }
    curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
    curl_setopt($ch, CURLOPT_TIMEOUT, 10);

    $response   = curl_exec($ch);
    $http_code  = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);

    if ($http_code === 200) {
        $data = json_decode($response, true);
        $results     = $data['hits'] ?? [];
        $total_hits  = $data['estimatedTotalHits'] ?? 0;
        $search_time = $data['processingTimeMs'] ?? 0;

        // 前端语言过滤（Meilisearch 不直接支持语言过滤）
        if (!empty($selected_lang)) {
            $filtered_results = [];
            foreach ($results as $r) {
                $item_url = $r['url'] ?? '';
                if (languageMatches($item_url, $selected_lang)) {
                    $filtered_results[] = $r;
                }
            }
            $results    = $filtered_results;
            $total_hits = count($results);
        }
    } else {
        $error = "搜索服务暂时不可用 (HTTP {$http_code})";
    }

    return [$results, $total_hits, $search_time, $error];
}
