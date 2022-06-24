import RPi.GPIO as GPIO

class motorCtrl:
    a = ''
    b = ''

    def _init_(self):
        pass

    def initialize(self):
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(32, GPIO.OUT, initial = GPIO.LOW)
        GPIO.setup(33, GPIO.OUT, initial = GPIO.LOW)
        GPIO.setup(35, GPIO.OUT, initial = GPIO.LOW)
        GPIO.setup(38, GPIO.OUT, initial = GPIO.LOW)
        self.a = GPIO.PWM(32, 50)
        self.b = GPIO.PWM(33, 50)
        self.a.start(0)
        self.b.start(0)
        # Inicialize o controle do motor
        print("motorCtrl.initialize()")

    def finalize(self):
        # Finalize o controle do motor (lembre-se de parar os motores!)
        GPIO.output(35, GPIO.LOW )
        GPIO.output(38, GPIO.LOW )
        self.a.stop()
        self.b.stop()
        GPIO.cleanup()    
        print("motorCtrl.finalize()")
        quit()

    def set_lr(self, l, r):
        # Aplica comandos nos motores:
        #   l é o valor (de -100 a 100) para o motor esquerdo
        #   r é o valor (de -100 a 100) para o motor esquerdo
        l = 100 if l>100 else -100 if l<-100 else l
        r = 100 if r>100 else -100 if r<-100 else r
        aSet = GPIO.HIGH if r >= 0 else GPIO.LOW
        bSet = GPIO.HIGH if l >= 0 else GPIO.LOW
        GPIO.output(32, aSet)
        GPIO.output(38, aSet)
        GPIO.output(33, bSet)
        GPIO.output(35, bSet)
        self.a.ChangeDutyCycle(100-r if r>= 0 else -r)
        self.b.ChangeDutyCycle(100-l if l>= 0 else -l)


        print("motorCtrl.set_lr(l={}, r={})".format(l, r))
        pass
