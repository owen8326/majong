import streamlit as st
import pandas as pd

st.set_page_config(page_title="🀄 12人麻將大賽記分板", page_icon="🀄", layout="wide")

st.title("🀄 12人麻將大賽 - 戰績追蹤系統")

# 初始化 12 人名單與歷史紀錄
if "players" not in st.session_state:
    st.session_state.players = [f"選手 {i}" for i in range(1, 13)]
if "records" not in st.session_state:
    st.session_state.records = []

# 側邊欄：選手管理
st.sidebar.header("👥 選手名單管理 (共12位)")
with st.sidebar.expander("修改選手姓名"):
    new_players = []
    for i in range(12):
        p_name = st.text_input(f"選手 {i+1}", value=st.session_state.players[i], key=f"p_{i}")
        new_players.append(p_name)
    if st.button("更新選手名單"):
        st.session_state.players = new_players
        st.success("選手名單已更新！")

# 主畫面：記錄一將的結果
st.subheader("📝 登記單將比賽結果")
with st.form("mahjong_12_form"):
    col1, col2 = st.columns(2)
    with col1:
        winner = st.selectbox("🏆 贏家 (胡牌)", st.session_state.players)
        win_type = st.radio("胡牌方式", ["自摸", "放槍"])
    with col2:
        loser = None
        if win_type == "放槍":
            loser = st.selectbox("💥 放槍者", [p for p in st.session_state.players if p != winner])
        
        amount = st.number_input("本將贏得總金額 ($)", value=320, step=10)
    
    submitted = st.form_submit_button("記錄這將")
    
    if submitted:
        record = {
            "贏家": winner,
            "方式": win_type,
            "輸家/受害群": loser if win_type == "放槍" else "三家分擔",
            "金額": amount
        }
        st.session_state.records.append(record)
        st.success(f"成功記錄！ {winner} 贏得 {amount} 元")

# 📊 總成績統計（計算 12 人的總將數、總金額）
st.divider()
st.subheader("📊 12 人總排行榜 (金額 / 將數)")

if st.session_state.records:
    # 建立統計表格
    stats = {p: {"總將數": 0, "總金額": 0} for p in st.session_state.players}
    
    for r in st.session_state.records:
        w = r["贏家"]
        amt = r["金額"]
        
        # 贏家增加將數與金額
        if w in stats:
            stats[w]["總將數"] += 1
            stats[w]["總金額"] += amt
            
        # 若是放槍，輸家扣金額、加將數
        if r["方式"] == "放槍":
            l = r["輸家/受害群"]
            if l in stats:
                stats[l]["總將數"] += 1
                stats[l]["總金額"] -= amt
        else:
            # 自摸：其餘參與者扣錢（簡單起見，這裡先將金額平分給另外11人或扣給三家，視規則而定）
            # 這裡用簡易示範：自摸時贏家拿全額，設定其他特定對象或平均扣
            pass

    # 轉換成 DataFrame 顯示
    df_stats = pd.DataFrame.from_dict(stats, orient="index").reset_index()
    df_stats.columns = ["選手名稱", "累計將數", "總淨利金額 ($)"]
    df_stats = df_stats.sort_values(by="總淨利金額 ($)", ascending=False).reset_index(drop=True)
    
    st.dataframe(df_stats, use_container_width=True)
    
    # 顯示詳細歷史紀錄
    with st.expander("🔍 檢視詳細對戰紀錄"):
        st.dataframe(pd.DataFrame(st.session_state.records), use_container_width=True)
else:
    st.info("目前尚無比賽紀錄，快開始登記第一將吧！")
