"""
Classe base para downloaders
"""

import os
import re
import requests
from abc import ABC, abstractmethod
from urllib.parse import urlparse, unquote


class BaseDownloader(ABC):
    """Classe base abstrata para todos os downloaders"""
    
    # Padrões de URL que este downloader suporta
    URL_PATTERNS = []
    
    # Nome do host
    HOST_NAME = "Unknown"
    
    def __init__(self, download_folder: str):
        self.download_folder = download_folder
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
    
    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Verifica se este downloader pode processar a URL"""
        for pattern in cls.URL_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                return True
        return False
    
    @abstractmethod
    def download(self, url: str, callback=None, options: dict = None) -> dict:
        """
        Executa o download
        
        Args:
            url: URL para download
            callback: Função de callback para progresso (downloaded, total, speed)
            options: Opções adicionais
        
        Returns:
            dict com 'success', 'filepath', 'filename', 'size', 'error'
        """
        pass
    
    @abstractmethod
    def get_file_info(self, url: str) -> dict:
        """
        Obtém informações do arquivo sem baixar
        
        Returns:
            dict com 'filename', 'size', 'available'
        """
        pass
    
    def extract_filename_from_url(self, url: str) -> str:
        """Extrai nome do arquivo da URL"""
        parsed = urlparse(url)
        path = unquote(parsed.path)
        filename = os.path.basename(path)
        
        if not filename or '.' not in filename:
            return None
        
        return self.sanitize_filename(filename)
    
    def extract_filename_from_headers(self, headers: dict) -> str:
        """Extrai nome do arquivo dos headers HTTP"""
        content_disposition = headers.get('Content-Disposition', '')
        
        # Tentar extrair filename do Content-Disposition
        if 'filename=' in content_disposition:
            match = re.search(r'filename[*]?=["\']?([^"\';]+)["\']?', content_disposition)
            if match:
                return self.sanitize_filename(unquote(match.group(1)))
        
        return None
    
    def sanitize_filename(self, filename: str) -> str:
        """Remove caracteres inválidos do nome do arquivo"""
        # Caracteres inválidos no Windows
        invalid_chars = r'[<>:"/\\|?*]'
        filename = re.sub(invalid_chars, '_', filename)
        
        # Limitar tamanho
        if len(filename) > 200:
            name, ext = os.path.splitext(filename)
            filename = name[:200-len(ext)] + ext
        
        return filename.strip()
    
    def get_unique_filepath(self, filename: str) -> str:
        """Retorna um caminho único para o arquivo"""
        filepath = os.path.join(self.download_folder, filename)
        
        if not os.path.exists(filepath):
            return filepath
        
        # Adicionar número se arquivo já existe
        name, ext = os.path.splitext(filename)
        counter = 1
        
        while os.path.exists(filepath):
            new_filename = f"{name}_{counter}{ext}"
            filepath = os.path.join(self.download_folder, new_filename)
            counter += 1
        
        return filepath
