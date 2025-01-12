document.addEventListener('DOMContentLoaded', () => {
    const buttons = document.querySelectorAll('.retro-button');
    buttons.forEach(button => {
        button.addEventListener('mouseover', () => {
            const audio = new Audio('/static/assets/hover.wav');
            audio.volume = 0.2;
            audio.play();
        });
    });
}); 