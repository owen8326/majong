import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="🀄 12人麻將賽事管理系統", page_icon="🀄", layout="wide")

# --- Google 試算表連線設定 ---
@st.cache_resource
def init_connection():
    scope = [
        "https://www.spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    # 從 Streamlit Secrets 讀取憑證
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=scope
    )
    client = gspread.authorize(creds)
    # 請改成你的 Google 試算表檔名
    spreadsheet = client.open("12人麻將大賽紀錄")
    return spreadsheet

try:
    sh = init_connection()
    sheet_record = sh.worksheet("戰績")
    sheet_players = sh.worksheet("參賽者名單")
    sheet_fee = sh.worksheet("東錢場地費紀錄")
    sheet_history = sh.worksheet("歷屆排名")
except Exception as e:
    st.error(f"連線 Google 試算表失敗，請檢查 Secrets 設定或試算表名稱！錯誤訊息：{e}")
    st.stop()

st.title("🀄 12人麻將大賽 - 雲端管理系統")

# --- 側邊欄導航 ---
menu = st.sidebar.selectbox("功能選單", ["📝 登記戰績", "💰 東錢與場地費", "👥 參賽者名單", "📊 總排行榜"])

# 讀取現有參賽者名單
player_data = sheet_players.get_all_records()
if player_data:
    players_list = [p.get("參賽者名字") or p.get("名字") for p in player_data]
    players_list = [p for p in players_list if p] # 過濾空值
else:
    players_list = [f"選手 {i}" for i in range(1, 13)]

# ================= 1. 登記戰績 =================
if menu == "📝 登記戰績":
    st.header("📝 單將戰績登記")
    st.write("紀錄會直接寫入 Google 試算表的 **「戰績」** 頁籤 (A欄:時間, B欄:名字, C欄:金額, D欄:將數)")
    
    with st.form("record_form"):
        col1, col2 = st.columns(2)
        with col1:
            winner = st.selectbox("🏆 贏家 (胡牌)", players_list)
            win_amount = st.number_input("贏得金額 ($)", value=320, step=10)
        with col2:
            loser = st.selectbox("💥 輸家 / 放槍者", [p for p in players_list if p != winner])
            lose_amount = -win_amount
            
        submitted = st.form_submit_button("送出戰績並同步至雲端")
        
        if submitted:
            now_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # 寫入兩筆資料：贏家(+金額, +1將)，輸家(-金額, +1將)
            # A欄:時間, B欄:名字, C欄:金額, D欄:將數
            sheet_record.append_row([now_time, winner, win_amount, 1])
            sheet_record.append_row([now_time, loser, lose_amount, 1])
            st.success(f"成功登記！ {winner} 獲得 ${win_amount}，{loser} 扣除 ${abs(lose_amount)}")

# ================= 2. 東錢場地費紀錄 =================
elif menu == "💰 東錢與場地費":
    st.header("💰 東錢與場地費紀錄")
    st.write("紀錄會寫入 Google 試算表的 **「東錢場地費紀錄」** 頁籤 (A欄:時間, B欄:東錢, C欄:場地費)")
    
    with st.form("fee_form"):
        fee_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        dong_money = st.number_input("東錢金額 ($)", value=100, step=10)
        venue_fee = st.number_input("場地費金額 ($)", value=500, step=50)
        
        fee_submitted = st.form_submit_button("儲存收支紀錄")
        
        if fee_submitted:
            sheet_fee.append_row([fee_time, dong_money, venue_fee])
            st.success("東錢與場地費已成功寫入 Google 試算表！")
            
    st.divider()
    st.subheader("📋 目前所有東錢與場地費明細")
    fee_records = sheet_fee.get_all_records()
    if fee_records:
        st.dataframe(pd.DataFrame(fee_records), use_container_width=True)
    else:
        st.info("目前尚無收支紀錄。")

# ================= 3. 參賽者名單管理 =================
elif menu == "👥 參賽者名單":
    st.header("👥 12人參賽者名單管理")
    st.write("直接同步 Google 試算表的 **「參賽者名單」** 頁籤。")
    
    with st.form("player_form"):
        new_names = []
        st.write("修改或確認 12 位選手名字：")
        for i in range(12):
            default_val = players_list[i] if i < len(players_list) else f"選手 {i+1}"
            n = st.text_input(f"選手 {i+1}", value=default_val, key=f"edit_p_{i}")
            new_names.append([n])
            
        update_p_btn = st.form_submit_button("更新雲端選手名單")
        
        if update_p_btn:
            # 清空並重新寫入名單
            sheet_players.clear()
            sheet_players.append_row(["參賽者名字"])
            for name in new_names:
                sheet_players.append_row(name)
            st.success("參賽者名單已成功更新至 Google 試算表！")
            st.rerun()

# ================= 4. 總排行榜 =================
elif menu == "📊 總排行榜":
    st.header("📊 12 人總排行榜 (依戰績即時計算)")
    
    records = sheet_record.get_all_records()
    
    if records:
        df = pd.DataFrame(records)
        # 預期欄位: 時間, 參賽者名字, 金額, 將數
        if {"參賽者名字", "金額", "將數"}.issubset(df.columns):
            # 依名字群組加總金額與將數
            summary = df.groupby("參賽者名字")[["金額", "將數"]].sum().reset_index()
            summary.columns = ["選手名稱", "總淨利金額 ($)", "累計將數"]
            summary = summary.sort_values(by="總淨利金額 ($)", ascending=False).reset_index(drop=True)
            
            st.dataframe(summary, use_container_width=True)
        else:
            st.warning("「戰績」頁籤的欄位名稱與程式預期不符，請確認是否包含『參賽者名字』、『金額』、『將數』。")
    else:
        st.info("目前還沒有任何對戰紀錄！")
