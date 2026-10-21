# Upload / Download

Site Python para importar diretamente na ShardCloud. Sem dependências externas.

- `GET /upload`: página para enviar um ficheiro.
- `POST /upload?name=ficheiro.bin`: upload do conteúdo bruto.
- `GET /download`: descarrega o último ficheiro enviado.

Cada upload substitui o ficheiro anterior. O limite é de 2 GiB. O servidor lê e escreve em blocos, sem carregar o ficheiro inteiro na memória.

## Iniciar

Usa o `Dockerfile` deste repositório na ShardCloud. A aplicação escuta em `0.0.0.0:$PORT` (8000 por omissão). Não são necessárias variáveis para upload ou armazenamento.

Localmente: `python server.py` e depois abre `http://localhost:8000/upload`.

O ficheiro é guardado no disco do container, junto da aplicação. Se a ShardCloud recriar o container, esse ficheiro pode desaparecer. O proxy da ShardCloud também precisa de aceitar pedidos grandes para uploads acima de 400 MB.

Testes: `python -m unittest discover -s tests -v`
