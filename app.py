# -*- coding: utf-8 -*-
"""
Simulador d'apostes
--------------------
Aplicacio web educativa que simula una casa d'apostes esportives fent
servir credits virtuals ("betcoin") en lloc de diners reals.

Aquest fitxer es el "cervell" de l'aplicacio: gestiona els usuaris,
els esdeveniments esportius, les apostes i l'historial.

Pensat perque sigui facil de llegir i modificar encara que no tinguis
gaire experiencia programant: cada funcio (cada "ruta", es a dir cada
pagina web) esta comentada i fa una sola cosa.
"""

import os
import sqlite3
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash, g
from werkzeug.security import generate_password_hash, check_password_hash

# ---------------------------------------------------------------------------
# Configuracio general
# ---------------------------------------------------------------------------

app = Flask(__name__)

# Clau secreta per xifrar la sessio de l'usuari (cookies de login).
# En producció real aixo NO s'hauria de deixar fix al codi, pero per a
# un treball de recerca / simulador local es suficient.
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "clau-secreta-treball-recerca-2026")

# On es guarda el fitxer de la base de dades SQLite.
# Fem servir una carpeta "data" perque despres, amb Podman, hi puguem
# connectar un volum i que les dades no es perdin en reiniciar el contenidor.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)
DATABASE_PATH = os.path.join(DATA_DIR, "simulador.db")

# Quants "betcoin" reben els usuaris nous en registrar-se.
CREDIT_INICIAL = 1000


# ---------------------------------------------------------------------------
# Connexio a la base de dades
# ---------------------------------------------------------------------------

def get_db():
    """Retorna una connexio a la base de dades, reutilitzant-la durant
    la mateixa petició web (patró estàndard de Flask)."""
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE_PATH)
        g.db.row_factory = sqlite3.Row  # ens deixa fer fila["nom_columna"]
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Crea les taules si no existeixen i afegeix partits d'exemple
    la primera vegada que s'arrenca l'aplicació."""
    db = sqlite3.connect(DATABASE_PATH)
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS usuaris (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom_usuari TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            saldo_betcoin INTEGER NOT NULL DEFAULT 0,
            data_registre TEXT NOT NULL,
            limit_aposta_diari INTEGER,
            autoexclos INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS esdeveniments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            esport TEXT NOT NULL,               -- 'futbol' o 'tenis'
            competicio TEXT NOT NULL,
            participant_1 TEXT NOT NULL,
            participant_2 TEXT NOT NULL,
            data_hora TEXT NOT NULL,
            quota_1 REAL NOT NULL,               -- quota que guanya participant_1
            quota_empat REAL,                    -- nomes futbol (NULL en tenis)
            quota_2 REAL NOT NULL,               -- quota que guanya participant_2
            resultat TEXT                        -- NULL=pendent, '1' | 'X' | '2'
        );

        CREATE TABLE IF NOT EXISTS apostes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuari_id INTEGER NOT NULL REFERENCES usuaris(id),
            esdeveniment_id INTEGER NOT NULL REFERENCES esdeveniments(id),
            seleccio TEXT NOT NULL,              -- '1', 'X' o '2'
            quota REAL NOT NULL,
            import_apostat INTEGER NOT NULL,
            guany_potencial INTEGER NOT NULL,
            estat TEXT NOT NULL DEFAULT 'pendent',  -- pendent | guanyada | perduda
            data_hora TEXT NOT NULL
        );
        """
    )
    db.commit()

    # Nomes sembrem partits d'exemple si la taula esta buida.
    hi_ha_partits = db.execute("SELECT COUNT(*) AS n FROM esdeveniments").fetchone()[0]
    if hi_ha_partits == 0:
        ara = datetime.now()
        partits_futbol = [
            ("futbol", "LaLiga", "Sevilla FC", "Deportivo Alavés", ara + timedelta(days=1, hours=2), 1.93, 3.35, 4.00),
            ("futbol", "LaLiga", "Màlaga CF", "Racing de Santander", ara + timedelta(days=2, hours=5), 2.38, 3.60, 2.70),
            ("futbol", "LaLiga", "RCD Espanyol", "Deportivo de la Coruña", ara + timedelta(days=4, hours=3), 2.15, 3.40, 3.25),
            ("futbol", "LaLiga", "CA Osasuna", "Athletic Club", ara + timedelta(days=1, hours=2), 3.25, 3.40, 2.15),
            ("futbol", "LaLiga", "València CF", "Real Madrid", ara + timedelta(days=1, hours=2), 9.00, 5.75, 1.28),
            ("futbol", "LaLiga", "Elche CF", "Real Betis", ara + timedelta(days=1, hours=2), 3.15, 3.70, 2.10),
            ("futbol", "LaLiga", "Celta de Vigo", "Levante CF", ara + timedelta(days=1, hours=2), 1.78, 3.75, 4.20),
            ("futbol", "LaLiga", "Villareal CF", "Getafe CF", ara + timedelta(days=1, hours=2), 1.45, 4.33, 7.00),
            ("futbol", "LaLiga", "Real Sociedad", "Rayo Vallecano", ara + timedelta(days=1, hours=2), 1.70, 3.95, 4.50),
            ("futbol", "LaLiga", "Atlético de Madrid", "FC Barcelona", ara + timedelta(days=1, hours=2), 3.65, 4.20, 1.80),
        ]
        for esport, comp, p1, p2, data, q1, qx, q2 in partits_futbol:
            db.execute(
                "INSERT INTO esdeveniments (esport, competicio, participant_1, participant_2, data_hora, quota_1, quota_empat, quota_2) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (esport, comp, p1, p2, data.isoformat(), q1, qx, q2),
            )

        partits_tenis = [
            ("tenis", "ATP Paris", "Casper Ruud (NOR)", "Juan Manuel Cerundolo (ARG)", ara + timedelta(days=1, hours=6), 1.48, None, 2.60),
            ("tenis", "ATP Paris", "Stefanos Tsitsipas (GRE)", "Learner Tien (USA)", ara + timedelta(days=1, hours=9), 2.05, None, 1.67),
            ("tenis", "ATP Paris", "Novak Djokovic (SRB)", "Valentin Vacherot (FRA)", ara + timedelta(days=2, hours=4), 1.42, None, 2.70),
        ]
        for esport, comp, p1, p2, data, q1, qx, q2 in partits_tenis:
            db.execute(
                "INSERT INTO esdeveniments (esport, competicio, participant_1, participant_2, data_hora, quota_1, quota_empat, quota_2) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (esport, comp, p1, p2, data.isoformat(), q1, qx, q2),
            )
        db.commit()

    db.close()


# ---------------------------------------------------------------------------
# Utilitats d'autenticacio
# ---------------------------------------------------------------------------

def usuari_actual():
    """Retorna la fila de l'usuari connectat, o None si ningu ha fet login."""
    usuari_id = session.get("usuari_id")
    if usuari_id is None:
        return None
    return get_db().execute("SELECT * FROM usuaris WHERE id = ?", (usuari_id,)).fetchone()


def cal_login(funcio):
    """Decorador: si l'usuari no ha fet login, el redirigim a /login."""
    from functools import wraps

    @wraps(funcio)
    def embolcall(*args, **kwargs):
        if usuari_actual() is None:
            return redirect(url_for("login"))
        return funcio(*args, **kwargs)

    return embolcall


@app.context_processor
def injectar_usuari():
    """Fa que 'usuari' estigui disponible a totes les plantilles HTML
    sense haver-lo de passar manualment cada vegada."""
    return {"usuari": usuari_actual()}


# ---------------------------------------------------------------------------
# Rutes: registre i login
# ---------------------------------------------------------------------------

@app.route("/registre", methods=["GET", "POST"])
def registre():
    if request.method == "POST":
        nom_usuari = request.form.get("nom_usuari", "").strip()
        password = request.form.get("password", "")

        if len(nom_usuari) < 3:
            flash("El nom d'usuari ha de tenir com a mínim 3 caràcters.")
            return redirect(url_for("registre"))
        if len(password) < 4:
            flash("La contrasenya ha de tenir com a mínim 4 caràcters.")
            return redirect(url_for("registre"))

        db = get_db()
        ja_existeix = db.execute(
            "SELECT id FROM usuaris WHERE nom_usuari = ?", (nom_usuari,)
        ).fetchone()
        if ja_existeix:
            flash("Aquest nom d'usuari ja existeix.")
            return redirect(url_for("registre"))

        db.execute(
            "INSERT INTO usuaris (nom_usuari, password_hash, saldo_betcoin, data_registre) "
            "VALUES (?, ?, ?, ?)",
            (nom_usuari, generate_password_hash(password), CREDIT_INICIAL, datetime.now().isoformat()),
        )
        db.commit()
        flash("Compte creat correctament. Ja pots iniciar sessió.")
        return redirect(url_for("login"))

    return render_template("registre.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        nom_usuari = request.form.get("nom_usuari", "").strip()
        password = request.form.get("password", "")

        fila = get_db().execute(
            "SELECT * FROM usuaris WHERE nom_usuari = ?", (nom_usuari,)
        ).fetchone()

        if fila is None or not check_password_hash(fila["password_hash"], password):
            flash("Nom d'usuari o contrasenya incorrectes.")
            return redirect(url_for("login"))

        session["usuari_id"] = fila["id"]
        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# Rutes principals
# ---------------------------------------------------------------------------

@app.route("/")
def arrel():
    return redirect(url_for("dashboard") if usuari_actual() else url_for("login"))


@app.route("/dashboard")
@cal_login
def dashboard():
    db = get_db()
    usuari = usuari_actual()
    apostes_recents = db.execute(
        """
        SELECT apostes.*, esdeveniments.participant_1, esdeveniments.participant_2, esdeveniments.esport
        FROM apostes
        JOIN esdeveniments ON apostes.esdeveniment_id = esdeveniments.id
        WHERE apostes.usuari_id = ?
        ORDER BY apostes.data_hora DESC
        LIMIT 5
        """,
        (usuari["id"],),
    ).fetchall()

    total_apostat_avui = db.execute(
        """
        SELECT COALESCE(SUM(import_apostat), 0) AS total
        FROM apostes
        WHERE usuari_id = ? AND date(data_hora) = date('now')
        """,
        (usuari["id"],),
    ).fetchone()["total"]

    return render_template(
        "dashboard.html",
        apostes_recents=apostes_recents,
        total_apostat_avui=total_apostat_avui,
    )


@app.route("/esport/<nom_esport>")
@cal_login
def esport(nom_esport):
    if nom_esport not in ("futbol", "tenis"):
        return redirect(url_for("dashboard"))

    esdeveniments = get_db().execute(
        "SELECT * FROM esdeveniments WHERE esport = ? AND resultat IS NULL ORDER BY data_hora ASC",
        (nom_esport,),
    ).fetchall()

    return render_template("esport.html", esdeveniments=esdeveniments, nom_esport=nom_esport)


@app.route("/apostar/<int:esdeveniment_id>", methods=["POST"])
@cal_login
def apostar(esdeveniment_id):
    usuari = usuari_actual()
    db = get_db()

    if usuari["autoexclos"]:
        flash("Tens l'autoexclusió activada des de Joc Responsable. No pots fer apostes.")
        return redirect(url_for("joc_responsable"))

    esdeveniment = db.execute(
        "SELECT * FROM esdeveniments WHERE id = ?", (esdeveniment_id,)
    ).fetchone()
    if esdeveniment is None:
        flash("Aquest esdeveniment no existeix.")
        return redirect(url_for("dashboard"))

    seleccio = request.form.get("seleccio")  # '1', 'X' o '2'
    try:
        import_apostat = int(request.form.get("import_apostat", 0))
    except ValueError:
        import_apostat = 0

    if import_apostat <= 0:
        flash("L'import de l'aposta ha de ser un número positiu.")
        return redirect(url_for("esport", nom_esport=esdeveniment["esport"]))

    if import_apostat > usuari["saldo_betcoin"]:
        flash("No tens prou betcoin per fer aquesta aposta.")
        return redirect(url_for("esport", nom_esport=esdeveniment["esport"]))

    # Comprovem el límit diari d'autolimitació, si l'usuari n'ha configurat un.
    if usuari["limit_aposta_diari"] is not None:
        apostat_avui = db.execute(
            """
            SELECT COALESCE(SUM(import_apostat), 0) AS total
            FROM apostes
            WHERE usuari_id = ? AND date(data_hora) = date('now')
            """,
            (usuari["id"],),
        ).fetchone()["total"]
        if apostat_avui + import_apostat > usuari["limit_aposta_diari"]:
            flash(
                f"Superaries el teu límit diari de {usuari['limit_aposta_diari']} betcoin "
                "que vas configurar a Joc Responsable."
            )
            return redirect(url_for("esport", nom_esport=esdeveniment["esport"]))

    quota = {
        "1": esdeveniment["quota_1"],
        "X": esdeveniment["quota_empat"],
        "2": esdeveniment["quota_2"],
    }.get(seleccio)

    if quota is None:
        flash("Selecció no vàlida.")
        return redirect(url_for("esport", nom_esport=esdeveniment["esport"]))

    guany_potencial = round(import_apostat * quota)

    db.execute(
        "UPDATE usuaris SET saldo_betcoin = saldo_betcoin - ? WHERE id = ?",
        (import_apostat, usuari["id"]),
    )
    db.execute(
        """
        INSERT INTO apostes (usuari_id, esdeveniment_id, seleccio, quota, import_apostat, guany_potencial, data_hora)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (usuari["id"], esdeveniment_id, seleccio, quota, import_apostat, guany_potencial, datetime.now().isoformat()),
    )
    db.commit()

    flash(f"Aposta registrada: {import_apostat} betcoin a quota {quota}. Guany potencial: {guany_potencial} betcoin.")
    return redirect(url_for("esport", nom_esport=esdeveniment["esport"]))


@app.route("/historial")
@cal_login
def historial():
    usuari = usuari_actual()
    apostes = get_db().execute(
        """
        SELECT apostes.*, esdeveniments.participant_1, esdeveniments.participant_2,
               esdeveniments.esport, esdeveniments.competicio
        FROM apostes
        JOIN esdeveniments ON apostes.esdeveniment_id = esdeveniments.id
        WHERE apostes.usuari_id = ?
        ORDER BY apostes.data_hora DESC
        """,
        (usuari["id"],),
    ).fetchall()
    return render_template("historial.html", apostes=apostes)


@app.route("/joc-responsable", methods=["GET", "POST"])
@cal_login
def joc_responsable():
    usuari = usuari_actual()
    db = get_db()

    if request.method == "POST":
        accio = request.form.get("accio")

        if accio == "definir_limit":
            try:
                nou_limit = int(request.form.get("limit_aposta_diari", 0))
                if nou_limit <= 0:
                    nou_limit = None
            except ValueError:
                nou_limit = None
            db.execute(
                "UPDATE usuaris SET limit_aposta_diari = ? WHERE id = ?",
                (nou_limit, usuari["id"]),
            )
            db.commit()
            flash("Límit diari actualitzat.")

        elif accio == "treure_limit":
            db.execute(
                "UPDATE usuaris SET limit_aposta_diari = NULL WHERE id = ?",
                (usuari["id"],),
            )
            db.commit()
            flash("Límit diari eliminat.")

        elif accio == "autoexcloure":
            db.execute(
                "UPDATE usuaris SET autoexclos = 1 WHERE id = ?", (usuari["id"],)
            )
            db.commit()
            flash("Autoexclusió activada. Ja no podràs fer apostes fins que la desactivis.")

        elif accio == "cancelar_autoexclusio":
            db.execute(
                "UPDATE usuaris SET autoexclos = 0 WHERE id = ?", (usuari["id"],)
            )
            db.commit()
            flash("Autoexclusió desactivada.")

        return redirect(url_for("joc_responsable"))

    usuari = usuari_actual()  # recarreguem per tenir les dades actualitzades
    return render_template("joc_responsable.html", usuari=usuari)


@app.route("/missio")
@cal_login
def missio():
    return render_template("missio.html")


@app.route("/valors")
@cal_login
def valors():
    return render_template("valors.html")


# ---------------------------------------------------------------------------
# Arrencada
# ---------------------------------------------------------------------------

init_db()

if __name__ == "__main__":
    # host="0.0.0.0" es necessari perque el servidor sigui accessible
    # des de fora del contenidor Podman.
    app.run(host="0.0.0.0", port=5000, debug=True)
