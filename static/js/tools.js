// Handle form submission for downloading
document.getElementById('extension-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const extensionUrl = document.getElementById('extension-url').value.trim();
    if (!extensionUrl) {
        showError('Please enter a Chrome Web Store URL or Extension ID');
        return;
    }
    
    try {
        const format = document.querySelector('input[name="format"]:checked').value;
        
        // Extract extension ID from URL or use as is
        const extensionId = extractExtensionId(extensionUrl);
        if (!extensionId) {
            showError('Invalid extension URL or ID');
            return;
        }
        
        // Send POST request with JSON data
        const response = await fetch('/download-extension', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                extension_id: extensionId,
                format: format
            })
        });
        
        if (!response.ok) {
            const error = await response.text();
            showError(error || 'Failed to download extension');
            return;
        }
        
        // Get the filename from the Content-Disposition header if available
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = `${extensionId}.${format}`;
        if (contentDisposition) {
            const filenameMatch = contentDisposition.match(/filename="(.+)"/);
            if (filenameMatch) {
                filename = filenameMatch[1];
            }
        }
        
        // Create a blob from the response and trigger download
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
    } catch (error) {
        console.error('Download error:', error);
        showError(error.message || 'Failed to download extension');
    }
});

// Extract extension ID from URL or return as is if it's just an ID
function extractExtensionId(input) {
    input = input.trim();
    if (!input) return null;
    
    // If it's a URL, try to extract the ID
    const urlMatch = input.match(/chrome(?:webstore)?\.google\.com\/(?:webstore\/)?detail\/[^\/]+\/([a-z0-9]{32})/i);
    if (urlMatch) {
        return urlMatch[1];
    }
    
    // If it's not a URL, check if it's a valid 32-character ID
    if (/^[a-z0-9]{32}$/i.test(input)) {
        return input.toLowerCase();
    }
    
    return null;
}

// Error handling
function showError(message) {
    const errorConsole = document.querySelector('.error-console');
    const errorOverlay = document.querySelector('.error-console-overlay');
    
    errorConsole.textContent = message;
    errorConsole.style.display = 'block';
    errorOverlay.style.display = 'block';
    
    setTimeout(() => {
        errorConsole.style.display = 'none';
        errorOverlay.style.display = 'none';
    }, 5000);
}

// Also update the input field to remove the required attribute
document.addEventListener('DOMContentLoaded', () => {
    const input = document.getElementById('extension-url');
    input.removeAttribute('required');
}); 