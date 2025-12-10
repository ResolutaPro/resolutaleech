# ResolutaLeech

Alternativa moderna ao Rapidleech desenvolvida em Python com Flask.

## Características

- **Interface moderna** - UI responsiva com TailwindCSS
- **Downloads diretos** - Suporte a qualquer link HTTP/HTTPS
- **MEGA.nz** - Suporte via megatools
- **Progresso em tempo real** - Acompanhe velocidade e progresso
- **Gerenciamento de arquivos** - Liste, baixe e delete arquivos
- **Multi-thread** - Downloads simultâneos em background

## Requisitos

- Python 3.8+
- megatools (opcional, para MEGA.nz)

## Instalação

```bash
# Clonar ou copiar para o diretório
cd resolutaleech

# Criar ambiente virtual (recomendado)
python -m venv venv
venv\Scripts\activate  # Windows
# ou
source venv/bin/activate  # Linux/Mac

# Instalar dependências
pip install -r requirements.txt
```

## Uso

```bash
# Iniciar servidor
python app.py

# Acessar no navegador
http://localhost:5000
```

## Instalar Megatools (opcional)

Para downloads do MEGA.nz:

### Windows
1. Baixe de: https://megatools.megous.com/
2. Extraia para `C:\megatools\`
3. Adicione ao PATH ou deixe na pasta padrão

### Linux
```bash
# Ubuntu/Debian
sudo apt install megatools

# Arch
sudo pacman -S megatools
```

## Estrutura do Projeto

```
resolutaleech/
├── app.py                 # Aplicação principal Flask
├── requirements.txt       # Dependências Python
├── README.md             # Este arquivo
├── downloads/            # Pasta de arquivos baixados
├── templates/
│   └── index.html        # Interface web
└── downloaders/
    ├── __init__.py
    ├── base.py           # Classe base
    ├── manager.py        # Gerenciador de downloads
    ├── direct.py         # Downloads HTTP diretos
    └── mega.py           # Downloads MEGA.nz
```

## API Endpoints

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/` | Página principal |
| POST | `/api/download` | Iniciar download |
| GET | `/api/download/<id>` | Status do download |
| DELETE | `/api/download/<id>` | Cancelar download |
| GET | `/api/downloads` | Listar downloads |
| GET | `/api/files` | Listar arquivos |
| DELETE | `/api/files/<name>` | Deletar arquivo |
| GET | `/api/system` | Info do sistema |
| GET | `/api/hosts` | Hosts suportados |

## Hosts Suportados

- **Direct Link** - Qualquer URL HTTP/HTTPS
- **MEGA.nz** - Requer megatools instalado

## Licença

MIT License
