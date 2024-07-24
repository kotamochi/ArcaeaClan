import os
import json
import re
import asyncio
import dotenv
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import pandas as pd
import discord

#envファイル読み込み
dotenv.load_dotenv()

async def start(client, now):
    """在籍確認開始"""
    #設定ファイル読み込み
    with open(os.environ["CONFIG"], mode="r", encoding="utf-8") as f:
        config = json.load(f)["Member_Check"]
    #メンバーリスト取得
    memberlist = pd.read_csv(os.environ["MEMBERLIST"])
    #終了時間を取得
    finish_time = now + timedelta(days=config["CheckPeriod"])
    weekdays = ["月", "火", "水", "木", "金", "土", "日"]
    time_dict = {
        "year":str(finish_time.year),
        "month":str(finish_time.month),
        "day":str(finish_time.day),
        "hour":str(finish_time.hour),
        "weekday":str(weekdays[finish_time.weekday()])
    }
    #チャンネル取得
    annnounce_CH = await client.fetch_channel(int(os.environ["ANNOUNCE_CH"]))

    #メッセージ作成
    message = config["CheckText_1"] #在籍確認メッセージ
    message = text_edit_time(message, time_dict) #メッセージに時刻を入力

    #送信
    checkmessage = await annnounce_CH.send(message)
    await checkmessage.add_reaction("✋")

    #メッセージidを保存
    save_json(checkmessage.id, "CheckMessage_ID")

    #チェックリスト送信
    #確認状況ごとに分ける
    num_still = len(memberlist[memberlist["MemberCheck"] == 0])
    num_any = len(memberlist[memberlist["MemberCheck"] == 2])

    #各状況を入力
    message = config["CheckText_2"] #チェックリストメッセージ
    message = re.sub("{Check_No}", str(num_still), message)
    message = re.sub("{Check_Any}", str(num_any), message)
    message = re.sub("{ALL_Member}", str(len(memberlist)-1), message) #マスターを除く

    #送信
    await annnounce_CH.send(message)


async def check(client, now):
    """確認状況を取得して送信する"""
    #設定ファイル読み込み
    with open(os.environ["CONFIG"], mode="r", encoding="utf-8") as f:
        config = json.load(f)["Member_Check"]
    #メンバーリスト取得
    memberlist = pd.read_csv(os.environ["MEMBERLIST"])
    #リアクションをつけているユーザーを取得
    reactions = await client.channel.fetch_message(config["CheckMessage_ID"]).reactions
    users = [user async for user in reactions.users()]

    #リアクション済みのユーザーを記録
    for user in users:
        memberlist.loc[memberlist[memberlist["Discord_ID"] == user.id].index, "MemberCheck"] = 1

    #確認状況ごとに分ける
    still_df = memberlist[memberlist["MemberCheck"] == 0]
    ok_df = memberlist[memberlist["MemberCheck"] == 1]
    any_df = memberlist[memberlist["MemberCheck"] == 2]

    #メッセージを作成
    ok_message = f"確認済み：{len(ok_df)}/{len(memberlist)-1}\n" #マスターを除く
    for idx, ok_user in ok_df.iterrows():
        ok_message += f"{idx+1}.{ok_user["User_Name"]}\n"

    still_message = f"未確認：{len(still_df)}/{len(memberlist)-1}\n" #マスターを除く
    for idx, still_user in still_df.iterrows():
        still_message += f"{idx+1}.{still_user["User_Name"]}\n"

    any_message = f"任意確認：{len(any_df)}/{len(memberlist)-1}\n" #マスターを除く
    for idx, any_user in any_df.iterrows():
        any_message += f"{idx+1}.{any_user["User_Name"]}\n"

    message = f"{now.month}月{now.day}日 在籍確認進捗\n"
    message += ok_message + still_message + any_message

    #マスターのDMオブジェクトを作成
    master = await client.fetch_user(int(os.environ["MASTER_ID"]))
    master_DM = await master.create_dm()

    #送信
    await master_DM.send(message)


async def remind(client, now):
    """確認状況を取得してお知らせに送信する"""
    #設定ファイル読み込み
    with open(os.environ["CONFIG"], mode="r", encoding="utf-8") as f:
        config = json.load(f)["Member_Check"]
    #メンバーリスト取得
    memberlist = pd.read_csv(os.environ["MEMBERLIST"])
    #リアクションをつけているユーザーを取得
    reactions = await client.channel.fetch_message(config["CheckMessage_ID"]).reactions
    users = [user async for user in reactions.users()]

    #リアクション済みのユーザーを記録
    for user in users:
        memberlist.loc[memberlist[memberlist["Discord_ID"] == user.id].index, "MemberCheck"] = 1

    #確認状況ごとに分ける
    num_still = len(memberlist[memberlist["MemberCheck"] == 0])
    num_ok = len(memberlist[memberlist["MemberCheck"] == 1])
    num_any = len(memberlist[memberlist["MemberCheck"] == 2])

    #メッセージ作成
    message = config["CheckText_1"] #在籍確認メッセージ
    weekdays = ["月", "火", "水", "木", "金", "土", "日"]
    time_dict = {
        "year":str(now.year),
        "month":str(now.month),
        "day":str(now.day),
        "hour":str(now.hour),
        "weekday":str(weekdays[now.weekday()])
    }
    message = text_edit_time(message, time_dict) #メッセージに時刻を入力
    #各状況を入力
    message = re.sub("{Check_Ok}", str(num_ok), message)
    message = re.sub("{Check_No}", str(num_still), message)
    message = re.sub("{Check_Any}", str(num_any), message)
    message = re.sub("{ALL_Member}", str(len(memberlist)-1), message) #マスターを除く

    #チャンネル取得
    annnounce_CH = await client.fetch_channel(int(os.environ["ANNOUNCE_CH"]))

    #リマインド送信
    await annnounce_CH.send(message)


async def finish(client, now):
    #設定ファイル読み込み
    with open(os.environ["CONFIG"], mode="r", encoding="utf-8") as f:
        config = json.load(f)["Member_Check"]
    #メンバーリスト取得
    memberlist = pd.read_csv(os.environ["MEMBERLIST"])

    if len(memberlist[memberlist["MemberCheck"] == 0]):
        #全員確認済みの場合終了する
        weekdays = ["月", "火", "水", "木", "金", "土", "日"]
        time_dict = {
            "year":str(now.year),
            "month":str(now.month),
            "day":str(now.day),
            "hour":str(now.hour),
            "weekday":str(weekdays[now.weekday()])
        }
        message = config["CheckFinishText"] #在籍確認終了メッセージ
        message = text_edit_time(message, time_dict) #メッセージに時刻を入力
        #次回情報を入力
        next = now + relativedelta(months=1)
        message = re.sub("{NEXT_MONTH}", str(next.month), message)
        message = re.sub("{(NEXT_DAY)}", f"({str(weekdays[next.weekday()])})", message)

        #チャンネル取得
        annnounce_CH = await client.fetch_channel(int(os.environ["ANNOUNCE_CH"]))

        #在籍確認終了送信
        await annnounce_CH.send(message)

        #在籍確認を初期化
        reset()
    else:
        #終わってない場合はマスターにDMを送信
        #マスターのDMオブジェクトを作成
        master = await client.fetch_user(int(os.environ["MASTER_ID"]))
        master_DM = await master.create_dm()

        #送信
        await master_DM.send("在籍確認が完了していない為、終了メッセージが送信されませんでした。\n確認完了後、終了コマンドを使用してください。")


async def reset():
    """ユーザーの在籍確認状態をリセットする"""
    #メンバーリスト取得
    memberlist = pd.read_csv(os.environ["MEMBERLIST"])
    memberlist["MemberCheck"] = 0 #初期化
    #マスターのみ数値を変更
    memberlist.loc[memberlist[memberlist["Discord_ID"] == int(os.environ["MASTER_ID"])].index, "MemberCheck"] = 3 #計算に干渉しない値をセット

    memberlist.to_csv(os.environ["MEMBERLIST"], index=False) #保存


def text_edit_time(text, time_dict):
    """時間類のメッセージ編集"""
    text = re.sub("{YEAR}", time_dict["year"], text)
    text = re.sub("{MONTH}", time_dict["month"], text)
    text = re.sub("{DAY}", time_dict["day"], text)
    text = re.sub("{(DAY)}", f"({time_dict["weekday"]})", text)
    return text


def save_json(data, name):
    """jsonファイルに保存する"""
    #読み込む
    with open(os.environ["CONFIG"], mode="r", encoding="utf-8") as f:
        file = json.load(f)
        
    #追加
    file["Member_Check"][f"{name}"] = data

    #更新
    with open(os.environ["CONFIG"], mode="w", encoding="utf-8") as f:
        file = json.dump(file, f, indent=4)