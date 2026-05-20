from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from pathlib import Path

app = Flask(__name__)
app.secret_key = "gdp-crud-secret"

DB_PATH = Path(__file__).parent / "data" / "records.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    DB_PATH.parent.mkdir(exist_ok=True)
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                country_code TEXT NOT NULL,
                country_name TEXT NOT NULL,
                year INTEGER NOT NULL,
                gdp_billion REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()


@app.route("/")
def index():
    search = request.args.get("search", "").strip()
    with get_db() as conn:
        if search:
            rows = conn.execute(
                "SELECT * FROM records WHERE country_name LIKE ? OR country_code LIKE ? ORDER BY year DESC",
                (f"%{search}%", f"%{search}%"),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM records ORDER BY year DESC").fetchall()
    return render_template("index.html", records=rows, search=search)


@app.route("/create", methods=["GET", "POST"])
def create():
    if request.method == "POST":
        code = request.form["country_code"].strip().upper()
        name = request.form["country_name"].strip()
        year = request.form["year"].strip()
        gdp = request.form["gdp_billion"].strip()

        errors = []
        if not code or len(code) > 3:
            errors.append("Código do país deve ter até 3 caracteres.")
        if not name:
            errors.append("Nome do país é obrigatório.")
        try:
            year = int(year)
            if year < 1900 or year > 2100:
                raise ValueError
        except ValueError:
            errors.append("Ano inválido.")
        try:
            gdp = float(gdp)
            if gdp < 0:
                raise ValueError
        except ValueError:
            errors.append("PIB deve ser um número positivo.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("form.html", action="Criar", record=request.form)

        with get_db() as conn:
            conn.execute(
                "INSERT INTO records (country_code, country_name, year, gdp_billion) VALUES (?, ?, ?, ?)",
                (code, name, year, gdp),
            )
            conn.commit()
        flash("Registro criado com sucesso!", "success")
        return redirect(url_for("index"))

    return render_template("form.html", action="Criar", record={})


@app.route("/edit/<int:record_id>", methods=["GET", "POST"])
def edit(record_id):
    with get_db() as conn:
        record = conn.execute("SELECT * FROM records WHERE id = ?", (record_id,)).fetchone()
    if not record:
        flash("Registro não encontrado.", "error")
        return redirect(url_for("index"))

    if request.method == "POST":
        code = request.form["country_code"].strip().upper()
        name = request.form["country_name"].strip()
        year = request.form["year"].strip()
        gdp = request.form["gdp_billion"].strip()

        errors = []
        if not code or len(code) > 3:
            errors.append("Código do país deve ter até 3 caracteres.")
        if not name:
            errors.append("Nome do país é obrigatório.")
        try:
            year = int(year)
            if year < 1900 or year > 2100:
                raise ValueError
        except ValueError:
            errors.append("Ano inválido.")
        try:
            gdp = float(gdp)
            if gdp < 0:
                raise ValueError
        except ValueError:
            errors.append("PIB deve ser um número positivo.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("form.html", action="Editar", record=request.form, record_id=record_id)

        with get_db() as conn:
            conn.execute(
                "UPDATE records SET country_code=?, country_name=?, year=?, gdp_billion=? WHERE id=?",
                (code, name, year, gdp, record_id),
            )
            conn.commit()
        flash("Registro atualizado com sucesso!", "success")
        return redirect(url_for("index"))

    return render_template("form.html", action="Editar", record=record, record_id=record_id)


@app.route("/delete/<int:record_id>", methods=["POST"])
def delete(record_id):
    with get_db() as conn:
        conn.execute("DELETE FROM records WHERE id = ?", (record_id,))
        conn.commit()
    flash("Registro removido com sucesso!", "success")
    return redirect(url_for("index"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="0.0.0.0", port=8080)
