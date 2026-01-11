import streamlit as st
from google import genai
from google.genai import types
import json
import urllib.parse

# --- 設定 ---
# 本番環境では st.secrets を使用
# ローカルで動かす場合は、.streamlit/secrets.toml を作成するか、
# ここで GOOGLE_API_KEY = "あなたのAPIキー" と書き換えてテストしてください
GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]

# ページ設定
st.set_page_config(
    page_title="DreamRoute | AI留学プランナー",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- URLパラメータから初期値を取得する関数 ---
def get_params():
    params = st.query_params
    return {
        "status": params.get("status", "大学生・大学院生"),
        "mbti": params.get("mbti", "わからない"),
        "period": params.get("period", "半年"),
        "budget": params.get("budget", "100〜200万円"),
        "interest": params.get("interest", ""),
        "preferred_country": params.get("preferred_country", "")
    }

# 初期値をロード
default_values = get_params()

# --- デザイン(CSS)の注入 ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=M+PLUS+Rounded+1c:wght@400;700&display=swap');
    
    /* === ベーススタイル（強制ライトモード） === */
    html, body, [class*="css"] {
        font-family: 'M PLUS Rounded 1c', sans-serif;
        background-color: #f8f9fa !important;
        color: #333333 !important;
    }
    
    /* 不要なヘッダー・フッター削除 */
    header, footer {visibility: hidden;}
    .block-container {
        padding-top: 1rem;
        padding-bottom: 5rem;
    }

    /* === ヒーローセクション === */
    .hero {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 40px 20px;
        border-radius: 15px;
        color: white !important;
        text-align: center;
        margin-bottom: 30px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .hero h1 { font-size: 2.5rem; font-weight: 700; color: white !important; margin: 0; }
    .hero p { color: rgba(255,255,255,0.9) !important; }
    
    /* === カードデザイン === */
    .card {
        background: white; padding: 25px; border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 20px;
        color: #333; transition: transform 0.2s;
    }
    .card-title {
        color: #764ba2; font-size: 1.2rem; font-weight: bold;
        margin-bottom: 15px; display: flex; align-items: center; gap: 10px;
        border-bottom: 2px solid #f0f0f0; padding-bottom: 10px;
    }
    /* カード内の文字色を強制的に黒にする（スマホのダークモード対策） */
    .card h1, .card h2, .card h3, .card h4, .card p, .card li, .card span, .card div {
        color: #333333;
    }
    
    /* === 【重要】入力フォームの視認性改善（スマホダークモード対策） === */
    
    /* 入力ラベル（「予算」などの文字） */
    .stSelectbox label, .stTextInput label {
        color: #333333 !important;
        font-weight: bold;
    }
    
    /* 入力ボックス本体（背景白、文字黒、枠線グレー） */
    div[data-baseweb="select"] > div, 
    div[data-baseweb="input"] > div {
        background-color: #ffffff !important;
        color: #333333 !important;
        border: 1px solid #d1d5db !important;
        border-radius: 8px !important;
    }
    
    /* 入力中の文字色 */
    input[type="text"], div[data-baseweb="select"] span {
        color: #333333 !important;
    }
    
    /* ドロップダウンメニューの中身 */
    ul[data-baseweb="menu"] {
        background-color: #ffffff !important;
    }
    li[data-baseweb="option"] {
        color: #333333 !important;
    }
    /* ========================================================== */

    /* ボタンスタイル */
    .stButton>button {
        width: 100%;
        background: linear-gradient(90deg, #ff758c 0%, #ff7eb3 100%);
        border: none; padding: 15px; border-radius: 30px;
        color: white !important;
        font-weight: bold; font-size: 1.1rem;
        box-shadow: 0 4px 15px rgba(255, 118, 136, 0.4);
    }
    
    .tag {
        display: inline-block; background: #eef2ff; color: #667eea !important;
        padding: 4px 12px; border-radius: 20px; font-size: 0.85rem; font-weight: bold; margin-right: 5px;
    }
    
    .cost-table { width: 100%; border-collapse: collapse; margin-top: 10px; }
    .cost-table th, .cost-table td { border-bottom: 1px solid #eee; padding: 8px; text-align:


