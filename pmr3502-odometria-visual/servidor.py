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
from asyncio import Queue
from aiohttp import web, MultipartWriter
import sys
import tempfile
import subprocess
import argparse
import numpy as np
from odometria_visual import EstimativaPosicao


class RobotPositionService():

    def __init__(self, app, endereco_servidor, porta_servidor):
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

    def run(self):
        web.run_app(self._app, host=self._endereco_servidor, port=self._porta_servidor)

    async def _pagina(self, request):
        return web.FileResponse('./static/showposition.html')

    async def _inicializa_tarefas(self, app):
        self._worker_task = asyncio.create_task(RobotPositionService._worker(self._app))

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
                        print(from_client.data)
                except asyncio.TimeoutError as e:
                    pass

                msg = await messages.get()
                messages.task_done()
                await ws.send_json(msg)
        except Exception as e:
            print("ERROR")
            print(e.__class__.__qualname__)
            raise e
        self._connections.remove(messages)


    # Colhe quadros da câmera, codifica-os em jpeg
    #   e grava-os em app['keep_alive']
    async def _worker(app):
        self = app['app_object']
        visao = EstimativaPosicao()
        while self._keep_alive:
            await asyncio.sleep(0.1)
            dados = list(visao.atualizaPosicao())
            for connection in self._connections:
                await connection.put(dados)



def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('-e', help="Endereço externo do servidor")
    parser.add_argument('-p', help="Porta do servidor", default="8080")

    args = parser.parse_args()
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

    print("Endereço do servidor: " + endereco_servidor)
    print("Porta do servidor: " + porta_servico)


    print("Url do servico: http://" + endereco_servidor + ":" + porta_servico + "/")


    serviceObj = RobotPositionService(web.Application(), endereco_servidor, porta_servico)

    serviceObj.run()

    return 0


if __name__ == '__main__':
    sys.exit(main())
