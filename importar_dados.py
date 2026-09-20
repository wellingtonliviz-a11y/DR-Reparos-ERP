import math
import re
from pathlib import Path
from openpyxl import load_workbook

from app import app, db, Cliente, CatalogoServico, Material


# ============================================================
# CONFIGURAÇÃO
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

ARQUIVO_CLIENTES = BASE_DIR / "clientes.xlsx"
ARQUIVO_SERVICOS = BASE_DIR / "Serviços.xlsx"
ARQUIVO_MATERIAIS = BASE_DIR / "material.xlsx"


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def texto(valor):
    """Converte valores da planilha para texto limpo."""
    if valor is None:
        return None

    valor = str(valor).strip()

    if not valor or valor.lower() in ("nan", "none"):
        return None

    return valor


def dinheiro(valor):
    """
    Converte:
    R$ 100,00
    R$ 1.250,50
    100
    100.50

    para float.
    """

    if valor is None:
        return 0.0

    if isinstance(valor, (int, float)):
        if isinstance(valor, float) and math.isnan(valor):
            return 0.0
        return float(valor)

    valor = str(valor).strip()

    if not valor or "nan" in valor.lower():
        return 0.0

    valor = valor.replace("R$", "").strip()
    valor = valor.replace(".", "")
    valor = valor.replace(",", ".")

    try:
        return float(valor)
    except ValueError:
        return 0.0


def inteiro(valor):
    if valor is None:
        return 0

    try:
        return int(float(valor))
    except (ValueError, TypeError):
        return 0


def somente_numeros(valor):
    if valor is None:
        return None

    numero = re.sub(r"\D", "", str(valor))

    return numero if numero else None


def cabecalhos(ws):
    """
    Cria um dicionário:
    Nome da coluna -> posição da coluna
    """

    resultado = {}

    for coluna, celula in enumerate(ws[1]):
        nome = texto(celula.value)

        if nome:
            resultado[nome] = coluna

    return resultado


# ============================================================
# CLIENTES
# ============================================================

def importar_clientes():

    print("\n======================================")
    print("IMPORTANDO CLIENTES")
    print("======================================")

    wb = load_workbook(ARQUIVO_CLIENTES, data_only=True)
    ws = wb.active

    col = cabecalhos(ws)

    adicionados = 0
    ignorados = 0

    for linha in ws.iter_rows(min_row=2, values_only=True):

        nome = texto(linha[col["Nome"]])
        telefone = somente_numeros(
            linha[col["Telefone Contato"]]
        )

        endereco = texto(
            linha[col["Endereço"]]
        )

        email = texto(
            linha[col["E-mail"]]
        )

        observacao = texto(
            linha[col["Observação"]]
        )

        if not nome:
            continue

        # -----------------------------------------
        # PROTEÇÃO CONTRA DUPLICIDADE
        # -----------------------------------------

        cliente_existente = None

        if telefone:
            cliente_existente = Cliente.query.filter_by(
                telefone=telefone
            ).first()

        if not cliente_existente:
            cliente_existente = Cliente.query.filter(
                db.func.lower(Cliente.nome) == nome.lower()
            ).first()

        if cliente_existente:
            print(f"IGNORADO: {nome}")
            ignorados += 1
            continue

        cliente = Cliente(
            nome=nome,
            telefone=telefone,
            email=email,
            endereco=endereco,
            observacoes=observacao
        )

        db.session.add(cliente)

        print(f"ADICIONADO: {nome}")

        adicionados += 1

    db.session.commit()

    return adicionados, ignorados


# ============================================================
# CATÁLOGO DE SERVIÇOS
# ============================================================

def importar_servicos():

    print("\n======================================")
    print("IMPORTANDO CATÁLOGO DE SERVIÇOS")
    print("======================================")

    wb = load_workbook(ARQUIVO_SERVICOS, data_only=True)
    ws = wb.active

    col = cabecalhos(ws)

    adicionados = 0
    ignorados = 0

    for linha in ws.iter_rows(min_row=2, values_only=True):

        codigo = texto(
            linha[col["Código"]]
        )

        descricao = texto(
            linha[col["Descrição Serviço"]]
        )

        complemento = texto(
            linha[col["Complemento"]]
        )

        categoria = texto(
            linha[col["Categoria"]]
        )

        custo = dinheiro(
            linha[col["Custo"]]
        )

        valor = dinheiro(
            linha[col["Valor"]]
        )

        if not codigo or not descricao:
            continue

        existente = CatalogoServico.query.filter_by(
            codigo=codigo
        ).first()

        if existente:
            print(
                f"IGNORADO: {codigo} - {descricao}"
            )

            ignorados += 1
            continue

        servico = CatalogoServico(
            codigo=codigo,
            descricao=descricao,
            complemento=complemento,
            categoria=categoria,
            custo_base=custo,
            valor_base=valor,
            ativo=True
        )

        db.session.add(servico)

        print(
            f"ADICIONADO: {codigo} - "
            f"{descricao} - R$ {valor:.2f}"
        )

        adicionados += 1

    db.session.commit()

    return adicionados, ignorados


# ============================================================
# MATERIAIS / ESTOQUE
# ============================================================

def importar_materiais():

    print("\n======================================")
    print("IMPORTANDO MATERIAIS")
    print("======================================")

    wb = load_workbook(ARQUIVO_MATERIAIS, data_only=True)
    ws = wb.active

    col = cabecalhos(ws)

    adicionados = 0
    ignorados = 0

    for linha in ws.iter_rows(min_row=2, values_only=True):

        codigo = texto(
            linha[col["Código"]]
        )

        descricao = texto(
            linha[col["Descrição"]]
        )

        complemento = texto(
            linha[col["Complemento"]]
        )

        categoria = texto(
            linha[col["Categoria"]]
        )

        quantidade = inteiro(
            linha[col["Qtdade Disponível"]]
        )

        custo_medio = dinheiro(
            linha[col["Custo Médio Unit."]]
        )

        valor_venda = dinheiro(
            linha[col["Valor Venda"]]
        )

        estoque_maximo = inteiro(
            linha[col["Estoque Máximo"]]
        )

        estoque_minimo = inteiro(
            linha[col["Estoque Mínimo"]]
        )

        if not codigo or not descricao:
            continue

        existente = Material.query.filter_by(
            codigo=codigo
        ).first()

        if existente:
            print(
                f"IGNORADO: {codigo} - {descricao}"
            )

            ignorados += 1
            continue

        material = Material(
            codigo=codigo,
            descricao=descricao,
            complemento=complemento,
            categoria=categoria,
            quantidade=quantidade,
            custo_medio=custo_medio,
            valor_venda=valor_venda,
            estoque_maximo=estoque_maximo,
            estoque_minimo=estoque_minimo,
            ativo=True
        )

        db.session.add(material)

        print(
            f"ADICIONADO: {codigo} - "
            f"{descricao} - "
            f"Estoque: {quantidade}"
        )

        adicionados += 1

    db.session.commit()

    return adicionados, ignorados


# ============================================================
# EXECUÇÃO
# ============================================================

if __name__ == "__main__":

    print("\n")
    print("==========================================")
    print("      DR REPAROS ERP - IMPORTAÇÃO")
    print("==========================================")

    arquivos = [
        ARQUIVO_CLIENTES,
        ARQUIVO_SERVICOS,
        ARQUIVO_MATERIAIS
    ]

    faltando = [
        arquivo.name
        for arquivo in arquivos
        if not arquivo.exists()
    ]

    if faltando:

        print("\nERRO!")

        print(
            "Os seguintes arquivos não foram encontrados:"
        )

        for arquivo in faltando:
            print(f"- {arquivo}")

        print(
            "\nColoque as três planilhas na mesma "
            "pasta do app.py."
        )

        exit()

    with app.app_context():

        try:

            clientes_add, clientes_ign = importar_clientes()

            servicos_add, servicos_ign = importar_servicos()

            materiais_add, materiais_ign = importar_materiais()

            print("\n")
            print("==========================================")
            print("         IMPORTAÇÃO CONCLUÍDA")
            print("==========================================")

            print("\nCLIENTES")
            print(f"Adicionados: {clientes_add}")
            print(f"Ignorados:   {clientes_ign}")

            print("\nSERVIÇOS")
            print(f"Adicionados: {servicos_add}")
            print(f"Ignorados:   {servicos_ign}")

            print("\nMATERIAIS")
            print(f"Adicionados: {materiais_add}")
            print(f"Ignorados:   {materiais_ign}")

            print("\nBanco de dados atualizado com sucesso.")

        except Exception as erro:

            db.session.rollback()

            print("\n==========================================")
            print("ERRO DURANTE A IMPORTAÇÃO")
            print("==========================================")

            print(erro)

            print(
                "\nNenhuma alteração da etapa que apresentou "
                "erro foi confirmada."
            )