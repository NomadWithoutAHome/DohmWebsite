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

// Show loading message only on index page and first visit
document.addEventListener('DOMContentLoaded', () => {
    // Check if we're on the index page
    const isIndexPage = window.location.pathname === '/' || window.location.pathname === '/index';
    
    // Check if this is the first visit this session
    const hasVisited = sessionStorage.getItem('hasVisited');
    
    if (isIndexPage && !hasVisited) {
        showRetroLoadingMessage();
        // Mark that we've shown the loading screen
        sessionStorage.setItem('hasVisited', 'true');
    }
}); 