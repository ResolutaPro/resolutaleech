"""
Downloader para MEGA.nz
Suporta megatools e API nativa
"""

import os
import re
import time
import subprocess
import shutil
from .base import BaseDownloader


class MegaDownloader(BaseDownloader):
    """Downloader para MEGA.nz usando megatools"""
    
    URL_PATTERNS = [
        r'mega\.nz/file/',
        r'mega\.nz/folder/',
        r'mega\.nz/#!',
        r'mega\.nz/#F!',
        r'mega\.co\.nz/',
    ]
    
    HOST_NAME = "MEGA.nz"
    
    def __init__(self, download_folder: str):
        super().__init__(download_folder)
        self.megatools_path = self._find_megatools()
        self.megatools_available = self.megatools_path is not None
        self.cancelled = False
    
    def _find_megatools(self) -> str:
        """Encontra o executável do megatools"""
        # Possíveis caminhos
        possible_paths = [
            'megadl',  # No PATH
            'megadl.exe',
            shutil.which('megadl'),
            shutil.which('megadl.exe'),
            '/usr/bin/megadl',
            '/usr/local/bin/megadl',
            'C:\\megatools\\megadl.exe',
            'C:\\Program Files\\megatools\\megadl.exe',
            os.path.join(os.path.dirname(__file__), 'megatools', 'megadl.exe'),
        ]
        
        for path in possible_paths:
            if path and self._test_megatools(path):
                return path
        
        return None
    
    def _test_megatools(self, path: str) -> bool:
        """Testa se o megatools funciona"""
        try:
            result = subprocess.run(
                [path, '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0 or 'megatools' in result.stdout.lower()
        except:
            return False
    
    def download(self, url: str, callback=None, options: dict = None) -> dict:
        """Executa download do MEGA.nz"""
        self.cancelled = False
        options = options or {}
        
        if not self.megatools_available:
            return {
                'success': False,
                'error': 'Megatools não está instalado. Baixe em: https://megatools.megous.com/'
            }
        
        try:
            # Preparar comando
            cmd = [
                self.megatools_path,
                '--path', self.download_folder,
                url
            ]
            
            # Executar download
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            output_lines = []
            filename = None
            downloaded = 0
            total = 0
            start_time = time.time()
            
            # Ler saída em tempo real
            for line in iter(process.stdout.readline, ''):
                if self.cancelled:
                    process.terminate()
                    return {'success': False, 'error': 'Download cancelado'}
                
                output_lines.append(line)
                
                # Tentar extrair progresso
                # Formato: "file.zip: 50.00% - 25.5 MiB of 51.0 MiB"
                progress_match = re.search(
                    r'(\d+\.?\d*)%.*?(\d+\.?\d*)\s*(B|KB|KiB|MB|MiB|GB|GiB)\s*of\s*(\d+\.?\d*)\s*(B|KB|KiB|MB|MiB|GB|GiB)',
                    line
                )
                
                if progress_match:
                    percent = float(progress_match.group(1))
                    dl_size = float(progress_match.group(2))
                    dl_unit = progress_match.group(3)
                    total_size = float(progress_match.group(4))
                    total_unit = progress_match.group(5)
                    
                    downloaded = self._convert_to_bytes(dl_size, dl_unit)
                    total = self._convert_to_bytes(total_size, total_unit)
                    
                    if callback:
                        elapsed = time.time() - start_time
                        speed = downloaded / elapsed if elapsed > 0 else 0
                        callback(downloaded, total, speed)
                
                # Extrair nome do arquivo
                if not filename:
                    name_match = re.search(r'^(.+?):\s*\d+', line)
                    if name_match:
                        filename = name_match.group(1).strip()
            
            process.wait()
            
            if process.returncode != 0:
                output = ''.join(output_lines)
                if 'quota' in output.lower() or 'limit' in output.lower():
                    return {'success': False, 'error': 'Limite de transferência do MEGA atingido'}
                return {'success': False, 'error': f'Erro no megatools: {output}'}
            
            # Encontrar arquivo baixado
            if filename:
                filepath = os.path.join(self.download_folder, filename)
                if os.path.exists(filepath):
                    return {
                        'success': True,
                        'filepath': filepath,
                        'filename': filename,
                        'size': os.path.getsize(filepath),
                    }
            
            # Tentar encontrar arquivo mais recente
            filepath = self._find_latest_file()
            if filepath:
                return {
                    'success': True,
                    'filepath': filepath,
                    'filename': os.path.basename(filepath),
                    'size': os.path.getsize(filepath),
                }
            
            return {'success': False, 'error': 'Arquivo baixado não encontrado'}
            
        except subprocess.TimeoutExpired:
            return {'success': False, 'error': 'Timeout no download'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _convert_to_bytes(self, size: float, unit: str) -> int:
        """Converte tamanho para bytes"""
        multipliers = {
            'B': 1,
            'KB': 1024,
            'KiB': 1024,
            'MB': 1024 * 1024,
            'MiB': 1024 * 1024,
            'GB': 1024 * 1024 * 1024,
            'GiB': 1024 * 1024 * 1024,
        }
        return int(size * multipliers.get(unit, 1))
    
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
        """Obtém informações do arquivo (não suportado sem API)"""
        return {
            'available': True,
            'filename': None,
            'size': 0,
            'note': 'Informações detalhadas requerem download'
        }
    
    def cancel(self):
        """Cancela o download atual"""
        self.cancelled = True
