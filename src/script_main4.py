import json
import pprint

import dash
import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
import plotly.graph_objs as go
import yfinance as yf
from dash.dependencies import Input, Output, State

# 모듈 정보
with open("./src/config.json", "r", encoding="utf-8") as fp:
    env_dict = json.load(fp)

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
        html.Button("Step Forward", id="step-forward-button", n_clicks=0),
        html.Button("Step Backward", id="step-backward-button", n_clicks=0),
        html.Button("Buy", id="buy-button", n_clicks=0),
        html.Button("Buy-Clear", id="buy-clear-button", n_clicks=0),
        html.Button("Sell", id="sell-button", n_clicks=0),
        html.Button("Sell-Clear", id="sell-clear-button", n_clicks=0),
        html.Button("Save Actions", id="save-action-button", n_clicks=0),
        dcc.Graph(id="live-graph"),
        html.Div(id="hidden-div", style={"display": "none"}, children=["", 0]),
        html.Div(id="hidden-div2", style={"display": "none"}, children=["", 0]),
        html.Div(
            id="actions-div", style={"display": "none"}, children="[]"
        ),  # 초기 값을 '[]'로 설정합니다.
        dcc.Textarea(
            id="action-history",
            value="Actions will be displayed here",
            style={"width": "100%", "height": 200},
        ),
    ]
)


def calculate_profit(profits):
    total_profit = 1  # 최종 수익률을 계산하기 위한 변수. 초기값은 1(즉, 100%)로 설정.

    n_items = len(profits)
    if n_items % 2 != 0:  # 만약 profits의 길이가 홀수라면
        profits = profits[:-1]  # profits의 마지막 요소를 제거
        n_items -= 1

    for i in range(0, n_items, 2):  # profits 리스트를 두 개씩 건너뛰며 반복
        action_1 = profits[i]
        action_2 = profits[i + 1]

        initial_price = action_1["level"]
        final_price = action_2["level"]

        # 매수와 매수 청산의 조합을 확인하고 수익률을 계산
        if action_1["act"] == "buy" and action_2["act"] == "buy_clear":
            profit_ratio = final_price / initial_price
        # 매도와 매도 청산의 조합을 확인하고 수익률을 계산
        elif action_1["act"] == "sell" and action_2["act"] == "sell_clear":
            profit_ratio = initial_price / final_price
        else:
            continue

        total_profit *= profit_ratio  # 현재까지의 총 수익률을 업데이트

    return (total_profit - 1) * 100  # 백분율로 수익률 변환


@app.callback(
    Output("action-history", "value"),
    [
        Input("actions-div", "children"),
    ],
)
def update_textarea(actions):
    profits = f"{str(0)} % \n"

    actions = json.loads(actions)  # actions를 JSON 문자열에서 Python 객체로 변환합니다.
    if len(actions) > 1:
        profits = f"{calculate_profit(actions):.3}% \n"  # 수익률을 계산합니다.
    actions = actions[::-1]

    return (
        "profits: " + str(profits) + "\n".join(map(str, actions))
    )  # 리스트의 각 요소를 문자열로 변환하고, 각 요소 사이에 줄바꿈을 추가합니다.


@app.callback(
    Output("hidden-div", "children"),
    [
        Input("step-forward-button", "n_clicks"),
        Input("step-backward-button", "n_clicks"),
        Input("buy-button", "n_clicks"),
        Input("buy-clear-button", "n_clicks"),
        Input("sell-button", "n_clicks"),
        Input("sell-clear-button", "n_clicks"),
    ],
    [State("hidden-div", "children")],
)
def update_step(n_forward, n_backward, n_buy, n_buy_clear, n_sell, n_sell_clear, n):
    ctx = dash.callback_context
    button_id = ctx.triggered[0]["prop_id"].split(".")[0]

    if button_id == "step-forward-button" and n[1] < len(df):
        return ["forward", n[1] + 1]
    elif button_id == "step-backward-button" and n[1] > 0:
        return ["backward", n[1] - 1]
    else:
        return n


@app.callback(
    Output("hidden-div2", "children"),
    [Input("save-action-button", "n_clicks")],
    [State("actions-div", "children")],
)
def save_action(n_save_action, actions):
    pd.read_json(actions).to_csv(f"{env_dict['base_dir']}/{env_dict['save_actions']}", index=False)

@app.callback(
    Output("actions-div", "children"),
    [
        Input("buy-button", "n_clicks"),
        Input("buy-clear-button", "n_clicks"),
        Input("sell-button", "n_clicks"),
        Input("sell-clear-button", "n_clicks"),
    ],
    [State("hidden-div", "children"), State("actions-div", "children")],
)
def update_actions(n_buy, n_buy_clear, n_sell, n_sell_clear, n, actions):
    ctx = dash.callback_context
    button_id, step = n

    if isinstance(actions, str):
        actions = json.loads(actions)

    if ctx.triggered[0]["prop_id"].split(".")[0] == "buy-button" and step > 0:
        line_level = df["Close"][step - 1]
        new_line = {
            "date": df["Date"][step - 1].strftime("%Y-%m-%d"),
            "level": line_level,
            "act": "buy",
        }  # date를 문자열로 변환합니다.
        actions.append(new_line)

    if ctx.triggered[0]["prop_id"].split(".")[0] == "buy-clear-button" and step > 0:
        line_level = df["Close"][step - 1]
        new_line = {
            "date": df["Date"][step - 1].strftime("%Y-%m-%d"),
            "level": line_level,
            "act": "buy_clear",
        }  # date를 문자열로 변환합니다.
        actions.append(new_line)

    if ctx.triggered[0]["prop_id"].split(".")[0] == "sell-button" and step > 0:
        line_level = df["Close"][step - 1]
        new_line = {
            "date": df["Date"][step - 1].strftime("%Y-%m-%d"),
            "level": line_level,
            "act": "sell",
        }  # date를 문자열로 변환합니다.
        actions.append(new_line)

    if ctx.triggered[0]["prop_id"].split(".")[0] == "sell-clear-button" and step > 0:
        line_level = df["Close"][step - 1]
        new_line = {
            "date": df["Date"][step - 1].strftime("%Y-%m-%d"),
            "level": line_level,
            "act": "sell_clear",
        }  # date를 문자열로 변환합니다.
        actions.append(new_line)

    return json.dumps(actions)


@app.callback(
    Output("live-graph", "figure"),
    [Input("hidden-div", "children")],
    [State("actions-div", "children")],
)
def update_graph_live(n, actions):
    _, step = n
    actions = json.loads(actions)  # actions를 JSON 문자열에서 Python 객체로 변환합니다.

    data = [
        go.Candlestick(
            x=df["Date"][:step],
            open=df["Open"][:step],
            high=df["High"][:step],
            low=df["Low"][:step],
            close=df["Close"][:step],
        ),
        go.Scatter(
            x=df["Date"][:step], y=df["10_day_MA"][:step], mode="lines", name="10일 이동평균"
        ),
        go.Scatter(
            x=df["Date"][:step], y=df["50_day_MA"][:step], mode="lines", name="50일 이동평균"
        ),
        go.Scatter(
            x=df["Date"][:step],
            y=df["100_day_MA"][:step],
            mode="lines",
            name="100일 이동평균",
        ),
    ]

    shapes = []
    color = None
    if len(actions) > 0:
        line = actions[-1]
        if line["act"] == "buy":
            color = "green"
        elif line["act"] == "sell":
            color = "red"
        else:
            color = None

        if color is not None:
            h_line = {
                "type": "line",
                "xref": "paper",
                "x0": 0,
                "x1": 1,
                "yref": "y",
                "y0": line["level"],
                "y1": line["level"],
                "line": {"color": color, "width": 1, "dash": "dash"},
            }
            v_line = {
                "type": "line",
                "xref": "x",
                "x0": line["date"],
                "x1": line["date"],
                "yref": "paper",
                "y0": 0,
                "y1": 1,
                "line": {"color": color, "width": 1, "dash": "dash"},
            }
            shapes.extend([h_line, v_line])

    layout = go.Layout(xaxis={"rangeslider": {"visible": False}}, shapes=shapes)

    return {"data": data, "layout": layout}


if __name__ == "__main__":
    app.run_server(debug=True)