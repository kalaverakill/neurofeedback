import machine

from config import (
    SSID,
    PASSWORD,
    UART_ID,
    BAUDRATE,
    RX_PIN,
    TX_PIN,
    UART_TIMEOUT,
    SERVER_PORT,
    SERVER_TIMEOUT,
    BUFFER_SIZE,
    MAX_PAYLOAD_LENGTH
)
from wifi import conectar_wifi
from eeg_parser import EEGParser
from dashboard import HTML
from web_server import WebServer


def main():
    conectar_wifi(SSID, PASSWORD)

    uart = machine.UART(
        UART_ID,
        baudrate=BAUDRATE,
        rx=RX_PIN,
        tx=TX_PIN,
        timeout=UART_TIMEOUT
    )

    parser = EEGParser(
        uart=uart,
        buffer_size=BUFFER_SIZE,
        max_payload_length=MAX_PAYLOAD_LENGTH
    )

    server = WebServer(
        parser=parser,
        html=HTML,
        port=SERVER_PORT,
        timeout=SERVER_TIMEOUT
    )

    server.iniciar()


main()
