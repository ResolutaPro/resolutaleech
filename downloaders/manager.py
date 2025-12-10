"""
Gerenciador central de downloads
"""

import os
import uuid
import threading
import time
from datetime import datetime
from typing import Dict, Optional, Callable

from .direct import DirectDownloader
from .mega import MegaDownloader


class DownloadManager:
    """Gerencia todos os downloads ativos e histórico"""
    
    def __init__(self, download_folder: str):
        self.download_folder = download_folder
        self.downloads: Dict[str, dict] = {}
        self.threads: Dict[str, threading.Thread] = {}
        self.lock = threading.Lock()
        
        # Registrar downloaders disponíveis
        self.downloaders = [
            MegaDownloader(download_folder),
            DirectDownloader(download_folder),  # Fallback para links diretos
        ]
    
    def add_download(self, url: str, options: dict = None) -> str:
        """Adiciona um novo download à fila"""
        download_id = str(uuid.uuid4())[:8]
        
        # Encontrar downloader apropriado
        downloader = self._get_downloader(url)
        if downloader is None:
            # Usar downloader direto como fallback
            downloader = self.downloaders[-1]
        
        # Criar registro do download
        download_info = {
            'id': download_id,
            'url': url,
            'status': 'starting',
            'progress': 0,
            'downloaded': 0,
            'total': 0,
            'speed': 0,
            'filename': options.get('filename', '') if options else '',
            'filepath': '',
            'host': downloader.HOST_NAME,
            'error': None,
            'started_at': datetime.now().isoformat(),
            'completed_at': None,
            'options': options or {},
        }
        
        with self.lock:
            self.downloads[download_id] = download_info
        
        # Iniciar download em thread separada
        thread = threading.Thread(
            target=self._download_worker,
            args=(download_id, url, downloader, options),
            daemon=True
        )
        self.threads[download_id] = thread
        thread.start()
        
        return download_id
    
    def _download_worker(self, download_id: str, url: str, downloader, options: dict):
        """Worker que executa o download em background"""
        try:
            self._update_status(download_id, 'downloading')
            
            # Callback para atualizar progresso
            def progress_callback(downloaded: int, total: int, speed: float):
                progress = (downloaded / total * 100) if total > 0 else 0
                with self.lock:
                    if download_id in self.downloads:
                        self.downloads[download_id].update({
                            'downloaded': downloaded,
                            'total': total,
                            'progress': round(progress, 1),
                            'speed': speed,
                        })
            
            # Executar download
            result = downloader.download(url, callback=progress_callback, options=options)
            
            if result.get('success'):
                with self.lock:
                    if download_id in self.downloads:
                        self.downloads[download_id].update({
                            'status': 'completed',
                            'progress': 100,
                            'filepath': result.get('filepath', ''),
                            'filename': result.get('filename', ''),
                            'total': result.get('size', 0),
                            'downloaded': result.get('size', 0),
                            'completed_at': datetime.now().isoformat(),
                        })
            else:
                self._update_status(download_id, 'error', result.get('error', 'Erro desconhecido'))
                
        except Exception as e:
            self._update_status(download_id, 'error', str(e))
    
    def _update_status(self, download_id: str, status: str, error: str = None):
        """Atualiza o status de um download"""
        with self.lock:
            if download_id in self.downloads:
                self.downloads[download_id]['status'] = status
                if error:
                    self.downloads[download_id]['error'] = error
    
    def _get_downloader(self, url: str):
        """Encontra o downloader apropriado para a URL"""
        for downloader in self.downloaders:
            if downloader.can_handle(url):
                return downloader
        return None
    
    def get_status(self, download_id: str) -> Optional[dict]:
        """Retorna o status de um download"""
        with self.lock:
            return self.downloads.get(download_id)
    
    def list_all(self) -> list:
        """Lista todos os downloads"""
        with self.lock:
            return list(self.downloads.values())
    
    def cancel(self, download_id: str) -> bool:
        """Cancela um download"""
        with self.lock:
            if download_id in self.downloads:
                self.downloads[download_id]['status'] = 'cancelled'
                return True
        return False
    
    def active_count(self) -> int:
        """Retorna número de downloads ativos"""
        with self.lock:
            return sum(1 for d in self.downloads.values() 
                      if d['status'] in ('starting', 'downloading'))
    
    def is_megatools_available(self) -> bool:
        """Verifica se megatools está disponível"""
        for downloader in self.downloaders:
            if isinstance(downloader, MegaDownloader):
                return downloader.megatools_available
        return False
    
    def get_supported_hosts(self) -> list:
        """Retorna lista de hosts suportados"""
        hosts = []
        for downloader in self.downloaders:
            hosts.append({
                'name': downloader.HOST_NAME,
                'patterns': downloader.URL_PATTERNS,
            })
        return hosts
