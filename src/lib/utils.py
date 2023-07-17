# replay data load
from joblib import load, dump
import bottleneck as bn
import pandas as pd


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


def calculate_return_rate_rpy(n, current_data):
    if n > 0:
        open_buy, open_sell, open_buy_hold, open_sell_hold = [], [], [], []
        tot_return_rate, c_tot_return_rate = 0, 0

        for idx in list(current_data.index):
            current_df = current_data.loc[idx]
            current_prc = current_df["Close"]

            # Open position
            if current_df["act"] == "buy":  # 나중에 리스트 처리 해서 멀티 포지션 계산할 수 있음
                open_buy.append(current_prc)
            elif current_df["act"] == "sell":
                open_sell.append(current_prc)

            # Class position
            if current_df["act"] == "buy_clear":
                for _ in range(len(open_buy)):
                    ob_prc = open_buy.pop()
                    tot_return_rate += ((current_prc - ob_prc) / ob_prc) * 100
            elif current_df["act"] == "sell_clear":
                for _ in range(len(open_sell)):
                    os_prc = open_sell.pop()
                    tot_return_rate += ((current_prc - os_prc) / os_prc) * -1 * 100

        # Format return rate as percentage
        return_rate_str = f"수익률: {tot_return_rate:.3f}% (매수포지션:{len(open_buy)}, 매도포지션:{len(open_sell)})"
    else:
        return_rate_str = f"수익률: {0:.3f}%"
    return return_rate_str


def add_feature_movingmean(data, ma=[10, 50, 100]):
    for _ma in ma:
        data[f"{_ma}_day_MA"] = bn.move_mean(data["Close"], window=_ma, min_count=1)

    return data


def calculate_return_rate(raw_actions, current_data):
    if raw_actions > 0:
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
        return return_rate_str, tot_return_rate
    else:
        return f"수익률: {0:.3f}%", 0
