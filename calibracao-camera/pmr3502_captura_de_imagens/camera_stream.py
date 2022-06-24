#!/usr/bin/python3
'''
	Author: Thiago Martins.
	"Inspirado" pelo servidor mjpeg feito por Igor Maculan
'''
import cv2
import logging
import os
import aiohttp
import asyncio
from aiohttp import web, MultipartWriter
import sys
import tempfile
import subprocess
import argparse

# Página principal
#   Só uma tag <img> com o endereço do serviço mjpeg
#   e um botão que envia um comando websocket
pag_template = r"""<!DOCTYPE HTML>
<html>
	<head>
		<title>Captura de video</title>
		<meta charset="utf-8">
	</head>
	<body>
        <center>
            <div><img src="http://{endr}:{porta}/image" /></div>
            <div><button id="botao_capturar" type="button">Capturar Imagem</button></div>
        </center>
		<script type="text/javascript">
var wsUri = (window.location.protocol=='https:'&&'wss://'||'ws://')+window.location.host+"/wsctrl";
var control_link = new WebSocket(wsUri);
document.getElementById("botao_capturar").onclick = function() {{envia_comando_capturar()}};
function envia_comando_capturar(){{
    control_link.send("capturar");
}}
		</script>
	</body>
</html>
"""


# Colhe quadros da câmera, codifica-os em jpeg
#   e grava-os em app['keep_alive']
async def capture_image(app):
    mjpeg_connections = app['mjpeg_connections']
    capture = cv2.VideoCapture(0)
    capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1280);
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 720);
    try :
        while app['keep_alive']:
            await asyncio.sleep(0)
            rc, img = capture.read()
            if not rc:
                continue
            frame = cv2.imencode('.jpg', img)[1].tobytes()
            app['last_frame'] = frame
    except asyncio.CancelledError:
        pass


# Processa uma requisiçao mjpeg
#   Esta função consume os frames
#   escritos em app['last_frame']
#   FIXME: Essa arquitetura faz com que o
#       serviço fique "preso" a um cliente
#       e só possa encerrar depois que a conexão
#       for fechada
async def mjpeg_request(request):
    my_boundary = 'image-boundary'
    response = web.StreamResponse(
        status=200,
        reason='OK',
        headers={
            'Content-Type': 'multipart/x-mixed-replace;boundary={}'.format(my_boundary)
        }
    )
    frame_anterior = None
    await response.prepare(request)
    while request.app['keep_alive']:
        await asyncio.sleep(0)
        frame = request.app['last_frame']
        if frame is None or frame is frame_anterior:
            continue
        with MultipartWriter('image/jpeg', boundary=my_boundary) as mpwriter:
            mpwriter.append(frame, {
                'Content-Type': 'image/jpeg'
            })
            # Evita envio de quadros repetidos
            frame_anterior = frame
            try:
                await mpwriter.write(response, close_boundary=False)
            except ConnectionResetError :
                # Desconexão
                break
        await response.write(b"\r\n")

# Responde a uma solicitação de gravação
async def websocket_handler(request):
    ws = web.WebSocketResponse()
    diretorio = request.app['capt_path']
    await ws.prepare(request)

    async for msg in ws:
        if msg.type == aiohttp.WSMsgType.TEXT:
            #grava o último quadro
            frame = request.app['last_frame']
            if frame is None:
                return
            with tempfile.NamedTemporaryFile(suffix=".jpg", prefix ="captura", delete=False, dir=diretorio) as file:
                print("Capturando em " + file.name)
                file.write(frame)

        elif msg.type == aiohttp.WSMsgType.ERROR:
            print('conexão ws encerrada com erro %s' %
                  ws.exception())
    print('conexão ws encerrada')
    return ws

async def root_handler(request):
    return aiohttp.web.Response(text=request.app['root_pag'], content_type="text/html")

async def inicializa_tarefas(app):
    app['capture_task'] = asyncio.create_task(capture_image(app))

async def encerra_tarefas(app):
    app['keep_alive'] = False
    app['capture_task'].cancel()
    await app['capture_task']

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('-e', help="Endereço externo do servidor")
    parser.add_argument('-p', help="Porta do servidor", default="8080")
    parser.add_argument('-d', help="Diretório para capturas", default="./capturas")

    args = parser.parse_args()
    diretorio_capturas = args.d
    endereco_servidor = args.e
    porta_servico = args.p

    if endereco_servidor == None:
        # Tenta determinar endereço via hostname
        # Primeiro com o fully-qualified name
        ret = subprocess.run(["/usr/bin/hostname", "-f"], capture_output=True)
        if ret.returncode !=0:
            # Falhou, vamos tentar o nome simples
            print("Aviso! Impossível determinar o endereço do servidor via hosthame -f")
            ret = subprocess.run(["/usr/bin/hostname"], capture_output=True)
        if ret.returncode !=0:
            print("Erro: Impossível determinar o endereço do servidor!")
            return 1
        endereco_servidor = ret.stdout.decode("utf-8").rstrip()

    print("Endereço do servidor mjpeg: " + endereco_servidor)
    print("Porta do servidor mjpeg: " + porta_servico)
    print("Diretório para imagens capturadas: " + diretorio_capturas)

    # Verifica se o diretório existe, caso não exista, cria
    if not os.path.isdir(diretorio_capturas):
        print("Diretório para imagens capturadas não existe, criando.")
        try:
            os.mkdir(diretorio_capturas)
        except:
            print("Impossível criar o caminho " + diretorio_capturas + ". Encerrando.")
            return -1


    print("Url do servico: http://" + endereco_servidor + ":" + porta_servico + "/")
    app = web.Application()
    app['mjpeg_connections'] = {}
    app['keep_alive'] = True
    app['root_pag'] = pag_template.format(endr=endereco_servidor, porta=porta_servico)
    app['last_frame'] = None
    app['capt_path'] = diretorio_capturas
    app.on_startup.append(inicializa_tarefas)
    app.on_cleanup.append(encerra_tarefas)
    # Página raiz
    app.router.add_route("GET", "/", root_handler)
    # Fluxo mjpeg
    app.add_routes([web.get('/image', mjpeg_request)])
    # Comando para gravar
    app.router.add_routes([web.get('/wsctrl', websocket_handler)])
    web.run_app(app, host=endereco_servidor, port=porta_servico)

    return 0


if __name__ == '__main__':
    sys.exit(main())

