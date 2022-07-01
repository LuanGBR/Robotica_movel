import RPi.GPIO as GPIO

class motorCtrl:

    def __init__(self):
        pass

    def initialize(self):
        # Inicialize o controle do motor
        print("motorCtrl.initialize()")

    def finalize(self):
        # Finalize o controle do motor (lembre-se de parar os motores!)
        print("motorCtrl.finalize()")
        pass

    def set_lr(self, l, r):
        # Aplica comandos nos motores:
        #   l é o valor (de -100 a 100) para o motor esquerdo
        #   r é o valor (de -100 a 100) para o motor esquerdo
        print("motorCtrl.set_lr(l={}, r={})".format(l, r))
        pass




