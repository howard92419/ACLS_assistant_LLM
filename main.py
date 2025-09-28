import os
import json
from datetime import datetime, timezone
from openai import OpenAI
from dotenv import load_dotenv
import pandas as pd
import pytz

# 直接匯入 utils/__init__.py 暴露出來的函式
from .utils import init_db, log_event, list_logs, clear_logs, start_timer


# ----------------------
# 初始化 OpenAI
# ----------------------
load_dotenv()
client = None
if os.getenv("OPENAI_API_KEY"):
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ----------------------
# Timer callback
# ----------------------
def on_timer_finish(label, seconds):
    print(f"[callback] 計時器 '{label}' 結束 ({seconds}s)")
    print("接下來的步驟：請繼續監控病人的反應，準備給藥。")


# ----------------------
# 顯示紀錄轉為 XML
# ----------------------
def logs_to_xml():
    rows = list_logs(1000)
    xml = "<logs>\n"
    for r in rows:
        xml += f'  <event id="{r[0]}" timestamp="{r[3]}">\n'
        xml += f'    <name>{r[1]}</name>\n'
        xml += f'    <note>{r[2]}</note>\n'
        xml += f'    <extra>{r[4]}</extra>\n'
        xml += "  </event>\n"
    xml += "</logs>"
    return xml


# ----------------------
# OpenAI 解析輸入
# ----------------------
def parse_openai_input(text, previous_events):
    if not client:
        return {"action": "reply", "message": "OpenAI 尚未設定"}

    system_prompt = (
        "你是一個到院前ACLS專業救護員，專注於協助使用者進行急救與進行記錄:\n"
        "你的任務包括：\n"
        "1. 判斷使用者輸入是否需要紀錄事件或給藥，並生成事件名稱、完整說明、藥物名稱、劑量、途徑、EKG等資訊。\n"
        "2. 判斷是否需要設定計時器，並提供建議。\n"
        "3. 僅提供急救建議，勿提供非急救醫療建議。\n"
        "4. 所有回覆請簡明、精準、禮貌，使用中文。\n"
        "5. 如果需要你紀錄事件，請自動根據ACLS紀錄完整，例如:epi 1mg ivp請記錄成Epinephrine 1mg IV-push\n"
        "6. 如果聽到紀錄相關詞，幫我在資料庫底下建立紀錄\n"
        "7. 如果使用者輸入了「病人OHCA」這樣的訊息，請紀錄病人發生OHCA的時間，並回覆指引："
        "紀錄事件：OHCA，開始急救。\n"
        "請提示開始心肺復甦（CPR），並準備使用除顫器（AED）。\n"
        "如果病人已經進行了電擊，請提示繼續下一步急救措施。\n"
        "\n"
        "8. **計時器提示**：如果使用者輸入或提到「計時」、「X分鐘」、「X秒」等字詞，請回傳 JSON 指令，而不是單純文字。"
        "JSON 格式如下：\n"
        "{\n"
        '  "action": "start_timer",\n'
        '  "seconds": 秒數,\n'
        '  "label": "計時器名稱"\n'
        "}\n"
        "範例：\n"
        "使用者輸入「幫我計時3分鐘」\n"
        "你回傳：\n"
        "{\n"
        '  "action": "start_timer",\n'
        '  "seconds": 180,\n'
        '  "label": "CPR計時"\n'
        "}\n"
        "請確保回傳 JSON，且秒數正確換算，label 可以加上簡短描述。\n"
        "\n"
        "這是過去的急救事件，請參考它來建議下一步：\n"
        f"過去的急救事件：{previous_events}\n"
        "現在請基於病人的狀況和過去的急救步驟，根據AHA-ACLS流程演算法，提供下一步的處置建議。"
        "9. 一定要仔細思考你的回覆，請重複思考兩次後再回覆\n"
    )

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ],
            temperature=0.5,
        )
        choice = resp.choices[0]
        content = getattr(choice.message, "content", "")
        try:
            data = json.loads(content)
        except:
            data = {"action": "reply", "message": content}
        return data
    except Exception as e:
        return {"action": "reply", "message": f"OpenAI解析錯誤: {e}"}


# ----------------------
# 事件紀錄處理
# ----------------------
def handle_action(data, previous_events):
    action = data.get("action")

    if action == "log_event":
        event = data.get("event", "事件")
        note = data.get("note", "")
        extra = data.get("extra")
        tz = pytz.timezone("Asia/Taipei")
        ts = datetime.now(tz).strftime("%Y/%m/%d %H:%M")
        log_event(event, note=note, ts=ts, extra=extra)
        previous_events.append(f"{ts} {event} - {note}")
        print(f"已紀錄事件：{ts} {event}")

        next_step = parse_openai_input("下一步我該做什麼", previous_events)
        if next_step.get("action") == "reply":
            print(f"建議步驟：{next_step.get('message')}")
        else:
            print("無法提供建議，請手動處理。")

    elif action == "start_timer":
        sec = data.get("seconds", 60)
        label = data.get("label", "計時器")
        start_timer(sec, label=label, on_finish=on_timer_finish)
        print(f"已開始計時器: {sec}秒 ({label})")

    elif action == "reply":
        print(data.get("message", "") + "\n")

    else:
        print("無法解析動作，請重新描述。")


# ----------------------
# 主程式迴圈
# ----------------------
def main_loop():
    init_db()
    clear_logs()
    print("ACLS Assistant CLI\n輸入 'help' 查看可用指令。")

    previous_events = []
    keywords = ["紀錄"]

    while True:
        try:
            text = input("> ").strip()
            if not text:
                continue
            if text.lower() in ("exit", "quit", "q"):
                print("bye")
                break
            if text in ("help", "h", "?"):
                print("可用指令:\n  show logs | 顯示記錄\n  export logs | 匯出紀錄\n  exit")
                continue

            data = parse_openai_input(text, previous_events)

            # 自動紀錄判斷
            trigger_log = any(kw in text for kw in keywords)
            if not trigger_log:
                if data.get("action") == "reply" and "紀錄" in data.get("message", ""):
                    trigger_log = True

            if trigger_log:
                tz = pytz.timezone("Asia/Taipei")
                ts = datetime.now(tz).strftime("%Y/%m/%d %H:%M")
                log_event(event="自動紀錄", note=f"觸發關鍵字: {text}", ts=ts, extra=None)
                previous_events.append(f"{ts}  {text}")
                print(f"已自動紀錄事件: {ts}")

            # 處理 OpenAI 指令
            handle_action(data, previous_events)

            # 顯示紀錄
            if "show logs" in text or "顯示紀錄" in text:
                print(logs_to_xml())

            # 匯出紀錄
            if "export logs" in text or "匯出紀錄" in text:
                filename = f"ACLS_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                rows = list_logs(1000)
                df = pd.DataFrame(rows, columns=["ID", "Event", "Note", "Timestamp", "Extra"])
                df.to_excel(filename, index=False)
                print(f"已匯出紀錄到 {filename}")

        except KeyboardInterrupt:
            print("\nKeyboardInterrupt, bye")
            break


if __name__ == "__main__":
    main_loop()
