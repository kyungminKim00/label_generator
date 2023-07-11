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


# replay data load
def replay_data_load(f_name, env_dict):
    replay_dict = load(f_name)
    replay_actions, replay_data = (
        replay_dict["replay_actions"],
        replay_dict["replay_data"],
    )
    replay_actions.set_index(env_dict["index_name"], inplace=True)

    last_action_date = replay_actions.index[-1]
    replay_data = replay_data.join(replay_actions)

    return replay_data.loc[:last_action_date]


replay_file_name = (
    "AAPL_15m_2023-04-13 10:30:00_2023-04-13 13:45:00_0.0_replay_actions.pkl"
)

with open("./src/config.json", "r", encoding="utf-8") as fp:
    env_dict = json.load(fp)
pprint.pprint(env_dict)


replay_data = replay_data_load(f"./assets/{replay_file_name}", env_dict)

# 데이터프레임을 대시보드에서 사용할 수 있는 형식으로 변환합니다.
df = replay_data.reset_index()
total_sample = len(df)

app = dash.Dash(__name__)

app.layout = html.Div(
    [
        html.Div(
            id="return-rate",
            children="수익률: 0.000%",
            style={
                "font-size": "20px",
                "font-weight": "bold",
                "color": "red",
                "margin-bottom": "10px",
                "margin-left": "10px",
                "margin-top": "10px",  # 위쪽 여백
                "margin-right": "10px",  # 오른쪽 여백
                "text-align": "center",
            },
        ),
        dcc.Graph(id="live-graph"),
        dcc.Interval(
            id="interval-component",
            interval=env_dict["replay_interval"] * 1000,
            n_intervals=0,
        ),
        dcc.Store(id="x-value"),
        dcc.Store(id="y-value"),
        html.Button("PAUSE", id="pause-button", n_clicks=0),
        html.Button("RESUME", id="resume-button", n_clicks=0),
        dcc.Dropdown(
            id="interval-dropdown",
            options=[
                {"label": "0.1초", "value": 0.1},
                {"label": "0.2초", "value": 0.2},
                {"label": "0.5초", "value": 0.5},
                {"label": "1초", "value": 1},
                {"label": "2초", "value": 2},
                {"label": "5초", "value": 5},
            ],
            value=env_dict["replay_interval"],
            style={"width": "100px"},
        ),
    ]
)


def calculate_return_rate(n, current_data):
    if n > 0:
        open_buy, open_sell = None, None
        tot_return_rate = 0
        for idx in list(current_data.index):
            current_df = current_data.loc[idx]
            current_prc = current_df["Close"]

            # Open position
            if current_df["act"] == "buy":  # 나중에 리스트 처리 해서 멀티 포지션 계산할 수 있음
                open_buy = current_prc
            elif current_df["act"] == "sell":
                open_sell = current_prc

            # Clse position
            if current_df["act"] == "buy_clear":
                tot_return_rate += ((current_prc - open_buy) / open_buy) * 100
                open_buy = None
            elif current_df["act"] == "sell_clear":
                tot_return_rate += ((current_prc - open_sell) / open_sell) * -1 * 100
                open_sell = None

            # Hold position
            if open_buy is not None:
                tot_return_rate += ((current_prc - open_buy) / open_buy) * 100
            if open_sell is not None:
                tot_return_rate += ((current_prc - open_sell) / open_sell) * -1 * 100

        # Format return rate as percentage
        return_rate_str = f"수익률: {tot_return_rate:.3f}%"
    else:
        return_rate_str = f"수익률: {0:.3f}%"
    return return_rate_str


@app.callback(
    Output("return-rate", "children"), [Input("interval-component", "n_intervals")]
)
def update_return_rate(n):
    # Get the last row of the dataframe
    n = n % total_sample
    current_data = df.iloc[:n]

    return calculate_return_rate(n, current_data)


@app.callback(
    Output("interval-component", "interval"), [Input("interval-dropdown", "value")]
)
def update_interval(value):
    return value * 1000


@app.callback(
    Output("interval-component", "max_intervals"),
    [Input("pause-button", "n_clicks"), Input("resume-button", "n_clicks")],
)
def pause_resume(pause_clicks, resume_clicks):
    if pause_clicks > resume_clicks:
        return 0
    else:
        return -1


@app.callback(
    Output("live-graph", "figure"),
    Output("x-value", "data"),
    Output("y-value", "data"),
    [
        Input("interval-component", "n_intervals"),
        Input("x-value", "data"),
        Input("y-value", "data"),
    ],
)
def update_graph_live(n, y_value, x_value):
    # 캔들스틱 그래프와 이동평균선을 그립니다.
    n = n % total_sample

    prc_of_date = df[env_dict["index_name"]][:n]
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
        if not np.isnan(df["level"][n - 1]):
            y_value = df["level"][n - 1]
            x_value = df[env_dict["index_name"]][n - 1]

            act = df["act"][n - 1]
            color = "grey"
            _dash = "solid"
            if act == "buy" or act == "sell":
                _dash = "dash"
                if act == "buy":
                    color = "green"
                else:
                    color = "red"

            y_value = {
                "type": "line",
                "xref": "paper",
                "x0": 0,
                "x1": 1,
                "yref": "y",
                "y0": y_value,
                "y1": y_value,
                "line": {"color": color, "width": 2, "dash": _dash},
            }
            x_value = {
                "type": "line",
                "xref": "x",
                "x0": x_value,
                "x1": x_value,
                "yref": "paper",
                "y0": 0,
                "y1": 1,
                "line": {"color": color, "width": 2, "dash": _dash},
            }

        shapes.extend([y_value, x_value])
    else:
        y_value, x_value = None, None

    if y_value is None and x_value is None:
        layout = go.Layout(xaxis={"rangeslider": {"visible": False}})
    else:
        layout = go.Layout(xaxis={"rangeslider": {"visible": False}}, shapes=shapes)

    return {"data": data, "layout": layout}, y_value, x_value


if __name__ == "__main__":
    app.run_server(debug=True)
