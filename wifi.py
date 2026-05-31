import network
import time


def conectar_wifi(ssid, password):
    """
    Conecta el ESP32 a una red WiFi en modo estación.
    Devuelve el objeto wlan ya conectado.
    """
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if not wlan.isconnected():
        wlan.connect(ssid, password)

        while not wlan.isconnected():
            print("Conectando a WiFi...")
            time.sleep(1)

    ip = wlan.ifconfig()[0]
    print("Sistema QEEG Online listo en: http://{}".format(ip))

    return wlan
