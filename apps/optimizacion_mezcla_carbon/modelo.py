import pandas as pd
from collections import OrderedDict
from pulp import *
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import seaborn as sns
import io
import base64

sns.set_theme(style="ticks")

def procesar_archivo(filepath, solo_mineros, limite_comercializadores, modelo='precio'):
    hoja = pd.read_excel(filepath, sheet_name=0, header=None, engine='openpyxl')
    df = hoja.iloc[2:, 0:13].copy()
    df.columns = hoja.iloc[1, 0:13]
    df = df[df['Disponible'].notnull() & df['Precio'].notnull()]
    df[['Disponible', 'Precio', 'HT', 'CZ', 'MV', 'S', 'FSI']] = df[['Disponible', 'Precio', 'HT', 'CZ', 'MV', 'S', 'FSI']].apply(pd.to_numeric, errors='coerce')
    df = df[df['Disponible'] > 0]
    df = df.drop_duplicates(subset=['Mina', 'Tipo']).sort_values(['Mina', 'Tipo'])

    if solo_mineros:
        df = df[df['Clasificación'] == 'Minero']

    df['Costo_CCB'] = df['Precio'] / ((1 - df['MV']) / (1 - 0.012))

    requerimiento_total = float(hoja.iloc[2, 14])
    calidad_esperada = hoja.iloc[2, 16:20]
    calidad_esperada.index = hoja.iloc[1, 16:20]
    calidad_esperada_dict = calidad_esperada.to_dict()

    limites = hoja.iloc[2:, 21:23].dropna()
    limites.columns = hoja.iloc[1, 21:23]
    limites_dict = dict(zip(limites['TIPO'], limites['LIMITE']))

    pares = list(OrderedDict.fromkeys(zip(df['Mina'], df['Tipo'])))
    comercializadores = df[df['Clasificación'] == 'Comercializador']
    pares_comercializadores = list(zip(comercializadores['Mina'], comercializadores['Tipo']))
    atributos = ['Costo_CCB', 'Precio', 'Disponible', 'HT', 'CZ', 'MV', 'S', 'FSI']
    datos = {atr: {(p, t): row[atr] for p, t, row in zip(df['Mina'], df['Tipo'], df.to_dict('records'))} for atr in atributos}
    tipos = df['Tipo'].unique().tolist()

    model = LpProblem("Optimizacion_Compras_Carbon", LpMinimize)
    x = LpVariable.dicts("Pedido", pares, lowBound=0, cat='Continuous')

    if modelo == 'costo_ccb':
        model += lpSum(x[par] * datos['Costo_CCB'][par] for par in pares)
    else:
        model += lpSum(x[par] * datos['Precio'][par] for par in pares)

    model += lpSum(x[par] for par in pares) == requerimiento_total

    for par in pares:
        model += x[par] <= datos['Disponible'][par]

    for tipo in tipos:
        limite = limites_dict.get(tipo, 1)
        model += lpSum(x[par] for par in pares if par[1] == tipo) <= limite * requerimiento_total

    total_pedido = lpSum(x[par] for par in pares)
    model += lpSum(x[par] * datos['S'][par] for par in pares) <= calidad_esperada_dict['S'] * total_pedido
    model += lpSum(x[par] * datos['FSI'][par] for par in pares) >= calidad_esperada_dict['FSI'] * total_pedido
    model += lpSum(x[par] * datos['CZ'][par] for par in pares) <= calidad_esperada_dict['CZ'] * total_pedido
    model += lpSum(x[par] * datos['MV'][par] for par in pares) <= calidad_esperada_dict['MV'] * total_pedido

    model += lpSum(x[par] for par in pares_comercializadores) <= limite_comercializadores * requerimiento_total

    model.solve()

    solucion = {par: x[par].varValue for par in pares if x[par].varValue > 0}
    df_sol = pd.DataFrame([{"Mina": p, "Tipo": t, "Toneladas": val} for (p, t), val in solucion.items()])
    df_sol = df_sol.merge(df[['Proveedor', 'Mina', 'Tipo', 'Clasificación']], on=['Mina', 'Tipo'], how='left')
    df_sol["Toneladas"] = df_sol["Toneladas"].round(2)
    df_sol = df_sol[['Proveedor','Mina','Tipo','Toneladas','Clasificación']]
    tabla_resultados = df_sol.to_html(index=False, classes="table table-striped table-bordered", table_id='tabla_resultados')

    total = sum(solucion.values())
    s_prom = sum(datos['S'][par] * cantidad for par, cantidad in solucion.items()) / total
    fsi_prom = sum(datos['FSI'][par] * cantidad for par, cantidad in solucion.items()) / total
    cz_prom = sum(datos['CZ'][par] * cantidad for par, cantidad in solucion.items()) / total
    mv_prom = sum(datos['MV'][par] * cantidad for par, cantidad in solucion.items()) / total

    df_resultado = pd.merge(df_sol, df[['Mina', 'Precio']], on='Mina', how='left')
    df_resultado['Total'] = df_resultado['Toneladas'] * df_resultado['Precio']
    costo_total = df_resultado['Total'].sum()

    rendimiento = ((1 - mv_prom) / (1 - 0.012))
    coque_bruto_producido = total * rendimiento
    costo_unitario_cbp = costo_total / coque_bruto_producido

    resumen = {
        'S (%)': f"{s_prom * 100:.2f}",
        'FSI': f"{fsi_prom:.2f}",
        'CZ (%)': f"{cz_prom * 100:.2f}",
        'MV (%)': f"{mv_prom * 100:.2f}",
        'Costo Total ($)': f"{costo_total:,.2f}",
        'Rendimiento Coque Bruto (%)': f"{rendimiento * 100:.2f}",
        'Total Coque Bruto Producido': f"{coque_bruto_producido:,.2f}",
        'Costo Unitario Coque Bruto ($/t)': f"{costo_unitario_cbp:,.2f}"
    }
    df_resumen = pd.DataFrame([resumen])
    tabla_resumen = df_resumen.to_html(index=False, classes="table table-bordered")

    tipo_cantidad = df_sol.groupby("Tipo")["Toneladas"].sum()
    colors = sns.color_palette("colorblind", n_colors=len(tipo_cantidad))
    fig1, ax1 = plt.subplots(figsize=(4, 4))
    ax1.pie(tipo_cantidad, labels=tipo_cantidad.index, autopct='%1.1f%%', startangle=90, colors=colors, textprops={'fontsize': 8})
    ax1.axis('equal')
    img_bytes = io.BytesIO()
    plt.savefig(img_bytes, format='png', bbox_inches='tight')
    img_bytes.seek(0)
    grafico_torta = base64.b64encode(img_bytes.read()).decode('utf-8')
    plt.close()

    pivot_df = df_sol.pivot_table(index='Mina', columns='Tipo', values='Toneladas', aggfunc='sum', fill_value=0)
    pivot_df['Total'] = pivot_df.sum(axis=1)
    pivot_df = pivot_df.sort_values('Total', ascending=False)
    valores_df = pivot_df.drop(columns='Total')

    fig2, ax2 = plt.subplots(figsize=(10, 5))
    bottom = [0] * len(valores_df)
    palette = sns.color_palette("colorblind", n_colors=len(valores_df.columns))
    x = range(len(valores_df))

    for i, tipo in enumerate(valores_df.columns):
        valores = valores_df[tipo].values
        ax2.bar(x, valores, bottom=bottom, label=tipo, color=palette[i], alpha=0.7)
        bottom = [bottom[j] + valores[j] for j in range(len(valores))]

    ax2.set_xticks(x)
    ax2.set_xticklabels(valores_df.index, rotation=45, ha='right', fontsize=8)
    ax2.set_ylabel("Toneladas")
    ax2.legend(title='Tipo', bbox_to_anchor=(1.01, 1), loc='upper left')
    img_bytes2 = io.BytesIO()
    plt.tight_layout()
    plt.savefig(img_bytes2, format='png')
    img_bytes2.seek(0)
    grafico_barras = base64.b64encode(img_bytes2.read()).decode('utf-8')
    plt.close()

    estado_modelo = LpStatus[model.status]
    estado_traducido = {
        'Optimal': 'Óptimo',
        'Infeasible': 'Inviable',
        'Unbounded': 'Sin acotar',
        'Undefined': 'Indefinido',
        'Not Solved': 'No resuelto'
    }.get(estado_modelo, estado_modelo)


    return {
        'estado': estado_traducido,
        'tabla_resultados': tabla_resultados,
        'tabla_resumen': tabla_resumen,
        'grafico_torta': grafico_torta,
        'grafico_barras': grafico_barras,
        'df_sol': df_sol,
        'modelo_usado': modelo
    }