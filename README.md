# Meta Ads AI Agent 🤖

Meta広告（Facebook/Instagram広告）の**自動監視・最適化・入稿**を行うAIエージェントです。
Claude AIと連携して、データに基づいた分析・提案・実行を自動化します。

## ✨ 主な機能

### 📊 自動監視 & Slack通知
- **毎時チェック**: パフォーマンス異常を即時検知
- **毎朝9時レポート**: 日次サマリー & AI提案をSlack送信
- **ASC対応**: Advantage+ ショッピングキャンペーン専用の分析

### 🚀 ワンクリック入稿
- **テンプレート入稿**: ASCブロード、トラフィック等をボタン1つで作成
- **AI自動生成**: メインテキスト・見出し・説明をClaudeが自動生成
- **クリエイティブライブラリ**: 既存画像をサムネイル表示→選択→入稿

### 🎯 目標値管理
- **キャンペーン別目標**: CPF、CPA、ROASの目標をダッシュボードで設定
- **フェーズ対応**: 目標値を随時変更可能

### 📈 分析 & レポート
- 複数期間比較（今日 vs 昨日 vs 過去7日 vs 過去30日）
- キャンペーン目的別の適切なKPI判定
- 週次/月次レポート生成 & CSV出力

---

## 🚀 クイックスタート

### 1. セットアップ

```bash
cd meta-ads-agent

# 仮想環境を作成
python3 -m venv venv
source venv/bin/activate

# 依存関係をインストール
pip install -r requirements.txt

# 環境変数を設定
cp env-example.txt .env
# .env を編集
```

### 2. API設定

#### Meta API
1. [Meta for Developers](https://developers.facebook.com/) でアプリを作成
2. [Graph API Explorer](https://developers.facebook.com/tools/explorer/) で長期トークン取得
3. `.env` に設定:

```env
META_ACCESS_TOKEN=EAARM2WnZARjMBQ...
META_AD_ACCOUNT_IDS=act_123456789
```

#### Claude API
1. [Anthropic Console](https://console.anthropic.com/) でAPIキー取得
2. `.env` に設定:

```env
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxx
```

#### Slack通知（オプション）
1. [Slack App](https://api.slack.com/apps) でWebhook URL取得
2. `.env` に設定:

```env
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
```

### 3. ダッシュボード起動

```bash
streamlit run dashboard/app.py --server.port 8502
```

ブラウザで http://localhost:8502 にアクセス

---

## 📱 使い方

### ダッシュボード

| ページ | 機能 |
|--------|------|
| 📊 ダッシュボード | パフォーマンス概要、主要KPI |
| 🔍 キャンペーン分析 | 詳細分析、AI提案 |
| 🔮 シミュレーション | 予算変更シミュレーション |
| 📈 パターン学習 | 成功パターン分析 |
| 📚 知識ベース | AIの知識管理 |
| 🤖 自動運用 | 監視設定、承認キュー、入稿提案 |
| 📤 入稿 | ワンクリック入稿、クリエイティブ管理 |

### ワンクリック入稿

1. 「📤 入稿」ページを開く
2. テンプレートを選択（ASCブロード等）
3. 商品名、URL、ページIDを入力
4. 画像を選択（ライブラリから）
5. 「🚀 入稿！」クリック

→ AIがテキスト自動生成 → キャンペーン作成完了！

### 自動監視の開始

#### ダッシュボードから
1. 「🤖 自動運用」→「⚙️ 設定」
2. 監視対象アカウントにチェック
3. 「▶️ 開始」ボタン

#### ターミナルから

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

### 手動コマンド

```bash
# 手動チェック
python run_monitor.py --check

# 日次レポート送信
python run_monitor.py --report

# Slack接続テスト
python run_monitor.py --test-slack
```

---

## ⚙️ 設定

### 目標値設定

ダッシュボード「🤖 自動運用」→「⚙️ 設定」で設定:

| 設定 | 説明 |
|------|------|
| 目標CPF | フォロー単価の目標（トラフィック用） |
| CPF注意ライン | この値を超えると注意アラート |
| CPF危険ライン | この値を超えると緊急アラート |
| 目標CPA | CV単価の目標（売上用） |
| 目標ROAS | 広告費用対効果の目標 |

### 監視スケジュール

- **毎時チェック**: 60分間隔でパフォーマンス監視
- **日次レポート**: 毎朝9時にSlack送信

---

## 📁 ディレクトリ構成

```
meta-ads-agent/
├── dashboard/
│   └── app.py              # Streamlitダッシュボード
├── meta_api/
│   ├── auth.py             # Meta API認証
│   ├── campaigns.py        # キャンペーン操作
│   ├── adsets.py           # 広告セット操作
│   ├── ads.py              # 広告操作
│   ├── insights.py         # パフォーマンスデータ
│   └── creative.py         # クリエイティブ管理
├── automation/
│   ├── monitor.py          # パフォーマンス監視
│   ├── notifier.py         # Slack通知
│   ├── scheduler.py        # 自動実行スケジューラー
│   ├── actions.py          # アクション実行
│   ├── targets.py          # 目標値管理
│   ├── campaign_templates.py # キャンペーンテンプレート
│   ├── auto_creative.py    # 自動入稿提案
│   ├── reports.py          # レポート生成
│   └── presets.py          # プリセット管理
├── agent/
│   ├── integrated_agent.py # 統合エージェント
│   ├── analyzer.py         # AI分析
│   └── bid_optimizer.py    # 入札最適化
├── knowledge_engine/
│   ├── knowledge_base.py   # 知識ベース
│   └── vector_store.py     # ベクトルDB
├── storage/
│   ├── campaign_targets.json  # 目標値設定
│   ├── monitor_config.json    # 監視設定
│   └── presets.json           # 入稿プリセット
├── scripts/
│   └── setup_background.sh # バックグラウンド実行
├── run_monitor.py          # 監視実行スクリプト
├── config.py               # 設定
└── .env                    # 環境変数
```

---

## 🔧 トラブルシューティング

### トークンエラー

```
Error validating access token
```

→ アクセストークンの有効期限切れ。Graph API Explorerで再取得してください。

### 権限エラー

```
(#200) Missing Permission
```

→ `ads_read`, `ads_management` 権限が付与されているか確認してください。

### APIレート制限

```
(#17) User request limit reached
```

→ しばらく待ってから再試行してください。

---

## 📝 ライセンス

MIT License

---

## 🤝 開発

機能追加・バグ報告は Issue / PR でお願いします。

