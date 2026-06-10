html.Header(
    className="top-0 z-20 sticky bg-white/90 shadow-sm backdrop-blur",
    children=[
        html.Div(
            className="flex justify-between items-center mx-auto px-6 py-4 max-w-7xl",
            children=[
                html.A(
                    className="font-extrabold text-[#d3196b] text-xl tracking-tight",
                    href="index.html",
                    children=["Liverpool Insights"],
                ),
                html.Nav(
                    className="hidden md:flex gap-6 font-medium text-[#4a2a4f] text-sm",
                    children=[
                        html.A(
                            className="hover:text-[#d3196b]",
                            href="index.html",
                            children=["Inicio"],
                        ),
                        html.A(
                            className="hover:text-[#d3196b]",
                            href="predictivo.html",
                            children=["Predictivo"],
                        ),
                        html.A(
                            className="hover:text-[#d3196b]",
                            href="Dashboards.html",
                            children=["Dashboards"],
                        ),
                        html.A(
                            className="hover:text-[#d3196b]",
                            href="marca.html",
                            children=["Marcas"],
                        ),
                    ],
                ),
            ],
        )
    ],
)
