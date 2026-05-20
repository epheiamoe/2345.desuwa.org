<?php

/**
 * 配置加载器
 *
 * 支持加载 .env 文件和共享 config.json 配置。
 *
 * @package TransSearch
 * @license MIT
 */

declare(strict_types=1);

if (!defined('TRANS_SEARCH')) {
    define('TRANS_SEARCH', true);
}

class AppConfig {
    private static ?array $shared = null;
    private static ?array $env = null;

    public static function init(): void {
        if (self::$shared !== null) {
            return;
        }

        self::$env = self::loadEnv(__DIR__ . '/../.env');

        $configPath = __DIR__ . '/../config.json';
        if (!file_exists($configPath)) {
            throw new RuntimeException("config.json not found at $configPath");
        }

        $content = file_get_contents($configPath);
        if ($content === false) {
            throw new RuntimeException("Unable to read config.json");
        }

        self::$shared = json_decode($content, true);
        if (json_last_error() !== JSON_ERROR_NONE) {
            throw new RuntimeException("Invalid JSON in config.json: " . json_last_error_msg());
        }
    }

    private static function loadEnv(string $path): array {
        $env = [];
        if (!file_exists($path)) {
            return $env;
        }

        $lines = file($path, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
        if ($lines === false) {
            return $env;
        }

        foreach ($lines as $line) {
            $line = trim($line);
            if ($line === '' || substr($line, 0, 1) === '#') {
                continue;
            }

            if (strpos($line, '=') !== false) {
                [$key, $value] = explode('=', $line, 2);
                $env[trim($key)] = trim($value, " \t\n\r\0\x0B\"'");
            }
        }

        return $env;
    }

    /**
     * @param mixed $default
     * @return mixed
     */
    public static function get(string $keyPath, $default = null) {
        self::init();

        $keys = explode('.', $keyPath);
        $value = self::$shared;

        foreach ($keys as $key) {
            if (is_array($value) && array_key_exists($key, $value)) {
                $value = $value[$key];
            } else {
                return $default;
            }
        }

        return $value ?? $default;
    }

    /**
     * @param mixed $default
     * @return mixed
     */
    public static function env(string $key, $default = null) {
        self::init();
        return self::$env[$key] ?? getenv($key) ?: $default;
    }

    public static function getTags(): array {
        return self::get('tags.available', []);
    }

    public static function getLanguages(): array {
        return self::get('languages.supported', []);
    }

    public static function getMeilisearchUrl(): string {
        $host = self::env('MEILISEARCH_HOST', 'localhost');
        $port = self::env('MEILISEARCH_PORT', '7700');
        $useSsl = self::get('meilisearch.use_ssl', false);
        $protocol = $useSsl ? 'https' : 'http';
        return "$protocol://$host:$port";
    }

    /**
     * 判断 API 功能是否启用
     *
     * 优先读取 .env 的 ENABLE_API，其次读取 config.json 的 deploy.features.api。
     * 如果两者都不存在，默认返回 true 以保持向后兼容（现有部署不受影响）。
     */
    public static function isApiEnabled(): bool {
        $envValue = self::env('ENABLE_API', '');
        if ($envValue !== '') {
            return strtolower($envValue) === 'true' || $envValue === '1';
        }

        $configValue = self::get('deploy.features.api');
        if ($configValue !== null) {
            return (bool) $configValue;
        }

        // 向后兼容：未配置时默认启用 API
        return true;
    }

    /**
     * 判断 OAuth 功能是否启用
     *
     * 优先读取 .env 的 ENABLE_OAUTH，其次读取 config.json 的 deploy.features.oauth。
     * 如果两者都不存在，默认返回 true 以保持向后兼容。
     */
    public static function isOAuthEnabled(): bool {
        $envValue = self::env('ENABLE_OAUTH', '');
        if ($envValue !== '') {
            return strtolower($envValue) === 'true' || $envValue === '1';
        }

        $configValue = self::get('deploy.features.oauth');
        if ($configValue !== null) {
            return (bool) $configValue;
        }

        // 向后兼容：未配置时默认启用 OAuth
        return true;
    }
}

AppConfig::init();
