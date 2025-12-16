#!/bin/bash
# Meta Ads AI Agent バックグラウンド実行セットアップスクリプト

set -e

# 色付き出力
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# プロジェクトディレクトリ
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENV_PATH="$PROJECT_DIR/venv"
PYTHON_PATH="$VENV_PATH/bin/python"
SCRIPT_PATH="$PROJECT_DIR/run_monitor.py"
LOG_DIR="$PROJECT_DIR/logs"
PID_FILE="$PROJECT_DIR/.monitor.pid"

echo -e "${GREEN}🤖 Meta Ads AI Agent - バックグラウンド実行セットアップ${NC}"
echo ""

# ログディレクトリ作成
mkdir -p "$LOG_DIR"

# 関数: プロセスの状態確認
check_status() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null 2>&1; then
            echo -e "${GREEN}✅ 監視プロセス実行中 (PID: $PID)${NC}"
            return 0
        else
            echo -e "${YELLOW}⚠️ PIDファイルは存在するが、プロセスは停止しています${NC}"
            rm -f "$PID_FILE"
            return 1
        fi
    else
        echo -e "${YELLOW}⏸️ 監視プロセスは停止しています${NC}"
        return 1
    fi
}

# 関数: プロセス開始
start_monitor() {
    if check_status > /dev/null 2>&1; then
        echo -e "${YELLOW}すでに実行中です${NC}"
        return 0
    fi
    
    echo -e "${GREEN}🚀 監視プロセスを開始します...${NC}"
    
    # バックグラウンドで実行
    cd "$PROJECT_DIR"
    nohup "$PYTHON_PATH" "$SCRIPT_PATH" --start > "$LOG_DIR/monitor.log" 2>&1 &
    echo $! > "$PID_FILE"
    
    sleep 2
    
    if check_status > /dev/null 2>&1; then
        echo -e "${GREEN}✅ 監視プロセスを開始しました${NC}"
        echo -e "   ログ: $LOG_DIR/monitor.log"
    else
        echo -e "${RED}❌ 開始に失敗しました。ログを確認してください${NC}"
        cat "$LOG_DIR/monitor.log" | tail -20
    fi
}

# 関数: プロセス停止
stop_monitor() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null 2>&1; then
            echo -e "${YELLOW}監視プロセスを停止します (PID: $PID)...${NC}"
            kill $PID
            sleep 2
            rm -f "$PID_FILE"
            echo -e "${GREEN}✅ 停止しました${NC}"
        else
            rm -f "$PID_FILE"
            echo -e "${YELLOW}プロセスは既に停止しています${NC}"
        fi
    else
        echo -e "${YELLOW}実行中のプロセスはありません${NC}"
    fi
}

# 関数: ログ表示
show_logs() {
    if [ -f "$LOG_DIR/monitor.log" ]; then
        echo -e "${GREEN}📋 最新のログ (最後の50行):${NC}"
        tail -50 "$LOG_DIR/monitor.log"
    else
        echo -e "${YELLOW}ログファイルがありません${NC}"
    fi
}

# 関数: ログをリアルタイム監視
follow_logs() {
    if [ -f "$LOG_DIR/monitor.log" ]; then
        echo -e "${GREEN}📋 ログをリアルタイム監視中 (Ctrl+C で終了):${NC}"
        tail -f "$LOG_DIR/monitor.log"
    else
        echo -e "${YELLOW}ログファイルがありません。まず start を実行してください${NC}"
    fi
}

# メイン処理
case "${1:-help}" in
    start)
        start_monitor
        ;;
    stop)
        stop_monitor
        ;;
    restart)
        stop_monitor
        sleep 1
        start_monitor
        ;;
    status)
        check_status
        ;;
    logs)
        show_logs
        ;;
    follow)
        follow_logs
        ;;
    help|*)
        echo "使い方: $0 {start|stop|restart|status|logs|follow}"
        echo ""
        echo "コマンド:"
        echo "  start   - 監視プロセスをバックグラウンドで開始"
        echo "  stop    - 監視プロセスを停止"
        echo "  restart - 監視プロセスを再起動"
        echo "  status  - 監視プロセスの状態を確認"
        echo "  logs    - 最新のログを表示"
        echo "  follow  - ログをリアルタイム監視"
        echo ""
        echo "例:"
        echo "  $0 start   # 開始"
        echo "  $0 status  # 状態確認"
        echo "  $0 logs    # ログ確認"
        ;;
esac

