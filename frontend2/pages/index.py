import dash
import httpx
from dash import html, dcc, callback, Input, Output, State

dash.register_page(__name__, path="/", title="Pagina principal", name="index")

API_URL = "http://localhost:8000"

@callback(
    Output("chat-modal", "style"),
    Input("bolo-image", "n_clicks"),
    Input("close-chat-btn", "n_clicks"),
    State("chat-modal", "style"),
    prevent_initial_call=True,
)
def toggle_chat_modal(image_clicks, close_clicks, current_style):
    image_clicks = image_clicks or 0
    close_clicks = close_clicks or 0
    if close_clicks > 0 and close_clicks >= image_clicks:
        return {"display": "none"}
    if image_clicks > close_clicks:
        return {"display": "flex"}
    return current_style or {"display": "none"}


@callback(
    Output("chat-messages", "children"),
    Output("chat-input", "value"),
    Input("send-message-btn", "n_clicks"),
    Input("chat-input", "n_submit"),
    State("chat-input", "value"),
    State("chat-messages", "children"),
    running=[
        (Output("send-message-btn", "disabled"), True, False),
        (Output("chat-spinner", "style"), {"display": "flex"}, {"display": "none"}),
    ],
    prevent_initial_call=True,
)
def add_message(n_clicks, n_submit, user_message, current_messages):
    if not user_message or not user_message.strip():
        return current_messages, ""
    if current_messages is None:
        current_messages = []

    user_msg = html.Div(
        style={"display": "flex", "justifyContent": "flex-end"},
        children=[html.Div(style={"display": "flex", "gap": "8px", "alignItems": "flex-end", "maxWidth": "320px"}, children=[
            html.Div(
                style={
                    "background": "linear-gradient(135deg, #ff4f99, #ff6fad)",
                    "color": "white",
                    "padding": "12px 16px",
                    "borderRadius": "18px 18px 4px 18px",
                    "fontSize": "14px",
                    "lineHeight": "1.5",
                    "wordWrap": "break-word",
                    "boxShadow": "0 2px 8px rgba(255,79,153,0.3)",
                },
                children=[user_message]
            ),
            html.Span("👤", style={"fontSize": "22px", "flexShrink": "0"}),
        ])]
    )
    current_messages.append(user_msg)

    try:
        with httpx.Client(timeout=None) as client:
            response = client.post(f"{API_URL}/bolo/chat", json={"mensaje": user_message})
        data = response.json()
        if "error" in data:
            error_msg = data["error"]
            if "429" in str(error_msg) or "RESOURCE_EXHAUSTED" in str(error_msg):
                bot_text = "⚠️ Estoy temporalmente sin servicio. Mi cuota de API se agotó. Intenta más tarde."
            else:
                bot_text = "⚠️ Ocurrió un error inesperado. Intenta de nuevo."
        else:
            bot_text = data.get("respuesta", "No obtuve respuesta.")
    except Exception as e:
        print("ERROR FRONTEND CHAT:", e)
        bot_text = "⚠️ No pude conectarme con el servidor. Verifica que esté corriendo."

    bot_msg = html.Div(
        style={"display": "flex", "justifyContent": "flex-start"},
        children=[html.Div(style={"display": "flex", "gap": "8px", "alignItems": "flex-end", "maxWidth": "320px"}, children=[
            html.Img(
                src=dash.get_asset_url("images/Bolo chatbot.png"),
                style={"width": "32px", "height": "32px", "borderRadius": "50%", "objectFit": "cover", "flexShrink": "0"},
                alt="Bolo"
            ),
            html.Div(
                style={
                    "background": "#f1f5f9",
                    "color": "#1e293b",
                    "padding": "12px 16px",
                    "borderRadius": "18px 18px 18px 4px",
                    "fontSize": "14px",
                    "lineHeight": "1.5",
                    "wordWrap": "break-word",
                },
                children=[
                    dcc.Markdown(
                        bot_text,
                        style={"fontSize": "14px", "lineHeight": "1.6", "margin": "0"},
                    )
                ]
            )
        ])]
    )
    current_messages.append(bot_msg)
    return current_messages, ""


@callback(
    Output("metrica-vigentes", "children"),
    Output("metrica-clases", "children"),
    Output("metrica-vencer", "children"),
    Output("metrica-precision", "children"),
    Input("intervalo-metricas", "n_intervals"),
)
def cargar_metricas(n):
    try:
        response = httpx.get(f"{API_URL}/metricas/resumen", timeout=10)
        data = response.json()
        if "error" in data:
            return "—", "—", "—", "96%"
        return (
            f"{data.get('marcas_vigentes', '—'):,}",
            str(data.get('clases', '—')),
            str(data.get('por_vencer_90_dias', '—')),
            f"{data.get('precision_modelo', 96)}%"
        )
    except Exception as e:
        print("ERROR FRONTEND METRICAS:", e)
        return "—", "—", "—", "96%"


def layout():
    return html.Main(
        children=[
            dcc.Interval(id="intervalo-metricas", interval=1, max_intervals=1),
            dcc.Store(id="chat-store", data={"messages": []}),

            # ── CHAT MODAL ──────────────────────────────────────────────────
            html.Div(
                id="chat-modal",
                className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50 p-4",
                style={"display": "none"},
                children=[
                    html.Div(
                        style={
                            "height": "680px",
                            "width": "100%",
                            "maxWidth": "512px",
                            "display": "flex",
                            "flexDirection": "column",
                            "background": "white",
                            "borderRadius": "16px",
                            "boxShadow": "0 25px 50px rgba(0,0,0,0.25)",
                            "overflow": "hidden",
                            "position": "relative",
                        },
                        children=[
                            # Header
                            html.Div(
                                style={
                                    "flexShrink": "0",
                                    "background": "linear-gradient(135deg, #ff4f99, #ff6fad, #d3196b)",
                                    "padding": "20px 24px",
                                    "display": "flex",
                                    "justifyContent": "space-between",
                                    "alignItems": "center",
                                },
                                children=[
                                    html.Div(style={"display": "flex", "alignItems": "center", "gap": "12px"}, children=[
                                        html.Img(
                                            src=dash.get_asset_url("images/Bolo chatbot.png"),
                                            style={"width": "48px", "height": "48px", "borderRadius": "50%", "objectFit": "cover", "border": "2px solid rgba(255,255,255,0.3)"},
                                            alt="Bolo"
                                        ),
                                        html.Div(children=[
                                            html.H3(style={"fontWeight": "700", "color": "white", "fontSize": "16px", "margin": "0"}, children=["Bolo - Asistente IA"]),
                                            html.Div(style={"display": "flex", "alignItems": "center", "gap": "4px"}, children=[
                                                html.Span(style={"width": "8px", "height": "8px", "background": "#86efac", "borderRadius": "50%"}),
                                                html.P(style={"color": "rgba(255,255,255,0.8)", "fontSize": "12px", "margin": "0"}, children=["En línea"])
                                            ])
                                        ])
                                    ]),
                                    html.Button(
                                        id="close-chat-btn",
                                        children=["✕"],
                                        n_clicks=0,
                                        style={"fontSize": "20px", "background": "none", "border": "none", "cursor": "pointer", "color": "white", "padding": "8px"}
                                    )
                                ]
                            ),

                            # Mensajes
                            html.Div(
                                id="chat-messages",
                                style={
                                    "flex": "1",
                                    "minHeight": "0",
                                    "overflowY": "auto",
                                    "padding": "20px",
                                    "display": "flex",
                                    "flexDirection": "column",
                                    "gap": "12px",
                                    "background": "linear-gradient(to bottom, #f8fafc, white)",
                                    "scrollBehavior": "smooth",
                                    "boxSizing": "border-box",
                                },
                                children=[
                                    html.Div(style={"display": "flex", "justifyContent": "flex-start"}, children=[
                                        html.Div(style={"display": "flex", "gap": "8px", "alignItems": "flex-end", "maxWidth": "320px"}, children=[
                                            html.Img(
                                                src=dash.get_asset_url("images/Bolo chatbot.png"),
                                                style={"width": "32px", "height": "32px", "borderRadius": "50%", "objectFit": "cover", "flexShrink": "0"},
                                                alt="Bolo"
                                            ),
                                            html.Div(
                                                style={"background": "#f1f5f9", "color": "#1e293b", "padding": "12px 16px", "borderRadius": "18px 18px 18px 4px", "fontSize": "14px", "lineHeight": "1.5"},
                                                children=["👋 ¡Hola! Soy Bolo, tu asistente de datos de Liverpool. Pregúntame sobre marcas, ventas y costos. ¿En qué te ayudo?"]
                                            )
                                        ])
                                    ])
                                ]
                            ),

                            # Spinner animado — se muestra via "running" en el callback
                            html.Div(
                                id="chat-spinner",
                                style={"display": "none"},
                                children=[
                                    html.Div(
                                        style={
                                            "position": "absolute",
                                            "bottom": "90px",
                                            "left": "20px",
                                            "display": "flex",
                                            "gap": "8px",
                                            "alignItems": "flex-end",
                                            "zIndex": "10",
                                        },
                                        children=[
                                            html.Img(
                                                src=dash.get_asset_url("images/Bolo chatbot.png"),
                                                style={"width": "32px", "height": "32px", "borderRadius": "50%", "objectFit": "cover"},
                                                alt="Bolo"
                                            ),
                                            html.Div(
                                                style={
                                                    "background": "#f1f5f9",
                                                    "padding": "12px 16px",
                                                    "borderRadius": "18px 18px 18px 4px",
                                                    "display": "flex",
                                                    "gap": "5px",
                                                    "alignItems": "center",
                                                },
                                                children=[
                                                    html.Span(style={"width": "8px", "height": "8px", "background": "#ff4f99", "borderRadius": "50%", "animation": "bounce 1s infinite 0s"}),
                                                    html.Span(style={"width": "8px", "height": "8px", "background": "#ff4f99", "borderRadius": "50%", "animation": "bounce 1s infinite 0.2s"}),
                                                    html.Span(style={"width": "8px", "height": "8px", "background": "#ff4f99", "borderRadius": "50%", "animation": "bounce 1s infinite 0.4s"}),
                                                ]
                                            )
                                        ]
                                    )
                                ]
                            ),

                            # Input
                            html.Div(
                                style={
                                    "flexShrink": "0",
                                    "borderTop": "1px solid #e2e8f0",
                                    "background": "white",
                                    "padding": "16px",
                                },
                                children=[
                                    html.Div(
                                        style={"display": "flex", "alignItems": "center", "gap": "12px", "background": "#f1f5f9", "borderRadius": "16px", "padding": "12px 16px"},
                                        children=[
                                            dcc.Input(
                                                id="chat-input",
                                                type="text",
                                                placeholder="Escribe tu pregunta aquí...",
                                                n_submit=0,
                                                style={
                                                    "fontFamily": "inherit",
                                                    "background": "transparent",
                                                    "border": "none",
                                                    "outline": "none",
                                                    "width": "100%",
                                                    "minWidth": "0",
                                                    "fontSize": "14px",
                                                    "color": "#1e293b",
                                                }
                                            ),
                                            html.Button(
                                                id="send-message-btn",
                                                n_clicks=0,
                                                children=["Enviar"],
                                                style={
                                                    "background": "#ff4f99",
                                                    "color": "white",
                                                    "border": "none",
                                                    "borderRadius": "12px",
                                                    "padding": "8px 16px",
                                                    "fontSize": "14px",
                                                    "fontWeight": "600",
                                                    "cursor": "pointer",
                                                    "whiteSpace": "nowrap",
                                                    "flexShrink": "0",
                                                }
                                            )
                                        ]
                                    )
                                ]
                            )
                        ]
                    )
                ]
            ),

            # ── HERO ─────────────────────────────────────────────────────────
            html.Section(
                className="lg:grid lg:grid-cols-2 lg:gap-12 lg:items-center mx-auto px-6 py-16 max-w-7xl",
                children=[
                    html.Div(className="space-y-6 max-w-2xl", children=[
                        html.P(
                            className="inline-flex bg-[#ffd2e8] px-4 py-1 rounded-full font-semibold text-[#993556] text-xs uppercase tracking-[0.25em]",
                            children=["Análisis de marcas"]
                        ),
                        html.H1(
                            className="font-extrabold text-[#331b35] text-4xl sm:text-5xl tracking-tight leading-tight",
                            children=["Inteligencia de datos para la gestión estratégica de marcas"]
                        ),
                        html.P(
                            className="text-[#5f3f5d] text-lg leading-8",
                            children=["Explora predicciones, dashboards y análisis profundo del portafolio marcario de Liverpool — todo en un solo lugar."]
                        ),
                        html.Div(className="flex sm:flex-row flex-col sm:items-center gap-4", children=[
                            html.A(className="inline-flex justify-center items-center bg-[#ff4f99] hover:bg-[#e03d82] shadow-lg px-6 py-3 rounded-full font-semibold text-white text-sm transition", href="/predictivo", children=["Ir a Predictivo"]),
                            html.A(className="inline-flex justify-center items-center bg-white hover:bg-[#ffe3f1] px-6 py-3 border border-[#d3196b] rounded-full font-semibold text-[#d3196b] text-sm transition", href="/dashboards", children=["Ver Dashboards"])
                        ]),

                        # Métricas
                        html.Div(
                            className="grid grid-cols-4 gap-3 pt-2",
                            children=[
                                html.Div(className="bg-[#fff0f6] border border-[#f7c0dd] rounded-2xl p-4", children=[
                                    html.P(className="text-[#a14478] text-xs uppercase tracking-wider font-semibold mb-1", children=["Vigentes"]),
                                    html.P(id="metrica-vigentes", className="text-[#331b35] text-2xl font-extrabold", children=["—"])
                                ]),
                                html.Div(className="bg-[#fff0f6] border border-[#f7c0dd] rounded-2xl p-4", children=[
                                    html.P(className="text-[#a14478] text-xs uppercase tracking-wider font-semibold mb-1", children=["Clases"]),
                                    html.P(id="metrica-clases", className="text-[#331b35] text-2xl font-extrabold", children=["—"])
                                ]),
                                html.Div(className="bg-[#fff0f6] border border-[#f7c0dd] rounded-2xl p-4", children=[
                                    html.P(className="text-[#a14478] text-xs uppercase tracking-wider font-semibold mb-1", children=["Por vencer"]),
                                    html.P(id="metrica-vencer", className="text-[#331b35] text-2xl font-extrabold", children=["—"])
                                ]),
                                html.Div(className="bg-[#fff0f6] border border-[#f7c0dd] rounded-2xl p-4", children=[
                                    html.P(className="text-[#a14478] text-xs uppercase tracking-wider font-semibold mb-1", children=["Precisión ML"]),
                                    html.P(id="metrica-precision", className="text-[#331b35] text-2xl font-extrabold", children=["—"])
                                ]),
                            ]
                        ),
                    ]),

                    # Bolo
                    html.Div(className="mt-12 lg:mt-0", children=[
                        html.Div(
                            className="bg-gradient-to-br from-[#ffd6e8] via-[#ffecf4] to-[#ffe8f2] border border-[#f7c0dd] rounded-[32px] p-8 flex flex-col items-center gap-4 text-center cursor-pointer hover:opacity-95 transition",
                            id="bolo-image",
                            n_clicks=0,
                            children=[
                                html.Img(alt="Bolo chatbot", className="w-64 h-64 object-contain", src=dash.get_asset_url("images/Bolo chatbot.png")),
                                html.Div(children=[
                                    html.P(className="text-[#a14478] text-xs uppercase tracking-[0.25em] font-semibold", children=["Haz clic para chatear con"]),
                                    html.H2(className="font-bold text-[#3e1e3b] text-3xl mt-1", children=["Bolo"]),
                                    html.P(className="text-[#5f3f5d] text-sm mt-1", children=["Liverpool es parte de mi vida."])
                                ]),
                                html.Div(
                                    className="flex items-center gap-2 bg-white border border-[#f7c0dd] rounded-full px-4 py-2 w-full",
                                    children=[
                                        html.Span(className="text-[#a14478] text-sm flex-1 text-left", children=["Pregúntame algo..."]),
                                        html.Span(className="bg-[#ff4f99] text-white rounded-full w-7 h-7 flex items-center justify-center text-sm font-bold", children=["→"])
                                    ]
                                )
                            ]
                        )
                    ]),
                ]
            ),

            # Cards
            html.Section(
                className="mx-auto px-6 pb-16 max-w-7xl",
                children=[
                    html.Div(className="gap-6 grid md:grid-cols-3", children=[
                        html.Article(className="bg-white/90 shadow-sm p-6 border border-[#f7c0dd] rounded-[24px]", children=[
                            html.Div(className="w-10 h-10 bg-[#ffd2e8] rounded-xl flex items-center justify-center mb-4", children=[html.Span(className="text-xl", children=["📊"])]),
                            html.H3(className="font-semibold text-[#331b35] text-lg mb-2", children=["Predicción de renovación"]),
                            html.P(className="text-[#5f3f5d] text-sm leading-6", children=["Modelo Random Forest que anticipa si una marca debe renovarse con 96% de precisión."])
                        ]),
                        html.Article(className="bg-white/90 shadow-sm p-6 border border-[#f7c0dd] rounded-[24px]", children=[
                            html.Div(className="w-10 h-10 bg-[#ffd2e8] rounded-xl flex items-center justify-center mb-4", children=[html.Span(className="text-xl", children=["📈"])]),
                            html.H3(className="font-semibold text-[#331b35] text-lg mb-2", children=["Dashboards interactivos"]),
                            html.P(className="text-[#5f3f5d] text-sm leading-6", children=["Visualiza KPIs clave, tendencias de consumo y desempeño por marca en tiempo real."])
                        ]),
                        html.Article(className="bg-white/90 shadow-sm p-6 border border-[#f7c0dd] rounded-[24px]", children=[
                            html.Div(className="w-10 h-10 bg-[#ffd2e8] rounded-xl flex items-center justify-center mb-4", children=[html.Span(className="text-xl", children=["🔍"])]),
                            html.H3(className="font-semibold text-[#331b35] text-lg mb-2", children=["Explorador de marcas"]),
                            html.P(className="text-[#5f3f5d] text-sm leading-6", children=["Consulta estatus, clase y vencimiento de cualquier marca del portafolio de Liverpool."])
                        ])
                    ])
                ]
            )
        ]
    )