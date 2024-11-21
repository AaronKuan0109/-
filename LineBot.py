import signal
import sys
import os
import base64
from flask import Flask, render_template, request, abort
from flask_socketio import SocketIO
import asyncio
import websockets
import threading
import time

from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    ImageMessage
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent

app = Flask(__name__)
socketio = SocketIO(app)

# 設定圖片存儲資料夾
screenshot_folder = "C:\\Users\\User\\Desktop\\WebSocket應用\\static\\received_screenshots"
os.makedirs(screenshot_folder, exist_ok=True)

# Line Bot 配置
configuration = Configuration(access_token='9t8VTx9Tc3TIP2ZZKe+IFXpraz8SxgcrA6kpq8bBCtVKfBF2ETCDukaX9GFKgTirk50B7KPL9L39Qzuf+UwjjDVKenm6fAlinbL5ZFtFbtip+rhhjZ3/vSMroBX2FAOWsnxelOYPCWHL8liwy4hG1AdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('7020e85166e4acc935491f45759e21f7')


# Jetson Nano 客戶端管理
clients = set()

# 處理信號以安全退出
def signal_handler(sig, frame):
    print("收到中斷信號，正在結束程序...")
    os._exit(0)  # 強制退出所有線程

signal.signal(signal.SIGINT, signal_handler)  # 捕捉 Ctrl+C 信號

# 處理 Jetson Nano 的 WebSocket 連接
async def handle_jetson_connection(websocket, path):
    print("Jetson Nano 已連接")
    clients.add(websocket)
    try:
        async for message in websocket:
            # 分離檔名和圖片數據
            filename, image_data = message.split(":", 1)
            print(f"接收到來自 Jetson Nano 的數據: {filename}")
            file_path = os.path.join(screenshot_folder, os.path.basename(filename))
            
            # 解碼圖片數據並儲存為圖片文件
            with open(file_path, "wb") as f:
                f.write(base64.b64decode(image_data))
            print(f"圖片已儲存為 {file_path}")
            
            
            # 傳送圖片路徑到前端顯示
            relative_path = f"/static/received_screenshots/{os.path.basename(filename)}"
            socketio.emit("image_received", {"filepath": relative_path})
    except websockets.ConnectionClosed:
        print("Jetson Nano 已斷開連接")
    finally:
        clients.remove(websocket)

# 啟動 WebSocket 伺服器的線程
def start_websocket_server():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    # WebSocket 伺服器監聽 8765 端口
    server = websockets.serve(handle_jetson_connection, "0.0.0.0", 8765)
    loop.run_until_complete(server)
    loop.run_forever()

@app.route("/")
def index():
    return render_template("index.html")

@socketio.on("screenshot")
def handle_screenshot_event():
    # 向所有連接的 Jetson Nano 客戶端發送截圖指令
    for client in clients:
        asyncio.run(client.send("screenshot"))

# Line Bot Webhook
@app.route("/callback", methods=['POST'])
def callback():
    # 獲取 X-Line-Signature 標頭的值
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # 處理 webhook 主體
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.info("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    text = event.message.text
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        
        if text == "@傳送猴子圖片":
            handle_screenshot_event()
            time.sleep(1)
            # 傳送最新截圖
            if os.listdir(screenshot_folder):
                latest_file = sorted(os.listdir(screenshot_folder))[-1]
                url = request.url_root + f'static/received_screenshots/{latest_file}'
                url = url.replace("http", "https")  # 如果需要使用 HTTPS
                app.logger.info("傳送圖片 URL=" + url)
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[
                            ImageMessage(original_content_url=url, preview_image_url=url)
                        ]
                    )
                )
            else:
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessageContent(text="目前沒有截圖可以傳送。")]
                    )
                )

if __name__ == "__main__":
    websocket_thread = threading.Thread(target=start_websocket_server)
    websocket_thread.start()
    socketio.run(app, host="0.0.0.0", port=5000)
