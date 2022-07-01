#!/usr/bin/python3

import selectors
import socket
import signal
import iio
import getopt
import sys

# Recupera dados da IMU e publica-os via tcp/ip
# Os dados são publicados em pacotes de 24 bytes reproduzindo o formato
# da IMU.
# Formato do pacote:
# 00 01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16 17 18 19 20 21 22 23
# [-ax] [-ay] [-az] [-rx] [-ry] [-rz] [---pad---] [------timestamp------]
# ax: aceleração em x (2 bytes big endian com sinal)
# ay: aceleração em y (2 bytes big endian com sinal)
# az: aceleração em z (2 bytes big endian com sinal)
# rx: vel. angular em x (2 bytes big endian com sinal)
# ry: vel. angular em y (2 bytes big endian com sinal)
# rz: vel. angular em z (2 bytes big endian com sinal)
# Pad: bytes a ignorar
# timestamp: horário da coleta em nanossegundos (8 bytes little endian sem sinal)

class IOProcessor():

    def __init__(self, addr, port):
        self._addr = addr
        self._port = port
        self._sel = selectors.DefaultSelector()
        self._connections = set()
        self._sock = None
        self._keepRunning = False
        self._oldsignal = None
        self._mpu = None
        self._buff = None
        self._newData = False
        self._lastData = None

    def start(self):
        self._sock = socket.socket()
        self._sock.bind((self._addr, self._port))
        self._sock.listen(100)
        self._sock.setblocking(False)
        self._sel.register(self._sock, selectors.EVENT_READ, self._accept)
        self._keepRunning = True
        # Ativa um tratador de sinal para receber SIGINT e terminar o processamento
        self._oldsignal = signal.signal(signal.SIGINT, self._sighandler)
        localiioctx = iio.Context()
        for dev in localiioctx.devices:
            if dev.name=='mpu6050':
                self._mpu = dev
        if self._mpu is None:
            raise Exception("MPU6050 não encontrado!")
        channelmap = {}
        for c in self._mpu.channels:
            channelmap[c.id] = c
        channelmap['accel_x'].enabled = True
        channelmap['accel_y'].enabled = True
        channelmap['accel_z'].enabled = True
        channelmap['anglvel_x'].enabled = True
        channelmap['anglvel_y'].enabled = True
        channelmap['anglvel_z'].enabled = True
        channelmap['timestamp'].enabled = True
        self._buff = iio.Buffer(self._mpu,1)
        self._sel.register(self._buff.poll_fd, selectors.EVENT_READ, self._readbuff)

    def stop(self):
        print("Encerrando...")
        for c in self._connections:
            c.close()
        self._coonections = set()
        if self._oldsignal:
            signal.signal(signal.SIGINT, self._oldsignal)
        self._oldsignal = None
        if self._sock:
            self._sel.unregister(self._sock)
            self._sock.close()
            self._sock = None
            self._keepRunning = False
        if self._mpu:
            self._mpu = None
        if self._buff:
            print("Cancelando buffer...")
            self._sel.unregister(self._buff.poll_fd)
            self._buff.cancel()
            self._buff = None
            print("Concluído.")

    def _readbuff(self, fd, mask):
        self._buff.refill()
        self._lastData = self._buff.read()
        self._newData = True

    def getNewData(self):
        ret = (self._newData, self._lastData)
        self._newData = False
        self._lastData = None
        return ret

    def started(self):
        return self._keepRunning

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, type, value, traceback):
        self.stop()
        return True

    def _accept(self, socket, mask):
        conn, addr = socket.accept()
        print('Conexão recebida:', conn, ' de:', addr)
        conn.setblocking(False)
        self._sel.register(conn, selectors.EVENT_READ, self._read)
        self._connections.add(conn)


    def _read(self, connection, mask):
        data = connection.recv(1)
        if not data:
            print('fechando', connection)
            self._sel.unregister(connection)
            self._connections.remove(connection)
            connection.close()

    def __del__(self):
        if self._sock:
            self._sel.unregister(self._sock)
            self._sock.close()

    def _sighandler(self, signum, frame):
        self._keepRunning = False
        print('Recebido sinal ', signum)

    def run(self):
        while self._keepRunning:
            events = self._sel.select(1)
            for key, mask in events:
                callback = key.data
                callback(key.fileobj, mask)
            newdata, data = self.getNewData()
            if newdata:
                for c in self._connections:
                    c.send(data)
        print("Execução encerrada, liberando recursos...")
        self.stop()

def mostra_uso():
    print('servicoimu.py -p <porta do servidor> -e <endereco externo do servidor>')

def main():
    porta_servico = 1234
    endereco_servidor = "localhost"
    try:
        opts, args = getopt.getopt(sys.argv[1:],"h:pe:")
        for opt, arg in opts:
            print(opt)
            if opt == '-h':
                mostra_uso()
                return 0
            elif opt in ("-p",):
                porta_servico = int(arg)
            elif opt in ("-e",):
                endereco_servidor = arg
    except:
      mostra_uso()
      return 2

    print("Endereço do servidor: " + endereco_servidor)
    print("Porta do servidor: " + str(porta_servico))

    with IOProcessor(endereco_servidor, porta_servico) as proc:
        proc.run()

    return 0

if __name__=="__main__":
    sys.exit(main())
