function showRetroLoadingMessage() {
    const messages = [
        'LOADING RETRO INTERFACE...',
        'INITIALIZING TIME CIRCUITS...',
        'CONNECTING TO 56K MODEM...',
        'INSERTING COIN...',
        'PRESS START TO CONTINUE...',
        'BUFFERING AT 88%...',
        'REWINDING TAPE...',
        'LOADING NEXT LEVEL...',
        'SAVING GAME STATE...',
        'ENTERING THE GRID...'
    ];
    
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'retro-loading';
    loadingDiv.innerHTML = `
        <div class="loading-content">
            <div class="loading-text">${messages[Math.floor(Math.random() * messages.length)]}</div>
            <div class="loading-bar">
                <div class="loading-progress"></div>
            </div>
        </div>
    `;
    
    document.body.appendChild(loadingDiv);
    
    // Animate progress bar
    const progressBar = loadingDiv.querySelector('.loading-progress');
    progressBar.style.width = '0%';
    setTimeout(() => {
        progressBar.style.width = '100%';
    }, 100);
    
    // Remove after animation
    setTimeout(() => {
        loadingDiv.classList.add('fade-out');
        setTimeout(() => {
            if (document.body.contains(loadingDiv)) {
                document.body.removeChild(loadingDiv);
            }
        }, 500);
    }, 2000);
}

// Show loading message on navigation
document.addEventListener('DOMContentLoaded', () => {
    // For regular link clicks
    document.addEventListener('click', (e) => {
        const link = e.target.closest('a');
        if (link && !link.target && link.href && !link.href.startsWith('#')) {
            showRetroLoadingMessage();
        }
    });
    
    // For form submissions
    document.addEventListener('submit', (e) => {
        const form = e.target;
        if (form.method.toLowerCase() !== 'post' || !form.hasAttribute('data-no-loading')) {
            showRetroLoadingMessage();
        }
    });
    
    // For initial page load
    if (performance.navigation.type === performance.navigation.TYPE_RELOAD) {
        showRetroLoadingMessage();
    }
}); 