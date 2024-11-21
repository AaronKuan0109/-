import signal
import sys
from flask import Flask, render_template
from flask_socketio import SocketIO
import asyncio
import websockets
import threading
import os
import base64

app = Flask(__name__)
socketio = SocketIO(app)

# 定義圖片存儲資料夾
screenshot_folder = "C:\\Users\\User\\Desktop\\WebSocket應用\\static\\received_screenshots"
os.makedirs(screenshot_folder, exist_ok=True)

# Jetson Nano 客戶端連接管理
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

#@app.route("/")
#def index():
    #return render_template("index.html")

@app.route("/")
def index():
    return render_template("C:\\Users\\User\\Desktop\\WebSocket應用\\LINE_BOT\\echo-bot\\app.py")

@socketio.on("screenshot")
def handle_screenshot_event():
    # 向所有連接的 Jetson Nano 客戶端發送截圖指令
    for client in clients:
        asyncio.run(client.send("screenshot"))

# 啟動 Flask 和 WebSocket 伺服器
if __name__ == "__main__":
    websocket_thread = threading.Thread(target=start_websocket_server)
    websocket_thread.start()
    socketio.run(app, host="0.0.0.0", port=5000)




