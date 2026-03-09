import { initializeApp } from "https://www.gstatic.com/firebasejs/11.6.1/firebase-app.js";
import {
  getFirestore,
  collection,
  addDoc,
  query,
  orderBy,
  limit,
  getDocs,
} from "https://www.gstatic.com/firebasejs/11.6.1/firebase-firestore.js";

// ===============================================================
// 전역 변수 선언 (Global Variables)
// ===============================================================
let GAME_CONFIG;
let UNIT_DATA;
let RECIPES;
let ENEMY_CONFIG;
let game; // Phaser.Game 인스턴스

// 플레이어 정보 관련
let currentPlayerName = "이름없음";
let currentMode = "normal"; // normal | hard | multi
let partnerName = "";
let myRoomName = null;

// ===============================================================
// Socket.IO 설정 및 이벤트 리스너
// ===============================================================
let socket = null;

// io 라이브러리가 로드되었는지 확인 (서버가 있을 때만 true)
if (typeof io !== "undefined") {
  socket = io();

  // (1) 연결 확인
  socket.on("connect", () => {
    console.log("✅ 서버 연결 성공! 내 ID:", socket.id);
  });

  // (2) 매칭 대기 중
  socket.on("waiting", (data) => {
    console.log("⏳ 대기열 등록됨");
    alert("다른 대원을 기다리고 있습니다...\n");
  });

  // (3) 게임 시작 신호
  socket.on("game_start", (data) => {
    console.log("⚔️ 매칭 성사! 게임 시작", data);
    const overlay = document.getElementById("login-overlay");
    if (overlay) overlay.style.display = "none";

    myRoomName = data.room;

    const myId = socket.id;
    const partner = data.players.find((p) => p.id !== myId);

    if (partner) {
      partnerName = partner.name;
      console.log("내 동료:", partnerName);
    } else {
      partnerName = "";
    }

    const isHost = data.players[0].id === myId;
    if (game) {
      game.scene.start("GameScene", { isHost: isHost, roomName: myRoomName });
    }
  });
} else {
  console.log("⚠️ 서버를 찾을 수 없습니다. (싱글 플레이만 가능)");
}

// ===============================================================
// Firebase 설정 (Configuration)
// ===============================================================
const firebaseConfig = {
  apiKey: "AIzaSyC71OnYx9gKWl9KF3JnTRzY0efaoyX9DGM",
  authDomain: "demon-slayer-random-defense.firebaseapp.com",
  projectId: "demon-slayer-random-defense",
  storageBucket: "demon-slayer-random-defense.firebasestorage.app",
  messagingSenderId: "1058543956168",
  appId: "1:1058543956168:web:c3ab59008ced6ed44535fd",
};

// 파이어베이스 초기화
const app = initializeApp(firebaseConfig);
const db = getFirestore(app);
console.log("Firebase Connected!");

// ===============================================================
// 유틸리티 함수
// ===============================================================

// 모드별 점수 컬렉션 이름 가져오기
function getScoreCollectionName(mode) {
  if (mode === "hard") {
    return "scores_hard";
  } else if (mode === "multi") {
    return "scores_multi"; // 협동 모드 전용 컬렉션
  } else {
    return "scores_normal";
  }
}

// === 모드별 랭킹 텍스트 가져오기 (MenuScene에서 사용) ===
async function fetchLeaderboardText(mode) {
  if (!db) return "데이터베이스 연결 실패";

  try {
    const q = query(
      collection(db, getScoreCollectionName(mode)),
      orderBy("round", "desc"),
      limit(10),
    );
    const snapshot = await getDocs(q);

    if (snapshot.empty) {
      return "아직 기록이 없습니다.";
    }

    let text = "";
    let rank = 1;
    snapshot.forEach((doc) => {
      const data = doc.data();
      text += `${rank}위. ${data.name} - ${data.round}라운드\n`;
      rank++;
    });
    return text;
  } catch (e) {
    console.error(e);
    return "랭킹 로드 중 오류 발생";
  }
}

// === HTML UI (대원 등록 화면만) ===
const overlay = document.getElementById("login-overlay");
const nicknameInput = document.getElementById("nickname");
const startBtn = document.getElementById("start-btn");

// 기존 startBtn 삭제하고 두 개의 버튼을 가져옵니다.
const btnNormal = document.getElementById("btn-normal");
const btnHard = document.getElementById("btn-hard");

// 게임 시작 공통 함수 추가
async function tryStartGame(selectedMode) {
  // 1. 게임 인스턴스 확인
  if (!game) {
    alert("게임 로딩 중입니다. 잠시만 기다려주세요!");
    return;
  }

  // 2. 이름 입력 확인
  const name = nicknameInput.value.trim();
  if (name.length < 1) {
    alert("이름을 입력해주세요!");
    return;
  }

  // 3. 공통 설정 (이름 저장, 데이터 로드)
  currentPlayerName = name;
  currentMode = selectedMode;

  console.log(`${selectedMode} 모드로 데이터 로딩 중...`);
  await loadDataForMode(selectedMode);

  if (selectedMode === "multi") {
    console.log("서버에 매칭 요청 보냄...");
    socket.emit("join_game", { nickname: name });
  } else {
    overlay.style.display = "none";
    game.scene.start("MenuScene");
  }
}

// Scene 1: Boot
class BootScene extends Phaser.Scene {
  constructor() {
    super("BootScene");
  }
  preload() {
    this.load.setPath("assets/images");

    // 메인 메뉴 배경 이미지 로드(스토리,지옥,협동)
    this.load.image("menu_bg", "background2.png");
    this.load.image("mode_normal", "background2.png");
    this.load.image("mode_hard", "mode_hard.png");
    this.load.image("mode_multi", "mode_multi.png");

    // 인게임 배경화면
    this.load.image("bg_stage1", "background3.png"); // 1~10라운드
    this.load.image("bg_stage2", "background4.png"); // 11~20라운드
    this.load.image("bg_stage3", "background5.png"); // 21~30라운드
    this.load.image("bg_stage4", "background6.png"); // 31~40라운드
    this.load.image("bg_stage5", "background7.png"); // 41~50라운드
    this.load.image("bg_stage6", "background8.png");
    this.load.image("bg_stage7", "background9.png");
    this.load.image("bg_stage8", "background10.png");
    this.load.image("bg_stage9", "background11.png");

    // 클리어 이미지
    this.load.image("game_clear_bg", "game_clear.png");

    // [★★★ 공격 모션 ★★★]
    this.load.spritesheet("attack_slayer_basic", "basic_attack.png", {
      frameWidth: 175 / 5,
      frameHeight: 32,
    });
    // 1. 탄지로 (type: "tanjiro_water")
    this.load.spritesheet("attack_tanjiro_water", "tanjiro_attack.png", {
      frameWidth: 252 / 7,
      frameHeight: 32,
    });

    // 2. 젠이츠 (type: "zenitsu_thunder")
    this.load.spritesheet("attack_zenitsu_thunder", "zenitsu_attack.png", {
      frameWidth: 175 / 5,
      frameHeight: 32,
    });

    // 3. 이노스케 (type: "inosuke_beast")
    this.load.spritesheet("attack_inosuke_beast", "inosuke_attack.png", {
      frameWidth: 175 / 5,
      frameHeight: 32,
    });

    // 4. 카나오 (type: "kanao_flower")
    this.load.spritesheet("attack_kanao_flower", "kanao_attack.png", {
      frameWidth: 416 / 13,
      frameHeight: 32,
    });

    // 5. 까마귀 (type: "crow_attack")
    this.load.spritesheet("attack_crow", "crow_attack.png", {
      frameWidth: 252 / 7,
      frameHeight: 32,
    });

    // 6. 은(Kakushi) (type: "kakushi_support")
    this.load.spritesheet("attack_kakushi_support", "kakushi_attack.png", {
      frameWidth: 164 / 4,
      frameHeight: 32,
    });

    this.load.spritesheet("attack_genya_gun", "genya_attack.png", {
      frameWidth: 44,
      frameHeight: 32,
    });

    this.load.spritesheet("attack_aoi_support", "tanjiro_attack.png", {
      frameWidth: 252 / 7,
      frameHeight: 32,
    });

    // 7. 우로코다키 (type: "urokodaki_water")
    this.load.spritesheet("attack_urokodaki", "urokodaki_attack.png", {
      frameWidth: 36,
      frameHeight: 32,
    });

    // 8. 쿠와지마 (type: "jigoro_thunder")
    this.load.spritesheet("attack_jigoro", "jigoro_attack.png", {
      frameWidth: 35,
      frameHeight: 32,
    });

    // 9. 하가네즈카 (type: "haganezuka_angry")
    this.load.spritesheet("attack_haganezuka", "haganezuka_attack.png", {
      frameWidth: 41,
      frameHeight: 32,
    });

    // 10. 사비토 (type: "sabito_spirit")
    this.load.spritesheet("attack_sabito", "sabito_attack.png", {
      frameWidth: 32,
      frameHeight: 27,
    });

    // 11. 네즈코 나무상자 (type: "nezuko_kick")
    this.load.spritesheet("attack_nezuko_box", "nezuko_box_attack.png", {
      frameWidth: 32,
      frameHeight: 24,
    });

    // 12. 유시로 (type: "yushiro_paper")
    this.load.spritesheet("attack_yushiro", "yushiro_attack.png", {
      frameWidth: 32,
      frameHeight: 24,
    });

    // 13. 무라타 (type: "murata_water")
    this.load.spritesheet("attack_murata", "murata_attack.png", {
      frameWidth: 35,
      frameHeight: 32,
    });

    // 14. 기유 (type: "giyu_water")
    this.load.spritesheet("attack_giyu", "giyu_attack.png", {
      frameWidth: 32,
      frameHeight: 32,
    });

    // 15. 렌고쿠 (type: "rengoku_fire")
    this.load.spritesheet("attack_rengoku", "rengoku_attack.png", {
      frameWidth: 32,
      frameHeight: 32,
    });

    // 16. 텐겐 (type: "tengen_sound")
    this.load.spritesheet("attack_tengen", "tengen_attack.png", {
      frameWidth: 32,
      frameHeight: 32,
    });

    // 17. 시노부 (type: "shinobu_poison")
    this.load.spritesheet("attack_shinobu", "shinobu_attack.png", {
      frameWidth: 32,
      frameHeight: 256 / 8,
    });

    // 18. 카나에 (type: "kanae_flower")
    this.load.spritesheet("attack_kanae", "kanae_attack.png", {
      frameWidth: 32,
      frameHeight: 32, // 8
    });

    // 19. 무이치로 (type: "muichiro_mist")
    this.load.spritesheet("attack_muichiro", "muichiro_attack.png", {
      frameWidth: 320 / 5,
      frameHeight: 48,
    });

    // 20. 미츠리 (type: "mitsuri_love")
    this.load.spritesheet("attack_mitsuri", "mitsuri_attack.png", {
      frameWidth: 32, // 8
      frameHeight: 32,
    });

    // 21. 오바나이 (type: "obanai_snake")
    this.load.spritesheet("attack_obanai", "obanai_attack.png", {
      frameWidth: 45, //6
      frameHeight: 32,
    });

    // 22. 사네미 (type: "sanemi_wind")
    this.load.spritesheet("attack_sanemi", "sanemi_attack.png", {
      frameWidth: 35, // 5
      frameHeight: 32,
    });

    // 23. 교메이 (type: "gyomei_stone")
    this.load.spritesheet("attack_gyomei", "gyomei_attack.png", {
      frameWidth: 32, // 30
      frameHeight: 32,
    });

    // 24. 타마요 (type: "tamayo_blood")
    this.load.spritesheet("attack_tamayo", "tamayo_attack.png", {
      frameWidth: 192 / 4,
      frameHeight: 32,
    });

    // 25. 탄지로(히노카미) (type: "tanjiro_sun")
    this.load.spritesheet("attack_tanjiro_sun", "tanjiro_sun_attack.png", {
      frameWidth: 400 / 8,
      frameHeight: 50,
    });

    // 26. 젠이츠(신속) (type: "zenitsu_god")
    this.load.spritesheet("attack_zenitsu_god", "zenitsu_god_attack.png", {
      frameWidth: 32, // 13
      frameHeight: 32,
    });

    // 27. 네즈코(각성) (type: "nezuko_blood_art")
    this.load.spritesheet("attack_nezuko_awake", "nezuko_awake_attack.png", {
      frameWidth: 64,
      frameHeight: 64,
    });

    // 28. 기유(반점) (type: "giyu_mark_water")
    this.load.spritesheet("attack_giyu_mark", "giyu_mark_attack.png", {
      frameWidth: 64,
      frameHeight: 64,
    });

    // 29. 무이치로(반점) (type: "muichiro_mark_mist")
    this.load.spritesheet("attack_muichiro_mark", "muichiro_mark_attack.png", {
      frameWidth: 64,
      frameHeight: 64,
    });

    // 30. 타마요&유시로 (type: "tamayo_yushiro_combo")
    this.load.spritesheet(
      "attack_tamayo_yushiro",
      "tamayo_yushiro_attack.png",
      {
        frameWidth: 224 / 7,
        frameHeight: 32,
      },
    );

    // 31. 이노스케(각성) (type: "inosuke_awake_beast")
    this.load.spritesheet("attack_inosuke_awake", "inosuke_awake_attack.png", {
      frameWidth: 152 / 4, // 38px
      frameHeight: 32,
    });

    // ===============================================================
    // [Tier 6] 신화 (Legend)
    // ===============================================================

    // 32. 탄지로(13형) (type: "tanjiro_13th")
    this.load.spritesheet("attack_tanjiro_final", "tanjiro_final_attack.png", {
      frameWidth: 48, // 16
      frameHeight: 48,
    });

    // 33. 교메이(반점) (type: "gyomei_mark_stone")
    this.load.spritesheet("attack_gyomei_mark", "gyomei_mark_attack.png", {
      frameWidth: 48, // 18
      frameHeight: 48,
    });

    // 34. 요리이치 (type: "yoriichi_sun")
    this.load.spritesheet("attack_yoriichi", "yoriichi_attack.png", {
      frameWidth: 36, // 10
      frameHeight: 36,
    });

    // 35. 이노스케(산의 왕) (type: "inosuke_king_beast")
    this.load.spritesheet("attack_inosuke_king", "inosuke_king_attack.png", {
      frameWidth: 32, // 6
      frameHeight: 32,
    });

    // ===============================================================
    // [HIDDEN UNITS] 히든
    // ===============================================================

    // 36. 요리이치 영식 (type: "yoriichi_doll")
    this.load.spritesheet("attack_yoriichi_zero", "yoriichi_zero_attack.png", {
      frameWidth: 64, // 5
      frameHeight: 48,
    });

    // 37. 코쿠시보(상현1) (type: "kokushibo_moon")
    this.load.spritesheet("attack_koku", "koku_attack.png", {
      frameWidth: 64, // 8
      frameHeight: 64,
    });

    // 38. 탄지로(오니의 왕) (type: "tanjiro_demon_king")
    this.load.spritesheet("attack_tanjiro_king", "tanjiro_king_attack.png", {
      frameWidth: 64, // 15
      frameHeight: 49,
    });

    // 39. 쌍둥이의 운명 (type: "twin_destiny_combo")
    this.load.spritesheet("attack_twin_destiny", "twin_destiny_attack.png", {
      frameWidth: 64, // 7
      frameHeight: 64,
    });

    // ===============================================================
    // [신규 추가: Tier 5 & 6 신규 유닛 공격 모션]
    // ===============================================================

    // 1. 렌고쿠(멸살) - rengoku_9th_form
    this.load.spritesheet("attack_rengoku_9th", "rengoku_9th_attack.png", {
      frameWidth: 64,
      frameHeight: 64,
    });
    // 2. 텐겐(악보) - tengen_musical_score
    this.load.spritesheet("attack_tengen_score", "tengen_score_attack.png", {
      frameWidth: 128,
      frameHeight: 64,
    });
    // 3. 시노부(종의형) - shinobu_last_dance
    this.load.spritesheet("attack_shinobu_dance", "shinobu_dance_attack.png", {
      frameWidth: 64,
      frameHeight: 64,
    });
    // 4. 카나에(꽃의영) - kanae_flower_final
    this.load.spritesheet("attack_kanae_spirit", "kanae_spirit_attack.png", {
      frameWidth: 64,
      frameHeight: 64,
    });
    // 5. 사네미(반점) - sanemi_typhoon
    this.load.spritesheet("attack_sanemi_mark", "sanemi_mark_attack.png", {
      frameWidth: 64,
      frameHeight: 64,
    });
    // 6. 오바나이(반점) - obanai_serpent_god
    this.load.spritesheet("attack_obanai_mark", "obanai_mark_attack.png", {
      frameWidth: 1248 / 13,
      frameHeight: 64,
    });
    // 7. 미츠리(반점) - mitsuri_love_cat
    this.load.spritesheet("attack_mitsuri_mark", "mitsuri_mark_attack.png", {
      frameWidth: 64,
      frameHeight: 64,
    });
    // 8. 렌고쿠(마지막 미소) - rengoku_smile_effect
    this.load.spritesheet("attack_rengoku_smile", "rengoku_smile_attack.png", {
      frameWidth: 400 / 8,
      frameHeight: 50,
    });

    // [신규 Tier 6]
    // 9. 젠이츠(화뢰신) - zenitsu_7th_form
    this.load.spritesheet("attack_zenitsu_7th", "zenitsu_7th_attack.png", {
      frameWidth: 64,
      frameHeight: 64,
    });
    // 10. 기유(잔잔한 물) - giyu_dead_calm
    this.load.spritesheet("attack_giyu_calm", "giyu_calm_attack.png", {
      frameWidth: 64,
      frameHeight: 64,
    });
    // 11. 사네미(바람의 신) - sanemi_wind_god
    this.load.spritesheet("attack_sanemi_god", "sanemi_god_attack.png", {
      frameWidth: 64,
      frameHeight: 48,
    });
    // 12. 렌고쿠(마음의 불꽃) - rengoku_legend_fire
    this.load.spritesheet(
      "attack_rengoku_legend",
      "rengoku_legend_attack.png",
      { frameWidth: 64, frameHeight: 64 },
    );

    // 13. 오바나이&미츠리 (사랑과 뱀의 호흡)
    this.load.spritesheet("attack_love_snake", "love_snake_attack.png", {
      frameWidth: 64,
      frameHeight: 64,
    });

    // 14. 무이치로 (내비세 - 투명한 세계)
    this.load.spritesheet(
      "attack_muichiro_trans",
      "muichiro_trans_attack.png",
      {
        frameWidth: 64,
        frameHeight: 64,
      },
    );

    // 15. 네즈코 (태양의 극복 - 붉은 태양)
    this.load.spritesheet("attack_nezuko_sun", "nezuko_sun_attack.png", {
      frameWidth: 50, // 8
      frameHeight: 50,
    });

    // 유닛 이미지 설정
    for (const key in UNIT_DATA) {
      this.load.image(key, `${key}.png`);
      if (UNIT_DATA[key].cutscene) {
        const cutsceneKey = UNIT_DATA[key].cutscene;
        this.load.image(cutsceneKey, `${cutsceneKey}.png`);
      }
    }

    // 적 이미지
    this.load.image("enemy_lower", "enemy_lower.png");

    // 보스 이미지 로드
    this.load.image("boss_rui", "boss_rui.png");
    this.load.image("boss_enmu", "boss_enmu.png");
    this.load.image("boss_daki", "boss_daki.png");
    this.load.image("boss_gyokko", "boss_gyokko.png");
    this.load.image("boss_hantengu", "boss_hantengu.png");
    this.load.image("boss_akaza", "boss_akaza.png");
    this.load.image("boss_doma", "boss_doma.png");
    this.load.image("boss_koku", "boss_koku.png");
    this.load.image("boss_muzan", "boss_muzan.png");

    // [보스 컷신 이미지 로드]
    this.load.image("boss_rui_img", "boss_rui_cutscene.png");
    this.load.image("boss_enmu_img", "boss_enmu_cutscene.png");
    this.load.image("boss_daki_img", "boss_daki_cutscene.png");
    this.load.image("boss_gyokko_img", "boss_gyokko_cutscene.png");
    this.load.image("boss_hantengu_img", "boss_hantengu_cutscene.png");
    this.load.image("boss_akaza_img", "boss_akaza_cutscene.png");
    this.load.image("boss_doma_img", "boss_doma_cutscene.png");
    this.load.image("boss_koku_img", "boss_koku_cutscene.png");
    this.load.image("boss_muzan_img", "boss_muzan_cutscene.png");

    // 총알 그래픽 생성
    const g = this.make.graphics({ x: 0, y: 0, add: false });
    g.fillStyle(0xffffff, 1);
    g.fillCircle(5, 5, 5);
    g.generateTexture("bullet", 10, 10);

    this.load.on("complete", () => {
      console.log("모든 리소스 로딩 완료!");
    });
  }
  create() {
    this.scene.stop();
  }
}

// --- Scene 2: Menu (모드 선택 + 랭킹) ---
class MenuScene extends Phaser.Scene {
  constructor() {
    super("MenuScene");
  }

  create() {
    // 1. 배경 (변수에 담아서 교체 가능하게 함)
    this.bg = this.add
      .image(640, 360, "menu_bg")
      .setOrigin(0.5)
      .setDisplaySize(1280, 720);

    // 2. 메인 타이틀
    this.add
      .text(640, 80, "귀멸의 칼날\n랜덤 디펜스", {
        fontFamily: "Cafe24ClassicType",
        fontSize: "56px",
        color: "#e74c3c",
        align: "center",
        fontStyle: "bold",
        stroke: "#000000",
        strokeThickness: 6,
        shadow: { offsetX: 3, offsetY: 3, color: "#000", blur: 5, fill: true },
      })
      .setOrigin(0.5);

    // 3. 환영 메시지
    this.add
      .text(640, 180, `대원: ${currentPlayerName}`, {
        fontFamily: "Cafe24ClassicType",
        fontSize: "28px",
        color: "#3498db",
        stroke: "#000",
        strokeThickness: 4,
      })
      .setOrigin(0.5);

    // 4. 모드 설명 텍스트 스타일
    const style = {
      fontFamily: "Cafe24ClassicType",
      fontSize: "32px",
      fontStyle: "bold",
      align: "center",
      stroke: "#000",
      strokeThickness: 6,
      shadow: { offsetX: 2, offsetY: 2, color: "#000", blur: 4, fill: true },
    };

    // [화면 3분할 텍스트 배치]
    // (1) 스토리 (왼쪽 구역: x=213 정도)
    this.labelNormal = this.add
      .text(250, 260, "스토리\n(Normal)", { ...style, color: "#3498db" })
      .setOrigin(0.5);

    // (2) 지옥 (중앙 구역: x=640)
    this.labelHard = this.add
      .text(640, 260, "지옥\n(Hard)", { ...style, color: "#e74c3c" })
      .setOrigin(0.5);

    // (3) 협동 (오른쪽 구역: x=1066 정도)
    this.labelMulti = this.add
      .text(1030, 260, "협동\n(Challenge)", { ...style, color: "#9b59b6" })
      .setOrigin(0.5);

    // 5. 랭킹 타이틀 및 리스트 (하단 중앙으로 배치)
    this.modeRankTitle = this.add
      .text(640, 380, "=== 랭킹 ===", {
        ...style,
        fontSize: "24px",
        color: "#f1c40f",
      })
      .setOrigin(0.5);
    this.leaderboardText = this.add
      .text(640, 420, "로딩중...", {
        fontFamily: "Cafe24ClassicType",
        fontSize: "18px",
        color: "#fff",
        align: "center",
        lineSpacing: 8,
        stroke: "#000",
        strokeThickness: 3,
      })
      .setOrigin(0.5, 0);

    // 6. [중요] 클릭 영역 (Zone) 3분할
    // 화면 너비 1280을 3등분 -> 약 426px 씩
    const zoneNormal = this.add
      .zone(0, 0, 426, 720)
      .setOrigin(0)
      .setInteractive({ useHandCursor: true });
    const zoneHard = this.add
      .zone(426, 0, 426, 720)
      .setOrigin(0)
      .setInteractive({ useHandCursor: true });
    const zoneMulti = this.add
      .zone(852, 0, 428, 720)
      .setOrigin(0)
      .setInteractive({ useHandCursor: true });

    // 7. 이벤트 연결
    zoneNormal.on("pointerover", () => this.setMode("normal"));
    zoneHard.on("pointerover", () => this.setMode("hard"));
    zoneMulti.on("pointerover", () => this.setMode("multi"));

    // 클릭 시 게임 시작 함수 호출
    const startFunc = () => this.startSelectedMode();
    zoneNormal.on("pointerdown", startFunc);
    zoneHard.on("pointerdown", startFunc);
    zoneMulti.on("pointerdown", startFunc);

    // 초기 설정
    this.setMode(currentMode || "normal");

    // 1. 대기 중 신호를 받으면 -> 화면에 대기 텍스트 표시
    if (socket) {
      socket.off("waiting");
      socket.off("game_start");

      // 1. 대기 중 신호를 받으면 -> 화면에 대기 텍스트 표시
      socket.on("waiting", (data) => {
        console.log("대기열 등록됨");
        this.modeRankTitle.setText("=== 매칭 대기 중 ===");
        this.leaderboardText.setText(
          "다른 대원을 기다리고 있습니다...\n(잠시만 기다려주세요)",
        );
      });

      // 2. 게임 시작 신호를 받으면 -> GameScene으로 이동
      socket.on("game_start", (data) => {
        console.log("매칭 성사! 게임 시작");

        const myId = socket.id;
        const partner = data.players.find((p) => p.id !== myId);
        if (partner) {
          partnerName = partner.name;
        }

        this.scene.start("GameScene");
      });
    }
  }

  // 모드 변경 시 화면 효과
  async setMode(mode) {
    if (currentMode === mode) return;
    currentMode = mode;

    // 1. 텍스트 효과 초기화
    const resetScale = (obj) => obj.setScale(1).setAlpha(0.5);
    resetScale(this.labelNormal);
    resetScale(this.labelHard);
    resetScale(this.labelMulti);

    let bgTexture = "menu_bg";
    let title = "";

    if (mode === "normal") {
      this.labelNormal.setScale(1.3).setAlpha(1);
      bgTexture = "mode_normal";
      title = "=== 스토리 모드 랭킹 ===";
    } else if (mode === "hard") {
      this.labelHard.setScale(1.3).setAlpha(1);
      bgTexture = "mode_hard";
      title = "=== 지옥 모드 랭킹 ===";
    } else {
      this.labelMulti.setScale(1.3).setAlpha(1);
      bgTexture = "mode_multi";
      title = "=== 협동 챌린지 랭킹 ===";
    }

    // 타이틀 텍스트 업데이트
    this.modeRankTitle.setText(title);

    // 3. 배경 전환 애니메이션
    this.tweens.killTweensOf(this.bg);
    this.tweens.add({
      targets: this.bg,
      alpha: 0.3,
      duration: 150,
      ease: "Power1",
      onComplete: () => {
        this.bg.setTexture(bgTexture);
        this.bg.setDisplaySize(1280, 720);
        this.tweens.add({
          targets: this.bg,
          alpha: 1,
          duration: 350,
          ease: "Power2",
        });
      },
    });

    // 4. 랭킹 로드
    const text = await fetchLeaderboardText(mode);
    this.leaderboardText.setText(text);
  }

  async startSelectedMode() {
    console.log(`${currentMode} 모드 선택됨`);

    // 데이터를 미리 로드 (공통)
    await loadDataForMode(currentMode);

    if (currentMode === "multi") {
      // 소켓이 연결되어 있는지 확인
      if (socket && socket.connected) {
        socket.emit("join_game", { nickname: currentPlayerName });
      } else {
        // 깃허브 페이지 등 서버가 없는 환경일 때
        alert(
          "서버와 연결되어 있지 않습니다.\n싱글 모드(스토리/지옥)만 플레이 가능합니다.",
        );
      }
    } else {
      // [싱글 모드] -> 바로 시작
      this.scene.start("GameScene");
    }
  }
}

// Scene 3: Game
class GameScene extends Phaser.Scene {
  constructor() {
    super("GameScene");
  }

  init(data) {
    this.round = 1;
    this.gold = GAME_CONFIG.initialGold;
    this.lives = GAME_CONFIG.initialLives;
    this.currentTime = GAME_CONFIG.roundTime;
    this.isPaused = false;
    this.isGameOver = false;

    this.bossSpawned = false;

    this.gridSize = 6;
    this.cellSize = 60;
    this.gridOffsetX = 100;
    this.gridOffsetY = 150;
    this.gridState = Array(this.gridSize)
      .fill(null)
      .map(() => Array(this.gridSize).fill(null));

    const safeData = data || {};

    // 방장 여부 확인 (데이터가 없으면 기본값 true = 싱글 플레이어)
    this.isHost = safeData.isHost !== undefined ? safeData.isHost : true;

    // 방 이름 확인
    this.myRoomName = safeData.roomName || null;

    // 멀티 모드 여부 판단
    this.isMultiplayer = !!this.myRoomName;

    console.log(
      `게임 초기화: Host=${this.isHost}, Room=${this.myRoomName}, Multi=${this.isMultiplayer}`,
    );
  }

  getTierColor(tier) {
    switch (tier) {
      case 1:
        return "#bdc3c7";
      case 2:
        return "#2ecc71";
      case 3:
        return "#3498db";
      case 4:
        return "#9b59b6";
      case 5:
        return "#e67e22";
      case 6:
        return "#e74c3c";
      default:
        return "#ffffff";
    }
  }

  create() {
    // 배경
    this.bg = this.add
      .image(640, 360, "bg_stage1")
      .setOrigin(0.5)
      .setDisplaySize(1280, 720)
      .setInteractive();
    this.bg.setDepth(-100);

    this.input.setDefaultCursor(
      "url(assets/images/cursor.png), 14 0, pointer'",
    );

    // 로드한 "basic_bullet_img"를 기반으로 애니메이션 생성
    if (!this.anims.exists("anim_slayer_basic")) {
      this.anims.create({
        key: "anim_slayer_basic",
        // 리소스 키 이름 (BootScene과 일치해야 함)
        frames: this.anims.generateFrameNumbers("attack_slayer_basic", {
          start: 0,
          end: 4,
        }),
        frameRate: 10,
        repeat: 0, // 무한 반복
      });
    }
    // 1. 탄지로 물의 호흡
    if (!this.anims.exists("anim_tanjiro_water")) {
      this.anims.create({
        key: "anim_tanjiro_water",
        frames: this.anims.generateFrameNumbers("attack_tanjiro_water", {
          start: 0,
          end: 6,
        }), // 5프레임(0~4)
        frameRate: 15,
        repeat: 0,
      });
    }

    // 2. 젠이츠 벽력일섬
    if (!this.anims.exists("anim_zenitsu_thunder")) {
      this.anims.create({
        key: "anim_zenitsu_thunder",
        frames: this.anims.generateFrameNumbers("attack_zenitsu_thunder", {
          start: 0,
          end: 4,
        }), // 5프레임
        frameRate: 20, // 빠름
        repeat: 0,
      });
    }

    // 3. 이노스케 짐승의 호흡
    if (!this.anims.exists("anim_inosuke_beast")) {
      this.anims.create({
        key: "anim_inosuke_beast",
        frames: this.anims.generateFrameNumbers("attack_inosuke_beast", {
          start: 0,
          end: 4,
        }), // 5프레임
        frameRate: 15,
        repeat: 0,
      });
    }

    // 4. 카나오 꽃의 호흡
    if (!this.anims.exists("anim_kanao_flower")) {
      this.anims.create({
        key: "anim_kanao_flower",
        frames: this.anims.generateFrameNumbers("attack_kanao_flower", {
          start: 0,
          end: 12,
        }),
        frameRate: 10,
        repeat: 0,
      });
    }

    // 5. 까마귀 공격
    if (!this.anims.exists("anim_crow")) {
      this.anims.create({
        key: "anim_crow",
        frames: this.anims.generateFrameNumbers("attack_crow", {
          start: 0,
          end: 6,
        }),
        frameRate: 12,
        repeat: 0,
      });
    }

    // 6. 은(Kakushi) 투척
    if (!this.anims.exists("anim_kakushi")) {
      this.anims.create({
        key: "anim_kakushi",
        frames: this.anims.generateFrameNumbers("attack_kakushi_support", {
          start: 0,
          end: 3,
        }),
        frameRate: 10,
        repeat: 0,
      });
    }

    if (!this.anims.exists("anim_genya_gun")) {
      this.anims.create({
        key: "anim_genya_gun",
        frames: this.anims.generateFrameNumbers("attack_genya_gun", {
          start: 0,
          end: 0,
        }),
        frameRate: 5,
        repeat: 0,
      });
    }

    if (!this.anims.exists("anim_aoi_support")) {
      this.anims.create({
        key: "anim_aoi_support",
        frames: this.anims.generateFrameNumbers("attack_aoi_support", {
          start: 0,
          end: 6,
        }),
        frameRate: 15,
        repeat: 0,
      });
    }

    // 7. 우로코다키
    if (!this.anims.exists("anim_urokodaki")) {
      this.anims.create({
        key: "anim_urokodaki",
        frames: this.anims.generateFrameNumbers("attack_urokodaki", {
          start: 0,
          end: 6,
        }),
        frameRate: 15,
        repeat: -1,
      });
    }

    // 8. 쿠와지마 (젠이츠 스승)
    if (!this.anims.exists("anim_jigoro")) {
      this.anims.create({
        key: "anim_jigoro",
        frames: this.anims.generateFrameNumbers("attack_jigoro", {
          start: 0,
          end: 4,
        }),
        frameRate: 15,
        repeat: -1,
      });
    }

    // 9. 하가네즈카 (칼갈이/분노)
    if (!this.anims.exists("anim_haganezuka")) {
      this.anims.create({
        key: "anim_haganezuka",
        frames: this.anims.generateFrameNumbers("attack_haganezuka", {
          start: 0,
          end: 3,
        }),
        frameRate: 10,
        repeat: -1,
      });
    }

    // 10. 사비토
    if (!this.anims.exists("anim_sabito")) {
      this.anims.create({
        key: "anim_sabito",
        frames: this.anims.generateFrameNumbers("attack_sabito", {
          start: 0,
          end: 3,
        }),
        frameRate: 10,
        repeat: -1,
      });
    }

    // 11. 네즈코 (발차기 등)
    if (!this.anims.exists("anim_nezuko_box")) {
      this.anims.create({
        key: "anim_nezuko_box",
        frames: this.anims.generateFrameNumbers("attack_nezuko_box", {
          start: 0,
          end: 4,
        }),
        frameRate: 10,
        repeat: -1,
      });
    }

    // 12. 유시로 (부적)
    if (!this.anims.exists("anim_yushiro")) {
      this.anims.create({
        key: "anim_yushiro",
        frames: this.anims.generateFrameNumbers("attack_yushiro", {
          start: 0,
          end: 4,
        }),
        frameRate: 10,
        repeat: -1,
      });
    }

    // 13. 무라타 (흐릿한 물의 호흡)
    if (!this.anims.exists("anim_murata")) {
      this.anims.create({
        key: "anim_murata",
        frames: this.anims.generateFrameNumbers("attack_murata", {
          start: 0,
          end: 4,
        }),
        frameRate: 10,
        repeat: -1,
      });
    }

    // 14. 기유 (잔잔한 물결)
    if (!this.anims.exists("anim_giyu")) {
      this.anims.create({
        key: "anim_giyu",
        frames: this.anims.generateFrameNumbers("attack_giyu", {
          start: 0,
          end: 5,
        }),
        frameRate: 10,
        repeat: -1,
      });
    }

    // 15. 렌고쿠 (화염)
    if (!this.anims.exists("anim_rengoku")) {
      this.anims.create({
        key: "anim_rengoku",
        frames: this.anims.generateFrameNumbers("attack_rengoku", {
          start: 0,
          end: 7,
        }),
        frameRate: 10,
        repeat: -1,
      });
    }

    // 16. 텐겐 (소리의 호흡 - 폭발적)
    if (!this.anims.exists("anim_tengen")) {
      this.anims.create({
        key: "anim_tengen",
        frames: this.anims.generateFrameNumbers("attack_tengen", {
          start: 0,
          end: 12,
        }),
        frameRate: 10,
        repeat: -1,
      });
    }

    // 17. 시노부 (찌르기 - 매우 빠름)
    if (!this.anims.exists("anim_shinobu")) {
      this.anims.create({
        key: "anim_shinobu",
        frames: this.anims.generateFrameNumbers("attack_shinobu", {
          start: 0,
          end: 7,
        }),
        frameRate: 10,
        repeat: -1,
      });
    }

    // 18. 카나에 (꽃의 호흡)
    if (!this.anims.exists("anim_kanae")) {
      this.anims.create({
        key: "anim_kanae",
        frames: this.anims.generateFrameNumbers("attack_kanae", {
          start: 0,
          end: 7,
        }),
        frameRate: 10,
        repeat: -1,
      });
    }

    // 19. 무이치로 (안개)
    if (!this.anims.exists("anim_muichiro")) {
      this.anims.create({
        key: "anim_muichiro",
        frames: this.anims.generateFrameNumbers("attack_muichiro", {
          start: 0,
          end: 4,
        }),
        frameRate: 10, // 안개처럼 흐르듯
        repeat: -1,
      });
    }

    // 20. 미츠리 (사랑의 호흡 - 채찍처럼)
    if (!this.anims.exists("anim_mitsuri")) {
      this.anims.create({
        key: "anim_mitsuri",
        frames: this.anims.generateFrameNumbers("attack_mitsuri", {
          start: 0,
          end: 7,
        }),
        frameRate: 10,
        repeat: -1,
      });
    }

    // 21. 오바나이 (뱀)
    if (!this.anims.exists("anim_obanai")) {
      this.anims.create({
        key: "anim_obanai",
        frames: this.anims.generateFrameNumbers("attack_obanai", {
          start: 0,
          end: 5,
        }),
        frameRate: 10,
        repeat: -1,
      });
    }

    // 22. 사네미 (바람)
    if (!this.anims.exists("anim_sanemi")) {
      this.anims.create({
        key: "anim_sanemi",
        frames: this.anims.generateFrameNumbers("attack_sanemi", {
          start: 0,
          end: 4,
        }),
        frameRate: 10,
        repeat: -1,
      });
    }

    // 23. 교메이 (바위/철퇴 - 묵직함)
    if (!this.anims.exists("anim_gyomei")) {
      this.anims.create({
        key: "anim_gyomei",
        frames: this.anims.generateFrameNumbers("attack_gyomei", {
          start: 0,
          end: 29,
        }),
        frameRate: 10,
        repeat: -1,
      });
    }

    // 24. 타마요 (혈귀술)
    if (!this.anims.exists("anim_tamayo")) {
      this.anims.create({
        key: "anim_tamayo",
        frames: this.anims.generateFrameNumbers("attack_tamayo", {
          start: 0,
          end: 3,
        }),
        frameRate: 10,
        repeat: -1,
      });
    }

    // 25. 탄지로(히노카미)
    if (!this.anims.exists("anim_tanjiro_sun")) {
      this.anims.create({
        key: "anim_tanjiro_sun",
        frames: this.anims.generateFrameNumbers("attack_tanjiro_sun", {
          start: 0,
          end: 7,
        }),
        frameRate: 10,
        repeat: -1,
      });
    }
    // 26. 젠이츠(신속) - 매우 빠름
    if (!this.anims.exists("anim_zenitsu_god")) {
      this.anims.create({
        key: "anim_zenitsu_god",
        frames: this.anims.generateFrameNumbers("attack_zenitsu_god", {
          start: 0,
          end: 12,
        }),
        frameRate: 10,
        repeat: -1,
      });
    }
    // 27. 네즈코(각성)
    if (!this.anims.exists("anim_nezuko_awake")) {
      this.anims.create({
        key: "anim_nezuko_awake",
        frames: this.anims.generateFrameNumbers("attack_nezuko_awake", {
          start: 0,
          end: 8,
        }),
        frameRate: 12,
        repeat: -1,
      });
    }
    // 28. 기유(반점)
    if (!this.anims.exists("anim_giyu_mark")) {
      this.anims.create({
        key: "anim_giyu_mark",
        frames: this.anims.generateFrameNumbers("attack_giyu_mark", {
          start: 0,
          end: 8,
        }),
        frameRate: 12,
        repeat: -1,
      });
    }
    // 29. 무이치로(반점)
    if (!this.anims.exists("anim_muichiro_mark")) {
      this.anims.create({
        key: "anim_muichiro_mark",
        frames: this.anims.generateFrameNumbers("attack_muichiro_mark", {
          start: 0,
          end: 8,
        }),
        frameRate: 10,
        repeat: -1,
      });
    }
    // 30. 타마요&유시로
    if (!this.anims.exists("anim_tamayo_yushiro")) {
      this.anims.create({
        key: "anim_tamayo_yushiro",
        frames: this.anims.generateFrameNumbers("attack_tamayo_yushiro", {
          start: 0,
          end: 6,
        }),
        frameRate: 10,
        repeat: -1,
      });
    }
    // 31. 이노스케(각성)
    if (!this.anims.exists("anim_inosuke_awake")) {
      this.anims.create({
        key: "anim_inosuke_awake",
        frames: this.anims.generateFrameNumbers("attack_inosuke_awake", {
          start: 0,
          end: 3,
        }),
        frameRate: 10,
        repeat: -1,
      });
    }

    // === [Tier 6] 신화 ===

    // 32. 탄지로(13형)
    if (!this.anims.exists("anim_tanjiro_final")) {
      this.anims.create({
        key: "anim_tanjiro_final",
        frames: this.anims.generateFrameNumbers("attack_tanjiro_final", {
          start: 0,
          end: 15,
        }),
        frameRate: 15,
        repeat: -1,
      });
    }
    // 33. 교메이(반점)
    if (!this.anims.exists("anim_gyomei_mark")) {
      this.anims.create({
        key: "anim_gyomei_mark",
        frames: this.anims.generateFrameNumbers("attack_gyomei_mark", {
          start: 0,
          end: 17,
        }),
        frameRate: 15,
        repeat: -1,
      });
    }
    // 34. 요리이치
    if (!this.anims.exists("anim_yoriichi")) {
      this.anims.create({
        key: "anim_yoriichi",
        frames: this.anims.generateFrameNumbers("attack_yoriichi", {
          start: 0,
          end: 9,
        }),
        frameRate: 15,
        repeat: -1,
      });
    }
    // 35. 이노스케(산의 왕)
    if (!this.anims.exists("anim_inosuke_king")) {
      this.anims.create({
        key: "anim_inosuke_king",
        frames: this.anims.generateFrameNumbers("attack_inosuke_king", {
          start: 0,
          end: 5,
        }),
        frameRate: 10,
        repeat: -1,
      });
    }

    // === [HIDDEN] 히든 ===

    // 36. 요리이치 영식
    if (!this.anims.exists("anim_yoriichi_zero")) {
      this.anims.create({
        key: "anim_yoriichi_zero",
        frames: this.anims.generateFrameNumbers("attack_yoriichi_zero", {
          start: 0,
          end: 4,
        }),
        frameRate: 22, // 난타
        repeat: -1,
      });
    }
    // 37. 코쿠시보
    if (!this.anims.exists("anim_koku")) {
      this.anims.create({
        key: "anim_koku",
        frames: this.anims.generateFrameNumbers("attack_koku", {
          start: 0,
          end: 7,
        }),
        frameRate: 10,
        repeat: -1,
      });
    }
    // 38. 탄지로(오니의 왕)
    if (!this.anims.exists("anim_tanjiro_king")) {
      this.anims.create({
        key: "anim_tanjiro_king",
        frames: this.anims.generateFrameNumbers("attack_tanjiro_king", {
          start: 0,
          end: 14,
        }),
        frameRate: 218,
        repeat: -1,
      });
    }
    // 39. 쌍둥이의 운명
    if (!this.anims.exists("anim_twin_destiny")) {
      this.anims.create({
        key: "anim_twin_destiny",
        frames: this.anims.generateFrameNumbers("attack_twin_destiny", {
          start: 0,
          end: 6,
        }),
        frameRate: 20,
        repeat: -1,
      });
    }

    // ===============================================================
    // [신규 추가] Tier 5 & 6 추가 애니메이션 등록
    // ===============================================================

    // 1. 렌고쿠(멸살)
    if (!this.anims.exists("anim_rengoku_9th")) {
      this.anims.create({
        key: "anim_rengoku_9th",
        frames: this.anims.generateFrameNumbers("attack_rengoku_9th", {
          start: 0,
          end: 8,
        }),
        frameRate: 14,
        repeat: -1,
      });
    }
    // 2. 텐겐(악보)
    if (!this.anims.exists("anim_tengen_score")) {
      this.anims.create({
        key: "anim_tengen_score",
        frames: this.anims.generateFrameNumbers("attack_tengen_score", {
          start: 0,
          end: 10,
        }),
        frameRate: 12,
        repeat: -1,
      });
    }
    // 3. 시노부(종의형)
    if (!this.anims.exists("anim_shinobu_dance")) {
      this.anims.create({
        key: "anim_shinobu_dance",
        frames: this.anims.generateFrameNumbers("attack_shinobu_dance", {
          start: 0,
          end: 8,
        }),
        frameRate: 12,
        repeat: -1,
      });
    }
    // 4. 카나에(꽃의영)
    if (!this.anims.exists("anim_kanae_spirit")) {
      this.anims.create({
        key: "anim_kanae_spirit",
        frames: this.anims.generateFrameNumbers("attack_kanae_spirit", {
          start: 0,
          end: 11,
        }),
        frameRate: 12,
        repeat: -1,
      });
    }
    // 5. 사네미(반점)
    if (!this.anims.exists("anim_sanemi_mark")) {
      this.anims.create({
        key: "anim_sanemi_mark",
        frames: this.anims.generateFrameNumbers("attack_sanemi_mark", {
          start: 0,
          end: 8,
        }),
        frameRate: 15,
        repeat: -1,
      });
    }
    // 6. 오바나이(반점)
    if (!this.anims.exists("anim_obanai_mark")) {
      this.anims.create({
        key: "anim_obanai_mark",
        frames: this.anims.generateFrameNumbers("attack_obanai_mark", {
          start: 0,
          end: 12,
        }),
        frameRate: 15,
        repeat: -1,
      });
    }
    // 7. 미츠리(반점)
    if (!this.anims.exists("anim_mitsuri_mark")) {
      this.anims.create({
        key: "anim_mitsuri_mark",
        frames: this.anims.generateFrameNumbers("attack_mitsuri_mark", {
          start: 0,
          end: 11,
        }),
        frameRate: 15,
        repeat: -1,
      });
    }
    // 8. 렌고쿠(마지막 미소)
    if (!this.anims.exists("anim_rengoku_smile")) {
      this.anims.create({
        key: "anim_rengoku_smile",
        frames: this.anims.generateFrameNumbers("attack_rengoku_smile", {
          start: 0,
          end: 7,
        }),
        frameRate: 12,
        repeat: -1,
      });
    }

    // [신규 Tier 6]
    // 9. 젠이츠(화뢰신)
    if (!this.anims.exists("anim_zenitsu_7th")) {
      this.anims.create({
        key: "anim_zenitsu_7th",
        frames: this.anims.generateFrameNumbers("attack_zenitsu_7th", {
          start: 0,
          end: 12,
        }),
        frameRate: 20,
        repeat: -1,
      });
    }
    // 10. 기유(잔잔한 물)
    if (!this.anims.exists("anim_giyu_calm")) {
      this.anims.create({
        key: "anim_giyu_calm",
        frames: this.anims.generateFrameNumbers("attack_giyu_calm", {
          start: 0,
          end: 8,
        }),
        frameRate: 14,
        repeat: -1,
      });
    }
    // 11. 사네미(바람의 신)
    if (!this.anims.exists("anim_sanemi_god")) {
      this.anims.create({
        key: "anim_sanemi_god",
        frames: this.anims.generateFrameNumbers("attack_sanemi_god", {
          start: 0,
          end: 4,
        }),
        frameRate: 10,
        repeat: -1,
      });
    }
    // 12. 렌고쿠(마음의 불꽃)
    if (!this.anims.exists("anim_rengoku_legend")) {
      this.anims.create({
        key: "anim_rengoku_legend",
        frames: this.anims.generateFrameNumbers("attack_rengoku_legend", {
          start: 0,
          end: 8,
        }),
        frameRate: 15,
        repeat: -1,
      });
    }
    // 13. 오바나이&미츠리
    if (!this.anims.exists("anim_love_snake")) {
      this.anims.create({
        key: "anim_love_snake",
        frames: this.anims.generateFrameNumbers("attack_love_snake", {
          start: 0,
          end: 7,
        }),
        frameRate: 16,
        repeat: 0,
      });
    }

    // 14. 무이치로 (내비세)
    if (!this.anims.exists("anim_muichiro_trans")) {
      this.anims.create({
        key: "anim_muichiro_trans",
        frames: this.anims.generateFrameNumbers("attack_muichiro_trans", {
          start: 0,
          end: 8,
        }),
        frameRate: 20,
        repeat: 0,
      });
    }

    // 15. 네즈코 (태양의 극복)
    if (!this.anims.exists("anim_nezuko_sun")) {
      this.anims.create({
        key: "anim_nezuko_sun",
        frames: this.anims.generateFrameNumbers("attack_nezuko_sun", {
          start: 0,
          end: 7,
        }),
        frameRate: 10,
        repeat: 0,
      });
    }

    // 배경 클릭 시 초기화
    this.bg.on("pointerdown", () => {
      this.rangeGraphics.clear();
      this.statText.setText("유닛을 클릭하면 정보가 표시됩니다.");
      this.recipeText.setVisible(false);
      this.hoverText.setVisible(false);
      this.selectedUnit = null;
      this.btnSell.setVisible(false);
    });
    this.add.rectangle(0, 0, 1280, 720, 0x000000, 0.4).setOrigin(0);
    const darkOverlay = this.add
      .rectangle(0, 0, 1280, 720, 0x000000, 0.4)
      .setOrigin(0)
      .setInteractive();

    // 2. 검은 막을 클릭했을 때 창 닫기 기능 연결
    darkOverlay.on("pointerdown", () => {
      // (1) 선택된 유닛 정보 및 사거리 지우기
      this.rangeGraphics.clear();
      this.statText.setText("유닛을 클릭하면 정보가 표시됩니다.");
      this.hoverText.setVisible(false);

      // (2) 선택 해제 및 판매 버튼 숨기기
      this.selectedUnit = null;
      this.btnSell.setVisible(false);

      // (3) [중요] 조합법 창 닫기
      if (this.recipeContainer) {
        this.recipeContainer.setVisible(false);
      }
    });

    this.mapCenter = { x: 900, y: 360 };
    this.mapRadius = 300;
    this.add
      .circle(this.mapCenter.x, this.mapCenter.y, this.mapRadius)
      .setStrokeStyle(4, 0x444444);

    this.drawGrid();
    this.createUI();

    this.enemies = this.physics.add.group();
    this.units = this.add.group();
    this.bullets = this.physics.add.group();

    this.timeEvent = this.time.addEvent({
      delay: 1000,
      callback: this.onSecondTick,
      callbackScope: this,
      loop: true,
    });
    this.spawnTimer = this.time.addEvent({
      delay: GAME_CONFIG.spawnInterval,
      callback: this.spawnEnemy,
      callbackScope: this,
      loop: true,
    });

    this.physics.add.overlap(
      this.bullets,
      this.enemies,
      this.hitEnemy,
      null,
      this,
    );

    // ============================================================
    // 입력 핸들러 (Click / Drag 완벽 분리)
    // ============================================================
    this.input.off("dragstart");
    this.input.off("drag");
    this.input.off("dragend");

    this.input.on("dragstart", (p, o) => {
      if (this.isPaused || this.isGameOver) return;
      try {
        o.isDragging = true;
        this.hoverText.setVisible(false);
        if (this.recipeContainer) this.recipeContainer.setVisible(false);
        this.children.bringToTop(o);
        o.startX = o.x;
        o.startY = o.y;
      } catch (e) {
        console.error(e);
      }
    });

    this.input.on("drag", (p, o, x, y) => {
      if (this.isPaused || this.isGameOver) return;
      o.x = x;
      o.y = y;
    });

    this.input.on("dragend", (p, o) => {
      if (this.isPaused || this.isGameOver) return;

      // 드래그 끝 (공격 재개 가능)
      o.isDragging = false;

      try {
        const dist = Phaser.Math.Distance.Between(o.startX, o.startY, o.x, o.y);
        if (dist < 5) {
          o.x = o.startX;
          o.y = o.startY;
          this.selectUnit(o);
        } else {
          // 5픽셀 이상 움직임 = 드래그(이동/조합)
          this.handleUnitDrop(o);
        }
      } catch (e) {
        console.error("Drag Error:", e);
        if (o.startX !== undefined) {
          o.x = o.startX;
          o.y = o.startY;
        }
      }
    });
    // [스페이스바 단축키 등록]
    const spaceKey = this.input.keyboard.addKey(
      Phaser.Input.Keyboard.KeyCodes.SPACE,
    );
    spaceKey.on("down", () => {
      if (this.isPaused || this.isGameOver) return;
      if (this.selectedUnit) {
        this.sellSelectedUnit();
      }
    });

    this.input.keyboard.addCapture(Phaser.Input.Keyboard.KeyCodes.SPACE);

    if (this.isMultiplayer) {
      socket.off("sync_action");
      socket.off("game_state_change");
      socket.off("partner_disconnected");

      // [기존] 유닛/적 동기화
      socket.on("sync_action", (data) => {
        // 1. 적 생성
        if (data.type === "spawn_enemy") {
          this.createEnemyFromData(data.payload);
        }
        // 2. 적 사망 (돈 획득 포함)
        else if (data.type === "enemy_died") {
          this.handleEnemyDeath(data.payload);
        }
        // 3. 유닛 배치
        else if (data.type === "place_unit") {
          this.createPartnerUnit(data.payload);
        }
        // 유닛 삭제/회수 신호
        else if (data.type === "unit_removed") {
          this.removePartnerUnit(data.payload.uniqueId);
        }
        // [★신규] 적 데미지 동기화
        else if (data.type === "enemy_damage") {
          this.handleEnemyDamage(data.payload);
        } else if (data.type === "game_over") {
          this.gameOver();
        }
        // [신규] 라운드 동기화
        else if (data.type === "next_round") {
          // 방장이 시키는 대로 라운드 변경
          this.handleRoundEnd(data.payload.round);
        }
        // [추가] 시간 강제 동기화
        else if (data.type === "sync_time") {
          // 내 시간과 2초 이상 차이나면 방장 시간으로 강제 맞춤
          if (Math.abs(this.currentTime - data.payload.time) > 2) {
            console.log("시간 동기화 보정:", data.payload.time);
            this.currentTime = data.payload.time;
          }
          // 라운드가 다르면 라운드도 맞춤
          if (this.round !== data.payload.round) {
            this.round = data.payload.round;
            this.txtRound.setText(`ROUND: ${this.round}`);
          }
        }
      });

      // [신규] 게임 상태(속도, 정지) 동기화
      socket.on("game_state_change", (data) => {
        if (data.type === "speed") {
          this.applySpeedChange(data.value);
        } else if (data.type === "pause") {
          this.applyPause(data.isPaused);
        }
      });

      // [신규] 파트너 탈주 처리
      socket.on("partner_disconnected", () => {
        alert("동료와의 연결이 끊어졌습니다. 게임을 종료합니다.");
        this.scene.start("MenuScene"); // 메뉴로 강제 이동
      });
    }
  }

  // [라운드별 배경 교체 함수]
  updateBackground() {
    let newBgKey = "bg_stage1";

    if (this.round >= 81) {
      newBgKey = "bg_stage9"; // 81~90 (무잔 등)
    } else if (this.round >= 71) {
      newBgKey = "bg_stage8"; // 71~80 (코쿠시보)
    } else if (this.round >= 61) {
      newBgKey = "bg_stage7"; // 61~70 (도우마)
    } else if (this.round >= 51) {
      newBgKey = "bg_stage6"; // 51~60 (아카자)
    } else if (this.round >= 41) {
      newBgKey = "bg_stage5"; // 41~50 (한텐구)
    } else if (this.round >= 31) {
      newBgKey = "bg_stage4"; // 31~40 (굣코)
    } else if (this.round >= 21) {
      newBgKey = "bg_stage3"; // 21~30 (다키)
    } else if (this.round >= 11) {
      newBgKey = "bg_stage2"; // 11~20 (엔무)
    }

    if (this.bg.texture.key !== newBgKey) {
      this.bg.setTexture(newBgKey);

      this.bg.setDisplaySize(1280, 720);

      this.tweens.add({
        targets: this.bg,
        alpha: { from: 0.5, to: 1 },
        duration: 1000,
        ease: "Power2",
      });

      console.log(`배경 변경됨: ${newBgKey} (현재 라운드: ${this.round})`);
    }
  }

  drawGrid() {
    this.add.rectangle(
      this.gridOffsetX +
        (this.gridSize * this.cellSize) / 2 -
        this.cellSize / 2,
      this.gridOffsetY +
        (this.gridSize * this.cellSize) / 2 -
        this.cellSize / 2,
      this.gridSize * this.cellSize + 20,
      this.gridSize * this.cellSize + 20,
      0x111111,
    );
    for (let y = 0; y < this.gridSize; y++) {
      for (let x = 0; x < this.gridSize; x++) {
        const cx = this.gridOffsetX + x * this.cellSize;
        const cy = this.gridOffsetY + y * this.cellSize;
        this.add
          .rectangle(cx, cy, this.cellSize - 4, this.cellSize - 4, 0x222222)
          .setStrokeStyle(1, 0x555555);
      }
      const gridLabel = this.add.text(250, 280, "유닛 대기실\n   [조합창]", {
        fontFamily: "Cafe24ClassicType",
        fontSize: "34px",
        color: "#ffffff",
        fontStyle: "bold",
      });

      gridLabel.setOrigin(0.5);
      gridLabel.setAlpha(0.1);
      gridLabel.setDepth(0);
    }
  }

  createUI() {
    // 상단 UI
    // 골드 (왼쪽 상단)
    this.txtGold = this.add
      .text(60, 40, `GOLD: ${this.gold}`, {
        fontFamily: "Cafe24ClassicType",
        fontSize: "26px",
        color: "#f1c40f",
        fontStyle: "bold",
      })
      .setOrigin(0, 0.5)
      .setDepth(100);

    // ----------------------------------------------------------------
    // [상단 중앙] 1열 세로 정렬 (라운드 -> 시간 -> 혈귀)
    // ----------------------------------------------------------------
    const topCenterX = 550;

    // (1) 라운드
    this.txtRound = this.add
      .text(topCenterX, 40, `ROUND: ${this.round}`, {
        fontFamily: "Cafe24ClassicType",
        fontSize: "20px",
        color: "#fff",
      })
      .setOrigin(0.5, 0.5)
      .setDepth(100);

    // (2) 시간 (라운드 아래)
    this.txtTime = this.add
      .text(topCenterX, 70, `TIME: ${this.currentTime}`, {
        fontFamily: "Cafe24ClassicType",
        fontSize: "32px",
        color: "#00ff00",
      })
      .setOrigin(0.5, 0.5)
      .setDepth(100);

    // (3) 남은 혈귀 (시간 아래)
    this.txtEnemyCount = this.add
      .text(topCenterX, 95, `남은 혈귀: 0 / ${GAME_CONFIG.maxEnemies}`, {
        fontFamily: "Cafe24ClassicType",
        fontSize: "16px",
        color: "#aaa",
      })
      .setOrigin(0.5, 0.5)
      .setDepth(100);

    // ----------------------------------------------------------------
    // [왼쪽 하단] 유닛 정보 & 버튼들
    // ----------------------------------------------------------------

    // 유닛 정보창 (그리드 바로 아래 배치)
    this.statText = this.add
      .text(280, 540, "유닛을 클릭하면 정보가 표시됩니다.", {
        fontFamily: "Cafe24ClassicType",
        fontSize: "18px",
        color: "#ffffff",
        backgroundColor: "#000000aa",
        padding: { x: 10, y: 5 },
      })
      .setOrigin(0.5, 0.5)
      .setDepth(100);

    // 유닛 판매 버튼
    this.btnSell = this.add.container(380, 600).setVisible(false).setDepth(101);

    // [수정] 버튼 크기를 키워서 (높이 40 -> 55) 두 줄이 들어가게 함
    const sellBg = this.add
      .rectangle(0, 0, 160, 55, 0xe74c3c)
      .setInteractive({ useHandCursor: true });

    // [수정] 판매 가격 텍스트 (위쪽으로 배치 y: -10)
    this.txtSell = this.add
      .text(0, -10, "판매 (+50G)", {
        fontFamily: "Cafe24ClassicType",
        fontSize: "20px",
        color: "#fff",
        fontStyle: "bold",
      })
      .setOrigin(0.5);

    // [신규] 스페이스바 단축키 안내 텍스트
    const txtShortcut = this.add
      .text(0, 13, "[ Space ]", {
        fontFamily: "Cafe24ClassicType",
        fontSize: "18px",
        color: "#ffcccc",
      })
      .setOrigin(0.5);

    if (currentMode === "multi" && partnerName) {
      this.add
        .text(1260, 700, `Together with: ${partnerName}`, {
          fontFamily: "Cafe24ClassicType",
          fontSize: "22px",
          color: "#9b59b6",
          stroke: "#000",
          strokeThickness: 4,
        })
        .setOrigin(1, 1)
        .setDepth(100);
    }

    // 컨테이너에 배경, 가격, 단축키 3개를 모두 담음
    this.btnSell.add([sellBg, this.txtSell, txtShortcut]);

    // 판매 버튼 클릭 이벤트
    sellBg.on("pointerdown", () => this.sellSelectedUnit());
    sellBg.on("pointerover", () => sellBg.setFillStyle(0xc0392b));
    sellBg.on("pointerout", () => sellBg.setFillStyle(0xe74c3c));

    // 버튼 그룹 (소환, 일시정지) - 1열 세로 배치
    // 왼쪽 구석(x=150) 쯤에 세로로 배치
    const btnX = 150;

    // (1) 소환 버튼
    const btnSummon = this.add
      .rectangle(btnX, 590, 200, 45, 0x3498db)
      .setInteractive({ useHandCursor: true });
    this.add
      .text(btnX, 590, `유닛 소환 (${GAME_CONFIG.unitSummonCost}G)`, {
        fontFamily: "Cafe24ClassicType",
        fontSize: "22px",
        color: "#2c0404",
      })
      .setOrigin(0.5);
    btnSummon.on("pointerdown", () => this.summonUnit());

    // (2) [기능] 레시피 북 버튼
    const btnRecipe = this.add
      .rectangle(btnX, 640, 200, 45, 0x8977ad)
      .setInteractive({ useHandCursor: true });
    this.add
      .text(btnX, 640, "조합법 보기", {
        fontFamily: "Cafe24ClassicType",
        fontSize: "24px",
        color: "#2c0404",
      })
      .setOrigin(0.5);
    btnRecipe.on("pointerdown", () => this.toggleRecipePopup());

    // (3) 일시정지 버튼
    const btnPause = this.add
      .rectangle(btnX, 690, 200, 45, 0x95a5a6)
      .setInteractive({ useHandCursor: true });
    this.txtPause = this.add
      .text(btnX, 690, "일시 정지", {
        fontFamily: "Cafe24ClassicType",
        fontSize: "24px",
        color: "#2c0404",
      })
      .setOrigin(0.5);
    btnPause.on("pointerdown", () => this.togglePause());

    // (4) 2배속 버튼 기능
    const btnSpeed = this.add
      .rectangle(370, 690, 200, 45, 0x95a5a6)
      .setInteractive({ useHandCursor: true });

    this.txtSpeed = this.add
      .text(370, 690, "속도: 1x", {
        fontFamily: "Cafe24ClassicType",
        fontSize: "24px",
        color: "0x000000",
      })
      .setOrigin(0.5);

    btnSpeed.on("pointerdown", () => this.toggleSpeed());

    this.rangeGraphics = this.add.graphics().setDepth(50);

    this.recipeContainer = this.add
      .container(0, 0)
      .setDepth(9999)
      .setVisible(false);

    this.hoverText = this.add
      .text(0, 0, "", {
        fontFamily: "Cafe24ClassicType",
        fontSize: "16px",
        backgroundColor: "#00000088",
        padding: { x: 5, y: 5 },
        color: "#ffffff",
      })
      .setOrigin(0.5, 1.5)
      .setVisible(false)
      .setDepth(200);

    this.pauseOverlay = this.add
      .rectangle(640, 360, 1280, 720, 0x000000, 0.7)
      .setVisible(false)
      .setDepth(9000);
    this.pauseText = this.add
      .text(640, 360, "PAUSED", {
        fontFamily: "Cafe24ClassicType",
        fontSize: "64px",
      })
      .setOrigin(0.5)
      .setVisible(false)
      .setDepth(9001);

    // 7. 배경 클릭 시 선택 해제 및 판매 버튼 숨기기 로직
    this.bg.on("pointerdown", () => {
      // (1) 그래픽 및 텍스트 초기화
      this.rangeGraphics.clear();
      this.statText.setText("유닛을 클릭하면 정보가 표시됩니다.");
      // (2) 툴팁 숨기기
      this.hoverText.setVisible(false);
      // (3) [중요] 조합법 컨테이너 숨기기!
      if (this.recipeContainer) {
        this.recipeContainer.setVisible(false);
      }
      // (4) 선택 변수 비우기 & 판매 버튼 숨기기
      this.selectedUnit = null;
      this.btnSell.setVisible(false);
    });
    // 8. 레시피 팝업 미리 생성
    this.createRecipePopup();
  }

  // 1. 배속 버튼 눌렀을 때
  toggleSpeed() {
    // 멀티 모드라면 -> 서버에 "속도 바꿔줘" 요청
    if (this.isMultiplayer) {
      const nextSpeed = this.time.timeScale > 1 ? 1.0 : 2.0;
      socket.emit("game_state_change", {
        room: this.myRoomName,
        type: "speed",
        value: nextSpeed,
      });
      return; // 내 거 바로 실행 안 함 (서버 응답 오면 실행)
    }

    // 싱글 모드면 기존 로직 실행
    this.applySpeedChange(this.time.timeScale > 1 ? 1.0 : 2.0);
  }

  // [신규] 실제 속도 변경 로직 분리
  applySpeedChange(targetSpeed) {
    this.time.timeScale = targetSpeed;
    this.physics.world.timeScale = 1 / targetSpeed;
    this.txtSpeed.setText(`속도: ${targetSpeed}x`);
    if (targetSpeed === 2) this.txtSpeed.setColor("#ffff00");
    else this.txtSpeed.setColor("0x000000");
  }

  // 선택된 유닛 판매
  sellSelectedUnit() {
    if (!this.selectedUnit || !this.selectedUnit.active) return;

    const unit = this.selectedUnit;
    const sellPrice = unit.dataVal.tier * 50; // 판매 가격 계산

    // 골드 증가
    this.gold += sellPrice;
    this.txtGold.setText(`GOLD: ${this.gold}`);

    // 그리드 점유 해제
    if (unit.gridX !== -1 && unit.gridY !== -1) {
      this.gridState[unit.gridY][unit.gridX] = null;
    }

    // 돈 획득 텍스트 이펙트
    const txt = this.add
      .text(unit.x, unit.y, `+${sellPrice}G`, {
        fontFamily: "Cafe24ClassicType",
        fontSize: "24px",
        color: "#f1c40f",
        stroke: "#000",
        strokeThickness: 2,
      })
      .setOrigin(0.5)
      .setDepth(500);

    this.tweens.add({
      targets: txt,
      y: unit.y - 50,
      alpha: 0,
      duration: 1000,
      onComplete: () => txt.destroy(),
    });

    // [★추가] 필드에 있던 유닛을 팔았다면 공유 화면에서도 삭제
    if (unit.gridX === -1 && this.isMultiplayer) {
      socket.emit("sync_action", {
        room: this.myRoomName,
        type: "unit_removed",
        payload: { uniqueId: unit.myUniqueId },
      });
    }

    // 유닛 제거
    unit.destroy();

    // UI 초기화
    this.selectedUnit = null;
    this.btnSell.setVisible(false);
    this.rangeGraphics.clear();
    this.statText.setText("유닛이 판매되었습니다.");
    // this.recipeText.setVisible(false);
    if (this.recipeContainer) this.recipeContainer.setVisible(false);
  }

  // 페이지 기능이 추가된 조합법 팝업
  createRecipePopup() {
    // 1. 컨테이너 위치: 그리드 중앙
    this.recipePopup = this.add
      .container(200, 250)
      .setDepth(9000)
      .setVisible(false);

    // 2. 배경 (크기 유지)
    const bg = this.add
      .rectangle(0, 0, 400, 450, 0x000000, 0.9)
      .setStrokeStyle(2, 0x9b59b6)
      .setInteractive();

    // 3. 제목
    const title = this.add
      .text(0, -200, "- 조합법 목록 -", {
        fontFamily: "Cafe24ClassicType",
        fontSize: "22px",
        color: "#f1c40f",
        fontStyle: "bold",
      })
      .setOrigin(0.5);

    // 4. 내용을 표시할 텍스트 객체 (처음엔 빈칸)
    this.recipeContentText = this.add
      .text(0, -160, "", {
        fontFamily: "Cafe24ClassicType",
        fontSize: "15px", // 글자 크기 약간 축소
        color: "#ffffff",
        lineSpacing: 0, // 줄 간격 조정
        align: "center",
      })
      .setOrigin(0.5, 0);

    // 5. 페이지 번호 표시
    this.pageText = this.add
      .text(0, 180, "1 / 1", {
        fontSize: "16px",
        color: "#aaa",
      })
      .setOrigin(0.5);

    // 6. [이전] [다음] 버튼 만들기
    this.btnPrev = this.add
      .text(-120, 180, "◀ 이전", {
        fontSize: "18px",
        color: "#f1c40f",
        fontStyle: "bold",
      })
      .setInteractive({ useHandCursor: true })
      .setOrigin(0.5);

    this.btnNext = this.add
      .text(120, 180, "다음 ▶", {
        fontSize: "18px",
        color: "#f1c40f",
        fontStyle: "bold",
      })
      .setInteractive({ useHandCursor: true })
      .setOrigin(0.5);

    // 버튼 이벤트 연결
    this.btnPrev.on("pointerdown", () => this.changeRecipePage(-1));
    this.btnNext.on("pointerdown", () => this.changeRecipePage(1));

    // 닫기 안내 (배경 클릭 시 닫힘)
    bg.on("pointerdown", () => this.toggleRecipePopup());

    // 팝업에 모두 담기
    this.recipePopup.add([
      bg,
      title,
      this.recipeContentText,
      this.pageText,
      this.btnPrev,
      this.btnNext,
    ]);

    // 데이터 정렬 및 초기화
    this.currentRecipePage = 0;
    this.itemsPerPage = 6; // 한 페이지에 6개씩 보여주기 (박스 크기에 맞춰 조절)
    this.sortedRecipes = [];

    if (typeof RECIPES !== "undefined") {
      this.sortedRecipes = [...RECIPES].sort((r1, r2) => {
        const t1 = UNIT_DATA[r1.result]?.tier || 0;
        const t2 = UNIT_DATA[r2.result]?.tier || 0;
        return t1 - t2;
      });
    }

    // 첫 페이지 그리기
    this.showRecipePage();
  }
  // 페이지 변경 처리
  changeRecipePage(delta) {
    const maxPage =
      Math.ceil(this.sortedRecipes.length / this.itemsPerPage) - 1;
    let newPage = this.currentRecipePage + delta;

    // 페이지 범위 체크
    if (newPage < 0) newPage = 0;
    if (newPage > maxPage) newPage = maxPage;

    // 페이지가 바뀌었으면 갱신
    if (newPage !== this.currentRecipePage) {
      this.currentRecipePage = newPage;
      this.showRecipePage();
    }
  }

  // 현재 페이지 내용 그리기
  showRecipePage() {
    if (this.sortedRecipes.length === 0) {
      this.recipeContentText.setText("데이터 없음");
      return;
    }

    const start = this.currentRecipePage * this.itemsPerPage;
    const end = start + this.itemsPerPage;
    const pageItems = this.sortedRecipes.slice(start, end);

    let contentStr = "";
    pageItems.forEach((recipe) => {
      if (recipe.hidden) return;

      const nameA = UNIT_DATA[recipe.a].name;
      const nameB = UNIT_DATA[recipe.b].name;
      const resData = UNIT_DATA[recipe.result];

      // 보기 좋게 포맷팅
      contentStr += `[★${resData.tier}] ${resData.name}\n= ${nameA} + ${nameB}\n\n`;
    });

    // 텍스트 업데이트
    this.recipeContentText.setText(contentStr);

    // 페이지 번호 업데이트
    const maxPage = Math.ceil(this.sortedRecipes.length / this.itemsPerPage);
    this.pageText.setText(`${this.currentRecipePage + 1} / ${maxPage}`);

    // 버튼 활성/비활성 시각적 처리
    this.btnPrev.setAlpha(this.currentRecipePage === 0 ? 0.3 : 1);
    this.btnNext.setAlpha(this.currentRecipePage === maxPage - 1 ? 0.3 : 1);
  }

  // [기능] 레시피 팝업 토글
  toggleRecipePopup() {
    const isVisible = this.recipePopup.visible;
    this.recipePopup.setVisible(!isVisible);
  }

  onSecondTick() {
    if (this.isPaused || this.isGameOver) return;
    this.currentTime--;

    // 남은 시간이 5초 이하가 되면 적 생성 타이머를 멈춤
    if (this.currentTime <= 5) {
      if (!this.spawnTimer.paused) {
        this.spawnTimer.paused = true; // 타이머 일시 정지
      }
    } else {
      // 시간이 넉넉할 땐 타이머가 계속 돌아야 함
      if (this.spawnTimer.paused) {
        this.spawnTimer.paused = false;
      }
    }

    // 시간 임박 효과 (화면 붉어짐)
    if (this.round % ENEMY_CONFIG.bossInterval === 0) {
      this.txtTime.setColor("#ff0000");
      this.bg.setTint(0xff5555);
    } else {
      this.txtTime.setColor("#00ff00");
      this.bg.clearTint();
    }

    this.txtTime.setText(`TIME: ${this.currentTime}`);

    if (this.currentTime <= 0) {
      // 1. 멀티 모드일 때: 방장이 아니면 아무것도 안 함 (방장 신호 대기)
      if (this.isMultiplayer && !this.isHost) {
        return;
      }

      // 2. 싱글이거나 방장인 경우: 라운드 넘김 로직 실행
      this.processRoundEnd();
    }

    // 시간이 0이 되었을 때의 처리
    if (this.currentTime <= 0) {
      // 1. 현재가 보스 라운드인지 확인 (10, 20, 30...)
      const isBossRound = this.round % 10 === 0;

      // 2. 살아있는 보스가 있는지 확인
      // (enemies 그룹에서 active 상태이고 isBoss 속성이 true인 녀석을 찾음)
      const liveBoss = this.enemies
        .getChildren()
        .find((e) => e.active && e.isBoss);

      if (isBossRound && liveBoss) {
        // 보스 라운드인데 시간이 0이고, 보스가 살아있다? -> 게임 오버!
        this.gameOver();
      } else {
        // 일반 라운드거나, 보스를 이미 잡았다면 -> 다음 라운드 진행
        this.handleRoundEnd();
      }

      if (this.isMultiplayer && this.isHost) {
        socket.emit("sync_action", {
          room: this.myRoomName,
          type: "sync_time", // 시간 동기화 신호
          payload: {
            time: this.currentTime,
            round: this.round,
          },
        });
      }
    }
  }

  // 데이터에 연결된 다른 이미지(컷신)를 띄우는 이펙트
  showCombinationEffect(key, tier) {
    const cx = 640;
    const cy = 360;

    // 1. 사용할 이미지 키 결정
    // 기본값은 유닛 키(도트)지만, cutscene 데이터가 있으면 그걸 사용
    let imageKey = key;
    if (UNIT_DATA[key].cutscene) {
      imageKey = UNIT_DATA[key].cutscene;
    }

    // 2. 배경 섬광
    const flash = this.add
      .rectangle(cx, cy, 1280, 720, 0xffffff)
      .setDepth(6000)
      .setAlpha(0);

    // 3. 이미지 생성 (imageKey 사용)
    const img = this.add
      .sprite(cx, cy, imageKey)
      .setDepth(6001)
      .setScale(0)
      .setAlpha(0)
      .setOrigin(0.5); // 중심 기준

    // 화면의 80% 영역(최대 크기 제한) 설정
    const maxW = 1280 * 0.8;
    const maxH = 720 * 0.8;
    // 원본 이미지 크기 가져오기
    const imgW = img.width;
    const imgH = img.height;
    // 가로 배율과 세로 배율 중 '더 작은 쪽'을 선택해야 비율 유지
    const scaleX = maxW / imgW;
    const scaleY = maxH / imgH;

    // 최종 목표 크기 (너무 작으면 최소 1배는 유지하도록 설정 가능)
    let finalScale = Math.min(scaleX, scaleY);
    // 이미지가 너무 작아서 화면에 꽉 채우고 싶다면 아래 주석 해제
    // if (finalScale < 1) finalScale = 0.9;

    // 4. 텍스트 설정
    let msg = "EVOLUTION!";
    let color = "#ffffff";
    if (tier === 4) {
      msg = "EPIC COMBINATION!";
      color = "#9b59b6";
    } else if (tier === 5) {
      msg = "LEGENDARY AWAKENING!";
      color = "#e67e22";
    } else if (tier === 6) {
      msg = "GOD TIER!";
      color = "#e74c3c";
    }

    const text = this.add
      .text(cx, cy + 250, msg, {
        fontFamily: "Cafe24ClassicType",
        fontSize: "48px",
        color: color,
        stroke: "#ffffff",
        strokeThickness: 4,
        fontStyle: "bold",
      })
      .setOrigin(0.5)
      .setDepth(6001)
      .setAlpha(0)
      .setScale(0.5);

    // === 애니메이션 ===
    this.tweens.add({
      targets: flash,
      alpha: { from: 1, to: 0 },
      duration: 500,
      onStart: () => {
        // 이미지 애니메이션: 0에서 계산된 finalScale까지 커짐
        this.tweens.add({
          targets: img,
          scale: { from: 0, to: finalScale }, // 계산된 비율 적용!!
          alpha: { from: 0, to: 1 },
          duration: 800,
          ease: "Back.out",
        });

        this.tweens.add({
          targets: text,
          scale: { from: 0.5, to: 1.2 },
          alpha: 1,
          duration: 600,
          ease: "Back.out",
          delay: 200,
        });
      },
      onComplete: () => {
        this.time.delayedCall(1400, () => {
          this.tweens.add({
            targets: [img, text],
            alpha: 0,
            scale: finalScale * 1.5, // 사라질 떼 크기조정
            duration: 500,
            onComplete: () => {
              img.destroy();
              text.destroy();
              flash.destroy();
            },
          });
        });
      },
    });
  }

  // [신규] 라운드 종료 판단 (방장만 실행)
  processRoundEnd() {
    // 보스 라운드 체크 등 기존 로직
    const isBossRound = this.round % 10 === 0;
    const liveBoss = this.enemies
      .getChildren()
      .find((e) => e.active && e.isBoss);

    if (isBossRound && liveBoss) {
      this.gameOver(); // 보스 못 잡음

      // 멀티면 게임오버 신호 전송 (위에서 update에 넣었지만 확실하게 한번 더)
      if (this.isMultiplayer) {
        socket.emit("sync_action", {
          room: this.myRoomName,
          type: "game_over",
          payload: {},
        });
      }
    } else {
      // 다음 라운드로 진행!
      const nextRound = this.round + 1;

      // 내 화면 갱신
      this.handleRoundEnd(nextRound);

      // 방원들에게 "다음 라운드로 가라!" 명령
      if (this.isMultiplayer) {
        socket.emit("sync_action", {
          room: this.myRoomName,
          type: "next_round",
          payload: { round: nextRound },
        });
      }
    }
  }

  // 실제 라운드 값 갱신 (방장/참가자 모두 실행)
  handleRoundEnd(serverRound) {
    // 서버에서 준 라운드 값으로 덮어씌움 (동기화)
    if (serverRound) this.round = serverRound;
    else this.round++;

    this.updateBackground();
    this.currentTime = GAME_CONFIG.roundTime;
    this.bossSpawned = false;
    this.spawnTimer.paused = false;

    this.txtRound.setText(`ROUND: ${this.round}`);
    this.txtTime.setText(`TIME: ${this.currentTime}`);

    // 보스 라운드 체크 (10라운드 단위)
    if (this.round % ENEMY_CONFIG.bossInterval === 0) {
      // 현재 라운드에 맞는 보스 정보 찾기
      let bossInfo = null;
      let bossKey = "";

      // spawnEnemy와 동일한 순서로 업데이트
      if (this.round === 10) {
        bossKey = "boss_rui";
        bossInfo = ENEMY_CONFIG.types.boss_rui;
      } else if (this.round === 20) {
        bossKey = "boss_enmu";
        bossInfo = ENEMY_CONFIG.types.boss_enmu;
      } else if (this.round === 30) {
        bossKey = "boss_daki";
        bossInfo = ENEMY_CONFIG.types.boss_daki;
      } else if (this.round === 40) {
        bossKey = "boss_gyokko"; // 굣코
        bossInfo = ENEMY_CONFIG.types.boss_gyokko;
      } else if (this.round === 50) {
        bossKey = "boss_hantengu"; // 한텐구
        bossInfo = ENEMY_CONFIG.types.boss_hantengu;
      } else if (this.round === 60) {
        bossKey = "boss_akaza"; // 아카자
        bossInfo = ENEMY_CONFIG.types.boss_akaza;
      } else if (this.round === 70) {
        bossKey = "boss_doma"; // 도우마
        bossInfo = ENEMY_CONFIG.types.boss_doma;
      } else if (this.round === 80) {
        bossKey = "boss_koku"; // 코쿠시보
        bossInfo = ENEMY_CONFIG.types.boss_koku;
      } else if (this.round >= 90) {
        bossKey = "boss_muzan"; // 무잔
        bossInfo = ENEMY_CONFIG.types.boss_muzan;
      }

      if (bossInfo) {
        const cutsceneKey = bossInfo.cutscene || null;
        this.showBossCutscene(bossKey, bossInfo.name, cutsceneKey);
        return;
      }
    }

    // 일반 라운드 알림 메시지
    const notice = this.add
      .text(640, 360, `ROUND ${this.round} START!`, {
        fontFamily: "Cafe24ClassicType",
        fontSize: "48px",
        color: "#ffff00",
        stroke: "#000",
        strokeThickness: 4,
      })
      .setOrigin(0.5)
      .setDepth(500);

    this.time.delayedCall(2000, () => notice.destroy());
  }

  spawnEnemy() {
    // 1. 기본 체크 (일시정지, 게임오버, 시간확인)
    if (this.isPaused || this.isGameOver) return;
    if (this.currentTime <= 5) return;

    // [멀티플레이] 내가 방장이 아니면 생성 금지
    if (this.isMultiplayer && !this.isHost) return;

    // 2. 적 정보 결정 (보스 라운드 체크 등)
    const isBossRound = this.round % ENEMY_CONFIG.bossInterval === 0;
    if (isBossRound && this.bossSpawned) return;

    // 3. 적 스펙 계산
    let key = "enemy_lower";
    let hp = this.round * 150;
    let moveSpeed = 20;
    let isBoss = false;

    // [보스 등장 로직] 라운드별 보스 교체
    if (isBossRound) {
      this.bossSpawned = true;
      isBoss = true;
      moveSpeed = 3;

      if (this.round === 10) {
        key = "boss_rui"; // 하현5 루이
        hp = ENEMY_CONFIG.types.boss_rui.hpMult;
      } else if (this.round === 20) {
        key = "boss_enmu"; // 하현1 엔무
        hp = ENEMY_CONFIG.types.boss_enmu.hpMult;
      } else if (this.round === 30) {
        key = "boss_daki"; // 상현6 다키
        hp = ENEMY_CONFIG.types.boss_daki.hpMult;
      } else if (this.round === 40) {
        key = "boss_gyokko";
        hp = ENEMY_CONFIG.types.boss_gyokko.hpMult;
      } else if (this.round === 50) {
        key = "boss_hantengu";
        hp = ENEMY_CONFIG.types.boss_hantengu.hpMult;
      } else if (this.round === 60) {
        key = "boss_akaza";
        hp = ENEMY_CONFIG.types.boss_akaza.hpMult;
      } else if (this.round === 70) {
        key = "boss_doma";
        hp = ENEMY_CONFIG.types.boss_doma.hpMult;
      } else if (this.round === 80) {
        key = "boss_koku";
        hp = ENEMY_CONFIG.types.boss_koku.hpMult;
      } else if (this.round >= 90) {
        key = "boss_muzan";
        hp = ENEMY_CONFIG.types.boss_muzan.hpMult;
        moveSpeed = 2;
      }
    } else {
      // [잡몹 라운드]
      let baseHp = this.round * 200;

      if (this.round > 10) baseHp += this.round * this.round * 30;
      if (this.round >= 20) baseHp = baseHp * 1.5;

      // [하드 모드]
      if (currentMode === "hard") {
        if (this.round > 1) baseHp += this.round * this.round * 150;
        baseHp = baseHp * 1.5;
        if (this.round > 90) baseHp = baseHp * Math.pow(1.05, this.round - 90);
      }

      // [★수정] 멀티 모드
      if (currentMode === "multi") {
        // 1. 하드 모드와 똑같은 제곱 공식 적용
        if (this.round > 1) baseHp += this.round * this.round * 150;

        // 2. 그리고 전체 체력 1.5배 (하드 동일)
        baseHp = baseHp * 1.5;

        // 3. [멀티 전용] 2명이니까 체력 1.5배 더!
        baseHp = baseHp * 1.5;

        // 4. 무한 라운드 복리
        if (this.round > 90) baseHp = baseHp * Math.pow(1.1, this.round - 90);
      }

      hp = Math.floor(baseHp);
    }

    // 4. 적 생성 데이터 패키징
    const startAngle = 0;
    const enemyData = {
      key: key,
      hp: hp,
      maxHp: hp,
      moveSpeed: moveSpeed,
      isBoss: isBoss,
      startAngle: startAngle,

      startX: this.mapCenter.x + Math.cos(startAngle) * (this.mapRadius - 20),
      startY: this.mapCenter.y + Math.sin(startAngle) * (this.mapRadius - 20),
      id: Date.now() + Math.random(),
    };

    // 5. 내 화면에 생성 (방장 본인)
    this.createEnemyFromData(enemyData);

    // 6. 방원에게 전송 (멀티일 경우)
    if (this.isMultiplayer && this.isHost) {
      if (typeof socket !== "undefined") {
        socket.emit("sync_action", {
          room: this.myRoomName,
          type: "spawn_enemy",
          payload: enemyData,
        });
      }
    }
  }

  createEnemyFromData(data) {
    const enemy = this.enemies.create(data.startX, data.startY, data.key);

    if (data.isBoss) {
      enemy.setDisplaySize(120, 140);
      enemy.setTint(0xffffff);
      enemy.body.setSize(10, 10);
      enemy.isBoss = true;
    } else {
      enemy.setDisplaySize(80, 90);
      enemy.body.setSize(10, 10);
      enemy.body.setOffset(15, 17.5);
      enemy.isBoss = false;
    }

    enemy.hp = data.hp;
    enemy.maxHp = data.maxHp;
    enemy.pathAngle = data.startAngle;
    enemy.moveSpeed = data.moveSpeed;
    enemy.uniqueId = data.id;

    // 체력바 생성
    enemy.hpBar = this.add.graphics();
    enemy.hpBar.setDepth(enemy.depth + 1);
  }

  // [수정] 적 사망 처리 + 돈 획득
  handleEnemyDeath(payload) {
    const targetId = payload.uniqueId;
    const isBoss = payload.isBoss;

    const targetEnemy = this.enemies
      .getChildren()
      .find((e) => e.uniqueId === targetId);

    if (targetEnemy) {
      if (targetEnemy.hpBar) targetEnemy.hpBar.destroy();

      // 이펙트 표시를 위해 좌표 저장
      const ex = targetEnemy.x;
      const ey = targetEnemy.y;

      targetEnemy.destroy();

      // [★핵심] 파트너가 죽여도 나한테 돈 들어옴!
      let reward = 0;
      if (isBoss) {
        reward = 1000;
        this.showGoldEffect(ex, ey, "+1000G", "#ff0000", 30);
      } else {
        reward = 5 + Math.floor(this.round / 4);
        if (reward > 10) reward = 10;
      }

      this.gold += reward;
      this.txtGold.setText(`GOLD: ${this.gold}`);
    }
  }

  // [신규] 데미지 동기화 처리
  handleEnemyDamage(payload) {
    const targetEnemy = this.enemies
      .getChildren()
      .find((e) => e.uniqueId === payload.uniqueId);
    if (targetEnemy && targetEnemy.active) {
      targetEnemy.hp -= payload.damage; // 체력 깎기

      // 시각 효과 (깜빡임)
      targetEnemy.setTint(0xff0000);
      this.time.delayedCall(100, () => targetEnemy.clearTint());

      // 체력바 갱신 (이미 update에서 그려지고 있다면 자동 반영되겠지만, 강제 갱신 필요 시 여기서)
    }
  }

  summonUnit() {
    if (this.isPaused || this.isGameOver) return;
    if (this.gold < GAME_CONFIG.unitSummonCost) return;

    // 빈자리 찾기
    let emptySlots = [];
    for (let y = 0; y < this.gridSize; y++) {
      for (let x = 0; x < this.gridSize; x++) {
        if (this.gridState[y][x] === null) emptySlots.push({ x, y });
      }
    }

    // 자리가 없으면 소환 불가 + 알림
    if (emptySlots.length === 0) {
      const fullText = this.add
        .text(150, 600, "대기실이 꽉 찼습니다!", {
          color: "#ff0000",
          fontFamily: "Cafe24ClassicType",
          fontSize: "14px",
        })
        .setOrigin(0.5);
      this.time.delayedCall(1000, () => fullText.destroy());
      return;
    }

    // 골드 차감
    this.gold -= GAME_CONFIG.unitSummonCost;
    this.txtGold.setText(`GOLD: ${this.gold}`);

    // -----------------------------------------------------------
    // [확률 뽑기 로직]
    // 1~100 사이의 숫자를 뽑아서 티어 결정
    // -----------------------------------------------------------
    const chance = Phaser.Math.Between(1, 100);
    let targetTier = 1;

    if (chance <= 10) {
      targetTier = 3; // 10% 확률 (희귀)
    } else if (chance <= 30) {
      targetTier = 2; // 30% 확률 (고급)
    } else {
      targetTier = 1; // 60% 확률 (일반)
    }

    const pool = Object.keys(UNIT_DATA).filter(
      (k) => UNIT_DATA[k].tier === targetTier,
    );

    const randomKey = Phaser.Utils.Array.GetRandom(pool);
    const slot = Phaser.Utils.Array.GetRandom(emptySlots);

    this.createUnitAt(slot.x, slot.y, randomKey);

    // 3티어 뽑으면 축하 이펙트 텍스트
    if (targetTier === 3) {
      const luckyText = this.add
        .text(
          slot.x * this.cellSize + this.gridOffsetX,
          slot.y * this.cellSize + this.gridOffsetY,
          "JACKPOT!!",
          {
            fontFamily: "Cafe24ClassicType",
            fontSize: "12px",
            color: "#ffff00",
            stroke: "#ff0000",
            strokeThickness: 2,
          },
        )
        .setOrigin(0.5)
        .setDepth(300);

      this.tweens.add({
        targets: luckyText,
        y: luckyText.y - 50,
        alpha: 0,
        duration: 1000,
        onComplete: () => luckyText.destroy(),
      });
    }
  }

  // [생성된 유닛 설정]
  createUnitAt(gx, gy, key) {
    const worldX = this.gridOffsetX + gx * this.cellSize;
    const worldY = this.gridOffsetY + gy * this.cellSize;

    // 유닛 생성
    const unit = this.add
      .sprite(worldX, worldY, key)
      .setInteractive({ draggable: true });

    unit.setDisplaySize(80, 85);
    unit.unitKey = key;
    unit.dataVal = UNIT_DATA[key];
    unit.lastFired = 0;
    unit.gridX = gx;
    unit.gridY = gy;

    // [수정] 소켓이 있으면 소켓ID, 없으면 'guest'라는 이름으로 ID 생성
    const ownerPrefix = socket && socket.id ? socket.id : "guest";
    unit.myUniqueId = `${ownerPrefix}_${Date.now()}_${Math.random()}`;

    this.setupUnitEvents(unit);
    this.gridState[gy][gx] = unit;
    this.units.add(unit);
  }

  // [신규] 필드 좌표에 유닛 직접 생성 (조합용)
  createUnitDirectly(x, y, key) {
    const unit = this.add.sprite(x, y, key).setInteractive({ draggable: true });

    unit.setDisplaySize(80, 85);
    unit.unitKey = key;
    unit.dataVal = UNIT_DATA[key];
    unit.lastFired = 0;
    unit.gridX = -1;
    unit.gridY = -1;

    const ownerPrefix = socket && socket.id ? socket.id : "guest";
    unit.myUniqueId = `${ownerPrefix}_${Date.now()}_${Math.random()}`;
    this.setupUnitEvents(unit);
    this.units.add(unit);

    // 멀티플레이라면 생성 정보 전송
    if (this.isMultiplayer && socket && socket.connected) {
      socket.emit("sync_action", {
        room: this.myRoomName,
        type: "place_unit",
        payload: {
          key: unit.unitKey,
          tier: unit.dataVal.tier,
          x: unit.x,
          y: unit.y,
          ownerId: socket.id,
          uniqueId: unit.myUniqueId,
        },
      });
    }
  }

  // 유닛의 마우스 이벤트(툴팁, 색상, 사거리)를 설정하는 공통 함수
  setupUnitEvents(unit) {
    // 1. 마우스 올렸을 때 (Pointer Over)
    unit.on("pointerover", () => {
      if (unit.isDragging) return;

      // 티어별 색상 설정
      let nameColor = "#ffffff";
      let circleColor = 0xffffff;

      switch (unit.dataVal.tier) {
        case 1:
          nameColor = "#bdc3c7";
          circleColor = 0xbdc3c7;
          break;
        case 2:
          nameColor = "#2ecc71";
          circleColor = 0x2ecc71;
          break;
        case 3:
          nameColor = "#3498db";
          circleColor = 0x3498db;
          break;
        case 4:
          nameColor = "#9b59b6";
          circleColor = 0x9b59b6;
          break;
        case 5:
          nameColor = "#e67e22";
          circleColor = 0xe67e22;
          break;
        case 6:
          nameColor = "#e74c3c";
          circleColor = 0xe74c3c;
          break;
      }

      const tierStr = "★".repeat(unit.dataVal.tier);
      this.hoverText.setText(`${tierStr} ${unit.dataVal.name}`);

      this.hoverText.setStyle({
        fontFamily: "Cafe24ClassicType",
        color: nameColor,
        stroke: "#000000",
        strokeThickness: 4,
        fontSize: "18px",
        fontWeight: "bold",
        backgroundColor: "#000000cc",
        padding: { x: 8, y: 5 },
      });

      this.hoverText.setPosition(unit.x, unit.y - 40);
      this.hoverText.setVisible(true);
      this.hoverText.setDepth(9999);
      unit.setTint(0xcccccc);

      // 사거리 원 그리기
      this.rangeGraphics.clear();
      this.rangeGraphics.fillStyle(circleColor, 0.15);
      this.rangeGraphics.lineStyle(2, circleColor, 0.8);
      this.rangeGraphics.fillCircle(unit.x, unit.y, unit.dataVal.range);
      this.rangeGraphics.strokeCircle(unit.x, unit.y, unit.dataVal.range);
    });

    unit.on("pointerout", () => {
      this.hoverText.setVisible(false);
      unit.clearTint();
      this.rangeGraphics.clear();
    });
  }

  // 유닛 선택 시 하단 정보창에 색상 적용
  selectUnit(unit) {
    // 1. 현재 선택된 유닛 저장 및 판매 버튼 활성화
    this.selectedUnit = unit;
    const sellPrice = unit.dataVal.tier * 50;
    this.txtSell.setText(`판매 (+${sellPrice}G)`);
    this.btnSell.setVisible(true);

    // 2. 티어별 색상 코드 결정
    let colorCode = "#ffffff";
    let hexColor = 0xffffff;

    switch (unit.dataVal.tier) {
      case 1:
        colorCode = "#bdc3c7";
        hexColor = 0xbdc3c7;
        break;
      case 2:
        colorCode = "#2ecc71";
        hexColor = 0x2ecc71;
        break;
      case 3:
        colorCode = "#3498db";
        hexColor = 0x3498db;
        break;
      case 4:
        colorCode = "#9b59b6";
        hexColor = 0x9b59b6;
        break;
      case 5:
        colorCode = "#e67e22";
        hexColor = 0xe67e22;
        break;
      case 6:
        colorCode = "#e74c3c";
        hexColor = 0xe74c3c;
        break;
    }

    // 3. 사거리 표시
    this.rangeGraphics.clear();
    this.rangeGraphics.fillStyle(hexColor, 0.2);
    this.rangeGraphics.lineStyle(2, hexColor, 0.8);
    this.rangeGraphics.fillCircle(unit.x, unit.y, unit.dataVal.range);
    this.rangeGraphics.strokeCircle(unit.x, unit.y, unit.dataVal.range);

    // 4. 하단 정보창 텍스트 업데이트 (색상 적용)
    const atkSpeedSec = (unit.dataVal.speed / 1000).toFixed(1);
    const stars = "★".repeat(unit.dataVal.tier);

    // 텍스트 내용 설정
    this.statText.setText(
      `[${stars}${unit.dataVal.name}]   공격력: ${unit.dataVal.dmg}   공속: ${atkSpeedSec}s   사거리: ${unit.dataVal.range}`,
    );

    // 텍스트 스타일(색상) 적용
    this.statText.setStyle({
      fontFamily: "Cafe24ClassicType",
      fontSize: "18px",
      color: colorCode, // 티어별 색상 적용
      backgroundColor: "#000000aa",
      padding: { x: 10, y: 5 },
    });

    // 5. 조합법 힌트 표시
    // 조합법 힌트 표시 (컬러 적용 버전)
    const myKey = unit.unitKey;
    const myRecipes = RECIPES.filter(
      (r) => (r.a === myKey || r.b === myKey) && !r.hidden,
    );

    // 1) 기존 내용 싹 비우기
    this.recipeContainer.removeAll(true);
    this.recipeContainer.setVisible(true);

    // 2) 위치 잡기 (유닛 오른쪽)
    // 화면 오른쪽 끝이라 잘린다면 x좌표를 unit.x - 200 등으로 조정 필요
    let startX = unit.x + 60;
    let startY = unit.y - 50;
    // 화면 밖으로 나가는 것 방지 (간단 보정)
    if (startX > 1000) startX = unit.x - 250;
    this.recipeContainer.setPosition(startX, startY);

    // --- [스타일 설정 변수] ---
    const bgOpacity = 0.5; // 배경 투명도
    const bgWidth = 280; // 박스 가로 길이
    const titleSize = "18px"; // 제목 폰트 크기
    const bodySize = "16px"; // 내용 폰트 크기
    const lineHeight = 22; // 줄 간격
    const padding = 10; // 박스 내부 여백
    // -----------------------------------------------------

    // 배경 박스 생성
    const bgGraphics = this.add.graphics();
    bgGraphics.fillStyle(0x000000, bgOpacity);

    // 박스 높이 자동 계산
    const boxHeight =
      40 + (myRecipes.length > 0 ? myRecipes.length * lineHeight : 30);

    bgGraphics.fillRoundedRect(-padding, -padding, bgWidth, boxHeight, 10);
    this.recipeContainer.add(bgGraphics);

    // 제목
    const titleText = this.add.text(0, 0, `[ ${unit.dataVal.name} 조합법 ]`, {
      fontFamily: "Cafe24ClassicType",
      fontSize: titleSize,
      color: "#ffffff",
      fontStyle: "bold",
    });
    this.recipeContainer.add(titleText);

    let currentY = 30; // 첫 번째 줄 Y 위치

    if (myRecipes.length === 0) {
      const noRecipe = this.add.text(0, currentY, "상위 조합식이 없습니다.", {
        fontFamily: "Cafe24ClassicType",
        fontSize: bodySize,
        color: "#aaaaaa",
      });
      this.recipeContainer.add(noRecipe);
    } else {
      myRecipes.forEach((r) => {
        let currentX = 0;

        const partnerKey = r.a === myKey ? r.b : r.a;
        const partnerData = UNIT_DATA[partnerKey];
        const resultData = UNIT_DATA[r.result];

        // 1. "+ "
        const plus = this.add.text(currentX, currentY, "+ ", {
          fontFamily: "Cafe24ClassicType",
          fontSize: bodySize,
          color: "#ffffff",
        });
        this.recipeContainer.add(plus);
        currentX += plus.width;

        // 2. 재료 이름
        const matName = this.add.text(currentX, currentY, partnerData.name, {
          fontFamily: "Cafe24ClassicType",
          fontSize: bodySize,
          color: this.getTierColor(partnerData.tier),
          fontStyle: "bold",
        });
        this.recipeContainer.add(matName);
        currentX += matName.width;

        // 3. " = "
        const equal = this.add.text(currentX, currentY, " = ", {
          fontFamily: "Cafe24ClassicType",
          fontSize: bodySize,
          color: "#ffffff",
        });
        this.recipeContainer.add(equal);
        currentX += equal.width;

        // 4. 결과 이름
        const resName = this.add.text(currentX, currentY, resultData.name, {
          fontFamily: "Cafe24ClassicType",
          fontSize: bodySize,
          color: this.getTierColor(resultData.tier),
          fontStyle: "bold",
        });
        this.recipeContainer.add(resName);

        currentY += lineHeight;
      });
    }
  }

  // handleUnitDrop 함수 그리드 밖의 유닛
  handleUnitDrop(unit) {
    // 1. 전투 필드(원 안쪽) 배치 로직
    const distToCenter = Phaser.Math.Distance.Between(
      unit.x,
      unit.y,
      this.mapCenter.x,
      this.mapCenter.y,
    );

    if (distToCenter < this.mapRadius - 40) {
      let targetUnit = null;
      let minDist = 40; // 겹침 판정 거리

      this.units.children.iterate((otherUnit) => {
        if (unit === otherUnit) return;
        if (!otherUnit.active) return;

        const dist = Phaser.Math.Distance.Between(
          unit.x,
          unit.y,
          otherUnit.x,
          otherUnit.y,
        );
        if (dist < minDist) {
          targetUnit = otherUnit;
          minDist = dist;
        }
      });

      // 2. 겹치는 유닛이 있다면? -> 조합 시도!
      if (targetUnit) {
        const combined = this.tryCombine(unit, targetUnit);

        if (combined) {
          return;
        } else {
          this.returnUnitToOriginalPos(unit);
          this.showWarningText(unit.x, unit.y, "겹침 불가!");
          return;
        }
      }

      // 기존 그리드 자리 비우기
      if (unit.gridX !== -1 && this.gridState[unit.gridY]) {
        this.gridState[unit.gridY][unit.gridX] = null;
      }

      // 필드 배치 상태로 변경
      unit.gridX = -1;
      unit.gridY = -1;
      this.selectUnit(unit);

      // ============================================================
      // [★신규] 멀티플레이라면 서버에 "유닛 배치" 신호 전송
      // ============================================================
      if (this.isMultiplayer && socket && socket.connected) {
        socket.emit("sync_action", {
          room: this.myRoomName,
          type: "place_unit",
          payload: {
            key: unit.unitKey,
            tier: unit.dataVal.tier,
            x: unit.x,
            y: unit.y,
            ownerId: socket.id,
            uniqueId: unit.myUniqueId,
          },
        });
      }
      return;
    }

    // 드롭된 위치의 그리드 좌표 계산
    const dropGX = Math.floor(
      (unit.x - this.gridOffsetX + this.cellSize / 2) / this.cellSize,
    );
    const dropGY = Math.floor(
      (unit.y - this.gridOffsetY + this.cellSize / 2) / this.cellSize,
    );

    // 그리드 밖으로 나갔으면 원위치
    if (
      dropGX < 0 ||
      dropGX >= this.gridSize ||
      dropGY < 0 ||
      dropGY >= this.gridSize
    ) {
      this.returnUnitToOriginalPos(unit);
      return;
    }

    if (unit.gridX === -1 && this.isMultiplayer) {
      socket.emit("sync_action", {
        room: this.myRoomName,
        type: "unit_removed", // 삭제 신호
        payload: { uniqueId: unit.myUniqueId },
      });
    }

    // 데이터(gridState)와 실제 유닛(Physics) 이중 체크
    // 1차: 데이터상에 유닛이 있는가?
    let targetUnit = this.gridState[dropGY][dropGX];

    // 2차: 데이터는 비어있다는데(null), 실제로 유령 유닛이 그 자리에 있는가? (버그 방지)
    if (targetUnit === null) {
      const ghostUnit = this.units
        .getChildren()
        .find(
          (u) =>
            u !== unit && u.active && u.gridX === dropGX && u.gridY === dropGY,
        );

      if (ghostUnit) {
        // 데이터 복구 및 타겟으로 설정
        console.log("유령 유닛 감지! 데이터 복구됨:", dropGX, dropGY);
        this.gridState[dropGY][dropGX] = ghostUnit;
        targetUnit = ghostUnit;
      }
    }

    // --- 판정 로직 ---
    if (targetUnit === null) {
      // (A) 진짜 빈칸이면 -> 이동
      if (unit.gridX !== -1) {
        this.gridState[unit.gridY][unit.gridX] = null;
      }
      this.gridState[dropGY][dropGX] = unit;

      unit.gridX = dropGX;
      unit.gridY = dropGY;
      // 위치를 그리드 중앙에 딱 맞춤 (Snap)
      unit.x = this.gridOffsetX + dropGX * this.cellSize;
      unit.y = this.gridOffsetY + dropGY * this.cellSize;

      this.selectUnit(unit);
    } else if (targetUnit !== unit) {
      const combined = this.tryCombine(unit, targetUnit);
      if (!combined) {
        this.returnUnitToOriginalPos(unit);
      }
    } else {
      this.returnUnitToOriginalPos(unit);
    }
  }

  createPartnerUnit(data) {
    if (data.ownerId === socket.id) return;

    // 1. 이미 존재하는 유닛인지 ID로 확인
    const existingUnit = this.units
      .getChildren()
      .find((u) => u.myUniqueId === data.uniqueId);

    if (existingUnit) {
      // 2. 이미 있으면? -> 위치만 쓱 이동시킴 (자연스럽게)
      this.tweens.add({
        targets: existingUnit,
        x: data.x,
        y: data.y,
        duration: 200, // 0.2초 동안 부드럽게 이동
        ease: "Power2",
      });
      return; // 새로 만들지 않고 종료
    }

    // 3. 없으면? -> 새로 생성 (기존 로직)
    const unit = this.add.sprite(data.x, data.y, data.key);
    unit.setDisplaySize(80, 85);

    unit.unitKey = data.key;
    unit.dataVal = UNIT_DATA[data.key];
    unit.lastFired = 0;
    unit.gridX = -1;
    unit.gridY = -1;
    unit.myUniqueId = data.uniqueId; // ID 저장 필수
    unit.isPartner = true;

    unit.setInteractive();
    unit.setAlpha(0.9);
    // 파트너 유닛은 내가 드래그 못하게 설정 (중요)
    this.input.setDraggable(unit, false);

    this.units.add(unit);

    // 파트너 텍스트
    const label = this.add
      .text(data.x, data.y - 50, "Partner", {
        fontSize: "12px",
        color: "#00ff00",
        stroke: "#000",
        strokeThickness: 3,
      })
      .setOrigin(0.5);

    // 간단하게 유닛 객체에 라벨을 붙여서 관리 (나중에 삭제할 때 편함)
    unit.partnerLabel = label;
  }

  // [신규] 파트너 유닛 삭제 함수
  removePartnerUnit(targetId) {
    const targetUnit = this.units
      .getChildren()
      .find((u) => u.myUniqueId === targetId);
    if (targetUnit) {
      // 라벨이 있으면 같이 삭제
      if (targetUnit.partnerLabel) targetUnit.partnerLabel.destroy();
      targetUnit.destroy();
    }
  }

  // (편의 기능) 경고 텍스트 띄우기 함수 추가
  showWarningText(x, y, msg) {
    const warning = this.add
      .text(x, y - 30, msg, {
        fontFamily: "Cafe24ClassicType",
        fontSize: "14px",
        color: "#ff0000",
        stroke: "#000",
        strokeThickness: 2,
      })
      .setOrigin(0.5)
      .setDepth(9999);

    this.tweens.add({
      targets: warning,
      y: warning.y - 20,
      alpha: 0,
      duration: 800,
      onComplete: () => warning.destroy(),
    });
  }

  // (도우미 함수) 원래 자리로 되돌리기
  returnUnitToOriginalPos(unit) {
    // 만약 그리드 출신이면 그리드 좌표로
    if (unit.gridX !== -1) {
      unit.x = this.gridOffsetX + unit.gridX * this.cellSize;
      unit.y = this.gridOffsetY + unit.gridY * this.cellSize;
    } else {
      // 이미 필드에 나와있던 녀석이면 드래그 시작 위치로
      unit.x = unit.startX;
      unit.y = unit.startY;
    }
  }

  tryCombine(unitA, unitB) {
    let success = false;
    let newKey = null;

    // 1. [우선순위] 레시피(족보)가 있는지 확인
    const recipe = RECIPES.find(
      (r) =>
        (r.a === unitA.unitKey && r.b === unitB.unitKey) ||
        (r.b === unitA.unitKey && r.a === unitB.unitKey),
    );

    if (recipe) {
      newKey = recipe.result;
      success = true;
    }

    if (success) {
      // UI 정리
      this.hoverText.setVisible(false);
      if (this.recipeContainer) this.recipeContainer.setVisible(false);
      this.rangeGraphics.clear();

      if (unitA.gridX >= 0 && unitA.gridY >= 0) {
        this.gridState[unitA.gridY][unitA.gridX] = null;
      }
      if (unitB.gridX >= 0 && unitB.gridY >= 0) {
        this.gridState[unitB.gridY][unitB.gridX] = null;
      }
      const targetX = unitB.x;
      const targetY = unitB.y;
      const isField = unitB.gridX === -1;

      const targetGridX = unitB.gridX;
      const targetGridY = unitB.gridY;

      // 재료 삭제
      unitA.destroy();
      unitB.destroy();

      if (isField) {
        this.createUnitDirectly(targetX, targetY, newKey);
      } else {
        this.createUnitAt(targetGridX, targetGridY, newKey);
      }

      const newData = UNIT_DATA[newKey];
      if (newData && newData.tier >= 4) {
        this.showCombinationEffect(newKey, newData.tier);
      }
      return true;
    } else {
      return false;
    }
  }

  unitAttack(unit) {
    if (unit.isDragging) return; // 드래그 중 공격 중지 로직

    const now = this.time.now;

    const timeScale = this.time.timeScale;
    const adjustedSpeed = unit.dataVal.speed / timeScale;

    if (now - unit.lastFired < adjustedSpeed) return;
    let closest = null;
    let minDist = unit.dataVal.range;
    this.enemies.children.iterate((e) => {
      if (!e.active) return;
      const dist = Phaser.Math.Distance.Between(unit.x, unit.y, e.x, e.y);
      if (dist < minDist) {
        minDist = dist;
        closest = e;
      }
    });
    if (closest) {
      unit.lastFired = now;
      this.fireBullet(unit, closest);
    }
  }

  // [유닛 타입에 따라 투사체 키(Key)와 애니메이션 결정]
  fireBullet(unit, target) {
    let bulletKey = "bullet";
    let animKey = null;
    let bulletSpeed = 500; // [공격모션이 날아가는 속도]
    let rotationOffset = 0;
    let animFrameRate = 10; // [애니메이션 기본 속도]

    const type = unit.dataVal.type;

    // === [유닛 타입별 리소스 분기] ===
    if (type === "slayer_basic") {
      bulletKey = "attack_slayer_basic"; // 스프라이트 이미지 키
      animKey = "anim_slayer_basic"; // 재생할 애니메이션 키
      animFrameRate = 10; // [애니메이션 속도(숫자가 클수록 빠르다!)]
      bulletSpeed = 500;
    } else if (type === "tanjiro_water") {
      bulletKey = "attack_tanjiro_water";
      animKey = "anim_tanjiro_water";
      animFrameRate = 15;
      bulletSpeed = 600;
    } else if (type === "zenitsu_thunder") {
      bulletKey = "attack_zenitsu_thunder";
      animKey = "anim_zenitsu_thunder";
      animFrameRate = 20;
      bulletSpeed = 1200;
    } else if (type === "inosuke_beast") {
      bulletKey = "attack_inosuke_beast";
      animKey = "anim_inosuke_beast";
      animFrameRate = 15;
      bulletSpeed = 700;
    } else if (type === "kanao_flower") {
      bulletKey = "attack_kanao_flower";
      animKey = "anim_kanao_flower";
      animFrameRate = 20;
      bulletSpeed = 500;
    } else if (type === "crow_attack") {
      bulletKey = "attack_crow";
      animKey = "anim_crow";
      animFrameRate = 12;
      bulletSpeed = 900;
    } else if (type === "kakushi_support") {
      bulletKey = "attack_kakushi_support";
      animKey = "anim_kakushi";
      animFrameRate = 10;
      bulletSpeed = 400;
    } else if (type === "genya_gun") {
      bulletKey = "attack_genya_gun";
      animKey = "anim_genya_gun";
      animFrameRate = 10;
      bulletSpeed = 1300;
    } else if (type === "aoi_support") {
      bulletKey = "attack_aoi_support";
      animKey = "anim_aoi_support";
      animFrameRate = 10;
      bulletSpeed = 400;
    }
    //===== 3티어 시작 =====
    else if (type === "urokodaki_water") {
      bulletKey = "attack_urokodaki";
      animKey = "anim_urokodaki";
      animFrameRate = 15;
      bulletSpeed = 600;
    } else if (type === "jigoro_thunder") {
      bulletKey = "attack_jigoro";
      animKey = "anim_jigoro";
      animFrameRate = 15;
      bulletSpeed = 1000;
    } else if (type === "haganezuka_angry") {
      bulletKey = "attack_haganezuka";
      animKey = "anim_haganezuka";
      animFrameRate = 12;
      bulletSpeed = 500;
    } else if (type === "sabito_spirit") {
      bulletKey = "attack_sabito";
      animKey = "anim_sabito";
      animFrameRate = 15;
      bulletSpeed = 700;
    } else if (type === "nezuko_kick") {
      bulletKey = "attack_nezuko_box";
      animKey = "anim_nezuko_box";
      animFrameRate = 8;
      bulletSpeed = 500;
    } else if (type === "yushiro_paper") {
      bulletKey = "attack_yushiro";
      animKey = "anim_yushiro";
      animFrameRate = 10;
      bulletSpeed = 700;
    } else if (type === "murata_water") {
      bulletKey = "attack_murata";
      animKey = "anim_murata";
      animFrameRate = 10;
      bulletSpeed = 500;
    }
    // ===== 4티어 시작 ======
    else if (type === "giyu_water") {
      bulletKey = "attack_giyu";
      animKey = "anim_giyu";
      animFrameRate = 12;
      bulletSpeed = 500;
    } else if (type === "rengoku_fire") {
      bulletKey = "attack_rengoku";
      animKey = "anim_rengoku";
      animFrameRate = 10;
      bulletSpeed = 500;
    } else if (type === "tengen_sound") {
      bulletKey = "attack_tengen";
      animKey = "anim_tengen";
      animFrameRate = 10;
      bulletSpeed = 800;
    } else if (type === "shinobu_poison") {
      bulletKey = "attack_shinobu";
      animKey = "anim_shinobu";
      animFrameRate = 10;
      bulletSpeed = 500;
    } else if (type === "kanae_flower") {
      bulletKey = "attack_kanae";
      animKey = "anim_kanae";
      animFrameRate = 10;
      bulletSpeed = 400;
    } else if (type === "muichiro_mist") {
      bulletKey = "attack_muichiro";
      animKey = "anim_muichiro";
      animFrameRate = 10;
      bulletSpeed = 700;
    } else if (type === "mitsuri_love") {
      bulletKey = "attack_mitsuri";
      animKey = "anim_mitsuri";
      animFrameRate = 10;
      bulletSpeed = 500;
    } else if (type === "obanai_snake") {
      bulletKey = "attack_obanai";
      animKey = "anim_obanai";
      animFrameRate = 8;
      bulletSpeed = 750;
    } else if (type === "sanemi_wind") {
      bulletKey = "attack_sanemi";
      animKey = "anim_sanemi";
      animFrameRate = 10;
      bulletSpeed = 750;
    } else if (type === "gyomei_stone") {
      bulletKey = "attack_gyomei";
      animKey = "anim_gyomei";
      animFrameRate = 10;
      bulletSpeed = 600;
    } else if (type === "tamayo_blood") {
      bulletKey = "attack_tamayo";
      animKey = "anim_tamayo";
      animFrameRate = 10;
      bulletSpeed = 750;
    }
    // ===== 5티어 시작 ======
    else if (type === "tanjiro_sun") {
      bulletKey = "attack_tanjiro_sun";
      animKey = "anim_tanjiro_sun";
      animFrameRate = 10;
      bulletSpeed = 500;
    } else if (type === "zenitsu_god") {
      bulletKey = "attack_zenitsu_god";
      animKey = "anim_zenitsu_god";
      animFrameRate = 10;
      bulletSpeed = 900;
    } else if (type === "nezuko_blood_art") {
      bulletKey = "attack_nezuko_awake";
      animKey = "anim_nezuko_awake";
      animFrameRate = 12;
      bulletSpeed = 500;
    } else if (type === "giyu_mark_water") {
      bulletKey = "attack_giyu_mark";
      animKey = "anim_giyu_mark";
      animFrameRate = 14;
      bulletSpeed = 500;
    } else if (type === "muichiro_mark_mist") {
      bulletKey = "attack_muichiro_mark";
      animKey = "anim_muichiro_mark";
      animFrameRate = 14;
      bulletSpeed = 500;
    } else if (type === "tamayo_yushiro_combo") {
      bulletKey = "attack_tamayo_yushiro";
      animKey = "anim_tamayo_yushiro";
      animFrameRate = 14;
      bulletSpeed = 500;
    } else if (type === "inosuke_awake_beast") {
      bulletKey = "attack_inosuke_awake";
      animKey = "anim_inosuke_awake";
      animFrameRate = 14;
      bulletSpeed = 500;
    }

    // [Tier 6] 신화
    else if (type === "tanjiro_13th") {
      bulletKey = "attack_tanjiro_final";
      animKey = "anim_tanjiro_final";
      animFrameRate = 14;
      bulletSpeed = 500;
    } else if (type === "gyomei_mark_stone") {
      bulletKey = "attack_gyomei_mark";
      animKey = "anim_gyomei_mark";
      animFrameRate = 14;
      bulletSpeed = 500;
    } else if (type === "yoriichi_sun") {
      bulletKey = "attack_yoriichi";
      animKey = "anim_yoriichi";
      animFrameRate = 14;
      bulletSpeed = 500;
    } else if (type === "inosuke_king_beast") {
      bulletKey = "attack_inosuke_king";
      animKey = "anim_inosuke_king";
      animFrameRate = 14;
      bulletSpeed = 500;

      // [HIDDEN] 히든
    } else if (type === "yoriichi_doll") {
      bulletKey = "attack_yoriichi_zero";
      animKey = "anim_yoriichi_zero";
      animFrameRate = 14;
      bulletSpeed = 500;
    } else if (type === "kokushibo_moon") {
      bulletKey = "attack_koku";
      animKey = "anim_koku";
      animFrameRate = 14;
      bulletSpeed = 500;
    } else if (type === "tanjiro_demon_king") {
      bulletKey = "attack_tanjiro_king";
      animKey = "anim_tanjiro_king";
      animFrameRate = 14;
      bulletSpeed = 500;
    } else if (type === "twin_destiny_combo") {
      bulletKey = "attack_twin_destiny";
      animKey = "anim_twin_destiny";
      animFrameRate = 14;
      bulletSpeed = 500;
    }

    // ===============================================================
    // [신규 추가] Tier 5 & 6 신규 유닛 공격 설정
    // ===============================================================

    // 1. 렌고쿠(멸살)
    else if (type === "rengoku_9th_form") {
      bulletKey = "attack_rengoku_9th";
      animKey = "anim_rengoku_9th";
      animFrameRate = 14;
      bulletSpeed = 500;
    }
    // 2. 텐겐(악보)
    else if (type === "tengen_musical_score") {
      bulletKey = "attack_tengen_score";
      animKey = "anim_tengen_score";
      animFrameRate = 14;
      bulletSpeed = 500;
    }
    // 3. 시노부(종의형)
    else if (type === "shinobu_last_dance") {
      bulletKey = "attack_shinobu_dance";
      animKey = "anim_shinobu_dance";
      animFrameRate = 14;
      bulletSpeed = 500;
    }
    // 4. 카나에(꽃의영)
    else if (type === "kanae_flower_final") {
      bulletKey = "attack_kanae_spirit";
      animKey = "anim_kanae_spirit";
      animFrameRate = 14;
      bulletSpeed = 500;
    }
    // 5. 사네미(반점)
    else if (type === "sanemi_typhoon") {
      bulletKey = "attack_sanemi_mark";
      animKey = "anim_sanemi_mark";
      animFrameRate = 14;
      bulletSpeed = 500;
    }
    // 6. 오바나이(반점)
    else if (type === "obanai_serpent_god") {
      bulletKey = "attack_obanai_mark";
      animKey = "anim_obanai_mark";
      animFrameRate = 14;
      bulletSpeed = 500;
    }
    // 7. 미츠리(반점)
    else if (type === "mitsuri_love_cat") {
      bulletKey = "attack_mitsuri_mark";
      animKey = "anim_mitsuri_mark";
      animFrameRate = 14;
      bulletSpeed = 500;
    }
    // 8. 렌고쿠(마지막 미소) - 서포트 느낌이거나 특수 연출
    else if (type === "rengoku_smile_effect") {
      bulletKey = "attack_rengoku_smile";
      animKey = "anim_rengoku_smile";
      animFrameRate = 14;
      bulletSpeed = 500;
    }

    // [신규 Tier 6]
    // 9. 젠이츠(화뢰신)
    else if (type === "zenitsu_7th_form") {
      bulletKey = "attack_zenitsu_7th";
      animKey = "anim_zenitsu_7th";
      animFrameRate = 18;
      bulletSpeed = 800; // 매우 빠름
    }
    // 10. 기유(잔잔한 물)
    else if (type === "giyu_dead_calm") {
      bulletKey = "attack_giyu_calm";
      animKey = "anim_giyu_calm";
      animFrameRate = 12;
      bulletSpeed = 500;
    }
    // 11. 사네미(바람의 신)
    else if (type === "sanemi_wind_god") {
      bulletKey = "attack_sanemi_god";
      animKey = "anim_sanemi_god";
      animFrameRate = 14;
      bulletSpeed = 500;
    }
    // 12. 렌고쿠(마음의 불꽃)
    else if (type === "rengoku_legend_fire") {
      bulletKey = "attack_rengoku_legend";
      animKey = "anim_rengoku_legend";
      animFrameRate = 14;
      bulletSpeed = 500;
    }
    // 13. 오바나이&미츠리 (커플)
    else if (type === "love_snake_couple_attack") {
      bulletKey = "attack_love_snake";
      animKey = "anim_love_snake";
      animFrameRate = 16;
      bulletSpeed = 600;
    }
    // 14. 무이치로 (내비세)
    else if (type === "muichiro_transparent_world") {
      bulletKey = "attack_muichiro_trans";
      animKey = "anim_muichiro_trans";
      animFrameRate = 20;
      bulletSpeed = 700;
    }
    // 15. 네즈코 (태양의 극복 - 히든)
    else if (type === "nezuko_sun_conqueror") {
      bulletKey = "attack_nezuko_sun";
      animKey = "anim_nezuko_sun";
      animFrameRate = 12;
      bulletSpeed = 500;
    }

    // 2. 투사체 생성
    const b = this.bullets.create(unit.x, unit.y, bulletKey);
    // [★추가] 파트너가 쏜 총알은 '유령 총알(Ghost)'로 표시
    if (unit.isPartner) {
      b.isGhost = true;
    }

    // 2-1. 투사체 크기 (티어별 직접 지정)
    let scaleRatio = 1.0;

    switch (unit.dataVal.tier) {
      case 1:
        scaleRatio = 1.5;
        break;
      case 2:
        scaleRatio = 2.4;
        break;
      case 3:
        scaleRatio = 2.7;
        break;
      case 4:
        scaleRatio = 4.5;
        break;
      case 5:
        scaleRatio = 5.0;
        break;
      case 6:
        scaleRatio = 5.0;
        break;
      default:
        scaleRatio = 1.5;
        break;
    }

    b.setScale(scaleRatio);

    // 투사체 충돌 이미지크기 설정!
    b.body.setSize(10, 10);
    b.body.setOffset((b.width - 10) / 2, (b.height - 10) / 2);

    // 3. 애니메이션 재생 (키가 있다면)
    if (animKey) {
      b.play({ key: animKey, frameRate: animFrameRate, repeat: -1 }); // repeat: 0 = 한 번만 재생
    }

    // 4. 데이터 주입
    b.target = target;
    b.damage = unit.dataVal.dmg;
    b.isCritical = Math.random() < 0.1;
    b.speed = bulletSpeed;
    b.savedFrameRate = animFrameRate;

    // 5. 시점에 적을 바라보게 회전(애니메이션이 회전!)
    const angle = Phaser.Math.Angle.Between(unit.x, unit.y, target.x, target.y);
    b.setRotation(angle + rotationOffset);

    this.physics.velocityFromRotation(angle, bulletSpeed, b.body.velocity);
  }

  updateBullets() {
    this.bullets.children.iterate((b) => {
      // 활성 상태가 아니거나, 이미 적에게 맞아서 멈춘(body.enable false) 총알은 이동 로직 건너뜀
      if (!b || !b.active || !b.body.enable) return;

      // 목표가 사라지거나 죽었으면 총알도 삭제
      if (!b.target || !b.target.active || b.target.hp <= 0) {
        b.destroy();
        return;
      }

      // [유도 기능 로직]
      // 현재 총알 위치에서 목표 위치까지의 각도를 계산 후 이동
      const angle = Phaser.Math.Angle.Between(b.x, b.y, b.target.x, b.target.y);
      this.physics.velocityFromRotation(angle, b.speed, b.body.velocity);

      // 투사체 머리가 적을 향하도록 이미지 회전
      // b.setRotation(angle + (Math.PI / 2)); // 이미지 방향에 따라 +90도 필요할 수 있음
      b.setRotation(angle);
    });
  }

  hitEnemy(b, e) {
    // 이미 맞았거나(active false), 물리 엔진이 꺼진(충돌 처리된) 총알은 무시
    if (!b.active || !e.active || !b.body.enable) return;
    if (b.isGhost) {
      b.destroy(); // 총알은 사라짐
      return;
    }
    b.body.enable = false;
    b.body.setVelocity(0, 0);

    let dmg = b.damage * (b.isCritical ? 2 : 1);
    e.hp -= dmg;
    e.setTint(0xff0000);
    this.time.delayedCall(100, () => e.clearTint());

    // [★신규] 데미지 입혔음을 서버에 전송 (체력바 동기화용)
    if (this.isMultiplayer) {
      socket.emit("sync_action", {
        room: this.myRoomName,
        type: "enemy_damage",
        payload: { uniqueId: e.uniqueId, damage: dmg },
      });
    }

    if (e.hp <= 0) {
      if (!e.active) return;
      // [디버깅용 로그 추가]
      console.log("적 사망! 이름:", e.name, "보스여부:", e.isBoss);

      if (e.hpBar) e.hpBar.destroy();
      e.destroy();

      // [★ 골드 보상 로직 업데이트 ★]
      let reward = 0;
      if (e.isBoss) {
        reward = 1000;
        this.showGoldEffect(e.x, e.y, "+1000G", "#ff0000", 30);
        if (currentMode === "normal" && this.round === 90) {
          console.log("스토리 모드 클리어!");
          this.gameClear();
          return;
        }
      } else {
        // [하드 모드 & 멀티 모드] 보상 상향
        if (currentMode === "hard" || currentMode === "multi") {
          reward = 7 + Math.floor(this.round / 4);
          if (reward > 20) reward = 20;
        }
        // [노멀 모드]
        else {
          reward = 5 + Math.floor(this.round / 4);
          // 노멀은 최대 10원으로 제한 유지
          if (reward > 10) reward = 10;
        }
      }

      this.gold += reward;
      this.txtGold.setText(`GOLD: ${this.gold}`);

      // 적 죽음 전송
      if (this.isMultiplayer) {
        socket.emit("sync_action", {
          room: this.myRoomName,
          type: "enemy_died",
          payload: { uniqueId: e.uniqueId, isBoss: e.isBoss },
        });
      }
    }

    // 애니메이션이 재생 중이라면 끝날 때까지 기다림
    if (b.anims.currentAnim) {
      b.setDepth(e.depth + 1);
      b.play({
        key: b.anims.currentAnim.key,
        frameRate: b.savedFrameRate || 10,
        repeat: 0,
        forceShift: true,
      });

      b.once("animationcomplete", () => {
        b.destroy();
      });
    } else {
      this.time.delayedCall(50, () => b.destroy());
    }
  }

  // 골드/데미지 텍스트 이펙트 함수
  showGoldEffect(x, y, msg, color, fontSize) {
    const txt = this.add
      .text(x, y, msg, {
        fontFamily: "Cafe24ClassicType",
        fontSize: `${fontSize}px`,
        color: color,
        stroke: "#000",
        strokeThickness: 3,
        fontStyle: "bold",
      })
      .setOrigin(0.5)
      .setDepth(2000);

    // 위로 떠오르며 사라지는 애니메이션
    this.tweens.add({
      targets: txt,
      y: y - 40,
      alpha: 0,
      duration: 1200,
      ease: "Power2",
      onComplete: () => {
        txt.destroy();
      },
    });
  }

  // 2. 일시정지 버튼 눌렀을 때
  togglePause() {
    // 멀티 모드라면 -> 서버에 "멈춰!" 요청
    if (this.isMultiplayer) {
      socket.emit("game_state_change", {
        room: this.myRoomName,
        type: "pause",
        isPaused: !this.isPaused,
      });
      return;
    }

    // 싱글 모드
    this.applyPause(!this.isPaused);
  }

  // [신규] 실제 일시정지 로직 분리
  applyPause(shouldPause) {
    this.isPaused = shouldPause;
    if (this.isPaused) {
      this.physics.pause();
      this.pauseOverlay.setVisible(true);
      this.pauseText.setVisible(true);
      this.txtPause.setText("다시 시작");
    } else {
      this.physics.resume();
      this.pauseOverlay.setVisible(false);
      this.pauseText.setVisible(false);
      this.txtPause.setText("일시 정지");
    }
  }

  update(time, delta) {
    if (this.isPaused || this.isGameOver) return;

    // 현재 게임 속도 (기본 1, 2배속 시 2)
    const speedMult = this.time.timeScale;

    // delta는 밀리초(ms) 단위이므로 초(second) 단위로 변환 (1초 = 1000ms)
    // dt = 1.0 이면 1초가 지났다는 뜻
    const dt = delta / 1000;

    // 적 이동 로직
    this.enemies.children.iterate((enemy) => {
      if (enemy && enemy.active) {
        // [속도 조절]
        // 기존 0.0002 같은 아주 작은 값은 '프레임당' 이동량이었지만,
        // 이제는 '1초당' 이동량(라디안)을 생각해야 한다.
        // 예: moveSpeed가 50이면 -> 0.5 라디안/초 (한 바퀴 도는데 약 12초 걸림)
        const ANGULAR_SPEED_FACTOR = 0.03;

        // (기본속도 50) * 0.01 = 0.5 라디안/초
        const moveSpeed = (enemy.moveSpeed || 50) * ANGULAR_SPEED_FACTOR;

        // (속도) * (게임배속) * (흐른 시간)
        // 이 공식이 있어야 144Hz 모니터든 60Hz 모니터든 똑같은 거리를 이동
        enemy.pathAngle += moveSpeed * speedMult * dt;

        // 궤도 위치 계산
        const orbitRadius = this.mapRadius - 20;
        enemy.x = this.mapCenter.x + Math.cos(enemy.pathAngle) * orbitRadius;
        enemy.y = this.mapCenter.y + Math.sin(enemy.pathAngle) * orbitRadius;
        enemy.setRotation(0);

        // 왼쪽/오른쪽 볼 때 뒤집기
        if (Math.cos(enemy.pathAngle) < 0) {
          enemy.setFlipX(true);
        } else {
          enemy.setFlipX(false);
        }
        if (enemy.hpBar) {
          enemy.hpBar.clear(); // 이전 프레임 그림 지우기

          // 보스냐 일반몹이냐에 따라 크기 다르게
          const width = enemy.isBoss ? 60 : 30; // 바 길이
          const height = 4; // 바 두께
          const offsetY = enemy.isBoss ? 50 : 30; // 적 머리 위(혹은 아래) 거리

          // 바 위치 계산 (적 중앙 하단)
          const barX = enemy.x - width / 2;
          const barY = enemy.y + offsetY;

          // 1. 배경 (검은색)
          enemy.hpBar.fillStyle(0x000000, 1);
          enemy.hpBar.fillRect(barX, barY, width, height);

          // 2. 현재 체력
          const hpPercent = Phaser.Math.Clamp(enemy.hp / enemy.maxHp, 0, 1);
          enemy.hpBar.fillStyle(0xff0000, 1);
          enemy.hpBar.fillRect(barX, barY, width * hpPercent, height);
        }
      }
    });
    this.units.children.iterate((u) => {
      if (u && u.active) this.unitAttack(u);
    });

    this.updateBullets();

    //=== 적 숫자 체크 로직 ===
    const currentEnemies = this.enemies.countActive(true);
    const maxEnemies = GAME_CONFIG.maxEnemies;

    if (this.txtEnemyCount) {
      this.txtEnemyCount.setText(
        `남은 혈귀: ${currentEnemies} / ${maxEnemies}`,
      );
      if (currentEnemies >= maxEnemies * 0.8) {
        this.txtEnemyCount.setColor("#ff0000");
      } else {
        this.txtEnemyCount.setColor("#ffffff");
      }
    }

    if (currentEnemies > maxEnemies) {
      if (!this.isGameOver) {
        this.gameOver(); // 내 화면 종료

        if (this.isMultiplayer) {
          socket.emit("sync_action", {
            room: this.myRoomName,
            type: "game_over", // 패배 신호 전송
            payload: {},
          });
        }
      }
    }
  }

  showBossCutscene(bossKey, bossName, cutsceneImgKey) {
    // 1. 게임 진행 일시 정지 (타이머 및 물리 엔진)
    this.spawnTimer.paused = true;
    this.physics.pause();

    // 컷신용 컨테이너 (나중에 한꺼번에 지우기 위함)
    const cutsceneContainer = this.add.container(0, 0).setDepth(99999);

    // 2. [연출] 붉은색 경고 점멸 (WARNING 효과)
    const redFlash = this.add.rectangle(640, 360, 1280, 720, 0xff0000, 0.5);
    cutsceneContainer.add(redFlash);

    this.tweens.add({
      targets: redFlash,
      alpha: 0,
      duration: 300,
      yoyo: true,
      repeat: 3, // 3번 깜빡임
      onComplete: () => {
        redFlash.destroy(); // 깜빡임 끝나면 제거
      },
    });

    // 3. 어두운 배경 (검은색 오버레이)
    const bg = this.add.rectangle(640, 360, 1280, 720, 0x000000, 0.85);
    bg.setAlpha(0); // 처음엔 투명했다가 나타남
    cutsceneContainer.add(bg);

    // 4. 보스 이미지 (화면 오른쪽 밖에서 왼쪽으로 슬라이드)
    // 이미지가 없으면 기본값 사용
    const imgKey = this.textures.exists(cutsceneImgKey)
      ? cutsceneImgKey
      : bossKey;

    const bossImg = this.add.sprite(1400, 360, imgKey).setOrigin(0.5);
    // 이미지 크기 조정 (화면 높이의 80% 정도)
    const scale = (720 * 0.8) / bossImg.height;
    bossImg.setScale(scale);
    bossImg.setAlpha(0);
    cutsceneContainer.add(bossImg);

    // 5. 텍스트 (WARNING 및 보스 이름)
    const warnText = this.add
      .text(640, 200, "⚠ WARNING ⚠", {
        fontFamily: "Cafe24ClassicType",
        fontSize: "60px",
        color: "#ff0000",
        fontStyle: "bold",
        stroke: "#ffffff",
        strokeThickness: 4,
      })
      .setOrigin(0.5)
      .setAlpha(0);

    const nameText = this.add
      .text(640, 600, `[ ${bossName} ]`, {
        fontFamily: "Cafe24ClassicType",
        fontSize: "50px",
        color: "#ffffff",
      })
      .setOrigin(0.5)
      .setAlpha(0);

    cutsceneContainer.add([warnText, nameText]);

    // === 애니메이션 시퀀스 ===

    // 배경 어두워짐
    this.tweens.add({
      targets: bg,
      alpha: 0.85,
      duration: 500,
    });

    // 보스 이미지 슬라이드 인 (오른쪽 -> 중앙)
    this.tweens.add({
      targets: bossImg,
      x: 800, // 약간 오른쪽 치우치게 배치
      alpha: 1,
      duration: 800,
      ease: "Power2",
      delay: 300, // 배경 어두워진 뒤 시작
    });

    // 텍스트 등장
    this.tweens.add({
      targets: [warnText, nameText],
      alpha: 1,
      scale: { from: 1.5, to: 1 }, // 쿵 찍는 효과
      duration: 500,
      ease: "Bounce",
      delay: 800,
    });

    // 6. 컷신 종료 및 게임 재개 (3초 후)
    this.time.delayedCall(3500, () => {
      // 서서히 사라짐
      this.tweens.add({
        targets: cutsceneContainer,
        alpha: 0,
        duration: 500,
        onComplete: () => {
          cutsceneContainer.destroy(); // 컷신 객체 삭제

          // 게임 재개
          this.physics.resume();
          this.spawnTimer.paused = false;

          // 보스 소환 알림 (선택 사항)
          console.log("보스 전투 시작!");
        },
      });
    });
  }
  // GameScene 클래스 내부에 추가 (gameOver 근처)

  // [신규] 게임 클리어 (노멀 모드 엔딩)
  async gameClear() {
    if (this.isGameOver) return;
    this.isGameOver = true; // 게임 상태 종료로 변경

    this.physics.pause(); // 모든 움직임 멈춤
    this.spawnTimer.paused = true; // 스폰 중지

    // 1. 화면 서서히 암전 (Fade Out)
    const overlay = this.add
      .rectangle(640, 360, 1280, 720, 0x000000, 0)
      .setDepth(9999);

    this.tweens.add({
      targets: overlay,
      alpha: 1,
      duration: 1000, // 1초 동안 암전
      onComplete: () => {
        // 2. 엔딩 이미지 보여주기 (Fade In)
        // 'game_clear_bg'가 없으면 에러나니 bootScene에서 꼭 로드하거나 다른 키를 쓰세요.
        const clearImg = this.add
          .image(640, 360, "game_clear_bg")
          .setOrigin(0.5)
          .setDepth(10000)
          .setAlpha(0);

        // 이미지 비율 맞추기 (화면에 꽉 차게)
        clearImg.setDisplaySize(1280, 720);

        this.tweens.add({
          targets: clearImg,
          alpha: 1,
          duration: 1500, // 1.5초 동안 서서히 밝아짐
          onComplete: () => {
            // 3. 축하 텍스트
            this.add
              .text(640, 600, "MISSION COMPLETE", {
                fontFamily: "Cafe24ClassicType",
                fontSize: "60px",
                color: "#f1c40f",
                stroke: "#000",
                strokeThickness: 6,
              })
              .setOrigin(0.5)
              .setDepth(10001);

            // 4. 파이어베이스에 클리어 기록 저장 (선택 사항)
            this.saveClearRecord();

            // 5. 5초 뒤에 메뉴로 이동
            this.time.delayedCall(5000, () => {
              this.scene.start("MenuScene");
            });
          },
        });
      },
    });
  }

  // (보너스) 클리어 기록 저장용 함수
  async saveClearRecord() {
    if (!db || !currentPlayerName) return;
    try {
      await addDoc(collection(db, "scores_normal"), {
        // 노멀 모드 점수판
        name: currentPlayerName,
        round: 90, // 클리어는 무조건 90라운드
        isClear: true, // 클리어 여부 표시
        createdAt: new Date().toISOString(),
      });
      console.log("클리어 기록 저장 완료");
    } catch (e) {
      console.error("저장 실패", e);
    }
  }

  async gameOver() {
    if (this.isGameOver) return;
    this.isGameOver = true;

    this.physics.pause(); // 게임 멈춤

    // 1. 배경 어둡게 (Depth를 높여서 유닛들보다 위에 오게 함)
    this.add.rectangle(640, 360, 1280, 720, 0x000000, 0.8).setDepth(9000); // [중요] 유닛보다 훨씬 높은 숫자

    // 2. 텍스트 표시
    this.add
      .text(640, 250, "GAME OVER", {
        fontFamily: "Cafe24ClassicType",
        fontFamily: "Cafe24ClassicType",
        fontSize: "64px",
        color: "red",
      })
      .setOrigin(0.5)
      .setDepth(9001);

    this.add
      .text(640, 350, `최종 기록: ${this.round} Round`, {
        fontFamily: "Cafe24ClassicType",
        fontFamily: "Cafe24ClassicType",
        fontSize: "32px",
        color: "white",
      })
      .setOrigin(0.5)
      .setDepth(9001);

    // 3. 저장 상태 텍스트
    const savingText = this.add
      .text(640, 450, "기록 저장 중...", {
        fontFamily: "Cafe24ClassicType",
        fontSize: "20px",
        color: "yellow",
      })
      .setOrigin(0.5)
      .setDepth(9001);

    // 4. [핵심] 메뉴 나가기 버튼 (Depth 최상위 설정)
    const btnRestart = this.add
      .rectangle(640, 550, 240, 70, 0xffffff)
      .setInteractive({ useHandCursor: true })
      .setDepth(9002); // 가장 위에!

    const txtRestart = this.add
      .text(640, 550, "메뉴로 나가기", {
        fontFamily: "Cafe24ClassicType",
        fontSize: "24px",
        color: "#000",
        fontStyle: "bold",
      })
      .setOrigin(0.5)
      .setDepth(9002);

    // 버튼 클릭 이벤트 (클릭되면 콘솔에 로그 찍힘)
    btnRestart.on("pointerdown", () => {
      console.log("메뉴 버튼 클릭됨!"); // F12 콘솔에서 확인 가능
      this.scene.stop("GameScene");
      this.scene.start("MenuScene");
    });

    // 마우스 올렸을 때 효과 (잘 작동하는지 눈으로 확인용)
    btnRestart.on("pointerover", () => btnRestart.setFillStyle(0xcccccc));
    btnRestart.on("pointerout", () => btnRestart.setFillStyle(0xffffff));

    // 5. Firebase 저장 시도
    if (db && currentPlayerName) {
      try {
        let saveName = currentPlayerName;

        // "멀티 모드"이고 "파트너 이름이 있을 때"만 이름을 합침
        if (currentMode === "multi" && partnerName !== "") {
          saveName = `${currentPlayerName} & ${partnerName}`;
          // 예: "탄지로 & 네즈코"
        }

        // 저장
        const timeoutPromise = new Promise((_, reject) =>
          setTimeout(() => reject(new Error("시간 초과")), 3000),
        );

        await Promise.race([
          addDoc(collection(db, getScoreCollectionName(currentMode)), {
            name: saveName,
            round: this.round,
            createdAt: new Date().toISOString(),
          }),
          timeoutPromise,
        ]);

        savingText.setText("기록 저장 완료!");
        savingText.setColor("#00ff00");
      } catch (e) {
        console.error("저장 실패:", e);
        savingText.setText("저장 실패");
        savingText.setColor("#ff0000");
      }
    }
  }

  // =================================================================
  // [RL Bridge] 강화학습 브릿지 메서드
  // =================================================================

  /** 현재 게임 상태를 JSON으로 직렬화 */
  getGameState() {
    const gridState = this.gridState.flat().map((cell) => {
      if (!cell || !cell.active) return null;
      return { key: cell.unitKey, tier: cell.dataVal.tier };
    });

    const fieldUnits = [];
    this.units.children.iterate((u) => {
      if (u && u.active && u.gridX === -1) {
        fieldUnits.push({
          key: u.unitKey,
          tier: u.dataVal.tier,
          x: u.x,
          y: u.y,
          dps: (u.dataVal.dmg * 1000) / u.dataVal.speed,
        });
      }
    });

    const enemies = [];
    this.enemies.children.iterate((e) => {
      if (e && e.active) {
        enemies.push({
          hp: e.hp,
          maxHp: e.maxHp,
          isBoss: !!e.isBoss,
        });
      }
    });

    const totalFieldDps = fieldUnits.reduce((sum, u) => sum + u.dps, 0);

    return {
      round: this.round,
      gold: this.gold,
      timeRemaining: this.currentTime,
      gridState: gridState,
      fieldUnits: fieldUnits,
      enemies: enemies,
      enemyCount: enemies.length,
      maxEnemies: GAME_CONFIG.maxEnemies,
      totalFieldDps: totalFieldDps,
      isGameOver: this.isGameOver,
      isPaused: this.isPaused,
    };
  }

  /** RL 행동 실행 */
  executeRLAction(action) {
    if (this.isGameOver || this.isPaused) return;

    const { type, params } = action;

    switch (type) {
      case "summon":
        this.summonUnit();
        break;

      case "place": {
        // params.unitKey - 배치할 유닛 키
        const unitKey = params?.unitKey;
        if (!unitKey) break;
        // 그리드에서 해당 유닛 찾기
        for (let y = 0; y < this.gridSize; y++) {
          for (let x = 0; x < this.gridSize; x++) {
            const cell = this.gridState[y][x];
            if (cell && cell.unitKey === unitKey) {
              // 필드 중앙 근처에 배치
              const angle = Math.random() * Math.PI * 2;
              const radius = 100 + Math.random() * 100;
              const fx = this.mapCenter.x + Math.cos(angle) * radius;
              const fy = this.mapCenter.y + Math.sin(angle) * radius;

              this.gridState[y][x] = null;
              cell.gridX = -1;
              cell.gridY = -1;
              cell.x = fx;
              cell.y = fy;
              return;
            }
          }
        }
        break;
      }

      case "sell": {
        const sellKey = params?.unitKey;
        if (!sellKey) break;
        for (let y = 0; y < this.gridSize; y++) {
          for (let x = 0; x < this.gridSize; x++) {
            const cell = this.gridState[y][x];
            if (cell && cell.unitKey === sellKey) {
              const sellPrice = cell.dataVal.tier * 50;
              this.gold += sellPrice;
              this.txtGold.setText(`GOLD: ${this.gold}`);
              this.gridState[y][x] = null;
              cell.destroy();
              return;
            }
          }
        }
        break;
      }

      case "combine": {
        // params.a, params.b - 조합할 두 유닛 키
        const keyA = params?.a;
        const keyB = params?.b;
        if (!keyA || !keyB) break;
        let unitA = null;
        let unitB = null;
        // 그리드에서 찾기
        for (let y = 0; y < this.gridSize; y++) {
          for (let x = 0; x < this.gridSize; x++) {
            const cell = this.gridState[y][x];
            if (!cell) continue;
            if (!unitA && cell.unitKey === keyA) {
              unitA = cell;
            } else if (!unitB && cell.unitKey === keyB) {
              unitB = cell;
            }
          }
        }
        if (unitA && unitB) {
          this.tryCombine(unitA, unitB);
        }
        break;
      }

      case "wait":
      default:
        break;
    }
  }

  /** RL 모드 초기화: 소켓 이벤트 등록 */
  initRLMode() {
    if (!socket) return;

    socket.emit("rl_game_ready");
    console.log("🤖 RL 모드 활성화");

    // RL 행동 수신 → 실행 → 상태 반환
    socket.on("rl_execute_action", (action) => {
      this.executeRLAction(action);

      // 실행 후 현재 상태 전송
      const state = this.getGameState();
      socket.emit("rl_state", state);
    });

    // 매 프레임마다 상태 전송 (선택적 - 주기적 동기화)
    this.time.addEvent({
      delay: 500,
      callback: () => {
        if (socket && socket.connected) {
          socket.emit("rl_state", this.getGameState());
        }
      },
      loop: true,
    });
  }
}

// RL 모드 감지 (URL 파라미터: ?rl=true)
const urlParams = new URLSearchParams(window.location.search);
const isRLMode = urlParams.get("rl") === "true";
if (isRLMode) {
  console.log("🤖 RL 모드 감지됨");
}

const config = {
  type: Phaser.AUTO,
  width: 1280,
  height: 720,
  parent: "game-container",
  backgroundColor: "#050510",
  physics: { default: "arcade", arcade: { debug: false } },
  scene: [BootScene, MenuScene, GameScene],
};

// === 모드별 데이터 로딩 함수 (MenuScene에서도 사용) ===
async function loadDataForMode(mode) {
  let modulePath = "./data.normal.js";

  if (mode === "hard") {
    modulePath = "./data.hard.js";
  } else if (mode === "multi") {
    modulePath = "./data.multi.js";
  }

  const dataModule = await import(modulePath);

  GAME_CONFIG = dataModule.GAME_CONFIG;
  UNIT_DATA = dataModule.UNIT_DATA;
  RECIPES = dataModule.RECIPES;
  ENEMY_CONFIG = dataModule.ENEMY_CONFIG;
}

// === Phaser 게임 부트스트랩 ===
async function bootstrap() {
  // 초기 실행을 위해 기본 데이터 하나는 로드해둡니다 (에러 방지용)
  await loadDataForMode("normal");

  game = new Phaser.Game(config);

  // RL 모드일 때 자동 시작
  if (isRLMode) {
    currentPlayerName = "RL_Agent";
    currentMode = "normal";
    overlay.style.display = "none";

    // 게임이 준비되면 자동 시작
    game.events.once("ready", () => {
      game.scene.start("MenuScene");
      // MenuScene을 바로 건너뛰고 GameScene으로
      setTimeout(() => {
        game.scene.stop("MenuScene");
        game.scene.start("GameScene");
        // GameScene이 생성된 후 RL 모드 초기화
        setTimeout(() => {
          const gameScene = game.scene.getScene("GameScene");
          if (gameScene) {
            gameScene.initRLMode();
            // RL 모드에서는 최고 속도로 실행
            gameScene.applySpeedChange(2.0);
          }
        }, 1000);
      }, 500);
    });
    return;
  }

  // ★ HTML 버튼 클릭 이벤트 (이름 입력 -> 메뉴 이동) ★
  if (startBtn) {
    startBtn.addEventListener("click", () => {
      if (!game) {
        alert("게임 로딩 중입니다...");
        return;
      }

      const name = nicknameInput.value.trim();
      if (name.length < 1) {
        alert("이름을 입력해주세요!");
        return;
      }

      currentPlayerName = name;
      partnerName = "";

      overlay.style.display = "none";
      game.scene.start("MenuScene");
    });
  }
}

bootstrap();
