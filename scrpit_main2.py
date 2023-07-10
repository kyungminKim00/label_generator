import yfinance as yf
import pandas as pd
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import plotly.graph_objs as go
import json

# 주식의 심볼을 지정합니다.
symbol = 'AAPL'

# 주가 데이터를 가져옵니다.
data = yf.download(symbol, period='1y')

# 이동평균을 계산합니다.
data['10_day_MA'] = data['Close'].rolling(window=10).mean()
data['50_day_MA'] = data['Close'].rolling(window=50).mean()
data['100_day_MA'] = data['Close'].rolling(window=100).mean()

# 데이터프레임을 대시보드에서 사용할 수 있는 형식으로 변환합니다.
df = data.reset_index()

app = dash.Dash(__name__)

app.layout = html.Div([
    html.Button('Step Forward', id='step-forward-button', n_clicks=0),
    html.Button('Step Backward', id='step-backward-button', n_clicks=0),
    html.Button('Mark Line', id='mark-line-button', n_clicks=0),
    dcc.Graph(id='live-graph'),
    html.Div(id='hidden-div', style={'display':'none'}, children=['', 0]),
    html.Div(id='lines-div', style={'display':'none'}, children='[]')  # 초기 값을 '[]'로 설정합니다.
])


@app.callback(
    Output('hidden-div', 'children'),
    [Input('step-forward-button', 'n_clicks'),
     Input('step-backward-button', 'n_clicks')],
    [State('hidden-div', 'children')]
)
def update_step(n_forward, n_backward, n):
    ctx = dash.callback_context
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if button_id == 'step-forward-button' and n[1] < len(df):
        return ['forward', n[1]+1]
    elif button_id == 'step-backward-button' and n[1] > 0:
        return ['backward', n[1]-1]
    else:
        return n

@app.callback(
    Output('lines-div', 'children'),
    [Input('mark-line-button', 'n_clicks')],
    [State('hidden-div', 'children'),
     State('lines-div', 'children')]
)
def update_lines(n_mark, n, lines):
    

    ctx = dash.callback_context
    button_id, step = n

    if isinstance(lines, str):
        lines = json.loads(lines)

    if ctx.triggered[0]['prop_id'].split('.')[0] == 'mark-line-button' and step > 0:
        lines = []
        line_level = df['Close'][step-1]
        new_line = {'date': df['Date'][step-1].strftime("%Y-%m-%d"), 'level': line_level}  # date를 문자열로 변환합니다.
        lines.append(new_line)

    return json.dumps(lines)


@app.callback(
    Output('live-graph', 'figure'), 
    [Input('hidden-div', 'children')],
    [State('lines-div', 'children')]
)
def update_graph_live(n, lines):
    

    _, step = n
    lines = json.loads(lines)  # lines를 JSON 문자열에서 Python 객체로 변환합니다.

    data = [
        go.Candlestick(
            x=df['Date'][:step],
            open=df['Open'][:step],
            high=df['High'][:step],
            low=df['Low'][:step],
            close=df['Close'][:step]
        ),
        go.Scatter(x=df['Date'][:step], y=df['10_day_MA'][:step], mode='lines', name='10일 이동평균'),
        go.Scatter(x=df['Date'][:step], y=df['50_day_MA'][:step], mode='lines', name='50일 이동평균'),
        go.Scatter(x=df['Date'][:step], y=df['100_day_MA'][:step], mode='lines', name='100일 이동평균')
    ]

    shapes = []
    for line in lines:
        h_line = {
            'type': 'line',
            'xref': 'paper', 'x0': 0, 'x1': 1,
            'yref': 'y', 'y0': line['level'], 'y1': line['level'],
            'line': {'color': 'black', 'width': 1, 'dash': 'dash'}
        }
        v_line = {
            'type': 'line',
            'xref': 'x', 'x0': line['date'], 'x1': line['date'],
            'yref': 'paper', 'y0': 0, 'y1': 1,
            'line': {'color': 'black', 'width': 1, 'dash': 'dash'}
        }
        shapes.extend([h_line, v_line])
    layout = go.Layout(xaxis = {'rangeslider': {'visible': False}}, shapes=shapes)

    return {'data': data, 'layout': layout}

if __name__ == '__main__':
    app.run_server(debug=True)
