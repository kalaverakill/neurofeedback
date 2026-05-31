import socket
import ujson
import gc


class WebServer:
    """
    Servidor web básico para MicroPython.

    Importante:
    - Usa timeout para que accept() no bloquee eternamente.
    - En cada vuelta del bucle procesa UART antes de atender peticiones HTTP.
    """

    def __init__(self, parser, html, port=80, timeout=0.1):
        self.parser = parser
        self.html = html
        self.port = port
        self.timeout = timeout
        self.socket = None

    def iniciar(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind(('', self.port))
        self.socket.listen(1)
        self.socket.settimeout(self.timeout)

        print("Servidor web iniciado en puerto {}".format(self.port))

        while True:
            self.parser.procesar()

            try:
                conn, addr = self.socket.accept()
                conn.settimeout(1.0)

                req = conn.recv(512).decode()

                if "GET /data" in req:
                    self._enviar_json(conn)
                else:
                    self._enviar_html(conn)

                conn.close()

            except OSError:
                # Timeout normal del socket. Permite seguir procesando UART.
                pass

            except Exception as e:
                print("Error en servidor web:", e)

            gc.collect()

    def _enviar_json(self, conn):
        body = ujson.dumps(self.parser.get_json_data())

        conn.send(
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: application/json\r\n"
            "Connection: close\r\n"
            "\r\n"
        )

        conn.send(body)

    def _enviar_html(self, conn):
        conn.send(
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: text/html\r\n"
            "Connection: close\r\n"
            "\r\n"
        )

        conn.sendall(self.html)
