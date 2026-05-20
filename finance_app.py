import os
from datetime import datetime, date
from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__, template_folder="templates/finance")
app.secret_key = os.environ.get("SECRET_KEY", "finance-dev-secret")

CATEGORIES = {
    "receita": ["Salário", "Freelance", "Investimentos", "Presente", "Outros"],
    "despesa": ["Alimentação", "Transporte", "Moradia", "Saúde", "Lazer", "Educação", "Vestuário", "Outros"],
}


def get_db():
    from google.cloud import firestore
    return firestore.Client()


def _parse_form(form):
    errors = []
    tipo = form.get("tipo", "").strip()
    categoria = form.get("categoria", "").strip()
    descricao = form.get("descricao", "").strip()
    valor_raw = form.get("valor", "").strip()
    data_raw = form.get("data", "").strip()

    if tipo not in ("receita", "despesa"):
        errors.append("Tipo deve ser receita ou despesa.")
    if not categoria:
        errors.append("Categoria é obrigatória.")
    if not descricao:
        errors.append("Descrição é obrigatória.")
    try:
        valor = float(valor_raw.replace(",", "."))
        if valor <= 0:
            raise ValueError
    except ValueError:
        valor = None
        errors.append("Valor deve ser um número positivo.")
    try:
        data_parsed = datetime.strptime(data_raw, "%Y-%m-%d").date()
        data_str = data_raw
    except ValueError:
        data_parsed = None
        data_str = ""
        errors.append("Data inválida.")

    record = {
        "tipo": tipo,
        "categoria": categoria,
        "descricao": descricao,
        "valor": valor,
        "data": data_str,
    }
    return record, errors


@app.route("/")
def index():
    db = get_db()
    filtro_tipo = request.args.get("tipo", "")
    filtro_mes = request.args.get("mes", "")

    query = db.collection("transactions").order_by("data", direction="DESCENDING")
    docs = [{"id": d.id, **d.to_dict()} for d in query.stream()]

    if filtro_tipo in ("receita", "despesa"):
        docs = [d for d in docs if d.get("tipo") == filtro_tipo]
    if filtro_mes:
        docs = [d for d in docs if d.get("data", "").startswith(filtro_mes)]

    total_receitas = sum(d["valor"] for d in docs if d.get("tipo") == "receita")
    total_despesas = sum(d["valor"] for d in docs if d.get("tipo") == "despesa")
    saldo = total_receitas - total_despesas

    all_docs = [{"id": d.id, **d.to_dict()} for d in db.collection("transactions").stream()]
    meses = sorted({d.get("data", "")[:7] for d in all_docs if d.get("data")}, reverse=True)

    return render_template(
        "index.html",
        transactions=docs,
        total_receitas=total_receitas,
        total_despesas=total_despesas,
        saldo=saldo,
        filtro_tipo=filtro_tipo,
        filtro_mes=filtro_mes,
        meses=meses,
    )


@app.route("/create", methods=["GET", "POST"])
def create():
    if request.method == "POST":
        record, errors = _parse_form(request.form)
        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("form.html", action="Adicionar", record=record, categories=CATEGORIES)
        db = get_db()
        record["criado_em"] = datetime.utcnow().isoformat()
        db.collection("transactions").add(record)
        flash("Lançamento adicionado com sucesso!", "success")
        return redirect(url_for("index"))

    today = date.today().strftime("%Y-%m-%d")
    return render_template("form.html", action="Adicionar", record={"data": today}, categories=CATEGORIES)


@app.route("/edit/<doc_id>", methods=["GET", "POST"])
def edit(doc_id):
    db = get_db()
    doc_ref = db.collection("transactions").document(doc_id)
    doc = doc_ref.get()
    if not doc.exists:
        flash("Registro não encontrado.", "error")
        return redirect(url_for("index"))

    if request.method == "POST":
        record, errors = _parse_form(request.form)
        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("form.html", action="Editar", record=record, doc_id=doc_id, categories=CATEGORIES)
        doc_ref.update(record)
        flash("Lançamento atualizado com sucesso!", "success")
        return redirect(url_for("index"))

    record = {"id": doc.id, **doc.to_dict()}
    return render_template("form.html", action="Editar", record=record, doc_id=doc_id, categories=CATEGORIES)


@app.route("/delete/<doc_id>", methods=["POST"])
def delete(doc_id):
    db = get_db()
    db.collection("transactions").document(doc_id).delete()
    flash("Lançamento removido.", "success")
    return redirect(url_for("index"))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG", "0") == "1")
