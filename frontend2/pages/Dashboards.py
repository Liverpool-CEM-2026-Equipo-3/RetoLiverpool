import dash
from dash import html

dash.register_page(
    __name__,
    path="/dashboards",
    title="Dashboards",
    name="Dashboards"
)

def layout():
    return html.Main(
        className="px-4 py-8",
        children=[
            html.Section(
                className="mb-8 max-w-7xl mx-auto",
                children=[
                    html.H1(
                        className="font-extrabold text-[#331b35] text-3xl sm:text-4xl",
                        children=["Dashboards Interactivos"],
                    ),
                    html.P(
                        className="mt-2 text-[#5f3f5d]",
                        children=["Explora los datos, interactúa con las gráficas y analiza el desempeño de las marcas en tiempo real."],
                    ),
                ],
            ),
            html.Section(
                className="space-y-10",
                children=[
                    html.Div(
                        children=[
                            html.Div(
                                className="flex justify-between items-center mb-3",
                                children=[
                                    html.H2(
                                        className="font-bold text-[#331b35] text-2xl",
                                        children=["Dashboard situacional"],
                                    ),
                                    html.Div(
                                        className="flex justify-end mb-2 gap-3",
                                        children=[
                                            html.A(
                                                "↗ Ver en Tableau",
                                                href="https://public.tableau.com/views/Dashboard1FinalE3FINALCORREGIDOTIPIIII/DasbpardFinal1",
                                                target="_blank",
                                                className="text-sm font-semibold text-[#d3196b] hover:underline"
                                            )
                                        ]
                                    ),
                                ]
                            ),
                            html.Section(
                                className="bg-white shadow-[0_30px_80px_rgba(255,79,153,0.12)] border border-[#f7c0dd] rounded-[24px] overflow-hidden",
                                style={"width": "100%"},
                                children=[
                                    html.Iframe(
                                        style={"width": "100%", "height": "900px", "border": "none"},
                                        src="https://public.tableau.com/views/Dashboard1FinalE3FINALCORREGIDOTIPIIII/DasbpardFinal1?:language=en-US&:embed=y&:display_count=n&:origin=viz_share_link&:showVizHome=no&:toolbar=yes",
                                    )
                                ],
                            ),
                        ]
                    ),
                    html.Div(
                        children=[
                            html.Div(
                                className="flex justify-between items-center mb-3",
                                children=[
                                    html.H2(
                                        className="font-bold text-[#331b35] text-2xl",
                                        children=["Dashboard ratios"],
                                    ),
                                    html.Div(
                                        className="flex justify-end mb-2 gap-3",
                                        children=[
                                            html.A(
                                                "↗ Ver en Tableau",
                                                href="https://public.tableau.com/views/DashboardMarcas4/Dashboard1",
                                                target="_blank",
                                                className="text-sm font-semibold text-[#d3196b] hover:underline"
                                            )
                                        ]
                                    ),
                                ]
                            ),
                            html.Section(
                                className="bg-white shadow-[0_30px_80px_rgba(255,79,153,0.12)] border border-[#f7c0dd] rounded-[24px] overflow-hidden",
                                style={"width": "100%"},
                                children=[
                                    html.Iframe(
                                        style={"width": "100%", "height": "900px", "border": "none"},
                                        src="https://public.tableau.com/views/DashboardMarcas4/Dashboard1?:language=es-ES&:embed=y&:display_count=n&:origin=viz_share_link&:showVizHome=no&:toolbar=yes",
                                    )
                                ],
                            ),
                        ]
                    ),
                ],
            ),
        ],
    )