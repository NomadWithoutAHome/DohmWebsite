function sort_files(files) {
    function get_sort_key(file) {
        const name = file.name;
        // Primary sort by file type
        let type_order;
        if (name === 'manifest.json') type_order = 0;
        else if (name.startsWith('_locales/')) type_order = 1;
        else if (get_generic_type(name) === 'code') type_order = 2;
        else if (get_generic_type(name) === 'markup') type_order = 3;
        else if (get_generic_type(name) === 'images') type_order = 4;
        else type_order = 5;
            
        // Secondary sort by directory depth
        const depth = name.split('/').length - 1;
        
        // Tertiary sort by name
        return [type_order, depth, name];
    }
    
    return files.sort((a, b) => {
        const [typeA, depthA, nameA] = get_sort_key(a);
        const [typeB, depthB, nameB] = get_sort_key(b);
        
        if (typeA !== typeB) return typeA - typeB;
        if (depthA !== depthB) return depthA - depthB;
        return nameA.localeCompare(nameB);
    });
}

function get_file_metadata(zip_info) {
    return {
        name: zip_info.filename,
        size: zip_info.file_size,
        size_formatted: format_file_size(zip_info.file_size),
        compressed_size: zip_info.compress_size,
        type: get_generic_type(zip_info.filename),
        mime_type: get_mime_type(zip_info.filename),
        is_binary: is_binary_file(zip_info.filename),
        modified: zip_info.date_time
    };
}

function create_file_list_item(file) {
    const listItem = document.createElement('li');
    listItem.innerHTML = `
        <span class="file-path">
            <span class="file-dir">${file.name.substring(0, file.name.lastIndexOf('/') + 1)}</span>
            <span class="file-name">${file.name.substring(file.name.lastIndexOf('/') + 1)}</span>
        </span>
        <span class="file-size" title="${file.size} bytes">${file.size_formatted}</span>
    `;
    
    listItem.dataset.filename = file.name;
    if (file.type) {
        listItem.classList.add(`gtype-${file.type}`);
    }
    
    listItem.addEventListener('click', () => {
        document.querySelector('.file-selected')?.classList.remove('file-selected');
        listItem.classList.add('file-selected');
        view_file_info(file);
    });
    
    return listItem;
}

function update_file_list(files) {
    const fileList = document.getElementById('file-list');
    fileList.textContent = '';
    
    const sortedFiles = sort_files(files);
    const fragment = document.createDocumentFragment();
    
    sortedFiles.forEach(file => {
        fragment.appendChild(create_file_list_item(file));
    });
    
    fileList.appendChild(fragment);
    
    // Update type counts
    const typeCounts = {};
    files.forEach(file => {
        if (file.type) {
            typeCounts[file.type] = (typeCounts[file.type] || 0) + 1;
        }
    });
    
    Object.entries(typeCounts).forEach(([type, count]) => {
        const checkbox = document.querySelector(`input[data-filter-type="${type}"]`);
        if (checkbox) {
            const counter = checkbox.parentNode.querySelector('.gcount');
            if (counter) counter.textContent = count;
        }
    });
} 