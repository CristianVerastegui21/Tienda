try:
    import cv2
    from pyzbar.pyzbar import decode
    SCANNER = True
except:
    SCANNER = False
    cv2 = None
    decode = None
