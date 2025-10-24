# 🔐 Bruteforce GPG (Práctica 2)
Programa en Python para averiguar la passphrase de un fichero cifrado con GnuPG (gpg) por fuerza bruta, suponiendo solo letras minúsculas (a..z).
Se prioriza el rendimiento mediante paralelismo, batches (--chunk) y reducción de I/O (p. ej., /dev/shm).
---

## 📦 Requisitos 
Sistema GNU/Linux con:

- Python 3.8+
- GnuPG (`gpg`) instalado

Instalación recomendada:

```bash
sudo apt update
sudo apt install gpg
```   
## 🚀 Uso rápido & Explicación de los parámetros
Formato general: 
```bash
python3 bruteforce.py -f <archivo.gpg> --min <n> --max <n> -j <procesos> --chunk <tamaño>
```
Ejecución recomendada (baseline):
```bash
python3 parallel_lower_brutegpg.py   -f archive.pdf.gpg   --min 4 --max 4   -j $(nproc) --chunk 32 --report-interval 60
```
Explicación de los parámetros:
- -f, --file: ruta al fichero .gpg/.pgp objetivo.
- --min / --max: longitudes mínima y máxima a probar (p. ej., --min 4 --max 4 para exactamente 4).
- -j, --jobs: nº de procesos worker. Recomendado: $(nproc) para usar todos los núcleos.
- --chunk: tamaño del lote de intentos que procesa cada worker antes de pedir más trabajo.
  - Valores pequeños (p. ej., 16–32): mejor tiempo de reacción cuando se encuentra la pass.
  - Valores grandes (p. ej., 64–128): más intentos/s (menos overhead por invocación a gpg).
- --report-interval: segundos entre informes de progreso (intentos/s, etc.).
## Mejoras & Pruebas
### Dockerfile
He preparado un Dockerfile mínimo basado en python:3.12-slim que instala solo lo imprescindible (gnupg, tini y utilidades básicas), configura GnuPG en modo loopback (sin UI) 
y arranca con tini como init para manejar señales y evitar procesos zombis. Un wrapper (/app/run.sh) copia el fichero objetivo a /dev/shm (RAM) para reducir la latencia de E/S y ejecuta el script con exec,
de modo que la parada al encontrar la clave es inmediata. 

En la ejecución de la captura limito CPU y memoria del contenedor (--cpus="$(nproc)", --memory=2g, --memory-swap=2g, --memory-reservation=1g) y monto /dev/shm como tmpfs de 1 GiB
En esta situación lanzó mi programa con jobs=32 y chunk=32 (equilibrio throughput/latencia), mostrando un ritmo estable de ≈100–108 intentos/s y encontrando la pass 'drgs' en 618.63 s tras ≈63.8 k intentos, 
lo que confirma un diseño eficiente, reproducible y orientado a rendimiento:

   <img width="803" height="579" alt="imagen" src="https://github.com/user-attachments/assets/d04409a7-6d65-4591-905e-2f1ffae6fec4" />

### Prueba en RAM

   
# ¿Por qué he optado por esta implementación?
## Resultados experimentales y análisis

A continuación se muestran tres ejecuciones representativas realizadas durante el desarrollo de la práctica. Las capturas corresponden a:

1. Ejecución local (sin contenedor) usando todos los núcleos y `--chunk 32`.
   <img width="819" height="377" alt="imagen" src="https://github.com/user-attachments/assets/ea8a6b08-d3db-4171-b978-b435f49cb4f0" />
2. Ejecución dentro de un contenedor Docker con configuración para limitar recursos, mismo comando (`--chunk 32`).
   <img width="795" height="446" alt="imagen" src="https://github.com/user-attachments/assets/c23859a3-7fd9-42e3-b759-e15bb3ceeebd" />

3. Ejecución leyendo el archivo desde `/dev/shm` y usando `--chunk 128`.
   <img width="640" height="400" alt="imagen" src="https://github.com/user-attachments/assets/e8669f69-a9d9-4ccf-a530-e9523d78dc5b" />
