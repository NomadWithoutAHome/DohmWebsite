// Handle form submission for downloading
document.getElementById('extension-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const errorMessage = document.getElementById('error-message');
    errorMessage.style.display = 'none';
    
    try {
        const extensionUrl = document.getElementById('extension-url').value;
        const format = document.querySelector('input[name="format"]:checked').value;
        
        // Extract extension ID from URL or use as is
        const extensionId = extractExtensionId(extensionUrl);
        if (!extensionId) {
            throw new Error('Invalid extension URL or ID');
        }
        
        // Create temporary link to trigger download
        const response = await fetch(`/download-extension?id=${extensionId}&format=${format}`);
        if (!response.ok) {
            const error = await response.text();
            throw new Error(error || 'Failed to download extension');
        }
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${extensionId}.${format}`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        a.remove();
    } catch (error) {
        console.error('Download error:', error);
        errorMessage.textContent = error.message;
        errorMessage.style.display = 'block';
    }
});

// Handle view source button click
document.getElementById('view-button').addEventListener('click', async () => {
    const errorMessage = document.getElementById('error-message');
    errorMessage.style.display = 'none';
    
    try {
        const extensionUrl = document.getElementById('extension-url').value;
        const extensionId = extractExtensionId(extensionUrl);
        if (!extensionId) {
            throw new Error('Invalid extension URL or ID');
        }
        
        const response = await fetch('/view-extension', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ id: extensionId })
        });
        
        if (!response.ok) {
            const error = await response.text();
            throw new Error(error || 'Failed to load extension source');
        }
        
        const data = await response.json();
        updateFileList(data.files);
        showModal();
    } catch (error) {
        console.error('View error:', error);
        errorMessage.textContent = error.message;
        errorMessage.style.display = 'block';
    }
});

// Extract extension ID from URL or return as is if it's just an ID
function extractExtensionId(input) {
    input = input.trim();
    if (!input) return null;
    
    // If it's a URL, extract the ID
    const match = input.match(/(?:\/detail\/|^)([a-z]{32})/i);
    return match ? match[1] : input;
}

// Modal handling
function showModal() {
    const modal = document.getElementById('source-modal');
    modal.classList.remove('hidden');
    modal.classList.add('flex');
}

function closeModal() {
    const modal = document.getElementById('source-modal');
    modal.classList.add('hidden');
    modal.classList.remove('flex');
}

// Handle file viewing
async function viewFile(filename) {
    const errorMessage = document.getElementById('error-message');
    const fileContent = document.getElementById('file-content');
    const binaryNotice = document.getElementById('binary-notice');
    const loadMore = document.getElementById('load-more');
    const code = fileContent.querySelector('code');
    
    try {
        const extensionUrl = document.getElementById('extension-url').value;
        const extensionId = extractExtensionId(extensionUrl);
        
        const response = await fetch('/view-extension', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                id: extensionId,
                filename: filename,
                offset: 0
            })
        });
        
        if (!response.ok) {
            throw new Error('Failed to load file content');
        }
        
        const data = await response.json();
        
        // Handle binary files
        if (data.is_binary) {
            fileContent.style.display = 'none';
            binaryNotice.style.display = 'block';
            loadMore.style.display = 'none';
            return;
        }
        
        // Handle text files
        fileContent.style.display = 'block';
        binaryNotice.style.display = 'none';
        
        // Set content and highlight
        code.className = `language-${data.language || 'plaintext'}`;
        code.textContent = data.content;
        Prism.highlightElement(code);
        
        // Show/hide load more button
        loadMore.style.display = data.has_more ? 'block' : 'none';
        loadMore.dataset.offset = data.next_offset;
        loadMore.dataset.filename = filename;
    } catch (error) {
        console.error('File view error:', error);
        errorMessage.textContent = error.message;
        errorMessage.style.display = 'block';
    }
}

// Handle loading more content
async function loadMoreContent() {
    const loadMore = document.getElementById('load-more');
    const filename = loadMore.dataset.filename;
    const offset = parseInt(loadMore.dataset.offset);
    
    try {
        const extensionUrl = document.getElementById('extension-url').value;
        const extensionId = extractExtensionId(extensionUrl);
        
        const response = await fetch('/view-extension', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                id: extensionId,
                filename: filename,
                offset: offset
            })
        });
        
        if (!response.ok) {
            throw new Error('Failed to load more content');
        }
        
        const data = await response.json();
        const code = document.querySelector('#file-content code');
        
        // Append new content
        code.textContent += data.content;
        Prism.highlightElement(code);
        
        // Update load more button
        loadMore.style.display = data.has_more ? 'block' : 'none';
        loadMore.dataset.offset = data.next_offset;
    } catch (error) {
        console.error('Load more error:', error);
        const errorMessage = document.getElementById('error-message');
        errorMessage.textContent = error.message;
        errorMessage.style.display = 'block';
    }
}

function showError(message) {
    const errorElement = document.querySelector('.error-message');
    // Format error message in a console-like way
    const timestamp = new Date().toISOString();
    const formattedError = `[${timestamp}]
Status: ERROR
------------------
${message}
------------------
Press any key to continue...`;
    
    errorElement.textContent = formattedError;
    errorElement.style.display = 'block';
    
    // Hide error on any keypress
    const hideError = (e) => {
        errorElement.style.display = 'none';
        document.removeEventListener('keydown', hideError);
    };
    document.addEventListener('keydown', hideError);
} 