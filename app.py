from flask import Flask, render_template, request, send_file, jsonify
import requests
import os
import zipfile
from io import BytesIO

app = Flask(__name__)

def download_crx(extension_id):
    crx_url = f"https://clients2.google.com/service/update2/crx?response=redirect&acceptformat=crx2,crx3&prodversion=49.0&x=id%3D{extension_id}%26installsource%3Dondemand%26uc"
    response = requests.get(crx_url)
    if response.status_code == 200:
        return response.content
    return None

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/tools')
def tools():
    return render_template('tools.html')

@app.route('/download-crx', methods=['POST'])
def download_extension():
    extension_id = request.form.get('extension_id')
    format_type = request.form.get('format', 'crx')
    
    if not extension_id:
        return jsonify({'error': 'Extension ID is required'}), 400
    
    crx_content = download_crx(extension_id)
    if not crx_content:
        return jsonify({'error': 'Failed to download extension'}), 400
    
    if format_type == 'zip':
        # Convert CRX to ZIP
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr(f'{extension_id}.crx', crx_content)
        zip_buffer.seek(0)
        return send_file(
            zip_buffer,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'{extension_id}.zip'
        )
    else:
        # Send as CRX
        return send_file(
            BytesIO(crx_content),
            mimetype='application/x-chrome-extension',
            as_attachment=True,
            download_name=f'{extension_id}.crx'
        )

if __name__ == '__main__':
    app.run(debug=True) 