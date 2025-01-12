function validate_crx(content) {
    if (content.length < 16) {
        return { isValid: false, version: null, error: "CRX file too small" };
    }
    
    // Check magic number ('Cr24')
    if (content.slice(0, 4) !== 'Cr24') {
        return { isValid: false, version: null, error: "Invalid CRX header: Not a valid CRX file" };
    }
    
    // Get CRX version (supported: 2 or 3)
    const version = new DataView(content.buffer).getUint32(4, true);
    if (![2, 3].includes(version)) {
        return { isValid: false, version: null, error: `Unsupported CRX version: ${version}` };
    }
    
    return { isValid: true, version: version, error: null };
}

function extract_extension_id(url_or_id) {
    // New Chrome Web Store URL pattern
    const url_pattern = /chromewebstore\.google\.com\/detail\/[^/]+\/([a-z0-9]{32})/;
    const match = url_pattern.exec(url_or_id);
    if (match) return match[1];
    
    // If it's already just an ID (alphanumeric string), return it
    if (/^[a-z0-9]{32}$/.test(url_or_id)) return url_or_id;
    
    return null;
} 