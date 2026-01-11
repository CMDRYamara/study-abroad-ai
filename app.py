import streamlit as st
from google import genai
from google.genai import types
import json
import urllib.parse
import os

# --- 設定 ---
# 本番環境では st.secrets を使用
# ローカルでテストする場合、secrets.tomlがないとエラーになるため、
# 以下のようにtry-exceptで環境変数か直接入力を許容するようにしておくと便利です
try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
except:
    # ローカルテスト用（gitには上げないでください）
    GOOGLE_API_KEY = "ここにAPIキーを入力"

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
# エラーの原因になりやすい箇所です。引用符の閉じ忘れに注意してください。
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
    /* カード内の文字色を強制的に黒にする */
    .card h1, .card h2, .card h3, .card h4, .card p, .card li, .card span, .card div {
        color: #333333;
    }
    
    /* === 【重要】入力フォームの視認性改善 === */
    .stSelectbox label, .stTextInput label {
        color: #333333 !important;
        font-weight: bold;
    }
    div[data-baseweb="select"] > div, 
    div[data-baseweb="input"] > div {
        background-color: #ffffff !important;
        color: #333333 !important;
        border: 1px solid #d1d5db !important;
        border-radius: 8px !important;
    }
    input[type="text"], div[data-baseweb="select"] span {
        color: #333333 !important;
    }
    ul[data-baseweb="menu"] {
        background-color: #ffffff !important;
    }
    li[data-baseweb="option"] {
        color: #333333 !important;
    }

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
    .cost-table th, .cost-table td { border-bottom: 1px solid #eee; padding: 8px; text-align: left; font-size: 0.95rem; color: #333; }
    </style>
""", unsafe_allow_html=True)

# --- AIロジック (Gemini 1.5 Flash固定) ---
def get_study_plan_json(status, mbti, budget, period, interest, preferred_country):
    if not GOOGLE_API_KEY or GOOGLE_API_KEY == "ここにAPIキーを入力":
        st.error("APIキーが設定されていません。コード内の `GOOGLE_API_KEY` を確認してください。")
        return None

    client = genai.Client(api_key=GOOGLE_API_KEY)
    
    # 任意の国指定がある場合の処理
    country_instruction = f"ユーザーの希望により、必ず「{preferred_country}」でのプランを作成してください。" if preferred_country else "条件に最適な国を選定してください。"

    prompt = f"""
    あなたはZ世代に特化したプロの留学コンサルタントAIです。
    以下のユーザー条件に基づき、最高のプラン(Plan A)と、比較用の代替プラン(Plan B)を作成してください。

    【ユーザー条件】
    ・現在の立場: {status}
    ・MBTI: {mbti}
    ・予算: {budget}
    ・期間: {period}
    ・興味: {interest}
    ・国指定: {preferred_country if preferred_country else "なし"}

    【出力要件】
    以下のJSONスキーマに従って出力してください。
    特に「金額の根拠」と「ロードマップ」は具体的に記述すること。
    
    {{
        "catchphrase": "ワクワクする短いキャッチコピー",
        "plan_a": {{
            "country": "国と都市名",
            "emoji": "国旗",
            "concept": "プランのコンセプトタイトル",
            "reason": "なぜここなのか（MBTIと興味に関連付けて）",
            "image_keyword": "このプランを表す英語の単語1つ（例: Cafe, Programming, Nature）",
            "cost_breakdown": [
                {{"item": "学費", "amount": "約〇〇万円", "detail": "語学学校3ヶ月分として算出"}},
                {{"item": "家賃", "amount": "約〇〇万円", "detail": "シェアハウス個室の相場"}},
                {{"item": "食費・生活費", "amount": "約〇〇万円", "detail": "自炊中心の場合"}},
                {{"item": "航空券・保険", "amount": "約〇〇万円", "detail": "LCC利用想定"}}
            ],
            "total_cost_comment": "この金額に収めるための具体的なアドバイス（プロの視点）",
            "roadmap": [
                {{"phase": "渡航前 (0-3ヶ月)", "action": "英語学習とビザ申請、〇〇の準備"}},
                {{"phase": "1ヶ月目", "action": "ホームステイで生活に慣れる、〇〇に参加する"}},
                {{"phase": "2-3ヶ月目", "action": "シェアハウスへ移動、現地の〇〇コミュニティに参加"}},
                {{"phase": "帰国前", "action": "インターン等の成果まとめ、帰国後の就活準備"}}
            ]
        }},
        "plan_b": {{
            "country": "Plan Aとは違う国・都市",
            "emoji": "国旗",
            "concept": "もう一つの可能性（少し視点を変えた提案）",
            "reason": "なぜこちらの選択肢もありなのか"
        }},
        "mentor_promo": "先輩に相談するメリットを一言で"
    }}
    """
    
    try:
        # モデルを制限の緩い gemini-1.5-flash に固定
        response = client.models.generate_content(
            model='gemini-1.5-flash',
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

col1, col2, col3 = st.columns(3)

# セレクトボックスの選択肢リスト
list_status = ["大学生・大学院生", "高校生", "中学生", "社会人", "その他"]
list_mbti = ["わからない", "INTJ", "INTP", "ENTJ", "ENTP", "INFJ", "INFP", "ENFJ", "ENFP", "ISTJ", "ISFJ", "ESTJ", "ESFJ", "ISTP", "ISFP", "ESTP", "ESFP"]
list_period = ["短期（1-2週間）", "1-3ヶ月", "半年", "1年", "2年以上"]
list_budget = ["50万円以下", "50-100万円", "100-200万円", "潤沢"]

# URLパラメータからインデックスを取得（安全策）
def get_index(options, value):
    try:
        return options.index(value)
    except ValueError:
        return 0

with col1:
    status = st.selectbox("現在の立場", list_status, index=get_index(list_status, default_values["status"]))
    mbti = st.selectbox("MBTIタイプ", list_mbti, index=get_index(list_mbti, default_values["mbti"]))

with col2:
    period = st.selectbox("期間", list_period, index=get_index(list_period, default_values["period"]))
    budget = st.selectbox("予算", list_budget, index=get_index(list_budget, default_values["budget"]))

with col3:
    interest = st.text_input("興味のあること", value=default_values["interest"], placeholder="例：カフェ, K-POP, IT")
    preferred_country = st.text_input("行きたい国（任意）", value=default_values["preferred_country"], placeholder="例：カナダ")

st.markdown('</div>', unsafe_allow_html=True)

# アクションボタン
if st.button("✨ ベストなプランを生成する"):
    if not interest:
        st.error("AIがプランを考えるために、「興味のあること」だけは教えてください！")
    else:
        # URLパラメータを更新
        st.query_params["status"] = status
        st.query_params["mbti"] = mbti
        st.query_params["period"] = period
        st.query_params["budget"] = budget
        st.query_params["interest"] = interest
        st.query_params["preferred_country"] = preferred_country

        with st.spinner("Gemini 1.5 Flashが、最新の現地情報を分析中..."):
            data = get_study_plan_json(status, mbti, budget, period, interest, preferred_country)
            
            if data:
                plan_a = data['plan_a']
                plan_b = data['plan_b']

                # キャッチコピー
                st.markdown(f"""
                <div style="text-align:center; margin: 30px 0;">
                    <h2 style="color:#764ba2; margin-bottom:0;">{data['catchphrase']}</h2>
                </div>
                """, unsafe_allow_html=True)

                # --- PLAN A メインカード ---
                image_keyword = plan_a.get('image_keyword', 'travel')
                image_url = f"https://image.pollinations.ai/prompt/scenic%20photo%20of%20{plan_a['country']}%20{image_keyword}%20atmosphere?width=800&height=400&nologo=true"
                
                st.markdown(f"""
                <div class="card" style="border-top: 5px solid #ff758c; padding:0; overflow:hidden;">
                    <img src="{image_url}" style="width:100%; height:250px; object-fit:cover;">
                    <div style="padding:25px;">
                        <h2 style="font-size:1.8rem;">{plan_a['emoji']} {plan_a['country']}：{plan_a['concept']}</h2>
                        <p>{plan_a['reason']}</p>
                        <div style="margin-top:15px;">
                            <span class="tag">#{status}プラン</span>
                            <span class="tag">#PlanA</span>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # --- 3カラム詳細情報 ---
                col_c1, col_c2, col_c3 = st.columns(3)
                
                # 金額試算
                with col_c1:
                    rows = "".join([f"<tr><td>{item['item']}</td><td>{item['amount']}</td></tr><tr><td colspan='2' style='color:#888; font-size:0.8em; border-bottom:1px solid #eee;'>└ {item['detail']}</td></tr>" for item in plan_a['cost_breakdown']])
                    st.markdown(f"""
                    <div class="card" style="height: 100%;">
                        <div class="card-title">💰 費用のリアルな内訳</div>
                        <table class="cost-table">
                            {rows}
                        </table>
                        <p style="margin-top:10px; font-size:0.9em; color:#764ba2;"><b>💡Pro Advice:</b><br>{plan_a['total_cost_comment']}</p>
                    </div>
                    """, unsafe_allow_html=True)

                # ロードマップ
                with col_c2:
                    roadmap_html = "".join([f"<li style='margin-bottom:10px;'><b>{step['phase']}</b><br>{step['action']}</li>" for step in plan_a['roadmap']])
                    st.markdown(f"""
                    <div class="card" style="height: 100%;">
                        <div class="card-title">📅 成功へのロードマップ</div>
                        <ul style="padding-left:20px; line-height:1.5; font-size:0.95rem;">{roadmap_html}</ul>
                    </div>
                    """, unsafe_allow_html=True)

                # 類似プラン (Plan B)
                with col_c3:
                    st.markdown(f"""
                    <div class="card" style="height: 100%; background-color:#fdfdfd; border: 2px dashed #ddd;">
                        <div class="card-title" style="color:#666;">🤔 他の選択肢 (Plan B)</div>
                        <h3>{plan_b['emoji']} {plan_b['country']}</h3>
                        <p style="font-weight:bold;">{plan_b['concept']}</p>
                        <p style="font-size:0.9rem;">{plan_b['reason']}</p>
                        <hr>
                        <p style="font-size:0.85rem; color:#888;">「こっちも気になる」と思ったら、チャットで相談してみよう。</p>
                    </div>
                    """, unsafe_allow_html=True)

                # --- シェア & コンバージョン ---
                st.markdown("---")
                
                # シェア用URL生成
                query_string = urllib.parse.urlencode({
                    "status": status,
                    "mbti": mbti,
                    "period": period,
                    "budget": budget,
                    "interest": interest,
                    "preferred_country": preferred_country
                })
                
                st.markdown("""
                <div style="text-align:center; margin-bottom:20px;">
                    <p style="color:#666;">👇 友達にこのプランをシェアするためのURLパラメータ</p>
                    <small>※あなたのアプリのURLの後ろに、以下をコピーして貼り付けて送ってください</small>
                </div>
                """, unsafe_allow_html=True)
                
                st.code(f"?{query_string}", language="text")

                # コンバージョン
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #e0c3fc 0%, #8ec5fc 100%); padding: 30px; border-radius: 15px; text-align: center;">
                    <h3 style="color: #fff;">{data['mentor_promo']}</h3>
                    <button style="background: white; color: #764ba2; border: none; padding: 12px 30px; border-radius: 25px; font-weight: bold; margin-top: 10px; cursor: pointer;">
                        📅 {plan_a['country']}の先輩と話す (初回無料)
                    </button>
                </div>
                """, unsafe_allow_html=True)
