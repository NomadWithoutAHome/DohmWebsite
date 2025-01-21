document.addEventListener('DOMContentLoaded', () => {
    const buttons = document.querySelectorAll('.retro-button');
    buttons.forEach(button => {
        button.addEventListener('mouseover', () => {
            // Removed hover sound
        });
    });
}); 