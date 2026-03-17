// 检测用户浏览器语言并自动选择
function detectUserLanguage() {
    var urlParams = new URLSearchParams(window.location.search);
    
    // 如果已有语言参数，不处理
    if (urlParams.get('lang')) return;
    
    var userLang = (navigator.language || navigator.userLanguage || '').toLowerCase();
    var lang = 'zh';
    
    // 检测中文简繁体
    if (userLang.startsWith('zh-hant') || userLang.startsWith('zh-tw') || userLang.startsWith('zh-hk')) {
        lang = 'zh-hant';
    } else if (userLang.startsWith('zh-cn') || userLang.startsWith('zh')) {
        lang = 'zh-cn';
    } else if (userLang.startsWith('en')) {
        lang = 'en';
    } else if (userLang.startsWith('ja')) {
        lang = 'ja';
    } else if (userLang.startsWith('es')) {
        lang = 'es';
    } else if (userLang.startsWith('nl')) {
        lang = 'nl';
    }
    
    // 构建新 URL
    var baseUrl = window.location.pathname;
    var query = urlParams.get('q') || '';
    var newUrl = baseUrl + '?lang=' + lang;
    if (query) {
        newUrl += '&q=' + encodeURIComponent(query);
    }
    
    window.location.href = newUrl;
}

// 暗黑模式
function initTheme() {
    var theme = localStorage.getItem('theme');
    var isDark = false;
    
    if (theme === 'dark') {
        isDark = true;
    } else if (theme === 'light') {
        isDark = false;
    } else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
        isDark = true;
    }
    
    if (isDark) {
        document.body.classList.add('dark');
    }
    
    updateThemeIcon(isDark);
}

function updateThemeIcon(isDark) {
    var themeBtn = document.getElementById('theme-toggle');
    if (themeBtn) {
        themeBtn.textContent = isDark ? '☀️' : '🌙';
    }
}

function toggleTheme() {
    var isDark = document.body.classList.toggle('dark');
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
    updateThemeIcon(isDark);
}

document.addEventListener('DOMContentLoaded', function() {
    initTheme();
    detectUserLanguage();
});
