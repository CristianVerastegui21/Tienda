SCANNER = False
cv2 = None
decode = None

try:
    import cv2
    from pyzbar.pyzbar import decode
    SCANNER = True
except Exception:
    pass
