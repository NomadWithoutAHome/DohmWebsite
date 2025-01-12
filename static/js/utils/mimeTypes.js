function getMimeType(filename) {
    // Special cases for plain text files
    if (/^META-INF\/.*\.[ms]f$/.test(filename)) {
        return 'text/plain';
    }
    
    if (/(^|\/)(?:AUTHORS|CHANGELOG|COPYING|INSTALL|LICENSE|NEWS|README|THANKS)$/i.test(filename)) {
        return 'text/plain';
    }
    
    const extension = filename.split('.').pop().toLowerCase();
    
    // Handle special cases
    if (['crx', 'nex', 'xpi'].includes(extension)) {
        return 'application/zip';
    }
    if (extension === 'md') {
        return 'text/plain';
    }
    
    // Common MIME types
    const mimeTypes = {
        // Code
        'js': 'application/javascript',
        'jsx': 'application/javascript',
        'ts': 'application/javascript',
        'tsx': 'application/javascript',
        'coffee': 'application/javascript',
        
        // Markup
        'css': 'text/css',
        'scss': 'text/css',
        'sass': 'text/css',
        'less': 'text/css',
        'html': 'text/html',
        'htm': 'text/html',
        'xml': 'text/xml',
        'svg': 'image/svg+xml',
        
        // Data
        'json': 'application/json',
        'yaml': 'text/plain',
        'yml': 'text/plain',
        'txt': 'text/plain',
        'md': 'text/plain',
        'ini': 'text/plain',
        'conf': 'text/plain',
        
        // Images
        'png': 'image/png',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'gif': 'image/gif',
        'webp': 'image/webp',
        'bmp': 'image/bmp',
        'ico': 'image/x-icon',
        
        // Audio
        'mp3': 'audio/mpeg',
        'wav': 'audio/wav',
        'ogg': 'audio/ogg',
        'm4a': 'audio/mp4',
        
        // Fonts
        'ttf': 'font/ttf',
        'woff': 'font/woff',
        'woff2': 'font/woff2',
        'otf': 'font/otf',
        'eot': 'application/vnd.ms-fontobject'
    };
    
    return mimeTypes[extension] || 'application/octet-stream';
} 