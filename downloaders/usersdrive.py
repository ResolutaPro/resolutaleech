"""
Downloader para UsersDrive.com
Extrai link direto automaticamente da página
"""

import os
import re
import time
import requests
from .base import BaseDownloader


class UsersDriveDownloader(BaseDownloader):
    """Downloader para UsersDrive.com"""
    
    URL_PATTERNS = [
        r'usersdrive\.com/[a-z0-9]+\.html',
    ]
    
    HOST_NAME = "UsersDrive"
    
    def __init__(self, download_folder: str):
        super().__init__(download_folder)
        self.cancelled = False
    
    def download(self, url: str, callback=None, options: dict = None) -> dict:
        """Executa download do UsersDrive"""
        self.cancelled = False
        options = options or {}
        
        try:
            # Extrair link direto da página
            direct_url, filename = self._extract_direct_link(url)
            
            if not direct_url:
                return {'success': False, 'error': 'Não foi possível extrair o link direto'}
            
            # Usar filename das opções se fornecido
            if options.get('filename'):
                filename = options['filename']
            
            # Fazer download direto
            return self._download_file(direct_url, filename, callback)
            
        except Exception as e:
            return {'success': False, 'error': f'Erro: {str(e)}'}
    
    def _extract_direct_link(self, page_url: str) -> tuple:
        """Extrai o link direto da página do UsersDrive"""
        try:
            # Acessar página inicial
            response = self.session.get(page_url, timeout=30)
            response.raise_for_status()
            html = response.text
            
            # Procurar link direto no HTML
            # Padrão 1: link em data-url ou href com userdrive.org
            patterns = [
                r'https?://[a-z0-9]+\.userdrive\.org[^"\'<>\s]+',
                r'https?://d\d+\.userdrive\.org:\d+/d/[^"\'<>\s]+',
                r'href=["\']([^"\']*userdrive\.org[^"\']*)["\']',
                r'src=["\']([^"\']*userdrive\.org[^"\']*)["\']',
            ]
            
            direct_url = None
            for pattern in patterns:
                match = re.search(pattern, html, re.IGNORECASE)
                if match:
                    direct_url = match.group(1) if match.lastindex else match.group(0)
                    break
            
            # Se não encontrou, tentar extrair do formulário/botão de download
            if not direct_url:
                # Procurar por token ou parâmetros de download
                file_id = re.search(r'/([a-z0-9]+)\.html', page_url)
                if file_id:
                    # Tentar fazer POST para obter link
                    direct_url = self._try_post_download(page_url, html, file_id.group(1))
            
            # Extrair nome do arquivo da URL
            filename = None
            if direct_url:
                # Decodificar URL e extrair nome
                from urllib.parse import unquote
                path = direct_url.split('/')[-1].split('?')[0]
                filename = unquote(path)
            
            return direct_url, filename
            
        except Exception as e:
            print(f"Erro ao extrair link: {e}")
            return None, None
    
    def _try_post_download(self, page_url: str, html: str, file_id: str) -> str:
        """Tenta obter link via POST request"""
        try:
            # Procurar form action ou endpoint de download
            form_match = re.search(r'<form[^>]*action=["\']([^"\']+)["\']', html)
            
            # Procurar tokens CSRF ou outros campos hidden
            tokens = {}
            hidden_fields = re.findall(r'<input[^>]*type=["\']hidden["\'][^>]*name=["\']([^"\']+)["\'][^>]*value=["\']([^"\']*)["\']', html)
            for name, value in hidden_fields:
                tokens[name] = value
            
            # Tentar diferentes endpoints
            endpoints = [
                page_url,
                f"https://usersdrive.com/download/{file_id}",
                f"https://usersdrive.com/d/{file_id}",
            ]
            
            if form_match:
                endpoints.insert(0, form_match.group(1))
            
            for endpoint in endpoints:
                try:
                    data = {'op': 'download', 'id': file_id, **tokens}
                    resp = self.session.post(endpoint, data=data, timeout=15, allow_redirects=False)
                    
                    # Verificar redirect para link direto
                    if resp.status_code in (301, 302, 303, 307):
                        location = resp.headers.get('Location', '')
                        if 'userdrive.org' in location:
                            return location
                    
                    # Verificar link no corpo da resposta
                    match = re.search(r'https?://[a-z0-9]+\.userdrive\.org[^"\'<>\s]+', resp.text)
                    if match:
                        return match.group(0)
                except:
                    continue
            
            return None
        except:
            return None
    
    def _download_file(self, url: str, filename: str, callback=None) -> dict:
        """Baixa o arquivo do link direto"""
        try:
            start_time = time.time()
            
            # Fazer request com stream
            response = self.session.get(url, stream=True, timeout=60)
            response.raise_for_status()
            
            # Obter tamanho total
            total_size = int(response.headers.get('content-length', 0))
            
            # Determinar nome do arquivo
            if not filename:
                filename = self.extract_filename_from_headers(response.headers)
            if not filename:
                filename = self.extract_filename_from_url(url)
            if not filename:
                filename = f"usersdrive_{int(time.time())}.mp4"
            
            filename = self.sanitize_filename(filename)
            filepath = self.get_unique_filepath(filename)
            
            # Baixar arquivo
            downloaded = 0
            chunk_size = 1024 * 1024  # 1MB
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if self.cancelled:
                        f.close()
                        if os.path.exists(filepath):
                            os.remove(filepath)
                        return {'success': False, 'error': 'Download cancelado'}
                    
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if callback:
                            elapsed = time.time() - start_time
                            speed = downloaded / elapsed if elapsed > 0 else 0
                            callback(downloaded, total_size, speed)
            
            return {
                'success': True,
                'filepath': filepath,
                'filename': os.path.basename(filepath),
                'size': os.path.getsize(filepath),
            }
            
        except requests.exceptions.HTTPError as e:
            return {'success': False, 'error': f'Erro HTTP: {e.response.status_code}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_file_info(self, url: str) -> dict:
        """Obtém informações do arquivo"""
        direct_url, filename = self._extract_direct_link(url)
        if direct_url:
            try:
                resp = self.session.head(direct_url, timeout=10)
                return {
                    'available': True,
                    'filename': filename,
                    'size': int(resp.headers.get('content-length', 0)),
                }
            except:
                pass
        
        return {
            'available': True,
            'filename': None,
            'size': 0,
        }
    
    def cancel(self):
        """Cancela o download atual"""
        self.cancelled = True
