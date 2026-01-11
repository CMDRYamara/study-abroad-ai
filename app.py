import streamlit as st
from google import genai
from google.genai import types
import json
import urllib.parse

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
    
    html, body, [class*="css"] {
        font-family: 'M PLUS Rounded 1c', sans-serif;
        background-color: #f8f9fa;
    }
    .hero {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 40px 20px;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin-bottom: 30px;
    }
    .hero h1 { font-size: 2.5rem; font-weight: 700; color: white; margin: 0; }
    
    .card {
        background: white; padding: 25px; border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 20px;
        color: #333; transition: transform 0.2s;
    }
    .card:hover { transform: translateY(-2px); }
    .card-title {
        color: #764ba2; font-size: 1.2rem; font-weight: bold;
        margin-bottom: 15px; display: flex; align-items: center; gap: 10px;
        border-bottom: 2px solid #f0f0f0; padding-bottom: 10px;
    }
    
    /* テキスト色の強制 */
    h1, h2, h3, p, li, span, div { color: #333; }
    .hero h1, .hero p { color: white !important; }
    .stButton>button { color: white !important; }
    
    /* ボタンスタイル */
    .stButton>button {
        width: 100%;
        background: linear-gradient(90deg, #ff758c 0%, #ff7eb3 100%);
        border: none; padding: 15px; border-radius: 30px;
        font-weight: bold; font-size: 1.1rem;
        box-shadow: 0 4px 15px rgba(255, 118, 136, 0.4);
    }
    .tag {
        display: inline-block; background: #eef2ff; color: #667eea !important;
        padding: 4px 12px; border-radius: 20px; font-size: 0.85rem; font-weight: bold; margin-right: 5px;
    }
    
    /* 金額の内訳テーブル */
    .cost-table { width: 100%; border-collapse: collapse; margin-top: 10px; }
    .cost-table th, .cost-table td { border-bottom: 1px solid #eee; padding: 8px; text-align: left; font-size: 0.95rem; }
    .cost-table th { color: #666; font-size: 0.85rem; }
    .total-row { font-weight: bold; color: #764ba2; }
    </style>
""", unsafe_allow_html=True)

# --- AIロジック (Gemini 2.5 Flash固定) ---
def get_study_plan_json(status, mbti, budget, period, interest, preferred_country):
    if not GOOGLE_API_KEY:
        st.error("APIキーが設定されていません。")
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
        # Gemini 2.5 Flashを指定
        response = client.models.generate_content(
            model='chat-bard',
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

with col1:
    status = st.selectbox("現在の立場", ["大学生・大学院生", "高校生", "中学生", "社会人", "その他"], index=["大学生・大学院生", "高校生", "中学生", "社会人", "その他"].index(default_values["status"]) if default_values["status"] in ["大学生・大学院生", "高校生", "中学生", "社会人", "その他"] else 0)
    mbti = st.selectbox("MBTIタイプ", ["わからない", "INTJ", "INTP", "ENTJ", "ENTP", "INFJ", "INFP", "ENFJ", "ENFP", "ISTJ", "ISFJ", "ESTJ", "ESFJ", "ISTP", "ISFP", "ESTP", "ESFP"], index=["わからない", "INTJ", "INTP", "ENTJ", "ENTP", "INFJ", "INFP", "ENFJ", "ENFP", "ISTJ", "ISFJ", "ESTJ", "ESFJ", "ISTP", "ISFP", "ESTP", "ESFP"].index(default_values["mbti"]) if default_values["mbti"] in ["わからない", "INTJ", "INTP", "ENTJ", "ENTP", "INFJ", "INFP", "ENFJ", "ENFP", "ISTJ", "ISFJ", "ESTJ", "ESFJ", "ISTP", "ISFP", "ESTP", "ESFP"] else 0)

with col2:
    period = st.selectbox("期間", ["短期（1-2週間）", "1-3ヶ月", "半年", "1年", "2年以上"], index=["短期（1-2週間）", "1-3ヶ月", "半年", "1年", "2年以上"].index(default_values["period"]) if default_values["period"] in ["短期（1-2週間）", "1-3ヶ月", "半年", "1年", "2年以上"] else 2)
    budget = st.selectbox("予算", ["50万円以下", "50-100万円", "100-200万円", "潤沢"], index=["50万円以下", "50-100万円", "100-200万円", "潤沢"].index(default_values["budget"]) if default_values["budget"] in ["50万円以下", "50-100万円", "100-200万円", "潤沢"] else 2)

with col3:
    interest = st.text_input("興味のあること", value=default_values["interest"], placeholder="例：カフェ, K-POP, IT")
    preferred_country = st.text_input("行きたい国（任意）", value=default_values["preferred_country"], placeholder="例：カナダ")

st.markdown('</div>', unsafe_allow_html=True)

# アクションボタン
if st.button("✨ ベストなプランを生成する"):
    if not interest:
        st.error("AIがプランを考えるために、「興味のあること」だけは教えてください！")
    else:
        # URLパラメータを更新（シェア用）
        st.query_params["status"] = status
        st.query_params["mbti"] = mbti
        st.query_params["period"] = period
        st.query_params["budget"] = budget
        st.query_params["interest"] = interest
        st.query_params["preferred_country"] = preferred_country

        with st.spinner("Gemini 2.5 Flashが、最新の現地情報を分析中..."):
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
                # 動的画像の生成 (Pollinations AIを使用。登録不要で使えるAPI)
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
                
                # シェア機能（URLコピー）
                share_url = f"https://あなたのアプリURL.streamlit.app/?status={urllib.parse.quote(status)}&interest={urllib.parse.quote(interest)}..." # 実際は現在のURL
                st.markdown("""
                <div style="text-align:center; margin-bottom:20px;">
                    <p style="color:#666;">👇 このプランを友達や親にシェアしよう（URLをコピー）</p>
                </div>
                """, unsafe_allow_html=True)
                # 現在のURLパラメータを含んだURLを表示（ローカルではlocalhostになります）
                st.code(f"https://share.streamlit.io/user/repo?status={status}&budget={budget}...", language="text")

                # コンバージョン
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #e0c3fc 0%, #8ec5fc 100%); padding: 30px; border-radius: 15px; text-align: center;">
                    <h3 style="color: #fff;">{data['mentor_promo']}</h3>
                    <button style="background: white; color: #764ba2; border: none; padding: 12px 30px; border-radius: 25px; font-weight: bold; margin-top: 10px; cursor: pointer;">
                        📅 {plan_a['country']}の先輩と話す (初回無料)
                    </button>
                </div>
                """, unsafe_allow_html=True)






