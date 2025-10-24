# Imagen ligera + Python rápido
FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Paquetes mínimos: gpg, tini (init limpio) y coreutils (cp, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gnupg tini coreutils && \
    rm -rf /var/lib/apt/lists/*

# Config GnuPG (loopback, evita pinentry)
RUN mkdir -p /root/.gnupg && \
    echo "allow-loopback-pinentry" > /root/.gnupg/gpg-agent.conf && \
    echo "pinentry-mode loopback"  > /root/.gnupg/gpg.conf && \
    chmod 700 /root/.gnupg && chmod 600 /root/.gnupg/*

WORKDIR /app

# Copia el script
COPY parallel_lower_brutegpg.py /app/parallel_lower_brutegpg.py

# Wrapper para copiar el .gpg a RAM (/dev/shm) y ejecutar (compatible con /bin/sh)
# Uso: /app/run.sh /data/archivo.gpg [args del script...]
RUN printf '%s\n' \
'#!/bin/sh' \
'set -eu' \
'IN="$1"; shift' \
'TARGET="/dev/shm/target.gpg"' \
'cp "$IN" "$TARGET"' \
'exec python /app/parallel_lower_brutegpg.py -f "$TARGET" "$@"' \
> /app/run.sh && chmod +x /app/run.sh

# tini como init para señales limpias
ENTRYPOINT ["/usr/bin/tini","--"]

# Por defecto, muestra la ayuda si se pasan args
CMD ["python","/app/parallel_lower_brutegpg.py","--help"]
