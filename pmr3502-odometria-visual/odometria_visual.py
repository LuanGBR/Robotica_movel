import cv2
import numpy as np
import traceback

class ProcessamentoVisao():

      def __init__(self, largura, altura, treshold):
            # Complete a inicialização do objeto
            pass


      def primeiroQuadro(self, quadro):
            # Complete a inicialização do primeiro quadro
            pass

      def estimaMovimento(self, quadro):
            # Complete a estimativa de movimento
            return (1.0, 1.0, 1.0)



class EstimativaPosicao():

      def __init__(self):
            self._x = 0.0
            self._y = 0.0
            self._t = 0.0
            self._video = cv2.VideoCapture(0)
            self._video.set(cv2.CAP_PROP_FRAME_WIDTH, 1280);
            self._video.set(cv2.CAP_PROP_FRAME_HEIGHT, 720);
            rc, img = self._video.read()
            self._processamento = ProcessamentoVisao(1280, 720, 800)
            self._processamento.primeiroQuadro(img)

      def atualizaPosicao(self):
            rc, img = self._video.read()

            if not rc:
                return (0.0, 0.0, 0.0)

            # Estima o movimento
            mov_x, mov_y, mov_t = self._processamento.estimaMovimento(img)

            # Atualiza a posição
            self._x += mov_x*np.cos(self._t) - mov_y*np.sin(self._t)
            self._y += mov_y*np.cos(self._t) + mov_x*np.sin(self._t)
            self._t += mov_t

            return (self._x, self._y, self._t)