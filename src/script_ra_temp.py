import yfinance as yf
import pandas as pd
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import plotly.graph_objs as go
import pprint
import json
from joblib import load, dump
import numpy as np


replay_file_name = "AAPL_15m_2020-12-01_2021-01-29_0.0_True.json"

with open("./src/config.json", "r", encoding="utf-8") as fp:
    env_dict = json.load(fp)
pprint.pprint(env_dict)

# replay data load
replay_dict = pd.read_json(f"./assets/{replay_file_name}")
replay_actions = replay_dict["replay_actions"]
replay_data = replay_dict["replay_data"]


# 데이터프레임을 대시보드에서 사용할 수 있는 형식으로 변환합니다.
df = replay_data.reset_index()

app = dash.Dash(__name__)

app.layout = html.Div(
    [
        dcc.Graph(id="live-graph"),
        dcc.Interval(
            id="interval-component",
            interval=env_dict["replay_interval"] * 1000,
            n_intervals=0,  # 1초마다 업데이트
        ),
    ]
)


@app.callback(
    Output("live-graph", "figure"),
    [
        Input("interval-component", "n_intervals"),
    ],
)
def update_graph_live(n):
    # 캔들스틱 그래프와 이동평균선을 그립니다.
    prc_of_date = df["Date"][:n]
    open_prc = df["Open"][:n]
    high_prc = df["High"][:n]
    low_prc = df["Low"][:n]
    close_prc = df["Close"][:n]
    data = [
        go.Candlestick(
            x=prc_of_date,
            open=open_prc,
            high=high_prc,
            low=low_prc,
            close=close_prc,
        ),
        go.Scatter(x=prc_of_date, y=df["10_day_MA"][:n], mode="lines", name="10일 이동평균"),
        go.Scatter(x=prc_of_date, y=df["50_day_MA"][:n], mode="lines", name="50일 이동평균"),
        go.Scatter(
            x=prc_of_date, y=df["100_day_MA"][:n], mode="lines", name="100일 이동평균"
        ),
    ]

    shapes = []
    if n > 0:
        y_value = df["h_line"][n - 1]
        x_value = df["v_line"][n - 1]
        if (
            np.isnan(df["h_line"][n - 1]) == False
            and np.isnan(df["v_line"][n - 1]) == False
        ):
            h_line = {
                "type": "line",
                "xref": "paper",
                "x0": 0,
                "x1": 1,
                "yref": "y",
                "y0": y_value,
                "y1": y_value,
                "line": {"color": "black", "width": 1, "dash": "dash"},
            }

            v_line = {
                "type": "line",
                "xref": "x",
                "x0": x_value,
                "x1": x_value,
                "yref": "paper",
                "y0": 0,
                "y1": 1,
                "line": {"color": "black", "width": 1, "dash": "dash"},
            }
            shapes.extend([h_line, v_line])

    layout = go.Layout(xaxis={"rangeslider": {"visible": False}}, shapes=shapes)

    return {"data": data, "layout": layout}


if __name__ == "__main__":
    app.run_server(debug=True)
