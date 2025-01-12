let currentChunk = {
    start: 0,
    size: 500,
    total: 0
};

async function viewFile(filename) {
    const sourceCode = document.getElementById('source-code');
    const loadingIndicator = document.getElementById('loading-indicator');
    const loadMore = document.getElementById('load-more');
    
    try {
        // Reset chunk tracking
        currentChunk.start = 0;
        
        // Show loading state
        loadingIndicator.classList.remove('hidden');
        sourceCode.classList.add('hidden');
        loadMore.classList.add('hidden');
        
        const response = await fetch('/view-extension', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                extension_id: document.getElementById('extension-id').value.trim(),
                filename: filename,
                chunk_start: currentChunk.start,
                chunk_size: currentChunk.size
            })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to load file');
        }
        
        // Update code display
        const code = sourceCode.querySelector('code');
        code.className = `language-${getLanguageFromMime(data.mime_type)}`;
        
        if (data.is_binary) {
            if (data.is_image) {
                code.innerHTML = `<img src="${data.content}" alt="${filename}">`;
            } else if (data.is_audio) {
                const style = document.createElement('style');
                style.textContent = data.custom_style;
                document.head.appendChild(style);
                code.innerHTML = `
                    <audio controls>
                        <source src="${data.content}" type="${data.mime_type}">
                        Your browser does not support the audio element.
                    </audio>
                `;
            } else {
                code.innerHTML = `<div class="binary-notice">Binary file: ${filename}</div>`;
            }
        } else {
            // Format code if needed
            let content = data.content;
            if (data.mime_type === 'application/json') {
                try {
                    content = JSON.stringify(JSON.parse(content), null, 2);
                } catch {}
            } else if (data.mime_type === 'text/html') {
                content = html_beautify(content);
            } else if (data.mime_type === 'text/css') {
                content = css_beautify(content);
            } else if (data.mime_type === 'application/javascript') {
                content = js_beautify(content);
            }
            
            code.textContent = content;
            Prism.highlightElement(code);
            
            // Update chunk tracking
            currentChunk.total = data.total_lines;
            loadMore.classList.toggle('hidden', 
                currentChunk.start + currentChunk.size >= currentChunk.total);
        }
        
        // Show content
        loadingIndicator.classList.add('hidden');
        sourceCode.classList.remove('hidden');
        
    } catch (error) {
        loadingIndicator.classList.add('hidden');
        sourceCode.classList.remove('hidden');
        sourceCode.querySelector('code').innerHTML = `
            <div class="error-message">${error.message}</div>
        `;
    }
}

async function loadMoreContent(filename) {
    const sourceCode = document.getElementById('source-code');
    const loadMore = document.getElementById('load-more');
    const code = sourceCode.querySelector('code');
    
    try {
        currentChunk.start += currentChunk.size;
        
        const response = await fetch('/view-extension', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                extension_id: document.getElementById('extension-id').value.trim(),
                filename: filename,
                chunk_start: currentChunk.start,
                chunk_size: currentChunk.size
            })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to load more content');
        }
        
        // Append new content
        code.textContent += '\n' + data.content;
        Prism.highlightElement(code);
        
        // Update load more button visibility
        loadMore.classList.toggle('hidden', 
            currentChunk.start + currentChunk.size >= currentChunk.total);
        
    } catch (error) {
        code.innerHTML += `
            <div class="error-message">${error.message}</div>
        `;
    }
}

function getLanguageFromMime(mimeType) {
    const mimeMap = {
        'application/javascript': 'javascript',
        'text/css': 'css',
        'text/html': 'html',
        'application/json': 'json',
        'text/xml': 'xml'
    };
    return mimeMap[mimeType] || 'plaintext';
} 