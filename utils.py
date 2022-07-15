import cv2
import numpy as np

with open("matrices.txt","r") as file:
	matrices = eval(file.read())
	
	
mtx = np.array(matrices["mtx"])
dist = np.array(matrices["dist"])	
rot = np.array(matrices["rot"])
trans = np.array(matrices["trans"])
mtx2 = np.array(matrices["trans"])


_P = np.array([[1, 0, 0, 0],[0, 1, 0, 0],[0, 0, 1, 0]])
_G = np.eye(4)
_G[0:3,0:3] = rot
_G[0:3,3] = trans
_N = _P@_G
_Nz = np.eye(3)
_Nz[0:3, 0:2] = _N[0:3,0:2]
_Nz[0:3, 2] = _N[:,3]
_Q = np.linalg.inv(_Nz)
_S = _Q/_Q[2][2]
_dim = (4*297, 4*210)
mapa_x, mapa_y = cv2.initUndistortRectifyMap(mtx, dist, _S, mtx2, _dim, cv2.CV_32FC1)


