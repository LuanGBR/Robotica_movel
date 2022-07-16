import cv2
video = cv2.VideoCapture(0)
rc, img = video.read()
video.release()
cv2.imwrite("imagem2.jpg", img)

