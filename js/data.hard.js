// data.js 파일
export const GAME_CONFIG = {
  initialGold: 1200,
  maxEnemies: 60,
  roundTime: 60,
  spawnInterval: 1000,
  unitSummonCost: 150,
  bgColors: {
    normal: 0x050510,
    boss: 0x2c0404,
  },
};

// =================================================================
// [UNIT DATA] 밸런스 패치 v3 (5배 배율 적용)
// Speed: 낮을수록 빠름 (Min: 400)
// =================================================================
export const UNIT_DATA = {
  // ===============================================================
  // [Tier 1] 평균 DPS: ~15
  // ===============================================================
  slayer_basic: {
    name: "일반 대원",
    tier: 1,
    color: 0x95a5a6,
    dmg: 15,
    speed: 1000, // 15 DPS
    range: 80,
    type: "slayer_basic",
  },
  crow: {
    name: "꺾쇠 까마귀",
    tier: 1,
    color: 0x2d3436,
    dmg: 10,
    speed: 650, // ~15.3 DPS
    range: 100,
    type: "crow_attack",
  },
  kakushi: {
    name: "은(Kakushi)",
    tier: 1,
    color: 0x555555,
    dmg: 6,
    speed: 400, // 15 DPS
    range: 80,
    type: "kakushi_support",
  },

  // ===============================================================
  // [Tier 2] 평균 DPS: ~75 (T1의 5배)
  // ===============================================================
  tanjiro: {
    name: "탄지로(물)",
    tier: 2,
    color: 0x2980b9,
    dmg: 60,
    speed: 800, // 75 DPS
    range: 100,
    type: "tanjiro_water",
  },
  zenitsu: {
    name: "젠이츠(기절)",
    tier: 2,
    color: 0xf1c40f,
    dmg: 75,
    speed: 1000, // 75 DPS
    range: 110,
    type: "zenitsu_thunder",
  },
  inosuke: {
    name: "이노스케",
    tier: 2,
    color: 0x7f8c8d,
    dmg: 68,
    speed: 900, // ~75.5 DPS
    range: 90,
    type: "inosuke_beast",
  },
  genya: {
    name: "겐야(총)",
    tier: 2,
    color: 0x8e44ad,
    dmg: 53,
    speed: 700, // ~75.7 DPS
    range: 220,
    type: "genya_gun",
  },
  kanao: {
    name: "츠유리 카나오",
    tier: 2,
    color: 0xe84393,
    dmg: 85,
    speed: 1100, // ~77 DPS (살짝 높음)
    range: 110,
    type: "kanao_flower",
  },
  aoi: {
    name: "칸자키 아오이",
    tier: 2,
    color: 0x2ecc71,
    dmg: 30, // 서포터라 딜 낮음
    speed: 500, // 60 DPS
    range: 100,
    type: "aoi_support",
  },

  // ===============================================================
  // [Tier 3] 평균 DPS: ~375 (T2의 5배)
  // ===============================================================
  urokodaki: {
    name: "우로코다키",
    tier: 3,
    color: 0x34495e,
    dmg: 345,
    speed: 920, // 375 DPS
    range: 120,
    type: "urokodaki_water",
  },
  jigoro: {
    name: "쿠와지마",
    tier: 3,
    color: 0xd35400,
    dmg: 375,
    speed: 1000, // 375 DPS
    range: 120,
    type: "jigoro_thunder",
  },
  haganezuka: {
    name: "하가네즈카",
    tier: 3,
    color: 0xe17055,
    dmg: 600, // 한방 딜러
    speed: 1500, // 400 DPS (공속이 느려 딜로스 감안하여 DPS 살짝 높게)
    range: 100,
    type: "haganezuka_angry",
  },
  sabito: {
    name: "사비토(영혼)",
    tier: 3,
    color: 0xa29bfe,
    dmg: 320,
    speed: 850, // ~376 DPS
    range: 140,
    type: "sabito_spirit",
  },
  nezuko_box: {
    name: "네즈코(나무상자)",
    tier: 3,
    color: 0xe74c3c,
    dmg: 280,
    speed: 750, // ~373 DPS
    range: 100,
    type: "nezuko_kick",
  },
  yushiro: {
    name: "유시로",
    tier: 3,
    color: 0xa5b1c2,
    dmg: 338,
    speed: 900, // ~375 DPS
    range: 110,
    type: "yushiro_paper",
  },
  murata: {
    name: "무라타(운)",
    tier: 3,
    color: 0xd2dae2,
    dmg: 265,
    speed: 700, // ~378 DPS
    range: 120,
    type: "murata_water",
  },

  // ===============================================================
  // [Tier 4] 주(Hashira) 평균 DPS: ~1,900 (T3의 5배)
  // * 교메이(암주)는 T3+T3 조합이므로 타 T4보다 강하게 설정
  // ===============================================================
  giyu: {
    name: "수주 기유",
    tier: 4,
    color: 0x0984e3,
    dmg: 1400,
    speed: 750, // ~1866 DPS
    range: 150,
    type: "giyu_water",
    cutscene: "giyu_cutscene",
  },
  rengoku: {
    name: "염주 렌고쿠",
    tier: 4,
    color: 0xff7675,
    dmg: 1900,
    speed: 1000, // 1900 DPS
    range: 160,
    type: "rengoku_fire",
    cutscene: "rengoku_cutscene",
  },
  tengen: {
    name: "음주 텐겐",
    tier: 4,
    color: 0xdfe6e9,
    dmg: 1500,
    speed: 800, // 1875 DPS
    range: 150,
    type: "tengen_sound",
    cutscene: "tengen_cutscene",
  },
  shinobu: {
    name: "충주 시노부",
    tier: 4,
    color: 0xa29bfe,
    dmg: 950,
    speed: 500, // 1900 DPS (매우 빠름)
    range: 150,
    type: "shinobu_poison",
    cutscene: "shinobu_cutscene",
  },
  kanae: {
    name: "화주 카나에",
    tier: 4,
    color: 0xffcccc,
    dmg: 1250,
    speed: 670, // ~1865 DPS
    range: 160,
    type: "kanae_flower",
    cutscene: "Kanae_cutscene",
  },
  muichiro: {
    name: "하주 무이치로",
    tier: 4,
    color: 0x74b9ff,
    dmg: 1750,
    speed: 920, // ~1902 DPS
    range: 170,
    type: "muichiro_mist",
    cutscene: "muichiro_cutscene",
  },
  mitsuri: {
    name: "연주 미츠리",
    tier: 4,
    color: 0xfd79a8,
    dmg: 1580,
    speed: 830, // ~1903 DPS
    range: 150,
    type: "mitsuri_love",
    cutscene: "mitsuri_cutscene",
  },
  obanai: {
    name: "사주 오바나이",
    tier: 4,
    color: 0x636e72,
    dmg: 1650,
    speed: 870, // ~1896 DPS
    range: 145,
    type: "obanai_snake",
    cutscene: "obanai_cutscene",
  },
  sanemi: {
    name: "풍주 사네미",
    tier: 4,
    color: 0x55efc4,
    dmg: 1850,
    speed: 970, // ~1907 DPS
    range: 140,
    type: "sanemi_wind",
    cutscene: "sanemi_cutscene",
  },
  // [보정] 교메이는 제작 난이도(T3+T3)가 높으므로 DPS 약 20% 상향
  gyomei: {
    name: "암주 교메이",
    tier: 4,
    color: 0x2d3436,
    dmg: 3500,
    speed: 1500, // ~2333 DPS (강력함)
    range: 170,
    type: "gyomei_stone",
    cutscene: "gyomei_cutscene",
  },
  tamayo: {
    name: "타마요",
    tier: 4,
    color: 0x9b59b6,
    dmg: 1100,
    speed: 580, // ~1896 DPS
    range: 150,
    type: "tamayo_blood",
    cutscene: "tamayo_cutscene",
  },

  // ===============================================================
  // [Tier 5] 각성 평균 DPS: ~10,000 (T4의 5배)
  // * 모든 T5는 T4+T4 조합이므로 강력하게 설정
  // ===============================================================
  tanjiro_sun: {
    name: "탄지로(히노카미)",
    tier: 5,
    color: 0xff0000,
    dmg: 6500,
    speed: 650, // 10,000 DPS
    range: 180,
    type: "tanjiro_sun",
    cutscene: "tanjiro_sun_cutscene",
  },
  zenitsu_god: {
    name: "젠이츠(신속)",
    tier: 5,
    color: 0xffeb3b,
    dmg: 8500,
    speed: 850, // 10,000 DPS
    range: 190,
    type: "zenitsu_god",
    cutscene: "zenitsu_god_cutscene",
  },
  nezuko_awake: {
    name: "네즈코(각성)",
    tier: 5,
    color: 0xd63031,
    dmg: 5800,
    speed: 580, // 10,000 DPS
    range: 180,
    type: "nezuko_blood_art",
    cutscene: "nezuko_awake_cutscene",
  },
  giyu_mark: {
    name: "기유(반점)",
    tier: 5,
    color: 0x0984e3,
    dmg: 6300,
    speed: 630, // 10,000 DPS
    range: 190,
    type: "giyu_mark_water",
    cutscene: "giyu_mark_cutscene",
  },
  muichiro_mark: {
    name: "무이치로(반점)",
    tier: 5,
    color: 0x74b9ff,
    dmg: 6000,
    speed: 600, // 10,000 DPS
    range: 210,
    type: "muichiro_mark_mist",
    cutscene: "muichiro_mark_cutscene",
  },
  tamayo_yushiro: {
    name: "타마요&유시로",
    tier: 5,
    color: 0x6c5ce7,
    dmg: 4700,
    speed: 470, // 10,000 DPS
    range: 190,
    type: "tamayo_yushiro_combo",
    cutscene: "tamayo_yushiro_cutscene",
  },
  inosuke_awake: {
    name: "이노스케(각성)",
    tier: 5,
    color: 0x7f8c8d,
    dmg: 6800,
    speed: 680, // 10,000 DPS
    range: 180,
    type: "inosuke_awake_beast",
    cutscene: "inosuke_awake_cutscene",
  },

  // [신규 5티어] - 재료가 되는 T4들의 특성을 반영해 미세 조정
  rengoku_awake: {
    name: "렌고쿠(멸살)",
    tier: 5,
    color: 0xe17055,
    dmg: 9500,
    speed: 920, // ~10,326 DPS (순간 폭딜)
    range: 170,
    type: "rengoku_9th_form",
    cutscene: "rengoku_awake_cutscene",
  },
  tengen_score: {
    name: "텐겐(악보)",
    tier: 5,
    color: 0xb2bec3,
    dmg: 7300,
    speed: 730, // 10,000 DPS
    range: 160,
    type: "tengen_musical_score",
    cutscene: "tengen_score_cutscene",
  },
  shinobu_dance: {
    name: "시노부(종의형)",
    tier: 5,
    color: 0x6c5ce7,
    dmg: 11000, // 한방 데미지 매우 높음
    speed: 1050, // ~10,476 DPS
    range: 150,
    type: "shinobu_last_dance",
    cutscene: "shinobu_dance_cutscene",
  },
  kanae_spirit: {
    name: "카나에(꽃의영)",
    tier: 5,
    color: 0xff9ff3,
    dmg: 5500,
    speed: 550, // 10,000 DPS
    range: 200,
    type: "kanae_flower_final",
    cutscene: "kanae_spirit_cutscene",
  },
  sanemi_mark: {
    name: "사네미(반점)",
    tier: 5,
    color: 0x00b894,
    dmg: 8000,
    speed: 790, // ~10,126 DPS
    range: 160,
    type: "sanemi_typhoon",
    cutscene: "sanemi_mark_cutscene",
  },
  obanai_mark: {
    name: "오바나이(반점)",
    tier: 5,
    color: 0x2d3436,
    dmg: 7700,
    speed: 760, // ~10,131 DPS
    range: 170,
    type: "obanai_serpent_god",
    cutscene: "obanai_mark_cutscene",
  },
  mitsuri_mark: {
    name: "미츠리(반점)",
    tier: 5,
    color: 0xfd79a8,
    dmg: 7100,
    speed: 710, // 10,000 DPS
    range: 200,
    type: "mitsuri_love_cat",
    cutscene: "mitsuri_mark_cutscene",
  },

  // ===============================================================
  // [Tier 6] 신화 (T5의 5.5배) - Target DPS: 54,000 ~ 59,000
  // * 사거리(Range)가 길면 공속(Speed)을 느리게 조정 (한방 딜 ↑)
  // * 사거리(Range)가 짧으면 공속(Speed)을 빠르게 조정 (연타 딜 ↑)
  // ===============================================================
  tanjiro_final: {
    name: "탄지로(13형)",
    tier: 6,
    color: 0xff4757,
    dmg: 47600,
    speed: 850, // [DPS: 56,000] 사거리 김(210)
    range: 210,
    type: "tanjiro_13th",
    cutscene: "tanjiro_final_cutscene",
  },
  gyomei_mark: {
    name: "교메이(반점)",
    tier: 6,
    color: 0x2d3436,
    dmg: 58000,
    speed: 1000, // [DPS: 58,000] 사거리 매우 김(230)
    range: 230,
    type: "gyomei_mark_stone",
    cutscene: "gyomei_mark_cutscene",
  },
  yoriichi: {
    name: "요리이치",
    tier: 6,
    color: 0xffd700,
    dmg: 50400,
    speed: 900, // [DPS: 56,000] 사거리 김(220)
    range: 220,
    type: "yoriichi_sun",
    cutscene: "yoriichi_cutscene",
  },
  inosuke_king: {
    name: "이노스케(산의 왕)",
    tier: 6,
    color: 0x3498db,
    dmg: 19600,
    speed: 350, // [DPS: 56,000] 사거리 짧음(150)
    range: 150, // 근접 컨셉 강화
    type: "inosuke_king_beast",
    cutscene: "inosuke_king_cutscene",
  },
  zenitsu_7th: {
    name: "젠이츠(화뢰신)",
    tier: 6,
    color: 0xfff200,
    dmg: 17100,
    speed: 300, // [DPS: 57,000] 사거리 짧음(160)
    range: 160, // 순간이동 컨셉
    type: "zenitsu_7th_form",
    cutscene: "zenitsu_7th_cutscene",
  },
  giyu_calm: {
    name: "기유(잔잔한 물)",
    tier: 6,
    color: 0x74b9ff,
    dmg: 53200,
    speed: 950, // [DPS: 56,000] 사거리 김(210)
    range: 210,
    type: "giyu_dead_calm",
    cutscene: "giyu_calm_cutscene",
  },
  sanemi_wind_god: {
    name: "사네미(바람의 신)",
    tier: 6,
    color: 0x55efc4,
    dmg: 43500,
    speed: 750, // [DPS: 58,000] 사거리 보통(200)
    range: 200,
    type: "sanemi_wind_god",
    cutscene: "sanemi_god_cutscene",
  },

  // [신규] 오바나이&미츠리 (커플)
  love_snake_couple: {
    name: "오바나이&미츠리",
    tier: 6,
    color: 0xffa502,
    dmg: 28000,
    speed: 500, // [DPS: 56,000] 사거리 약간 짧음(180)
    range: 180,
    type: "love_snake_couple_attack",
    cutscene: "love_snake_cutscene",
  },

  // [신규] 무이치로(내비세) - 스나이퍼 컨셉
  muichiro_transparent: {
    name: "무이치로(내비세)",
    tier: 6,
    color: 0xdfe6e9,
    dmg: 82500,
    speed: 1500, // [DPS: 55,000] 사거리 압도적(260)
    range: 260,
    type: "muichiro_transparent_world",
    cutscene: "muichiro_trans_cutscene",
  },

  // ========================================================
  // [HIDDEN UNITS] (일반 T6 대비 1.1~1.2배 강력함)
  // Target DPS: 62,000 ~ 68,000
  // ========================================================
  yoriichi_zero: {
    name: "요리이치 영식",
    tier: 5, // T5 히든 (T5 평균 10,000 대비 1.2배)
    color: 0x7f8c8d,
    dmg: 4800,
    speed: 400, // [DPS: 12,000] T5 최상위
    range: 110,
    type: "yoriichi_doll",
    cutscene: "yoriichi_zero_cutscene",
  },
  rengoku_smile: {
    name: "렌고쿠(마지막 미소)",
    tier: 5, // T5 히든
    color: 0xffa502,
    dmg: 10000,
    speed: 800, // [DPS: 12,500] T5 최상위
    range: 180,
    type: "rengoku_smile_effect",
    cutscene: "rengoku_smile_cutscene",
  },

  // [히든 T6]
  koku: {
    name: "코쿠시보(상현1)",
    tier: 6,
    color: 0xffd700,
    dmg: 54400,
    speed: 850, // [DPS: 64,000] 사거리 김(240)
    range: 240,
    type: "kokushibo_moon",
    cutscene: "koku_cutscene",
  },
  tanjiro_king: {
    name: "탄지로(오니의 왕)",
    tier: 6,
    color: 0x2d3436,
    dmg: 29250,
    speed: 450, // [DPS: 65,000] 사거리 짧음(160)
    range: 160,
    type: "tanjiro_demon_king",
    cutscene: "tanjiro_king_cutscene",
  },
  twin_destiny: {
    name: "쌍둥이의 운명",
    tier: 6,
    color: 0xb33939,
    dmg: 60000,
    speed: 400,
    range: 220,
    type: "twin_destiny_combo",
    cutscene: "twin_destiny_cutscene",
  },
  rengoku_legend: {
    name: "렌고쿠(마음의 불꽃)",
    tier: 6,
    color: 0xff4757,
    dmg: 56700,
    speed: 900, // [DPS: 63,000] 사거리 김(210)
    range: 210,
    type: "rengoku_legend_fire",
    cutscene: "rengoku_legend_cutscene",
  },

  // [히든 T6] 네즈코
  nezuko_sun: {
    name: "네즈코(태양의 극복)",
    tier: 6,
    color: 0xff7675,
    dmg: 37200,
    speed: 600, // [DPS: 62,000] 사거리 적당(190)
    range: 190,
    type: "nezuko_sun_conqueror",
    cutscene: "nezuko_sun_cutscene",
  },
};

// =================================================================
// [RECIPES] - 밸런스 패치 v5 (렌고쿠 히든 조합 수정 & 주석 완비)
// =================================================================
export const RECIPES = [
  // =============================================================
  // [1단계] 기초 조합 (T1 + T1 -> T2)
  // =============================================================

  // 일반 + 까마귀 = 탄지로
  { a: "slayer_basic", b: "crow", result: "tanjiro" },

  // 까마귀 + 까마귀 = 젠이츠
  { a: "crow", b: "crow", result: "zenitsu" },

  // 일반 + 은 = 이노스케
  { a: "slayer_basic", b: "kakushi", result: "inosuke" },

  // 은 + 은 = 겐야
  { a: "kakushi", b: "kakushi", result: "genya" },

  // 까마귀 + 은 = 카나오 (기존 유지)
  { a: "crow", b: "kakushi", result: "kanao" },

  // 일반 + 일반 = 아오이
  { a: "slayer_basic", b: "slayer_basic", result: "aoi" },

  // =============================================================
  // [2단계] 성장 조합 (T2 + T1 -> T3)
  // =============================================================

  // 탄지로 + 까마귀 = 우로코다키
  { a: "tanjiro", b: "crow", result: "urokodaki" },

  // 탄지로 + 은 = 네즈코(상자)
  { a: "tanjiro", b: "kakushi", result: "nezuko_box" },

  // 젠이츠 + 일반 = 쿠와지마
  { a: "zenitsu", b: "slayer_basic", result: "jigoro" },

  // 이노스케 + 은 = 하가네즈카
  { a: "inosuke", b: "kakushi", result: "haganezuka" },

  // 겐야 + 까마귀 = 무라타
  { a: "genya", b: "crow", result: "murata" },

  // 카나오 + 은 = 사비토
  { a: "kanao", b: "kakushi", result: "sabito" },

  // 아오이 + 겐야 = 유시로
  { a: "aoi", b: "genya", result: "yushiro" },

  // =============================================================
  // [3단계] 지주(Hashira) 조합 (T3 + T2 -> T4)
  // =============================================================

  // 우로코다키(T3) + 사비토(T3) = 수주 기유
  { a: "urokodaki", b: "sabito", result: "giyu" },

  // 네즈코상자(T3) + 탄지로(T2) = 염주 렌고쿠
  { a: "nezuko_box", b: "tanjiro", result: "rengoku" },

  // 무라타(T3) + 젠이츠(T2) = 음주 텐겐
  { a: "murata", b: "zenitsu", result: "tengen" },

  // 네즈코상자(T3) + 아오이(T2) = 충주 시노부
  { a: "nezuko_box", b: "aoi", result: "shinobu" },

  // 사비토(T3) + 카나오(T2) = 화주 카나에
  { a: "sabito", b: "kanao", result: "kanae" },

  // 사비토(T3) + 겐야(T2) = 하주 무이치로
  { a: "sabito", b: "genya", result: "muichiro" },

  // 하가네즈카(T3) + 탄지로(T2) = 연주 미츠리
  { a: "haganezuka", b: "tanjiro", result: "mitsuri" },

  // 무라타(T3) + 이노스케(T2) = 사주 오바나이
  { a: "murata", b: "inosuke", result: "obanai" },

  // 쿠와지마(T3) + 겐야(T2) = 풍주 사네미
  { a: "jigoro", b: "genya", result: "sanemi" },

  // 우로코다키(T3) + 쿠와지마(T3) = 암주 교메이
  { a: "urokodaki", b: "jigoro", result: "gyomei" },

  // 유시로(T3) + 아오이(T2) = 타마요
  { a: "yushiro", b: "aoi", result: "tamayo" },

  // =============================================================
  // [4단계] 각성 조합 (T4 + T4 -> T5)
  // =============================================================

  // 기유 + 렌고쿠 = 탄지로(히노카미)
  { a: "giyu", b: "rengoku", result: "tanjiro_sun" },

  // 텐겐 + 교메이 = 젠이츠(신속)
  { a: "tengen", b: "gyomei", result: "zenitsu_god" },

  // 미츠리 + 시노부 = 네즈코(각성)
  { a: "mitsuri", b: "shinobu", result: "nezuko_awake" },

  // 시노부 + 기유 = 이노스케(각성)
  { a: "shinobu", b: "giyu", result: "inosuke_awake" },

  // 기유 + 사네미 = 기유(반점)
  { a: "giyu", b: "sanemi", result: "giyu_mark" },

  // 무이치로 + 렌고쿠 = 무이치로(반점)
  { a: "muichiro", b: "rengoku", result: "muichiro_mark" },

  // 타마요 + 시노부 = 타마요&유시로
  { a: "tamayo", b: "shinobu", result: "tamayo_yushiro" },

  // 렌고쿠 + 미츠리 = 렌고쿠(멸살)
  { a: "rengoku", b: "mitsuri", result: "rengoku_awake" },

  // 텐겐 + 오바나이 = 텐겐(악보)
  { a: "tengen", b: "obanai", result: "tengen_score" },

  // 시노부 + 카나에 = 시노부(종의형)
  { a: "shinobu", b: "kanae", result: "shinobu_dance" },

  // 카나에 + 사네미 = 카나에(꽃의영)
  { a: "kanae", b: "sanemi", result: "kanae_spirit" },

  // 사네미 + 교메이 = 사네미(반점)
  { a: "sanemi", b: "gyomei", result: "sanemi_mark" },

  // 오바나이 + 미츠리 = 오바나이(반점)
  { a: "obanai", b: "mitsuri", result: "obanai_mark" },

  // 미츠리 + 무이치로 = 미츠리(반점)
  { a: "mitsuri", b: "muichiro", result: "mitsuri_mark" },

  // =============================================================
  // [5단계] 신화 조합 (T5 + T5 -> T6)
  // =============================================================

  // 탄지로(히노카미) + 기유(반점) = 탄지로(13형)
  { a: "tanjiro_sun", b: "giyu_mark", result: "tanjiro_final" },

  // 사네미(반점) + 무이치로(반점) = 교메이(반점)
  { a: "sanemi_mark", b: "muichiro_mark", result: "gyomei_mark" },

  // 탄지로(히노카미) + 렌고쿠(멸살) = 요리이치
  { a: "tanjiro_sun", b: "rengoku_awake", result: "yoriichi" },

  // 이노스케(각성) + 젠이츠(신속) = 이노스케(산의 왕)
  { a: "inosuke_awake", b: "zenitsu_god", result: "inosuke_king" },

  // 젠이츠(신속) + 텐겐(악보) = 젠이츠(화뢰신)
  { a: "zenitsu_god", b: "tengen_score", result: "zenitsu_7th" },

  // 기유(반점) + 시노부(종의형) = 기유(잔잔한 물)
  { a: "giyu_mark", b: "shinobu_dance", result: "giyu_calm" },

  // 사네미(반점) + 카나에(꽃의영) = 사네미(바람의 신)
  { a: "sanemi_mark", b: "kanae_spirit", result: "sanemi_wind_god" },

  // [T6] 오바나이(반점)(T5) + 미츠리(반점)(T5) = 오바나이&미츠리
  // 설명: 서로의 마음을 확인하고 함께 싸우는 두 지주 (커플 조합)
  // * 현재 사용처가 없는 오바나이와 미츠리를 구제하는 핵심 조합
  { a: "obanai_mark", b: "mitsuri_mark", result: "love_snake_couple" },

  // [T6] 무이치로(반점)(T5) + 텐겐(악보)(T5) = 무이치로(내비세)
  // 설명: 텐겐의 전투 센스(악보)를 전수받아 내비세에 도달 (속도+안개)
  // * 젠이츠 재료로만 쓰이던 텐겐, 교메이 재료로만 쓰이던 무이치로 활용
  { a: "muichiro_mark", b: "tengen_score", result: "muichiro_transparent" },

  // =============================================================
  // [HIDDEN] 히든 조합법
  // =============================================================

  // 오바나이(T4) + 무이치로(T4) = 요리이치 영식 (T5급)
  { a: "obanai", b: "muichiro", result: "yoriichi_zero", hidden: true },

  // 요리이치 영식(Hidden) + 사네미(반점)(T5) = 코쿠시보 (T6급)
  { a: "yoriichi_zero", b: "sanemi_mark", result: "koku", hidden: true },

  // 기유(반점)(T5) + 네즈코(각성)(T5) = 탄지로(오니의 왕) (T6급)
  { a: "giyu_mark", b: "nezuko_awake", result: "tanjiro_king", hidden: true },

  // 요리이치(T6) + 코쿠시보(T6) = 쌍둥이의 운명 (T6 최강)
  { a: "yoriichi", b: "koku", result: "twin_destiny", hidden: true },

  // [변경] 렌고쿠(T4) + 카나에(T4) = 렌고쿠(마지막 미소) (T5급)
  // * 의미: 먼저 떠난 지주들의 숭고한 정신 (재료 밸런스 최적화)
  { a: "rengoku", b: "kanae", result: "rengoku_smile", hidden: true },

  // 렌고쿠 미소(Hidden) + 탄지로 히노카미(T5) = 렌고쿠(마음의 불꽃) (T6급)
  {
    a: "rengoku_smile",
    b: "tanjiro_sun",
    result: "rengoku_legend",
    hidden: true,
  },

  // [히든] 네즈코(각성)(T5) + 타마요&유시로(T5) = 네즈코(태양의 극복)
  // 설명: 타마요의 약으로 태양을 극복한 네즈코
  // * T6 진입이 불가능했던 타마요&유시로를 히든 재료로 격상
  {
    a: "nezuko_awake",
    b: "tamayo_yushiro",
    result: "nezuko_sun",
    hidden: true,
  },
];

export const ENEMY_CONFIG = {
  bossInterval: 10,
  finalRound: 90,
  types: {
    lower: { color: 0x555555, radius: 15, name: "하현 졸개", hpMult: 150 },

    boss_rui: {
      color: 0xffffff,
      radius: 25,
      name: "하현5 루이",
      hpMult: 100000,
      cutscene: "boss_rui_img",
    },
    boss_enmu: {
      color: 0x8e44ad,
      radius: 25,
      name: "하현1 엔무",
      hpMult: 200000,
      cutscene: "boss_enmu_img",
    },
    boss_daki: {
      color: 0x00b894,
      radius: 30,
      name: "상현6 다키",
      hpMult: 500000,
      cutscene: "boss_daki_img",
    },
    boss_gyokko: {
      color: 0x74b9ff,
      radius: 30,
      name: "상현5 굣코",
      hpMult: 1000000,
      cutscene: "boss_gyokko_img",
    },
    boss_hantengu: {
      color: 0xff7675,
      radius: 30,
      name: "상현4 한텐구",
      hpMult: 3000000,
      cutscene: "boss_hantengu_img",
    },
    boss_akaza: {
      color: 0xe17055,
      radius: 35,
      name: "상현3 아카자",
      hpMult: 10000000,
      cutscene: "boss_akaza_img",
    },
    boss_doma: {
      color: 0x81ecec,
      radius: 35,
      name: "상현2 도우마",
      hpMult: 20000000,
      cutscene: "boss_doma_img",
    },
    boss_koku: {
      color: 0x6c5ce7,
      radius: 40,
      name: "상현1 코쿠시보",
      hpMult: 30000000,
      cutscene: "boss_koku_img",
    },
    boss_muzan: {
      color: 0x000000,
      radius: 50,
      name: "키부츠지 무잔",
      hpMult: 60000000,
      cutscene: "boss_muzan_img",
    },
  },
};

// =====================================================================
// 시너지 (Synergy) - T6 유닛 조합 보너스
// 3명이 필드에 모두 배치되면 해당 유닛 공격력 +20%
// 여러 시너지에 동시에 포함되면 보너스가 합연산으로 누적됨
// =====================================================================
export const SYNERGIES = [
  {
    name: "카마도 혈통",
    units: ["tanjiro_final", "nezuko_sun", "tanjiro_king"],
  },
  {
    name: "동기조의 유대",
    units: ["tanjiro_final", "inosuke_king", "zenitsu_7th"],
  },
  {
    name: "상현1 토벌대",
    units: ["gyomei_mark", "sanemi_wind_god", "muichiro_transparent"],
  },
  { name: "쌍둥이의 인연", units: ["yoriichi", "koku", "twin_destiny"] },
  {
    name: "귀살대 핵심",
    units: ["tanjiro_final", "giyu_calm", "rengoku_legend"],
  },
  {
    name: "주 연합전선",
    units: ["giyu_calm", "sanemi_wind_god", "love_snake_couple"],
  },
  {
    name: "불꽃의 의지",
    units: ["rengoku_legend", "nezuko_sun", "love_snake_couple"],
  },
  { name: "달의 호흡", units: ["koku", "muichiro_transparent", "gyomei_mark"] },
  { name: "귀의 왕 계보", units: ["twin_destiny", "yoriichi", "tanjiro_king"] },
  { name: "물의 계보", units: ["giyu_calm", "inosuke_king", "zenitsu_7th"] },
];

export const SYNERGY_DPS_MULTIPLIER = 1.2;
