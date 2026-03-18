// 检测用户浏览器语言并自动选择（仅在用户未明确选择语言时）
function detectUserLanguage() {
    var urlParams = new URLSearchParams(window.location.search);
    
    // 如果已有语言参数，说明用户已明确选择，不进行自动检测
    if (urlParams.get('lang')) return;
    
    // 检查 localStorage 是否已有用户手动选择的语言
    var savedLang = localStorage.getItem('user_language');
    if (savedLang) return;  // 用户之前已选择，不覆盖
    
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
    
    // 构建新 URL（不添加其他参数，避免搜索词等丢失）
    window.location.search = 'lang=' + lang;
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
