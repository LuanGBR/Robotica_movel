import cv2
import numpy as np
import matplotlib.pyplot as plt

with open("/home/pi/Robotica_movel/matrices.txt","r") as file:
	matrices = eval(file.read())
	
	
mtx = np.array(matrices["mtx"])
dist = np.array(matrices["dist"])
rot = np.array(matrices["rot"])
trans = np.array(matrices["trans"])
mtx2 = np.array(matrices["mtx2"])
rodrigues, jacobiano = cv2.Rodrigues(rot)

def _Q():
	_P = np.array([[1, 0, 0, 0],[0, 1, 0, 0],[0, 0, 1, 0]])
	_G = np.eye(4)
	_G[0:3,0:3] = rodrigues
	_G[0:3,3] = trans.T
	_N = _P@_G
	_Nz = np.eye(3)
	_Nz[0:3, 0:2] = _N[0:3,0:2]
	_Nz[0:3, 2] = _N[:,3]
	Q = np.linalg.inv(_Nz)
	return Q
Q = _Q()

def _S():
	S = Q/Q[2][2]
	return S
S = _S()

def _mapaxy(dim=(4*297,4*210)):
	# valores obtidos com a função
	# imagem2global de um notebook anterior
	y_max = 333.522
	y_min = -320.964
	x_max = 439.217
	x_min = 62.422

	s = 1
    # matriz do campo visual do robô:
	C = np.array([[s,  0, -s*x_min],
				  [0, -s,  s*y_max],
				  [0,  0,		1]])
    
	return cv2.initUndistortRectifyMap(mtx, dist, S, C, dim, cv2.CV_32FC1)
mapa_x,mapa_y = _mapaxy()


def reprojeta(img):
	img_reprojetada = cv2.remap(img, mapa_x, mapa_y, cv2.INTER_LINEAR, cv2.BORDER_REPLICATE)
	return img_reprojetada

def recalibra_extrinseca(img, dim=(6,6)):
	img_cinza = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
	CALIB_OPTIONS = cv2.CALIB_CB_EXHAUSTIVE + cv2.CALIB_CB_LARGER + cv2.CALIB_CB_MARKER
	ret, corners, meta = cv2.findChessboardCornersSBWithMeta(img_cinza, dim, CALIB_OPTIONS)

	coords_globais = []
	DIST = 12.1
	x_central = 297.0/2
	y_central = 0.0
	for x in range(-6, 7, 1):
		for y in range(4, -5, -1):
			coords_globais.append((x_central+(x*DIST), y_central-(y*DIST), 0.0))

	ret, _rot, _trans = cv2.solvePnP(np.array(coords_globais), corners, mtx, dist)
	matrices["rot"] = _rot.tolist()
	matrices["trans"] = _trans.tolist()
	rot = _rot
	trans = _trans
	with open("/home/pi/Robotica_movel/matrices.txt","w") as file:
		file.write(repr(matrices))

def captura_e_recalibra_extrinseca():
	from IPython.display import clear_output
	vid = cv2.VideoCapture(0, cv2.CAP_V4L2)
	vid.set(cv2.CAP_PROP_AUTOFOCUS,0)
	vid.set(cv2.CAP_PROP_FOCUS,0)
	vid.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
	vid.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
	ret, frame = vid.read()
	clear_output(wait=True)
	frame = cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
	vid.release()
	recalibra_extrinseca(frame)

def imagem2global(p, lamb):
	p = cv2.undistortPoints(np.float32(p), mtx, dist)
	p = [*p[0][0], 1]
	return lamb*rot.T@p - rot.T@trans

def get_pontos_surf(img, treshold=15000):
    surf = cv2.xfeatures2d.SURF_create(60000)
    surf.setHessianThreshold(treshold)
    kp, desc = surf.detectAndCompute(img, None)
    return kp, desc

def get_transformada_entre_conjuntos_pontos(kp1, desc1, kp2, desc2):
    matches = matcher.knnMatch(desc2, desc1, k=2)
    np.array([kp[matches[i][0].queryIdx].pt for i in range(len(matches))])


