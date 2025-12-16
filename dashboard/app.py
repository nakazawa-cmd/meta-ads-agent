"""
Meta Ads Intelligent Agent ダッシュボード
Streamlitベースの統合管理UI
"""
import json
import sys
import os
from datetime import datetime
from pathlib import Path

# パスを追加
sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import streamlit as st

# ページ設定
st.set_page_config(
    page_title="Meta Ads AI Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# CSSスタイル
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0;
    }
    .sub-header {
        color: #666;
        font-size: 1rem;
        margin-top: 0;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
    }
    .status-good { color: #10B981; font-weight: bold; }
    .status-warning { color: #F59E0B; font-weight: bold; }
    .status-critical { color: #EF4444; font-weight: bold; }
    .recommendation-card {
        background: #f8f9fa;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #667eea;
        margin: 10px 0;
    }
    .alert-critical {
        background: #FEE2E2;
        border-left: 4px solid #EF4444;
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
    }
    .alert-warning {
        background: #FEF3C7;
        border-left: 4px solid #F59E0B;
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
    }
    .opportunity-card {
        background: #D1FAE5;
        border-left: 4px solid #10B981;
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)


def init_agent():
    """エージェントを初期化"""
    if "agent" not in st.session_state:
        from agent import IntegratedAgent
        st.session_state.agent = IntegratedAgent()
    return st.session_state.agent


def get_available_accounts(agent):
    """利用可能な広告アカウント一覧を取得"""
    if "ad_accounts" not in st.session_state:
        if agent.meta_initialized and agent.meta_auth:
            accounts = agent.meta_auth.get_ad_accounts()
            st.session_state.ad_accounts = accounts
        else:
            st.session_state.ad_accounts = []
    return st.session_state.ad_accounts


def select_account_widget(agent):
    """アカウント選択ウィジェット"""
    accounts = get_available_accounts(agent)
    
    if not accounts:
        return None
    
    # アカウント選択用のオプションを作成
    account_options = {
        f"{acc.get('name', 'Unknown')} ({acc.get('account_id', '')})": acc.get('id')
        for acc in accounts
    }
    
    if not account_options:
        return None
    
    # デフォルト選択
    if "selected_account" not in st.session_state:
        st.session_state.selected_account = list(account_options.values())[0]
    
    selected_name = st.selectbox(
        "📊 広告アカウント",
        options=list(account_options.keys()),
        index=list(account_options.values()).index(st.session_state.selected_account) if st.session_state.selected_account in account_options.values() else 0,
    )
    
    st.session_state.selected_account = account_options[selected_name]
    return st.session_state.selected_account


def main():
    # ヘッダー
    st.markdown('<h1 class="main-header">🤖 Meta Ads AI Agent</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">人間のルールを超える総合判断</p>', unsafe_allow_html=True)
    
    # サイドバー
    with st.sidebar:
        st.header("⚙️ 設定")
        
        page = st.radio(
            "ページ選択",
            ["📊 ダッシュボード", "🔍 キャンペーン分析", "🔮 シミュレーション", "📈 パターン学習", "📚 知識ベース", "🤖 自動運用", "📤 入稿"],
            index=0,
        )
        
        st.divider()
        
        # Meta API接続状態
        agent = init_agent()
        if agent.meta_initialized:
            st.success("✅ Meta API 接続済み")
            
            # アカウント選択
            st.subheader("🏢 アカウント選択")
            selected_account = select_account_widget(agent)
            
            if selected_account:
                st.caption(f"ID: {selected_account}")
            
            # アカウント一覧を更新
            if st.button("🔄 アカウント一覧を更新"):
                if "ad_accounts" in st.session_state:
                    del st.session_state.ad_accounts
                st.rerun()
        else:
            st.warning("⚠️ デモモード（Meta API未接続）")
        
        st.divider()
        st.caption("© 2024 Meta Ads AI Agent")
    
    # ページルーティング
    if page == "📊 ダッシュボード":
        show_dashboard(agent)
    elif page == "🔍 キャンペーン分析":
        show_campaign_analysis(agent)
    elif page == "🔮 シミュレーション":
        show_simulation(agent)
    elif page == "📈 パターン学習":
        show_pattern_learning(agent)
    elif page == "📚 知識ベース":
        show_knowledge_base()
    elif page == "🤖 自動運用":
        show_automation(agent)
    elif page == "📤 入稿":
        show_creative_management(agent)


def show_creative_management(agent):
    """入稿・クリエイティブ管理ページ"""
    st.header("📤 ワンクリック入稿")
    
    selected_account = st.session_state.get("selected_account")
    
    if not agent.meta_initialized:
        st.warning("⚠️ Meta APIに接続してください")
        return
    
    if not selected_account:
        st.warning("⚠️ アカウントを選択してください")
        return
    
    tab1, tab2, tab3 = st.tabs(["🚀 ワンクリック入稿", "🖼️ クリエイティブ管理", "📋 手動入稿"])
    
    managers = agent._get_managers(selected_account)
    if not managers:
        st.error("マネージャーの初期化に失敗しました")
        return
    
    # =====================================================
    # ワンクリック入稿タブ
    # =====================================================
    with tab1:
        st.subheader("🚀 テンプレートから即入稿")
        
        st.success("""
        💡 **ボタン1つでキャンペーン作成！**
        
        1. テンプレートを選択
        2. 商品名とURLを入力
        3. 画像を選択（ライブラリから）
        4. 🚀 入稿！
        
        → メインテキスト・見出し・説明は**AIが自動生成**します
        """)
        
        try:
            from automation.campaign_templates import QuickLaunchEngine, CAMPAIGN_TEMPLATES
            
            quick_launch = QuickLaunchEngine(
                meta_auth=agent.meta_auth,
                integrated_agent=agent,
            )
            
            # テンプレート選択
            st.markdown("### 1️⃣ テンプレートを選択")
            
            template_cols = st.columns(len(CAMPAIGN_TEMPLATES))
            selected_template = st.session_state.get("selected_template", "asc_broad")
            
            for i, (key, template) in enumerate(CAMPAIGN_TEMPLATES.items()):
                with template_cols[i]:
                    is_selected = selected_template == key
                    button_type = "primary" if is_selected else "secondary"
                    
                    if st.button(
                        f"{template['icon']} {template['name']}",
                        key=f"template_{key}",
                        type=button_type,
                        use_container_width=True,
                    ):
                        st.session_state["selected_template"] = key
                        st.rerun()
                    
                    st.caption(template["description"])
            
            # 選択中のテンプレート情報
            template = CAMPAIGN_TEMPLATES.get(selected_template, {})
            defaults = template.get("defaults", {})
            
            st.divider()
            
            # 入力フォーム
            st.markdown("### 2️⃣ 基本情報を入力")
            
            col1, col2 = st.columns(2)
            
            with col1:
                product_name = st.text_input(
                    "商品/サービス名 *",
                    placeholder="例: ロジリカ",
                    help="AIがこの名前を使ってテキストを生成します",
                )
                
                link_url = st.text_input(
                    "リンク先URL *",
                    placeholder="https://example.com/lp",
                )
                
                page_id = st.text_input(
                    "FacebookページID *",
                    value=st.session_state.get("default_page_id", ""),
                    help="Meta Business Suiteで確認できます",
                )
                
                # ページIDを記憶
                if page_id:
                    st.session_state["default_page_id"] = page_id
            
            with col2:
                daily_budget = st.number_input(
                    "日予算（円）",
                    value=defaults.get("daily_budget", 10000),
                    step=1000,
                    min_value=100,
                )
                
                auto_generate = st.checkbox("✨ テキストをAIで自動生成", value=True)
                
                if not auto_generate:
                    st.markdown("**カスタムテキスト**")
                    custom_headline = st.text_input("見出し（25文字以内）", max_chars=25)
                    custom_primary = st.text_area("メインテキスト（125文字以内）", max_chars=125)
                    custom_desc = st.text_input("説明（30文字以内）", max_chars=30)
            
            st.divider()
            
            # 画像選択
            st.markdown("### 3️⃣ クリエイティブを選択")
            
            # 画像ライブラリを取得
            if st.button("🔄 画像ライブラリを読み込み"):
                with st.spinner("読み込み中..."):
                    images = quick_launch.get_ad_images(selected_account, limit=30)
                    st.session_state["ad_images"] = images
            
            ad_images = st.session_state.get("ad_images", [])
            
            if ad_images:
                st.write(f"📷 {len(ad_images)}件の画像が見つかりました")
                
                # 画像をグリッド表示
                selected_hashes = st.session_state.get("selected_image_hashes", [])
                
                cols = st.columns(5)
                for i, img in enumerate(ad_images[:20]):
                    with cols[i % 5]:
                        img_hash = img.get("hash", "")
                        img_url = img.get("url", "")
                        img_name = img.get("name", "")[:15]
                        
                        is_selected = img_hash in selected_hashes
                        
                        if img_url:
                            st.image(img_url, width=100)
                        
                        if st.checkbox(
                            img_name or f"画像{i+1}",
                            value=is_selected,
                            key=f"img_{img_hash}",
                        ):
                            if img_hash not in selected_hashes:
                                selected_hashes.append(img_hash)
                        else:
                            if img_hash in selected_hashes:
                                selected_hashes.remove(img_hash)
                
                st.session_state["selected_image_hashes"] = selected_hashes
                st.write(f"選択中: {len(selected_hashes)}件")
            else:
                st.info("「🔄 画像ライブラリを読み込み」をクリックしてください")
                
                # 画像アップロード
                st.markdown("**または新しい画像をアップロード:**")
                uploaded = st.file_uploader("画像を選択", type=["jpg", "jpeg", "png"])
                
                if uploaded:
                    st.image(uploaded, width=150)
                    if st.button("📤 アップロード"):
                        from meta_api.creative import CreativeManager
                        import tempfile
                        
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                            tmp.write(uploaded.getvalue())
                            tmp_path = tmp.name
                        
                        ad_account = agent.meta_auth.get_ad_account(selected_account)
                        cm = CreativeManager(ad_account)
                        result = cm.upload_image(tmp_path, uploaded.name)
                        
                        import os
                        os.unlink(tmp_path)
                        
                        if result:
                            st.success(f"✅ アップロード完了！")
                            if "selected_image_hashes" not in st.session_state:
                                st.session_state["selected_image_hashes"] = []
                            st.session_state["selected_image_hashes"].append(result["hash"])
            
            st.divider()
            
            # 入稿実行
            st.markdown("### 4️⃣ 入稿！")
            
            selected_hashes = st.session_state.get("selected_image_hashes", [])
            
            # バリデーション
            can_launch = all([
                product_name,
                link_url,
                page_id,
                len(selected_hashes) > 0,
            ])
            
            if not can_launch:
                missing = []
                if not product_name: missing.append("商品名")
                if not link_url: missing.append("URL")
                if not page_id: missing.append("ページID")
                if not selected_hashes: missing.append("画像")
                st.warning(f"⚠️ 以下が未入力です: {', '.join(missing)}")
            
            col1, col2 = st.columns([1, 2])
            
            with col1:
                if st.button(
                    f"🚀 {template.get('name', 'キャンペーン')}を作成！",
                    type="primary",
                    disabled=not can_launch,
                    use_container_width=True,
                ):
                    with st.spinner("入稿中..."):
                        # カスタムテキスト
                        custom_texts = None
                        if not auto_generate:
                            custom_texts = [{
                                "headline": custom_headline,
                                "primary_text": custom_primary,
                                "description": custom_desc,
                            }]
                        
                        result = quick_launch.quick_launch(
                            account_id=selected_account,
                            template_id=selected_template,
                            product_name=product_name,
                            page_id=page_id,
                            link_url=link_url,
                            image_hashes=selected_hashes,
                            custom_budget=daily_budget,
                            custom_texts=custom_texts,
                            auto_generate_texts=auto_generate,
                        )
                        
                        if result.get("success"):
                            st.success(result.get("message", "✅ 作成成功！"))
                            st.balloons()
                            
                            st.markdown(f"""
                            **作成されたキャンペーン:**
                            - 名前: `{result.get('campaign_name')}`
                            - 予算: ¥{result.get('budget', 0):,}/日
                            - 広告数: {result.get('ads_created', 0)}件
                            
                            ⚠️ **停止状態で作成されています。** Meta広告マネージャーで確認後、有効化してください。
                            """)
                        else:
                            st.error(f"❌ エラー: {result.get('error')}")
            
            with col2:
                st.caption(f"テンプレート: {template.get('name')} | 予算: ¥{daily_budget:,}/日 | 画像: {len(selected_hashes)}枚")
        
        except Exception as e:
            st.error(f"エラー: {e}")
            import traceback
            st.code(traceback.format_exc())
    
    # =====================================================
    # クリエイティブ管理タブ
    # =====================================================
    with tab2:
        st.subheader("🖼️ クリエイティブライブラリ")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📷 画像アップロード")
            
            uploaded_file = st.file_uploader("画像を選択", type=["jpg", "jpeg", "png"], key="upload_tab2")
            
            if uploaded_file:
                st.image(uploaded_file, width=200)
                
                if st.button("📤 アップロード", key="upload_btn_tab2"):
                    from meta_api.creative import CreativeManager
                    import tempfile
                    
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                        tmp.write(uploaded_file.getvalue())
                        tmp_path = tmp.name
                    
                    ad_account = agent.meta_auth.get_ad_account(selected_account)
                    creative_manager = CreativeManager(ad_account)
                    result = creative_manager.upload_image(tmp_path, uploaded_file.name)
                    
                    import os
                    os.unlink(tmp_path)
                    
                    if result:
                        st.success(f"✅ アップロード完了！")
                        st.code(f"Image Hash: {result['hash']}")
                    else:
                        st.error("アップロードに失敗しました")
        
        with col2:
            st.markdown("#### 📋 画像一覧")
            
            if st.button("🔄 一覧を更新", key="refresh_images"):
                from automation.campaign_templates import QuickLaunchEngine
                quick_launch = QuickLaunchEngine(meta_auth=agent.meta_auth)
                images = quick_launch.get_ad_images(selected_account, limit=20)
                st.session_state["images_list_tab2"] = images
            
            images = st.session_state.get("images_list_tab2", [])
            if images:
                for img in images[:10]:
                    with st.expander(f"🖼️ {img.get('name', 'Unknown')[:30]}"):
                        if img.get("url"):
                            st.image(img["url"], width=150)
                        st.code(f"Hash: {img.get('hash')}")
            else:
                st.caption("「🔄 一覧を更新」をクリックしてください")
    
    # =====================================================
    # 手動入稿タブ（従来の機能）
    # =====================================================
    with tab3:
        st.subheader("📋 手動入稿")
        
        st.info("細かい設定が必要な場合はこちらから手動で入稿できます。")
        
        # キャンペーン作成
        st.markdown("#### 🎯 キャンペーン作成・複製")
        
        campaigns = managers["campaign"].get_campaigns(status_filter=["ACTIVE", "PAUSED"])
        
        col1, col2 = st.columns(2)
        
        with col1:
            with st.form("create_campaign_manual"):
                camp_name = st.text_input("キャンペーン名", placeholder="例: 2024_12_ロジリカ_トラフィック")
                camp_objective = st.selectbox(
                    "目的",
                    [
                        ("OUTCOME_TRAFFIC", "トラフィック"),
                        ("OUTCOME_ENGAGEMENT", "エンゲージメント"),
                        ("OUTCOME_SALES", "売上"),
                    ],
                    format_func=lambda x: x[1],
                )
                camp_budget = st.number_input("日予算（円）", value=10000, step=1000)
                
                if st.form_submit_button("🚀 作成"):
                    if camp_name:
                        result = managers["campaign"].create_campaign(
                            name=camp_name,
                            objective=camp_objective[0],
                            daily_budget=camp_budget,
                        )
                        if result:
                            st.success(f"✅ 作成しました: {result['id']}")
                        else:
                            st.error("作成に失敗しました")
        
        with col2:
            if campaigns:
                with st.form("duplicate_campaign_manual"):
                    campaign_options = {c["name"]: c for c in campaigns}
                    selected_camp = st.selectbox("複製元", list(campaign_options.keys()))
                    new_name = st.text_input("新しい名前", placeholder="空欄で自動生成")
                    
                    if st.form_submit_button("📋 複製"):
                        orig = campaign_options[selected_camp]
                        result = managers["campaign"].duplicate_campaign(
                            campaign_id=orig["id"],
                            new_name=new_name or None,
                        )
                        if result:
                            st.success(f"✅ 複製しました: {result['name']}")
        
        st.divider()
        
        # 広告セット作成
        st.markdown("#### 📦 広告セット作成")
        
        if campaigns:
            with st.form("create_adset_manual"):
                campaign_options = {c["name"]: c for c in campaigns}
                selected_camp = st.selectbox("キャンペーン", list(campaign_options.keys()), key="adset_camp")
                adset_name = st.text_input("広告セット名", placeholder="例: JP_18-65_ブロード")
                adset_budget = st.number_input("日予算（円）", value=3000, step=1000)
                
                if st.form_submit_button("🚀 作成"):
                    if adset_name:
                        camp = campaign_options[selected_camp]
                        result = managers["adset"].create_adset(
                            campaign_id=camp["id"],
                            name=adset_name,
                            daily_budget=adset_budget,
                        )
                        if result:
                            st.success(f"✅ 作成しました: {result['id']}")
        else:
            st.caption("先にキャンペーンを作成してください")


def show_dashboard(agent):
    """ダッシュボードページ"""
    st.header("📊 パフォーマンスダッシュボード")
    
    # 期間選択
    col1, col2 = st.columns([2, 1])
    with col1:
        date_range = st.selectbox(
            "📅 期間選択",
            ["今日", "昨日", "過去3日", "過去7日", "過去14日", "過去30日"],
            index=3,  # デフォルトは過去7日
        )
    
    # 期間をdate_presetに変換
    date_preset_map = {
        "今日": "today",
        "昨日": "yesterday",
        "過去3日": "last_3d",
        "過去7日": "last_7d",
        "過去14日": "last_14d",
        "過去30日": "last_30d",
    }
    date_preset = date_preset_map.get(date_range, "last_7d")
    
    # 選択中のアカウント
    selected_account = st.session_state.get("selected_account")
    
    # レポート取得
    with st.spinner("データを読み込み中..."):
        report = agent.get_daily_report(account_id=selected_account, date_preset=date_preset)
    
    if "error" in report:
        st.error(f"エラー: {report['error']}")
        return
    
    # デモモード表示
    if report.get("demo_mode"):
        st.info("🎮 デモモードで動作中。実データを表示するにはMeta APIを接続してください。")
    
    # メトリクス
    current = report.get("current", {})
    previous = report.get("previous", {})
    
    # 期間ラベル
    period_label = date_range
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        spend_current = current.get("spend", 0)
        spend_previous = previous.get("spend", 0)
        delta = ((spend_current - spend_previous) / spend_previous * 100) if spend_previous > 0 else 0
        st.metric("💰 消化", f"¥{spend_current:,.0f}", f"{delta:+.1f}%")
    
    with col2:
        cv_current = current.get("conversions", 0)
        cv_previous = previous.get("conversions", 0)
        delta = ((cv_current - cv_previous) / cv_previous * 100) if cv_previous > 0 else 0
        st.metric("🎯 CV", f"{cv_current}件", f"{delta:+.1f}%")
    
    with col3:
        ctr_current = current.get("ctr", 0)
        ctr_previous = previous.get("ctr", 0)
        delta = ((ctr_current - ctr_previous) / ctr_previous * 100) if ctr_previous > 0 else 0
        st.metric("👆 CTR", f"{ctr_current:.2f}%", f"{delta:+.1f}%")
    
    with col4:
        cpa_current = current.get("cpa", 0)
        cpa_previous = previous.get("cpa", 0)
        delta = ((cpa_current - cpa_previous) / cpa_previous * 100) if cpa_previous > 0 else 0
        st.metric("📉 CPA", f"¥{cpa_current:,.0f}", f"{delta:+.1f}%", delta_color="inverse")
    
    with col5:
        roas_current = current.get("roas", 0)
        roas_previous = previous.get("roas", 0)
        delta = ((roas_current - roas_previous) / roas_previous * 100) if roas_previous > 0 else 0
        st.metric("📈 ROAS", f"{roas_current:.2f}x", f"{delta:+.1f}%")
    
    st.divider()
    
    # AIブリーフィング
    briefing = report.get("ai_briefing", {})
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🚨 アラート")
        alerts = briefing.get("alerts", [])
        if alerts:
            for alert in alerts:
                alert_type = alert.get("type", "warning")
                css_class = "alert-critical" if alert_type == "critical" else "alert-warning"
                icon = "🔴" if alert_type == "critical" else "🟡"
                st.markdown(f"""
                <div class="{css_class}">
                    {icon} <strong>{alert.get('project')}</strong><br>
                    {alert.get('message')}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.success("✅ アラートはありません")
    
    with col2:
        st.subheader("✨ 機会")
        opportunities = briefing.get("opportunities", [])
        if opportunities:
            for opp in opportunities:
                st.markdown(f"""
                <div class="opportunity-card">
                    🟢 <strong>{opp.get('project')}</strong><br>
                    {opp.get('message')}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("特に目立った機会はありません")
    
    st.divider()
    
    # サマリー
    summary = briefing.get("summary", {})
    st.subheader("📋 サマリー")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("稼働キャンペーン数", summary.get("projects_count", 0))
    with col2:
        st.metric("アラート数", summary.get("alerts_count", 0))
    with col3:
        st.metric("機会数", summary.get("opportunities_count", 0))
    
    # CSVエクスポート
    st.divider()
    st.subheader("📥 データエクスポート")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📊 週次レポート生成"):
            with st.spinner("レポート生成中..."):
                try:
                    from automation.reports import ReportGenerator
                    generator = ReportGenerator(integrated_agent=agent)
                    weekly_report = generator.generate_weekly_report(selected_account)
                    
                    if "error" not in weekly_report:
                        st.session_state["weekly_report"] = weekly_report
                        st.success("✅ 週次レポートを生成しました")
                    else:
                        st.error(f"エラー: {weekly_report['error']}")
                except Exception as e:
                    st.error(f"エラー: {e}")
    
    with col2:
        if st.button("📈 月次レポート生成"):
            with st.spinner("レポート生成中..."):
                try:
                    from automation.reports import ReportGenerator
                    generator = ReportGenerator(integrated_agent=agent)
                    monthly_report = generator.generate_monthly_report(selected_account)
                    
                    if "error" not in monthly_report:
                        st.session_state["monthly_report"] = monthly_report
                        st.success("✅ 月次レポートを生成しました")
                    else:
                        st.error(f"エラー: {monthly_report['error']}")
                except Exception as e:
                    st.error(f"エラー: {e}")
    
    # CSVダウンロード
    with col3:
        report_to_export = st.session_state.get("weekly_report") or st.session_state.get("monthly_report")
        if report_to_export:
            from automation.reports import ReportGenerator
            generator = ReportGenerator()
            csv_data = generator.export_csv(report_to_export)
            
            st.download_button(
                label="📥 CSVダウンロード",
                data=csv_data,
                file_name=f"meta_ads_report_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
            )
        else:
            st.caption("レポートを生成するとCSVダウンロードできます")
    
    # レポートプレビュー
    report_data = st.session_state.get("weekly_report") or st.session_state.get("monthly_report")
    if report_data and "error" not in report_data:
        with st.expander("📋 レポートプレビュー", expanded=False):
            summary = report_data.get("summary", {})
            st.write(f"**期間:** {report_data.get('date_preset')}")
            st.write(f"**総消化:** ¥{summary.get('total_spend', 0):,.0f}")
            st.write(f"**総売上:** ¥{summary.get('total_revenue', 0):,.0f}")
            st.write(f"**ROAS:** {summary.get('overall_roas', 0):.2f}")
            st.write(f"**CPA:** ¥{summary.get('overall_cpa', 0):,.0f}")
            
            # キャンペーン別
            campaigns_data = report_data.get("campaigns", [])
            if campaigns_data:
                import pandas as pd
                df = pd.DataFrame(campaigns_data)
                st.dataframe(df[["name", "spend", "conversions", "roas", "cpa", "ctr"]])


def show_campaign_analysis(agent):
    """キャンペーン分析ページ"""
    st.header("🔍 AIキャンペーン分析")
    
    st.info("💡 AI が知識ベース、パターン学習、市場分析を統合して総合判断します")
    
    # 選択中のアカウント
    selected_account = st.session_state.get("selected_account")
    
    # キャンペーン一覧を取得
    campaigns = []
    if agent.meta_initialized and selected_account:
        managers = agent._get_managers(selected_account)
        if managers:
            campaigns = managers["campaign"].get_campaigns(status_filter=["ACTIVE", "PAUSED"])
    
    # キャンペーン選択
    st.subheader("📌 キャンペーン選択")
    
    if campaigns:
        campaign_options = {
            f"{c.get('name', 'Unknown')} ({c.get('effective_status', '')})": c
            for c in campaigns
        }
        
        selected_campaign_name = st.selectbox(
            "分析するキャンペーンを選択",
            options=list(campaign_options.keys()),
        )
        
        selected_campaign = campaign_options[selected_campaign_name]
        campaign_id = selected_campaign.get("id")
        
        # 期間選択
        col1, col2 = st.columns(2)
        with col1:
            analysis_period = st.selectbox(
                "📅 分析期間",
                ["過去7日", "過去14日", "過去30日"],
                index=0,
            )
        
        period_map = {"過去7日": "last_7d", "過去14日": "last_14d", "過去30日": "last_30d"}
        date_preset = period_map[analysis_period]
        
        # パフォーマンスデータを取得
        with st.spinner("パフォーマンスデータを取得中..."):
            insights = managers["insights"].get_campaign_insights(
                date_preset=date_preset,
                campaign_ids=[campaign_id],
            )
            
            if insights:
                # 集計
                perf_data = agent._aggregate_insights(insights)
            else:
                perf_data = {}
        
        # パフォーマンス表示
        st.subheader("📊 パフォーマンスデータ（自動取得）")
        
        if perf_data:
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                st.metric("消化", f"¥{perf_data.get('spend', 0):,.0f}")
            with col2:
                st.metric("CV", f"{perf_data.get('conversions', 0)}件")
            with col3:
                st.metric("CTR", f"{perf_data.get('ctr', 0):.2f}%")
            with col4:
                st.metric("CPA", f"¥{perf_data.get('cpa', 0):,.0f}")
            with col5:
                st.metric("ROAS", f"{perf_data.get('roas', 0):.2f}x")
            
            # 詳細
            with st.expander("詳細データ"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"インプレッション: {perf_data.get('impressions', 0):,}")
                    st.write(f"クリック: {perf_data.get('clicks', 0):,}")
                    st.write(f"CPC: ¥{perf_data.get('cpc', 0):,.0f}")
                with col2:
                    st.write(f"CVR: {perf_data.get('cvr', 0):.2f}%")
                    st.write(f"CPM: ¥{perf_data.get('cpm', 0):,.0f}")
                    st.write(f"リーチ: {perf_data.get('reach', 0):,}")
        else:
            st.warning("パフォーマンスデータがありません")
            perf_data = {}
        
        # 変数を設定
        spend = perf_data.get("spend", 0)
        impressions = perf_data.get("impressions", 0)
        clicks = perf_data.get("clicks", 0)
        conversions = perf_data.get("conversions", 0)
        ctr = perf_data.get("ctr", 0)
        cvr = perf_data.get("cvr", 0)
        cpa = perf_data.get("cpa", 0)
        roas = perf_data.get("roas", 0)
        
    else:
        st.warning("⚠️ キャンペーンが見つかりません。Meta APIが接続されているか、アカウントを選択しているか確認してください。")
        campaign_id = None
        spend = impressions = clicks = conversions = 0
        ctr = cvr = cpa = roas = 0
    
    st.divider()
    
    # 案件情報入力
    with st.expander("📝 案件情報を入力", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            project_name = st.text_input("案件名", selected_campaign.get("name", "") if campaigns else "")
            
            # 業界カテゴリ（大分類）
            industry_category = st.selectbox(
                "業界カテゴリ",
                ["EC・物販", "美容・コスメ", "健康食品・サプリ", "ファッション・アパレル", "教育・オンライン講座", "BtoB・SaaS", "金融・保険", "飲食・フード", "旅行・レジャー", "その他"],
            )
            
            # 具体的なジャンル（自由入力）
            specific_genre = st.text_input(
                "具体的なジャンル",
                placeholder="例: ファッションジュエリー、メンズ脱毛、英会話スクール",
            )
            
            # キャンペーン目的
            campaign_objective = st.selectbox(
                "🎯 キャンペーン目的",
                [
                    "コンバージョン（購入・申込）",
                    "ROAS最大化（売上重視）",
                    "リード獲得（問い合わせ）",
                    "フォロワー獲得",
                    "ブランド認知・リーチ",
                    "エンゲージメント（いいね・コメント）",
                    "トラフィック（サイト誘導）",
                    "動画再生",
                ],
            )
        
        with col2:
            # 目的に応じて入力項目を変える
            if campaign_objective in ["コンバージョン（購入・申込）", "リード獲得（問い合わせ）"]:
                judgment_basis = st.radio(
                    "📊 判断基準",
                    ["CPA重視", "両方"],
                    horizontal=True,
                )
                target_cpa = st.number_input("目標CPA（円）", value=5000, step=500)
                target_roas = None
                
            elif campaign_objective == "ROAS最大化（売上重視）":
                judgment_basis = "ROAS重視"
                target_roas = st.number_input("目標ROAS", value=3.0, step=0.5)
                target_cpa = None
                st.info("💡 ROASベースで分析します")
                
            elif campaign_objective == "フォロワー獲得":
                judgment_basis = "フォロワー単価"
                target_follower_cost = st.number_input("目標フォロワー単価（円）", value=100, step=10)
                target_cpa = None
                target_roas = None
                st.info("💡 フォロワー単価とエンゲージメント率で分析します")
                
            elif campaign_objective in ["ブランド認知・リーチ", "動画再生"]:
                judgment_basis = "リーチ効率"
                target_cpm = st.number_input("目標CPM（円）", value=500, step=50)
                target_cpa = None
                target_roas = None
                st.info("💡 リーチ数・CPM・フリークエンシーで分析します")
                
            elif campaign_objective == "エンゲージメント（いいね・コメント）":
                judgment_basis = "エンゲージメント"
                target_engagement_rate = st.number_input("目標エンゲージメント率（%）", value=3.0, step=0.5)
                target_cpa = None
                target_roas = None
                st.info("💡 エンゲージメント率・CPEで分析します")
                
            else:  # トラフィック
                judgment_basis = "CPC重視"
                target_cpc = st.number_input("目標CPC（円）", value=30, step=5)
                target_cpa = None
                target_roas = None
                st.info("💡 CPC・CTR・直帰率で分析します")
            
            has_article_lp = st.checkbox("記事LPあり", value=False)
            offer = st.text_input("オファー内容", "", placeholder="例: 初回980円、送料無料")
    
    question = st.text_area(
        "🤔 AIへの質問（オプション）",
        placeholder="例: このまま配信を続けるべき？予算を増やすべき？",
    )
    
    if st.button("🤖 AIに分析を依頼", type="primary", use_container_width=True):
        if not perf_data:
            st.error("パフォーマンスデータがありません")
            return
        
        project = {
            "name": project_name,
            "industry_category": industry_category,
            "specific_genre": specific_genre,
            "campaign_objective": campaign_objective,
            "judgment_basis": judgment_basis,
            "has_article_lp": has_article_lp,
            "offer": offer,
        }
        
        # 目的に応じて目標値を設定
        if campaign_objective in ["コンバージョン（購入・申込）", "リード獲得（問い合わせ）"]:
            project["target_cpa"] = target_cpa
        elif campaign_objective == "ROAS最大化（売上重視）":
            project["target_roas"] = target_roas
        elif campaign_objective == "フォロワー獲得":
            project["target_follower_cost"] = target_follower_cost
        elif campaign_objective in ["ブランド認知・リーチ", "動画再生"]:
            project["target_cpm"] = target_cpm
        elif campaign_objective == "エンゲージメント（いいね・コメント）":
            project["target_engagement_rate"] = target_engagement_rate
        else:  # トラフィック
            project["target_cpc"] = target_cpc
        
        performance = {
            "spend": spend,
            "impressions": impressions,
            "clicks": clicks,
            "conversions": conversions,
            "ctr": ctr,
            "cpc": perf_data.get("cpc", 0),
            "cvr": cvr,
            "cpa": cpa,
            "roas": roas,
            "reach": perf_data.get("reach", 0),
            "cpm": perf_data.get("cpm", 0),
        }
        
        with st.spinner("🧠 AIが分析中..."):
            from knowledge_engine import IntelligentAgent
            ia = IntelligentAgent()
            result = ia.analyze_and_decide(
                project=project,
                performance=performance,
                question=question if question else None,
            )
        
        # 結果表示
        st.divider()
        st.subheader("📋 AI分析結果")
        
        judgment = result.get("comprehensive_judgment", {})
        
        if "overall_judgment" in judgment:
            oj = judgment["overall_judgment"]
            
            # ステータスに応じた色
            status = oj.get("status", "warning")
            if status == "good":
                status_class = "status-good"
                status_icon = "🟢"
            elif status == "critical":
                status_class = "status-critical"
                status_icon = "🔴"
            else:
                status_class = "status-warning"
                status_icon = "🟡"
            
            st.markdown(f"""
            ### {status_icon} 総合判断
            - **ステータス**: <span class="{status_class}">{status.upper()}</span>
            - **判定**: {oj.get('verdict')}
            - **確信度**: {oj.get('confidence')}
            - **サマリー**: {oj.get('one_line_summary')}
            """, unsafe_allow_html=True)
        
        if "deep_analysis" in judgment:
            da = judgment["deep_analysis"]
            st.subheader("🔬 深層分析")
            
            st.markdown(f"""
            **なぜこの数値になっているか:**
            > {da.get('why_this_performance')}
            
            **改善の余地:**
            > {da.get('improvement_potential')}
            """)
            
            if da.get("hidden_opportunities"):
                st.info(f"💡 隠れた機会: {da.get('hidden_opportunities')}")
            
            if da.get("risks_not_obvious"):
                st.warning(f"⚠️ 見落としがちなリスク: {da.get('risks_not_obvious')}")
        
        if "recommendations" in judgment:
            st.subheader("💡 推奨アクション")
            
            for rec in judgment["recommendations"]:
                priority = rec.get("priority", "medium")
                if priority == "immediate":
                    priority_label = "🔴 今すぐ"
                elif priority == "this_week":
                    priority_label = "🟡 今週中"
                else:
                    priority_label = "🟢 今月中"
                
                st.markdown(f"""
                <div class="recommendation-card">
                    <strong>{priority_label}</strong><br>
                    <strong>アクション:</strong> {rec.get('action')}<br>
                    <strong>期待効果:</strong> {rec.get('expected_impact')}<br>
                    <em>理由: {rec.get('reasoning', '')}</em>
                </div>
                """, unsafe_allow_html=True)
        
        if "what_not_to_do" in judgment:
            st.subheader("⚠️ やってはいけないこと")
            for item in judgment["what_not_to_do"]:
                st.error(f"❌ {item}")
        
        # 分析に使用したデータソース
        sources = result.get("data_sources_used", {})
        with st.expander("📚 分析に使用したデータソース"):
            st.json(sources)


def show_simulation(agent):
    """シミュレーションページ"""
    st.header("🔮 予測シミュレーター")
    
    # 選択中のアカウント
    selected_account = st.session_state.get("selected_account")
    
    # キャンペーン一覧を取得
    campaigns = []
    if agent.meta_initialized and selected_account:
        managers = agent._get_managers(selected_account)
        if managers:
            campaigns = managers["campaign"].get_campaigns(status_filter=["ACTIVE"])
    
    tab1, tab2 = st.tabs(["💰 予算変更シミュレーション", "🤔 What-If 分析"])
    
    with tab1:
        st.subheader("💰 予算変更シミュレーション")
        
        # キャンペーン選択
        selected_campaign = None
        current_perf = None
        
        if campaigns:
            campaign_options = {f"{c.get('name', 'Unknown')}": c for c in campaigns}
            selected_name = st.selectbox(
                "📌 シミュレーション対象のキャンペーン",
                options=list(campaign_options.keys()),
                key="sim_campaign",
            )
            selected_campaign = campaign_options[selected_name]
            
            # 現在のパフォーマンスを取得
            with st.spinner("現在のパフォーマンスを取得中..."):
                insights = managers["insights"].get_campaign_insights(
                    date_preset="last_7d",
                    campaign_ids=[selected_campaign.get("id")],
                )
                if insights:
                    current_perf = agent._aggregate_insights(insights)
            
            if current_perf:
                st.success(f"✅ 直近7日のデータを取得しました")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("現在の日消化（平均）", f"¥{current_perf.get('spend', 0) / 7:,.0f}")
                with col2:
                    st.metric("現在のCPA", f"¥{current_perf.get('cpa', 0):,.0f}")
                with col3:
                    st.metric("現在のROAS", f"{current_perf.get('roas', 0):.2f}x")
        else:
            st.warning("⚠️ キャンペーンがありません。デモデータで実行します。")
        
        st.divider()
        
        col1, col2 = st.columns(2)
        
        with col1:
            # 現在の日予算（実データがあればそれを使用）
            default_budget = int(current_perf.get("spend", 70000) / 7) if current_perf else 10000
            current_budget = st.number_input("現在の日予算（円）", value=default_budget, step=1000, min_value=100)
            new_budget = st.number_input("変更後の日予算（円）", value=int(current_budget * 1.5), step=1000, min_value=100)
            
            change_percent = ((new_budget - current_budget) / current_budget * 100) if current_budget > 0 else 0
            change_amount = abs(new_budget - current_budget)
            
            # 金額と割合の両方を考慮した警告
            if change_amount <= 5000:
                st.success(f"✅ 変更額 ¥{change_amount:,} は軽微な変更です（学習への影響は軽微）")
            elif change_percent > 20 and change_amount > 10000:
                st.warning(f"⚠️ {change_percent:.0f}%（¥{change_amount:,}）の変更は学習フェーズに影響する可能性があります")
            elif change_percent > 50:
                st.error(f"🔴 {change_percent:.0f}%の大幅な変更は学習リセットのリスクがあります")
        
        with col2:
            st.metric("変更率", f"{change_percent:+.0f}%")
            st.metric("変更額", f"¥{new_budget - current_budget:+,}")
            st.caption("💡 小額（5,000円以下）の変更は影響軽微")
        
        if st.button("🔮 シミュレーション実行", key="budget_sim"):
            with st.spinner("シミュレーション中..."):
                from knowledge_engine import Predictor
                predictor = Predictor()
                
                # 実データがあればそれを使用、なければ推定
                if current_perf:
                    performance_for_sim = {
                        "spend": current_perf.get("spend", 0) / 7,  # 日平均
                        "impressions": current_perf.get("impressions", 0) / 7,
                        "clicks": current_perf.get("clicks", 0) / 7,
                        "conversions": current_perf.get("conversions", 0) / 7,
                        "ctr": current_perf.get("ctr", 0),
                        "cvr": current_perf.get("cvr", 0),
                        "cpc": current_perf.get("cpc", 0),
                        "cpa": current_perf.get("cpa", 0),
                        "roas": current_perf.get("roas", 0),
                    }
                else:
                    performance_for_sim = {
                        "spend": current_budget,
                        "impressions": int(current_budget / 0.3),
                        "clicks": int(current_budget / 0.3 * 0.015),
                        "conversions": max(1, int(current_budget / 5000)),
                        "ctr": 1.5,
                        "cvr": 0.3,
                        "cpc": 20,
                        "cpa": 5000,
                        "roas": 3.0,
                    }
                
                result = predictor.simulate_budget_change(
                    current_performance=performance_for_sim,
                    current_budget=current_budget,
                    new_budget=new_budget,
                    context={
                        "change_amount": change_amount,
                        "is_small_change": change_amount <= 5000,
                        "campaign_name": selected_campaign.get("name") if selected_campaign else "デモ",
                    },
                )
            
            if "error" in result:
                st.error(f"エラー: {result['error']}")
            else:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("📊 予測パフォーマンス")
                    pred = result.get("predicted_performance", {})
                    st.metric("予測CPA", f"¥{pred.get('cpa', 0):,.0f}")
                    st.metric("予測ROAS", f"{pred.get('roas', 0):.2f}x")
                    st.metric("予測CV数", f"{pred.get('conversions', 0)}件")
                    st.caption(f"信頼区間: {pred.get('confidence_interval', '不明')}")
                
                with col2:
                    st.subheader("⚠️ 学習フェーズへの影響")
                    impact = result.get("learning_phase_impact", {})
                    if impact.get("will_reset"):
                        st.error(f"🔄 学習リセットの可能性: {impact.get('severity', 'unknown').upper()}")
                        st.warning(f"予想回復期間: {impact.get('expected_duration_days', '?')}日")
                    else:
                        st.success("✅ 学習フェーズへの影響は軽微です")
                
                st.subheader("💡 推奨戦略")
                st.info(result.get("optimal_strategy", "情報なし"))
                
                with st.expander("詳細データ"):
                    st.json(result)
    
    with tab2:
        st.subheader("🤔 What-If 分析")
        
        scenario = st.text_area(
            "シナリオを入力してください",
            placeholder="例: 競合が増えてCPMが30%上昇したら？\n例: クリエイティブを全部動画に変えたら？\n例: 記事LPを追加したら？",
            height=100,
        )
        
        if st.button("🔮 シナリオ分析", key="whatif"):
            if not scenario:
                st.warning("シナリオを入力してください")
            else:
                with st.spinner("分析中..."):
                    from knowledge_engine import Predictor
                    predictor = Predictor()
                    
                    result = predictor.what_if(
                        current_state={
                            "performance": {"cpm": 300, "ctr": 1.8, "cvr": 0.35, "cpa": 5000, "roas": 4.0},
                            "context": {"target_cpa": 6000, "monthly_budget": 3000000},
                        },
                        scenario=scenario,
                    )
                
                if "error" in result:
                    st.error(f"エラー: {result['error']}")
                else:
                    st.subheader("📊 分析結果")
                    
                    st.markdown(f"""
                    **シナリオ分析:**
                    > {result.get('scenario_analysis', '')}
                    """)
                    
                    outcome = result.get("likely_outcome", {})
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.markdown("**短期（1週間）**")
                        st.write(outcome.get("short_term", ""))
                    
                    with col2:
                        st.markdown("**中期（1ヶ月）**")
                        st.write(outcome.get("medium_term", ""))
                    
                    with col3:
                        st.markdown("**長期（3ヶ月+）**")
                        st.write(outcome.get("long_term", ""))
                    
                    prob = result.get("probability_of_success", 0)
                    st.metric("成功確率", f"{prob:.0%}")
                    
                    st.subheader("💡 推奨")
                    st.info(result.get("recommendation", ""))
                    
                    with st.expander("詳細データ"):
                        st.json(result)


def show_pattern_learning(agent):
    """パターン学習ページ"""
    st.header("📈 パターン学習")
    
    st.info("💡 実際のパフォーマンスデータを蓄積し、AIが成功/失敗パターンを自動学習します")
    
    from knowledge_engine import PatternLearner
    learner = PatternLearner()
    
    # 選択中のアカウント
    selected_account = st.session_state.get("selected_account")
    
    # 統計
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("蓄積履歴", f"{len(learner.history)}件")
    
    with col2:
        st.metric("学習パターン", f"{len(learner.patterns)}件")
    
    with col3:
        min_records = 5
        can_learn = len(learner.history) >= min_records
        if can_learn:
            if st.button("🔄 パターン再学習", type="primary"):
                with st.spinner("AIがパターンを抽出中..."):
                    patterns = learner.extract_patterns()
                    st.success(f"✅ {len(patterns)}件のパターンを抽出しました")
                    st.rerun()
        else:
            st.button("🔄 パターン再学習", disabled=True)
            st.caption(f"あと{min_records - len(learner.history)}件のデータが必要")
    
    st.divider()
    
    # 実データ記録セクション
    st.subheader("📥 パフォーマンスデータの記録")
    
    if agent.meta_initialized and selected_account:
        managers = agent._get_managers(selected_account)
        if managers:
            campaigns = managers["campaign"].get_campaigns(status_filter=["ACTIVE", "PAUSED"])
            
            if campaigns:
                st.write(f"**対象キャンペーン: {len(campaigns)}件**")
                
                # 一括記録
                col1, col2 = st.columns(2)
                with col1:
                    record_period = st.selectbox(
                        "記録する期間",
                        ["過去7日（日別）", "過去14日（日別）", "過去30日（日別）"],
                    )
                
                with col2:
                    if st.button("📊 選択期間のデータを一括記録", type="primary"):
                        period_map = {"過去7日（日別）": 7, "過去14日（日別）": 14, "過去30日（日別）": 30}
                        days = period_map[record_period]
                        
                        progress_bar = st.progress(0, text="データを記録中...")
                        
                        total_recorded = 0
                        for idx, campaign in enumerate(campaigns):
                            try:
                                # 日別データを取得
                                insights = managers["insights"].get_campaign_insights(
                                    date_preset=f"last_{days}d",
                                    campaign_ids=[campaign.get("id")],
                                )
                                
                                for insight in insights:
                                    date = insight.get("date_start", datetime.now().strftime("%Y-%m-%d"))
                                    perf = agent._format_performance(insight)
                                    
                                    learner.record_performance(
                                        project_id=campaign.get("id"),
                                        project_name=campaign.get("name", "Unknown"),
                                        date=date,
                                        metrics=perf,
                                        context={
                                            "account_id": selected_account,
                                            "objective": campaign.get("objective"),
                                        },
                                    )
                                    total_recorded += 1
                            except Exception as e:
                                st.warning(f"⚠️ {campaign.get('name')}: {e}")
                            
                            progress_bar.progress((idx + 1) / len(campaigns), text=f"{campaign.get('name', '')[:20]}...")
                        
                        progress_bar.empty()
                        st.success(f"✅ {total_recorded}件のデータを記録しました！")
                        st.rerun()
            else:
                st.warning("キャンペーンがありません")
    else:
        st.warning("⚠️ Meta APIに接続してアカウントを選択してください")
    
    st.divider()
    
    # 蓄積データの確認
    st.subheader("📋 蓄積済みデータ")
    
    if learner.history:
        # 直近のデータを表示
        recent_data = learner.history[-20:]  # 直近20件
        
        import pandas as pd
        df_data = []
        for h in reversed(recent_data):  # 新しい順
            m = h.get("metrics", {})
            df_data.append({
                "日付": h.get("date"),
                "キャンペーン": h.get("project_name", "")[:25],
                "消化": f"¥{m.get('spend', 0):,.0f}",
                "CV": int(m.get("conversions", 0)),
                "CPA": f"¥{m.get('cpa', 0):,.0f}" if m.get("cpa", 0) > 0 else "-",
                "ROAS": f"{m.get('roas', 0):.2f}x" if m.get("roas", 0) > 0 else "-",
                "CTR": f"{m.get('ctr', 0):.2f}%",
            })
        
        df = pd.DataFrame(df_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        st.caption(f"全{len(learner.history)}件中、直近20件を表示（新しい順）")
        
        # データ管理オプション
        with st.expander("🔧 データ管理"):
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🗑️ 全データをクリア", type="secondary"):
                    learner.history = []
                    learner.patterns = []
                    learner._save_json(learner.history_file, learner.history)
                    learner._save_json(learner.patterns_file, learner.patterns)
                    st.success("✅ 全データをクリアしました")
                    st.rerun()
            with col2:
                st.download_button(
                    "📥 データをエクスポート",
                    data=json.dumps(learner.history, ensure_ascii=False, indent=2),
                    file_name="pattern_learning_data.json",
                    mime="application/json",
                )
    else:
        st.info("📭 まだデータがありません。上の「📊 選択期間のデータを一括記録」で実データを蓄積してください。")
    
    st.divider()
    
    # パターン一覧
    st.subheader("🧠 学習済みパターン")
    
    if learner.patterns:
        for pattern in learner.patterns:
            pattern_type = pattern.get("type", "unknown")
            if pattern_type == "success":
                icon = "🟢"
            elif pattern_type == "failure":
                icon = "🔴"
            else:
                icon = "🟡"
            
            with st.expander(f"{icon} {pattern.get('name', '無名')} ({pattern.get('confidence', 0):.0%})"):
                st.markdown(f"""
                **タイプ:** {pattern_type}  
                **サンプル数:** {pattern.get('sample_count', 0)}  
                **説明:** {pattern.get('description', '')}  
                **推奨:** {pattern.get('recommendation', '')}
                """)
                
                if pattern.get("conditions"):
                    st.json(pattern.get("conditions", {}))
    else:
        st.info("📭 パターンがまだ学習されていません。データを5件以上蓄積してから「🔄 パターン再学習」を実行してください。")


def show_knowledge_base():
    """知識ベースページ"""
    st.header("📚 知識ベース")
    
    st.info("""
    💡 **知識ベースの役割**: AIが広告運用の判断をする際に参照する情報源です。
    各カテゴリの情報が蓄積されるほど、AIの判断精度が向上します。
    """)
    
    from knowledge_engine import VectorStore, KnowledgeBase
    from knowledge_engine.document_collector import DocumentCollector
    
    vs = VectorStore()
    kb = KnowledgeBase()
    
    # 統計
    stats = vs.get_collection_stats()
    
    st.subheader("📊 コレクション統計")
    
    cols = st.columns(len(stats))
    for i, (name, count) in enumerate(stats.items()):
        with cols[i]:
            display_name = {
                "meta_official_docs": "Meta公式",
                "industry_knowledge": "業界知見",
                "operation_tips": "運用Tips",
                "performance_patterns": "パフォーマンス",
                "case_studies": "事例",
            }.get(name, name)
            st.metric(display_name, f"{count}件")
    
    st.divider()
    
    # カテゴリ別の説明と管理
    st.subheader("📁 カテゴリ別管理")
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🏢 Meta公式", "💡 業界知見", "📝 運用Tips", "📊 パフォーマンス", "📚 事例"])
    
    with tab1:
        st.markdown("""
        ### 🏢 Meta公式ドキュメント
        
        **内容**: Meta Business Help、Marketing API ドキュメントからの公式情報
        
        **含まれる情報**:
        - 学習期間のベストプラクティス
        - 予算設定のルール
        - 入札戦略の選び方
        - Advantage+ キャンペーン
        - オーディエンス設定
        - クリエイティブガイドライン
        - その他多数...
        """)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Meta公式情報を更新/追加", type="primary"):
                with st.spinner("Meta公式情報を収集中..."):
                    collector = DocumentCollector()
                    docs = collector.collect_meta_marketing_api_docs()
                    
                    # VectorStoreに追加
                    for doc in docs:
                        vs.add_document(
                            collection_name="meta_official_docs",
                            document=doc["content"],
                            metadata={
                                "title": doc["title"],
                                "category": doc["category"],
                                "source": doc["source"],
                            },
                            doc_id=f"meta_{doc['title'][:30]}",
                        )
                    
                    st.success(f"✅ {len(docs)}件のMeta公式情報を追加/更新しました")
                    st.rerun()
        
        with col2:
            st.caption(f"現在: {stats.get('meta_official_docs', 0)}件")
    
    with tab2:
        st.markdown("""
        ### 💡 業界知見
        
        **内容**: 運用者の間で知られている通説・ベストプラクティス
        
        **含まれる情報**:
        - 20%ルール（予算変更）
        - CPAからの逆算思考
        - クリエイティブの訴求軸
        - 記事LPの効果と使い方
        - キャンペーン構造のパターン
        
        **追加方法**: 
        - 参考になるリンクやノウハウをNotionに貯めていく
        - または下の「運用Tips」から追加
        """)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 業界知見を更新/追加"):
                with st.spinner("業界知見を収集中..."):
                    collector = DocumentCollector()
                    docs = collector.collect_industry_knowledge()
                    
                    for doc in docs:
                        vs.add_document(
                            collection_name="industry_knowledge",
                            document=doc["content"],
                            metadata={
                                "title": doc["title"],
                                "category": doc["category"],
                                "source": doc["source"],
                            },
                            doc_id=f"industry_{doc['title'][:30]}",
                        )
                    
                    st.success(f"✅ {len(docs)}件の業界知見を追加/更新しました")
                    st.rerun()
        
        with col2:
            st.caption(f"現在: {stats.get('industry_knowledge', 0)}件")
    
    with tab3:
        st.markdown("""
        ### 📝 運用Tips
        
        **内容**: あなた自身が蓄積する運用ノウハウ
        
        **追加すべき情報**:
        - 「この案件ではこうやったらうまくいった」
        - 「このジャンルはCTRが低くても回る」
        - 「記事LP入れたらCVR上がった」
        - 特定の業界での成功パターン
        
        **追加方法**: 下のフォームから追加
        """)
        
        with st.form("add_tip"):
            tip_title = st.text_input("タイトル", placeholder="例: ジュエリーECは動画より静止画が効く")
            tip_content = st.text_area("内容", placeholder="具体的なノウハウを記載...", height=150)
            tip_category = st.selectbox("カテゴリ", ["入札", "クリエイティブ", "ターゲティング", "予算", "業界特有", "その他"])
            
            if st.form_submit_button("➕ Tipsを追加"):
                if tip_title and tip_content:
                    success = kb.add_operation_tip(
                        title=tip_title,
                        content=tip_content,
                        category=tip_category,
                    )
                    if success:
                        st.success("✅ 運用Tipsを追加しました")
                        st.rerun()
                    else:
                        st.error("追加に失敗しました")
                else:
                    st.warning("タイトルと内容を入力してください")
        
        st.caption(f"現在: {stats.get('operation_tips', 0)}件")
    
    with tab4:
        st.markdown("""
        ### 📊 パフォーマンスパターン
        
        **内容**: 過去の広告パフォーマンスから学習したパターン
        
        **蓄積方法**: 
        1. 「📈 パターン学習」ページで実データを記録
        2. 「パターン再学習」を実行
        3. AIが成功/失敗パターンを自動抽出
        
        **活用方法**:
        - キャンペーン分析時に、AIが類似パターンを参照
        - 「この数値は過去の成功パターンに近い」などの判断材料に
        """)
        
        st.caption(f"現在: {stats.get('performance_patterns', 0)}件")
        st.info("💡 「📈 パターン学習」ページから蓄積されます")
    
    with tab5:
        st.markdown("""
        ### 📚 事例
        
        **内容**: 具体的な成功/失敗事例
        
        **活用方法**:
        - 新規案件で類似事例を参照
        - 「同じ業界で過去にこういう結果だった」という判断材料
        """)
        
        st.caption(f"現在: {stats.get('case_studies', 0)}件")
        
        # 事例追加フォーム
        st.subheader("➕ 事例を追加")
        
        with st.form("add_case_study"):
            col1, col2 = st.columns(2)
            
            with col1:
                case_title = st.text_input("事例タイトル", placeholder="例: ファッションEC × リール広告で成功")
                case_industry = st.selectbox(
                    "業界",
                    ["EC・物販", "美容・コスメ", "健康食品", "ファッション", "教育", "BtoB", "金融", "その他"],
                )
                case_result = st.radio("結果", ["成功", "失敗", "学び"], horizontal=True)
            
            with col2:
                case_spend = st.number_input("総消化（円）", value=100000, step=10000)
                case_period = st.text_input("運用期間", placeholder="例: 2024年10月〜12月（3ヶ月）")
                case_metrics = st.text_input("主要指標", placeholder="例: CPA 3,000円、ROAS 4.5x")
            
            case_summary = st.text_area(
                "概要・何をしたか",
                placeholder="例: リール広告に注力し、UGC風クリエイティブでCTR改善...",
                height=100,
            )
            
            case_learnings = st.text_area(
                "学び・気づき",
                placeholder="例: このジャンルは動画より静止画が効く傾向...",
                height=100,
            )
            
            if st.form_submit_button("📚 事例を保存", type="primary"):
                if case_title and case_summary:
                    case_content = f"""
## {case_title}

**業界**: {case_industry}
**結果**: {case_result}
**消化**: ¥{case_spend:,}
**期間**: {case_period}
**主要指標**: {case_metrics}

### 概要
{case_summary}

### 学び・気づき
{case_learnings}
"""
                    
                    try:
                        vs.add_document(
                            collection_name="case_studies",
                            document=case_content,
                            metadata={
                                "title": case_title,
                                "industry": case_industry,
                                "result": case_result,
                                "spend": case_spend,
                            },
                            doc_id=f"case_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                        )
                        st.success("✅ 事例を保存しました！")
                        st.rerun()
                    except Exception as e:
                        st.error(f"保存エラー: {e}")
                else:
                    st.warning("タイトルと概要を入力してください")
        
        # 保存済み事例一覧
        if stats.get("case_studies", 0) > 0:
            st.subheader("📋 保存済み事例")
            case_results = vs.get_all("case_studies", limit=50)
            
            for case in case_results:
                meta = case.get("metadata", {})
                result_icon = {"成功": "🟢", "失敗": "🔴", "学び": "🟡"}.get(meta.get("result", ""), "📄")
                
                with st.expander(f"{result_icon} {meta.get('title', '無題')} ({meta.get('industry', '')})"):
                    st.markdown(case.get("document", ""))
    
    st.divider()
    
    # 検索
    st.subheader("🔍 知識検索")
    
    query = st.text_input("検索キーワード", placeholder="例: 予算を増やす方法、CTR改善、学習期間")
    
    if query:
        results = kb.search_knowledge(query, n_results=8)
        
        if results:
            for r in results:
                collection = r.get('collection', 'unknown')
                icon = {
                    "meta_official_docs": "🏢",
                    "industry_knowledge": "💡",
                    "operation_tips": "📝",
                    "performance_patterns": "📊",
                    "case_studies": "📚",
                }.get(collection, "📄")
                
                with st.expander(f"{icon} {r.get('metadata', {}).get('title', '無題')}"):
                    st.markdown(r.get("document", ""))
                    st.caption(f"カテゴリ: {r.get('metadata', {}).get('category', 'unknown')} | ソース: {collection}")
        else:
            st.info("検索結果がありません")


def show_automation(agent):
    """自動運用ページ"""
    st.header("🤖 自動運用")
    
    st.info("""
    💡 **自動運用システム**
    
    定期的にパフォーマンスをチェックし、異常やチャンスを検知してSlackに通知します。
    """)
    
    # 選択中のアカウント
    selected_account = st.session_state.get("selected_account")
    
    # 監視エンジン初期化
    try:
        from automation.monitor import PerformanceMonitor
        from automation.notifier import SlackNotifier
        from automation.scheduler import AutomationScheduler
        
        monitor = PerformanceMonitor(integrated_agent=agent)
        notifier = SlackNotifier()
        
    except Exception as e:
        st.error(f"自動運用モジュールの読み込みエラー: {e}")
        return
    
    # ActionExecutor初期化
    try:
        from automation.actions import ActionExecutor
        executor = ActionExecutor(integrated_agent=agent, mode="approval_required")
    except Exception as e:
        executor = None
        logger.warning(f"ActionExecutor初期化エラー: {e}")
    
    # タブ
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 手動チェック", "✅ 承認キュー", "🎨 入稿提案", "⚙️ 設定", "📋 履歴"])
    
    with tab1:
        st.subheader("📊 手動パフォーマンスチェック")
        
        if not agent.meta_initialized:
            st.warning("⚠️ Meta APIに接続してください")
        elif not selected_account:
            st.warning("⚠️ アカウントを選択してください")
        else:
            st.write(f"**対象アカウント:** {selected_account}")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🔍 今すぐチェック", type="primary"):
                    with st.spinner("パフォーマンスをチェック中..."):
                        results = monitor.check_all_accounts([selected_account])
                        
                        # 結果を保存
                        st.session_state["last_check_results"] = results
                    
                    st.success("✅ チェック完了！")
            
            with col2:
                if st.button("📤 Slack接続テスト"):
                    with st.spinner("Slack接続テスト中..."):
                        if notifier.test_connection():
                            st.success("✅ Slack接続成功！")
                        else:
                            st.error("❌ Slack接続失敗。Webhook URLを確認してください。")
            
            # 結果表示
            if "last_check_results" in st.session_state:
                results = st.session_state["last_check_results"]
                summary = results.get("summary", {})
                
                st.divider()
                
                # サマリー
                status = summary.get("status", "unknown")
                status_colors = {"critical": "🔴", "warning": "🟡", "opportunity": "🟢", "normal": "✅"}
                
                st.markdown(f"### {status_colors.get(status, '⚪')} {summary.get('status_message', '')}")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("アラート", f"{summary.get('total_alerts', 0)}件")
                with col2:
                    st.metric("緊急アラート", f"{summary.get('high_alerts', 0)}件")
                with col3:
                    st.metric("拡大チャンス", f"{summary.get('total_opportunities', 0)}件")
                
                # アラート詳細
                alerts = results.get("alerts", [])
                if alerts:
                    st.subheader("🚨 アラート")
                    for alert in alerts:
                        severity = alert.get("severity", "medium")
                        icon = "🔴" if severity == "high" else "🟡"
                        objective = alert.get("objective", "")
                        
                        with st.expander(f"{icon} {alert.get('campaign_name', '')} [{objective}]"):
                            st.write(f"**サマリー:** {alert.get('message', '')}")
                            
                            # 問題点
                            issues = alert.get("issues", [])
                            if issues:
                                st.markdown("**📋 問題点:**")
                                for issue in issues:
                                    sev_icon = "🔴" if issue.get("severity") == "critical" else "🟡"
                                    st.markdown(f"- {sev_icon} {issue.get('message', '')}")
                                    if issue.get("note"):
                                        st.caption(f"   ↳ {issue.get('note')}")
                            
                            # 比較情報
                            comparisons = alert.get("comparisons", [])
                            if comparisons:
                                st.markdown("**📊 比較データ:**")
                                for comp in comparisons:
                                    st.markdown(f"- {comp}")
                            
                            # 詳細データ
                            with st.expander("詳細データ"):
                                data = alert.get("data", {})
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.markdown("**今日:**")
                                    today = data.get("today", {})
                                    st.write(f"消化: ¥{today.get('spend', 0):,.0f}")
                                    st.write(f"CPA: ¥{today.get('cpa', 0):,.0f}")
                                    st.write(f"ROAS: {today.get('roas', 0):.2f}x")
                                    st.write(f"CTR: {today.get('ctr', 0):.2f}%")
                                with col2:
                                    st.markdown("**昨日:**")
                                    yesterday = data.get("yesterday", {})
                                    st.write(f"消化: ¥{yesterday.get('spend', 0):,.0f}")
                                    st.write(f"CPA: ¥{yesterday.get('cpa', 0):,.0f}")
                                    st.write(f"ROAS: {yesterday.get('roas', 0):.2f}x")
                                    st.write(f"CTR: {yesterday.get('ctr', 0):.2f}%")
                                
                                budget_status = data.get("budget_status", {})
                                if budget_status:
                                    st.markdown(f"**予算状況:** {budget_status.get('message', '')}")
                
                # チャンス詳細
                opportunities = results.get("opportunities", [])
                if opportunities:
                    st.subheader("🚀 拡大チャンス")
                    for opp in opportunities:
                        objective = opp.get("objective", "")
                        with st.expander(f"🟢 {opp.get('campaign_name', '')} [{objective}]"):
                            st.write(f"**サマリー:** {opp.get('message', '')}")
                            
                            # ポジティブ要素
                            positives = opp.get("positives", [])
                            if positives:
                                st.markdown("**✨ 好調ポイント:**")
                                for pos in positives:
                                    st.markdown(f"- 🟢 {pos}")
                            
                            if opp.get("suggested_action"):
                                st.success(f"💡 **推奨アクション:** {opp.get('suggested_action')}")
                
                # 推奨アクション
                recommendations = []
                for account_data in results.get("accounts", {}).values():
                    if isinstance(account_data, dict):
                        recommendations.extend(account_data.get("recommendations", []))
                
                if recommendations:
                    st.subheader("💡 AIの推奨アクション")
                    
                    # キャンペーン名→IDのマッピングを作成
                    campaign_id_map = {}
                    for account_data in results.get("accounts", {}).values():
                        if isinstance(account_data, dict):
                            for c in account_data.get("campaigns", []):
                                campaign_id_map[c.get("name")] = c.get("id")
                    
                    for i, rec in enumerate(recommendations, 1):
                        priority = rec.get("priority", "medium")
                        icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(priority, "⚪")
                        
                        # 新形式対応
                        campaign_name = rec.get("campaign_name") or rec.get("campaign", "")
                        action_display = rec.get("action_display") or rec.get("action", "")
                        action_type = rec.get("action_type", "none")
                        params = rec.get("params", {})
                        
                        st.markdown(f"### {icon} {i}. {action_display}")
                        if campaign_name:
                            st.caption(f"対象: {campaign_name}")
                        
                        col1, col2, col3 = st.columns([2, 2, 1])
                        with col1:
                            st.markdown(f"**理由:** {rec.get('reason', '')}")
                            if rec.get("risk"):
                                st.warning(f"⚠️ {rec.get('risk')}")
                        with col2:
                            if rec.get("expected_impact"):
                                st.info(f"📈 {rec.get('expected_impact')}")
                        
                        # ★ 即実行ボタン
                        with col3:
                            if action_type != "none" and executor:
                                campaign_id = campaign_id_map.get(campaign_name)
                                
                                if campaign_id and action_type in ["budget_increase", "budget_decrease"]:
                                    if st.button(f"🚀 即実行", key=f"exec_rec_{i}", type="primary"):
                                        with st.spinner("実行中..."):
                                            # 予算変更を実行
                                            current = params.get("current_value", 0)
                                            new = params.get("new_value", 0)
                                            
                                            result = executor.execute_budget_change_direct(
                                                campaign_id=campaign_id,
                                                new_budget=new,
                                                account_id=selected_account,
                                            )
                                            
                                            if result.get("success"):
                                                st.success(f"✅ 予算を¥{current:,}→¥{new:,}に変更しました！")
                                            else:
                                                st.error(f"❌ {result.get('error', '実行失敗')}")
                                
                                elif campaign_id and action_type == "pause":
                                    if st.button(f"⏸️ 停止", key=f"pause_rec_{i}"):
                                        result = executor.execute_status_change_direct(
                                            campaign_id=campaign_id,
                                            new_status="PAUSED",
                                            account_id=selected_account,
                                        )
                                        if result.get("success"):
                                            st.success("✅ 停止しました")
                                        else:
                                            st.error(f"❌ {result.get('error')}")
                            else:
                                st.caption("様子見")
                        
                        st.divider()
                
                # Slack送信ボタン
                st.divider()
                if st.button("📤 この結果をSlackに送信"):
                    with st.spinner("送信中..."):
                        if notifier.send_daily_report(results):
                            st.success("✅ Slackに送信しました！")
                        else:
                            st.error("❌ 送信失敗")
    
    with tab2:
        st.subheader("✅ 承認待ちアクション")
        
        st.info("💡 AIが提案したアクションを確認し、承認または却下できます。承認するとMeta広告に反映されます。")
        
        if executor:
            pending_actions = executor.get_pending_actions()
            
            if pending_actions:
                st.write(f"**承認待ち: {len(pending_actions)}件**")
                
                for action_item in pending_actions:
                    action = action_item.get("action", {})
                    action_id = action_item.get("id")
                    created_at = action_item.get("created_at", "")[:16]
                    
                    action_type = action.get("type", "unknown")
                    campaign_name = action.get("campaign_name", "Unknown")
                    reason = action.get("reason", "")
                    params = action.get("params", {})
                    
                    # アイコン
                    type_icon = {
                        "budget_change": "💰",
                        "status_change": "⚡",
                        "pause": "⏸️",
                        "resume": "▶️",
                    }.get(action_type, "📌")
                    
                    with st.expander(f"{type_icon} {campaign_name} - {action_type}", expanded=True):
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            st.write(f"**ID:** `{action_id}`")
                            st.write(f"**作成日時:** {created_at}")
                            st.write(f"**理由:** {reason}")
                            
                            if action_type == "budget_change":
                                current = params.get("current_budget", 0)
                                new = params.get("new_budget", 0)
                                change = params.get("change_percent", 0)
                                st.write(f"**変更:** ¥{current:,.0f} → ¥{new:,.0f} ({change:+.0f}%)")
                            
                            elif action_type == "status_change":
                                new_status = params.get("new_status", "")
                                st.write(f"**新ステータス:** {new_status}")
                        
                        with col2:
                            if st.button("✅ 承認", key=f"approve_{action_id}", type="primary"):
                                with st.spinner("実行中..."):
                                    result = executor.approve_action(action_id)
                                    if result.get("success"):
                                        st.success("✅ 実行完了！")
                                        notifier.send_action_executed(action, result)
                                    else:
                                        st.error(f"❌ {result.get('message')}")
                                st.rerun()
                            
                            if st.button("❌ 却下", key=f"reject_{action_id}"):
                                executor.reject_action(action_id)
                                st.warning("却下しました")
                                st.rerun()
            else:
                st.info("📭 承認待ちのアクションはありません")
            
            st.divider()
            
            # 手動でアクションを提案
            st.subheader("➕ アクションを手動で追加")
            
            if agent.meta_initialized and selected_account:
                managers = agent._get_managers(selected_account)
                if managers:
                    campaigns = managers["campaign"].get_campaigns(status_filter=["ACTIVE", "PAUSED"])
                    
                    if campaigns:
                        with st.form("manual_action"):
                            action_type = st.selectbox(
                                "アクション種類",
                                ["予算変更", "配信ON", "配信OFF"],
                            )
                            
                            campaign_options = {c["name"]: c for c in campaigns}
                            selected_campaign_name = st.selectbox(
                                "対象キャンペーン",
                                list(campaign_options.keys()),
                            )
                            selected_campaign = campaign_options[selected_campaign_name]
                            
                            if action_type == "予算変更":
                                current_budget = selected_campaign.get("daily_budget", 0) or 0
                                st.write(f"現在の日予算: ¥{current_budget:,.0f}")
                                new_budget = st.number_input("新しい日予算（円）", value=int(current_budget), step=1000)
                            
                            reason = st.text_input("理由", placeholder="例: ROAS好調のため増額")
                            
                            if st.form_submit_button("📝 アクションを提案"):
                                if action_type == "予算変更":
                                    action_id = executor.create_budget_action(
                                        campaign_id=selected_campaign["id"],
                                        campaign_name=selected_campaign["name"],
                                        account_id=selected_account,
                                        current_budget=current_budget,
                                        new_budget=new_budget,
                                        reason=reason,
                                    )
                                elif action_type == "配信ON":
                                    action_id = executor.create_status_action(
                                        campaign_id=selected_campaign["id"],
                                        campaign_name=selected_campaign["name"],
                                        account_id=selected_account,
                                        new_status="ACTIVE",
                                        reason=reason,
                                    )
                                else:  # 配信OFF
                                    action_id = executor.create_status_action(
                                        campaign_id=selected_campaign["id"],
                                        campaign_name=selected_campaign["name"],
                                        account_id=selected_account,
                                        new_status="PAUSED",
                                        reason=reason,
                                    )
                                
                                st.success(f"✅ アクション提案完了！ID: {action_id}")
                                st.rerun()
        else:
            st.warning("ActionExecutorが初期化されていません")
    
    # =====================================================
    # 入稿提案タブ
    # =====================================================
    with tab3:
        st.subheader("🎨 AI入稿提案")
        
        st.info("""
        💡 **自動入稿提案機能**
        
        AIがパフォーマンスを分析し、以下を自動提案します：
        - 好調キャンペーンへのクリエイティブ追加
        - 好調広告セットの複製
        - ASCキャンペーンの強化
        """)
        
        # 監視結果から入稿提案を生成
        if st.button("🔍 入稿提案を生成", type="primary"):
            if not agent.meta_initialized or not selected_account:
                st.warning("Meta APIに接続し、アカウントを選択してください")
            else:
                with st.spinner("分析中..."):
                    try:
                        from automation.auto_creative import AutoCreativeProposer
                        from automation.monitor import PerformanceMonitor
                        
                        # パフォーマンス監視を実行
                        monitor = PerformanceMonitor(integrated_agent=agent)
                        monitor_results = monitor.check_account(selected_account)
                        
                        # 入稿提案を生成
                        proposer = AutoCreativeProposer(
                            integrated_agent=agent,
                            action_executor=executor,
                        )
                        proposals = proposer.analyze_and_propose(selected_account, monitor_results)
                        
                        st.session_state["creative_proposals"] = proposals
                        
                        if proposals:
                            st.success(f"✅ {len(proposals)}件の入稿提案を生成しました")
                        else:
                            st.info("現在、入稿提案はありません（好調なキャンペーンがないか、既に最適化されています）")
                    
                    except Exception as e:
                        st.error(f"分析エラー: {e}")
        
        # 提案一覧を表示
        proposals = st.session_state.get("creative_proposals", [])
        
        if proposals:
            st.divider()
            st.markdown("### 📋 生成された提案")
            
            for i, proposal in enumerate(proposals):
                priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(proposal.get("priority", ""), "⚪")
                
                with st.expander(
                    f"{priority_icon} {proposal.get('campaign_name', 'Unknown')} - {proposal.get('type', '')}",
                    expanded=i == 0,
                ):
                    st.write(f"**理由:** {proposal.get('reason', '')}")
                    st.write(f"**期待効果:** {proposal.get('expected_impact', '')}")
                    
                    # 詳細
                    details = proposal.get("details", {})
                    if details:
                        st.json(details)
                    
                    # 必要な入力
                    required = proposal.get("required_inputs", [])
                    if required:
                        st.markdown("**必要な入力:**")
                        for req in required:
                            st.write(f"  • {req}")
                    
                    # アクションボタン
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ 承認キューに追加", key=f"approve_proposal_{i}"):
                            if executor:
                                action_id = proposer.create_proposal_action(proposal)
                                if action_id:
                                    st.success(f"✅ 承認キューに追加しました: {action_id}")
                                else:
                                    st.error("追加に失敗しました")
                            else:
                                st.error("ActionExecutorが未設定です")
                    with col2:
                        if st.button("❌ スキップ", key=f"skip_proposal_{i}"):
                            st.info("この提案をスキップしました")
        
        st.divider()
        
        # 手動入稿リンク
        st.markdown("""
        ### 📤 手動入稿
        
        手動でクリエイティブを入稿する場合は、サイドバーから「📤 入稿」ページへ移動してください。
        """)
    
    # =====================================================
    # 設定タブ
    # =====================================================
    with tab4:
        st.subheader("⚙️ 自動運用設定")
        
        # ========================================
        # 監視対象アカウント設定
        # ========================================
        st.markdown("### 🏢 監視対象アカウント")
        
        st.info("💡 監視したいアカウントにチェックを入れてください。チェックしたアカウントのみ定期監視＆Slack通知の対象になります。")
        
        try:
            from automation.config_manager import get_config_manager
            config_manager = get_config_manager()
            
            # 現在の設定を取得
            enabled_accounts = config_manager.get_enabled_accounts()
            enabled_ids = [a["id"] for a in enabled_accounts]
            
            # Meta APIからアカウント一覧を取得
            if agent.meta_initialized and agent.meta_auth:
                all_accounts = agent.meta_auth.get_ad_accounts()
                
                if all_accounts:
                    st.markdown("**利用可能なアカウント:**")
                    
                    # チェックボックスで選択
                    updated_accounts = []
                    for acc in all_accounts:
                        acc_id = acc.get("id", "")
                        acc_name = acc.get("name", "Unknown")
                        
                        # 既存の設定があればそれを使用
                        is_enabled = acc_id in enabled_ids
                        
                        checked = st.checkbox(
                            f"📊 {acc_name}",
                            value=is_enabled,
                            key=f"monitor_acc_{acc_id}",
                            help=f"ID: {acc_id}",
                        )
                        
                        if checked:
                            updated_accounts.append({
                                "id": acc_id,
                                "name": acc_name,
                                "enabled": True,
                            })
                    
                    # 保存ボタン
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        if st.button("💾 保存", key="save_monitor_accounts", type="primary"):
                            config_manager.set_enabled_accounts(updated_accounts)
                            st.success(f"✅ {len(updated_accounts)}件のアカウントを監視対象に設定しました")
                            st.rerun()
                    with col2:
                        st.caption(f"現在の監視対象: {len([a for a in enabled_accounts if a.get('enabled')])}件")
                else:
                    st.warning("アカウントが見つかりません")
            else:
                st.warning("Meta APIに接続してください")
                
                # 手動入力フォーム
                st.markdown("**または手動でアカウントIDを追加:**")
                with st.form("add_manual_account"):
                    manual_id = st.text_input("アカウントID", placeholder="act_123456789")
                    manual_name = st.text_input("アカウント名", placeholder="ロジリカ広告アカウント")
                    
                    if st.form_submit_button("➕ 追加"):
                        if manual_id and manual_name:
                            config_manager.add_account(manual_id, manual_name, enabled=True)
                            st.success(f"✅ {manual_name} を追加しました")
                            st.rerun()
            
            # 現在の監視対象一覧
            if enabled_accounts:
                with st.expander("📋 現在の監視対象一覧", expanded=False):
                    for acc in enabled_accounts:
                        status = "✅" if acc.get("enabled", True) else "⏸️"
                        st.write(f"{status} {acc.get('name')} (`{acc.get('id')}`)")
        
        except Exception as e:
            st.error(f"設定読み込みエラー: {e}")
        
        st.divider()
        
        st.markdown("""
        ### Slack Webhook URL
        
        1. [Slack App作成ページ](https://api.slack.com/apps) にアクセス
        2. 「Create New App」→「From scratch」
        3. 「Incoming Webhooks」を有効化
        4. 「Add New Webhook to Workspace」でチャンネルを選択
        5. Webhook URLをコピー
        """)
        
        import config
        current_webhook = getattr(config, "SLACK_WEBHOOK_URL", "")
        
        if current_webhook:
            st.success("✅ Slack Webhook URL が設定されています")
            st.code(current_webhook[:50] + "..." if len(current_webhook) > 50 else current_webhook)
        else:
            st.warning("⚠️ Slack Webhook URL が未設定です")
            st.info("`.env` ファイルに `SLACK_WEBHOOK_URL=https://hooks.slack.com/...` を追加してください")
        
        st.divider()
        
        # 通知カスタマイズ
        st.markdown("### 🔔 通知設定")
        
        try:
            notifications = config_manager.get_notifications()
            
            col1, col2 = st.columns(2)
            
            with col1:
                send_hourly = st.checkbox(
                    "毎時アラート通知",
                    value=notifications.get("send_hourly_alerts", True),
                    help="毎時チェックでアラートがあればSlack通知",
                )
                
                send_daily = st.checkbox(
                    "日次レポート通知",
                    value=notifications.get("send_daily_report", True),
                    help="毎朝9時に日次レポートをSlack送信",
                )
            
            with col2:
                severity_options = ["low", "medium", "high"]
                current_severity = notifications.get("alert_severity_threshold", "medium")
                severity_index = severity_options.index(current_severity) if current_severity in severity_options else 1
                
                severity_threshold = st.selectbox(
                    "通知するアラートレベル",
                    severity_options,
                    index=severity_index,
                    format_func=lambda x: {"low": "🟢 低以上（すべて）", "medium": "🟡 中以上", "high": "🔴 高のみ"}.get(x, x),
                    help="このレベル以上のアラートのみSlack通知",
                )
            
            if st.button("💾 通知設定を保存", key="save_notifications"):
                config_manager.set_notifications(
                    send_hourly_alerts=send_hourly,
                    send_daily_report=send_daily,
                    alert_severity_threshold=severity_threshold,
                )
                st.success("✅ 通知設定を保存しました")
        
        except Exception as e:
            st.error(f"通知設定エラー: {e}")
        
        st.divider()
        
        st.markdown("### ⏰ スケジュール設定")
        
        # 監視プロセスの状態確認
        import subprocess
        import os
        
        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        pid_file = os.path.join(project_dir, ".monitor.pid")
        
        is_running = False
        current_pid = None
        
        if os.path.exists(pid_file):
            try:
                with open(pid_file, "r") as f:
                    current_pid = int(f.read().strip())
                # プロセスが存在するか確認
                os.kill(current_pid, 0)
                is_running = True
            except (ProcessLookupError, ValueError, PermissionError):
                is_running = False
                if os.path.exists(pid_file):
                    os.remove(pid_file)
        
        # ステータス表示
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            if is_running:
                st.success(f"🟢 監視プロセス実行中 (PID: {current_pid})")
            else:
                st.warning("🔴 監視プロセス停止中")
        
        with col2:
            if not is_running:
                if st.button("▶️ 開始", type="primary", key="start_monitor"):
                    try:
                        # バックグラウンドで開始
                        script_path = os.path.join(project_dir, "scripts", "setup_background.sh")
                        result = subprocess.run(
                            [script_path, "start"],
                            capture_output=True,
                            text=True,
                            cwd=project_dir,
                        )
                        if result.returncode == 0:
                            st.success("✅ 監視を開始しました！")
                        else:
                            st.error(f"エラー: {result.stderr}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"開始エラー: {e}")
            else:
                if st.button("⏹️ 停止", key="stop_monitor"):
                    try:
                        os.kill(current_pid, 15)  # SIGTERM
                        if os.path.exists(pid_file):
                            os.remove(pid_file)
                        st.success("✅ 監視を停止しました")
                        st.rerun()
                    except Exception as e:
                        st.error(f"停止エラー: {e}")
        
        with col3:
            if st.button("🔄 状態更新", key="refresh_monitor"):
                st.rerun()
        
        # ログ表示
        log_file = os.path.join(project_dir, "logs", "monitor.log")
        if os.path.exists(log_file):
            with st.expander("📋 最新ログ（最後の20行）", expanded=False):
                try:
                    with open(log_file, "r") as f:
                        lines = f.readlines()
                        st.code("".join(lines[-20:]), language="text")
                except Exception as e:
                    st.error(f"ログ読み込みエラー: {e}")
        
        st.divider()
        
        st.markdown("""
        **ターミナルからの操作:**
        
        ```bash
        # 開始
        ./scripts/setup_background.sh start
        
        # 停止
        ./scripts/setup_background.sh stop
        
        # 状態確認
        ./scripts/setup_background.sh status
        
        # ログ監視
        ./scripts/setup_background.sh follow
        ```
        """)
        
        st.info("""
        💡 **Macを閉じても動かしたい場合**
        
        - Heroku / Railway / Render などのクラウドサービスにデプロイ
        - または常時起動のサーバー（VPS）で実行
        """)
        
        st.divider()
        
        # ========================================
        # 目標値設定セクション
        # ========================================
        st.subheader("🎯 目標値設定")
        
        st.info("キャンペーンごとの目標値（CPF、CPA、ROAS等）を設定します。フェーズに応じて変更してください。")
        
        try:
            from automation.targets import get_target_manager
            target_manager = get_target_manager()
            
            # デフォルト目標値の設定
            st.markdown("#### 📌 デフォルト目標値")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**トラフィック/フォロー獲得**")
                defaults_traffic = target_manager.get_defaults().get("traffic", {})
                
                new_cpf = st.number_input(
                    "目標CPF（フォロー単価）",
                    value=defaults_traffic.get("target_cpf", 50),
                    step=10,
                    help="フォロー1件あたりの目標コスト（円）",
                )
                new_cpf_warning = st.number_input(
                    "CPF注意ライン",
                    value=defaults_traffic.get("cpf_warning", 100),
                    step=10,
                    help="この値を超えると注意アラート",
                )
                new_cpf_critical = st.number_input(
                    "CPF危険ライン",
                    value=defaults_traffic.get("cpf_critical", 200),
                    step=10,
                    help="この値を超えると緊急アラート",
                )
                
                if st.button("💾 トラフィック目標を保存", key="save_traffic"):
                    target_manager.set_default_targets("traffic", {
                        "target_cpf": new_cpf,
                        "cpf_warning": new_cpf_warning,
                        "cpf_critical": new_cpf_critical,
                    })
                    st.success("✅ 保存しました！")
                    st.rerun()
            
            with col2:
                st.markdown("**売上/コンバージョン**")
                defaults_sales = target_manager.get_defaults().get("sales", {})
                
                new_cpa = st.number_input(
                    "目標CPA",
                    value=defaults_sales.get("target_cpa", 5000),
                    step=500,
                    help="CV1件あたりの目標コスト（円）",
                )
                new_roas = st.number_input(
                    "目標ROAS",
                    value=float(defaults_sales.get("target_roas", 3.0)),
                    step=0.5,
                    help="目標広告費用対効果",
                )
                
                if st.button("💾 売上目標を保存", key="save_sales"):
                    target_manager.set_default_targets("sales", {
                        "target_cpa": new_cpa,
                        "target_roas": new_roas,
                    })
                    st.success("✅ 保存しました！")
                    st.rerun()
            
            # キャンペーン個別の目標値
            st.divider()
            st.markdown("#### 📋 キャンペーン個別設定")
            
            campaign_targets = target_manager.get_all_campaign_targets()
            
            if campaign_targets:
                for cid, ctarget in campaign_targets.items():
                    with st.expander(f"📌 {ctarget.get('name', cid)}", expanded=False):
                        st.json(ctarget)
                        if st.button("🗑️ 削除（デフォルトに戻す）", key=f"del_{cid}"):
                            target_manager.remove_campaign_targets(cid)
                            st.success("削除しました")
                            st.rerun()
            else:
                st.caption("キャンペーン個別の設定はありません（全てデフォルト値を使用）")
            
            # キャンペーン個別設定の追加
            if agent.meta_initialized and selected_account:
                managers = agent._get_managers(selected_account)
                if managers:
                    campaigns = managers["campaign"].get_campaigns(status_filter=["ACTIVE", "PAUSED"])
                    
                    if campaigns:
                        st.markdown("##### ➕ キャンペーン個別目標を追加")
                        
                        with st.form("add_campaign_target"):
                            campaign_options = {c["name"]: c for c in campaigns}
                            sel_name = st.selectbox("キャンペーン", list(campaign_options.keys()))
                            sel_campaign = campaign_options[sel_name]
                            
                            target_type = st.radio("目標タイプ", ["CPF（フォロー単価）", "CPA", "ROAS"], horizontal=True)
                            
                            if target_type == "CPF（フォロー単価）":
                                target_value = st.number_input("目標CPF（円）", value=50, step=10)
                                target_dict = {"target_cpf": target_value}
                            elif target_type == "CPA":
                                target_value = st.number_input("目標CPA（円）", value=5000, step=500)
                                target_dict = {"target_cpa": target_value}
                            else:
                                target_value = st.number_input("目標ROAS", value=3.0, step=0.5)
                                target_dict = {"target_roas": target_value}
                            
                            if st.form_submit_button("💾 保存"):
                                target_manager.set_campaign_targets(
                                    sel_campaign["id"],
                                    sel_campaign["name"],
                                    target_dict,
                                )
                                st.success(f"✅ {sel_name} の目標を設定しました！")
                                st.rerun()
        
        except Exception as e:
            st.error(f"目標値管理モジュールの読み込みエラー: {e}")
    
    # =====================================================
    # 履歴タブ
    # =====================================================
    with tab5:
        st.subheader("📋 アクション履歴")
        
        if executor:
            history = executor.get_action_history(limit=30)
            
            if history:
                for item in reversed(history):  # 新しい順
                    action = item.get("action", {})
                    status = item.get("status", "unknown")
                    
                    status_icon = {
                        "executed": "✅",
                        "approved": "🟡",
                        "rejected": "❌",
                    }.get(status, "⚪")
                    
                    campaign_name = action.get("campaign_name", "Unknown")
                    action_type = action.get("type", "unknown")
                    
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        st.write(f"{status_icon} **{campaign_name}** - {action_type}")
                    with col2:
                        st.caption(status)
                    with col3:
                        timestamp = item.get("executed_at") or item.get("approved_at") or item.get("rejected_at") or item.get("created_at", "")
                        st.caption(timestamp[:16] if timestamp else "")
            else:
                st.info("📭 履歴がありません")
        else:
            st.warning("ActionExecutorが初期化されていません")


if __name__ == "__main__":
    main()


