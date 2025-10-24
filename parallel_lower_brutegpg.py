#!/usr/bin/env python3
"""
Bruteforce GPG simétrico (a..z), paralelo.

Este script prueba contraseñas formadas por las letras 'a'..'z' con longitudes
entre --min y --max usando varios procesos (multiprocessing). Para cada
contraseña lanza `gpg --decrypt` con --passphrase y comprueba si el comando
termina con código 0 (descifrado correcto).
"""
import argparse
import itertools
import os
import subprocess
import sys
import time
from multiprocessing import get_context

def parse_args():
    """
    Define y parsea los argumentos de línea de comandos.

    Argumentos principales:
    - -f / --file: ruta al archivo .gpg a descifrar (obligatorio)
    - --min / --max: longitud mínima y máxima de las contraseñas a probar
    - -j / --jobs: número de procesos worker (0 => cpu_count())
    - --chunk: cuántas contraseñas agrupar en cada tarea enviada al pool
    - --report-interval: cada cuántos segundos imprimir estadísticas
    """
    p = argparse.ArgumentParser(description="Bruteforce GPG simétrico (solo a..z), paralelo.")
    p.add_argument("-f", "--file", required=True, help="Ruta al archivo .gpg/.pgp")
    p.add_argument("--min", dest="min_len", type=int, default=1, help="Longitud mínima")
    p.add_argument("--max", dest="max_len", type=int, default=6, help="Longitud máxima")
    p.add_argument("-j", "--jobs", type=int, default=0, help="Procesos (0 = cpu_count())")
    p.add_argument("--chunk", type=int, default=64, help="Tamaño de lote por tarea")
    p.add_argument("--report-interval", type=float, default=5.0, help="Segundos entre informes")
    return p.parse_args()

# Charset usado para generar contraseñas (solo minúsculas a..z)
CHARS = "abcdefghijklmnopqrstuvwxyz"

# --- Variables globales que serán inicializadas dentro de cada proceso worker
#     (se usan para evitar pasarlas en cada llamada al worker) ---
G_FILE = None         # ruta del archivo .gpg (string)
G_STOP = None         # multiprocessing.Event para indicar que se ha encontrado la pass
G_COUNTER = None      # multiprocessing.Value que cuenta intentos totales
G_FLUSH_EVERY = None  # cada cuántos intentos local se actualiza el contador global

def init_worker(gpg_file, stop_event, counter, flush_every):
    """
    Inicializador del pool: se ejecuta al arrancar cada proceso worker.

    Guarda referencias en variables globales (accesibles por la función `worker`).
    Esto evita problemas de serialización y pasa objetos compartidos (Event/Value).
    """
    global G_FILE, G_STOP, G_COUNTER, G_FLUSH_EVERY
    G_FILE = gpg_file
    G_STOP = stop_event
    G_COUNTER = counter
    G_FLUSH_EVERY = flush_every

def try_pass(gpg_file, pwd):
    """
    Intenta descifrar gpg_file usando la contraseña pwd.

    - Construye el comando 'gpg' con '--pinentry-mode loopback' para pasar la
      passphrase directamente.
    - Redirige stdout/stderr a /dev/null porque solo me interesa el código de
      salida: 0 => éxito (descifrado), distinto de 0 => fallo.
    - Devuelve True si gpg devuelve 0.

    """
    # Comando que se ejecutará
    cmd = [
        "gpg", "--batch", "--yes", "--no-tty",
        "--pinentry-mode", "loopback",
        "--passphrase", pwd,
        "--decrypt", gpg_file
    ]

    # Abrimos /dev/null para silenciar la salida
    with open(os.devnull, "wb") as devnull:
        try:
            # Ejecuta gpg y espera a que termine
            r = subprocess.run(cmd, stdout=devnull, stderr=devnull)
            # True si returncode == 0 (descifrado correcto)
            return r.returncode == 0
        except Exception:
            # Si hay cualquier excepción (p. ej. gpg no encontrado) devolvemos False
            return False

def batched(it, n):
    """
    Agrupa un iterable it en listas de tamaño n.
    De esta manera, por ejemplo, batched(range(10), 3) => [0,1,2], [3,4,5], [6,7,8], [9]
    """
    buf = []
    for x in it:
        buf.append(x)
        if len(buf) == n:
            yield buf
            buf = []
    if buf:
        yield buf

def generate(lo, hi):
    """
    Generador que produce todas las combinaciones del charset CHARS con
    longitudes desde lo(lower) hasta hi(high) (ambos inclusive).

    Usa itertools.product para generar el producto cartesiano (todas las combinaciones posibles).
    """
    for L in range(lo, hi + 1):
        for tup in itertools.product(CHARS, repeat=L):
            yield "".join(tup)

def worker(batch):
    """
    Función que ejecuta cada worker en el Pool.

    - batch es una lista de contraseñas a probar.
    - Mantiene un contador local local con los intentos realizados en este
      lote. Cada G_FLUSH_EVERY intentos actualiza el contador global
      G_COUNTER para que el proceso principal pueda calcular tasas.
    - Si G_STOP (Event) está activado, el worker aborta su trabajo.
    - Si encuentra la contraseña correcta devuelve (pwd, local) donde pwd
      es la contraseña encontrada. Si no la encuentra devuelve (None, local).
    """
    local = 0  # contador local de intentos en este batch

    for pwd in batch:
        # Si otro worker ya encontró la pass, abortamos
        if G_STOP.is_set():
            break

        # Contamos el intento antes de llamar a gpg para que las estadísticas
        # avancen incluso si gpg es lento. Esto hace que el contador sea una
        # aproximación del número de pruebas lanzadas.
        local += 1

        # Cada G_FLUSH_EVERY intentos volcamos al contador global.
        if local % G_FLUSH_EVERY == 0:
            # get_lock() asegura que la operación sea atómica entre procesos.
            with G_COUNTER.get_lock():
                G_COUNTER.value += G_FLUSH_EVERY

        # Intentamos la contraseña
        if try_pass(G_FILE, pwd):
            # Si encontramos la contraseña, añadimos el remanente local que
            # no se haya volcado todavía al contador global.
            rem = local % G_FLUSH_EVERY
            if rem:
                with G_COUNTER.get_lock():
                    G_COUNTER.value += rem

            # Indicamos a los demás que paren
            G_STOP.set()

            # Devolvemos la contraseña encontrada y cuántos intentos locales
            return (pwd, local)

    # Si acabamos el batch sin éxito, volcamos el remanente (si lo hay) y
    # devolvemos (None, local) indicando que no se encontró nada en este batch.
    rem = local % G_FLUSH_EVERY
    if rem:
        with G_COUNTER.get_lock():
            G_COUNTER.value += rem
    return (None, local)

def main():
    """
    Función principal: crea el pool, reparte trabajo y muestra estadísticas.

    Pasos resumidos:
    1. Parsear args y validar existencia del archivo
    2. Crear contexto multiprocessing adecuado (fork) y objetos compartidos
    3. Generar todas las contraseñas y agruparlas en chunks
    4. Consumir los resultados de imap_unordered e imprimir estadísticas
    5. Al encontrar la pass, parar y mostrar resultados.
    """
    a = parse_args()

    # El archivo debe existir
    if not os.path.exists(a.file):
        print(f"ERROR: no existe {a.file}", file=sys.stderr)
        return 2

    # Número de procesos: 0/None -> cpu_count(); mínimo 1
    jobs = (os.cpu_count() or 1) if a.jobs in (0, None) else max(1, a.jobs)

    print(f"[i] Archivo: {a.file}")
    print(f"[i] Charset: '{CHARS}'  Longitud: {a.min_len}..{a.max_len}")
    print(f"[i] jobs={jobs}  chunk={a.chunk}  report-interval={a.report_interval}s")

    # Se crea un contexto multiprocessing explícito.
    ctx = get_context("fork")

    # counter es un Value('Q', 0) compartido entre procesos para contabilizar intentos
    counter = ctx.Value('Q', 0)

    # stop_ev es un Event compartido para indicar a los workers que deben parar
    stop_ev = ctx.Event()

    # Medición de tiempo para estadísticas
    t0 = time.perf_counter()
    last_t = t0
    last_c = 0
    found = None

    # Generador de contraseñas para no almacenar todo en memoria
    gen = generate(a.min_len, a.max_len)

    # Abrimos un Pool de procesos y lanzamos los workers. Inicializamos cada
    # worker con init_worker para que tenga acceso a las variables globales.
    with ctx.Pool(
        processes=jobs,
        initializer=init_worker,
        # initargs: (ruta fichero, evento stop, contador compartido, flush_every)
        initargs=(a.file, stop_ev, counter, 128)  # flush cada 128 intentos
    ) as pool:
        # imap_unordered consume los resultados conforme los workers los van
        # produciendo, sin mantener el orden de envío. Envio al pool
        # iterables ya batched (listas de contraseñas) para reducir overhead.
        it = pool.imap_unordered(worker, batched(gen, a.chunk), chunksize=1)

        # Recorremos los resultados que van llegando
        for pwd, _ in it:
            now = time.perf_counter()

            # Cada report_interval segundos imprimimos estadísticas:
            # total intentos aproximado y velocidad (intentos/s)
            if (now - last_t) >= a.report_interval:
                total = counter.value
                delta = total - last_c
                rate = delta / (now - last_t) if now > last_t else 0.0
                print(f"[stats] total={total:,}  rate={rate:.1f} intentos/s")
                last_t = now
                last_c = total

            # Si pwd no es None significa que un worker encontró la contraseña
            if pwd is not None:
                found = pwd
                # Indicamos a los demás workers que paren (aunque los que ya están
                # en un subprocess.run siguen hasta que termine ese proceso)
                stop_ev.set()
                break

        # Al salir del bucle, se hace un último informe de estadísticas
        now = time.perf_counter()
        total = counter.value
        delta = total - last_c
        rate = delta / (now - last_t) if now > last_t else 0.0
        print(f"[stats] total={total:,}  rate={rate:.1f} intentos/s")

    # Tiempo total transcurrido
    dt = time.perf_counter() - t0

    if found:
        print(f"[+] ENCONTRADA: '{found}' en {dt:.2f}s  (intentos≈{counter.value:,})")
        # Imprimimos la contraseña para que pueda ser capturada
        print(found)
        return 0
    else:
        print(f"[-] No encontrada tras {dt:.2f}s  (intentos≈{counter.value:,})")
        return 1

if __name__ == "__main__":
    sys.exit(main())
