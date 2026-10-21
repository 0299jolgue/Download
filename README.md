# Site de upload/download

Servidor Python com apenas duas rotas:

- `GET /upload`: página para escolher um ficheiro. `POST /upload`: envia-o.
- `GET /download`: descarrega o último ficheiro enviado.

O upload exige a variável de ambiente `UPLOAD_KEY`. O download é público. O ficheiro é escrito em blocos no disco, sem carregar tudo na memória. O limite configurado é 2 GiB.

## ShardCloud

Usa o `Dockerfile` incluído. Configura `UPLOAD_KEY` com uma chave longa, por exemplo gerada com `python -c 'import secrets; print(secrets.token_urlsafe(32))'`. Configura também um volume persistente montado em `/data`; o container usa `DATA_DIR=/data`. O processo escuta em `0.0.0.0:$PORT`, com `PORT=8000` por omissão.

O proxy da ShardCloud tem de aceitar pedidos de pelo menos 400 MB e permitir tempo suficiente para o upload. Sem isso, o pedido pode ser bloqueado antes de chegar à aplicação. Usa HTTPS no endereço público.

## Local

```bash
export UPLOAD_KEY='uma-chave-longa'
python server.py
```

Abre `http://localhost:8000/upload`. O ficheiro fica em `./data` se `DATA_DIR` não estiver definido. `http://localhost:8000/download` devolve o mesmo conteúdo enviado.

Testes: `python -m unittest discover -s tests -v`
