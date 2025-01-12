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
        showError(error.message || 'Failed to download extension');
    }
});

// Also update the input field to remove the required attribute
document.addEventListener('DOMContentLoaded', () => {
    const input = document.getElementById('extension-url');
    input.removeAttribute('required');
});

// Handle view source button click
document.getElementById('view-button').addEventListener('click', async () => {
    try {
        const extensionUrl = document.getElementById('extension-url').value;
        const extensionId = extractExtensionId(extensionUrl);
        if (!extensionId) {
            showError('Invalid extension URL or ID');
            return;
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
            showError(error || 'Failed to load extension source');
            return;
        }
        
        const data = await response.json();
        updateFileList(data.files);
        showModal();
    } catch (error) {
        console.error('View error:', error);
        showError(error.message || 'Failed to load extension source');
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
        const ext = filename.split('.').pop().toLowerCase();
        
        // Handle binary files
        if (data.is_binary) {
            fileContent.style.display = 'none';
            binaryNotice.style.display = 'block';
            loadMore.style.display = 'none';
            
            // Handle images
            if (/^(bmp|cur|gif|ico|jpe?g|png|psd|svg|tiff?|xcf|webp)$/.test(ext)) {
                binaryNotice.innerHTML = `<img src="data:${data.mime_type};base64,${data.content}" alt="${filename}" style="max-width: 100%; max-height: 500px;">`;
                return;
            }
            
            // Handle audio
            if (/^(mp3|ogg|wav|m4a)$/.test(ext)) {
                binaryNotice.innerHTML = `
                    <div class="retro-audio">
                        <div class="retro-audio-title">${filename}</div>
                        <audio controls>
                            <source src="data:${data.mime_type};base64,${data.content}" type="${data.mime_type}">
                            Your browser does not support the audio element.
                        </audio>
                    </div>`;
                return;
            }
            
            // Other binary files
            binaryNotice.textContent = `Binary file: ${filename}`;
            return;
        }
        
        // Handle text files
        fileContent.style.display = 'block';
        binaryNotice.style.display = 'none';
        
        // Beautify the code based on file type
        let beautifiedContent = data.content;
        
        // Only beautify if the libraries are loaded
        if (window.js_beautify && window.css_beautify && window.html_beautify) {
            const opts = { indent_size: 2, preserve_newlines: true };
            
            if (['js', 'json', 'jsx', 'ts', 'tsx'].includes(ext)) {
                beautifiedContent = js_beautify(data.content, opts);
            } else if (['css', 'scss', 'less'].includes(ext)) {
                beautifiedContent = css_beautify(data.content, opts);
            } else if (['html', 'htm', 'xml', 'svg'].includes(ext)) {
                beautifiedContent = html_beautify(data.content, opts);
            }
        }
        
        // Set content and highlight
        code.className = `language-${data.language || 'plaintext'}`;
        code.textContent = beautifiedContent;
        Prism.highlightElement(code);
        
        // Show/hide load more button
        loadMore.style.display = data.has_more ? 'block' : 'none';
        loadMore.dataset.offset = data.next_offset;
        loadMore.dataset.filename = filename;
    } catch (error) {
        console.error('File view error:', error);
        showError(error.message || 'Failed to load file content');
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
    const errorConsole = document.querySelector('.error-console') || createErrorConsole();
    const errorOverlay = document.querySelector('.error-console-overlay') || createErrorOverlay();
    
    // Format error message in a console-like way
    const timestamp = new Date().toISOString();
    const formattedError = `ERROR:\\> [${timestamp}]
Status: ERROR
------------------
${message}
------------------
Press ENTER to continue...`;
    
    // Remove the ERROR:\\> prefix since it's added by CSS
    errorConsole.textContent = formattedError;
    const prompt = document.createElement('span');
    prompt.className = 'error-console-prompt';
    prompt.textContent = '_';
    errorConsole.appendChild(prompt);
    
    // Show the console and overlay
    errorOverlay.style.display = 'block';
    errorConsole.style.display = 'block';
    
    // Handle Enter key press
    const hideError = (e) => {
        if (e.key === 'Enter') {
            errorOverlay.style.display = 'none';
            errorConsole.style.display = 'none';
            document.removeEventListener('keydown', hideError);
        }
    };
    document.addEventListener('keydown', hideError);
}

function createErrorConsole() {
    const console = document.createElement('div');
    console.className = 'error-console';
    document.body.appendChild(console);
    return console;
}

function createErrorOverlay() {
    const overlay = document.createElement('div');
    overlay.className = 'error-console-overlay';
    document.body.appendChild(overlay);
    return overlay;
}

function updateFileList(files) {
    const fileList = document.querySelector('.file-list');
    fileList.innerHTML = ''; // Clear existing content
    
    // Group files by type
    const groups = {
        manifest: { title: 'Manifest', files: [] },
        code: { title: 'Code Files', files: [] },
        markup: { title: 'Markup Files', files: [] },
        locales: { title: 'Locales', files: [] },
        images: { title: 'Images', files: [] },
        audio: { title: 'Audio', files: [] },
        font: { title: 'Fonts', files: [] },
        misc: { title: 'Other Files', files: [] }
    };
    
    // Sort files by directory depth and name
    files.sort((a, b) => {
        const depthA = a.name.split('/').length;
        const depthB = b.name.split('/').length;
        if (depthA !== depthB) return depthA - depthB;
        return a.name.localeCompare(b.name);
    });
    
    // Group files
    files.forEach(file => {
        groups[file.type].files.push(file);
    });
    
    // Create group elements
    Object.entries(groups).forEach(([type, group]) => {
        if (group.files.length === 0) return;
        
        const groupDiv = document.createElement('div');
        groupDiv.className = 'file-group';
        
        const header = document.createElement('div');
        header.className = 'group-header';
        header.textContent = `${group.title} (${group.files.length})`;
        groupDiv.appendChild(header);
        
        const filesDiv = document.createElement('div');
        filesDiv.className = 'group-files';
        
        group.files.forEach(file => {
            const fileItem = document.createElement('div');
            fileItem.className = 'file-item';
            fileItem.dataset.type = type;
            fileItem.onclick = () => {
                // Remove selected class from all items
                document.querySelectorAll('.file-item').forEach(item => {
                    item.classList.remove('selected');
                });
                // Add selected class to clicked item
                fileItem.classList.add('selected');
                viewFile(file.name);
            };
            
            const fileInfo = document.createElement('div');
            fileInfo.className = 'file-info';
            
            // Get icon based on file type
            const icon = getFileTypeIcon(type, file.name);
            const fileIcon = document.createElement('span');
            fileIcon.className = 'file-icon';
            fileIcon.textContent = icon;
            fileInfo.appendChild(fileIcon);
            
            const filePath = document.createElement('div');
            filePath.className = 'file-path';
            
            // Split path into directory and filename
            const parts = file.name.split('/');
            const fileName = parts.pop();
            const directory = parts.join('/');
            
            if (directory) {
                const dirSpan = document.createElement('span');
                dirSpan.className = 'file-dir';
                dirSpan.textContent = directory + '/';
                filePath.appendChild(dirSpan);
            }
            
            const nameSpan = document.createElement('span');
            nameSpan.className = 'file-name';
            nameSpan.textContent = fileName;
            filePath.appendChild(nameSpan);
            
            fileInfo.appendChild(filePath);
            
            const fileSize = document.createElement('div');
            fileSize.className = 'file-size';
            fileSize.textContent = file.size_formatted;
            fileInfo.appendChild(fileSize);
            
            fileItem.appendChild(fileInfo);
            filesDiv.appendChild(fileItem);
        });
        
        groupDiv.appendChild(filesDiv);
        fileList.appendChild(groupDiv);
    });
    
    // Select and view the first file
    if (files.length > 0) {
        const firstFile = fileList.querySelector('.file-item');
        if (firstFile) {
            firstFile.classList.add('selected');
            viewFile(files[0].name);
        }
    }
}

function getFileTypeIcon(type, filename) {
    const icons = {
        manifest: '📄',
        code: '📝',
        markup: '🌐',
        locales: '🌍',
        images: '🖼️',
        audio: '🔊',
        font: '🔤',
        misc: '📎'
    };
    return icons[type] || '📄';
} 