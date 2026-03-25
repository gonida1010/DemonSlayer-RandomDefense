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
// [API] 학습된 모델 목록 조회
// ===============================================================
const fs = require("fs");

app.get("/api/models", (req, res) => {
  const modelsDir = path.join(__dirname, "python", "models");
  const models = [];

  if (!fs.existsSync(modelsDir)) {
    return res.json({ models: [] });
  }

  // 알고리즘별 폴더 탐색 (ppo, recurrent, dqn)
  const algoDirs = fs
    .readdirSync(modelsDir, { withFileTypes: true })
    .filter((d) => d.isDirectory())
    .map((d) => d.name);

  for (const algo of algoDirs) {
    const algoPath = path.join(modelsDir, algo);
    const files = fs
      .readdirSync(algoPath)
      .filter((f) => f.endsWith(".zip"))
      .sort();

    for (const file of files) {
      const filePath = path.join("python", "models", algo, file);
      const stat = fs.statSync(path.join(algoPath, file));
      const isBest = file === "best_model.zip";
      const isFinal = file === "demon_slayer_final.zip";

      models.push({
        algorithm: algo,
        filename: file,
        path: filePath,
        size: (stat.size / (1024 * 1024)).toFixed(1) + " MB",
        modified: stat.mtime.toISOString(),
        isBest,
        isFinal,
        label: isBest
          ? `[BEST] ${algo}`
          : isFinal
            ? `[FINAL] ${algo}`
            : `${algo}/${file}`,
      });
    }
  }

  res.json({ models });
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

  // 모델 변경 요청 (브라우저 → Python)
  socket.on("rl_load_model", (data) => {
    console.log(`🤖 모델 변경 요청: ${data?.path}`);
    if (rlSocket) {
      rlSocket.emit("rl_load_model", data);
    }
  });

  // 모델 변경 완료 (Python → 브라우저)
  socket.on("rl_model_loaded", (data) => {
    if (socket === rlSocket && gameSocket) {
      gameSocket.emit("rl_model_loaded", data);
    }
  });

  // ===============================================================
  // [AI 대전] 브라우저 ↔ Python RL 브릿지 중계
  // ===============================================================

  // 브라우저 → Python: AI 대전 시작 요청
  socket.on("ai_battle_start", (data) => {
    console.log("🤖 AI 대전 요청!");
    if (rlSocket) {
      rlSocket.emit("ai_battle_start", data);
    } else {
      console.log("  RL 클라이언트 미연결 → 브라우저 로컬 시뮬레이션 사용");
      socket.emit("ai_battle_no_bridge");
    }
  });

  // Python → 브라우저: AI 진행 상황
  socket.on("ai_battle_state", (data) => {
    if (socket === rlSocket) {
      io.emit("ai_battle_state", data);
    }
  });

  // Python → 브라우저: AI 최종 결과
  socket.on("ai_battle_result", (data) => {
    if (socket === rlSocket) {
      io.emit("ai_battle_result", data);
    }
  });
});

const PORT = 3000;
http.listen(PORT, () => {
  console.log(`서버 가동 중: http://localhost:${PORT}`);
});
