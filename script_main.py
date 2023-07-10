import yfinance as yf
import pandas as pd
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import plotly.graph_objs as go

# 주식의 심볼을 지정합니다.
symbol = "AAPL"

# 주가 데이터를 가져옵니다.
data = yf.download(symbol, period="1y")

# 이동평균을 계산합니다.
data["10_day_MA"] = data["Close"].rolling(window=10).mean()
data["50_day_MA"] = data["Close"].rolling(window=50).mean()
data["100_day_MA"] = data["Close"].rolling(window=100).mean()

# 데이터프레임을 대시보드에서 사용할 수 있는 형식으로 변환합니다.
df = data.reset_index()

app = dash.Dash(__name__)

app.layout = html.Div(
    [
        html.Button("가격 표시", id="mark-price-button"),
        dcc.Graph(id="live-graph"),
        dcc.Interval(
            id="interval-component", interval=1 * 1000, n_intervals=0  # 1초마다 업데이트
        ),
    ]
)


# @app.callback(Output('live-graph', 'figure'),
#              [Input('interval-component', 'n_intervals'),
#               Input('mark-price-button', 'n_clicks')])
# def update_graph_live(n, n_clicks):
@app.callback(
    Output("live-graph", "figure"),
    [
        Input("interval-component", "n_intervals"),
        Input("mark-price-button", "n_clicks"),
    ],
    [State("mark-price-button", "n_clicks")],
)
def update_graph_live(n, n_clicks, n_clicks_state):
    # 캔들스틱 그래프와 이동평균선을 그립니다.
    print(n, n_clicks, n_clicks_state)
    data = [
        go.Candlestick(
            x=df["Date"][:n],
            open=df["Open"][:n],
            high=df["High"][:n],
            low=df["Low"][:n],
            close=df["Close"][:n],
        ),
        go.Scatter(
            x=df["Date"][:n], y=df["10_day_MA"][:n], mode="lines", name="10일 이동평균"
        ),
        go.Scatter(
            x=df["Date"][:n], y=df["50_day_MA"][:n], mode="lines", name="50일 이동평균"
        ),
        go.Scatter(
            x=df["Date"][:n], y=df["100_day_MA"][:n], mode="lines", name="100일 이동평균"
        ),
    ]

    # 현재 가격에 대한 수평선과 세로선을 그립니다.
    # if n_clicks is not None and n_clicks > 0:
    if n_clicks is not None and n_clicks > 0 and n_clicks_state > 0:
        line_level = df["Close"][n - 1]
        h_line = {
            "type": "line",
            "xref": "paper",
            "x0": 0,
            "x1": 1,
            "yref": "y",
            "y0": line_level,
            "y1": line_level,
            "line": {"color": "black", "width": 1, "dash": "dash"},
        }
        v_line = {
            "type": "line",
            "xref": "x",
            "x0": df["Date"][n - 1],
            "x1": df["Date"][n - 1],
            "yref": "paper",
            "y0": 0,
            "y1": 1,
            "line": {"color": "black", "width": 1, "dash": "dash"},
        }
        layout = go.Layout(
            xaxis={"rangeslider": {"visible": False}}, shapes=[h_line, v_line]
        )
    else:
        layout = go.Layout(xaxis={"rangeslider": {"visible": False}})

    return {"data": data, "layout": layout}


@app.callback(
    Output("mark-price-button", "n_clicks"),
    [Input("interval-component", "n_intervals")],
)
def reset_n_clicks(n):
    return 0


if __name__ == "__main__":
    app.run_server(debug=True)
