import os
import json
import re
import asyncio
import dotenv
from datetime import datetime, timedelta, date
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
    message = re.sub("{NOW_YEAR}", str(now.year), message)
    message = re.sub("{NOW_MONTH}", str(now.month), message)
    message = text_edit_time(message, time_dict) #メッセージに時刻を入力

    #送信
    checkmessage = await annnounce_CH.send(message)
    await checkmessage.add_reaction("✋")

    #メッセージidを保存
    save_json(checkmessage.id, "C_Msg_ID")

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
    cl_message = await annnounce_CH.send(message)
    
    #メッセージidを保存
    save_json(cl_message.id, "CL_Msg_ID")


async def check(client, now):
    """確認状況を取得して送信する"""
    #設定ファイル読み込み
    with open(os.environ["CONFIG"], mode="r", encoding="utf-8") as f:
        config = json.load(f)["Member_Check"]
    #メンバーリスト取得
    memberlist = pd.read_csv(os.environ["MEMBERLIST"])
    #リアクションをつけているユーザーを取得
    annnounce_CH = await client.fetch_channel(int(os.environ["ANNOUNCE_CH"]))
    message = await annnounce_CH.fetch_message(config["C_Msg_ID"])
    reactions = message.reactions[0]
    users = [user async for user in reactions.users()]

    #リアクション済みのユーザーを記録
    for user in users:
        memberlist.loc[memberlist[memberlist["Discord_ID"] == user.id].index, "MemberCheck"] = 1

    #確認状況ごとに分ける
    still_df = memberlist[memberlist["MemberCheck"] == 0].reset_index()
    ok_df = memberlist[memberlist["MemberCheck"] == 1].reset_index()
    any_df = memberlist[memberlist["MemberCheck"] == 2].reset_index()

    #メッセージを作成
    ok_message = f"✅確認済み：{len(ok_df)}/{len(memberlist)-1}\n" #マスターを除く
    for idx, ok_user in ok_df.iterrows():
        ok_message += f"{idx+1}.{ok_user['User_Name']}\n"

    still_message = f"\n🟥未確認：{len(still_df)}/{len(memberlist)-1}\n" #マスターを除く
    for idx, still_user in still_df.iterrows():
        still_message += f"{idx+1}.{still_user['User_Name']}\n"

    any_message = f"\n🟨任意確認：{len(any_df)}/{len(memberlist)-1}\n" #マスターを除く
    for idx, any_user in any_df.iterrows():
        any_message += f"{idx+1}.{any_user['User_Name']}\n"

    message = f"{now.month}月{now.day}日 在籍確認進捗\n"
    message += ok_message + still_message + any_message

    #マスターのDMオブジェクトを作成
    master = await client.fetch_user(int(os.environ["CREATER_ID"]))
    master_DM = await master.create_dm()

    #送信
    await master_DM.send(message)
    
    #保存
    memberlist.to_csv(os.environ["MEMBERLIST"], index=False)


async def remind(client, now):
    """確認状況を取得してお知らせに送信する"""
    #設定ファイル読み込み
    with open(os.environ["CONFIG"], mode="r", encoding="utf-8") as f:
        config = json.load(f)["Member_Check"]
    #メンバーリスト取得
    memberlist = pd.read_csv(os.environ["MEMBERLIST"])
    #リアクションをつけているユーザーを取得
    annnounce_CH = await client.fetch_channel(int(os.environ["ANNOUNCE_CH"]))
    message = await annnounce_CH.fetch_message(config["C_Msg_ID"])
    reactions = message.reactions[0]
    users = [user async for user in reactions.users()]

    #リアクション済みのユーザーを記録
    for user in users:
        memberlist.loc[memberlist[memberlist["Discord_ID"] == user.id].index, "MemberCheck"] = 1

    #確認状況ごとに分ける
    num_still = len(memberlist[memberlist["MemberCheck"] == 0])
    num_ok = len(memberlist[memberlist["MemberCheck"] == 1])
    num_any = len(memberlist[memberlist["MemberCheck"] == 2])

    #メッセージ作成
    message = config["RemindText"] #リマインドメッセージ
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
    remaindmessage = await annnounce_CH.send(message)
    
    #メッセージidを保存
    save_json(remaindmessage.id, "CR_Msg_ID")


async def finish(client, now):
    """メンバー確認処理終了"""
    #設定ファイル読み込み
    with open(os.environ["CONFIG"], mode="r", encoding="utf-8") as f:
        config = json.load(f)["Member_Check"]
    #メンバーリスト取得
    memberlist = pd.read_csv(os.environ["MEMBERLIST"])

    if len(memberlist[memberlist["MemberCheck"] == 0]) == 0:
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
        next = date(int(next.year), int(next.month), 20)
        message = re.sub("{NEXT_MONTH}", str(next.month), message)
        message = re.sub("{NEXT_WEEKDAY}", weekdays[next.weekday()], message)

        #チャンネル取得
        annnounce_CH = await client.fetch_channel(int(os.environ["ANNOUNCE_CH"]))

        #在籍確認メッセージを削除
        annnounce_CH = await client.fetch_channel(int(os.environ["ANNOUNCE_CH"]))
        cm_names = ["C_Msg_ID", "CL_Msg_ID", "CR_Msg_ID"] #削除メッセージのID名リスト
        for name in cm_names:
            del_message = await annnounce_CH.fetch_message(config[name])
            await del_message.delete() #削除する

        #在籍確認終了送信
        await annnounce_CH.send(message)

        #在籍確認ステータスを初期化
        await reset()
        
        #マスターのDMに終了報告を送信
        master = await client.fetch_user(int(os.environ["CREATER_ID"]))
        master_DM = await master.create_dm()

        #送信
        await master_DM.send("在籍確認が正常に終了しました。お疲れ様でした。")
    else:
        #終わってない場合はマスターにDMを送信
        #マスターのDMオブジェクトを作成
        master = await client.fetch_user(int(os.environ["CREATER_ID"]))
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
    text = re.sub("{WEEKDAY}", time_dict['weekday'], text)
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
        file = json.dump(file, f, indent=4, ensure_ascii=False)
        
        
def get_membernames():
    #メンバーリスト取得
    memberlist = pd.read_csv(os.environ["MEMBERLIST"])
    #ユーザーのディスプレイ名リストを返す
    return [user["User_Name"] for _, user in memberlist.iterrows()]


async def change_checkstate(ctx, user_name):
    """確認ステータスの変更を行う"""
    #メンバーリスト取得
    memberlist = pd.read_csv(os.environ["MEMBERLIST"])
    #現在のステータスを取得
    c_state = int(memberlist[memberlist["User_Name"] == user_name]["MemberCheck"].values)
    #変更するステータス値に更新
    if c_state == 0:
        memberlist.loc[memberlist[memberlist["User_Name"] == user_name].index, "MemberCheck"] = 2
        await ctx.response.send_message(f"{user_name}の在籍確認ステータスを「任意」に変更しました。")
    elif c_state == 2:
        memberlist.loc[memberlist[memberlist["User_Name"] == user_name].index, "MemberCheck"] = 0
        await ctx.response.send_message(f"{user_name}の在籍確認ステータスを「必須」に変更しました。")
    else:
        return await ctx.response.send_message(f"{user_name}は既に確認済みか変更できないユーザーです。")
    
    #保存
    memberlist.to_csv(os.environ["MEMBERLIST"], index=False)
    
    
def show_anymember():
    """免除者の一覧メッセージ作成"""
    #メンバーリスト取得
    memberlist = pd.read_csv(os.environ["MEMBERLIST"])
    any_df = memberlist[memberlist["MemberCheck"] == 2]
    #一覧メッセージ作成
    message = "現在の確認免除者一覧"
    if len(any_df) != 0:
        for _, user in any_df.iterrows():
            message += f"\n・{user['User_Name']}"
    else:
        message += "\n・なし"
        
    return message