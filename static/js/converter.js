// Initialize JSON Editor
const editor = new JSONEditor(document.getElementById('json-editor'), {
    mode: 'tree',
    modes: ['tree', 'code'],
    theme: 'ace/theme/monokai',
    templates: [
        {
            text: 'Object',
            title: 'Insert a new object',
            className: 'jsoneditor-type-object',
            field: 'ObjectName',
            value: {
                'field1': 'value1'
            }
        }
    ],
    onError: function(err) {
        showError(err.toString());
    },
    onModeChange: function(newMode, oldMode) {
        console.log('Mode switched from', oldMode, 'to', newMode);
    },
    onChange: function() {
        document.getElementById('save-button').disabled = false;
        document.getElementById('save-button').classList.remove('opacity-50', 'cursor-not-allowed');
    },
    colors: {
        default: '#fbbf24',
        background: '#1f2937',
        border: '#f97316',
        selected: '#374151',
        hover: '#374151',
        expandable: '#fbbf24',
        separator: '#f97316'
    }
});

let currentFileName = '';
let originalData = null;

// Show error in retro style
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

// Handle file upload
document.getElementById('save-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const fileInput = document.getElementById('save-file');
    const file = fileInput.files[0];
    
    if (!file) {
        showError('Please select a file first.');
        return;
    }

    if (!file.name.toLowerCase().endsWith('.txt')) {
        showError('Only .txt files are allowed.');
        return;
    }

    currentFileName = file.name;
    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/convert/upload', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        if (response.ok) {
            editor.set(result.data);
            originalData = JSON.stringify(result.data);
            document.getElementById('editor-section').classList.remove('hidden');
            document.getElementById('save-button').disabled = true;
            document.getElementById('save-button').classList.add('opacity-50', 'cursor-not-allowed');
            console.log('Save file loaded successfully');
            fileInput.value = '';
        } else {
            showError(result.error);
        }
    } catch (error) {
        showError('Error uploading file: ' + error.message);
    }
});

// Handle save changes
document.getElementById('save-button').addEventListener('click', async () => {
    try {
        const data = editor.get();
        const activeTab = document.querySelector('.tab-button.active').getAttribute('data-tab');
        
        // Use different endpoints based on the active tab
        const endpoint = activeTab === 'wsdir-editor' ? '/convert/wsdir/save' : '/convert/save';
        
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                data: data,
                filename: currentFileName
            })
        });

        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = currentFileName;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            originalData = JSON.stringify(data);
            document.getElementById('save-button').disabled = true;
            document.getElementById('save-button').classList.add('opacity-50', 'cursor-not-allowed');
            console.log(activeTab === 'wsdir-editor' ? 'WSDir file saved successfully' : 'Save file downloaded successfully');
        } else {
            const error = await response.json();
            showError(error.error);
        }
    } catch (error) {
        showError('Error saving file: ' + error.message);
    }
});

// Check for changes in the editor
editor.aceEditor?.on('change', () => {
    const currentData = JSON.stringify(editor.get());
    const hasChanges = currentData !== originalData;
    document.getElementById('save-button').disabled = !hasChanges;
    if (hasChanges) {
        document.getElementById('save-button').classList.remove('opacity-50', 'cursor-not-allowed');
    } else {
        document.getElementById('save-button').classList.add('opacity-50', 'cursor-not-allowed');
    }
});

// Handle JSON download
document.getElementById('download-json').addEventListener('click', () => {
    try {
        const data = editor.get();
        const activeTab = document.querySelector('.tab-button.active').getAttribute('data-tab');
        
        // Get base filename without extension
        let jsonFilename;
        if (activeTab === 'wsref-editor') {
            jsonFilename = currentFileName.replace('.assets', '.json');
        } else if (activeTab === 'wsdir-editor' || activeTab === 'save-editor') {
            jsonFilename = currentFileName.replace('.txt', '.json');
        } else {
            jsonFilename = currentFileName + '.json';
        }

        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = jsonFilename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        console.log('JSON file downloaded successfully');
    } catch (error) {
        showError('Error downloading JSON: ' + error.message);
    }
});

// Handle WSRef file upload
document.getElementById('load-wsref-button').addEventListener('click', async () => {
    const fileInput = document.getElementById('wsref-file');
    const file = fileInput.files[0];
    
    if (!file) {
        showError('Please select a file first.');
        return;
    }

    if (!file.name.toLowerCase().endsWith('.assets')) {
        showError('Only .assets files are allowed.');
        return;
    }

    currentFileName = file.name;
    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/convert/wsref/upload', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        if (response.ok) {
            editor.set(result.data);
            originalData = JSON.stringify(result.data);
            document.getElementById('editor-section').classList.remove('hidden');
            document.getElementById('save-button').disabled = true;
            document.getElementById('save-button').classList.add('opacity-50', 'cursor-not-allowed');
            console.log('WSRef data loaded successfully');
            fileInput.value = '';
        } else {
            showError(result.error);
        }
    } catch (error) {
        showError('Error uploading file: ' + error.message);
    }
});

// Handle WSDir file upload
document.getElementById('load-wsdir-button').addEventListener('click', async () => {
    const fileInput = document.getElementById('wsdir-file');
    const file = fileInput.files[0];
    
    if (!file) {
        showError('Please select a file first.');
        return;
    }

    if (!file.name.toLowerCase().endsWith('.txt')) {
        showError('Only .txt files are allowed.');
        return;
    }

    currentFileName = file.name;
    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/convert/wsdir/upload', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        if (response.ok) {
            editor.set(result.data);
            originalData = JSON.stringify(result.data);
            document.getElementById('editor-section').classList.remove('hidden');
            document.getElementById('save-button').disabled = true;
            document.getElementById('save-button').classList.add('opacity-50', 'cursor-not-allowed');
            console.log('WSDir data loaded successfully');
            fileInput.value = '';
        } else {
            showError(result.error);
        }
    } catch (error) {
        showError('Error uploading file: ' + error.message);
    }
}); 