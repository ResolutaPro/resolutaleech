"""
Downloader para MEGA.nz
Implementação nativa usando API do MEGA diretamente
"""

import os
import re
import time
import json
import base64
import struct
import binascii
import threading
import requests
from Crypto.Cipher import AES
from Crypto.Util import Counter
from .base import BaseDownloader


class MegaDownloader(BaseDownloader):
    """Downloader para MEGA.nz usando API nativa"""
    
    URL_PATTERNS = [
        r'mega\.nz/file/',
        r'mega\.nz/folder/',
        r'mega\.nz/#!',
        r'mega\.nz/#F!',
        r'mega\.co\.nz/',
    ]
    
    HOST_NAME = "MEGA.nz"
    API_URL = "https://g.api.mega.co.nz/cs"
    
    def __init__(self, download_folder: str):
        super().__init__(download_folder)
        self.mega_available = True
        self.cancelled = False
        self.seq_no = int(time.time())
    
    def download(self, url: str, callback=None, options: dict = None) -> dict:
        """Executa download do MEGA.nz"""
        self.cancelled = False
        options = options or {}
        
        try:
            # Extrair file_id e key da URL
            file_id, file_key = self._parse_url(url)
            if not file_id or not file_key:
                return {'success': False, 'error': 'URL inválida - não foi possível extrair ID e chave'}
            
            # Obter informações do arquivo via API
            file_info = self._get_file_info_api(file_id)
            if not file_info:
                return {'success': False, 'error': 'Arquivo não encontrado ou indisponível'}
            
            # Decodificar chave
            key = self._base64_to_bytes(file_key)
            if len(key) != 32:
                return {'success': False, 'error': 'Chave de decriptação inválida'}
            
            # Preparar chave AES
            key_array = struct.unpack('>IIIIIIII', key)
            aes_key = struct.pack('>IIII', 
                key_array[0] ^ key_array[4],
                key_array[1] ^ key_array[5],
                key_array[2] ^ key_array[6],
                key_array[3] ^ key_array[7]
            )
            iv = struct.pack('>II', key_array[4], key_array[5]) + b'\x00' * 8
            
            # Decriptar atributos do arquivo
            attr_data = self._base64_to_bytes(file_info['at'])
            filename = self._decrypt_attr(attr_data, aes_key)
            if not filename:
                filename = f"mega_download_{file_id}"
            
            # URL de download
            download_url = file_info.get('g')
            if not download_url:
                return {'success': False, 'error': 'Limite de transferência atingido ou arquivo indisponível'}
            
            file_size = file_info.get('s', 0)
            
            # Preparar arquivo de saída
            filename = self.sanitize_filename(filename)
            filepath = self.get_unique_filepath(filename)
            
            # Fazer download com decriptação
            result = self._download_and_decrypt(
                download_url, filepath, aes_key, iv, file_size, callback
            )
            
            if result['success']:
                return {
                    'success': True,
                    'filepath': filepath,
                    'filename': os.path.basename(filepath),
                    'size': os.path.getsize(filepath) if os.path.exists(filepath) else 0,
                }
            
            return result
            
        except Exception as e:
            error_msg = str(e)
            if 'quota' in error_msg.lower() or 'limit' in error_msg.lower() or '-17' in error_msg:
                return {'success': False, 'error': 'Limite de transferência do MEGA atingido. Tente mais tarde.'}
            return {'success': False, 'error': f'Erro: {error_msg}'}
    
    def _parse_url(self, url: str):
        """Extrai file_id e key da URL do MEGA"""
        url = url.replace('mega.co.nz', 'mega.nz')
        
        # Novo formato: mega.nz/file/FILE_ID#KEY
        match = re.search(r'mega\.nz/file/([^#]+)#(.+)', url)
        if match:
            return match.group(1), match.group(2)
        
        # Formato antigo: mega.nz/#!FILE_ID!KEY
        match = re.search(r'mega\.nz/#!([^!]+)!(.+)', url)
        if match:
            return match.group(1), match.group(2)
        
        return None, None
    
    def _get_file_info_api(self, file_id: str) -> dict:
        """Obtém informações do arquivo via API do MEGA"""
        try:
            self.seq_no += 1
            data = [{'a': 'g', 'g': 1, 'p': file_id}]
            
            response = requests.post(
                f"{self.API_URL}?id={self.seq_no}",
                json=data,
                timeout=30
            )
            
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                if isinstance(result[0], int) and result[0] < 0:
                    return None  # Erro da API
                return result[0]
            return None
        except:
            return None
    
    def _base64_to_bytes(self, data: str) -> bytes:
        """Converte base64 URL-safe para bytes"""
        # Adicionar padding se necessário
        data = data.replace('-', '+').replace('_', '/').replace(',', '')
        padding = 4 - len(data) % 4
        if padding != 4:
            data += '=' * padding
        return base64.b64decode(data)
    
    def _decrypt_attr(self, data: bytes, key: bytes) -> str:
        """Decripta atributos do arquivo para obter o nome"""
        try:
            # Padding para múltiplo de 16
            if len(data) % 16:
                data += b'\x00' * (16 - len(data) % 16)
            
            cipher = AES.new(key, AES.MODE_CBC, iv=b'\x00' * 16)
            decrypted = cipher.decrypt(data)
            
            # Remover padding e encontrar JSON
            decrypted = decrypted.rstrip(b'\x00')
            
            # Procurar por MEGA{"n":"filename"}
            if decrypted.startswith(b'MEGA'):
                json_str = decrypted[4:].decode('utf-8', errors='ignore')
                # Encontrar o final do JSON
                brace_count = 0
                end_pos = 0
                for i, c in enumerate(json_str):
                    if c == '{':
                        brace_count += 1
                    elif c == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end_pos = i + 1
                            break
                
                if end_pos > 0:
                    json_str = json_str[:end_pos]
                    attr = json.loads(json_str)
                    return attr.get('n', '')
            
            return None
        except:
            return None
    
    def _download_and_decrypt(self, url: str, filepath: str, key: bytes, iv: bytes, 
                               total_size: int, callback=None) -> dict:
        """Baixa e decripta o arquivo"""
        try:
            start_time = time.time()
            downloaded = 0
            chunk_size = 1024 * 1024  # 1MB chunks
            
            # Criar cipher para CTR mode
            ctr = Counter.new(128, initial_value=int.from_bytes(iv, 'big'))
            cipher = AES.new(key, AES.MODE_CTR, counter=ctr)
            
            response = requests.get(url, stream=True, timeout=60)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if self.cancelled:
                        f.close()
                        if os.path.exists(filepath):
                            os.remove(filepath)
                        return {'success': False, 'error': 'Download cancelado'}
                    
                    if chunk:
                        # Decriptar chunk
                        decrypted_chunk = cipher.decrypt(chunk)
                        f.write(decrypted_chunk)
                        downloaded += len(chunk)
                        
                        # Callback de progresso
                        if callback:
                            elapsed = time.time() - start_time
                            speed = downloaded / elapsed if elapsed > 0 else 0
                            callback(downloaded, total_size, speed)
            
            return {'success': True}
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 509:
                return {'success': False, 'error': 'Limite de transferência atingido'}
            return {'success': False, 'error': f'Erro HTTP: {e.response.status_code}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _find_latest_file(self) -> str:
        """Encontra o arquivo mais recente na pasta de downloads"""
        try:
            files = [
                os.path.join(self.download_folder, f)
                for f in os.listdir(self.download_folder)
                if os.path.isfile(os.path.join(self.download_folder, f))
            ]
            if not files:
                return None
            return max(files, key=os.path.getmtime)
        except:
            return None
    
    def get_file_info(self, url: str) -> dict:
        """Obtém informações do arquivo"""
        return {
            'available': True,
            'filename': None,
            'size': 0,
            'note': 'Informações serão obtidas durante o download'
        }
    
    def cancel(self):
        """Cancela o download atual"""
        self.cancelled = True
