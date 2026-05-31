class EEGParser:
    """
    Parser para tramas ThinkGear/MindWave.

    Formato de trama:
    0xAA 0xAA [payload_length] [payload] [checksum]

    Codigos usados:
    - 0x02: poor signal, 1 byte
    - 0x04: attention, 1 byte
    - 0x05: meditation, 1 byte
    - 0x80: raw wave, longitud 2, signed 16-bit
    - 0x83: ASIC EEG power, longitud 24, ocho valores unsigned 24-bit
    """

    def __init__(self, uart, buffer_size=35, max_payload_length=169):
        self.uart = uart
        self.max_payload_length = max_payload_length

        self.rx_buffer = bytearray()
        self.raw_index = 0
        self.raw_activity = 0
        self.last_raw = 0
        self.raw_baseline = 0
        self.raw_baseline_ready = False
        self.has_eeg_power = False

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
            "RawValue": 0,
            "RawSamples": 0,
            "ValidFrames": 0,
            "BadChecksum": 0,
            "EEGPowerFrames": 0
        }

        self.buffer = {
            "Fp1": [0] * buffer_size,
            "Fp1Raw": [0] * buffer_size
        }

    def procesar(self):
        """
        Lee bytes disponibles y procesa todas las tramas completas.

        UART puede entregar una trama partida entre varias lecturas; por eso
        se acumulan bytes antes de validar cabecera, longitud y checksum.
        """
        available = self.uart.any()
        if available:
            chunk = self.uart.read(available)
            if chunk:
                self.rx_buffer.extend(chunk)

        while len(self.rx_buffer) >= 4:
            if self.rx_buffer[0] != 0xAA:
                self._drop_rx(1)
                continue

            if self.rx_buffer[1] != 0xAA:
                self._drop_rx(1)
                continue

            payload_len = self.rx_buffer[2]
            if payload_len > self.max_payload_length:
                self._drop_rx(1)
                continue

            frame_len = 2 + 1 + payload_len + 1
            if len(self.rx_buffer) < frame_len:
                return

            payload = self.rx_buffer[3:3 + payload_len]
            checksum = self.rx_buffer[3 + payload_len]
            self._drop_rx(frame_len)

            checksum_calculado = 255 - (sum(payload) & 0xFF)
            if checksum != checksum_calculado:
                self.data["BadChecksum"] += 1
                continue

            self.data["ValidFrames"] += 1
            self._extraer_payload(payload)

        if len(self.rx_buffer) > 512:
            self.rx_buffer = self.rx_buffer[-256:]

    def _drop_rx(self, count):
        self.rx_buffer = self.rx_buffer[count:]

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

    def _raw_to_visual(self, value):
        """
        Convierte raw signed 16-bit a una senal visible para el canvas.

        El paquete 0x80 puede traer una componente DC grande o valores muy
        pequenos. Para depuracion visual se centra con una linea base lenta y
        se aplica ganancia agresiva. El raw real queda intacto en Fp1Raw.
        """
        if not self.raw_baseline_ready:
            self.raw_baseline = value
            self.raw_baseline_ready = True

        self.raw_baseline = ((self.raw_baseline * 31) + value) // 32
        centered = value - self.raw_baseline

        visual = centered * 4

        if visual > 130:
            return 130
        if visual < -130:
            return -130
        return visual

    def _append_raw(self, value):
        self.last_raw = value
        self.data["RawValue"] = value
        self.data["RawSamples"] += 1

        self.buffer["Fp1Raw"][self.raw_index] = value
        self.buffer["Fp1"][self.raw_index] = self._raw_to_visual(value)
        self.raw_index = (self.raw_index + 1) % len(self.buffer["Fp1"])

        amplitude = abs(value)
        self.raw_activity = ((self.raw_activity * 7) + amplitude) // 8

        if not self.has_eeg_power:
            self._actualizar_bandas_desde_raw()

    def _actualizar_bandas_desde_raw(self):
        """
        Genera actividad visual desde paquetes 0x80 cuando no llegan 0x83.

        Esto no sustituye un calculo espectral QEEG real. Solo evita que el
        dashboard quede en cero cuando el casco esta enviando raw wave.
        """
        level = self.raw_activity // 32
        if level > 100:
            level = 100

        fast = abs(self.last_raw) // 64
        if fast > 100:
            fast = 100

        self.data.update({
            "Delta": level,
            "Theta": (level * 3) // 4,
            "LowAlpha": fast // 2,
            "HighAlpha": fast // 2,
            "Alpha": fast,
            "LowBeta": fast // 3,
            "HighBeta": fast // 3,
            "Beta": (fast * 2) // 3,
            "Gamma": fast // 4
        })

    def _extraer_payload(self, payload):
        """
        Extrae datos ThinkGear usando formato TLV dentro del payload.
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
                    self.has_eeg_power = True
                    self.data["EEGPowerFrames"] += 1

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

    def _ordered_buffer(self, name):
        values = self.buffer[name]
        return values[self.raw_index:] + values[:self.raw_index]

    def get_json_data(self):
        """
        Devuelve datos listos para /data.

        raw.Fp1 es una senal escalada para el dashboard actual.
        raw.Fp1Raw conserva los valores signed 16-bit reales del paquete 0x80.
        """
        return {
            "raw": {
                "Fp1": self._ordered_buffer("Fp1"),
                "Fp1Raw": self._ordered_buffer("Fp1Raw")
            },
            "fp1": self.data
        }
