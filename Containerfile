# Containerfile del "Simulador d'apostes"
# Podman i Docker fan servir el mateix format, per això aquest fitxer
# tambe funcionaria si l'anomenessis "Dockerfile".

FROM python:3.12-slim

# Evita que Python generi fitxers .pyc i força que els prints surtin
# immediatament als logs del contenidor (útil per depurar).
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copiem primer nomes les dependencies per aprofitar la cache de Podman:
# si no canvies requirements.txt, aquest pas no es torna a refer.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Ara copiem la resta del codi de l'aplicació.
COPY . .

# Carpeta on es guardarà la base de dades SQLite (hi connectarem un volum).
RUN mkdir -p /app/data

# Render (i la majoria de plataformes) assignen el port dinàmicament
# mitjançant la variable d'entorn PORT; en local (Podman) no la definim,
# i per això fem servir 5000 com a valor per defecte.
EXPOSE 5000

# Gunicorn es el servidor de produccio: mes robust i segur que el
# "python app.py" que fem servir nomes per a proves rapides en local
# sense contenidor. Un sol worker amb varis threads es suficient per
# a un simulador de treball de recerca amb poc trafic, i evita
# problemes de concurrencia en escriure al fitxer SQLite.
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-5000} --workers 1 --threads 4 --timeout 60 app:app"]
