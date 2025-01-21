class RetroTypewriter {
    constructor(element, options = {}) {
        this.element = element;
        this.text = element.textContent.trim();
        this.options = {
            typingSpeed: options.typingSpeed || 100,
            cursorSpeed: options.cursorSpeed || 500,
            cursorChar: options.cursorChar || '█',
            startDelay: options.startDelay || 500
        };
        
        // Clear the element
        this.element.textContent = '';
        this.element.classList.add('typewriter');
        
        // Create cursor element
        this.cursor = document.createElement('span');
        this.cursor.className = 'typewriter-cursor';
        this.cursor.textContent = this.options.cursorChar;
        this.element.appendChild(this.cursor);
        
        // Start cursor blinking
        setInterval(() => {
            this.cursor.style.opacity = this.cursor.style.opacity === '0' ? '1' : '0';
        }, this.options.cursorSpeed);
    }
    
    async typeText() {
        // Wait for start delay
        await new Promise(resolve => setTimeout(resolve, this.options.startDelay));
        
        // Type each character
        for (let char of this.text) {
            // Add random delay variation for more realistic effect
            const delay = this.options.typingSpeed + (Math.random() * 100 - 50);
            await new Promise(resolve => setTimeout(resolve, delay));
            
            // Create text node
            const textNode = document.createTextNode(char);
            this.element.insertBefore(textNode, this.cursor);
        }
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    const titleElement = document.querySelector('.typewriter-title');
    if (titleElement) {
        const typewriter = new RetroTypewriter(titleElement, {
            typingSpeed: 150,
            cursorSpeed: 500,
            startDelay: 1000
        });
        typewriter.typeText();
    }
}); 