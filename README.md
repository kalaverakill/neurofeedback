# QEEG Project - ESP32 + MindWave/ThinkGear

Proyecto modular para leer datos EEG desde UART en un ESP32 y mostrarlos en un dashboard web.

## Archivos

- `main.py`: punto de entrada.
- `config.py`: configuración WiFi, UART y servidor.
- `wifi.py`: conexión WiFi.
- `eeg_parser.py`: parser de tramas EEG.
- `dashboard.py`: interfaz HTML.
- `web_server.py`: servidor HTTP para `/` y `/data`.

## Uso en Thonny

1. Copiar todos los archivos al ESP32.
2. Ejecutar `main.py`.
3. Abrir en el navegador la IP que aparece en consola.

## Hardware esperado

- ESP32 / Wemos Mini ESP32.
- UART1:
  - RX: GPIO 16
  - TX: GPIO 17
- Baudrate: 57600.
- Protocolo esperado: tramas tipo ThinkGear con cabecera `0xAA 0xAA`.
