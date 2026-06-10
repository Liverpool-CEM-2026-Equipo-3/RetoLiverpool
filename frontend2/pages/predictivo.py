import dash
import httpx
import base64
import io
import pandas as pd
from dash import html, dcc, callback, Input, Output, State

dash.register_page(
    __name__,
    path="/predictivo",
    title="Predictivo",
    name="predictivo"
)

API_URL = "http://localhost:8000"

def asignar_porcentaje_cogs(texto):
    texto = str(texto).upper()
    if "PUBLICIDAD" in texto or "GESTION" in texto or "ADMINISTRACION" in texto or "TRABAJOS DE OFICINA" in texto:
        return 0.15
    elif "PRENDAS DE VESTIR" in texto or "VESTUARIO" in texto or "CALZADO" in texto or "SOMBRERERIA" in texto:
        return 0.42
    elif "JOYERIA" in texto or "RELOJERIA" in texto or "METALES PRECIOSOS" in texto:
        return 0.55
    elif "ALIMENTOS" in texto or "LIMPIEZA" in texto or "FERRETERIA" in texto or "VELAS" in texto:
        return 0.60
    else:
        return 0.48

def input_field(label, input_id, val, ph, **kwargs):
    return html.Div(
        className="flex flex-col gap-1",
        children=[
            html.Label(label, className="text-xs font-semibold text-[#5f3f5d] uppercase tracking-wider"),
            dcc.Input(
                id=input_id,
                type="text",
                value=val,
                placeholder=ph,
                debounce=False,
                style={
                    "width": "100%",
                    "padding": "12px 16px",
                    "background": "white",
                    "border": "2px solid #f7c0dd",
                    "borderRadius": "12px",
                    "fontSize": "15px",
                    "color": "#331b35",
                    "outline": "none",
                    "boxSizing": "border-box",
                    "fontFamily": "inherit",
                    "boxShadow": "inset 0 1px 3px rgba(255,79,153,0.05)",
                },
                **kwargs
            )
        ]
    )

async def layout():
    return html.Div(
        className="mx-auto px-6 py-12 max-w-7xl space-y-10",
        children=[

            # HEADER
            html.Div(className="space-y-2", children=[
                html.P(className="inline-flex bg-[#ffd2e8] px-4 py-1 rounded-full font-semibold text-[#993556] text-xs uppercase tracking-[0.25em]", children=["Modelo predictivo"]),
                html.H1(className="font-extrabold text-[#331b35] text-4xl", children=["Predicción de renovación de marca"]),
                html.P(className="text-[#5f3f5d] text-base", children=["Ingresa las variables de la marca y obtén una predicción con nuestro modelo Random Forest de 96% de precisión."]),
            ]),

            # FORMULARIO + RESULTADO
            html.Div(className="grid lg:grid-cols-5 gap-8", children=[

                # Formulario (3/5)
                html.Div(className="lg:col-span-3 bg-white border border-[#f7c0dd] rounded-[28px] p-8 space-y-6", children=[
                    html.H2(className="font-bold text-[#331b35] text-xl", children=["Variables de la marca"]),

                    # Dropdown sector
                    html.Div(className="flex flex-col gap-1", children=[
                        html.Label("Sector", className="text-xs font-semibold text-[#5f3f5d] uppercase tracking-wider"),
                        dcc.Dropdown(
                            id="input-sector",
                            options=[
                                {"label": "Publicidad / Gestión / Administración / Trabajos de oficina", "value": "PUBLICIDAD"},
                                {"label": "Prendas de vestir / Vestuario / Calzado / Sombrerería", "value": "PRENDAS DE VESTIR"},
                                {"label": "Joyería / Relojería / Metales preciosos", "value": "JOYERIA"},
                                {"label": "Alimentos / Limpieza / Ferretería / Velas", "value": "ALIMENTOS"},
                                {"label": "Otro", "value": "OTRO"},
                            ],
                            value="OTRO",
                            clearable=False,
                            style={"borderRadius": "12px", "fontSize": "15px", "color": "#331b35"},
                        )
                    ]),

                    html.Div(className="grid grid-cols-2 gap-4", children=[
                        input_field("Ventas Totales", "input-ventas-totales", 62, "Ej: 12000", min=0),
                        input_field("Ingresos", "input-ingresos", 9281.9, "Ej: 500000", min=0),
                        input_field("Antigüedad (años)", "input-antiguedad", 22, "Ej: 10", min=0),
                        input_field("Leads en web", "input-leads-web", 31, "Ej: 500", min=0),
                        input_field("Calif. Prom. Producto", "input-calif-prom", 4.455021552, "Ej: 4.2", min=0.0, max=5.0, step=0.1),
                        input_field("Devoluciones", "input-devoluciones", 2, "Ej: 5", min=0),
                        input_field("Part. de mercado (%)", "input-part-mercado", 0.006166118, "Ej: 0.20", min=0.0, max=1.0, step=0.01),
                        input_field("Part. Mer. Promedio", "input-part-mercado-prom", 0.005502441, "Ej: 0.15", min=0.0, max=1.0, step=0.01),
                    ]),

                    # Ratios calculados
                    html.Div(
                        className="bg-[#fff0f6] border border-[#f7c0dd] rounded-2xl p-4 space-y-3",
                        children=[
                            html.P(className="text-xs font-bold text-[#993556] uppercase tracking-wider", children=["⚙️ Ratios calculados automáticamente"]),
                            html.Div(className="grid grid-cols-3 gap-3", children=[
                                html.Div(className="bg-white rounded-xl p-3 text-center border border-[#f7c0dd]", children=[
                                    html.P(className="text-xs text-[#a14478] font-semibold uppercase", children=["Costo Ops"]),
                                    html.P(id="ratio-costo-ops", className="text-[#331b35] font-bold text-lg", children=["—"])
                                ]),
                                html.Div(className="bg-white rounded-xl p-3 text-center border border-[#f7c0dd]", children=[
                                    html.P(className="text-xs text-[#a14478] font-semibold uppercase", children=["Margen Neto"]),
                                    html.P(id="ratio-margen", className="text-[#331b35] font-bold text-lg", children=["—"])
                                ]),
                                html.Div(className="bg-white rounded-xl p-3 text-center border border-[#f7c0dd]", children=[
                                    html.P(className="text-xs text-[#a14478] font-semibold uppercase", children=["ROI"]),
                                    html.P(id="ratio-roi", className="text-[#331b35] font-bold text-lg", children=["—"])
                                ]),
                            ])
                        ]
                    ),

                    html.Button(
                        id="btn-predecir-individual",
                        n_clicks=0,
                        style={"width": "100%", "background": "#ff4f99", "color": "white", "fontWeight": "600", "padding": "14px", "borderRadius": "16px", "border": "none", "cursor": "pointer", "fontSize": "15px"},
                        children=["Generar predicción"],
                    ),
                ]),

                # Resultado (2/5)
                html.Div(className="lg:col-span-2 flex flex-col gap-6", children=[
                    html.Div(
                        className="flex-1 bg-white border border-[#f7c0dd] rounded-[28px] p-8 flex flex-col items-center justify-center text-center min-h-[300px]",
                        children=[dcc.Loading(children=[html.Div(id="resultado-individual", children=[
                            html.Div(className="w-20 h-20 bg-[#fff0f6] rounded-full flex items-center justify-center mx-auto mb-4", children=[html.Span(className="text-4xl", children=["🔮"])]),
                            html.H3(className="font-bold text-[#331b35] text-xl mb-2", children=["Esperando datos..."]),
                            html.P(className="text-[#5f3f5d] text-sm", children=["Completa el formulario y presiona Generar predicción"]),
                        ])], type="default")]
                    ),
                    html.Div(className="bg-[#fff0f6] border border-[#f7c0dd] rounded-[24px] p-6 space-y-3", children=[
                        html.H3(className="font-bold text-[#331b35] text-sm uppercase tracking-wider", children=["Sobre el modelo"]),
                        html.Div(className="flex items-center gap-3", children=[html.Span(className="text-lg", children=["🌲"]), html.P(className="text-[#5f3f5d] text-sm", children=["Random Forest Classifier"])]),
                        html.Div(className="flex items-center gap-3", children=[html.Span(className="text-lg", children=["🎯"]), html.P(className="text-[#5f3f5d] text-sm", children=["96% de precisión"])]),
                        html.Div(className="flex items-center gap-3", children=[html.Span(className="text-lg", children=["⚙️"]), html.P(className="text-[#5f3f5d] text-sm", children=["Ratios calculados automáticamente"])]),
                    ]),
                ]),
            ]),

            # PREDICCIÓN MASIVA
            html.Div(className="bg-white border border-[#f7c0dd] rounded-[28px] p-8", children=[
                html.Div(className="flex items-start gap-4 mb-6", children=[
                    html.Div(className="w-12 h-12 bg-[#ffd2e8] rounded-2xl flex items-center justify-center flex-shrink-0", children=[html.Span(className="text-2xl", children=["📂"])]),
                    html.Div(children=[
                        html.H2(className="font-bold text-[#331b35] text-xl", children=["Predicción masiva"]),
                        html.P(className="text-[#5f3f5d] text-sm mt-1", children=["Sube un CSV o Excel con los ratios ya calculados."]),
                    ])
                ]),
                html.Div(className="grid md:grid-cols-3 gap-4 mb-4", children=[
                    html.Div(className="md:col-span-2", children=[
                        dcc.Upload(
                            id='upload-data',
                            children=html.Div([
                                html.Span(className="text-2xl block mb-2", children=["⬆️"]),
                                html.Span(className="font-semibold text-[#993556] text-sm", children=["Arrastra tu archivo aquí"]),
                                html.Span(className="text-[#5f3f5d] text-xs block mt-1", children=["o haz clic para seleccionar"])
                            ], className="text-center"),
                            className="w-full h-32 border-2 border-dashed border-[#f7c0dd] rounded-2xl flex items-center justify-center bg-[#fff8fb] hover:bg-[#fff0f6] cursor-pointer transition"
                        ),
                    ]),
                    html.Div(className="flex flex-col justify-center gap-2", children=[
                        html.P(className="text-xs text-[#5f3f5d] font-semibold uppercase tracking-wider", children=["Columnas requeridas:"]),
                        html.Div(className="flex flex-wrap gap-1", children=[
                            html.Span(className="bg-[#ffd2e8] text-[#993556] text-xs px-2 py-1 rounded-lg", children=[col])
                            for col in ["total_sales", "revenue", "antiguedad_de_la_marca", "numero_de_leads_en_web", "calificacion_promedio_de_productos", "numero_de_devoluciones", "participacion_de_mercado_(%)", "avg_market_share", "crecimiento_total_sales", "pct_costo", "costo_ops_total", "margen_neto_marca", "revenue_por_lead", "ratio_devolucion_revenue", "roi_marca", "ratio_dev_revenue"]
                        ])
                    ])
                ]),
                html.Button(
                    id="btn-predecir-masivo", n_clicks=0,
                    style={"background": "#ff4f99", "color": "white", "fontWeight": "600", "padding": "12px 28px", "borderRadius": "16px", "border": "none", "cursor": "pointer", "fontSize": "14px"},
                    children=["Ejecutar predicción masiva"],
                ),
                html.Div(id="tablaResultados", className="mt-6 border border-[#f7c0dd] rounded-[20px] overflow-hidden"),
            ]),

            # CLUSTERING
            html.Div(className="bg-white border border-[#f7c0dd] rounded-[28px] p-8", children=[
                html.Div(className="flex items-start gap-4 mb-6", children=[
                    html.Div(className="w-12 h-12 bg-[#ffd2e8] rounded-2xl flex items-center justify-center flex-shrink-0", children=[html.Span(className="text-2xl", children=["🔵"])]),
                    html.Div(children=[
                        html.H2(className="font-bold text-[#331b35] text-xl", children=["Agrupación de marcas"]),
                        html.P(className="text-[#5f3f5d] text-sm mt-1", children=["Visualización de clustering — segmentación de marcas por similitud de variables."]),
                    ])
                ]),
                html.Div(className="bg-[#fff8fb] border border-[#f7c0dd] rounded-[20px] overflow-hidden", children=[
                    html.Img(alt="Agrupación de marcas", className="w-full object-cover", src=dash.get_asset_url("images/cluster.png"))
                ]),
            ]),
        ]
    )


@callback(
    Output("ratio-costo-ops", "children"),
    Output("ratio-margen", "children"),
    Output("ratio-roi", "children"),
    Input("input-ingresos", "value"),
    Input("input-ventas-totales", "value"),
    Input("input-calif-prom", "value"),
    Input("input-sector", "value"),
)
def actualizar_ratios(ingresos, ventas, calif, sector):
    try:
        ingresos = float(ingresos) if ingresos is not None else 0.0
        ventas = float(ventas) if ventas is not None else 0.0
        calif = float(calif) if calif is not None else 0.0
        pct_costo = asignar_porcentaje_cogs(sector)
        costo_por_pieza = 65 if calif < 3.0 else 30
        costo_ops = (ingresos * pct_costo) + (ventas * costo_por_pieza)
        margen = (ingresos - costo_ops) / ingresos if ingresos > 0 else 0.0
        roi = (ingresos - costo_ops) / (costo_ops + 1)
        return f"{costo_ops:,.2f}", f"{margen:.2%}", f"{roi:.2f}"
    except Exception:
        return "—", "—", "—"


@callback(
    Output("resultado-individual", "children"),
    Input("btn-predecir-individual", "n_clicks"),
    State("input-ventas-totales", "value"),
    State("input-ingresos", "value"),
    State("input-antiguedad", "value"),
    State("input-leads-web", "value"),
    State("input-calif-prom", "value"),
    State("input-devoluciones", "value"),
    State("input-part-mercado", "value"),
    State("input-part-mercado-prom", "value"),
    State("input-sector", "value"),
    prevent_initial_call=True
)
async def hacer_prediccion(n_clicks, ventas, ingresos, antiguedad, leads, calif, devoluciones, part_mercado, part_prom, sector):
    if n_clicks > 0:
        try:
            async with httpx.AsyncClient(timeout=None) as client:
                payload = {
                    "ventas_totales": float(ventas) if ventas is not None else 0.0,
                    "ingresos": float(ingresos) if ingresos is not None else 0.0,
                    "antiguedad_marca": int(antiguedad) if antiguedad is not None else 0,
                    "numero_leads_web": int(leads) if leads is not None else 0,
                    "calificacion_promedio_productos": float(calif) if calif is not None else 0.0,
                    "numero_devoluciones": int(devoluciones) if devoluciones is not None else 0,
                    "participacion_mercado": float(part_mercado) if part_mercado is not None else 0.0,
                    "participacion_mercado_promedio": float(part_prom) if part_prom is not None else 0.0,
                    "sector": sector or "OTRO",
                }
                response = await client.post(f"{API_URL}/predict-market-share", json=payload)
                response.raise_for_status()
                prediccion = response.json()
                if prediccion["renovacion"] == 1:
                    return html.Div(className="space-y-4", children=[
                        html.Div(className="w-24 h-24 bg-green-50 rounded-full flex items-center justify-center mx-auto", children=[html.Span(className="text-5xl", children=["✅"])]),
                        html.H3(className="font-extrabold text-green-600 text-2xl", children=["Sí debería renovarse"]),
                        html.P(className="text-[#5f3f5d] text-sm", children=["El modelo recomienda renovar esta marca."])
                    ])
                else:
                    return html.Div(className="space-y-4", children=[
                        html.Div(className="w-24 h-24 bg-red-50 rounded-full flex items-center justify-center mx-auto", children=[html.Span(className="text-5xl", children=["❌"])]),
                        html.H3(className="font-extrabold text-red-600 text-2xl", children=["No debería renovarse"]),
                        html.P(className="text-[#5f3f5d] text-sm", children=["El modelo no recomienda renovar esta marca."])
                    ])
        except Exception as e:
            return html.Div(className="space-y-3", children=[
                html.Span(className="text-5xl block", children=["⚠️"]),
                html.H3(className="font-bold text-amber-500 text-xl", children=["Error de conexión"]),
                html.P(className="text-gray-500 text-sm", children=[str(e)])
            ])


@callback(
    Output("tablaResultados", "children"),
    Input("btn-predecir-masivo", "n_clicks"),
    State("upload-data", "contents"),
    State("upload-data", "filename"),
    prevent_initial_call=True
)
async def predecir_masivo(n_clicks, contents, filename):
    if not contents:
        return html.P(className="p-6 text-center text-[#5f3f5d]", children=["Primero sube un archivo CSV o Excel."])
    content_type, content_string = contents.split(",")
    decoded = base64.b64decode(content_string)
    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(io.StringIO(decoded.decode("utf-8")))
        elif filename.endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(decoded))
        else:
            return html.P(className="p-6 text-red-500 text-center", children=["Formato no soportado."])
    except Exception as e:
        return html.P(className="p-6 text-red-500 text-center", children=[f"Error al leer: {str(e)}"])

    columnas = ["total_sales", "revenue", "antiguedad_de_la_marca", "numero_de_leads_en_web",
                "calificacion_promedio_de_productos", "numero_de_devoluciones",
                "participacion_de_mercado_(%)", "avg_market_share", "crecimiento_total_sales",
                "pct_costo", "costo_ops_total", "margen_neto_marca", "revenue_por_lead",
                "ratio_devolucion_revenue", "roi_marca", "ratio_dev_revenue"]

    faltantes = [c for c in columnas if c not in df.columns]
    if faltantes:
        return html.Div(className="p-6", children=[
            html.P(className="text-red-500 font-semibold", children=[f"Faltan columnas: {', '.join(faltantes)}"]),
            html.P(className="text-sm text-gray-500 mt-2", children=[f"El archivo tiene: {', '.join(df.columns.tolist())}"])
        ])

    resultados = []
    async with httpx.AsyncClient(timeout=None) as client:
        for _, row in df.iterrows():
            try:
                payload = {
                    "total_sales": float(row["total_sales"]),
                    "revenue": float(row["revenue"]),
                    "antiguedad_de_la_marca": float(row["antiguedad_de_la_marca"]),
                    "numero_de_leads_en_web": float(row["numero_de_leads_en_web"]),
                    "calificacion_promedio_de_productos": float(row["calificacion_promedio_de_productos"]),
                    "numero_de_devoluciones": float(row["numero_de_devoluciones"]),
                    "participacion_de_mercado": float(row["participacion_de_mercado_(%)"]),
                    "avg_market_share": float(row["avg_market_share"]),
                    "crecimiento_total_sales": float(row["crecimiento_total_sales"]),
                    "pct_costo": float(row["pct_costo"]),
                    "costo_ops_total": float(row["costo_ops_total"]),
                    "margen_neto_marca": float(row["margen_neto_marca"]),
                    "revenue_por_lead": float(row["revenue_por_lead"]),
                    "ratio_devolucion_revenue": float(row["ratio_devolucion_revenue"]),
                    "roi_marca": float(row["roi_marca"]),
                    "ratio_dev_revenue": float(row["ratio_dev_revenue"]),
                }
                response = await client.post(f"{API_URL}/predict-batch", json=payload)
                response.raise_for_status()
                pred = response.json()
                resultados.append("✅ Debería renovarse" if pred["renovacion"] == 1 else "❌ No debería renovarse")
            except Exception:
                resultados.append("⚠️ Error")

    df["Renovación"] = resultados
    encabezados = [html.Th(className="px-4 py-3 text-left text-xs font-semibold text-[#5f3f5d] uppercase tracking-wider bg-[#ffd2e8]", children=[col]) for col in df.columns]
    filas = []
    for _, row in df.iterrows():
        celdas = []
        for col in df.columns:
            val = row[col]
            if col == "Renovación":
                color = "text-green-600 font-bold" if "Sí" in str(val) else ("text-red-600 font-bold" if "No" in str(val) else "text-amber-500")
                celdas.append(html.Td(className=f"px-4 py-3 text-sm {color}", children=[str(val)]))
            else:
                celdas.append(html.Td(
    className="px-4 py-3 text-sm text-gray-700",
    style={"maxWidth": "200px", "overflow": "hidden", "textOverflow": "ellipsis", "whiteSpace": "nowrap"},
    children=[str(val)]
))
        filas.append(html.Tr(className="border-t border-[#f7c0dd] hover:bg-pink-50 transition", children=celdas))

    return html.Div(className="overflow-x-auto", children=[
        html.P(className="px-6 py-3 text-sm text-[#5f3f5d] font-semibold", children=[f"Procesadas {len(df)} marcas."]),
        html.Table(className="min-w-full", children=[
            html.Thead(children=[html.Tr(children=encabezados)]),
            html.Tbody(children=filas)
        ])
    ])