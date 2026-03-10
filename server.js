// server.js
const express = require("express");
const app = express();
const http = require("http").createServer(app);
const io = require("socket.io")(http);
const path = require("path");

app.use(express.static(__dirname));
app.use(express.json());

app.get("/", (req, res) => {
  res.sendFile(path.join(__dirname, "index.html"));
});

// ===============================================================
// [RL Bridge] 강화학습 브릿지
// ===============================================================
let rlSocket = null; // RL 클라이언트 소켓
let gameSocket = null; // 게임 클라이언트 소켓 (RL 모드)

let waitingPlayer = null;

io.on("connection", (socket) => {
  console.log("☑️ 유저 접속! ID:", socket.id);

  socket.on("join_game", (userData) => {
    console.log(`[매칭 요청] ${userData.nickname} (ID: ${socket.id})`);

    if (waitingPlayer) {
      const partnerSocket = waitingPlayer.socket;
      const partnerName = waitingPlayer.nickname;

      console.log(`매칭 성공! ${partnerName} vs ${userData.nickname}`);

      // 방 이름 만들기
      const roomName = `room_${partnerSocket.id}_${socket.id}`;
      // 두 사람을 같은 방에 넣음
      socket.join(roomName);
      partnerSocket.join(roomName);

      socket.currentRoom = roomName;
      partnerSocket.currentRoom = roomName;

      io.to(roomName).emit("game_start", {
        players: [
          { id: partnerSocket.id, name: partnerName },
          { id: socket.id, name: userData.nickname },
        ],
        room: roomName,
      });

      // 대기열 초기화
      waitingPlayer = null;
    } else {
      // 대기자가 없다면 -> 내가 대기자가 됨
      waitingPlayer = { socket: socket, nickname: userData.nickname };
      socket.emit("waiting", { message: "다른 대원을 기다리는 중..." });
      console.log("⏳ 대기열 등록 완료");
    }
  });

  socket.on("sync_action", (data) => {
    if (data.room) {
      // 나를 제외한 방 안의 사람들에게 전송
      socket.to(data.room).emit("sync_action", data);
    }
  });

  socket.on("game_state_change", (data) => {
    if (data.room) {
      // 나를 포함한 방 전체에 알림 (속도는 다 같이 바껴야 하니까)
      io.to(data.room).emit("game_state_change", data);
    }
  });

  // 유접 접속 해제
  socket.on("disconnect", () => {
    console.log("❌ 유저 접속 해제:", socket.id);
    if (waitingPlayer && waitingPlayer.socket.id === socket.id) {
      waitingPlayer = null;
    }
    if (socket.currentRoom) {
      socket.to(socket.currentRoom).emit("partner_disconnected");
    }

    // RL 클라이언트 연결 해제 처리
    if (socket === rlSocket) {
      console.log("🤖 RL 클라이언트 연결 해제");
      rlSocket = null;
    }
    if (socket === gameSocket) {
      gameSocket = null;
    }
  });

  // ===============================================================
  // [RL Bridge] 강화학습 소켓 이벤트
  // ===============================================================

  // RL 클라이언트 연결 (Python에서 접속)
  socket.on("rl_connect", (data) => {
    console.log("🤖 RL 클라이언트 연결!");
    rlSocket = socket;
    // 게임 브라우저에 RL 모드 시작 알림
    if (gameSocket) {
      gameSocket.emit("rl_mode_start", { speed: data?.speed || 10 });
    }
  });

  // RL 행동 전송 (Python → 게임 브라우저)
  socket.on("rl_action", (action) => {
    if (gameSocket) {
      gameSocket.emit("rl_execute_action", action);
    }
  });

  // 게임 상태 전송 (게임 브라우저 → Python)
  socket.on("rl_state", (state) => {
    if (rlSocket && rlSocket.id !== socket.id) {
      rlSocket.emit("rl_state", state);
    }
  });

  // 게임 브라우저 등록
  socket.on("rl_game_ready", () => {
    console.log("🎮 RL 게임 브라우저 준비 완료");
    gameSocket = socket;
    if (rlSocket) {
      rlSocket.emit("rl_game_ready");
    }
  });
});

const PORT = 3000;
http.listen(PORT, () => {
  console.log(`서버 가동 중: http://localhost:${PORT}`);
});
