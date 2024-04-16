import dash
import dash_html_components as html

# Crear la aplicación Dash
app = dash.Dash(__name__)

# Layout de la aplicación
app.layout = html.Div(
    children=[
        html.H1("¡Hola, Dash!"),
        html.P("Esta es una aplicación Dash simple para probar la conexión.")
    ]
)

# Ejecutar la aplicación
if __name__ == "__main__":
    app.run_server(debug=True)
