"""
Downloader para links diretos (HTTP/HTTPS)
"""

import os
import time
import requests
from .base import BaseDownloader


class DirectDownloader(BaseDownloader):
    """Downloader para links HTTP/HTTPS diretos"""
    
    URL_PATTERNS = [
        r'^https?://',  # Qualquer URL HTTP/HTTPS
    ]
    
    HOST_NAME = "Direct Link"
    
    def __init__(self, download_folder: str):
        super().__init__(download_folder)
        self.chunk_size = 8192  # 8KB chunks
        self.cancelled = False
    
    def download(self, url: str, callback=None, options: dict = None) -> dict:
        """Executa download direto via HTTP"""
        self.cancelled = False
        options = options or {}
        
        try:
            # Fazer requisição com stream
            response = self.session.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            # Obter informações do arquivo
            total_size = int(response.headers.get('content-length', 0))
            
            # Determinar nome do arquivo
            filename = options.get('filename', '')
            if not filename:
                filename = self.extract_filename_from_headers(response.headers)
            if not filename:
                filename = self.extract_filename_from_url(url)
            if not filename:
                filename = f"download_{int(time.time())}"
            
            filename = self.sanitize_filename(filename)
            filepath = self.get_unique_filepath(filename)
            
            # Baixar arquivo
            downloaded = 0
            start_time = time.time()
            last_callback_time = start_time
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=self.chunk_size):
                    if self.cancelled:
                        f.close()
                        if os.path.exists(filepath):
                            os.remove(filepath)
                        return {'success': False, 'error': 'Download cancelado'}
                    
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Callback de progresso (máximo 10x por segundo)
                        current_time = time.time()
                        if callback and (current_time - last_callback_time) >= 0.1:
                            elapsed = current_time - start_time
                            speed = downloaded / elapsed if elapsed > 0 else 0
                            callback(downloaded, total_size, speed)
                            last_callback_time = current_time
            
            # Callback final
            if callback:
                elapsed = time.time() - start_time
                speed = downloaded / elapsed if elapsed > 0 else 0
                callback(downloaded, total_size, speed)
            
            return {
                'success': True,
                'filepath': filepath,
                'filename': os.path.basename(filepath),
                'size': downloaded,
            }
            
        except requests.exceptions.Timeout:
            return {'success': False, 'error': 'Timeout na conexão'}
        except requests.exceptions.HTTPError as e:
            return {'success': False, 'error': f'Erro HTTP: {e.response.status_code}'}
        except requests.exceptions.RequestException as e:
            return {'success': False, 'error': f'Erro de conexão: {str(e)}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_file_info(self, url: str) -> dict:
        """Obtém informações do arquivo via HEAD request"""
        try:
            response = self.session.head(url, timeout=10, allow_redirects=True)
            response.raise_for_status()
            
            size = int(response.headers.get('content-length', 0))
            filename = self.extract_filename_from_headers(response.headers)
            if not filename:
                filename = self.extract_filename_from_url(url)
            
            return {
                'available': True,
                'filename': filename,
                'size': size,
            }
        except Exception as e:
            return {
                'available': False,
                'error': str(e),
            }
    
    def cancel(self):
        """Cancela o download atual"""
        self.cancelled = True
