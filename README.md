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
He creado un Dockerfile con una configuración que usa una imagen mínima python:3.12-slim con solo lo necesario (gpg, tini), 
habilita GnuPG en modo loopback (sin UI) y ejecuta con tini como init para manejar señales y evitar zombis.
Además, el wrapper run.sh copia el objetivo a /dev/shm (RAM) para reducir latencia de E/S 
y lanza el script con exec, lo que mejora la parada inmediata cuando se encuentra la clave.

En la siguiente captura se ve /dev/shm montado como tmpfs (4 GB) con límites altos de procesos/FDs, ejecución con jobs=32 y chunk=32 (equilibrio entre throughput y reacción), 
un ritmo estable de ≈98–111 intentos/s y hallazgo de la pass 'drgs' en 610.86 s tras ≈63 819 intentos, confirmando que el diseño es eficiente, reproducible y orientado a rendimiento.
   <img width="795" height="446" alt="imagen" src="https://github.com/user-attachments/assets/c23859a3-7fd9-42e3-b759-e15bb3ceeebd" />

   
# ¿Por qué he optado por esta implementación?
## Resultados experimentales y análisis

A continuación se muestran tres ejecuciones representativas realizadas durante el desarrollo de la práctica. Las capturas corresponden a:

1. Ejecución local (sin contenedor) usando todos los núcleos y `--chunk 32`.
   <img width="819" height="377" alt="imagen" src="https://github.com/user-attachments/assets/ea8a6b08-d3db-4171-b978-b435f49cb4f0" />
2. Ejecución dentro de un contenedor Docker con configuración para limitar recursos, mismo comando (`--chunk 32`).
   <img width="795" height="446" alt="imagen" src="https://github.com/user-attachments/assets/c23859a3-7fd9-42e3-b759-e15bb3ceeebd" />

3. Ejecución leyendo el archivo desde `/dev/shm` y usando `--chunk 128`.
   <img width="640" height="400" alt="imagen" src="https://github.com/user-attachments/assets/e8669f69-a9d9-4ccf-a530-e9523d78dc5b" />
