import cv2
import numpy as np
import traceback
import math

import sys
sys.path.insert(0, '../') #caminho relativo para a raiz
from utils import *

class ProcessamentoVisao():

      def __init__(self, largura, altura, treshold):
            self.largura = largura
            self.altura = altura
            self.treshold = treshold
            self.x = 0
            self.y = 0
            self.theta = 0

      def primeiroQuadro(self, quadro):
            self.quadro_anterior = reprojeta(quadro)

      def estimaMovimento(self, quadro):
            self.quadro = reprojeta(quadro)
            
            kp1, desc1 = get_pontos_surf(self.quadro)
            kp2, desc2 = get_pontos_surf(self.quadro_anterior)
            # TODO: conferir se existem ao menos 8 associações boas
            matriz, mascara = get_transformada_entre_conjuntos_pontos(kp1, desc1, kp2, desc2)
            
#             if len(mascara) < 5:
#                 print("aviso: mascara < 5")
            
#             print(matriz)
            
            self.quadro_anterior = self.quadro
#             return (10.0, 10.0, 1.0*math.pi/180)
            return (self.x, self.y, self.theta)



class EstimativaPosicao():

      def __init__(self):
            self._x = 0.0
            self._y = 0.0
            self._t = 0.0
            self._video = cv2.VideoCapture(0)
            self._video.set(cv2.CAP_PROP_FRAME_WIDTH, 1280);
            self._video.set(cv2.CAP_PROP_FRAME_HEIGHT, 720);
            rc, img = self._video.read()
            img = cv2.imread("../images/adp_v2.jpg")
            self._processamento = ProcessamentoVisao(1280, 720, 800)
            self._processamento.primeiroQuadro(img)

      def atualizaPosicao(self):
            rc, img = self._video.read()
            img = cv2.imread("../images/adp_v2.jpg")

            if not rc:
                  print("not rc")
                  return (0.0, 0.0, 0.0)

            # Estima o movimento
            mov_x, mov_y, mov_t = self._processamento.estimaMovimento(img)

            # Atualiza a posição
            self._x += mov_x*np.cos(self._t) - mov_y*np.sin(self._t)
            self._y += mov_y*np.cos(self._t) + mov_x*np.sin(self._t)
            self._t += mov_t

            return (self._x, self._y, self._t)