# Sistema EEG de Neurofeedback en Tiempo Real con ESP32

Prototipo de adquisicion y visualizacion EEG en tiempo real construido con Wemos Mini ESP32, MicroPython, comunicacion Bluetooth UART y un dashboard web embebido.

El sistema recibe paquetes EEG compatibles con ThinkGear desde un casco BrainMind Wave Mobile 2 mediante un modulo Bluetooth HC-05, procesa el flujo serial en el ESP32, expone los datos como JSON y sirve una interfaz web accesible desde un telefono movil en la misma red WiFi local.

> Este proyecto es un prototipo educativo y tecnico de sistemas embebidos, IoT y neurofeedback. No es un dispositivo medico certificado y no debe usarse para diagnostico clinico sin validacion, calibracion y revision regulatoria.

---

## Descripcion Tecnica

Este proyecto implementa una ruta completa de datos EEG usando solo un ESP32 y MicroPython. El ESP32 funciona como controlador de adquisicion, parser de protocolo y servidor web local.

El sistema:

- Se conecta a una red WiFi en modo estacion.
- Recibe datos EEG por UART desde un modulo HC-05.
- Interpreta tramas compatibles con ThinkGear / NeuroSky.
- Valida longitud de payload y checksum.
- Extrae senal cruda desde paquetes `0x80`.
- Extrae bandas EEG desde paquetes `0x83` cuando estan disponibles.
- Mantiene un buffer circular de senal.
- Publica datos en tiempo real mediante el endpoint `/data`.
- Sirve un dashboard HTML/JavaScript directamente desde el ESP32.

El objetivo es construir una plataforma portatil de neurofeedback local, sin depender de servicios cloud, software de escritorio ni servidores externos.

---

## Arquitectura del Sistema

Flujo completo de datos:

```text
+--------------------------+
| BrainMind Wave Mobile 2  |
| Casco EEG                |
+------------+-------------+
             |
             | Flujo Bluetooth serial
             v
+--------------------------+
| Modulo HC-05             |
| Puente Bluetooth -> UART |
+------------+-------------+
             |
             | UART @ 57600 baud
             | TX -> ESP32 GPIO16 (RX)
             | RX -> ESP32 GPIO17 (TX)
             v
+--------------------------+
| Wemos Mini ESP32         |
| MicroPython              |
+------------+-------------+
             |
             v
+--------------------------+
| Parser ThinkGear         |
| Cabecera, payload        |
| checksum, 0x80, 0x83     |
+------------+-------------+
             |
             v
+--------------------------+
| Procesamiento EEG        |
| Buffer circular          |
| Escalado visual          |
| Metricas internas        |
+------------+-------------+
             |
             v
+--------------------------+
| Servidor HTTP embebido   |
| /      -> dashboard      |
| /data  -> JSON           |
+------------+-------------+
             |
             | Red WiFi local
             v
+--------------------------+
| Navegador movil          |
| Dashboard EEG            |
+--------------------------+
```

---

## Hardware Utilizado

| Componente | Funcion |
| --- | --- |
| Wemos Mini ESP32 | Controlador principal, receptor UART, parser ThinkGear y servidor web |
| HC-05 | Puente Bluetooth a UART entre el casco y el ESP32 |
| BrainMind Wave Mobile 2 | Casco EEG que transmite paquetes compatibles con ThinkGear |
| Smartphone | Cliente web para visualizar el dashboard |
| Red WiFi local | Comunicacion entre el ESP32 y el navegador del telefono |

### Conexion UART

| HC-05 | ESP32 | Funcion |
| --- | --- | --- |
| TX | GPIO16 (RX) | Entrada serial EEG hacia el ESP32 |
| RX | GPIO17 (TX) | Salida serial opcional desde el ESP32 |
| GND | GND | Tierra comun |
| VCC | Alimentacion compatible | Alimentacion del HC-05 |

Configuracion serial por defecto:

```text
UART:      UART1
RX:        GPIO16
TX:        GPIO17
Baudrate:  57600
Protocolo: ThinkGear / NeuroSky
```

---

## Estructura del Proyecto

```text
neurofeedback/
|-- main.py
|-- config.py
|-- wifi.py
|-- eeg_parser.py
|-- web_server.py
|-- dashboard.py
`-- README.md
```

### `main.py`

Punto de entrada del sistema.

Responsabilidades:

- Cargar configuracion.
- Conectar el ESP32 a WiFi.
- Inicializar UART1 con los pines configurados.
- Crear el parser EEG.
- Crear el servidor web embebido.
- Iniciar el bucle principal de adquisicion y servicio HTTP.

### `eeg_parser.py`

Parser ThinkGear y modelo de datos EEG.

Responsabilidades:

- Mantener un buffer interno para lecturas UART parciales.
- Resincronizar tramas usando la cabecera `0xAA 0xAA`.
- Validar longitud de payload.
- Validar checksum.
- Decodificar paquetes raw wave `0x80` como enteros signed 16-bit.
- Decodificar paquetes EEG power `0x83` cuando aparecen.
- Mantener buffers circulares:
  - `raw.Fp1`: senal escalada para el dashboard.
  - `raw.Fp1Raw`: senal cruda real.
- Generar actividad visual si solo llegan paquetes `0x80`.
- Exponer `get_json_data()` para el endpoint `/data`.

### `web_server.py`

Servidor HTTP minimalista para MicroPython.

Responsabilidades:

- Abrir un socket TCP en el puerto configurado.
- Atender solicitudes HTTP.
- Llamar continuamente a `parser.procesar()`.
- Servir:
  - `/` como dashboard HTML.
  - `/data` como JSON.
- Ejecutar recoleccion de basura para reducir presion de memoria.

### `dashboard.py`

Interfaz web embebida.

Responsabilidades:

- Definir el HTML, CSS y JavaScript del dashboard.
- Mostrar boton de inicio/detencion de test.
- Dibujar barras de potencia EEG.
- Dibujar trazado EEG frontal en canvas.
- Consultar `/data` periodicamente mediante `fetch()`.
- Actualizar tabla, barras y grafica en tiempo real.

### `wifi.py`

Modulo de conectividad WiFi.

Responsabilidades:

- Activar la interfaz WiFi del ESP32.
- Conectar a la red configurada.
- Esperar hasta obtener conexion.
- Mostrar por consola la URL del dashboard.

### `config.py`

Modulo central de configuracion.

Responsabilidades:

- Credenciales WiFi.
- UART, baudrate, RX, TX y timeout.
- Puerto y timeout del servidor web.
- Tamano del buffer EEG.
- Longitud maxima del payload ThinkGear.

Patron recomendado para credenciales:

```python
try:
    from secrets import SSID, PASSWORD
except ImportError:
    SSID = "TU_WIFI"
    PASSWORD = "TU_PASSWORD"
```

No publiques credenciales reales en GitHub.

---

## Protocolo EEG

El proyecto procesa tramas compatibles con ThinkGear / NeuroSky.

### Formato de Trama

```text
0xAA 0xAA [payload_length] [payload] [checksum]
```

### Cabecera

Cada trama comienza con:

```text
AA AA
```

El parser usa esta cabecera para sincronizarse de nuevo si recibe bytes parciales, basura serial o datos incompletos.

### Payload

El byte despues de la cabecera indica la longitud del payload.

El parser rechaza paquetes con longitud mayor que `MAX_PAYLOAD_LENGTH`.

### Checksum

El checksum se calcula asi:

```text
checksum = 255 - (sum(payload) & 0xFF)
```

Si el checksum recibido no coincide, la trama se descarta y aumenta el contador `BadChecksum`.

### Paquete `0x80` Raw Wave

Formato:

```text
0x80 0x02 [high_byte] [low_byte]
```

Los dos bytes se interpretan como entero signed 16-bit:

```python
value = (high_byte << 8) | low_byte
if value & 0x8000:
    value -= 0x10000
```

El valor real se publica en:

```text
raw.Fp1Raw
```

La version escalada para visualizacion se publica en:

```text
raw.Fp1
```

### Paquete `0x83` EEG Power

Formato:

```text
0x83 0x18 [24 bytes]
```

Contiene ocho valores unsigned de 24 bits:

1. Delta
2. Theta
3. Low Alpha
4. High Alpha
5. Low Beta
6. High Beta
7. Low Gamma
8. High Gamma

El parser publica tambien:

- `Alpha = LowAlpha + HighAlpha`
- `Beta = LowBeta + HighBeta`
- `Gamma = LowGamma + HighGamma`

Si no llegan paquetes `0x83`, el sistema mantiene movimiento visual usando la actividad derivada de paquetes raw `0x80`.

---

## Caracteristicas Actuales

- Adquisicion EEG en tiempo real por UART.
- Comunicacion Bluetooth mediante HC-05.
- Parser ThinkGear con sincronizacion por cabecera.
- Validacion de checksum.
- Lectura robusta ante paquetes UART parciales.
- Decodificacion de paquetes `0x80`.
- Decodificacion de paquetes `0x83` cuando estan disponibles.
- Buffer circular de senal.
- Endpoint JSON `/data`.
- Servidor web embebido en ESP32.
- Dashboard movil por WiFi local.
- Escalado visual temporal para senal raw.
- Metricas internas:
  - `RawSamples`
  - `RawValue`
  - `ValidFrames`
  - `BadChecksum`
  - `EEGPowerFrames`

---

## Instalacion Paso a Paso

### 1. Instalar Thonny

Descarga Thonny:

```text
https://thonny.org/
```

Usa Thonny como IDE, consola REPL y herramienta para subir archivos al ESP32.

### 2. Instalar MicroPython en el ESP32

En Thonny:

1. Conecta el Wemos Mini ESP32 por USB.
2. Abre `Tools -> Options -> Interpreter`.
3. Selecciona MicroPython para ESP32.
4. Instala o actualiza el firmware si hace falta.
5. Confirma que puedes usar la consola REPL.

### 3. Conectar el HC-05

Conexion esperada:

```text
HC-05 TX -> ESP32 GPIO16 (RX)
HC-05 RX -> ESP32 GPIO17 (TX)
GND      -> GND
```

Verifica que el HC-05 este configurado a `57600` baud.

### 4. Configurar WiFi

Opcion recomendada: crear `secrets.py` en el ESP32:

```python
SSID = "nombre_de_tu_wifi"
PASSWORD = "password_de_tu_wifi"
```

`secrets.py` no debe subirse al repositorio.

### 5. Subir Archivos al ESP32

Desde Thonny, subir al dispositivo MicroPython:

```text
main.py
config.py
wifi.py
eeg_parser.py
web_server.py
dashboard.py
secrets.py
```

Asegurate de guardar en `MicroPython device`, no solo en el PC.

### 6. Ejecutar

En Thonny:

```python
exec(open("main.py").read())
```

O abre `main.py` y pulsa Run.

Salida esperada:

```text
Sistema QEEG Online listo en: http://10.254.0.45
Servidor web iniciado en puerto 80
```

---

## Uso

1. Enciende el casco EEG.
2. Asegura que el HC-05 este conectado y recibiendo datos.
3. Ejecuta `main.py` en el ESP32.
4. Abre la IP impresa por consola desde un telefono en la misma red WiFi.
5. Pulsa `Iniciar Test`.
6. Observa:
   - barras EEG,
   - valores por banda,
   - trazado frontal en tiempo real.

### Endpoint JSON

```text
http://<ip-del-esp32>/data
```

Ejemplo:

```json
{
  "raw": {
    "Fp1": [0, 12, -18],
    "Fp1Raw": [120, 384, -512]
  },
  "fp1": {
    "RawSamples": 100,
    "RawValue": -512,
    "ValidFrames": 100,
    "BadChecksum": 0,
    "EEGPowerFrames": 0
  }
}
```

### Interpretacion Basica

- `raw.Fp1Raw`: valor crudo signed 16-bit de paquetes `0x80`.
- `raw.Fp1`: valor escalado para el canvas.
- `RawSamples`: cantidad de muestras raw recibidas.
- `ValidFrames`: tramas ThinkGear validas.
- `BadChecksum`: tramas descartadas por checksum incorrecto.
- `EEGPowerFrames`: paquetes `0x83` recibidos.

Si `RawSamples` sube y `EEGPowerFrames` queda en cero, el casco esta transmitiendo senal raw, pero no paquetes de potencia EEG.

---

## Solucion de Problemas

### `AttributeError: 'EEGParser' object has no attribute 'uart'`

Causa: el constructor de `EEGParser` esta mal escrito en el archivo del ESP32.

Correcto:

```python
def __init__(self, uart, buffer_size=35, max_payload_length=169):
```

Incorrecto:

```python
def init(...)
def _init_(...)
```

Verificacion en Thonny:

```python
for i, line in enumerate(open("eeg_parser.py")):
    if "init" in line:
        print(i + 1, repr(line))
```

### La Web Abre Pero No Se Mueve la Senal

Revisa `/data`:

- Si `RawSamples` sube, UART y parser funcionan.
- Si `raw.Fp1` esta plano, ajustar escalado visual en `eeg_parser.py`.
- Si `RawSamples` no sube, revisar entrada Bluetooth/UART.

### No Llegan Datos UART

Verifica:

- HC-05 TX conectado a GPIO16.
- HC-05 RX conectado a GPIO17.
- GND comun.
- Baudrate `57600`.
- Casco encendido, emparejado y transmitiendo.

### WiFi No Conecta

Verifica:

- SSID y password.
- Alcance de red.
- Que el telefono y el ESP32 esten en la misma red.
- Que `secrets.py` exista si se usa configuracion privada.

### El Navegador No Abre el Dashboard

Verifica:

- El ESP32 imprimio una IP.
- Se esta usando `http://`, no `https://`.
- El telefono esta en la misma red WiFi.
- El servidor esta en puerto `80`.

### `BadChecksum` Alto

Posibles causas:

- Ruido serial.
- Baudrate incorrecto.
- Enlace Bluetooth inestable.
- Alimentacion inestable.
- Datos parciales o corrupcion en UART.

---

## Mejoras Futuras

Ideas de evolucion tecnica:

- Filtros digitales:
  - remocion DC,
  - filtro notch,
  - filtro pasa banda.
- FFT real en ESP32 o en navegador.
- Calculo real de bandas EEG.
- Escalado adaptativo del trazado.
- Exportacion CSV.
- Almacenamiento historico de sesiones.
- Multiples canales.
- Modos de entrenamiento neurofeedback.
- Umbrales adaptativos.
- Marcadores de eventos: parpadeo, cejas, mandibula, atencion.
- Experimentos de machine learning.
- Streaming con WebSocket o Server-Sent Events.
- Reconexion WiFi automatica.
- Manejo mas robusto de sockets.

---

## Creditos

Autor:

```text
Kevin Surribas
```

Mentoria tecnica:

```text
Gonzalo Surribas
```

---

## Licencia

MIT License.

Este repositorio esta orientado a educacion, investigacion y portfolio tecnico. Cualquier uso medico o clinico requiere validacion, pruebas de seguridad y cumplimiento regulatorio.
