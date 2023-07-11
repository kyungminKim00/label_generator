import json
import pprint

import dash
import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
import plotly.graph_objs as go
import yfinance as yf
from dash.dependencies import Input, Output, State
from joblib import load, dump

# 모듈 정보
with open("./src/config.json", "r", encoding="utf-8") as fp:
    env_dict = json.load(fp)
pprint.pprint(env_dict)

# 주가 데이터를 가져옵니다.
if env_dict["interval"] == "15m":
    env_dict["period"] = "60d"  # 60일 15min max period
    f_strftime = "%Y-%m-%d %H:%M:%S"
else:
    f_strftime = "%Y-%m-%d"
data = yf.download(
    tickers=env_dict["tickers"],
    period=env_dict["period"],
    interval=env_dict["interval"],
)
data.index.name = env_dict["index_name"]


start = str(data.index[0]).replace(":", "_").replace("-", "_").replace(" ", "_")
end = str(data.index[-1]).replace(":", "_").replace("-", "_").replace(" ", "_")


# 이동평균을 계산합니다.
data["10_day_MA"] = data["Close"].rolling(window=10).mean()
data["50_day_MA"] = data["Close"].rolling(window=50).mean()
data["100_day_MA"] = data["Close"].rolling(window=100).mean()

# 데이터프레임을 대시보드에서 사용할 수 있는 형식으로 변환합니다.
df = data.reset_index()


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
        html.Button(
            "Step Forward",
            id="step-forward-button",
            n_clicks=0,
            style={"margin-right": "0px"},
        ),
        html.Button(
            "Step Backward",
            id="step-backward-button",
            n_clicks=0,
            style={"margin-right": "10px"},
        ),
        html.Button("Buy", id="buy-button", n_clicks=0, style={"margin-right": "0px"}),
        html.Button(
            "Buy-Clear",
            id="buy-clear-button",
            n_clicks=0,
            style={"margin-right": "10px"},
        ),
        html.Button(
            "Sell", id="sell-button", n_clicks=0, style={"margin-right": "0px"}
        ),
        html.Button(
            "Sell-Clear",
            id="sell-clear-button",
            n_clicks=0,
            style={"margin-right": "10px"},
        ),
        html.Button(
            "Save Actions",
            id="save-action-button",
            n_clicks=0,
            style={"margin-right": "10px"},
        ),
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


def calculate_return_rate(n, current_data):
    if n > 0:
        open_buy, open_sell = [], []
        opening_buy_positions, opening_sell_positions = 0, 0
        tot_return_rate = 0

        last_buy_clear = current_data[current_data["act"] == "buy_clear"].index
        last_sell_clear = current_data[current_data["act"] == "sell_clear"].index

        if len(last_buy_clear) == 0:
            opening_buy_positions = current_data[current_data["act"] == "buy"].shape[0]
        else:
            last_buy_clear = last_buy_clear[-1]
            tmp = current_data.loc[last_buy_clear:]
            opening_buy_positions = tmp[tmp["act"] == "buy"].shape[0]

        if len(last_sell_clear) == 0:
            opening_sell_positions = current_data[current_data["act"] == "sell"].shape[
                0
            ]
        else:
            last_sell_clear = last_sell_clear[-1]
            tmp = current_data.loc[last_sell_clear:]
            opening_sell_positions = tmp[tmp["act"] == "sell"].shape[0]

        for idx in list(current_data.index):
            current_df = current_data.loc[idx]
            current_prc = current_df["level"]

            if current_df["act"] == "buy":
                open_buy.append(current_prc)
            elif current_df["act"] == "sell":
                open_sell.append(current_prc)

            if current_df["act"] == "buy_clear":
                for _ in range(len(open_buy)):
                    ob_prc = open_buy.pop()
                    tot_return_rate += ((current_prc - ob_prc) / ob_prc) * 100
            elif current_df["act"] == "sell_clear":
                for _ in range(len(open_sell)):
                    os_prc = open_sell.pop()
                    tot_return_rate += ((current_prc - os_prc) / os_prc) * -1 * 100

        # Format return rate as percentage
        return_rate_str = f"수익률: {tot_return_rate:.3f}% (매수포지션:{opening_buy_positions}, 매도포지션:{opening_sell_positions})"
    else:
        return_rate_str = f"수익률: {0:.3f}%"
    return return_rate_str


@app.callback(
    [Output("action-history", "value"), Output("return-rate", "children")],
    [
        Input("actions-div", "children"),
    ],
)
def update_textarea(actions):
    raw_actions = json.loads(actions)  # actions를 JSON 문자열에서 Python 객체로 변환합니다.
    actions = raw_actions[::-1]

    return "\n".join(map(str, actions)), calculate_return_rate(
        len(raw_actions), pd.DataFrame.from_dict(raw_actions)
    )


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
    res = pd.read_json(actions)
    if res.shape[0] > 0:
        s_action_date = str(res.iloc[0][env_dict["index_name"]])
        e_action_date = str(res.iloc[-1][env_dict["index_name"]])
        file_prefix = f"{env_dict['tickers']}_{env_dict['interval']}_{s_action_date}_{e_action_date}"

        dump(
            {"replay_actions": pd.read_json(actions), "replay_data": data},
            f"{env_dict['assets']}/{file_prefix}_{g_action_profits:.3}_{env_dict['save_actions']}",
        )
    return None


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
            env_dict["index_name"]: df[env_dict["index_name"]][step - 1].strftime(
                f_strftime
            ),
            "level": line_level,
            "act": "buy",
        }  # date를 문자열로 변환합니다.
        actions.append(new_line)

    if ctx.triggered[0]["prop_id"].split(".")[0] == "buy-clear-button" and step > 0:
        line_level = df["Close"][step - 1]
        new_line = {
            env_dict["index_name"]: df[env_dict["index_name"]][step - 1].strftime(
                f_strftime
            ),
            "level": line_level,
            "act": "buy_clear",
        }  # date를 문자열로 변환합니다.
        actions.append(new_line)

    if ctx.triggered[0]["prop_id"].split(".")[0] == "sell-button" and step > 0:
        line_level = df["Close"][step - 1]
        new_line = {
            env_dict["index_name"]: df[env_dict["index_name"]][step - 1].strftime(
                f_strftime
            ),
            "level": line_level,
            "act": "sell",
        }  # date를 문자열로 변환합니다.
        actions.append(new_line)

    if ctx.triggered[0]["prop_id"].split(".")[0] == "sell-clear-button" and step > 0:
        line_level = df["Close"][step - 1]
        new_line = {
            env_dict["index_name"]: df[env_dict["index_name"]][step - 1].strftime(
                f_strftime
            ),
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
    _data = df.iloc[:step]
    index_data = _data[env_dict["index_name"]]
    MA_10_day = df["10_day_MA"][:step]
    MA_50_day = df["50_day_MA"][:step]
    MA_100_day = df["100_day_MA"][:step]

    data = [
        go.Candlestick(
            x=index_data,
            open=_data["Open"],
            high=_data["High"],
            low=_data["Low"],
            close=_data["Close"],
        ),
        go.Scatter(x=index_data, y=MA_10_day, mode="lines", name="10일 이동평균"),
        go.Scatter(x=index_data, y=MA_50_day, mode="lines", name="50일 이동평균"),
        go.Scatter(
            x=index_data,
            y=MA_100_day,
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
                "line": {"color": color, "width": 2, "dash": "dash"},
            }
            v_line = {
                "type": "line",
                "xref": "x",
                "x0": line[env_dict["index_name"]],
                "x1": line[env_dict["index_name"]],
                "yref": "paper",
                "y0": 0,
                "y1": 1,
                "line": {"color": color, "width": 2, "dash": "dash"},
            }
            shapes.extend([h_line, v_line])

    layout = go.Layout(xaxis={"rangeslider": {"visible": False}}, shapes=shapes)

    return {"data": data, "layout": layout}


if __name__ == "__main__":
    app.run_server(debug=True)
