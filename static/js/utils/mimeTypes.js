function get_mime_type(filename) {
    if (/^META-INF\/.*\.[ms]f$/.test(filename)) {
        return 'text/plain';
    }
    
    if (/(^|\/)(AUTHORS|CHANGELOG|COPYING|INSTALL|LICENSE|NEWS|README|THANKS)$/i.test(filename)) {
        return 'text/plain';
    }
    
    const extension = filename.split('.').pop().toLowerCase();
    const mime_types = {
        'js': 'application/javascript',
        'css': 'text/css',
        'html': 'text/html',
        'json': 'application/json',
        'txt': 'text/plain',
        'xml': 'text/xml',
        'png': 'image/png',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'gif': 'image/gif',
        'webp': 'image/webp',
        'svg': 'image/svg+xml',
        'ttf': 'font/ttf',
        'woff': 'font/woff',
        'woff2': 'font/woff2',
        'otf': 'font/otf',
        'eot': 'application/vnd.ms-fontobject',
        'crx': 'application/zip',
        'nex': 'application/zip',
        'xpi': 'application/zip',
        'md': 'text/plain'
    };
    
    return mime_types[extension] || 'application/octet-stream';
} 