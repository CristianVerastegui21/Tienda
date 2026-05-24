try:
    import cv2
    from pyzbar.pyzbar import decode
    SCANNER = True
except Exception:
    SCANNER = False
    cv2 = None
    decode = None
