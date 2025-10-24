# 🔐 Bruteforce GPG (Práctica 2)

Programa en Python para averiguar la passphrase de un fichero cifrado con GnuPG (gpg) por fuerza bruta, suponiendo solo letras minúsculas (a..z). Se prioriza el rendimiento mediante paralelismo, batches (--chunk) y reducción de I/O (p. ej., usando /dev/shm). 
En mis pruebas controladas (archivo en RAM, -j $(nproc)=32, --chunk 32), el sistema sostuvo una media > 100 intentos/s (≈100–110 intentos/s), encontrando la clave en torno a ~598 s tras ~63.5k intentos.
---

# Índice
- 📦 Requisitos 
- 🚀 Uso rápido & Explicación de los parámetros
- 📈 Mejoras & Pruebas
  - Dockerfile
  - Prueba en RAM
  - Otros intentos e implementaciones de código adicionales
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
<img width="819" height="377" alt="imagen" src="https://github.com/user-attachments/assets/0d5932d8-7598-426e-83c7-d2354e4cd4df" />

Explicación de los parámetros:
- -f, --file: ruta al fichero .gpg/.pgp objetivo.
- --min / --max: longitudes mínima y máxima a probar (p. ej., --min 4 --max 4 para exactamente 4).
- -j, --jobs: nº de procesos worker. Recomendado: $(nproc) para usar todos los núcleos.
- --chunk: tamaño del lote de intentos que procesa cada worker antes de pedir más trabajo.
  - Valores pequeños (p. ej., 16–32): mejor tiempo de reacción cuando se encuentra la pass.
  - Valores grandes (p. ej., 64–128): más intentos/s (menos overhead por invocación a gpg).
- --report-interval: segundos entre informes de progreso (intentos/s, etc.).
## 📈 Mejoras & Pruebas
### Dockerfile
He preparado un Dockerfile mínimo basado en python:3.12-slim que instala solo lo imprescindible (gnupg, tini y utilidades básicas), configura GnuPG en modo loopback (sin UI) 
y arranca con tini como init para manejar señales y evitar procesos zombis. Un wrapper (/app/run.sh) copia el fichero objetivo a /dev/shm (RAM) para reducir la latencia de E/S y ejecuta el script con exec,
de modo que la parada al encontrar la clave es inmediata. 

En la ejecución de la captura limito CPU y memoria del contenedor (--cpus="$(nproc)", --memory=2g, --memory-swap=2g, --memory-reservation=1g) y monto /dev/shm como tmpfs de 1 GiB
En esta situación lanzó mi programa con jobs=32 y chunk=32 (equilibrio throughput/latencia), mostrando un ritmo estable de ≈100–108 intentos/s y encontrando la pass 'drgs' en 618.63 s tras ≈63.8 k intentos, 
lo que confirma un diseño eficiente, reproducible y orientado a rendimiento:
```bash
docker build -t gpg-cracker .
docker run --rm -it   --cpus="$(nproc)"   --memory=2g   --memory-swap=2g   --memory-reservation=1g   --tmpfs /dev/shm:rw,noexec,nosuid,nodev,size=1g   -v "$PWD":/data   gpg-cracker   /app/run.sh /data/archive.pdf.gpg   --min 4 --max 4 -j "$(nproc)" --chunk 32 --report-interval 60
``` 
   <img width="803" height="579" alt="imagen" src="https://github.com/user-attachments/assets/d04409a7-6d65-4591-905e-2f1ffae6fec4" />

### Prueba en RAM
También he probado a copiar el archivo a RAM porque al poner así todo va más rápido y más estable. 
En disco, cada intento de gpg tiene que leer el fichero y eso añade tiempos de espera (latencia) y variaciones por el sistema de archivos. En RAM:
- No hay latencia de disco → más intentos por segundo.
- Menos ruido del sistema → medidas más estables y comparables.
- Sin penalización de volúmenes Docker.
```bash
cp archive.pdf.gpg /dev/shm/target.gpg
python3 parallel_lower_brutegpg.py   -f /dev/shm/target.gpg   --min 4 --max 4   -j "$(nproc)"   --chunk 32   --report-interval 60
```   
<img width="804" height="530" alt="imagen" src="https://github.com/user-attachments/assets/c6b173db-9185-4cad-8132-0612eaa97876" />

### Otros intentos e implementaciones de código adicionales
Con el objetivo de seleccionar la alternativa más eficiente, realicé una comparativa sistemática variando (i) el grado de paralelismo (-j) y el tamaño de lote (--chunk). 
Para aislar el efecto de cada parámetro, mantuve constantes el resto de condiciones: fichero en RAM (/dev/shm), mismas longitudes de búsqueda, mismo hardware y, cuando correspondía, límites de CPU/RAM en Docker. 
Los resultados mostraron que el mejor compromiso entre rendimiento y estabilidad se obtenía con -j $(nproc) (32 procesos en mi equipo) y --chunk 32, alcanzando de forma consistente una media > 100 intentos/s (≈100–110 intentos/s).



También evalué versiones previas del cracker (distintas estrategias de generación de candidatos y orquestación de invocaciones a gpg) y ejecuciones en entorno nativo y en contenedor; bajo las mismas condiciones controladas provando las distintas versiones con contraseñas inválidas. De esta manera en el repositorio se encuentra la versión que fue la más rápida.
