#!/usr/bin/python3
import aiohttp
from aiohttp import web
import sys
import os
import motorctrl
import subprocess
import getopt

pag_template = r"""<!DOCTYPE HTML>
<html>
	<head>
		<title>Joy 2</title>
		<meta charset="utf-8">
		<style>
*
{{
	box-sizing: border-box;
}}
body
{{
	margin: 0px;
	padding: 0px;
	font-family: monospace;
}}
.float-child {{
    width: 50%;
    float: left;
}}
    </style>
		<script src="static/joy.js"></script>
	</head>
	<body>
        <center>
            <img src="http://{endr}:{porta}/?action=stream" />
            <div class="float-container">
                <div class="float-child">
                    <div id="joy1Div" style="width:400px;height:400px;margin:50px"></div>
                </div>
                <div class="float-child">
                    <div id="joy2Div" style="width:400px;height:400px;margin:50px"></div>
                </div>
            </div>
        </center>
		<script type="text/javascript">
var Joy1 = new JoyStick('joy1Div', {{"max_x": 0, "min_x": 0}} );
var Joy2 = new JoyStick('joy2Div', {{"max_x": 0, "min_x": 0}} );
var wsUri = (window.location.protocol=='https:'&&'wss://'||'ws://')+window.location.host+"/wsctrl";
var control_link = new WebSocket(wsUri);
setInterval(function(){{
            control_link.send(""+Joy1.GetY()+","+Joy2.GetY());
        }}, 50);
		</script>
	</body>
</html>
"""

pag = None
ctrl = None

async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    async for msg in ws:
        if msg.type == aiohttp.WSMsgType.TEXT:
            try:
                components = msg.data.split(",")
                x = float(components[0])
                y = float(components[1])
                ctrl.set_lr(x,y)
            finally:
                pass

        elif msg.type == aiohttp.WSMsgType.ERROR:
            print('conexão ws encerrada com erro %s' %
                  ws.exception())
    ctrl.set_lr(0,0)
    print('conexão ws encerrada')

    return ws


async def pagina(request):
    return web.Response(text=pag, content_type="text/html")

async def favicon(request):
    return web.FileResponse('./static/5x35n5.svg')

def main():
    porta_mjpeg = "8008"
    endereco_servidor = None
    try:
      opts, args = getopt.getopt(sys.argv[1:],"h:pe:")
    except getopt.GetoptError:
      print('test.py -p <porta do servidor mjpeg> -e <endereco externo do servidor>')
      sys.exit(2)
    for opt, arg in opts:
        print(opt)
        if opt == '-h':
            print('test.py -p <porta do servidor mjpeg> -e <endereco externo do servidor>')
            sys.exit()
        elif opt in ("-p",):
            porta_mjpeg = arg
        elif opt in ("-e",):
            endereco_servidor = arg

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
        endereco_servidor = ret.stdout.decode("utf-8")

    print("Endereço do servidor mjpeg: " + endereco_servidor)
    print("Porta do servidor mjpeg: " + porta_mjpeg)

    global ctrl
    global pag
    ctrl = motorctrl.motorCtrl()


    pag = pag_template.format(endr=endereco_servidor, porta=porta_mjpeg)
    STATIC_PATH = os.path.join(os.path.dirname(__file__), "static")
    app = web.Application()
    app.router.add_routes([web.get('/', pagina)])
    app.router.add_routes([web.get('/favicon.ico', favicon)])
    app.router.add_routes([web.get('/wsctrl', websocket_handler)])
    app.router.add_static('/static/', STATIC_PATH, name='static')
    ctrl.initialize()
    web.run_app(app)
    ctrl.finalize()
    return 0


if __name__ == '__main__':
    sys.exit(main())
