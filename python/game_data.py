"""
game_data.py - 귀멸의 칼날 랜덤 디펜스 게임 데이터
data.normal.js에서 추출한 스토리 모드(Normal) 데이터
"""

# =====================================================================
# 게임 설정 (Normal Mode)
# =====================================================================
GAME_CONFIG = {
    'initialGold': 1200,
    'maxEnemies': 60,
    'roundTime': 60,
    'spawnInterval': 1.2,       # 적 스폰 간격 (초)
    'unitSummonCost': 150,
    'finalRound': 90,
    'bossInterval': 10,         # 몇 라운드마다 보스
}

# =====================================================================
# 유닛 데이터 (tier, dmg, speed → dps = dmg * 1000 / speed)
# =====================================================================
UNIT_DATA = {
    # --- Tier 1 (평균 DPS ~15) ---
    'slayer_basic': {'tier': 1, 'dmg': 15, 'speed': 1000, 'range': 80},
    'crow':         {'tier': 1, 'dmg': 10, 'speed': 650,  'range': 100},
    'kakushi':      {'tier': 1, 'dmg': 6,  'speed': 400,  'range': 80},

    # --- Tier 2 (평균 DPS ~75) ---
    'tanjiro':  {'tier': 2, 'dmg': 60,  'speed': 800,  'range': 100},
    'zenitsu':  {'tier': 2, 'dmg': 75,  'speed': 1000, 'range': 110},
    'inosuke':  {'tier': 2, 'dmg': 68,  'speed': 900,  'range': 90},
    'genya':    {'tier': 2, 'dmg': 53,  'speed': 700,  'range': 220},
    'kanao':    {'tier': 2, 'dmg': 85,  'speed': 1100, 'range': 110},
    'aoi':      {'tier': 2, 'dmg': 30,  'speed': 500,  'range': 100},

    # --- Tier 3 (평균 DPS ~375) ---
    'urokodaki':  {'tier': 3, 'dmg': 345, 'speed': 920,  'range': 120},
    'jigoro':     {'tier': 3, 'dmg': 375, 'speed': 1000, 'range': 120},
    'haganezuka': {'tier': 3, 'dmg': 600, 'speed': 1500, 'range': 100},
    'sabito':     {'tier': 3, 'dmg': 320, 'speed': 850,  'range': 140},
    'nezuko_box': {'tier': 3, 'dmg': 280, 'speed': 750,  'range': 100},
    'yushiro':    {'tier': 3, 'dmg': 338, 'speed': 900,  'range': 110},
    'murata':     {'tier': 3, 'dmg': 265, 'speed': 700,  'range': 120},

    # --- Tier 4 주(Hashira) (평균 DPS ~1900) ---
    'giyu':     {'tier': 4, 'dmg': 1400, 'speed': 750,  'range': 150},
    'rengoku':  {'tier': 4, 'dmg': 1900, 'speed': 1000, 'range': 160},
    'tengen':   {'tier': 4, 'dmg': 1500, 'speed': 800,  'range': 150},
    'shinobu':  {'tier': 4, 'dmg': 950,  'speed': 500,  'range': 150},
    'kanae':    {'tier': 4, 'dmg': 1250, 'speed': 670,  'range': 160},
    'muichiro': {'tier': 4, 'dmg': 1750, 'speed': 920,  'range': 170},
    'mitsuri':  {'tier': 4, 'dmg': 1580, 'speed': 830,  'range': 150},
    'obanai':   {'tier': 4, 'dmg': 1650, 'speed': 870,  'range': 145},
    'sanemi':   {'tier': 4, 'dmg': 1850, 'speed': 970,  'range': 140},
    'gyomei':   {'tier': 4, 'dmg': 3500, 'speed': 1500, 'range': 170},
    'tamayo':   {'tier': 4, 'dmg': 1100, 'speed': 580,  'range': 150},

    # --- Tier 5 각성 (평균 DPS ~10000) ---
    'tanjiro_sun':    {'tier': 5, 'dmg': 6500,  'speed': 650,  'range': 180},
    'zenitsu_god':    {'tier': 5, 'dmg': 8500,  'speed': 850,  'range': 190},
    'nezuko_awake':   {'tier': 5, 'dmg': 5800,  'speed': 580,  'range': 180},
    'giyu_mark':      {'tier': 5, 'dmg': 6300,  'speed': 630,  'range': 190},
    'muichiro_mark':  {'tier': 5, 'dmg': 6000,  'speed': 600,  'range': 210},
    'tamayo_yushiro': {'tier': 5, 'dmg': 4700,  'speed': 470,  'range': 190},
    'inosuke_awake':  {'tier': 5, 'dmg': 6800,  'speed': 680,  'range': 180},
    'rengoku_awake':  {'tier': 5, 'dmg': 9500,  'speed': 920,  'range': 170},
    'tengen_score':   {'tier': 5, 'dmg': 7300,  'speed': 730,  'range': 160},
    'shinobu_dance':  {'tier': 5, 'dmg': 11000, 'speed': 1050, 'range': 150},
    'kanae_spirit':   {'tier': 5, 'dmg': 5500,  'speed': 550,  'range': 200},
    'sanemi_mark':    {'tier': 5, 'dmg': 8000,  'speed': 790,  'range': 160},
    'obanai_mark':    {'tier': 5, 'dmg': 7700,  'speed': 760,  'range': 170},
    'mitsuri_mark':   {'tier': 5, 'dmg': 7100,  'speed': 710,  'range': 200},
    'yoriichi_zero':  {'tier': 5, 'dmg': 4800,  'speed': 400,  'range': 190},
    'rengoku_smile':  {'tier': 5, 'dmg': 10000, 'speed': 800,  'range': 170},

    # --- Tier 6 신화 (평균 DPS ~56000) ---
    'tanjiro_final':       {'tier': 6, 'dmg': 47600, 'speed': 850,  'range': 210},
    'gyomei_mark':         {'tier': 6, 'dmg': 58000, 'speed': 1000, 'range': 230},
    'yoriichi':            {'tier': 6, 'dmg': 50400, 'speed': 900,  'range': 220},
    'inosuke_king':        {'tier': 6, 'dmg': 19600, 'speed': 350,  'range': 150},
    'zenitsu_7th':         {'tier': 6, 'dmg': 17100, 'speed': 300,  'range': 160},
    'giyu_calm':           {'tier': 6, 'dmg': 53200, 'speed': 950,  'range': 210},
    'sanemi_wind_god':     {'tier': 6, 'dmg': 43500, 'speed': 750,  'range': 200},
    'love_snake_couple':   {'tier': 6, 'dmg': 28000, 'speed': 500,  'range': 180},
    'muichiro_transparent':{'tier': 6, 'dmg': 82500, 'speed': 1500, 'range': 200},
    'koku':                {'tier': 6, 'dmg': 54400, 'speed': 850,  'range': 200},
    'tanjiro_king':        {'tier': 6, 'dmg': 29250, 'speed': 450,  'range': 190},
    'twin_destiny':        {'tier': 6, 'dmg': 60000, 'speed': 400,  'range': 220},
    'rengoku_legend':      {'tier': 6, 'dmg': 56700, 'speed': 900,  'range': 200},
    'nezuko_sun':          {'tier': 6, 'dmg': 37200, 'speed': 600,  'range': 200},
}

# DPS 사전 계산
for _k, _v in UNIT_DATA.items():
    _v['dps'] = _v['dmg'] * 1000.0 / _v['speed']

# =====================================================================
# 유닛 키 목록 및 인덱스 매핑
# =====================================================================
UNIT_KEYS = list(UNIT_DATA.keys())
NUM_UNIT_TYPES = len(UNIT_KEYS)  # 57
UNIT_KEY_TO_IDX = {key: i for i, key in enumerate(UNIT_KEYS)}

# 티어별 유닛 풀 (소환 시 사용)
TIER_POOL = {}
for _k, _v in UNIT_DATA.items():
    t = _v['tier']
    if t not in TIER_POOL:
        TIER_POOL[t] = []
    TIER_POOL[t].append(_k)

# =====================================================================
# 조합 레시피 (54개)
# =====================================================================
RECIPES = [
    # [1단계] T1 + T1 → T2
    {'a': 'slayer_basic', 'b': 'crow',     'result': 'tanjiro'},
    {'a': 'crow',         'b': 'crow',     'result': 'zenitsu'},
    {'a': 'slayer_basic', 'b': 'kakushi',  'result': 'inosuke'},
    {'a': 'kakushi',      'b': 'kakushi',  'result': 'genya'},
    {'a': 'crow',         'b': 'kakushi',  'result': 'kanao'},
    {'a': 'slayer_basic', 'b': 'slayer_basic', 'result': 'aoi'},

    # [2단계] T2 + T1 → T3
    {'a': 'tanjiro',  'b': 'crow',         'result': 'urokodaki'},
    {'a': 'tanjiro',  'b': 'kakushi',      'result': 'nezuko_box'},
    {'a': 'zenitsu',  'b': 'slayer_basic', 'result': 'jigoro'},
    {'a': 'inosuke',  'b': 'kakushi',      'result': 'haganezuka'},
    {'a': 'genya',    'b': 'crow',         'result': 'murata'},
    {'a': 'kanao',    'b': 'kakushi',      'result': 'sabito'},
    {'a': 'aoi',      'b': 'genya',        'result': 'yushiro'},

    # [3단계] T3 + T2/T3 → T4
    {'a': 'urokodaki',  'b': 'sabito',   'result': 'giyu'},
    {'a': 'nezuko_box', 'b': 'tanjiro',  'result': 'rengoku'},
    {'a': 'murata',     'b': 'zenitsu',  'result': 'tengen'},
    {'a': 'nezuko_box', 'b': 'aoi',      'result': 'shinobu'},
    {'a': 'sabito',     'b': 'kanao',    'result': 'kanae'},
    {'a': 'sabito',     'b': 'genya',    'result': 'muichiro'},
    {'a': 'haganezuka', 'b': 'tanjiro',  'result': 'mitsuri'},
    {'a': 'murata',     'b': 'inosuke',  'result': 'obanai'},
    {'a': 'jigoro',     'b': 'genya',    'result': 'sanemi'},
    {'a': 'urokodaki',  'b': 'jigoro',   'result': 'gyomei'},
    {'a': 'yushiro',    'b': 'aoi',      'result': 'tamayo'},

    # [4단계] T4 + T4 → T5
    {'a': 'giyu',     'b': 'rengoku',  'result': 'tanjiro_sun'},
    {'a': 'tengen',   'b': 'gyomei',   'result': 'zenitsu_god'},
    {'a': 'mitsuri',  'b': 'shinobu',  'result': 'nezuko_awake'},
    {'a': 'shinobu',  'b': 'giyu',     'result': 'inosuke_awake'},
    {'a': 'giyu',     'b': 'sanemi',   'result': 'giyu_mark'},
    {'a': 'muichiro', 'b': 'rengoku',  'result': 'muichiro_mark'},
    {'a': 'tamayo',   'b': 'shinobu',  'result': 'tamayo_yushiro'},
    {'a': 'rengoku',  'b': 'mitsuri',  'result': 'rengoku_awake'},
    {'a': 'tengen',   'b': 'obanai',   'result': 'tengen_score'},
    {'a': 'shinobu',  'b': 'kanae',    'result': 'shinobu_dance'},
    {'a': 'kanae',    'b': 'sanemi',   'result': 'kanae_spirit'},
    {'a': 'sanemi',   'b': 'gyomei',   'result': 'sanemi_mark'},
    {'a': 'obanai',   'b': 'mitsuri',  'result': 'obanai_mark'},
    {'a': 'mitsuri',  'b': 'muichiro', 'result': 'mitsuri_mark'},

    # [5단계] T5 + T5 → T6
    {'a': 'tanjiro_sun',   'b': 'giyu_mark',      'result': 'tanjiro_final'},
    {'a': 'sanemi_mark',   'b': 'muichiro_mark',  'result': 'gyomei_mark'},
    {'a': 'tanjiro_sun',   'b': 'rengoku_awake',  'result': 'yoriichi'},
    {'a': 'inosuke_awake', 'b': 'zenitsu_god',    'result': 'inosuke_king'},
    {'a': 'zenitsu_god',   'b': 'tengen_score',   'result': 'zenitsu_7th'},
    {'a': 'giyu_mark',     'b': 'shinobu_dance',  'result': 'giyu_calm'},
    {'a': 'sanemi_mark',   'b': 'kanae_spirit',   'result': 'sanemi_wind_god'},
    {'a': 'obanai_mark',   'b': 'mitsuri_mark',   'result': 'love_snake_couple'},
    {'a': 'muichiro_mark', 'b': 'tengen_score',   'result': 'muichiro_transparent'},

    # [히든] 특수 조합
    {'a': 'obanai',        'b': 'muichiro',       'result': 'yoriichi_zero'},
    {'a': 'yoriichi_zero', 'b': 'sanemi_mark',    'result': 'koku'},
    {'a': 'giyu_mark',     'b': 'nezuko_awake',   'result': 'tanjiro_king'},
    {'a': 'yoriichi',      'b': 'koku',           'result': 'twin_destiny'},
    {'a': 'rengoku',       'b': 'kanae',          'result': 'rengoku_smile'},
    {'a': 'rengoku_smile', 'b': 'tanjiro_sun',    'result': 'rengoku_legend'},
    {'a': 'nezuko_awake',  'b': 'tamayo_yushiro', 'result': 'nezuko_sun'},
]

NUM_RECIPES = len(RECIPES)  # 54

# =====================================================================
# 보스 데이터
# =====================================================================
BOSS_DATA = {
    10: {'name': '하현5 루이',       'hp': 50000},
    20: {'name': '하현1 엔무',       'hp': 100000},
    30: {'name': '상현6 다키',       'hp': 250000},
    40: {'name': '상현5 굣코',       'hp': 600000},
    50: {'name': '상현4 한텐구',     'hp': 1000000},
    60: {'name': '상현3 아카자',     'hp': 2000000},
    70: {'name': '상현2 도우마',     'hp': 5000000},
    80: {'name': '상현1 코쿠시보',   'hp': 10000000},
    90: {'name': '키부츠지 무잔',    'hp': 20000000},
}

# =====================================================================
# 행동 공간 정의
# =====================================================================
# 0: WAIT
# 1: SUMMON
# 2 ~ 58: PLACE(unit_keys[i-2])
# 59 ~ 115: SELL(unit_keys[i-59])
# 116 ~ 169: COMBINE(recipes[i-116])
NUM_ACTIONS = 1 + 1 + NUM_UNIT_TYPES + NUM_UNIT_TYPES + NUM_RECIPES  # 170
OBS_DIM = 10 + NUM_UNIT_TYPES  # 67 (v4: 개별 유닛 카운트 복원)

ACTION_WAIT = 0
ACTION_SUMMON = 1
ACTION_PLACE_START = 2
ACTION_PLACE_END = 2 + NUM_UNIT_TYPES - 1            # 58
ACTION_SELL_START = 2 + NUM_UNIT_TYPES                # 59
ACTION_SELL_END = 2 + 2 * NUM_UNIT_TYPES - 1         # 115
ACTION_COMBINE_START = 2 + 2 * NUM_UNIT_TYPES         # 116
ACTION_COMBINE_END = NUM_ACTIONS - 1                   # 169

# 소환 확률 (JS 코드와 동일)
SUMMON_PROBS = {1: 0.70, 2: 0.20, 3: 0.10}


def get_normal_enemy_hp(round_num):
    """일반 적 체력 계산 (game.js spawnEnemy 공식 그대로)"""
    base_hp = round_num * 150  # game.js: this.round * 150
    if round_num > 10:
        base_hp += round_num * round_num * 30
    if round_num >= 20:
        base_hp = base_hp * 1.5
    return int(base_hp)


def get_kill_gold(round_num):
    """적 처치 시 골드 보상"""
    reward = 5 + round_num // 4
    return min(reward, 10)


def get_required_dps(round_num):
    """해당 라운드 생존에 필요한 대략적 DPS (적 오버플로우 방지 기준)"""
    is_boss = (round_num % GAME_CONFIG['bossInterval'] == 0)
    if is_boss:
        boss_hp = BOSS_DATA.get(round_num, {}).get('hp', 1000)
        return boss_hp / float(GAME_CONFIG['roundTime'])
    else:
        enemy_hp = get_normal_enemy_hp(round_num)
        spawn_dur = max(GAME_CONFIG['roundTime'] - 5, 1)
        num_enemies = spawn_dur / GAME_CONFIG['spawnInterval']
        total_hp = enemy_hp * num_enemies
        return total_hp / float(GAME_CONFIG['roundTime'])
