# Explicação do ResolutaLeech

## Objetivo
Criar uma alternativa moderna ao Rapidleech em Python, com interface web responsiva e suporte a múltiplos hosts de download.

## Arquitetura

### Backend (Flask)
- **app.py**: Servidor Flask com API REST
- **downloaders/**: Módulo de gerenciamento de downloads

### Frontend
- **templates/index.html**: SPA com TailwindCSS
- Interface responsiva e moderna
- Atualização em tempo real via polling

### Downloaders
- **base.py**: Classe abstrata com métodos comuns
- **manager.py**: Orquestra downloads em threads separadas
- **direct.py**: Downloads HTTP/HTTPS genéricos
- **mega.py**: Downloads MEGA.nz via megatools

## Funcionalidades

1. **Downloads diretos**: Qualquer URL HTTP/HTTPS
2. **MEGA.nz**: Via megatools (detectado automaticamente)
3. **Progresso em tempo real**: Velocidade, porcentagem, tamanho
4. **Gerenciamento de arquivos**: Listar, baixar, deletar
5. **Info do sistema**: Espaço em disco, downloads ativos

## API REST

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/download` | POST | Iniciar download |
| `/api/download/<id>` | GET | Status do download |
| `/api/download/<id>` | DELETE | Cancelar download |
| `/api/downloads` | GET | Listar todos |
| `/api/files` | GET | Listar arquivos |
| `/api/files/<name>` | DELETE | Deletar arquivo |
| `/api/system` | GET | Info do sistema |

## Motivação
- Rapidleech é antigo e tem problemas com PHP 8+
- Python oferece melhor suporte a threading e bibliotecas modernas
- Interface moderna melhora experiência do usuário
- Arquitetura modular facilita adicionar novos hosts
