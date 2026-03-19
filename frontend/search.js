// 暗黑模式切换（不依赖 JS 也能正常浏览，只是无法切换主题）
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

function toggleSearchTips() {
    var dropdown = document.getElementById('searchTipsDropdown');
    var btn = document.getElementById('tipsBtn');
    if (dropdown.style.display === 'none') {
        dropdown.style.display = 'block';
        dropdown.style.animation = 'dropdownFadeIn 0.2s ease';
        btn.textContent = '▲ 搜索技巧';
    } else {
        dropdown.style.display = 'none';
        btn.textContent = '▼ 搜索技巧';
    }
}

function toggleMoreTags() {
    var moreTags = document.querySelectorAll('.tag-more');
    var btn = document.getElementById('moreTagsBtn');
    var isHidden = moreTags[0] && moreTags[0].style.display === 'none';
    moreTags.forEach(function(el) {
        el.style.display = isHidden ? 'inline' : 'none';
    });
    btn.textContent = isHidden ? '收起' : '更多';
}

// 点击其他地方关闭下拉框
document.addEventListener('click', function(e) {
    var dropdown = document.getElementById('searchTipsDropdown');
    var btn = document.getElementById('tipsBtn');
    if (dropdown && btn && !btn.contains(e.target) && !dropdown.contains(e.target)) {
        dropdown.style.display = 'none';
        btn.textContent = '▼ 搜索技巧';
    }
});

document.addEventListener('DOMContentLoaded', function() {
    initTheme();
    
    // 显示PWA安装提示（仅JS可用时）
    var pwaHint = document.getElementById('pwa-hint');
    if (pwaHint && 'serviceWorker' in navigator) {
        pwaHint.style.display = 'block';
    }
});

// PWA 安装
let deferredPrompt = null;

window.addEventListener('beforeinstallprompt', function(e) {
    e.preventDefault();
    deferredPrompt = e;
});

function installPWA() {
    if (deferredPrompt) {
        deferredPrompt.prompt();
        deferredPrompt.userChoice.then(function(choiceResult) {
            if (choiceResult.outcome === 'accepted') {
                console.log('User accepted the PWA install');
            }
            deferredPrompt = null;
            var btn = document.getElementById('pwa-install-btn');
            if (btn) {
                btn.textContent = '已安装';
                btn.disabled = true;
            }
        });
    }
}
