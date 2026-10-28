import streamlit as st
import pandas as pd
from datetime import datetime
import gspread

st.set_page_config(page_title="🀄 12人麻將賽事管理系統", page_icon="🀄", layout="wide")

# --- Google 試算表連線設定 ---
@st.cache_resource
def init_connection():
    creds_dict = dict(st.secrets["gcp_service_account"])
    client = gspread.service_account_from_dict(creds_dict)
    spreadsheet = client.open("麻將盃資料庫py")
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

# --- 初始化頁面狀態 ---
if "menu" not in st.session_state:
    st.session_state.menu = "📊 排行榜"

# --- 側邊欄按鈕導航 ---
st.sidebar.header("🎯 功能選單")

menu_items = [
    "📊 排行榜", 
    "📝 登記戰績", 
    "💰 東錢與場地費", 
    "👥 參賽者名單", 
    "📜 歷程比賽紀錄", 
    "🏆 歷屆排名", 
    "📅 賽季月曆", 
    "📖 比賽規則"
]

for item in menu_items:
    # 讓按鈕填滿側邊欄寬度，手機更好按
    # 如果是目前所在的頁面，可以用不同樣式或直接點擊切換
    if st.sidebar.button(item, use_container_width=True):
        st.session_state.menu = item

menu = st.session_state.menu

# 讀取「參賽者名單」Sheet 的 A 欄 (動態增減)
def get_players():
    data = sheet_players.get_all_values()
    if data and len(data) > 1:
        players = [row[0] for row in data[1:] if row and row[0].strip() != ""]
        return players
    return []

players_list = get_players()

# ================= 1. 排行榜 =================
if menu == "📊 排行榜":
    st.header("📊 即時總排行榜")
    st.write("依據「戰績」頁籤自動統計，按累計金額排序，並顯示總將數。")
    
    records = sheet_record.get_all_records()
    
    if records:
        df = pd.DataFrame(records)
        if {"參賽者名字", "金額", "將數"}.issubset(df.columns):
            df["金額"] = pd.to_numeric(df["金額"], errors="coerce").fillna(0)
            df["將數"] = pd.to_numeric(df["將數"], errors="coerce").fillna(0)
            
            summary = df.groupby("參賽者名字")[["金額", "將數"]].sum().reset_index()
            summary.columns = ["選手名稱", "總淨利金額 ($)", "累積將數"]
            summary = summary.sort_values(by="總淨利金額 ($)", ascending=False).reset_index(drop=True)
            
            summary.index = summary.index + 1
            summary.index.name = "名次"
            
            st.dataframe(summary, use_container_width=True)
        else:
            st.warning("「戰績」頁籤的欄位名稱需包含：時間、參賽者名字、金額、將數。")
    else:
        st.info("目前尚無任何戰績資料，快去登記第一場吧！")

# ================= 2. 登記戰績 =================
elif menu == "📝 登記戰績":
    st.header("📝 單將戰績登記")
    st.write("紀錄會直接寫入 Google 試算表的 **「戰績」** 頁籤 (A欄:時間, B欄:參賽者名字, C欄:金額, D欄:將數)")
    
    if not players_list:
        st.warning("目前「參賽者名單」無人，請先至左側點擊【👥 參賽者名單】新增選手！")
    else:
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
                sheet_record.append_row([now_time, winner, win_amount, 1])
                sheet_record.append_row([now_time, loser, lose_amount, 1])
                st.success(f"成功登記！ {winner} 獲得 ${win_amount}，{loser} 扣除 ${abs(lose_amount)}")

# ================= 3. 東錢與場地費 =================
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

# ================= 4. 參賽者名單 =================
elif menu == "👥 參賽者名單":
    st.header("👥 參賽者名單管理")
    st.write("直接讀取與寫入 Google 試算表的 **「參賽者名單」** A 欄。你可以自由新增或刪除選手。")
    
    st.subheader("目前參賽名單：")
    if players_list:
        for idx, p in enumerate(players_list, 1):
            st.write(f"{idx}. {p}")
    else:
        st.info("目前尚無選手。")
        
    st.divider()
    st.subheader("➕ 新增或更新選手")
    
    with st.form("add_player_form"):
        new_player_name = st.text_input("輸入新選手名字")
        add_btn = st.form_submit_button("加入名單")
        
        if add_btn and new_player_name:
            if new_player_name in players_list:
                st.warning("此選手名字已經存在名單中了！")
            else:
                sheet_players.append_row([new_player_name])
                st.success(f"成功新增選手：{new_player_name}")
                st.rerun()
                
    st.divider()
    st.subheader("🗑️ 刪除選手或重設名單")
    with st.form("remove_player_form"):
        target_to_remove = st.selectbox("選擇要刪除的選手", ["請選擇"] + players_list)
        remove_btn = st.form_submit_button("從名單移除")
        
        if remove_btn and target_to_remove != "請選擇":
            all_rows = sheet_players.get_all_values()
            new_rows = [all_rows[0]]
            for row in all_rows[1:]:
                if row and row[0] != target_to_remove:
                    new_rows.append(row)
            
            sheet_players.clear()
            sheet_players.update(new_rows)
            st.success(f"已成功移除選手：{target_to_remove}")
            st.rerun()

# ================= 5. 歷程比賽紀錄 =================
elif menu == "📜 歷程比賽紀錄":
    st.header("📜 詳細歷程比賽紀錄")
    st.write("檢視「戰績」頁籤中的所有原始逐局紀錄。")
    
    records = sheet_record.get_all_records()
    if records:
        st.dataframe(pd.DataFrame(records), use_container_width=True)
    else:
        st.info("目前尚無歷史戰績紀錄。")

# ================= 6. 歷屆排名 =================
elif menu == "🏆 歷屆排名":
    st.header("🏆 歷屆賽事排名")
    st.write("讀取 Google 試算表的 **「歷屆排名」** 頁籤內容。")
    
    history_data = sheet_history.get_all_records()
    if history_data:
        st.dataframe(pd.DataFrame(history_data), use_container_width=True)
    else:
        st.info("目前尚無歷屆排名資料（你可以直接在 Google 試算表的「歷屆排名」頁籤中填入過去的賽果）。")

# ================= 7. 賽季月曆 =================
elif menu == "📅 賽季月曆":
    st.header("📅 賽季月曆與賽程安排")
    st.info("這裡可以公告你們本賽季的開打日期、聚會時間與賽程規劃。")
    st.markdown("""
    * **第一賽季**：2026/03/01 ～ 2026/06/30
    * **固定聚會時間**：每週五晚上 19:00 開打
    * **賽制說明**：採積分累積制，每季結算總淨利前三名。
    """)

# ================= 8. 比賽規則 =================
elif menu == "📖 比賽規則":
    st.header("📖 12人麻將大賽 - 官方比賽規則")
    st.markdown("""
    ### 1. 基本設定
    * **底台規定**：依現場決議（預設底分與台數）。
    * **計分方式**：採用淨利金額制，每將結算。
    
    ### 2. 犯規與罰則
    * **相公 / 詐胡**：該將以放銃或倒扣最大金額計算。
    * **遲到**：超過約定時間 15 分鐘扣點。
    
    ### 3. 賽事積分
    * 每打完一將，務必由當桌人員透過本系統即時登記【贏家】與【輸家/金額】，系統將自動計入總排行榜與累計將數。
    """)
