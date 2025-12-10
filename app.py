"""
ResolutaLeech - Alternativa ao Rapidleech em Python
Um gerenciador de downloads web moderno e eficiente
"""

import os
import json
import time
import threading
import uuid
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory, Response
from werkzeug.utils import secure_filename

# Importar gerenciadores de download
from downloaders import DownloadManager

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24).hex()
app.config['DOWNLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'downloads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

# Criar pasta de downloads se não existir
os.makedirs(app.config['DOWNLOAD_FOLDER'], exist_ok=True)

# Gerenciador de downloads global
download_manager = DownloadManager(app.config['DOWNLOAD_FOLDER'])


@app.route('/')
def index():
    """Página principal"""
    return render_template('index.html')


@app.route('/api/download', methods=['POST'])
def start_download():
    """Inicia um novo download"""
    data = request.get_json()
    
    if not data or 'url' not in data:
        return jsonify({'error': 'URL não fornecida'}), 400
    
    url = data['url'].strip()
    if not url:
        return jsonify({'error': 'URL vazia'}), 400
    
    # Opções de download
    options = {
        'filename': data.get('filename', ''),
        'use_megatools': data.get('use_megatools', False),
    }
    
    try:
        download_id = download_manager.add_download(url, options)
        return jsonify({
            'success': True,
            'download_id': download_id,
            'message': 'Download iniciado'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/download/<download_id>', methods=['GET'])
def get_download_status(download_id):
    """Retorna o status de um download"""
    status = download_manager.get_status(download_id)
    if status is None:
        return jsonify({'error': 'Download não encontrado'}), 404
    return jsonify(status)


@app.route('/api/downloads', methods=['GET'])
def list_downloads():
    """Lista todos os downloads"""
    return jsonify(download_manager.list_all())


@app.route('/api/download/<download_id>', methods=['DELETE'])
def cancel_download(download_id):
    """Cancela um download"""
    success = download_manager.cancel(download_id)
    if success:
        return jsonify({'success': True, 'message': 'Download cancelado'})
    return jsonify({'error': 'Download não encontrado'}), 404


@app.route('/api/download/<download_id>/file', methods=['GET'])
def download_file(download_id):
    """Baixa o arquivo finalizado"""
    status = download_manager.get_status(download_id)
    if status is None:
        return jsonify({'error': 'Download não encontrado'}), 404
    
    if status['status'] != 'completed':
        return jsonify({'error': 'Download ainda não concluído'}), 400
    
    filepath = status.get('filepath', '')
    if not filepath or not os.path.exists(filepath):
        return jsonify({'error': 'Arquivo não encontrado'}), 404
    
    directory = os.path.dirname(filepath)
    filename = os.path.basename(filepath)
    return send_from_directory(directory, filename, as_attachment=True)


@app.route('/api/files', methods=['GET'])
def list_files():
    """Lista arquivos na pasta de downloads"""
    files = []
    download_folder = app.config['DOWNLOAD_FOLDER']
    
    for filename in os.listdir(download_folder):
        filepath = os.path.join(download_folder, filename)
        if os.path.isfile(filepath):
            stat = os.stat(filepath)
            files.append({
                'name': filename,
                'size': stat.st_size,
                'size_formatted': format_size(stat.st_size),
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })
    
    files.sort(key=lambda x: x['modified'], reverse=True)
    return jsonify(files)


@app.route('/api/files/<filename>', methods=['DELETE'])
def delete_file(filename):
    """Deleta um arquivo"""
    filepath = os.path.join(app.config['DOWNLOAD_FOLDER'], secure_filename(filename))
    if os.path.exists(filepath):
        os.remove(filepath)
        return jsonify({'success': True, 'message': 'Arquivo deletado'})
    return jsonify({'error': 'Arquivo não encontrado'}), 404


@app.route('/api/system', methods=['GET'])
def system_info():
    """Retorna informações do sistema"""
    import shutil
    
    download_folder = app.config['DOWNLOAD_FOLDER']
    total, used, free = shutil.disk_usage(download_folder)
    
    return jsonify({
        'disk': {
            'total': total,
            'used': used,
            'free': free,
            'total_formatted': format_size(total),
            'used_formatted': format_size(used),
            'free_formatted': format_size(free),
            'percent_used': round((used / total) * 100, 1)
        },
        'download_folder': download_folder,
        'active_downloads': download_manager.active_count(),
        'megatools_available': download_manager.is_megatools_available(),
    })


@app.route('/api/hosts', methods=['GET'])
def list_hosts():
    """Lista hosts suportados"""
    return jsonify(download_manager.get_supported_hosts())


@app.route('/files/<filename>')
def serve_file(filename):
    """Serve um arquivo para download"""
    return send_from_directory(app.config['DOWNLOAD_FOLDER'], filename)


def format_size(size_bytes):
    """Formata tamanho em bytes para formato legível"""
    if size_bytes == 0:
        return "0 B"
    
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    i = 0
    size = float(size_bytes)
    
    while size >= 1024 and i < len(units) - 1:
        size /= 1024
        i += 1
    
    return f"{size:.2f} {units[i]}"


if __name__ == '__main__':
    print("=" * 50)
    print("  ResolutaLeech - Gerenciador de Downloads")
    print("=" * 50)
    print(f"  Pasta de downloads: {app.config['DOWNLOAD_FOLDER']}")
    print(f"  Acesse: http://localhost:5000")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=True)
