import dash
from dash import dcc, html
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash.dependencies import Input, Output
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
sql_query = "SELECT * FROM nikki_test.nikki_sales"
cursor.execute(sql_query)

data = cursor.fetchall()
columnas = [i[0] for i in cursor.description]

# Crear DataFrame y convertir la columna 'Date' a datetime
df = pd.DataFrame(data, columns=columnas)
df['Date'] = pd.to_datetime(df['Date'])

# Calcular el costo ponderado mensual
df['Costo_Ponderado'] = df.groupby(pd.Grouper(key='Date', freq='ME'))['Cost'].transform('sum') / \
                        df.groupby(pd.Grouper(key='Date', freq='ME'))['Order_Quantity'].transform('sum')

# Calcular el margen ponderado mensual
df['Margen_Ponderado'] = df.groupby(pd.Grouper(key='Date', freq='ME'))['Profit'].transform('sum') / \
                          df.groupby(pd.Grouper(key='Date', freq='ME'))['Revenue'].transform('sum')

# Calcular el precio ponderado mensual
df['Precio_Ponderado'] = df.groupby(pd.Grouper(key='Date', freq='ME'))['Revenue'].transform('sum') / \
                          df.groupby(pd.Grouper(key='Date', freq='ME'))['Order_Quantity'].transform('sum')

# Crear DataFrame con las variables ponderadas mensuales
monthly_data = df.groupby(pd.Grouper(key='Date', freq='ME')).agg({
    'Costo_Ponderado': 'mean',
    'Margen_Ponderado': 'mean',
    'Precio_Ponderado': 'mean'
}).reset_index()

# Crear la aplicación Dash
app = dash.Dash(__name__)
application = app.server

# Definir una paleta de colores personalizada
custom_colors = px.colors.qualitative.Set1

# Layout de la aplicación
app.layout = html.Div([
    html.Div([
        html.Div([
            dcc.RangeSlider(
                id='year-slider',
                min=df['Date'].dt.year.min(),
                max=df['Date'].dt.year.max(),
                value=[df['Date'].dt.year.min(), df['Date'].dt.year.max()],
                marks={str(year): str(year) for year in range(df['Date'].dt.year.min(), df['Date'].dt.year.max() + 1)},
                step=None
            )
        ], style={'width': '50%', 'display': 'inline-block'}),
        html.Div([
            dcc.Dropdown(
                id='group-by-dropdown',
                options=[
                    {'label': 'Product Category', 'value': 'Product_Category'},
                    {'label': 'Sub Category', 'value': 'Sub_Category'},
                    {'label': 'Product', 'value': 'Product'}
                ],
                optionHeight= 35,
                value='Product_Category',
                placeholder="Please Select...",
                searchable = True,
                search_value = '',
                clearable=False,
                style={'width': '180px', 'fontSize': '14px', 'margin': 'auto'}  # Ajusta el ancho máximo del dropdown
            ),
        ], style={'width': '50%', 'display': 'inline-block', 'textAlign': 'center'}),
        html.Div([
            # Asigna un ID único al componente dcc.Dropdown
            dcc.Dropdown(
                id='filter-dropdown',
                placeholder='Selecciona opciones',
                multi=True,
                style={'width': '150px', 'fontSize': '14px', 'margin': 'auto'}  # Ajusta el ancho máximo del dropdown
            ),
        ], id='filter-dropdown-container', style={'width': '50%', 'display': 'inline-block', 'textAlign': 'center'}),
    ], style={'margin': '50px', 'display': 'flex', 'justifyContent': 'space-between'}),  # Alinea los elementos a ambos lados

    html.Div([
        html.Div([
            dcc.Graph(id='line-chart', style={'width': '100%', 'height': '100%'})  # Define el tamaño del gráfico de líneas
        ], style={'width': '50%', 'display': 'inline-block'}),
        html.Div([
            dcc.Graph(id='tree-chart', style={'width': '100%', 'height': '100%'})  # Define el tamaño del treemap
        ], style={'width': '50%', 'display': 'inline-block'}),
    ]),
    dcc.Graph(id='box-plot', style={'width': '100%', 'height': '100%'}),  # Define el tamaño del gráfico de cajas
    dcc.Graph(id='bar-chart', style={'width': '100%', 'height': '100%'}),  # Define el tamaño del gráfico de barras
    dcc.Graph(id='choropleth-map', style={'width': '100%', 'height': '100%'}),  # Define el tamaño del mapa de calor
    dcc.Interval(
        id='interval-component',
        interval=60000,
        n_intervals=0
    )
])

# Callback para mostrar el filtro dinámico basado en la selección del primer dropdown
@app.callback(
    Output('filter-dropdown-container', 'children'),
    [Input('group-by-dropdown', 'value')]
)
def update_filter_dropdown(group_by):
    if group_by == 'Product_Category':
        options = [{'label': category, 'value': category} for category in df['Product_Category'].unique()]
    elif group_by == 'Sub_Category':
        options = [{'label': category, 'value': category} for category in df['Sub_Category'].unique()]
    elif group_by == 'Product':
        options = [{'label': product, 'value': product} for product in df['Product'].unique()]
    else:
        options = []
    
    return dcc.Dropdown(
        id='filter-dropdown',
        options=options,
        placeholder='Selecciona opciones',
        multi=True,
        style={'width': '150px', 'fontSize': '14px', 'margin': 'auto'}  # Ajusta el ancho máximo del dropdown
    )

# Callback para actualizar los gráficos con los datos más recientes
@app.callback(
    [Output('line-chart', 'figure'),
     Output('tree-chart', 'figure'),
     Output('box-plot', 'figure'),
     Output('bar-chart', 'figure')],
    [Input('interval-component', 'n_intervals'),
     Input('group-by-dropdown', 'value'),
     Input('filter-dropdown', 'value'),
     Input('year-slider', 'value')]
)
def update_figures(n, group_by, filter_by, year_range):
    # Filtrar los datos por el rango de años seleccionado
    filtered_df = df[(df['Date'].dt.year >= year_range[0]) & (df['Date'].dt.year <= year_range[1])]
    
    # Aplicar el filtro seleccionado en el nuevo dropdown
    if filter_by:
        filtered_df = filtered_df[filtered_df[group_by].isin(filter_by)]

    # Agrupar los datos mensualmente y calcular la suma del revenue para cada categoría en cada mes
    monthly_revenue = filtered_df.groupby([pd.Grouper(key='Date', freq='ME'), group_by])['Revenue'].sum().reset_index()

    # Tendencia lineal
    line_fig = px.line(monthly_revenue, x='Date', y='Revenue', color=group_by,
                        title='Tendencia de Ventas Mensuales por {}'.format(group_by),
                        color_discrete_sequence=custom_colors)

    # Calcular la fecha hace 30 días a partir de la última fecha en el conjunto de datos
    fecha_inicio = filtered_df['Date'].max() - pd.Timedelta(days=30)

    # Filtrar los datos para obtener los últimos 30 días
    last_30_days_df = filtered_df[filtered_df['Date'] >= fecha_inicio]

    # Calcular la suma del revenue por categoría
    tree_data = last_30_days_df.groupby([group_by])['Revenue'].sum().reset_index()

    # Crear el treemap
    tree_fig = px.treemap(tree_data, path=[group_by], values='Revenue', custom_data=['Revenue'],
                          title='Ventas de los últimos 30 días por {}'.format(group_by),
                          color_discrete_sequence=custom_colors)

    # Configurar el texto del hover para incluir el revenue
    tree_fig.update_traces(hovertemplate='<b>%{label}</b><br><br>Revenue: %{customdata[0]:,.2f}')

    # Configurar el texto de las celdas para incluir el revenue y el signo de la moneda
    tree_fig.update_traces(texttemplate='%{label}: $%{value:,.2f}')

    # Filtrar los datos mensuales ponderados
    filtered_monthly_data = filtered_df.groupby(pd.Grouper(key='Date', freq='ME')).agg({
        'Costo_Ponderado': 'mean',
        'Margen_Ponderado': 'mean',
        'Precio_Ponderado': 'mean'
    }).reset_index()

    # Trazar el gráfico de barras
    bar_fig = px.bar(filtered_monthly_data, x='Date', y=['Costo_Ponderado', 'Precio_Ponderado'],
                     barmode='group', title='Variables Ponderadas Mensuales',
                     labels={'Date': 'Fecha', 'value': 'Valor Ponderado', 'variable': 'Variable'},
                     color_discrete_sequence=custom_colors)

    # Agregar la línea de margen ponderado en un segundo eje
    bar_fig.add_trace(go.Scatter(x=filtered_monthly_data['Date'], y=filtered_monthly_data['Margen_Ponderado'],
                                  mode='lines', name='Margen Ponderado', yaxis='y2'))

    # Actualizar el layout para agregar el segundo eje y configurar la posición de la leyenda
    bar_fig.update_layout(yaxis2=dict(title='Margen Ponderado', overlaying='y', side='right'),
                          legend=dict(x=1.1, y=1))

    # Inicializar la variable box_fig
    box_fig = None

    # Si el dropdown es 'Product Category'
    if group_by == 'Product_Category':
        # Calcular la media del Unit_Price y del Unit_Cost por categoría de producto
        Prom_Unit_Price = last_30_days_df.groupby(['Product', 'Product_Category'])['Unit_Price'].mean().reset_index()
        Prom_Unit_Cost = last_30_days_df.groupby(['Product', 'Product_Category'])['Unit_Cost'].mean().reset_index()

        # Fusionar los DataFrames de promedios por categoría de producto
        merged_df = pd.merge(Prom_Unit_Price, Prom_Unit_Cost, on=['Product', 'Product_Category'], suffixes=('_Price', '_Cost'))

        # Calcular margen porcentual unitario por categoría de producto
        merged_df['Margen_Porcentual_Unitario'] = (merged_df['Unit_Price'] - merged_df['Unit_Cost']) / merged_df['Unit_Price']

        # Crear el boxplot agrupado por Product_Category
        box_fig = px.box(merged_df, x='Product_Category', y='Margen_Porcentual_Unitario',
                     title='Promedio Margen Porcentual Unitario por Categoría de Producto',
                     color='Product_Category',
                     color_discrete_sequence=custom_colors)
    # Si el dropdown es 'Sub Category'
    elif group_by == 'Sub_Category':
        # Calcular la media del Unit_Price y del Unit_Cost por subcategoría de producto
        Prom_Unit_Price = last_30_days_df.groupby(['Product', 'Sub_Category'])['Unit_Price'].mean().reset_index()
        Prom_Unit_Cost = last_30_days_df.groupby(['Product', 'Sub_Category'])['Unit_Cost'].mean().reset_index()

        # Fusionar los DataFrames de promedios por subcategoría de producto
        merged_df = pd.merge(Prom_Unit_Price, Prom_Unit_Cost, on=['Product', 'Sub_Category'], suffixes=('_Price', '_Cost'))

        # Calcular margen porcentual unitario por subcategoría de producto
        merged_df['Margen_Porcentual_Unitario'] = (merged_df['Unit_Price'] - merged_df['Unit_Cost']) / merged_df['Unit_Price']

        # Crear el boxplot agrupado por Sub_Category
        box_fig = px.box(merged_df, x='Sub_Category', y='Margen_Porcentual_Unitario',
                     title='Promedio Margen Porcentual Unitario por Subcategoría de Producto',
                     color='Sub_Category',
                     color_discrete_sequence=custom_colors)

    return [line_fig, tree_fig, box_fig, bar_fig]


# Callback para actualizar el mapa de calor
@app.callback(
    Output('choropleth-map', 'figure'),
    [Input('interval-component', 'n_intervals'),
     Input('year-slider', 'value')]
)
def update_choropleth_map(n, year_range):
    # Filtrar los datos por el rango de años seleccionado
    filtered_df = df[(df['Date'].dt.year >= year_range[0]) & (df['Date'].dt.year <= year_range[1])]
    
    # Filtrar los datos para obtener las ventas de los últimos 30 días
    fecha_inicio = filtered_df['Date'].max() - pd.Timedelta(days=30)
    last_30_days_df = filtered_df[filtered_df['Date'] >= fecha_inicio]

    # Calcular el Revenue sumado de los últimos 30 días por país y estado
    revenue_by_country = last_30_days_df.groupby('Country')['Revenue'].sum().reset_index()
    
    # Crear el mapa de calor para los países
    fig = px.choropleth(
        revenue_by_country,
        locations='Country',
        locationmode='country names',
        color='Revenue',
        hover_name='Country',
        color_continuous_scale='viridis',
        title='Ventas por País en los últimos 30 días'
    )
    # Actualizar el diseño del mapa
    fig.update_layout(
        geo=dict(
            showcoastlines=True,  # Mostrar líneas de costa
            projection_type='equirectangular'  # Tipo de proyección
        )
    )
    return fig

# Ejecutar la aplicación
if __name__=='__main__':
    application.run(host='0.0.0.0', port='8080')