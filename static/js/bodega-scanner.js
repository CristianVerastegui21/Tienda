/**
 * Escaneo en el navegador (camara) y lectores USB tipo teclado.
 */
const BodegaScanner = (function () {
  let html5QrCode = null;
  let escaneando = false;
  let onScanCallback = null;
  let procesandoLectura = false;

  function modal() {
    return document.getElementById('bodegaScannerModal');
  }

  function readerId() {
    return 'bodega-qr-reader';
  }

  function limpiarReader() {
    const el = document.getElementById(readerId());
    if (el) {
      el.innerHTML = '';
    }
  }

  function formatosSoportados() {
    if (typeof Html5QrcodeSupportedFormats === 'undefined') {
      return undefined;
    }
    return [
      Html5QrcodeSupportedFormats.QR_CODE,
      Html5QrcodeSupportedFormats.EAN_13,
      Html5QrcodeSupportedFormats.EAN_8,
      Html5QrcodeSupportedFormats.CODE_128,
      Html5QrcodeSupportedFormats.CODE_39,
      Html5QrcodeSupportedFormats.UPC_A,
      Html5QrcodeSupportedFormats.UPC_E,
      Html5QrcodeSupportedFormats.ITF,
      Html5QrcodeSupportedFormats.CODABAR,
      Html5QrcodeSupportedFormats.PDF_417,
    ];
  }

  function configCamara() {
    return {
      fps: 15,
      aspectRatio: 1.777,
      disableFlip: false,
      experimentalFeatures: {
        useBarCodeDetectorIfSupported: true,
      },
      qrbox: function (viewfinderWidth, viewfinderHeight) {
        const w = Math.floor(Math.min(viewfinderWidth * 0.92, 420));
        const h = Math.floor(Math.min(viewfinderHeight * 0.55, 200));
        return { width: w, height: h };
      },
    };
  }

  function mostrarEstado(msg, esError) {
    const el = document.getElementById('bodegaScannerStatus');
    if (!el) return;
    el.textContent = msg || '';
    el.style.color = esError ? 'var(--red, #ff4f6a)' : 'var(--green, #22c98a)';
  }

  function alDetectar(codigo) {
    const texto = String(codigo || '').trim();
    if (!texto || !onScanCallback || procesandoLectura) {
      return;
    }

    procesandoLectura = true;
    mostrarEstado('Codigo leido: ' + texto, false);

    const callback = onScanCallback;
    callback(texto);

    setTimeout(function () {
      procesandoLectura = false;
      cerrarCamara();
    }, 150);
  }

  function detenerCamara() {
    if (!html5QrCode || !escaneando) {
      return Promise.resolve();
    }

    return html5QrCode
      .stop()
      .then(function () {
        return html5QrCode.clear();
      })
      .catch(function () {})
      .finally(function () {
        escaneando = false;
        html5QrCode = null;
        limpiarReader();
      });
  }

  function iniciarCamara() {
    if (typeof Html5Qrcode === 'undefined') {
      mostrarEstado('No se cargo la libreria de escaneo. Recarga la pagina.', true);
      return;
    }

    limpiarReader();
    procesandoLectura = false;

    const formats = formatosSoportados();
    html5QrCode = formats
      ? new Html5Qrcode(readerId(), { formatsToSupport: formats, verbose: false })
      : new Html5Qrcode(readerId());

    const config = configCamara();
    const onSuccess = function (decodedText) {
      alDetectar(decodedText);
    };
    const onError = function () {};

    function iniciar(constraints) {
      return html5QrCode.start(constraints, config, onSuccess, onError);
    }

    Html5Qrcode.getCameras()
      .then(function (cameras) {
        if (cameras && cameras.length) {
          const trasera = cameras.find(function (c) {
            return /back|rear|environment|trasera|posterior/i.test(c.label || '');
          });
          const cam = trasera || cameras[cameras.length - 1];
          return iniciar(cam.id);
        }
        return iniciar({ facingMode: 'environment' });
      })
      .catch(function () {
        return iniciar({ facingMode: 'environment' }).catch(function () {
          return iniciar({ facingMode: 'user' });
        });
      })
      .then(function () {
        escaneando = true;
        mostrarEstado('Apunta al codigo. Se agregara automaticamente al detectarlo.');
      })
      .catch(function (err) {
        mostrarEstado(
          'No se pudo usar la camara. Usa el lector USB o escribe el codigo. ' +
            (err && err.message ? err.message : ''),
          true
        );
      });
  }

  function abrir(options) {
    onScanCallback = options && options.onScan ? options.onScan : null;
    procesandoLectura = false;

    const m = modal();
    if (!m) return;

    m.classList.add('show');
    m.style.display = 'block';
    document.body.classList.add('modal-open');

    setTimeout(iniciarCamara, 350);
  }

  function cerrarCamara() {
    const m = modal();
    if (m) {
      m.classList.remove('show');
      m.style.display = 'none';
    }
    document.body.classList.remove('modal-open');
    mostrarEstado('');
    return detenerCamara();
  }

  function setupLector(input, onScan, opciones) {
    if (!input || !onScan) return;

    const opts = opciones || {};
    const limpiarDespues = opts.limpiarDespues !== false;

    input.addEventListener('keydown', function (e) {
      if (e.key !== 'Enter') return;
      e.preventDefault();

      const codigo = input.value.trim();
      if (!codigo || procesandoLectura) return;

      procesandoLectura = true;
      onScan(codigo);

      if (limpiarDespues) {
        input.value = '';
      }

      setTimeout(function () {
        procesandoLectura = false;
      }, 300);
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    const m = modal();
    if (!m) return;

    m.querySelectorAll('[data-bs-dismiss="scanner"], .btn-close-scanner').forEach(function (btn) {
      btn.addEventListener('click', cerrarCamara);
    });

    m.addEventListener('click', function (e) {
      if (e.target === m) cerrarCamara();
    });
  });

  return { abrir: abrir, cerrar: cerrarCamara, setupLector: setupLector };
})();
