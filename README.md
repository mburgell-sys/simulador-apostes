# Simulador d'apostes

Aplicació web educativa (treball de recerca de 2n de batxillerat) que simula
una casa d'apostes esportives fent servir crèdits virtuals ("betcoin") en
lloc de diners reals. Backend en **Python + Flask**, base de dades
**SQLite**, tot executat dins un contenidor amb **Podman**.

## Estructura del projecte

```
simulador-apostes/
├── app.py                 # Backend: rutes, lògica de negoci, base de dades
├── requirements.txt       # Dependències de Python
├── Containerfile           # Recepta del contenidor (com un Dockerfile), arrenca amb Gunicorn
├── podman-compose.yml      # Orquestració local amb Podman
├── render.yaml              # Configuració per desplegar a Render amb un clic
├── templates/               # Pàgines HTML (Jinja2)
├── static/css/style.css     # Estils
├── static/js/main.js        # Interacció del client (tiquet d'aposta)
└── data/                    # Es crea sola: fitxer simulador.db (SQLite)
```

## 1. Instal·lar Podman a Windows

1. Descarrega i instal·la **Podman Desktop**: https://podman-desktop.io/downloads
2. Durant la instal·lació, deixa que creï la "màquina" de Podman (fa servir
   WSL2 per sota). Si t'ho demana, reinicia l'ordinador.
3. Obre una terminal (PowerShell) i comprova que funciona:
   ```powershell
   podman --version
   podman machine start
   ```
4. Instal·la `podman-compose` (necessita Python instal·lat a Windows):
   ```powershell
   pip install podman-compose
   ```

## 2. Arrencar l'aplicació

Des de la carpeta del projecte (`simulador-apostes/`):

```powershell
podman-compose up --build
```

La primera vegada construeix la imatge (baixa Python, instal·la Flask...).
Quan vegis un missatge similar a `Running on http://0.0.0.0:5000`, obre el
navegador a:

```
http://localhost:5000
```

Per aturar-la, prem `Ctrl+C` i després:

```powershell
podman-compose down
```

### Alternativa sense compose (només amb Podman)

```powershell
podman build -t simulador-apostes -f Containerfile .
podman run -p 5000:5000 -v ${PWD}\data:/app/data:Z simulador-apostes
```

## 3. Fer servir l'aplicació

1. Ves a `http://localhost:5000`, clica "Registra't" i crea un usuari.
   Cada compte nou rep 1000 betcoin de regal.
2. Al menú de l'esquerra tries l'esport (Futbol o Tenis).
3. Cliques la quota (1 / X / 2) del partit que t'interessi: apareix un
   petit formulari ("tiquet") on poses quants betcoin vols apostar.
4. A **Historial** veus totes les apostes que has fet.
5. A **Joc Responsable** pots configurar un límit diari d'aposta o
   activar l'autoexclusió (bloquejar-te temporalment).

Les dades es guarden al fitxer `data/simulador.db`, que amb
`podman-compose` es manté encara que aturis i tornis a arrencar el
contenidor (gràcies al volum definit a `podman-compose.yml`).

## 4. Modificar l'aplicació

- **Afegir partits d'exemple**: edita la funció `init_db()` a `app.py`
  (llista `partits_futbol` / `partits_tenis`). Com que la llavor només
  s'insereix si la taula està buida, si vols tornar a generar-los cal
  esborrar `data/simulador.db` i reiniciar.
- **Canviar colors/tipografia**: tot està centralitzat a les variables
  `:root` de `static/css/style.css`.
- **Afegir una pàgina nova**: crea una plantilla a `templates/` que
  comenci amb `{% extends "base.html" %}`, i afegeix una ruta nova a
  `app.py` amb `@app.route(...)`.
- Després de qualsevol canvi al codi, cal reconstruir el contenidor:
  ```powershell
  podman-compose up --build
  ```

## 5. Desplegar-la a Render (accessible des d'internet)

L'aplicació ja està preparada per desplegar-se a [Render](https://render.com)
fent servir el `Containerfile` (Gunicorn en lloc del servidor de
desenvolupament de Flask).

### Opció A: amb el fitxer `render.yaml` (recomanat)

1. Puja el projecte a un repositori de GitHub (o GitLab).
2. Crea un compte a Render i tria **New → Blueprint**.
3. Selecciona el repositori: Render llegirà `render.yaml` automàticament
   i configurarà el servei (incloent una `SECRET_KEY` aleatòria).
4. Clica **Apply**. Al cap d'uns minuts tindràs una URL pública del tipus
   `https://simulador-apostes.onrender.com`.

### Opció B: manualment, sense `render.yaml`

1. **New → Web Service**, connecta el repositori.
2. **Runtime**: Docker. **Dockerfile Path**: `Containerfile`.
3. A **Environment**, afegeix la variable `SECRET_KEY` amb un valor
   aleatori (per exemple, generat amb `python -c "import secrets; print(secrets.token_hex(32))"`).
4. Desplega.

### Important: persistència de dades a Render

El **pla gratuït de Render no té disc persistent**. Això vol dir que cada
cop que el servei es reinicia o es torna a desplegar (per exemple, si
puges un canvi al codi), el fitxer `simulador.db` es perd i es torna a
crear buit, amb els partits d'exemple però sense els usuaris que
s'haguessin registrat.

- Per a la **defensa del treball**, normalment és acceptable: fas login
  o et registres just abans de la demostració.
- Si vols que les dades es mantinguin sempre, cal passar a un pla de
  pagament ("Starter" o superior) i afegir un disc persistent muntat a
  `/app/data` (les línies corresponents ja estan preparades, comentades,
  dins `render.yaml`).

### Restringir l'accés (opcional)

Si només vols que hi accedeixin el tribunal o algunes persones concretes
mentre dura la defensa, a Render pots activar autenticació HTTP bàsica
des de la configuració del servei, sense haver de tocar el codi de
l'aplicació.

## Nota important

Aquesta aplicació és un simulador amb finalitat exclusivament educativa,
elaborat en el marc d'un treball de recerca sobre les addiccions dels
joves a les apostes esportives. El "betcoin" no té cap valor econòmic
real, no es pot comprar ni bescanviar per diners, i l'aplicació no s'ha
de fer servir fora d'aquest context acadèmic.
