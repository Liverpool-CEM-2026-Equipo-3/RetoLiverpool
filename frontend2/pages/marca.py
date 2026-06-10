import dash
import httpx
from dash import html, dcc, Input, Output, callback

dash.register_page(
    __name__,
    path="/marca",
    title="Buscador de Marcas",
    name="marca"
)

API_URL = "http://localhost:8000"


def render_card(marca: dict):
    clases_raw = marca.get("clases") or []
    clases = ", ".join(sorted(set(str(c) for c in clases_raw))) or "—"
    estatus = marca.get("estatus_marca") or "—"
    vencimiento = marca.get("fecha_vencimiento") or "—"

    if estatus == "Vigente":
        badge_class = "bg-green-100 text-green-700"
        dot_class = "bg-green-500"
    elif estatus == "Vencido":
        badge_class = "bg-red-100 text-red-700"
        dot_class = "bg-red-500"
    else:
        badge_class = "bg-gray-100 text-gray-600"
        dot_class = "bg-gray-400"

    def fila(etiqueta, valor):
        return html.Div(
            className="grid gap-2",
            style={"gridTemplateColumns": "100px 1fr"},
            children=[
                html.Span(className="text-xs font-bold text-[#a14478] uppercase tracking-wider self-start pt-0.5", children=[etiqueta]),
                html.Span(className="text-sm text-[#331b35]", children=[str(valor)])
            ]
        )

    return html.Div(
        className="bg-white border border-[#f7c0dd] rounded-[24px] p-6 flex flex-col gap-3 hover:shadow-md transition",
        children=[
            html.Div(
                className="flex items-start justify-between gap-3",
                children=[
                    html.H3(
                        className="font-bold text-[#331b35] text-base leading-snug flex-1",
                        children=[marca.get("denominacion") or "Sin nombre"]
                    ),
                    html.Span(
                        className=f"inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-semibold flex-shrink-0 {badge_class}",
                        children=[
                            html.Span(className=f"w-1.5 h-1.5 rounded-full inline-block {dot_class}"),
                            estatus
                        ]
                    )
                ]
            ),
            html.Div(
                className="border-t border-[#f7c0dd] pt-3 flex flex-col gap-2",
                children=[
                    fila("Tipo", marca.get("tipo") or "—"),
                    fila("Clases", clases),
                    fila("Vencimiento", vencimiento),
                ]
            )
        ]
    )


def layout():
    return html.Div(
        children=[
            html.Main(
                className="mx-auto px-6 py-16 max-w-7xl",
                children=[
                    # Header
                    html.Section(
                        className="mb-12 text-center",
                        children=[
                            html.P(
                                className="inline-flex bg-[#ffd2e8] px-4 py-1 rounded-full font-semibold text-[#993556] text-xs uppercase tracking-[0.25em] mb-4",
                                children=["Gestión de marcas Liverpool"]
                            ),
                            html.H1(
                                className="mb-4 font-extrabold text-[#331b35] text-4xl sm:text-5xl",
                                children=["Explora Marcas"]
                            ),
                            html.P(
                                className="mb-8 text-[#5f3f5d] text-base max-w-lg mx-auto",
                                children=["Busca cualquier marca del portafolio de Liverpool y consulta su tipo, clases y estatus de renovación."]
                            ),
                            html.Div(
                                className="flex justify-center px-4",
                                children=[
                                    html.Div(
                                        style={"width": "100%", "maxWidth": "560px"},
                                        children=[
                                            dcc.Input(
                                                id="input-busqueda",
                                                type="text",
                                                placeholder="🔍  Escribe el nombre de la marca...",
                                                debounce=False,
                                                value="",
                                                style={
                                                    "width": "100%",
                                                    "padding": "14px 24px",
                                                    "borderRadius": "100px",
                                                    "border": "2px solid #f7c0dd",
                                                    "fontSize": "14px",
                                                    "color": "#331b35",
                                                    "outline": "none",
                                                    "boxSizing": "border-box",
                                                    "boxShadow": "0 4px 20px rgba(255, 79, 153, 0.08)",
                                                    "fontFamily": "inherit",
                                                }
                                            )
                                        ]
                                    )
                                ]
                            ),
                        ],
                    ),

                    # Resultados
                    html.Section(
                        children=[
                            html.Div(
                                id="resultados-marcas",
                                className="gap-5 grid md:grid-cols-3"
                            )
                        ]
                    ),
                ],
            ),
        ]
    )


@callback(
    Output("resultados-marcas", "children"),
    Input("input-busqueda", "value"),
)
def actualizar_resultados(nombre):
    if not nombre or len(nombre.strip()) < 2:
        return html.Div(
            className="col-span-3 mt-12 text-center",
            children=[
                html.Span(className="text-4xl block mb-3", children=["🔎"]),
                html.P(className="text-[#a14478] font-semibold", children=["Escribe al menos 2 letras para buscar marcas."]),
                html.P(className="text-[#5f3f5d] text-sm mt-1", children=["Puedes buscar por nombre completo o parcial."])
            ]
        )
    try:
        response = httpx.get(f"{API_URL}/marcas/buscar", params={"nombre": nombre.strip()}, timeout=10)
        marcas = response.json()
        if isinstance(marcas, dict) and "error" in marcas:
            return html.P(className="text-center text-red-500 col-span-3 mt-8", children=[f"Error: {marcas['error']}"])
        if not marcas:
            return html.Div(
                className="col-span-3 mt-12 text-center",
                children=[
                    html.Span(className="text-4xl block mb-3", children=["😕"]),
                    html.P(className="text-[#a14478] font-semibold", children=[f'No se encontraron marcas con "{nombre}".']),
                    html.P(className="text-[#5f3f5d] text-sm mt-1", children=["Intenta con otro término de búsqueda."])
                ]
            )
        return [render_card(m) for m in marcas]
    except Exception as e:
        return html.P(className="text-center text-red-500 col-span-3 mt-8", children=[f"Error de conexión: {str(e)}"])