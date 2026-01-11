import streamlit as st
from google import genai
from google.genai import types
import json
import urllib.parse
import base64

# --- 設定 ---
# 本番環境では st.secrets を使用
GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]

# ページ設定
st.set_page_config(
    page_title="DreamRoute | AI留学プランナー",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- URLパラメータの管理 ---
# アプリ起動時にURLからパラメータを読み込む
query_params = st.query_params
default_status = query_params.get("status", "大学生・大学院生")
default_mbti = query_params.get("mbti", "わからない")
default_period = query_params.get("period", "半年")
default_budget = query_params.get("budget", "100〜200万円")
default_interest = query_params.get("interest", "")
default_country = query_params.get("preferred_country", "")

# --- デザイン(CSS)の注入 ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=M+PLUS+Rounded+1c:wght@400;700&display=swap');
    
    /* ベース設定: 強制的にライトモードのような見た目にする */
    html, body, [class*="css"] {
        font-family: 'M PLUS Rounded 1c', sans-serif;
        background-color: #f8f9fa !important;
        color: #333333 !important;
    }
    
    /* 入力フォームの視認性改善（スマホ・ダークモード対策） */
    /* セレクトボックス、テキスト入力の背景を白、文字を黒に強制 */
    .stSelectbox > div > div, .stTextInput > div > div {
        background-color: #ffffff !important;
        color: #333333 !important;
        border-color: #d1d5db !important;
    }
    /* 入力文字色 */
    input {
        color: #333333 !important;
    }
    /* ラベルの色 */
    .stSelectbox label, .stTextInput label {
        color: #333333 !important;
        font-weight: bold;
    }
    
    /* ヒーローセクション */
    .hero {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 40px 20px;
        border-radius: 15px;
        color: white !important;
        text-align: center;
        margin-bottom: 30px;
    }
    .hero h1, .hero p { color: white !important; }
    
    /* カードデザイン */
    .card {
        background: white; padding: 25px; border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 20px;
        color: #333;
    }
    .card-title {
        color: #764ba2 !important; font-size: 1.2rem; font-weight: bold;
        margin-bottom: 15px; display: flex; align-items: center; gap: 10px;
        border-bottom: 2px solid #f0f0f0; padding-bottom: 10px;
    }
    
    /* ボタン */
    .stButton>button {
        background: linear-gradient(90deg, #ff758c 0%, #ff7eb3 100%);
        border: none; padding: 15px; border-radius: 30px;
        color: white !important; font-weight: bold;
    }
    
    /* テーブル */
    .cost-table { width: 100%; border-collapse: collapse; color: #333; }
    .cost-table td { border-bottom: 1px solid #eee; padding: 8px; }
    </style>
""", unsafe_allow_html=True)

# --- AIロジック (Gemini 2.5 Flash) ---
def get_study_plan_json(status, mbti, budget, period, interest, preferred_country):
    if not GOOGLE_API_KEY:
        st.error("APIキーが設定されていません。")
        return None

    client = genai.Client(api_key=GOOGLE_API_KEY)
    
    prompt = f"""
    あなたはZ世代に特化したプロの留学コンサルタントAIです。
    ユーザー条件に基づき、以下の情報をJSON形式で出力してください。

    【条件】
    立場: {status}, MBTI: {mbti}, 予算: {budget}, 期間: {period}, 興味: {interest}, 国指定: {preferred_country}

    【出力要件 (JSON)】
    {{
        "catchphrase": "魅力的なキャッチコピー",
        "plan_a": {{
            "country": "国・都市",
            "emoji": "国旗",
            "concept": "プラン名",
            "reason": "選定理由",
            "image_keyword": "英語の画像検索キーワード(1語)",
            "cost_breakdown": [
                {{"item": "項目名", "amount": "金額", "detail": "詳細"}}
            ],
            "total_cost_comment": "予算に関するアドバイス",
            "roadmap": [
                {{"phase": "時期", "action": "行動内容"}}
            ]
        }},
        "plan_b": {{
            "country": "代替案の国",
            "emoji": "国旗",
            "concept": "コンセプト",
            "reason": "おすすめ理由"
        }},
        "similar_story": {{
            "profile": "似た属性の先輩（例：21歳 大学生 INTJ）",
            "story": "その人が実際に体験したという設定の成功談・感想（100文字程度）"
        }},
        "mentor_promo": "相談誘導の文言"
    }}
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type='application/json')
        )
        return json.loads(response.text)
    except Exception as e:
        st.error(f"エラー: {e}")
        return None

# --- HTMLダウンロード用関数 ---
def get_html_download_link(data, interest):
    # 簡易的なHTMLを生成
    html_content = f"""
    <html>
    <head>
        <title>留学プラン - {interest}</title>
        <style>
            body {{ font-family: sans-serif; padding: 20px; color: #333; }}
            .card {{ border: 1px solid #ddd; padding: 20px; border-radius: 10px; margin-bottom: 20px; }}
            h1 {{ color: #764ba2; }}
            .tag {{ background: #eee; padding: 5px 10px; border-radius: 15px; font-size: 0.8em; }}
        </style>
    </head>
    <body>
        <h1>✈️ {data['plan_a']['country']} 留学プラン</h1>
        <p><b>テーマ:</b> {data['catchphrase']}</p>
        
        <div class="card">
            <h2>Plan A: {data['plan_a']['country']}</h2>
            <p>{data['plan_a']['reason']}</p>
            <h3>💰 概算費用</h3>
            <ul>
                {''.join([f"<li>{item['item']}: {item['amount']} ({item['detail']})</li>" for item in data['plan_a']['cost_breakdown']])}
            </ul>
        </div>
        
        <div class="card">
            <h3>📅 ロードマップ</h3>
            <ul>
                {''.join([f"<li><b>{step['phase']}</b>: {step['action']}</li>" for step in data['plan_a']['roadmap']])}
            </ul>
        </div>
        <p style="font-size:0.8em; color:#888;">Powered by DreamRoute AI</p>
    </body>
    </html>
    """
    b64 = base64.b64encode(html_content.encode()).decode()
    return f'<a href="data:text/html;base64,{b64}" download="my_study_plan.html" style="text-decoration:none; background:#764ba2; color:white; padding:10px 20px; border-radius:5px;">📥 プランを保存する</a>'

# --- UI構築 ---

st.markdown('<div class="hero"><h1>DreamRoute ✈️</h1><p>あなただけの留学ルートをデザイン</p></div>', unsafe_allow_html=True)

st.markdown('<div class="card"><div class="card-title">🔍 条件入力</div>', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)
with col1:
    status = st.selectbox("現在の立場", ["大学生・大学院生", "高校生", "中学生", "社会人"], index=["大学生・大学院生", "高校生", "中学生", "社会人"].index(default_status) if default_status in ["大学生・大学院生", "高校生", "中学生", "社会人"] else 0)
    mbti = st.selectbox("MBTI", ["わからない", "INTJ", "INTP", "ENTJ", "ENTP", "INFJ", "INFP", "ENFJ", "ENFP", "ISTJ", "ISFJ", "ESTJ", "ESFJ", "ISTP", "ISFP", "ESTP", "ESFP"], index=["わからない", "INTJ", "INTP", "ENTJ", "ENTP", "INFJ", "INFP", "ENFJ", "ENFP", "ISTJ", "ISFJ", "ESTJ", "ESFJ", "ISTP", "ISFP", "ESTP", "ESFP"].index(default_mbti) if default_mbti in ["わからない", "INTJ", "INTP", "ENTJ", "ENTP", "INFJ", "INFP", "ENFJ", "ENFP", "ISTJ", "ISFJ", "ESTJ", "ESFJ", "ISTP", "ISFP", "ESTP", "ESFP"] else 0)
with col2:
    period = st.selectbox("期間", ["短期", "1-3ヶ月", "半年", "1年", "2年以上"], index=["短期", "1-3ヶ月", "半年", "1年", "2年以上"].index(default_period) if default_period in ["短期", "1-3ヶ月", "半年", "1年", "2年以上"] else 2)
    budget = st.selectbox("予算", ["50万円以下", "50-100万円", "100-200万円", "潤沢"], index=["50万円以下", "50-100万円", "100-200万円", "潤沢"].index(default_budget) if default_budget in ["50万円以下", "50-100万円", "100-200万円", "潤沢"] else 2)
with col3:
    interest = st.text_input("興味", value=default_interest, placeholder="例：カフェ")
    preferred_country = st.text_input("希望国(任意)", value=default_country)

st.markdown('</div>', unsafe_allow_html=True)

if st.button("✨ プランを作成"):
    if not interest:
        st.error("「興味」を入力してください")
    else:
        # URLパラメータを更新 (これでリンク共有が可能になる)
        st.query_params.status = status
        st.query_params.mbti = mbti
        st.query_params.period = period
        st.query_params.budget = budget
        st.query_params.interest = interest
        st.query_params.preferred_country = preferred_country

        with st.spinner("プラン作成中..."):
            data = get_study_plan_json(status, mbti, budget, period, interest, preferred_country)
            
            if data:
                plan_a = data['plan_a']
                
                # --- 結果表示 ---
                st.markdown(f"<h2 style='text-align:center; color:#764ba2;'>{data['catchphrase']}</h2>", unsafe_allow_html=True)

                # 画像
                img_url = f"https://image.pollinations.ai/prompt/scenic%20photo%20of%20{plan_a['country']}%20{plan_a['image_keyword']}?width=800&height=400&nologo=true"
                st.image(img_url, use_column_width=True)

                # Plan A 詳細
                st.markdown(f"""
                <div class="card">
                    <h2>{plan_a['emoji']} {plan_a['country']}：{plan_a['concept']}</h2>
                    <p>{plan_a['reason']}</p>
                </div>
                """, unsafe_allow_html=True)

                c1, c2 = st.columns(2)
                with c1:
                    # 費用
                    rows = "".join([f"<tr><td>{i['item']}</td><td>{i['amount']}</td></tr>" for i in plan_a['cost_breakdown']])
                    st.markdown(f"""<div class="card"><h3>💰 費用内訳</h3><table class="cost-table">{rows}</table><p style="font-size:0.9em; color:#764ba2; margin-top:10px;">{plan_a['total_cost_comment']}</p></div>""", unsafe_allow_html=True)
                with c2:
                    # ロードマップ
                    steps = "".join([f"<li><b>{s['phase']}</b>: {s['action']}</li>" for s in plan_a['roadmap']])
                    st.markdown(f"""<div class="card"><h3>📅 ロードマップ</h3><ul>{steps}</ul></div>""", unsafe_allow_html=True)

                # 類似ユーザーの声 (Plan Bの横など)
                c3, c4 = st.columns(2)
                with c3:
                     st.markdown(f"""
                    <div class="card" style="background:#f9f9f9;">
                        <h3>🤔 Plan B</h3>
                        <b>{data['plan_b']['emoji']} {data['plan_b']['country']}</b>
                        <p>{data['plan_b']['concept']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                with c4:
                    # ペルソナ表示（類似ルートの代替）
                    st.markdown(f"""
                    <div class="card" style="border-left: 4px solid #764ba2;">
                        <h3>🗣️ 先輩の体験談 (AI Sim)</h3>
                        <p style="font-size:0.9em; font-weight:bold;">{data['similar_story']['profile']}</p>
                        <p style="font-style:italic;">"{data['similar_story']['story']}"</p>
                    </div>
                    """, unsafe_allow_html=True)

                # アクションエリア
                st.markdown("---")
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    # HTMLダウンロードボタン表示
                    st.markdown(get_html_download_link(data, interest), unsafe_allow_html=True)
                with col_btn2:
                     st.markdown(f"""<div style="text-align:center;"><b>👇 このページを共有</b><br><code style="user-select:all;">{st.query_params}</code>からはコピーできませんが、<br>ブラウザのURLバーをコピーすれば同じ結果が出ます！</div>""", unsafe_allow_html=True)

