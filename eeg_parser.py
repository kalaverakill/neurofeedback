class EEGParser:
    """
    Parser para tramas ThinkGear/MindWave.

    Formato de trama:
    0xAA 0xAA [payload_length] [payload] [checksum]

    El payload contiene codigos ThinkGear:
    - 0x02: poor signal, 1 byte
    - 0x04: attention, 1 byte
    - 0x05: meditation, 1 byte
    - 0x80: raw wave, longitud 2, valor signed 16-bit
    - 0x83: ASIC EEG power, longitud 24, ocho valores de 24 bits
    """

    def __init__(self, uart, buffer_size=35, max_payload_length=169):
        self.uart = uart
        self.max_payload_length = max_payload_length

        self.rx_buffer = bytearray()
        self.raw_index = 0

        self.data = {
            "Delta": 0,
            "Theta": 0,
            "LowAlpha": 0,
            "HighAlpha": 0,
            "Alpha": 0,
            "LowBeta": 0,
            "HighBeta": 0,
            "Beta": 0,
            "Gamma": 0,
            "PoorSignal": 200,
            "Attention": 0,
            "Meditation": 0,
            "ValidFrames": 0,
            "BadChecksum": 0
        }

        self.buffer = {
            "Fp1": [0] * buffer_size
        }

    def procesar(self):
        """
        Lee bytes disponibles de UART y procesa todas las tramas completas.

        UART puede entregar una trama partida en varias lecturas. Por eso se
        acumulan bytes en rx_buffer hasta tener una trama completa.
        """
        available = self.uart.any()
        if available:
            chunk = self.uart.read(available)
            if chunk:
                self.rx_buffer.extend(chunk)

        while len(self.rx_buffer) >= 4:
            if self.rx_buffer[0] != 0xAA:
                del self.rx_buffer[0]
                continue

            if self.rx_buffer[1] != 0xAA:
                del self.rx_buffer[0]
                continue

            payload_len = self.rx_buffer[2]

            if payload_len > self.max_payload_length:
                del self.rx_buffer[0]
                continue

            frame_len = 2 + 1 + payload_len + 1
            if len(self.rx_buffer) < frame_len:
                return

            payload = self.rx_buffer[3:3 + payload_len]
            checksum = self.rx_buffer[3 + payload_len]
            del self.rx_buffer[:frame_len]

            checksum_calculado = 255 - (sum(payload) & 0xFF)
            if checksum != checksum_calculado:
                self.data["BadChecksum"] += 1
                continue

            self.data["ValidFrames"] += 1
            self._extraer_payload(payload)

        if len(self.rx_buffer) > 512:
            del self.rx_buffer[:-256]

    def _leer_24_bits(self, payload, offset):
        return (
            (payload[offset] << 16) |
            (payload[offset + 1] << 8) |
            payload[offset + 2]
        )

    def _leer_raw_16_bits(self, payload):
        value = (payload[0] << 8) | payload[1]
        if value & 0x8000:
            value -= 0x10000
        return value

    def _append_raw(self, value):
        self.buffer["Fp1"][self.raw_index] = value
        self.raw_index = (self.raw_index + 1) % len(self.buffer["Fp1"])

    def _extraer_payload(self, payload):
        """
        Extrae datos ThinkGear del payload usando formato TLV.
        """
        i = 0
        length = len(payload)

        while i < length:
            code = payload[i]
            i += 1

            if code == 0x02:
                if i >= length:
                    return
                self.data["PoorSignal"] = payload[i]
                i += 1

            elif code == 0x04:
                if i >= length:
                    return
                self.data["Attention"] = payload[i]
                i += 1

            elif code == 0x05:
                if i >= length:
                    return
                self.data["Meditation"] = payload[i]
                i += 1

            elif code >= 0x80:
                if i >= length:
                    return

                data_len = payload[i]
                i += 1

                if i + data_len > length:
                    return

                data = payload[i:i + data_len]
                i += data_len

                if code == 0x80 and data_len == 2:
                    self._append_raw(self._leer_raw_16_bits(data))

                elif code == 0x83 and data_len == 24:
                    delta = self._leer_24_bits(data, 0)
                    theta = self._leer_24_bits(data, 3)
                    low_alpha = self._leer_24_bits(data, 6)
                    high_alpha = self._leer_24_bits(data, 9)
                    low_beta = self._leer_24_bits(data, 12)
                    high_beta = self._leer_24_bits(data, 15)
                    low_gamma = self._leer_24_bits(data, 18)
                    high_gamma = self._leer_24_bits(data, 21)

                    self.data.update({
                        "Delta": delta,
                        "Theta": theta,
                        "LowAlpha": low_alpha,
                        "HighAlpha": high_alpha,
                        "Alpha": low_alpha + high_alpha,
                        "LowBeta": low_beta,
                        "HighBeta": high_beta,
                        "Beta": low_beta + high_beta,
                        "Gamma": low_gamma + high_gamma
                    })

            else:
                if i >= length:
                    return
                i += 1

    def get_json_data(self):
        """
        Devuelve datos listos para /data.

        El buffer circular se reordena para que el navegador reciba la onda
        temporal en orden cronologico.
        """
        raw = self.buffer["Fp1"][self.raw_index:] + self.buffer["Fp1"][:self.raw_index]

        return {
            "raw": {
                "Fp1": raw
            },
            "fp1": self.data
        }
