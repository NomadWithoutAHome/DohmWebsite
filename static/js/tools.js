let currentExtensionId = null;

document.addEventListener('DOMContentLoaded', () => {
    const crxForm = document.getElementById('crx-form');
    const viewButton = document.getElementById('view-button');
    const sourceViewerModal = document.getElementById('source-viewer-modal');
    const closeModal = document.getElementById('close-modal');
    
    crxForm.addEventListener('submit', handle_download);
    viewButton.addEventListener('click', handle_view);
    closeModal.addEventListener('click', () => sourceViewerModal.classList.add('hidden'));
    
    // Add hover sound effect to buttons
    document.querySelectorAll('.retro-button').forEach(button => {
        button.addEventListener('mouseover', () => {
            const audio = new Audio('/static/assets/hover.wav');
            audio.volume = 0.2;
            audio.play();
        });
    });
});

async function handle_download(e) {
    e.preventDefault();
    const form = e.target;
    const errorMsg = document.getElementById('error-message');
    errorMsg.style.display = 'none';
    
    const formData = new FormData(form);
    try {
        const response = await fetch('/download-crx', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.error || 'Download failed');
        }
        
        // Create a temporary link to download the file
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = response.headers.get('content-disposition')?.split('filename=')[1] || 'extension.crx';
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
    } catch (error) {
        errorMsg.textContent = error.message;
        errorMsg.style.display = 'block';
    }
}

async function handle_view() {
    const extensionInput = document.getElementById('extension-id');
    const errorMsg = document.getElementById('error-message');
    const sourceViewerModal = document.getElementById('source-viewer-modal');
    const fileSelector = document.getElementById('file-selector');
    
    errorMsg.style.display = 'none';
    currentExtensionId = extensionInput.value;
    
    try {
        const response = await fetch('/view-extension', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                extension_id: currentExtensionId,
                list_files: true
            })
        });
        
        const data = await response.json();
        if (data.error) {
            throw new Error(data.error);
        }
        
        // Update file selector
        fileSelector.innerHTML = '';
        data.files.forEach(file => {
            const option = document.createElement('option');
            option.value = file.name;
            option.textContent = file.name;
            fileSelector.appendChild(option);
        });
        
        // Update file list
        update_file_list(data.files);
        
        // Show modal
        sourceViewerModal.classList.remove('hidden');
        
        // View first file (usually manifest.json)
        if (data.files.length > 0) {
            view_file_info(data.files[0]);
        }
    } catch (error) {
        errorMsg.textContent = error.message;
        errorMsg.style.display = 'block';
    }
}

// File selector change handler
document.getElementById('file-selector')?.addEventListener('change', (e) => {
    const filename = e.target.value;
    const fileItem = document.querySelector(`[data-filename="${filename}"]`);
    if (fileItem) {
        fileItem.click();
    }
}); 