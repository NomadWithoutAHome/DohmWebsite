async function safe_download_crx(extension_id) {
    try {
        // Using the modern Chrome version to avoid 204 responses
        const crx_url = `https://clients2.google.com/service/update2/crx?response=redirect&acceptformat=crx2,crx3&prodversion=102.0.5005.61&x=id%3D${extension_id}%26installsource%3Dondemand%26uc`;
        
        const response = await fetch(crx_url);
        if (!response.ok) {
            return { content: null, error: `Failed to download extension (Status: ${response.status})` };
        }
        
        const content = await response.arrayBuffer();
        const validation = validate_crx(content);
        
        if (!validation.isValid) {
            return { content: null, error: validation.error };
        }
        
        return { content: content, error: null };
    } catch (e) {
        if (e instanceof TypeError) {
            return { content: null, error: `Network error: ${e.message}` };
        }
        return { content: null, error: `Unexpected error: ${e.message}` };
    }
}

async function get_extension_name(zip_content) {
    try {
        const zip = await JSZip.loadAsync(zip_content);
        const manifest = await zip.file('manifest.json').async('string');
        const manifestData = JSON.parse(manifest);
        let name = manifestData.name?.trim() || '';
        
        // Check if name is a message placeholder
        if (name.startsWith('__MSG_') && name.endsWith('__')) {
            const message_name = name.slice(6, -2);  // Remove __MSG_ and __
            name = await get_localized_message(zip, message_name) || name;
        }
        
        // Remove special characters and spaces, keep alphanumeric and dashes
        let sanitized_name = name.replace(/[^\w\-]/g, '-')
                               .replace(/-+/g, '-')  // Remove multiple consecutive dashes
                               .replace(/^-|-$/g, '');  // Remove leading/trailing dashes
        
        return sanitized_name || null;
    } catch {
        return null;
    }
}

async function get_localized_message(zip, message_name) {
    try {
        // Try English first
        const locales = ['en', 'en_US', 'en_GB'];
        for (const locale of locales) {
            try {
                const messages = await zip.file(`_locales/${locale}/messages.json`).async('string');
                const messageData = JSON.parse(messages);
                if (messageData[message_name]) {
                    return messageData[message_name].message;
                }
            } catch {
                continue;
            }
        }
        
        // If English not found, try any available locale
        const files = Object.keys(zip.files);
        for (const filename of files) {
            if (filename.startsWith('_locales/') && filename.endsWith('/messages.json')) {
                try {
                    const messages = await zip.file(filename).async('string');
                    const messageData = JSON.parse(messages);
                    if (messageData[message_name]) {
                        return messageData[message_name].message;
                    }
                } catch {
                    continue;
                }
            }
        }
        return null;
    } catch {
        return null;
    }
} 