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
rodrigues,jacobiano = cv2.Rodrigues(rot)
# dim = matrices["dim"]

def _S():
	_P = np.array([[1, 0, 0, 0],[0, 1, 0, 0],[0, 0, 1, 0]])
	_G = np.eye(4)
	_G[0:3,0:3] = rodrigues
	_G[0:3,3] = trans
	_N = _P@_G
	_Nz = np.eye(3)
	_Nz[0:3, 0:2] = _N[0:3,0:2]
	_Nz[0:3, 2] = _N[:,3]
	_Q = np.linalg.inv(_Nz)
	S = _Q/_Q[2][2]
	return S
S = _S()

def _mapaxy(dim=(948,840)):
	return cv2.initUndistortRectifyMap(mtx, dist, S, mtx2, dim, cv2.CV_32FC1)
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

# 	print(corners)
# 	print("\n")
# 	print(coords_globais)
# 	print("\n")
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
	plt.imshow(frame)
	recalibra_extrinseca(frame)

def imagem2global(p, lamb):
    p = cv2.undistortPoints(np.float32(p), mtx, dist)
    p = [*p[0][0], 1]
    return lamb*R.T@p - R.T@t



