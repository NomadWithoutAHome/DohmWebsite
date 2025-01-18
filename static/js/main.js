// Check if we've already shown the intro animation this session
if (!sessionStorage.getItem('introShown')) {
    // Show intro screen
    const introScreen = document.querySelector('.main-intro-screen');
    if (introScreen) {
        introScreen.style.display = 'flex';
        setTimeout(() => {
            introScreen.style.opacity = '0';
            setTimeout(() => {
                introScreen.style.display = 'none';
                // Mark that we've shown the animation
                sessionStorage.setItem('introShown', 'true');
            }, 1000);
        }, 2000);
    }
} else {
    // Hide intro screen immediately if we've already shown it
    const introScreen = document.querySelector('.main-intro-screen');
    if (introScreen) {
        introScreen.style.display = 'none';
    }
}

// ... rest of your existing code ... 