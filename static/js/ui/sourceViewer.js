async function view_file_info(file) {
    const codeContainer = document.getElementById('code-container');
    const loadingIndicator = document.getElementById('loading-indicator');
    const sourceCode = document.getElementById('source-code');
    const loadMore = document.getElementById('load-more');
    
    loadingIndicator.classList.remove('hidden');
    sourceCode.classList.add('hidden');
    loadMore.classList.add('hidden');
    
    try {
        const response = await fetch('/view-extension', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                extension_id: currentExtensionId,
                filename: file.name,
                chunk_start: 0,
                chunk_size: 500
            })
        });
        
        const data = await response.json();
        if (data.error) {
            throw new Error(data.error);
        }
        
        if (data.is_binary) {
            handle_binary_file(data, sourceCode);
        } else {
            handle_text_file(data, sourceCode, loadMore);
        }
    } catch (error) {
        sourceCode.innerHTML = `<div class="error-message">Error loading file: ${error.message}</div>`;
        sourceCode.classList.remove('hidden');
    } finally {
        loadingIndicator.classList.add('hidden');
    }
}

function handle_binary_file(data, sourceCode) {
    if (data.is_image) {
        sourceCode.innerHTML = `<img ${data.content} class="max-w-full h-auto">`;
    } else if (data.is_audio) {
        sourceCode.innerHTML = `
            <audio controls class="w-full">
                <source src="${data.content}" type="${data.mime_type}">
                Your browser does not support the audio element.
            </audio>
            <style>${data.custom_style || ''}</style>
        `;
    } else {
        sourceCode.innerHTML = '<div class="error-message">Binary file cannot be displayed</div>';
    }
    sourceCode.classList.remove('hidden');
}

function handle_text_file(data, sourceCode, loadMore) {
    const code = document.createElement('code');
    code.textContent = data.content;
    code.className = `language-${get_language_class(data.mime_type)}`;
    
    sourceCode.textContent = '';
    sourceCode.appendChild(code);
    
    Prism.highlightElement(code);
    sourceCode.classList.remove('hidden');
    
    if (data.current_chunk.end < data.total_lines) {
        loadMore.classList.remove('hidden');
        loadMore.querySelector('button').onclick = () => load_more_content(data.current_chunk);
    }
}

function get_language_class(mime_type) {
    const map = {
        'application/javascript': 'javascript',
        'text/css': 'css',
        'text/html': 'html',
        'application/json': 'json',
        'text/xml': 'xml'
    };
    return map[mime_type] || 'plaintext';
}

async function load_more_content(currentChunk) {
    const nextChunk = {
        start: currentChunk.end,
        size: currentChunk.size
    };
    
    const sourceCode = document.getElementById('source-code');
    const loadMore = document.getElementById('load-more');
    loadMore.classList.add('hidden');
    
    try {
        const response = await fetch('/view-extension', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                extension_id: currentExtensionId,
                filename: document.querySelector('.file-selected').dataset.filename,
                chunk_start: nextChunk.start,
                chunk_size: nextChunk.size
            })
        });
        
        const data = await response.json();
        if (data.error) {
            throw new Error(data.error);
        }
        
        const code = document.createElement('code');
        code.textContent = data.content;
        code.className = sourceCode.querySelector('code').className;
        
        sourceCode.appendChild(document.createElement('br'));
        sourceCode.appendChild(code);
        
        Prism.highlightElement(code);
        
        if (data.current_chunk.end < data.total_lines) {
            loadMore.classList.remove('hidden');
            loadMore.querySelector('button').onclick = () => load_more_content(data.current_chunk);
        }
    } catch (error) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.textContent = `Error loading more content: ${error.message}`;
        sourceCode.appendChild(errorDiv);
    }
} 