import os
from datetime import date, datetime, timedelta
from decimal import Decimal

from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, text

from flask import send_file
from io import BytesIO
import os

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image
)

load_dotenv()

app = Flask(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL não encontrada no arquivo .env")

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True,
    "pool_recycle": 300,
}

db = SQLAlchemy(app)


class ConfiguracaoEmpresa(db.Model):
    __tablename__ = "configuracao_empresa"

    id = db.Column(db.Integer, primary_key=True)

    nome_empresa = db.Column(
        db.String(150),
        nullable=False,
        default="DR Reparos"
    )

    documento = db.Column(db.String(30))
    telefone = db.Column(db.String(30))
    email = db.Column(db.String(150))
    instagram = db.Column(db.String(100))

    endereco = db.Column(db.String(200))
    cidade = db.Column(db.String(100))
    estado = db.Column(db.String(2))
    cep = db.Column(db.String(15))

    pix = db.Column(db.String(150))

    formas_pagamento = db.Column(
        db.Text,
        default="PIX, Dinheiro, Débito e Crédito"
    )

    texto_orcamento = db.Column(
        db.Text,
        default="Agradecemos a oportunidade de apresentar nosso orçamento."
    )

    observacoes_orcamento = db.Column(db.Text)


# =========================================================
# CLIENTES
# =========================================================

class Cliente(db.Model):
    __tablename__ = "clientes"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False)
    telefone = db.Column(db.String(30), nullable=False)
    email = db.Column(db.String(150))
    endereco = db.Column(db.String(250))
    observacoes = db.Column(db.Text)

    data_cadastro = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )

   

    orcamentos = db.relationship(
        "Orcamento",
        back_populates="cliente",
        lazy=True
    )

    servicos = db.relationship(
        "Servico",
        back_populates="cliente",
        lazy=True
    )


class CatalogoServico(db.Model):
    __tablename__ = "catalogo_servicos"

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(20), unique=True, nullable=False)
    descricao = db.Column(db.String(200), nullable=False)
    complemento = db.Column(db.String(200))
    categoria = db.Column(db.String(100))
    custo_base = db.Column(db.Numeric(10, 2), default=0)
    valor_base = db.Column(db.Numeric(10, 2), nullable=False)
    ativo = db.Column(db.Boolean, default=True)


class Material(db.Model):
    __tablename__ = "materiais"

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(20), unique=True, nullable=False)
    descricao = db.Column(db.String(200), nullable=False)
    complemento = db.Column(db.String(300))
    categoria = db.Column(db.String(100))

    quantidade = db.Column(db.Integer, default=0)

    custo_medio = db.Column(db.Numeric(10, 2), default=0)
    valor_venda = db.Column(db.Numeric(10, 2), default=0)

    estoque_maximo = db.Column(db.Integer, default=0)
    estoque_minimo = db.Column(db.Integer, default=0)

    ativo = db.Column(db.Boolean, default=True)

# =========================================================
# ORÇAMENTOS
# =========================================================

class Orcamento(db.Model):
    __tablename__ = "orcamentos"

    id = db.Column(db.Integer, primary_key=True)

    cliente_id = db.Column(
        db.Integer,
        db.ForeignKey("clientes.id"),
        nullable=False
    )

    descricao = db.Column(db.Text, nullable=False)
    valor = db.Column(db.Numeric(10, 2), nullable=False)

    data_orcamento = db.Column(
        db.Date,
        default=date.today,
        nullable=False
    )

    # Data em que o orçamento passou a contar como faturamento
    data_aprovacao = db.Column(db.Date)

    validade_dias = db.Column(db.Integer, default=15)

    status = db.Column(
        db.String(30),
        default="Aguardando",
        nullable=False
    )

    observacoes = db.Column(db.Text)
    motivo_perda = db.Column(db.String(200))

    data_cadastro = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    # Data em que o orçamento passou a contar como faturamento.
    data_aprovacao = db.Column(db.Date)

    cliente = db.relationship(
        "Cliente",
        back_populates="orcamentos"
    )

    servico = db.relationship(
        "Servico",
        back_populates="orcamento",
        uselist=False
    )

    itens = db.relationship(
        "OrcamentoItem",
        back_populates="orcamento",
        cascade="all, delete-orphan",
        order_by="OrcamentoItem.id"
    )


class OrcamentoItem(db.Model):
    __tablename__ = "orcamento_itens"

    id = db.Column(db.Integer, primary_key=True)
    orcamento_id = db.Column(
        db.Integer,
        db.ForeignKey("orcamentos.id"),
        nullable=False
    )
    tipo = db.Column(db.String(20), nullable=False, default="Serviço")
    descricao = db.Column(db.Text, nullable=False)
    quantidade = db.Column(db.Numeric(10, 2), nullable=False, default=1)
    valor_unitario = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    valor_total = db.Column(db.Numeric(10, 2), nullable=False, default=0)

    orcamento = db.relationship(
        "Orcamento",
        back_populates="itens"
    )


# =========================================================
# SERVIÇOS
# =========================================================

class Servico(db.Model):
    __tablename__ = "servicos"

    id = db.Column(db.Integer, primary_key=True)

    numero_os = db.Column(db.Integer)

    cliente_id = db.Column(
        db.Integer,
        db.ForeignKey("clientes.id"),
        nullable=False
    )

    orcamento_id = db.Column(
        db.Integer,
        db.ForeignKey("orcamentos.id"),
        unique=True
    )

    descricao = db.Column(db.Text, nullable=False)

    valor = db.Column(
        db.Numeric(10, 2),
        nullable=False,
        default=Decimal("0.00")
    )

       # Data marcada para executar o atendimento
    data_agendada = db.Column(db.Date)

    # Data em que o atendimento foi realmente concluído
    data_servico = db.Column(db.Date)

    status = db.Column(
        db.String(30),
        default="Aguardando execução",
        nullable=False
    )

    observacoes = db.Column(db.Text)

    data_cadastro = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    # Data em que o orçamento passou a contar como faturamento.
    data_aprovacao = db.Column(db.Date)

    cliente = db.relationship(
        "Cliente",
        back_populates="servicos"
    )

    orcamento = db.relationship(
        "Orcamento",
        back_populates="servico"
    )

    pagamento = db.relationship(
        "Pagamento",
        back_populates="servico",
        uselist=False
    )

    custos = db.relationship(
        "Custo",
        back_populates="servico",
        lazy=True
    )


# =========================================================
# PAGAMENTOS / RECEITAS
# =========================================================

class Pagamento(db.Model):
    __tablename__ = "pagamentos"

    id = db.Column(db.Integer, primary_key=True)

    servico_id = db.Column(
        db.Integer,
        db.ForeignKey("servicos.id"),
        unique=True,
        nullable=False
    )

    valor = db.Column(
        db.Numeric(10, 2),
        nullable=False
    )

    forma_pagamento = db.Column(
        db.String(30),
        nullable=False
    )

    data_pagamento = db.Column(
        db.Date,
        default=date.today,
        nullable=False
    )

    servico = db.relationship(
        "Servico",
        back_populates="pagamento"
    )


# =========================================================
# CUSTOS DOS SERVIÇOS
# =========================================================

class Custo(db.Model):
    __tablename__ = "custos"

    id = db.Column(db.Integer, primary_key=True)

    servico_id = db.Column(
        db.Integer,
        db.ForeignKey("servicos.id"),
        nullable=False
    )

    categoria = db.Column(
        db.String(50),
        nullable=False
    )

    descricao = db.Column(
        db.String(200)
    )

    valor = db.Column(
        db.Numeric(10, 2),
        nullable=False
    )

    data_custo = db.Column(
        db.Date,
        default=date.today,
        nullable=False
    )

    servico = db.relationship(
        "Servico",
        back_populates="custos"
    )


# =========================================================
# DESPESAS GERAIS
# =========================================================

class Despesa(db.Model):
    __tablename__ = "despesas"

    id = db.Column(db.Integer, primary_key=True)

    categoria = db.Column(
        db.String(50),
        nullable=False
    )

    descricao = db.Column(
        db.String(200),
        nullable=False
    )

    valor = db.Column(
        db.Numeric(10, 2),
        nullable=False
    )

    data_despesa = db.Column(
        db.Date,
        default=date.today,
        nullable=False
    )


# =========================================================
# METAS
# =========================================================

class Meta(db.Model):
    __tablename__ = "metas"

    id = db.Column(db.Integer, primary_key=True)

    mes = db.Column(
        db.Integer,
        nullable=False
    )

    ano = db.Column(
        db.Integer,
        nullable=False
    )

    valor = db.Column(
        db.Numeric(10, 2),
        nullable=False
    )

    __table_args__ = (
        db.UniqueConstraint(
            "mes",
            "ano",
            name="uq_meta_mes_ano"
        ),
    )
def formatar_telefone(telefone):

    if not telefone:
        return ""

    # Mantém apenas números
    numeros = "".join(
        caractere
        for caractere in str(telefone)
        if caractere.isdigit()
    )

    # Celular com DDD
    # 12997135447 -> (12) 99713-5447
    if len(numeros) == 11:
        return (
            f"({numeros[:2]}) "
            f"{numeros[2:7]}-"
            f"{numeros[7:]}"
        )

    # Telefone fixo com DDD
    # 1236431234 -> (12) 3643-1234
    if len(numeros) == 10:
        return (
            f"({numeros[:2]}) "
            f"{numeros[2:6]}-"
            f"{numeros[6:]}"
        )

    # Caso esteja em outro formato
    return telefone
# =========================================================
# PDF - ORÇAMENTO DR REPAROS
# =========================================================

def desenhar_pagina_orcamento(canvas, doc):

    largura, altura = A4

    caminho_mascote = os.path.join(
        app.root_path,
        "static",
        "img",
        "mascote.png"
    )

    # =====================================================
    # MARCA D'ÁGUA
    # =====================================================

    if os.path.exists(caminho_mascote):

        canvas.saveState()

        try:
            canvas.setFillAlpha(0.06)
            canvas.setStrokeAlpha(0.06)
        except Exception:
            pass

        tamanho = 115 * mm

        canvas.drawImage(
            caminho_mascote,
            (largura - tamanho) / 2,
            (altura - tamanho) / 2,
            width=tamanho,
            height=tamanho,
            preserveAspectRatio=True,
            mask="auto"
        )

        canvas.restoreState()

    # =====================================================
    # RODAPÉ
    # =====================================================

    canvas.saveState()

    canvas.setStrokeColor(
        colors.HexColor("#FF7900")
    )

    canvas.setLineWidth(1)

    canvas.line(
        18 * mm,
        14 * mm,
        largura - 18 * mm,
        14 * mm
    )

    canvas.setFillColor(
        colors.HexColor("#666666")
    )

    canvas.setFont(
        "Helvetica",
        8
    )

    canvas.drawCentredString(
        largura / 2,
        9 * mm,
        "DR Reparos - Manutenção Residencial"
    )

    canvas.restoreState()


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/")
def inicio():

    hoje = date.today()

    quantidade_clientes = Cliente.query.count()
    quantidade_orcamentos = Orcamento.query.count()

    aguardando = Orcamento.query.filter(
        Orcamento.status.notin_(["Aprovado", "Não aprovado"])
    ).count()
    aprovados = Orcamento.query.filter_by(status="Aprovado").count()
    nao_aprovados = Orcamento.query.filter_by(status="Não aprovado").count()

    decididos = aprovados + nao_aprovados
    taxa_conversao = round((aprovados / decididos) * 100, 1) if decididos else 0

    # REGRA DO NEGÓCIO: orçamento aprovado já é faturamento.
    data_faturamento = func.coalesce(Orcamento.data_aprovacao, Orcamento.data_orcamento)
    faturamento = db.session.query(
        func.coalesce(func.sum(Orcamento.valor), 0)
    ).filter(
        Orcamento.status == "Aprovado",
        func.extract("month", data_faturamento) == hoje.month,
        func.extract("year", data_faturamento) == hoje.year
    ).scalar()
    faturamento = Decimal(faturamento or 0)

    custos_servicos = db.session.query(
        func.coalesce(func.sum(Custo.valor), 0)
    ).filter(
        func.extract("month", Custo.data_custo) == hoje.month,
        func.extract("year", Custo.data_custo) == hoje.year
    ).scalar()
    custos_servicos = Decimal(custos_servicos or 0)

    despesas_gerais = db.session.query(
        func.coalesce(func.sum(Despesa.valor), 0)
    ).filter(
        func.extract("month", Despesa.data_despesa) == hoje.month,
        func.extract("year", Despesa.data_despesa) == hoje.year
    ).scalar()
    despesas_gerais = Decimal(despesas_gerais or 0)

    despesas_totais = custos_servicos + despesas_gerais
    resultado = faturamento - despesas_totais

    aprovados_mes = Orcamento.query.filter(
        Orcamento.status == "Aprovado",
        func.extract("month", data_faturamento) == hoje.month,
        func.extract("year", data_faturamento) == hoje.year
    ).count()
    ticket_medio = faturamento / aprovados_mes if aprovados_mes else Decimal("0.00")

    meta = Meta.query.filter_by(mes=hoje.month, ano=hoje.year).first()
    valor_meta = Decimal(meta.valor) if meta else Decimal("0.00")
    percentual_meta = min(round(float(faturamento / valor_meta * 100), 1), 100) if valor_meta > 0 else 0

    ultimos_orcamentos = Orcamento.query.order_by(Orcamento.id.desc()).limit(5).all()

    return render_template(
        "index.html",
        quantidade_clientes=quantidade_clientes,
        quantidade_orcamentos=quantidade_orcamentos,
        aguardando=aguardando,
        aprovados=aprovados,
        nao_aprovados=nao_aprovados,
        taxa_conversao=taxa_conversao,
        aprovados_mes=aprovados_mes,
        faturamento=faturamento,
        despesas_totais=despesas_totais,
        resultado=resultado,
        ticket_medio=ticket_medio,
        valor_meta=valor_meta,
        percentual_meta=percentual_meta,
        ultimos_orcamentos=ultimos_orcamentos
    )


# =========================================================
# CLIENTES
# =========================================================

@app.route("/clientes")
def clientes():

    lista_clientes = Cliente.query.order_by(
        Cliente.nome
    ).all()

    return render_template(
        "clientes.html",
        clientes=lista_clientes
    )


@app.route("/clientes/novo", methods=["GET", "POST"])
def novo_cliente():

    if request.method == "POST":

        novo = Cliente(
            nome=request.form["nome"].strip(),
            telefone=request.form["telefone"].strip(),
            email=request.form.get("email", "").strip() or None,
            endereco=request.form.get("endereco", "").strip() or None,
            observacoes=request.form.get(
                "observacoes", ""
            ).strip() or None
        )

        db.session.add(novo)
        db.session.commit()

        return redirect(url_for("clientes"))

    return render_template("novo_cliente.html")


@app.route("/clientes/novo-rapido", methods=["POST"])
def novo_cliente_rapido():

    nome = request.form.get("nome", "").strip()
    telefone = request.form.get("telefone", "").strip()
    email = request.form.get("email", "").strip() or None
    endereco = request.form.get("endereco", "").strip() or None
    observacoes = request.form.get("observacoes", "").strip() or None

    if not nome or not telefone:
        return {
            "sucesso": False,
            "erro": "Nome e telefone são obrigatórios."
        }, 400

    novo = Cliente(
        nome=nome,
        telefone=telefone,
        email=email,
        endereco=endereco,
        observacoes=observacoes
    )

    db.session.add(novo)
    db.session.commit()

    return {
        "sucesso": True,
        "cliente": {
            "id": novo.id,
            "nome": novo.nome
        }
    }

# =========================================================
# ORÇAMENTOS
# =========================================================

@app.route("/orcamentos")
def orcamentos():

    lista = Orcamento.query.order_by(
        Orcamento.id.desc()
    ).all()

    return render_template(
        "orcamentos.html",
        orcamentos=lista
    )


@app.route("/orcamentos/novo", methods=["GET", "POST"])
def novo_orcamento():

    lista_clientes = Cliente.query.order_by(Cliente.nome).all()
    lista_catalogo = CatalogoServico.query.filter_by(ativo=True).order_by(
        CatalogoServico.descricao.asc()
    ).all()
    lista_materiais = Material.query.filter_by(ativo=True).order_by(Material.descricao.asc()).all()

    if request.method == "POST":
        cliente_id = int(request.form["cliente_id"])
        validade_dias = int(request.form.get("validade_dias", 15))
        observacoes = request.form.get("observacoes", "").strip() or None

        tipos = request.form.getlist("item_tipo")
        descricoes = request.form.getlist("item_descricao")
        quantidades = request.form.getlist("item_quantidade")
        valores = request.form.getlist("item_valor")

        itens = []
        for tipo, descricao, quantidade_texto, valor_texto in zip(
            tipos, descricoes, quantidades, valores
        ):
            tipo = "Material" if tipo == "Material" else "Serviço"
            descricao = descricao.strip()
            if not descricao:
                continue
            quantidade = Decimal(int(Decimal(quantidade_texto.replace(",", ".") or "1")))
            valor_unitario = Decimal(valor_texto.replace(",", ".") or "0")
            if quantidade <= 0:
                continue
            valor_total = (quantidade * valor_unitario).quantize(Decimal("0.01"))
            itens.append((tipo, descricao, quantidade, valor_unitario, valor_total))

        # Compatibilidade com o formulário antigo.
        if not itens:
            descricao = request.form.get("descricao", "").strip()
            valor_texto = request.form.get("valor", "0").strip().replace(",", ".")
            if descricao:
                valor = Decimal(valor_texto or "0")
                itens.append(("Serviço", descricao, Decimal("1"), valor, valor))

        if not itens:
            return redirect(url_for("novo_orcamento"))

        total = sum((item[4] for item in itens), Decimal("0.00"))
        descricao_resumo = "\n".join(
            f"{int(item[2])}x - {item[1]}" for item in itens
        )

        novo = Orcamento(
            cliente_id=cliente_id,
            descricao=descricao_resumo,
            valor=total,
            validade_dias=validade_dias,
            status="Aguardando aprovação",
            observacoes=observacoes
        )

        db.session.add(novo)
        db.session.flush()

        for tipo, descricao, quantidade, valor_unitario, valor_total in itens:
            db.session.add(OrcamentoItem(
                orcamento_id=novo.id,
                tipo=tipo,
                descricao=descricao,
                quantidade=quantidade,
                valor_unitario=valor_unitario,
                valor_total=valor_total
            ))

        db.session.commit()
        return redirect(url_for("orcamentos"))

    return render_template(
        "novo_orcamento.html",
        clientes=lista_clientes,
        catalogo=lista_catalogo,
        materiais=lista_materiais
    )


@app.route("/orcamentos/<int:id>/editar", methods=["GET", "POST"])
def editar_orcamento(id):

    orcamento = db.get_or_404(Orcamento, id)

    if orcamento.status != "Aguardando aprovação":
        return redirect(url_for("orcamentos"))

    lista_clientes = Cliente.query.order_by(Cliente.nome).all()
    lista_catalogo = CatalogoServico.query.filter_by(ativo=True).order_by(
        CatalogoServico.descricao.asc()
    ).all()

    itens_tela = orcamento.itens[:] if orcamento.itens else [{
        "tipo": "Serviço",
        "descricao": orcamento.descricao,
        "quantidade": Decimal("1"),
        "valor_unitario": Decimal(orcamento.valor or 0),
        "valor_total": Decimal(orcamento.valor or 0)
    }]
    lista_materiais = Material.query.filter_by(ativo=True).order_by(Material.descricao.asc()).all()

    if request.method == "POST":
        cliente_id = int(request.form["cliente_id"])
        validade_dias = int(request.form.get("validade_dias", 15))
        observacoes = request.form.get("observacoes", "").strip() or None

        tipos = request.form.getlist("item_tipo")
        descricoes = request.form.getlist("item_descricao")
        quantidades = request.form.getlist("item_quantidade")
        valores = request.form.getlist("item_valor")

        itens = []
        for tipo, descricao, quantidade_texto, valor_texto in zip(
            tipos, descricoes, quantidades, valores
        ):
            tipo = "Material" if tipo == "Material" else "Serviço"
            descricao = descricao.strip()
            if not descricao:
                continue
            quantidade = Decimal(int(Decimal(quantidade_texto.replace(",", ".") or "1")))
            valor_unitario = Decimal(valor_texto.replace(",", ".") or "0")
            if quantidade <= 0:
                continue
            valor_total = (quantidade * valor_unitario).quantize(Decimal("0.01"))
            itens.append((tipo, descricao, quantidade, valor_unitario, valor_total))

        if not itens:
            return redirect(url_for("editar_orcamento", id=id))

        orcamento.cliente_id = cliente_id
        orcamento.valor = sum((item[4] for item in itens), Decimal("0.00"))
        orcamento.validade_dias = validade_dias
        orcamento.observacoes = observacoes
        orcamento.descricao = "\n".join(
            f"{int(item[2])}x - {item[1]}" for item in itens
        )

        for item in list(orcamento.itens):
            db.session.delete(item)
        db.session.flush()

        for tipo, descricao, quantidade, valor_unitario, valor_total in itens:
            db.session.add(OrcamentoItem(
                orcamento_id=orcamento.id,
                tipo=tipo,
                descricao=descricao,
                quantidade=quantidade,
                valor_unitario=valor_unitario,
                valor_total=valor_total
            ))

        db.session.commit()
        return redirect(url_for("orcamentos"))

    return render_template(
        "novo_orcamento.html",
        clientes=lista_clientes,
        catalogo=lista_catalogo,
        materiais=lista_materiais,
        orcamento=orcamento,
        itens_edicao=itens_tela
    )


@app.route("/orcamentos/<int:id>/aprovar", methods=["POST"])
def aprovar_orcamento(id):
    orcamento = db.get_or_404(Orcamento, id)
    orcamento.status = "Aprovado"
    orcamento.motivo_perda = None
    orcamento.data_aprovacao = date.today()
    db.session.commit()
    return redirect(url_for("orcamentos"))


@app.route("/orcamentos/<int:id>/recusar", methods=["POST"])
def recusar_orcamento(id):

    orcamento = db.get_or_404(Orcamento, id)

    motivo = request.form.get(
        "motivo_perda",
        ""
    ).strip()

    orcamento.status = "Não aprovado"
    orcamento.motivo_perda = motivo or "Não informado"

    db.session.commit()

    return redirect(url_for("orcamentos"))
@app.route("/orcamentos/<int:id>/pdf")
def gerar_orcamento_pdf(id):

    orcamento = db.get_or_404(Orcamento, id)

    empresa = ConfiguracaoEmpresa.query.first()

    buffer = BytesIO()

    documento = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=20 * mm
    )

    elementos = []

    estilos = getSampleStyleSheet()

    estilo_normal = ParagraphStyle(
        "NormalDR",
        parent=estilos["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=15,
        textColor=colors.HexColor("#333333")
    )

    estilo_laranja = ParagraphStyle(
        "LaranjaDR",
        parent=estilo_normal,
        fontName="Helvetica-Bold",
        fontSize=11,
        textColor=colors.HexColor("#FF7900")
    )

    caminho_mascote = os.path.join(
        app.root_path,
        "static",
        "img",
        "mascote.png"
    )

    # =====================================================
    # CABEÇALHO
    # =====================================================

    if os.path.exists(caminho_mascote):
        mascote = Image(
            caminho_mascote,
            width=30 * mm,
            height=30 * mm
        )
    else:
        mascote = Paragraph("", estilo_normal)

    nome_empresa = (
        empresa.nome_empresa
        if empresa and empresa.nome_empresa
        else "DR Reparos"
    )

    contatos = []

    if empresa:

        if empresa.telefone:
            contatos.append(
            f"WhatsApp: {formatar_telefone(empresa.telefone)}"
        )

        if empresa.email:
            contatos.append(
                f"E-mail: {empresa.email}"
            )

        if empresa.instagram:
            contatos.append(
                f"Instagram: {empresa.instagram}"
            )

    dados_contato = "<br/>".join(contatos)

    dados_empresa = Paragraph(
        f"""
        <font size="18">
            <b>{nome_empresa}</b>
        </font>
        <br/>

        <font color="#FF7900">
            <b>Manutenção Residencial</b>
        </font>

        <br/><br/>

        {dados_contato}
        """,
        estilo_normal
    )

    numero_orcamento = Paragraph(
        f"""
        <para alignment="right">

            <font
                size="9"
                color="#777777"
            >
                ORÇAMENTO
            </font>

            <br/>

            <font size="18">
                <b>#{orcamento.id:04d}</b>
            </font>

        </para>
        """,
        estilo_normal
    )

    cabecalho = Table(
        [[
            mascote,
            dados_empresa,
            numero_orcamento
        ]],
        colWidths=[
            32 * mm,
            100 * mm,
            42 * mm
        ]
    )

    cabecalho.setStyle(
        TableStyle([
            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "MIDDLE"
            ),
            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                10
            )
        ])
    )

    elementos.append(cabecalho)

    # Linha laranja

    linha = Table(
        [[""]],
        colWidths=[174 * mm],
        rowHeights=[2 * mm]
    )

    linha.setStyle(
        TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (-1, -1),
                colors.HexColor("#FF7900")
            )
        ])
    )

    elementos.append(linha)

    elementos.append(
        Spacer(1, 7 * mm)
    )

    # =====================================================
    # DATA E VALIDADE
    # =====================================================

    if orcamento.data_orcamento:
        data_orcamento = orcamento.data_orcamento.strftime(
            "%d/%m/%Y"
        )
    else:
        data_orcamento = "-"

    validade = orcamento.validade_dias or 0

    if orcamento.data_orcamento and validade > 0:
        data_limite = (
            orcamento.data_orcamento
            + timedelta(days=validade)
        )
        validade_texto = (
            f"{validade} dias - "
            f"até {data_limite.strftime('%d/%m/%Y')}"
        )
    else:
        validade_texto = f"{validade} dias"

    dados_orcamento = Table(
        [
            [
                Paragraph(
                    "<b>Data do orçamento</b>",
                    estilo_normal
                ),
                Paragraph(
                    "<b>Validade</b>",
                    estilo_normal
                )
            ],
            [
                data_orcamento,
                validade_texto
            ]
        ],
        colWidths=[
            87 * mm,
            87 * mm
        ]
    )

    dados_orcamento.setStyle(
        TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.HexColor("#F3F4F6")
            ),
            (
                "BOX",
                (0, 0),
                (-1, -1),
                0.5,
                colors.HexColor("#DDDDDD")
            ),
            (
                "INNERGRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.HexColor("#DDDDDD")
            ),
            (
                "PADDING",
                (0, 0),
                (-1, -1),
                8
            )
        ])
    )

    elementos.append(dados_orcamento)

    elementos.append(
        Spacer(1, 7 * mm)
    )

    # =====================================================
    # CLIENTE
    # =====================================================

    elementos.append(
        Paragraph(
            "CLIENTE",
            estilo_laranja
        )
    )

    elementos.append(
        Spacer(1, 2 * mm)
    )

    cliente = orcamento.cliente

    cliente_dados = (
        f"<b>{cliente.nome}</b>"
    )

    if cliente.telefone:
        cliente_dados += (
        f"<br/>Telefone: {formatar_telefone(cliente.telefone)}"
    )

    if cliente.email:
        cliente_dados += (
            f"<br/>E-mail: {cliente.email}"
        )

    if cliente.endereco:
        cliente_dados += (
            f"<br/>Endereço: {cliente.endereco}"
        )

    elementos.append(
        Paragraph(
            cliente_dados,
            estilo_normal
        )
    )

    elementos.append(
        Spacer(1, 7 * mm)
    )

    # =====================================================
    # SERVIÇOS / ITENS
    # =====================================================

    elementos.append(Paragraph("ITENS DO ORÇAMENTO", estilo_laranja))
    elementos.append(Spacer(1, 3 * mm))

    itens_pdf = orcamento.itens
    if not itens_pdf:
        itens_pdf = [
            type(
                "ItemLegado",
                (),
                {
                    "tipo": "Serviço",
                    "descricao": orcamento.descricao,
                    "quantidade": Decimal("1"),
                    "valor_unitario": Decimal(orcamento.valor or 0),
                    "valor_total": Decimal(orcamento.valor or 0)
                }
            )()
        ]

    def dinheiro(valor):
        return (
            f"R$ {Decimal(valor):,.2f}"
            .replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )

    tabela_dados = [[
        Paragraph("<b>Tipo</b>", estilo_normal),
        Paragraph("<b>Descrição</b>", estilo_normal),
        Paragraph("<b>Qtd.</b>", estilo_normal),
        Paragraph("<b>Valor unit.</b>", estilo_normal),
        Paragraph("<b>Total</b>", estilo_normal)
    ]]

    for item in itens_pdf:
        qtd = Decimal(item.quantidade or 0)
        unit = Decimal(item.valor_unitario or 0)
        total_item = Decimal(item.valor_total or (qtd * unit))
        tabela_dados.append([
            Paragraph(str(getattr(item, "tipo", "Serviço")), estilo_normal),
            Paragraph(str(item.descricao).replace("\n", "<br/>"), estilo_normal),
            str(int(qtd)),
            dinheiro(unit),
            dinheiro(total_item)
        ])

    tabela_servico = Table(
        tabela_dados,
        colWidths=[25 * mm, 61 * mm, 18 * mm, 35 * mm, 35 * mm],
        repeatRows=1
    )

    tabela_servico.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#FFF3E8")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#111111")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
        ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#FF7900")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
        ("PADDING", (0, 0), (-1, -1), 7)
    ]))

    elementos.append(tabela_servico)
    elementos.append(Spacer(1, 5 * mm))

    # =====================================================
    # TOTAL
    # =====================================================

    total = Table(
        [[
            Paragraph(
                "<b>TOTAL DO ORÇAMENTO</b>",
                estilo_normal
            ),
            Paragraph(
                f"""
                <para alignment="right">
                    <font size="15">
                        <b>{dinheiro(orcamento.valor)}</b>
                    </font>
                </para>
                """,
                estilo_normal
            )
        ]],
        colWidths=[
            110 * mm,
            64 * mm
        ]
    )

    total.setStyle(
        TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (-1, -1),
                colors.HexColor("#FFF3E8")
            ),
            (
                "BOX",
                (0, 0),
                (-1, -1),
                1,
                colors.HexColor("#FF7900")
            ),
            (
                "PADDING",
                (0, 0),
                (-1, -1),
                12
            )
        ])
    )

    elementos.append(total)

    elementos.append(
        Spacer(1, 7 * mm)
    )

    # =====================================================
    # OBSERVAÇÕES DO ORÇAMENTO
    # =====================================================

    if orcamento.observacoes:

        elementos.append(
            Paragraph(
                "OBSERVAÇÕES",
                estilo_laranja
            )
        )

        elementos.append(
            Spacer(1, 2 * mm)
        )

        elementos.append(
            Paragraph(
                orcamento.observacoes,
                estilo_normal
            )
        )

        elementos.append(
            Spacer(1, 5 * mm)
        )

    # =====================================================
    # INFORMAÇÕES PADRÃO DA EMPRESA
    # =====================================================

    if empresa:

        if empresa.texto_orcamento:

            elementos.append(
                Paragraph(
                    empresa.texto_orcamento,
                    estilo_normal
                )
            )

            elementos.append(
                Spacer(1, 4 * mm)
            )

        if empresa.observacoes_orcamento:

            elementos.append(
                Paragraph(
                    empresa.observacoes_orcamento,
                    estilo_normal
                )
            )

            elementos.append(
                Spacer(1, 5 * mm)
            )

        if empresa.formas_pagamento:

            elementos.append(
                Paragraph(
                    "FORMAS DE PAGAMENTO",
                    estilo_laranja
                )
            )

            elementos.append(
                Spacer(1, 2 * mm)
            )

            elementos.append(
                Paragraph(
                    empresa.formas_pagamento,
                    estilo_normal
                )
            )

        if empresa.pix:

            elementos.append(
                Spacer(1, 2 * mm)
            )

            elementos.append(
                Paragraph(
                    f"<b>PIX:</b> {empresa.pix}",
                    estilo_normal
                )
            )

    # =====================================================
    # GERAR PDF
    # =====================================================

    documento.build(
        elementos,
        onFirstPage=desenhar_pagina_orcamento,
        onLaterPages=desenhar_pagina_orcamento
    )

    buffer.seek(0)

    nome_arquivo = (
        f"Orcamento_DR_Reparos_"
        f"{orcamento.id:04d}.pdf"
    )

    return send_file(
        buffer,
        as_attachment=False,
        download_name=nome_arquivo,
        mimetype="application/pdf"
    )

# =========================================================
# SERVIÇOS
# =========================================================

@app.route("/servicos")
def servicos():

    lista = Servico.query.order_by(
        Servico.id.desc()
    ).all()

    return render_template(
        "servicos.html",
        servicos=lista
    )

@app.route("/servicos/<int:id>")
def detalhes_servico(id):

    servico = db.get_or_404(
        Servico,
        id
    )

    custos = Custo.query.filter_by(
        servico_id=servico.id
    ).order_by(
        Custo.id.asc()
    ).all()

    custo_total = sum(
        (
            Decimal(custo.valor or 0)
            for custo in custos
        ),
        Decimal("0.00")
    )

    valor_servico = Decimal(
        servico.valor or 0
    )

    resultado_servico = (
        valor_servico - custo_total
    )

    margem = (
        round(
            float(
                resultado_servico
                / valor_servico
                * 100
            ),
            1
        )
        if valor_servico > 0
        else 0
    )

    return render_template(
        "detalhes_servico.html",
        servico=servico,
        custos=custos,
        custo_total=custo_total,
        resultado_servico=resultado_servico,
        margem=margem
    )

@app.route(
    "/servicos/<int:id>/agendar",
    methods=["POST"]
)
def agendar_servico(id):

    servico = db.get_or_404(
        Servico,
        id
    )

    data_texto = request.form.get(
        "data_agendada",
        ""
    ).strip()

    if data_texto:

        servico.data_agendada = datetime.strptime(
            data_texto,
            "%Y-%m-%d"
        ).date()

    else:

        servico.data_agendada = None

    db.session.commit()

    return redirect(
        url_for(
            "detalhes_servico",
            id=servico.id
        )
    )


@app.route("/servicos/<int:id>/finalizar", methods=["GET", "POST"])
def finalizar_servico(id):

    servico = db.get_or_404(Servico, id)

    # Se já possui pagamento, o serviço já foi finalizado
    if servico.pagamento:
        return redirect(url_for("servicos"))

    # Materiais disponíveis
    materiais = Material.query.filter_by(
        ativo=True
    ).order_by(
        Material.descricao.asc()
    ).all()

    mensagem_erro = None

    if request.method == "POST":

        forma_pagamento = request.form[
            "forma_pagamento"
        ]

        deslocamento = Decimal(
            request.form.get("deslocamento") or "0"
        )

        outros = Decimal(
            request.form.get("outros") or "0"
        )

        # =====================================================
        # MATERIAIS CADASTRADOS
        # =====================================================

        materiais_ids = request.form.getlist(
            "material_id[]"
        )

        quantidades = request.form.getlist(
            "material_quantidade[]"
        )

        materiais_utilizados = []

        # Primeiro validamos tudo antes de alterar estoque
        for material_id, quantidade_texto in zip(
            materiais_ids,
            quantidades
        ):

            if not material_id:
                continue

            quantidade = int(
                quantidade_texto or 0
            )

            if quantidade <= 0:
                continue

            material = db.session.get(
                Material,
                int(material_id)
            )

            if not material:
                continue

            estoque_atual = (
                material.quantidade or 0
            )

            if quantidade > estoque_atual:

                mensagem_erro = (
                    f"Estoque insuficiente para "
                    f"{material.descricao}. "
                    f"Disponível: {estoque_atual}."
                )

                return render_template(
                    "finalizar_servico.html",
                    servico=servico,
                    materiais=materiais,
                    erro=mensagem_erro
                )

            materiais_utilizados.append(
                (
                    material,
                    quantidade
                )
            )

        # =====================================================
        # MATERIAL NÃO CADASTRADO
        # =====================================================

        material_manual_descricao = (
            request.form.get(
                "material_manual_descricao",
                ""
            ).strip()
        )

        material_manual_valor_texto = (
            request.form.get(
                "material_manual_valor",
                ""
            ).strip()
        )

        material_manual_valor = Decimal("0.00")

        if material_manual_valor_texto:

            material_manual_valor = Decimal(
                material_manual_valor_texto.replace(
                    ",",
                    "."
                )
            )

        # =====================================================
        # PAGAMENTO
        # =====================================================

        pagamento = Pagamento(
            servico_id=servico.id,
            valor=servico.valor,
            forma_pagamento=forma_pagamento,
            data_pagamento=date.today()
        )

        db.session.add(pagamento)

        # =====================================================
        # BAIXA DOS MATERIAIS
        # =====================================================

        for material, quantidade in materiais_utilizados:

            custo_unitario = Decimal(
                material.custo_medio or 0
            )

            custo_total = (
                custo_unitario *
                Decimal(quantidade)
            )

            # Baixa no estoque
            material.quantidade = (
                (material.quantidade or 0)
                - quantidade
            )

            # Registra custo no serviço
            custo_material = Custo(
                servico_id=servico.id,
                categoria="Material",
                descricao=(
                    f"{quantidade}x "
                    f"{material.descricao}"
                ),
                valor=custo_total,
                data_custo=date.today()
            )

            db.session.add(
                custo_material
            )

        # =====================================================
        # MATERIAL MANUAL
        # =====================================================

        if (
            material_manual_descricao
            and material_manual_valor > 0
        ):

            db.session.add(
                Custo(
                    servico_id=servico.id,
                    categoria="Material",
                    descricao=material_manual_descricao,
                    valor=material_manual_valor,
                    data_custo=date.today()
                )
            )

        # =====================================================
        # DESLOCAMENTO
        # =====================================================

        if deslocamento > 0:

            db.session.add(
                Custo(
                    servico_id=servico.id,
                    categoria="Deslocamento",
                    descricao="Deslocamento do atendimento",
                    valor=deslocamento,
                    data_custo=date.today()
                )
            )

        # =====================================================
        # OUTROS CUSTOS
        # =====================================================

        if outros > 0:

            db.session.add(
                Custo(
                    servico_id=servico.id,
                    categoria="Outros",
                    descricao="Outros custos do serviço",
                    valor=outros,
                    data_custo=date.today()
                )
            )

        # =====================================================
        # FINALIZA SERVIÇO
        # =====================================================

        servico.status = "Concluído"
        servico.data_servico = date.today()

        db.session.commit()

        return redirect(
            url_for("inicio")
        )

    return render_template(
        "finalizar_servico.html",
        servico=servico,
        materiais=materiais,
        erro=mensagem_erro
    )

# =========================================================
# FINANCEIRO
# =========================================================

@app.route("/financeiro")
def financeiro():
    orcamentos_aprovados = Orcamento.query.filter_by(status="Aprovado").order_by(
        func.coalesce(Orcamento.data_aprovacao, Orcamento.data_orcamento).desc(),
        Orcamento.id.desc()
    ).all()
    despesas = Despesa.query.order_by(Despesa.data_despesa.desc(), Despesa.id.desc()).all()
    total_entradas = db.session.query(func.coalesce(func.sum(Orcamento.valor), 0)).filter(
        Orcamento.status == "Aprovado"
    ).scalar()
    total_custos = db.session.query(func.coalesce(func.sum(Custo.valor), 0)).scalar()
    total_despesas = db.session.query(func.coalesce(func.sum(Despesa.valor), 0)).scalar()
    total_saidas = Decimal(total_custos or 0) + Decimal(total_despesas or 0)
    saldo = Decimal(total_entradas or 0) - total_saidas
    return render_template(
        "financeiro.html",
        orcamentos_aprovados=orcamentos_aprovados,
        despesas=despesas,
        total_entradas=total_entradas,
        total_saidas=total_saidas,
        saldo=saldo
    )


@app.route("/financeiro/despesa/nova", methods=["GET", "POST"])
def nova_despesa():

    if request.method == "POST":

        despesa = Despesa(
            categoria=request.form["categoria"],
            descricao=request.form["descricao"].strip(),
            valor=Decimal(request.form["valor"]),
            data_despesa=date.today()
        )

        db.session.add(despesa)
        db.session.commit()

        return redirect(url_for("financeiro"))

    return render_template("nova_despesa.html")


# =========================================================
# META
# =========================================================

@app.route("/meta", methods=["GET", "POST"])
def configurar_meta():

    hoje = date.today()

    meta = Meta.query.filter_by(
        mes=hoje.month,
        ano=hoje.year
    ).first()

    if request.method == "POST":

        valor = Decimal(request.form["valor"])

        if meta:
            meta.valor = valor
        else:
            meta = Meta(
                mes=hoje.month,
                ano=hoje.year,
                valor=valor
            )

            db.session.add(meta)

        db.session.commit()

        return redirect(url_for("inicio"))

    return render_template(
        "meta.html",
        meta=meta,
        mes=hoje.month,
        ano=hoje.year
    )


# =========================================================
# BANCO
# =========================================================
@app.route("/catalogo-servicos")
def catalogo_servicos():
    servicos_catalogo = CatalogoServico.query.order_by(
        CatalogoServico.descricao.asc()
    ).all()

    return render_template(
        "catalogo_servicos.html",
        servicos=servicos_catalogo
    )

@app.route("/catalogo-servicos/<int:id>/editar", methods=["GET", "POST"])
def editar_catalogo_servico(id):

    servico = CatalogoServico.query.get_or_404(id)

    if request.method == "POST":

        servico.descricao = request.form["descricao"].strip()

        servico.complemento = (
            request.form.get("complemento", "").strip() or None
        )

        servico.categoria = (
            request.form.get("categoria", "").strip() or None
        )

        valor = request.form["valor_base"].replace(",", ".")
        custo = request.form.get("custo_base", "0").replace(",", ".")

        servico.valor_base = float(valor)
        servico.custo_base = float(custo or 0)

        servico.ativo = request.form.get("ativo") == "on"

        db.session.commit()

        return redirect(url_for("catalogo_servicos"))

    return render_template(
        "editar_catalogo_servico.html",
        servico=servico
    )


# =========================================================
# MATERIAIS / ESTOQUE
# =========================================================

@app.route("/materiais", methods=["GET", "POST"])
def materiais():

    # CADASTRAR NOVO MATERIAL
    if request.method == "POST":

        codigo = request.form["codigo"].strip()
        descricao = request.form["descricao"].strip()

        # Verifica se o código já existe
        codigo_existente = Material.query.filter_by(
            codigo=codigo
        ).first()

        if codigo_existente:
            return redirect(url_for("materiais"))

        novo_material = Material(
            codigo=codigo,
            descricao=descricao,

            complemento=request.form.get(
                "complemento",
                ""
            ).strip() or None,

            categoria=request.form.get(
                "categoria",
                ""
            ).strip() or None,

            quantidade=int(
                request.form.get("quantidade") or 0
            ),

            custo_medio=Decimal(
                request.form.get("custo_medio") or "0"
            ),

            valor_venda=Decimal(
                request.form.get("valor_venda") or "0"
            ),

            estoque_minimo=int(
                request.form.get("estoque_minimo") or 0
            ),

            estoque_maximo=int(
                request.form.get("estoque_maximo") or 0
            ),

            ativo=True
        )

        db.session.add(novo_material)
        db.session.commit()

        return redirect(url_for("materiais"))


    # LISTAGEM
    lista_materiais = Material.query.order_by(
        Material.descricao.asc()
    ).all()


    # INDICADORES
    total_materiais = len(lista_materiais)

    estoque_baixo = 0
    sem_estoque = 0

    valor_estoque = Decimal("0.00")


    for material in lista_materiais:

        quantidade = material.quantidade or 0

        minimo = material.estoque_minimo or 0

        custo = Decimal(
            material.custo_medio or 0
        )

        valor_estoque += (
            Decimal(quantidade) * custo
        )


        if quantidade <= 0:
            sem_estoque += 1

        elif minimo > 0 and quantidade <= minimo:
            estoque_baixo += 1


    return render_template(
        "materiais.html",
        materiais=lista_materiais,
        total_materiais=total_materiais,
        estoque_baixo=estoque_baixo,
        sem_estoque=sem_estoque,
        valor_estoque=valor_estoque
    )


@app.route(
    "/materiais/<int:id>/editar",
    methods=["GET", "POST"]
)
def editar_material(id):

    material = db.get_or_404(
        Material,
        id
    )


    if request.method == "POST":

        material.codigo = request.form[
            "codigo"
        ].strip()

        material.descricao = request.form[
            "descricao"
        ].strip()

        material.complemento = (
            request.form.get(
                "complemento",
                ""
            ).strip() or None
        )

        material.categoria = (
            request.form.get(
                "categoria",
                ""
            ).strip() or None
        )

        material.quantidade = int(
            request.form.get(
                "quantidade"
            ) or 0
        )

        material.custo_medio = Decimal(
            request.form.get(
                "custo_medio"
            ) or "0"
        )

        material.valor_venda = Decimal(
            request.form.get(
                "valor_venda"
            ) or "0"
        )

        material.estoque_minimo = int(
            request.form.get(
                "estoque_minimo"
            ) or 0
        )

        material.estoque_maximo = int(
            request.form.get(
                "estoque_maximo"
            ) or 0
        )

        material.ativo = (
            request.form.get("ativo") == "on"
        )

        db.session.commit()

        return redirect(
            url_for("materiais")
        )


    return render_template(
        "editar_material.html",
        material=material
    )

@app.route(
    "/configuracoes",
    methods=["GET", "POST"]
)
def configuracoes():

    empresa = ConfiguracaoEmpresa.query.first()

    if not empresa:
        empresa = ConfiguracaoEmpresa(
            nome_empresa="DR Reparos"
        )

        db.session.add(empresa)
        db.session.commit()

    if request.method == "POST":

        empresa.nome_empresa = request.form.get(
            "nome_empresa",
            ""
        ).strip()

        empresa.documento = request.form.get(
            "documento",
            ""
        ).strip() or None

        empresa.telefone = request.form.get(
            "telefone",
            ""
        ).strip() or None

        empresa.email = request.form.get(
            "email",
            ""
        ).strip() or None

        empresa.instagram = request.form.get(
        "instagram",
        ""
        ).strip() or None

        empresa.endereco = request.form.get(
            "endereco",
            ""
        ).strip() or None

        empresa.cidade = request.form.get(
            "cidade",
            ""
        ).strip() or None

        empresa.estado = request.form.get(
            "estado",
            ""
        ).strip().upper() or None

        empresa.cep = request.form.get(
            "cep",
            ""
        ).strip() or None

        empresa.pix = request.form.get(
            "pix",
            ""
        ).strip() or None

        empresa.formas_pagamento = request.form.get(
            "formas_pagamento",
            ""
        ).strip() or None

        empresa.texto_orcamento = request.form.get(
            "texto_orcamento",
            ""
        ).strip() or None

        empresa.observacoes_orcamento = request.form.get(
            "observacoes_orcamento",
            ""
        ).strip() or None

        db.session.commit()

        return redirect(
            url_for("configuracoes")
        )

    return render_template(
        "configuracoes.html",
        empresa=empresa
    )


# Garante a criação de novas tabelas também no deploy via Gunicorn/Railway.
with app.app_context():
    db.create_all()
    # Migrações aditivas e seguras para instalações existentes no Neon.
    db.session.execute(text(
        "ALTER TABLE orcamentos ADD COLUMN IF NOT EXISTS data_aprovacao DATE"
    ))
    db.session.execute(text(
        "ALTER TABLE orcamento_itens ADD COLUMN IF NOT EXISTS tipo VARCHAR(20) DEFAULT 'Serviço'"
    ))
    db.session.execute(text(
        "UPDATE orcamento_itens SET tipo = 'Serviço' WHERE tipo IS NULL"
    ))
    db.session.commit()


if __name__ == "__main__":
    app.run(debug=True)