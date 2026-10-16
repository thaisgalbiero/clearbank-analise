"""Versão reutilizável das funções do notebook (biblioteca padrão)."""
import csv
import json
import math
import re
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
LIMITE_SUSPEITO = 10000.0
COLUNAS = ['id', 'data', 'cliente_id', 'tipo', 'valor', 'descricao', 'categoria']

def ler_transacoes(caminho='transacoes.csv'):
    """Retorna registros brutos; None indica erro de arquivo, não base vazia."""
    try:
        with open(caminho, encoding='utf-8-sig', newline='') as arquivo:
            leitor = csv.DictReader(arquivo)
            if leitor.fieldnames != COLUNAS:
                print('Cabeçalho inválido. Colunas esperadas:', ', '.join(COLUNAS))
                return None
            return list(leitor)
    except FileNotFoundError:
        print(f'Arquivo não encontrado: {caminho}. Coloque o CSV na pasta do notebook.')
        return None
    except (OSError, UnicodeError, csv.Error) as erro:
        print(f'Não foi possível ler o CSV: {erro}')
        return None

def validar_transacao(linha):
    """Descarta erros silenciosamente; mantém descrição e categoria opcionais."""
    if set(linha) != set(COLUNAS) or any((v is None for v in linha.values())):
        return None
    registro = {chave: valor.strip() for chave, valor in linha.items()}
    if not re.fullmatch('[0-9]+', registro['id']) or not registro['cliente_id']:
        return None
    if registro['tipo'] not in ('credito', 'debito'):
        return None
    try:
        valor = float(registro['valor'])
    except (ValueError, OverflowError):
        return None
    if not math.isfinite(valor) or valor <= 0:
        return None
    try:
        data = datetime.strptime(registro['data'], '%Y-%m-%d')
    except ValueError:
        return None
    if not re.fullmatch('[0-9]{4}-[0-9]{2}-[0-9]{2}', registro['data']):
        return None
    registro.update(id=int(registro['id']), data=data, valor=Decimal(registro['valor']), suspeita=valor > LIMITE_SUSPEITO)
    return registro

def limpar_transacoes(linhas):
    """Primeiro registro válido de cada ID prevalece; duplicatas são descartes."""
    validas, ids = ([], set())
    invalidas = duplicadas = 0
    for linha in linhas:
        registro = validar_transacao(linha)
        if registro is None:
            invalidas += 1
        elif registro['id'] in ids:
            invalidas += 1
            duplicadas += 1
        else:
            ids.add(registro['id'])
            validas.append(registro)
    return (validas, invalidas, duplicadas)

def numero(valor):
    """Arredonda a apresentação a centavos, mantendo Decimal nos cálculos."""
    return float(valor.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))

def serializar_transacao(transacao):
    return {**transacao, 'data': transacao['data'].strftime('%Y-%m-%d'), 'valor': numero(transacao['valor'])}

def resumir_mes(transacoes):
    credito = sum((t['valor'] for t in transacoes if t['tipo'] == 'credito'), Decimal(0))
    debito = sum((t['valor'] for t in transacoes if t['tipo'] == 'debito'), Decimal(0))
    maior = max(transacoes, key=lambda t: t['valor'])
    menor = min(transacoes, key=lambda t: t['valor'])
    return {'quantidade': len(transacoes), 'total_credito': numero(credito), 'total_debito': numero(debito), 'saldo': numero(credito - debito), 'media': numero((credito + debito) / len(transacoes)), 'maior_valor': numero(maior['valor']), 'menor_valor': numero(menor['valor']), 'maior_transacao': serializar_transacao(maior), 'menor_transacao': serializar_transacao(menor)}

def gerar_relatorio(transacoes, invalidas=0, duplicadas=0, hoje=None):
    hoje = hoje or date.today()
    grupos = {}
    for transacao in transacoes:
        mes = transacao['data'].strftime('%Y-%m')
        grupos.setdefault(mes, []).append(transacao)
    periodo = None
    if transacoes:
        inicio = min((t['data'].date() for t in transacoes))
        fim = max((t['data'].date() for t in transacoes))
        periodo = {'inicio': inicio.isoformat(), 'fim': fim.isoformat(), 'dias_desde_mais_antiga': (hoje - inicio).days, 'dias_desde_mais_recente': (hoje - fim).days}
    return {'gerado_em': hoje.isoformat(), 'total_transacoes_validas': len(transacoes), 'total_transacoes_invalidas': invalidas, 'total_duplicadas': duplicadas, 'total_linhas_lidas': len(transacoes) + invalidas, 'periodo': periodo, 'resumo_mensal': {mes: resumir_mes(grupos[mes]) for mes in sorted(grupos)}, 'transacoes_suspeitas': [serializar_transacao(t) for t in transacoes if t['suspeita']]}

def salvar_json(relatorio, caminho='relatorio.json'):
    try:
        with open(caminho, 'w', encoding='utf-8') as arquivo:
            json.dump(relatorio, arquivo, ensure_ascii=False, indent=2, allow_nan=False)
    except OSError as erro:
        print(f'Falha ao salvar JSON: {erro}')
        return False
    return True

def moeda(valor):
    return f'R$ {valor:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')

def exibir_relatorio(relatorio):
    print('===== LIMPEZA DOS DADOS =====')
    print(f"Total de linhas lidas: {relatorio['total_linhas_lidas']}")
    print(f"Linhas válidas: {relatorio['total_transacoes_validas']}")
    print(f"Linhas inválidas: {relatorio['total_transacoes_invalidas']}")
    print(f"Duplicatas incluídas nos descartes: {relatorio['total_duplicadas']}")
    periodo = relatorio['periodo']
    if periodo:
        print(f"Período analisado: {periodo['inicio']} → {periodo['fim']}")
        print(f"Dias desde a mais antiga: {periodo['dias_desde_mais_antiga']}")
        print(f"Dias desde a mais recente: {periodo['dias_desde_mais_recente']}")
    else:
        print('Sem transações válidas para analisar.')
    print('\n===== RELATÓRIO MENSAL =====')
    campos = [('total_credito', 'Total crédito'), ('total_debito', 'Total débito'), ('saldo', 'Saldo'), ('media', 'Média'), ('maior_valor', 'Maior valor'), ('menor_valor', 'Menor valor')]
    for mes, dados in relatorio['resumo_mensal'].items():
        print(f"\nMês: {mes}\n  Transações: {dados['quantidade']}")
        for chave, rotulo in campos:
            print(f'  {rotulo}: {moeda(dados[chave])}')
    print('\n===== TRANSAÇÕES SUSPEITAS =====')
    if not relatorio['transacoes_suspeitas']:
        print('Nenhuma transação suspeita encontrada.')
    for t in relatorio['transacoes_suspeitas']:
        print(f"ID: {t['id']} | Cliente: {t['cliente_id']} | Data: {t['data']} | Valor: {moeda(t['valor'])}")
from tempfile import TemporaryDirectory

def executar(caminho='transacoes.csv'):
    linhas = ler_transacoes(caminho)
    if linhas is None:
        return None
    transacoes, invalidas, duplicadas = limpar_transacoes(linhas)
    relatorio = gerar_relatorio(transacoes, invalidas, duplicadas)
    exibir_relatorio(relatorio)
    if salvar_json(relatorio):
        print('\nArquivo relatorio.json salvo com sucesso.')
    return relatorio

if __name__ == "__main__":
    executar()
