"""Leitura alternativa e agrupamento com pandas; validação compartilhada."""
from decimal import Decimal
import pandas as pd
from analise_nativa import COLUNAS, limpar_transacoes, numero


def analisar_pandas(caminho='transacoes.csv'):
    dados = pd.read_csv(caminho, dtype=str, keep_default_na=False)
    if list(dados.columns) != COLUNAS:
        raise ValueError('Cabeçalho inválido')
    validas, invalidas, duplicadas = limpar_transacoes(dados.to_dict('records'))
    if not validas:
        return {}, invalidas, duplicadas
    df = pd.DataFrame(validas)
    df['mes'] = df['data'].dt.strftime('%Y-%m')
    df['credito'] = df.apply(lambda t: t['valor'] if t['tipo'] == 'credito' else Decimal(0), axis=1)
    df['debito'] = df.apply(lambda t: t['valor'] if t['tipo'] == 'debito' else Decimal(0), axis=1)
    grupos = df.groupby('mes', sort=True).agg(
        quantidade=('id', 'size'), total_credito=('credito', 'sum'),
        total_debito=('debito', 'sum'), total=('valor', 'sum'),
        maior_valor=('valor', 'max'), menor_valor=('valor', 'min'))
    resumo = {}
    for mes, t in grupos.iterrows():
        resumo[mes] = {'quantidade': int(t['quantidade']),
            'total_credito': numero(t['total_credito']), 'total_debito': numero(t['total_debito']),
            'saldo': numero(t['total_credito'] - t['total_debito']),
            'media': numero(t['total'] / int(t['quantidade'])),
            'maior_valor': numero(t['maior_valor']), 'menor_valor': numero(t['menor_valor'])}
    return resumo, invalidas, duplicadas


if __name__ == '__main__':
    from pprint import pprint
    pprint(analisar_pandas())
