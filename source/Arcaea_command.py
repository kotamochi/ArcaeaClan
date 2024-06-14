import os
import json
import math
import dotenv
import random
import asyncio
import discord
import pandas as pd
from datetime import datetime, timedelta
import ui

#.envファイルの読み込み
dotenv.load_dotenv()

async def Random_Select_Level(level1=None, level2=None, dif=None, level_list=None):
    """ランダム選曲機能"""

    #ランダム選曲時
    if level_list == None:
        #レベル指定があるか
        if level1 == None and level2 == None:
            level1, level2 = "0", "12" #全曲指定にする
        elif level1 != None and level2 == None:
            level2 = level1            #単一の難易度のみにする

        #＋難易度が指定された時は.7表記に変更する
        try:
            #引数を数値型に変換
            level1 = float(level1)
        except ValueError:
            #引数を数値型に変換
            if level1[-1] == "+":
                level1 = float(level1[:-1]) + 0.7

        try:
            #引数を数値型に変換
            level2 = float(level2)
        except ValueError:
            #引数を数値型に変換
            if level2[-1] == "+":
                level2 = float(level2[:-1]) + 0.7

        #楽曲情報をデータフレームに読み込む
        df_music = pd.read_csv(os.environ["MUSIC"])

        async def get_music(dif_name):
            """指定難易度の楽曲データを取得"""
            df = df_music[df_music[dif_name] >= level1].copy()
            df = df[df[dif_name] <= level2]

            return df

        #指定された難易度の曲を取得
        if dif == "FTR" or dif == "ftr":
            df_range_music = await get_music("FTR_Level")
        elif dif == "ETR" or dif == "etr":
            df_range_music = await get_music("ETR_Level")
        elif dif =="BYD" or dif == "byd":
            df_range_music = await get_music("BYD_Level")
        else:
            #指定がなければ全部
            df_music_FTR = await get_music("FTR_Level")
            df_music_ETR = await get_music("ETR_Level")
            df_music_BYD = await get_music("BYD_Level")
            #曲データを結合
            df_range_music = pd.concat([df_music_FTR, df_music_ETR, df_music_BYD])

    #対戦時
    else:
        #楽曲情報をデータフレームに読み込む
        df_music = pd.read_csv(os.environ["MUSIC"])

        async def get_music_b(dif_name):
            """指定難易度の楽曲データを取得(対戦用)"""
            count = 0
            for lv in level_list:  
                df = df_music[df_music[f"{dif_name}_Level"] == lv].copy()
                if count == 0:
                    music_df = df
                    count += 1
                else:
                    music_df = pd.concat([music_df, df])

            return music_df

        #選択された難易度
        count = 0
        for i in dif:
            df = await get_music_b(i)
            if count == 0:
                df_range_music = df
                count += 1
            else:
                df_range_music = pd.concat([df_range_music, df])

    ##ここから共通
    #乱数の範囲を取得
    music_num = len(df_range_music)

    #乱数を作成
    rand = random.randint(0,music_num-1)

    #乱数から選ばれた楽曲を抽出
    hit_music = df_range_music.iloc[rand]

    #結果を保存
    title = hit_music["Music_Title"] #曲名

    #難易度帯を検索して取得
    if pd.isnull(hit_music["BYD_Level"]) == True and pd.isnull(hit_music["ETR_Level"]) == True:
        level = hit_music["FTR_Level"]
        deffecult = "FTR" #難易度を表示
    elif pd.isnull(hit_music["BYD_Level"]) == True:
        level = hit_music["ETR_Level"]
        deffecult = "ETR" #難易度を表示
    else:
        level = hit_music["BYD_Level"]
        deffecult = "BYD" #難易度を表示

    #楽曲レベルを表示用に調整
    if level % 1 != 0.0:
        level_str = str(math.floor(level)) + "+"
    else:
        level_str = str(math.floor(level))

    #画像データを取得
    image = hit_music["Image"]

    return title, level_str, deffecult, image


async def match_host(ctx, user, kind):
    """対戦のホストを立てる"""
    #メンバーリストを取得
    MemberList = pd.read_csv(os.environ["MEMBERLIST"])
    #登録済みか確認
    if MemberList["Discord_ID"].isin([user]).any().any():
        #登録済みなら無視
        pass
    else:
        #登録されてないことを通知して終了
        return await ctx.response.send_message("メンバー登録が行われていません。\n先に /sign_up でメンバー登録を行ってください", ephemeral=True)
    
    #対戦中、対戦待機中でないか確認
    check = await state_check(user)
    if check:
        #参加できない状態を通知して終了
        return await ctx.response.send_message(f"あなたは対戦中、もしくは対戦ホスト中です。", ephemeral=True)
        
    #対戦形式を読み込み
    with open(os.environ["VS_DICT"], mode="r") as f:
        vs_dict = json.load(f)
    #対戦募集ボタンを表示
    await ctx.response.defer()
    view = ui.VSHostButton(user, kind, timeout=120) #2分で募集を削除
    msg = await ctx.followup.send(f"{ctx.user.mention}:Create {vs_dict[kind]} Room", view=view)
    await view.msg_send(msg) #メッセージを渡す
    #対戦フラグをDataFrameに登録
    await state_chenge(user, True)


async def state_check(user):
    """対戦ステータスを確認する"""
    #メンバーリスト取得
    MemberList = pd.read_csv(os.environ["MEMBERLIST"])
    #ユーザーデータ取得
    user_state = MemberList[MemberList["Discord_ID"] == user].copy()
    #ステータス取得
    if user_state["State"].item():
        return True #対戦中
    else:
        return False #未対戦
        

async def state_chenge(user:int, state:bool):
    """対戦ステータスの変更"""
    #メンバーリスト取得
    MemberList = pd.read_csv(os.environ["MEMBERLIST"])
    #ステータス変更
    MemberList.loc[MemberList[MemberList["Discord_ID"] == user].index, "State"] = state
    #保存
    MemberList.to_csv(os.environ["MEMBERLIST"], index=False)


async def Arcaea_ScoreBattle(ctx, host_id, guest_id, battle_type):
    """スコアバトルを行う関数"""
    ##対戦を始める
    #ゲスト側の対戦ステータスを変更
    await state_chenge(guest_id, True)
    #idからユーザーを取得
    host_user = ctx.client.get_user(host_id)
    guest_user = ctx.client.get_user(guest_id)
    
    #対戦形式名を作成
    EX_flg = int(battle_type)
    if EX_flg == 1:
        vs_format = "EXScoreBattle"
    else:
        vs_format = "ScoreBattle"

    #対戦スレッドを作成
    thread = await ctx.channel.create_thread(name="{} vs {}：{}".format(host_user.display_name, guest_user.display_name, vs_format),type=discord.ChannelType.public_thread)

    #スレッド内でのエラーをキャッチ
    try:
        #リンクプレイコードのチェック関数
        def checkLinkID(m):
            try:
                #英語4文字数字2文字であるか
                ms = m.content
                if len(ms) == 6:
                    str(ms[0:4])
                    int(ms[4:6])
                    return True
            except Exception:
                return False

        #メッセージとボタンを作成
        an = f"Channel：{thread.mention} \n {host_user.display_name} vs {guest_user.display_name}" #対戦CH用
        ms = f"Channel：{host_user.mention} vs {guest_user.mention} \n (途中終了する時はお互いに「終了」を押してね)" #スレッド用
        b_stop = ui.VSStopbutton(host_user.id, guest_user.id, timeout=None)

        #メッセージを送信して難易度選択を待機
        await ctx.response.send_message(an)
        await thread.send(ms, view=b_stop) #終了ボタン送信
        await thread.send(f"{host_user.mention}:Link Playのルームを作成して、ルームコードを入力してね")
        
        #メッセージを受け取ったスレッドに対してのみ返す
        while True:
            #リンクコードを待機
            msg = await ctx.client.wait_for('message', check=checkLinkID, timeout=600)
            #同一スレッドかつホストの入力であるか確認
            if thread.id == msg.channel.id and host_user.id == msg.author.id:
                break
            else:
                pass

        await asyncio.sleep(0.5) #インターバル

        #課題曲難易度選択のボタンを送信
        view = ui.VSMusicDifChoice(thread, host_user.id, guest_user.id, EX_flg, timeout=600)
        await thread.send("難易度を選択してね!お互いがOKを押したら次に進むよ",view=view)

    #スレッド内でトラブルが起こったらスレッドを閉じる
    except Exception:
        await asyncio.sleep(1) #間を空ける
        await thread.send("タイムアウトより対戦が終了されたよ。チャンネルを削除するね")
        await asyncio.sleep(3) #スレッド削除まで待機
        await thread.delete()
        #対戦ステータスを変更
        await state_chenge(host_user.id, False)
        await state_chenge(guest_user.id, False)
        

async def s_sb_selectlevel(ctx, host_user_id, guest_user_id, dif_ls, EX_flg):
    """レベル選択ボタンを表示"""
    #レベル選択ボタンを送信
    view = ui.VSMusicLevelChoice(ctx.channel, host_user_id, guest_user_id, dif_ls, EX_flg, timeout=600)
    await ctx.followup.send("レベルを選択してね!お互いがOKを押したら次に進むよ",view=view)


async def s_sb_musicselect(ctx, host_user_id, guest_user_id, dif_ls, level_ls, EX_flg, Score_Count=None):
    """楽曲表示と決定処理"""
    #選曲を行う
    music, level_str, dif, image = await Random_Select_Level(dif=dif_ls, level_list=level_ls)

    #対戦開始前のメッセージを作成
    musicmsg = f"対戦曲:[{music}] {dif}:{level_str}!!"
    music = f"{music} {dif} {level_str}"
    #課題曲を表示
    view = ui.VSMusicButton(ctx.channel, host_user_id, guest_user_id, dif_ls, level_ls, music, EX_flg, Score_Count, timeout=600)
    await ctx.channel.send(musicmsg, file=discord.File(image), view=view)
    await ctx.channel.send("お互いが選択したらゲームスタート!!")
    

async def s_sb_battle(ctx, host_user_id, guest_user_id, dif_ls, level_ls, music, EX_flg, Score_Count=None):
    """スコア受け取りから終了まで"""
    try:
        #初回の場合はインスタンス作成
        if Score_Count != None:
            pass
        else:
            Score_Count = ScoreManage()

        #チャンネル属性を取得
        channel = ctx.channel
        #ユーザー属性を取得
        host_user =  ctx.client.get_user(host_user_id)
        guest_user =  ctx.client.get_user(guest_user_id)

        ##スコア入力処理
        #一人目
        result1 = await s_sb_score_check(ctx=ctx, channel=channel, score_user=host_user, wait_user=guest_user, EX_flg=EX_flg)
        if result1 is None:
            #タイムアウト処理が行われたので終了
            return

        result2 = await s_sb_score_check(ctx=ctx, channel=channel, score_user=guest_user, wait_user=host_user, EX_flg=EX_flg)
        if result2 is None:
            #タイムアウト処理が行われたので終了
            return

        await asyncio.sleep(1) #インターバル

        #スコアをlistに保存
        Score_Count.score1.append(result1.content)
        Score_Count.score2.append(result2.content)

        #曲数を数える
        Score_Count.count += 1

        #対戦曲をレコード用に取得
        Score_Count.music_ls.append(music)

        #最終曲になったらループを抜ける
        if Score_Count.count == 2:
            #2曲終わったら終了処理へ
            await channel.send(f"対戦終了～～！！ 対戦結果は～～？")
            await asyncio.sleep(3)

            #スコア計算、結果表示へ
            await s_sb_result(ctx, channel, host_user, guest_user, Score_Count.score1, Score_Count.score2, Score_Count.music_ls, EX_flg)
        else:
            #次の曲へ移行
            await channel.send(f"{Score_Count.count}曲目おつかれさま！！ {Score_Count.count+1}曲目はなにがでるかな～")
            await asyncio.sleep(3)
            #楽曲抽選に移行
            await s_sb_musicselect(ctx, host_user_id, guest_user_id, dif_ls, level_ls, EX_flg, Score_Count)

    #スレッド内でトラブルが起こったらスレッドを閉じる
    except Exception as e:
        print(e)
        await asyncio.sleep(1) #間を空ける
        await channel.send("タイムアウトより対戦が終了されたよ。チャンネルを削除するね")
        await asyncio.sleep(3) #スレッド削除まで待機
        await channel.delete()
        #対戦ステータスを変更
        await state_chenge(host_user.id, False)
        await state_chenge(guest_user.id, False)


class ScoreManage():
    """対戦のスコアを一時保存するためのクラス"""
    def __init__(self):
        self.score1 = []
        self.score2 = []
        self.music_ls = []
        self.count = 0
        
        
async def s_sb_score_check(ctx, channel, score_user, wait_user, EX_flg):
    """スコア入力受け取りと確認"""
    #スコア受け取り監視関数を定義
    def check(m):
        """通常スコア用チェック関数"""
        try:
            ms = m.content.split(' ')
            if len(ms) == 1:
                for i in ms:
                    int(i)
                return True
        except Exception:
            return False

    def checkEX(m):
        """EXスコア用チェック関数"""
        try:
            ms = m.content.split(' ')
            if len(ms) == 4:
                for i in ms:
                    int(i)
                return True
        except Exception:
            return False
    
    if EX_flg == False:
        #通常スコア
        await channel.send(f"{score_user.mention}さんのスコアを入力してください。")
        result = await ctx.client.wait_for('message', check=check, timeout=600) #スコア入力を受け付ける
    else:
        #EXスコア
        await channel.send(f"{score_user.mention}さんのスコアを入力してください。\n例:1430 1387 15 5(Pure,内部Pure,Far,Lost)")
        result = await ctx.client.wait_for('message', check=checkEX, timeout=600) #スコア入力を受け付ける
        
    #メッセージを受け取ったスレッドであるか、メンションされたユーザーからであるかを確認
    if channel.id == result.channel.id and score_user.id == result.author.id:
        #スコア確認ボタンを表示
        view = ui.VSScoreCheck(score_user.id)
        if EX_flg == False:
            #通常スコア
            await channel.send(f"入力スコア「{int(result.content):,}」でOKかな？", view=view)
        else:
            #EXスコア
            ex_result = result.content.split(" ")
            await channel.send(f"入力スコア「Pure:{int(ex_result[0]):,}, 内部Pure:{int(ex_result[1]):,}, Far:{int(ex_result[2]):,}, Lost{int(ex_result[3]):,}」でOKかな？", view=view)
        
        #タイムアウト用処理
        stasrt_time = datetime.now()
        timeout = stasrt_time + timedelta(minutes=10)
        while True:
            #時刻を取得
            nowtime = datetime.now()
            #次に進む
            if view.check_flg is not None:
                break
            #終了する
            elif nowtime >= timeout:
                try:
                    #チャンネルを削除
                    await ctx.channel.delete()
                    #対戦ステータスを変更
                    await state_chenge(score_user.id, False)
                    await state_chenge(wait_user.id, False)
                    return #終わる
                except discord.HTTPException:
                    return #終わる
            else:
                await asyncio.sleep(1)

        if view.check_flg:
            #二人目に進む
            return result
        else:
            #入力し直しを行う
            return await s_sb_score_check(ctx, channel, score_user, wait_user, EX_flg)
    else:
        #他ユーザーからの反応は無視して再度入力を待つ
        return await s_sb_score_check(ctx, channel, score_user, wait_user, EX_flg)


async def s_sb_result(ctx, channel, host_user, guest_user, score1, score2, music_ls, EX_flg):
        """対戦結果を作成して送信"""
        #対戦方式によってスコア計算を分岐
        if EX_flg == False:
            #通常スコア
            winner, loser, player1_score, player2_score = await Score_Battle(score1, score2, host_user, guest_user)
        else:
            #EXスコア対決
            winner, loser, player1_score, player2_score, Drow_Flg = await EX_Score_Battle(score1, score2, host_user, guest_user)

        #表示名を取得
        host_name = host_user.display_name
        guest_name = guest_user.display_name

        #勝敗をスレッドに表示
        if EX_flg == False:
            #通常スコア
            vs_format = "ScoreBattle"
            if player1_score == player2_score:
                #引き分けの時
                await channel.send(f"結果は両者 {player1_score:,} で引き分け!! 白熱した戦いだったね!")
                Drow_Flg = True
                #表示用リザルトを作成
                result = f"[{vs_format}]\n"\
                         f"・1曲目 {music_ls[0]}\n{host_name}：{int(score1[0]):,}\n{guest_name}：{int(score2[0]):,}\n"\
                         f"・2曲目 {music_ls[1]}\n{host_name}：{int(score1[1]):,}\n{guest_name}：{int(score2[1]):,}\n"\
                         f"・Total\n{host_name}：{player1_score:,}\n{guest_name}：{player2_score:,}\n\n"\
                         f"Drow：{winner.display_name} {loser.display_name}!!"

            else:
                #勝敗が決まった時
                await channel.send(f"{host_name}: {player1_score:,}\n{guest_name}: {player2_score:,}\n\n勝者は{winner.mention}さん!!おめでとう!!🎉🎉")
                Drow_Flg = False
                #表示用リザルトを作成
                result = f"[{vs_format}]\n"\
                         f"・1曲目 {music_ls[0]}\n{host_name}：{int(score1[0]):,}\n{guest_name}：{int(score2[0]):,}\n"\
                         f"・2曲目 {music_ls[1]}\n{host_name}：{int(score1[1]):,}\n{guest_name}：{int(score2[1]):,}\n"\
                         f"・Total\n{host_name}：{player1_score:,}\n{guest_name}：{player2_score:,}\n\n"\
                         f"Winner：{winner.display_name}!!"
                         
        else:
            #EXスコア
            vs_format = "EXScoreBattle"
            if sum(player1_score) == sum(player2_score):
                #引き分けの時
                await channel.send(f"結果は両者 {sum(player1_score):,} で引き分け!! 白熱した戦いだったね!")
                Drow_Flg = True
                #表示用リザルトを作成
                result = f"[{vs_format}]\n"\
                         f"・1曲目 {music_ls[0]}\n{host_name}：{int(player1_score[0]):,}\n{guest_name}：{int(player2_score[0]):,}\n"\
                         f"・2曲目 {music_ls[1]}\n{host_name}：{int(player1_score[1]):,}\n{guest_name}：{int(player2_score[1]):,}\n"\
                         f"・Total\n{host_name}：{sum(player1_score):,}\n{guest_name}：{sum(player2_score):,}\n\n"\
                         f"{winner.display_name}さんvs{loser.display_name}さんは引き分けでした!!!"

            else:
                #勝敗が決まった時
                await channel.send(f"{host_name}: {sum(player1_score):,}\n{guest_name}: {sum(player2_score):,}\n\n勝者は{winner.mention}さん!!おめでとう!!🎉🎉")
                Drow_Flg = False
                #表示用リザルトを作成
                result = f"[{vs_format}]\n"\
                         f"・1曲目 {music_ls[0]}\n{host_name}：{int(player1_score[0]):,}\n{guest_name}：{int(player2_score[0]):,}\n"\
                         f"・2曲目 {music_ls[1]}\n{host_name}：{int(player1_score[1]):,}\n{guest_name}：{int(player2_score[1]):,}\n"\
                         f"・Total\n{host_name}：{sum(player1_score):,}\n{guest_name}：{sum(player2_score):,}\n\n"\
                         f"勝者は{winner.display_name}さんでした!!!"


        ##csvファイルに結果を保存
        #ファイルパスを取得
        if EX_flg == False:
            #通常スコア
            log_path = os.environ["SCORE_LOG"]
        else:
            #EXスコア
            log_path = os.environ["EXSCORE_LOG"]

        df_log = pd.read_csv(log_path) #ファイルを取得
        now_data = [[winner.id, loser.id, Drow_Flg]] #ファイル用の結果を作成
        df_now = pd.DataFrame(now_data, columns=["Winner", "Loser", "Drow_Flg"]) #データ作成
        df_log = pd.concat([df_log, df_now]) #作ったデータを既存データに追加
        df_log.to_csv(log_path, index=False) #保存

        #結果を対戦CHに表示
        result_ch = await ctx.client.fetch_channel(int(os.environ["BATTLE_CH"])) #対戦CHオブジェクトを取得
        await result_ch.send(result) #送信

        #対戦ステータスを変更
        await state_chenge(host_user.id, False)
        await state_chenge(guest_user.id, False)

        #30秒後スレッドを閉じる
        await asyncio.sleep(1) #間を空ける
        await channel.send(f"このチャンネルは1分後に自動で削除されるよ\nおつかれさま～～!またね!!")
        await asyncio.sleep(60) #スレッド削除まで待機
        await channel.delete() #スレッドを削除


#スコア対決の計算
async def Score_Battle(user1, user2, name1, name2):
    """スコアを計算する"""
    #変数定義
    user1_score = 0
    user2_score = 0

    #一曲ずつ計算
    for score1, score2 in zip(user1, user2):

        user1_score += int(score1)
        user2_score += int(score2)

    #勝敗の判定
    if user1_score > user2_score:    #user1の勝利
        return name1, name2, user1_score, user2_score
    elif user1_score == user2_score: #引き分け
        return name1, name2, user1_score, user2_score
    else:                            #user2の勝利
        return name2, name1, user1_score, user2_score


#EXスコア対決の計算
async def EX_Score_Battle(user1, user2, name1, name2):
    """EXスコアを計算する"""
    #変数定義
    user1_score = 0
    user2_score = 0
    total_P_pure1 = 0
    total_P_pure2 = 0
    user1_score_ls = []
    user2_score_ls = []

    #一曲ずつ計算
    for score1, score2 in zip(user1, user2):
        #EXスコアを計算(無印Pure:3点,Pure:2点,Far:1点,Lost:0点)
        #1Pプレイヤーのスコアを計算
        pure1, P_pure1, far1, lost1 = score1.split(' ') #内訳ごとに分ける
        F_pure1 = int(pure1) - int(P_pure1) #内部の出たPure数を計算
        user1_score += int(P_pure1)*3 + int(F_pure1)*2 + int(far1)*1 #EXスコアを計算
        total_P_pure1 += int(P_pure1)
        user1_score_ls.append(int(P_pure1)*3 + int(F_pure1)*2 + int(far1)*1) #曲ごとのEXスコアを入れる

        #2Pプレイヤーのスコアを計算
        pure2, P_pure2, far2, lost2 = score2.split(' ') #内訳ごとに分ける
        F_pure2 = int(pure2) - int(P_pure2) #内部の出たPure数を計算
        user2_score += int(P_pure2)*3 + int(F_pure2)*2 + int(far2)*1 #EXスコアを計算
        total_P_pure2 += int(P_pure1)
        user2_score_ls.append(int(P_pure2)*3 + int(F_pure2)*2 + int(far2)*1) #曲ごとのEXスコアを入れる

    #勝敗の判定
    if user1_score > user2_score:   #user1の勝利
        Drow_Flg = False
        return name1, name2, user1_score_ls, user2_score_ls, Drow_Flg
    elif user1_score < user2_score: #user2の勝利
        Drow_Flg = False
        return name2, name1, user1_score_ls, user2_score_ls, Drow_Flg
    else:                           #EXスコアが引き分けのときは内部精度で判定する
        if total_P_pure1 > total_P_pure2:   #user1の勝利
            Drow_Flg = False
            return name1, name2, user1_score_ls, user2_score_ls, Drow_Flg
        elif total_P_pure1 < total_P_pure2: #user2の勝利
            Drow_Flg = False
            return name2, name1, user1_score_ls, user2_score_ls, Drow_Flg
        else:                               #それでも決まらない場合は引き分け
            Drow_Flg = True
            return name1, name2, user1_score_ls, user2_score_ls, Drow_Flg


#戦績を確認
async def User_Status(ctx, user, file_path):
    #データを読み込んで加工しやすいように前処理
    BattleLog = pd.read_csv(file_path)
    #idをint型に変換
    BattleLog["Winner"] = BattleLog["Winner"].astype("Int64")
    BattleLog["Loser"] = BattleLog["Loser"].astype("Int64")
    #自身の戦績を取得
    wins = BattleLog[BattleLog["Winner"] == user] #勝利
    loses = BattleLog[BattleLog["Loser"] == user] #敗北
    userdata = pd.concat([wins, loses]) #自身の戦績データ

    #引き分け行に前処理を行う
    idx = 0
    for recode in userdata.itertuples():
        if recode.Drow_Flg == True:
            if recode.Winner == user:
                pass
            else:
                #引き分けかつwinnerに名前が入っていない場合は集計の為に結果を入れ替える
                userdata.loc[idx, "Loser"] == userdata.loc[idx, "Winner"]
                userdata.loc[idx, "Winner"] == user

    #重複行を纏める
    margedata = userdata.drop_duplicates()
    #結果を保存するデータフレームを作成
    result = pd.DataFrame(columns=["User"])

    #対戦した相手一覧を作成
    for _, recode in margedata.iterrows():
        if recode["Winner"] == user: #勝ってたとき
            if (result["User"] == recode["Loser"]).any():
                pass
            else:
                new_user = pd.DataFrame({"User":[recode["Loser"]]})
                result = pd.concat([result, new_user])
        elif recode.Loser == user: #負けてたとき
            if (result["User"] == recode["Winner"]).any():
                pass
            else:
                new_user = pd.DataFrame({"User":[recode["Winner"]]})
                result = pd.concat([result, new_user])

    #勝敗結果を記録するために列を追加、インデックスを追加
    result = result.assign(Win=0, Lose=0, Drow=0)
    result.index = range(len(result))

    #戦績データを処理し、結果を作成
    for _, recode in userdata.iterrows():
        if recode["Winner"] == user and recode["Drow_Flg"] == False: #入力者が勝者の場合
            idx = result.index[result["User"] == recode["Loser"]]
            result.loc[idx, "Win"] += 1 
        elif recode["Loser"] == user and recode["Drow_Flg"] == False: #入力者が敗者の場合
            idx = result.index[result["User"] == recode["Winner"]]
            result.loc[idx,"Lose"] += 1
        elif recode["Drow_Flg"] == True:
            if recode["Winner"] == user:
                idx = result.index[result["User"] == recode["Loser"]]
                result.loc[idx,"Drow"] += 1
            elif recode["Loser"] == user:
                idx = result.index[result["User"] == recode["Winner"]]
                result.loc[idx,"Drow"] += 1

    #idから表示名に変更する
    for idx, recode in result.iterrows():
        result.loc[idx, "User"] = (await ctx.client.fetch_user(recode["User"])).display_name

    #集計が終了したデータを勝利→引き分け→敗北にソートして返す
    return result.sort_values(by=["Win", "Drow", "Lose"])


#作りかけの機能
#async def task_create():
#    """今週の課題曲を指定"""
#    music, level_str, dif = Random_Select_Level("9")
#
#    msg = f"「{music}」{dif}:{level_str}" 
#    #メッセージを作成
#    embed = discord.Embed(title="今週の課題曲",description=msg)
#    embed.add_field(name="今週の課題曲", value=msg, inline=False)