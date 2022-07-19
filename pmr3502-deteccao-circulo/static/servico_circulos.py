#!/usr/bin/python3
'''
	Author: Thiago Martins.
'''
import cv2
import logging
import os
import aiohttp
import asyncio
from asyncio import Queue
from aiohttp import web, MultipartWriter
import sys
import tempfile
import subprocess
import argparse
import numpy as np
import time


# Estima o momento do boot
def getboottime():
    times = []
    for i in range(40):
        t2 = time.clock_gettime(time.CLOCK_REALTIME)
        t1 = time.clock_gettime(time.CLOCK_MONOTONIC)
        times.append(t2-t1)
        t1 = time.clock_gettime(time.CLOCK_MONOTONIC)
        t2 = time.clock_gettime(time.CLOCK_REALTIME)
        times.append(t2-t1)

    times.sort()
    tot = 0.0
    for i in range(15,25):
        tot += times[i]
    return tot/10



class Detector():
    def __init__(self, min_radius, max_radius, scale=1.0):
        # Parâmetros minRadius e maxRadius
        self._min_radius = np.int32(np.floor(min_radius*scale))
        self._max_radius = np.int32(np.ceil(max_radius*scale))

        self._vid = cv2.VideoCapture(0, cv2.CAP_V4L2)
        self._vid.set(cv2.CAP_PROP_AUTOFOCUS,0)
        self._vid.set(cv2.CAP_PROP_FOCUS,0)
        self._vid.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self._vid.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self._boot_time = getboottime()*1000000000
        self._prev_frame_ts = time.time()

        # TODO:
        # Inicialize o mapa de reprojeção da imagem
        #   e a matriz de transformação de coordenadas de imagem para robô
        self._itrans_matrix = None  # Substitua None pela matriz que transforma coordenadas da imagem
                                    # em coordenadas do robô

    def detecta(self):
        ret, frame = self._vid.read()
        ts = int((self._vid.get(cv2.CAP_PROP_POS_MSEC)*1000000)+self._boot_time)
        # Imagem em tons de cinza
        cinza = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # TODO:
        # 1. Remapeie a imagem
        # 2. Aplique cv2.medianBlur(imagem, 5)
        # 3. Detecte círculos com HoughCircles.
        #       use method = cv2.HOUGH_GRADIENT, param1=100 e param2=15
        #       Os parâmetros minRadius e maxRadius estão no objeto

        circles = None  # Substitua pelo resultado da chamada a HoughCircles
        coordenadas = []
        if circles is not None:
            for c in circles[0, :]:
                coordnumpy = self._itrans_matrix.dot(np.float32([c[0], c[1], 1.0]))
                coordenadas.append([float(coordnumpy[0]), float(coordnumpy[1])])
            ncircles = len(circles[0, :])
        else:
            ncircles = 0
        t = time.time()
        print("n: " + str(ncircles) + " FPS: " + str(1/(t-self._prev_frame_ts)) + " lag: " + str(time.time() - ts/1000000000), end="\r")
        self._prev_frame_ts = t
        return coordenadas, ts

class ServicoDetectorCirculos():

    def __init__(self, app, endereco_servidor, porta_servidor, raio_minimo, raio_maximo):
        self._app = app
        self._endereco_servidor = endereco_servidor
        self._porta_servidor = porta_servidor
        self._app['app_object'] = self
        # Tarefas de inicializacao e encerramento
        self._app.on_startup.append(self._inicializa_tarefas)
        self._app.on_cleanup.append(self._encerra_tarefas)
        self._app.router.add_routes([web.get('/wsctrl', self._websocket_handler)])
        self._app.router.add_routes([web.get('/', self._pagina)])
        self._keep_alive = True
        self._worker_task = None
        self._connections = set()
        self._detector = Detector(raio_minimo, raio_maximo)

    def run(self):
        web.run_app(self._app, host=self._endereco_servidor, port=self._porta_servidor)

    async def _pagina(self, request):
        return web.FileResponse('./static/showcircles.html')

    async def _inicializa_tarefas(self, app):
        self._worker_task = asyncio.create_task(ServicoDetectorCirculos._worker(self._app))

    async def _encerra_tarefas(self, app):
        self._keep_alive = False
        if self._worker_task is not None:
            self._worker_task.cancel()
            await self._worker_task
            self._worker_task = None

    # Responde a uma conexão web socket
    async def _websocket_handler(self, request):
        messages = Queue()
        self._connections.add(messages)
        ws = web.WebSocketResponse(receive_timeout=0)
        await ws.prepare(request)
        try:
            while self._keep_alive and not ws.closed:
                try:
                    from_client = await ws.receive(timeout = 0)
                    if from_client.type==web.WSMsgType.CLOSE:
                        break
                    elif from_client.type==web.WSMsgType.TEXT:
                        pass
                except asyncio.TimeoutError as e:
                    pass

                msg = await messages.get()
                messages.task_done()
                await ws.send_json(msg)
        except Exception as e:
            print("ERROR")
            print(e.__class__.__qualname__)
        self._connections.remove(messages)


    # Detecta os círculos
    async def _worker(app):
        self = app['app_object']
        while self._keep_alive:
            await asyncio.sleep(0)
            coordenadas, timestamp = self._detector.detecta()
            dados = {"timestamp": timestamp, "coordenadas" : coordenadas }
            for connection in self._connections:
                await connection.put(dados)

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('-e', help="Endereço externo do servidor")
    parser.add_argument('-p', help="Porta do servidor", default="8087")
    parser.add_argument('-a', help="Raio máximo do círculo", default="16")
    parser.add_argument('-i', help="Raio mínimo do círculo", default="9")

    args = parser.parse_args()
    endereco_servidor = args.e
    porta_servico = args.p
    raio_minimo = args.i
    raio_maximo = args.a

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

    print("Endereço do servidor: " + endereco_servidor)
    print("Porta do servidor: " + porta_servico)


    serviceObj = ServicoDetectorCirculos(web.Application(), endereco_servidor, porta_servico, int(raio_minimo), int(raio_maximo))

    serviceObj.run()

    return 0


if __name__ == '__main__':
    sys.exit(main())
