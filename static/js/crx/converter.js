function get_zip_offset(content, version) {
    if (version === 2) {
        // CRX2 format: header + public key length + signature length
        const view = new DataView(content.buffer);
        const public_key_length = view.getUint32(8, true);
        const signature_length = view.getUint32(12, true);
        return 16 + public_key_length + signature_length;
    } else {  // version === 3
        // CRX3 format: header + header length
        const view = new DataView(content.buffer);
        const header_length = view.getUint32(8, true);
        return 12 + header_length;
    }
}

function crx_to_zip(crx_content) {
    try {
        const validation = validate_crx(crx_content);
        if (!validation.isValid) {
            return { content: null, error: validation.error };
        }
        
        // Get ZIP start offset
        const zip_offset = get_zip_offset(crx_content, validation.version);
        
        // Extract ZIP content
        const zip_content = crx_content.slice(zip_offset);
        
        // Verify ZIP header
        if (zip_content.slice(0, 4) !== 'PK\x03\x04') {
            return { content: null, error: "Invalid ZIP data in CRX" };
        }
        
        return { content: zip_content, error: null };
    } catch (e) {
        return { content: null, error: `Error processing CRX: ${e.message}` };
    }
} 