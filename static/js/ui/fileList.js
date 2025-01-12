function createFileListItem(file) {
    const item = document.createElement('div');
    item.className = 'file-item';
    item.dataset.filename = file.name;
    
    // Get file type icon
    const typeIcon = getFileTypeIcon(file.type, file.name);
    
    // Split path into directory and filename
    const lastSlash = file.name.lastIndexOf('/');
    const directory = lastSlash > -1 ? file.name.substring(0, lastSlash + 1) : '';
    const filename = lastSlash > -1 ? file.name.substring(lastSlash + 1) : file.name;
    
    item.innerHTML = `
        <div class="file-info">
            <span class="file-icon text-sm">${typeIcon}</span>
            <span class="file-path truncate">
                ${directory && `<span class="file-dir opacity-60">${directory}</span>`}
                <span class="file-name">${filename}</span>
            </span>
            <span class="file-size opacity-60" title="${file.size} bytes">${file.size_formatted}</span>
        </div>
    `;
    
    item.onclick = () => {
        document.querySelector('.file-item.selected')?.classList.remove('selected');
        item.classList.add('selected');
        viewFile(file.name);
    };
    
    return item;
}

function getFileTypeIcon(type, filename) {
    if (filename === 'manifest.json') return '📄';
    
    const iconMap = {
        'code': '📝',
        'markup': '🌐',
        'locales': '🌍',
        'images': '🖼️',
        'audio': '🔊',
        'font': '🔤',
        'misc': '📁'
    };
    
    return iconMap[type] || '📄';
}

function getFileGroup(type, filename) {
    if (filename === 'manifest.json') return 'manifest';
    return type || 'misc';
}

function updateFileList(files) {
    // Group files by type
    const fileGroups = {};
    
    files.forEach(file => {
        const group = getFileGroup(file.type, file.name);
        if (!fileGroups[group]) {
            fileGroups[group] = [];
        }
        fileGroups[group].push(file);
    });
    
    // Sort files within each group
    Object.values(fileGroups).forEach(group => {
        group.sort((a, b) => {
            // Sort by directory depth first
            const depthA = a.name.split('/').length;
            const depthB = b.name.split('/').length;
            if (depthA !== depthB) return depthA - depthB;
            
            // Then by name
            return a.name.localeCompare(b.name);
        });
    });
    
    // Update the file list UI
    const fileList = document.getElementById('file-list');
    
    // Show/hide group containers based on whether they have files
    fileList.querySelectorAll('.file-group').forEach(group => {
        const type = group.dataset.type;
        const hasFiles = fileGroups[type]?.length > 0;
        group.style.display = hasFiles ? 'block' : 'none';
        
        if (hasFiles) {
            const filesContainer = group.querySelector('.group-files');
            filesContainer.innerHTML = '';
            fileGroups[type].forEach(file => {
                filesContainer.appendChild(createFileListItem(file));
            });
        }
    });
    
    // Select first file
    if (files.length > 0) {
        const firstGroup = Object.values(fileGroups)[0];
        if (firstGroup?.length > 0) {
            const firstFile = firstGroup[0];
            const firstItem = fileList.querySelector(`[data-filename="${firstFile.name}"]`);
            firstItem?.click();
        }
    }
    
    // Update type counts
    updateTypeCounts(fileGroups);
}

function updateTypeCounts(fileGroups) {
    Object.entries(fileGroups).forEach(([type, files]) => {
        const header = document.querySelector(`.file-group[data-type="${type}"] .group-header`);
        if (header && files.length > 0) {
            header.textContent = `${header.textContent.split('(')[0]} (${files.length})`;
        }
    });
} 