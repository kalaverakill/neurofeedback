# =======================================================
# CONFIGURACIÓN GENERAL DEL PROYECTO QEEG
# =======================================================

try:
    from secrets import SSID, PASSWORD
except ImportError:
    SSID = "TU_WIFI"
    PASSWORD = "TU_PASSWORD"

# UART1 en ESP32
UART_ID = 1
BAUDRATE = 57600
RX_PIN = 16
TX_PIN = 17
UART_TIMEOUT = 10

# Servidor web
SERVER_PORT = 80
SERVER_TIMEOUT = 0.1

# Datos EEG
BUFFER_SIZE = 35
MAX_PAYLOAD_LENGTH = 169
