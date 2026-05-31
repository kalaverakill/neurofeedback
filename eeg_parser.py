class EEGParser:
    """
    Parser para tramas EEG tipo ThinkGear/MindWave.

    Espera tramas con cabecera:
    0xAA 0xAA [payload_length] [payload] [checksum]

    Dentro del payload busca el código 0x83, que contiene los valores
    de potencia EEG extendida: Delta, Theta, Alpha, Beta y Gamma.
    """

    def __init__(self, uart, buffer_size=35, max_payload_length=169):
        self.uart = uart
        self.max_payload_length = max_payload_length

        self.data = {
            "Delta": 0,
            "Theta": 0,
            "LowAlpha": 0,
            "HighAlpha": 0,
            "Alpha": 0,
            "LowBeta": 0,
            "HighBeta": 0,
            "Beta": 0,
            "Gamma": 0
        }

        self.buffer = {
            "Fp1": [0] * buffer_size
        }

    def procesar(self):
        """
        Lee una trama desde UART si hay datos disponibles.
        Si la trama es válida, actualiza self.data y self.buffer.
        """
        if self.uart.any() < 3:
            return

        if self.uart.read(1) != b'\xAA':
            return

        if self.uart.read(1) != b'\xAA':
            return

        payload_len = ord(self.uart.read(1) or b'\x00')

        if payload_len > self.max_payload_length:
            return

        payload = self.uart.read(payload_len)
        checksum = ord(self.uart.read(1) or b'\x00')

        if not payload:
            return

        checksum_calculado = 255 - (sum(list(payload)) & 0xFF)

        if checksum != checksum_calculado:
            return

        self._extraer_payload(payload)

    def _leer_24_bits(self, p, offset):
        """
        Convierte 3 bytes consecutivos en un valor numérico.
        """
        if offset + 2 >= len(p):
            return 0

        return (
            (p[offset] << 16) |
            (p[offset + 1] << 8) |
            p[offset + 2]
        ) / 1000

    def _extraer_payload(self, payload):
        """
        Extrae las bandas EEG desde el payload.
        """
        p = list(payload)
        i = 0

        while i < len(p):

            if p[i] == 0x83:
                off = i + 2

                delta = self._leer_24_bits(p, off)
                theta = self._leer_24_bits(p, off + 3)
                low_alpha = self._leer_24_bits(p, off + 6)
                high_alpha = self._leer_24_bits(p, off + 9)
                low_beta = self._leer_24_bits(p, off + 12)
                high_beta = self._leer_24_bits(p, off + 15)
                low_gamma = self._leer_24_bits(p, off + 18)
                high_gamma = self._leer_24_bits(p, off + 21)

                self.data.update({
                    "Delta": delta,
                    "Theta": theta,
                    "LowAlpha": low_alpha,
                    "HighAlpha": high_alpha,
                    "Alpha": (low_alpha + high_alpha) / 2,
                    "LowBeta": low_beta,
                    "HighBeta": high_beta,
                    "Beta": (low_beta + high_beta) / 2,
                    "Gamma": (low_gamma + high_gamma) / 2
                })

                self.buffer["Fp1"].pop(0)
                self.buffer["Fp1"].append(int(theta % 100))

                i += 26

            elif p[i] in [0x02, 0x04, 0x05]:
                i += 2

            else:
                i += 1

    def get_json_data(self):
        """
        Devuelve los datos listos para enviarse al navegador.
        """
        return {
            "raw": self.buffer,
            "fp1": self.data
        }
