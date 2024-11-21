// 建立 SocketIO 連接
const socket = io();

// 嘗試連接，更新狀態為已連接
socket.on("connect", () => {
    document.getElementById("status").innerText = "狀態: 已連接";
    document.getElementById("status").classList.add("connected");
});

// 斷開連接時，顯示嘗試重新連接的訊息
socket.on("disconnect", () => {
    document.getElementById("status").innerText = "狀態: 與 Jetson Nano 斷開連接，嘗試重新連接中...";
    document.getElementById("status").classList.remove("connected");
    document.getElementById("receivedImage").style.display = "none"; // 隱藏圖片
    document.getElementById("imageName").innerText = ""; // 清除圖片名稱
});

// 發送截圖指令給後端伺服器
function sendScreenshotCommand() {
    socket.emit("screenshot");
}

// 當接收到圖片路徑時，更新圖片和圖片名稱顯示
socket.on("image_received", (data) => {
    document.getElementById("imageName").innerText = "收到的圖片: " + data.filepath.split("/").pop();
    document.getElementById("receivedImage").src = data.filepath; // 設定圖片顯示路徑
    document.getElementById("receivedImage").style.display = "block"; // 顯示圖片
});


