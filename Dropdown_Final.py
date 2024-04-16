import dash
from dash import dcc
from dash import html
import pandas as pd
import plotly.express as px
from dash.dependencies import Input
from dash.dependencies import Output
import pymysql

# Variables para la conexión a la BD en AWS
host = 'db-nikki.c32w48gkahsu.us-east-1.rds.amazonaws.com'
user = 'nikki'
password = 'm0x1eNikki'

# Conectar a la base de datos y recuperar los datos
conn = pymysql.connect(
    host=host,
    user=user,
    password=password
)

cursor = conn.cursor()
sql_query = "select * from nikki_test.nikki_sales"
cursor.execute(sql_query)

data = cursor.fetchall()
columnas = [i[0] for i in cursor.description]

# Cerrar la conexión
cursor.close()
conn.close()

# Crear DataFrame y convertir la columna 'Date' a datetime
df = pd.DataFrame(data, columns=columnas)
df['Date'] = pd.to_datetime(df['Date'])

# Crear la aplicación Dash
app = dash.Dash(__name__)

# Layout de la aplicación
app.layout = html.Div([
    html.Div([
        dcc.Dropdown(
            id='group-by-dropdown',
            options=[
                {'label': 'Product Category', 'value': 'Product_Category'},
                {'label': 'Sub Category', 'value': 'Sub_Category'},
                {'label': 'Product', 'value': 'Product'}
            ],
            value='Product_Category',  # Valor predeterminado
            placeholder="Agrupaciones",
            clearable=False,
            style={'width': '200px', 'fontSize': '14px'}
        ),
    ], style={'width': '100%', 'display': 'flex', 'justifyContent': 'flex-end'}),
    html.Div([
        html.Div([
            dcc.Graph(id='line-chart')
        ], style={'width': '50%', 'display': 'inline-block'}),
        html.Div([
            dcc.Graph(id='tree-chart')
        ], style={'width': '50%', 'display': 'inline-block'}),
    ]),
    dcc.Interval(
        id='interval-component',
        interval=60000,  # en milisegundos, actualiza cada minuto
        n_intervals=0
    )
])

# Callback para actualizar los gráficos con los datos más recientes
@app.callback(
    [Output('line-chart', 'figure'),
     Output('tree-chart', 'figure')],
    [Input('interval-component', 'n_intervals'),
     Input('group-by-dropdown', 'value')]
)
def update_figures(n, group_by):
    # Tendencia lineal
    line_fig = px.line(df.groupby(['Date', group_by]).sum().reset_index(), x='Date', y='Revenue', color=group_by,
                        title='Tendencia de Ventas por {}'.format(group_by))

    # Calcular la fecha hace 30 días a partir de la última fecha en el conjunto de datos
    fecha_inicio = df['Date'].max() - pd.Timedelta(days=30)

    # Filtrar los datos para obtener los últimos 30 días
    last_30_days_df = df[df['Date'] >= fecha_inicio]

    # Calcular la suma del revenue por categoría
    tree_data = last_30_days_df.groupby([group_by])['Revenue'].sum().reset_index()

    # Crear el treemap
    tree_fig = px.treemap(tree_data, path=[group_by], values='Revenue', custom_data=['Revenue'],
                          title='Ventas de los últimos 30 días por {}'.format(group_by))

    # Configurar el texto del hover para incluir el revenue
    tree_fig.update_traces(hovertemplate='<b>%{label}</b><br><br>Revenue: %{customdata[0]:,.2f}')

    # Configurar el texto de las celdas para incluir el revenue y el signo de la moneda
    tree_fig.update_traces(texttemplate='%{label}: $%{value:,.2f}')


    return [line_fig, tree_fig]

# Ejecutar la aplicación
if __name__ == '__main__':
    app.run_server(debug=True)
