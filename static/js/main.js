console.log('main.js loaded');  // Add this at the very top

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

// Track outbound clicks
function initializeOutboundTracking() {
    console.log('Initializing outbound tracking...');  // Debug log
    
    // Track all links in the code dropdown specifically
    const links = document.querySelectorAll('#code-dropdown a');
    console.log('Found links:', links.length);  // Debug log
    
    links.forEach(link => {
        // Remove any existing click listeners first
        link.removeEventListener('click', handleOutboundClick);
        link.addEventListener('click', handleOutboundClick);
    });
}

// Separate the click handler function
async function handleOutboundClick(e) {
    const link = e.currentTarget;
    console.log('Link clicked:', link.href);  // Debug log
    
    // Don't track if it's internal or the "More Projects" link
    if (link.href.includes('dohmboy64.com') || link.href === '#') {
        console.log('Skipping internal link');  // Debug log
        return;
    }
    
    // Prevent default to ensure tracking completes
    e.preventDefault();
    
    // Get the project name from the link text
    const projectName = link.textContent.trim();
    console.log('Project name:', projectName);  // Debug log
    
    // Send tracking data
    try {
        const response = await fetch('/track/outbound', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                destination: link.href,
                type: `GitHub Project - ${projectName}`
            })
        });
        
        console.log('Tracking response:', await response.json());  // Debug log
        
        // After tracking is complete, navigate to the link
        window.location.href = link.href;
    } catch (err) {
        console.error('Error tracking outbound click:', err);
        // If tracking fails, still navigate to the link
        window.location.href = link.href;
    }
}

// Initialize tracking when the document is ready
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM Content Loaded');  // Debug log
    initializeOutboundTracking();
    
    // Also watch for dropdown toggle clicks
    const dropdownToggle = document.querySelector('[data-dropdown="code"]');
    if (dropdownToggle) {
        dropdownToggle.addEventListener('click', () => {
            console.log('Dropdown toggled');  // Debug log
            // Small delay to ensure dropdown content is rendered
            setTimeout(initializeOutboundTracking, 100);
        });
    }
});

// Also initialize tracking when the dropdown is shown
const codeDropdown = document.getElementById('code-dropdown');
if (codeDropdown) {
    console.log('Found code dropdown');  // Debug log
    const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            if (mutation.target.classList.contains('show')) {
                console.log('Dropdown shown');  // Debug log
                initializeOutboundTracking();
            }
        });
    });

    observer.observe(codeDropdown, {
        attributes: true,
        attributeFilter: ['class']
    });
}

// ... rest of your existing code ... 