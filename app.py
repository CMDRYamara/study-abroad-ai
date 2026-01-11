import streamlit as st
from google import genai
from google.genai import types
import json
import os

# --- 設定 ---
# ※ここにAPIキーを貼り直してください
# 本番環境(Streamlit Cloud)では st.secrets を使い、ローカルでは直接記述などの使い分け推奨
# GOOGLE_API_KEY = "ここにAPIキー" 
GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]

# ページ設定
st.set_page_config(
    page_title="DreamRoute | AI留学プランナー",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- デザイン(CSS)の注入 ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=M+PLUS+Rounded+1c:wght@400;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'M PLUS Rounded 1c', sans-serif;
        background-color: #f8f9fa;
    }
    .block-container {
        padding-top: 1rem;
        padding-bottom: 5rem;
    }
    header, footer {visibility: hidden;}

    /* ヒーローセクション */
    .hero {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 40px 20px;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin-bottom: 30px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .hero h1 { font-size: 2.2rem; margin-bottom: 10px; font-weight: 700; color: white; }

    /* カードデザイン */
    .card {
        background: white;
        padding: 25px;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        margin-bottom: 20px;
        transition: transform 0.2s;
        color: #333333;
    }
    
    .card:hover { transform: translateY(-2px); }
    .card-title {
        color: #764ba2; font-size: 1.1rem; font-weight: bold;
        margin-bottom: 10px; display: flex; align-items: center; gap: 10px;
    }
    
    .card h1, .card h2, .card h3, .card h4, .card h5, .card h6, .card p, .card li {
        color: #333333; 
    }

    /* ボタン */
    .stButton>button {
        width: 100%;
        background: linear-gradient(90deg, #ff758c 0%, #ff7eb3 100%);
        border: none; color: white; font-weight: bold; padding: 15px;
        border-radius: 30px; font-size: 1.1rem; transition: 0.3s;
        box-shadow: 0 4px 15px rgba(255, 118, 136, 0.4);
    }
    .stButton>button:hover { opacity: 0.9; transform: scale(1.02); }

    .tag {
        display: inline-block; background: #eef2ff; color: #667eea;
        padding: 4px 12px; border-radius: 20px; font-size: 0.85rem; font-weight: bold; margin-right: 5px;
    }
    </style>
""", unsafe_allow_html=True)

# --- AIロジック (新しい google.genai を使用) ---
def get_study_plan_json(status, mbti, budget, period, interest, preferred_country):
    # APIキーのチェック
    if not GOOGLE_API_KEY:
        st.error("APIキーが設定されていません。")
        return None

    client = genai.Client(api_key=GOOGLE_API_KEY)
    
    # 任意の国指定がある場合の処理
    country_instruction = f"ユーザーの希望により、必ず「{preferred_country}」でのプランを作成してください。" if preferred_country else "ユーザーの条件に最も適した国・都市をAIが選定して提案してください。"

    prompt = f"""
    あなたはZ世代に特化した留学コンサルタントAIです。
    以下のユーザー属性と条件に基づき、最適な留学プランを作成してください。

    【ユーザー条件】
    ・現在の立場: {status}
    ・MBTI: {mbti}
    ・予算: {budget}
    ・期間: {period}
    ・興味: {interest}
    ・国指定: {preferred_country if preferred_country else "なし（AIにお任せ）"}

    【考慮すべきポイント】
    1. **立場の考慮**:
       - ユーザーは「{status}」です。この属性に合わせたプランにすること。
       - 中高生の場合：治安重視、ホームステイ、現地の高校体験や語学学校、サポート体制への言及。
       - 大学生の場合：インターン、ワーホリ、大学の単位認定、キャリア形成、現地の若者との交流。
    2. **国の選定**: {country_instruction}

    【出力形式】
    以下のJSONスキーマに従って出力してください。
    {{
        "catchphrase": "ユーザーの心を掴む短いキャッチコピー（20文字以内）",
        "country": "提案する国と都市名",
        "country_emoji": "その国の国旗絵文字",
        "reason_title": "なぜおすすめかの一言タイトル",
        "reason_desc": "MBTIと今の立場（{status}）に基づいたおすすめ理由（150文字程度）",
        "todo_list": ["現地でやるべきこと1", "現地でやるべきこと2", "現地でやるべきこと3"],
        "budget_hack": "予算内で収めるための具体的な裏技アドバイス",
        "roadmap": "留学までの大まかな流れ（ビザ→準備→渡航など簡潔に）",
        "mentor_promo": "先輩に相談することのメリットを一言で"
    }}
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type='application/json' 
            )
        )
        return json.loads(response.text)
    except Exception as e:
        st.error(f"エラーが発生しました: {e}")
        return None

# --- UI構築 ---

# ヒーローセクション
st.markdown("""
    <div class="hero">
        <h1>DreamRoute ✈️</h1>
        <p>AIと先輩がサポートする、<br>エージェントを使わない「新しい留学」</p>
    </div>
""", unsafe_allow_html=True)

# 入力フォーム
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown('<div class="card-title">🔍 あなたの希望を教えてください</div>', unsafe_allow_html=True)

# 3カラムにして情報を整理
col1, col2, col3 = st.columns(3)

with col1:
    # 追加: 現在の立場
    status = st.selectbox("現在の立場", ["大学生・大学院生", "高校生", "中学生", "社会人", "その他"])
    mbti = st.selectbox("MBTIタイプ", ["わからない", "INTJ", "INTP", "ENTJ", "ENTP", "INFJ", "INFP", "ENFJ", "ENFP", "ISTJ", "ISFJ", "ESTJ", "ESFJ", "ISTP", "ISFP", "ESTP", "ESFP"])

with col2:
    period = st.selectbox("期間", ["短期（1-2週間）", "1-3ヶ月", "半年", "1年", "2年以上"])
    budget = st.selectbox("予算", ["50万円以下", "50-100万円", "100-200万円", "潤沢"])

with col3:
    interest = st.text_input("興味のあること", placeholder="例：カフェ, K-POP, IT")
    # 追加: 任意の国指定
    preferred_country = st.text_input("行きたい国（決まっていれば）", placeholder="例：カナダ（空欄でAI提案）")

st.markdown('</div>', unsafe_allow_html=True)

# アクション
if st.button("✨ ベストなプランを生成する"):
    if not interest:
        st.error("AIがプランを考えるために、「興味のあること」だけは教えてください！")
    else:
        with st.spinner("AIが世界中のルートを検索中..."):
            # 引数に status と preferred_country を追加
            data = get_study_plan_json(status, mbti, budget, period, interest, preferred_country)
            
            if data:
                # 結果表示
                st.markdown(f"""
                <div style="text-align:center; margin: 30px 0;">
                    <h2 style="color:#764ba2; margin-bottom:0;">{data['catchphrase']}</h2>
                </div>
                """, unsafe_allow_html=True)

                st.markdown(f"""
                <div class="card" style="border-top: 5px solid #ff758c;">
                    <h2 style="font-size:1.8rem;">{data.get('country_emoji', '✈️')} {data['country']}</h2>
                    <p style="color:#666; font-weight:bold;">{data['reason_title']}</p>
                    <p>{data['reason_desc']}</p>
                    <div style="margin-top:15px;">
                        <span class="tag">#{status}プラン</span>
                        <span class="tag">#MBTIマッチ度高</span>
                        <span class="tag">#{interest}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                col_res1, col_res2 = st.columns(2)
                
                with col_res1:
                    todos = data.get('todo_list', [])
                    todos_html = "".join([f"<li>{item}</li>" for item in todos])
                    st.markdown(f"""
                    <div class="card" style="height: 100%;">
                        <div class="card-title">📌 {data['country']}でのミッション</div>
                        <ul style="padding-left:20px; line-height:1.6;">{todos_html}</ul>
                    </div>
                    """, unsafe_allow_html=True)

                with col_res2:
                    st.markdown(f"""
                    <div class="card" style="height: 100%;">
                        <div class="card-title">💰 予算の裏技</div>
                        <p>{data['budget_hack']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown(f"""
                <div class="card">
                    <div class="card-title">🚀 渡航までのロードマップ</div>
                    <p>{data['roadmap']}</p>
                </div>
                """, unsafe_allow_html=True)

                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #e0c3fc 0%, #8ec5fc 100%); padding: 30px; border-radius: 15px; text-align: center; margin-top: 30px;">
                    <h3 style="color: #fff;">{data['mentor_promo']}</h3>
                    <button style="background: white; color: #764ba2; border: none; padding: 12px 30px; border-radius: 25px; font-weight: bold; margin-top: 10px; cursor: pointer;">
                        📅 先輩と話してみる (初回無料)
                    </button>
                </div>
                """, unsafe_allow_html=True)
