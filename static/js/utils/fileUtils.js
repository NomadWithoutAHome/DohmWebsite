function is_binary_file(filename) {
    const binary_extensions = new Set([
        // Images
        'png', 'jpg', 'jpeg', 'gif', 'bmp', 'ico', 'webp', 'svg',
        // Audio
        'mp3', 'wav', 'ogg', 'm4a',
        // Fonts
        'ttf', 'woff', 'woff2', 'otf', 'eot'
    ]);
    return binary_extensions.has(filename.split('.').pop().toLowerCase());
}

function is_font_file(filename) {
    const font_extensions = new Set(['ttf', 'woff', 'woff2', 'otf', 'eot']);
    return font_extensions.has(filename.split('.').pop().toLowerCase());
}

function format_file_size(size) {
    if (size < 1024) return `${size} B`;
    if (size < 1024 * 1024) return `${(size/1024).toFixed(1)} KB`;
    if (size < 1024 * 1024 * 1024) return `${(size/1024/1024).toFixed(1)} MB`;
    return `${(size/1024/1024/1024).toFixed(1)} GB`;
}

function get_generic_type(filename) {
    if (filename === 'manifest.json') return '';
    
    const extension = filename.split('.').pop().toLowerCase();
    
    if (/^(jsx?|tsx?|wat|coffee)$/.test(extension)) return 'code';
    if (/^(bmp|cur|gif|ico|jpe?g|png|psd|svg|tiff?|xcf|webp)$/.test(extension)) return 'images';
    if (/^(css|sass|less|html?|xhtml|xml)$/.test(extension)) return 'markup';
    if (filename.startsWith('_locales/')) return 'locales';
    
    return 'misc';
} 