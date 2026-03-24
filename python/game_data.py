"""
game_data.py - 귀멸의 칼날 랜덤 디펜스 게임 데이터
data.hard.js에서 추출한 지옥 모드(Hard) 데이터 - 무한 라운드
"""

# =====================================================================
# 게임 설정 (Hard Mode - 무한 라운드)
# =====================================================================
GAME_CONFIG = {
    'initialGold': 1200,
    'maxEnemies': 60,
    'roundTime': 60,
    'spawnInterval': 1.0,        # 하드: 1.0초 (노멀: 1.2초)
    'unitSummonCost': 150,
    'bossInterval': 10,          # 10라운드마다 보스
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
    'muichiro_transparent':{'tier': 6, 'dmg': 82500, 'speed': 1500, 'range': 260},
    'koku':                {'tier': 6, 'dmg': 54400, 'speed': 850,  'range': 240},
    'tanjiro_king':        {'tier': 6, 'dmg': 29250, 'speed': 450,  'range': 160},
    'twin_destiny':        {'tier': 6, 'dmg': 60000, 'speed': 400,  'range': 220},
    'rengoku_legend':      {'tier': 6, 'dmg': 56700, 'speed': 900,  'range': 210},
    'nezuko_sun':          {'tier': 6, 'dmg': 37200, 'speed': 600,  'range': 190},
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
    {'a': 'obanai',        'b': 'muichiro',       'result': 'yoriichi_zero',  'hidden': True},
    {'a': 'yoriichi_zero', 'b': 'sanemi_mark',    'result': 'koku',           'hidden': True},
    {'a': 'giyu_mark',     'b': 'nezuko_awake',   'result': 'tanjiro_king',   'hidden': True},
    {'a': 'yoriichi',      'b': 'koku',           'result': 'twin_destiny',   'hidden': True},
    {'a': 'rengoku',       'b': 'kanae',          'result': 'rengoku_smile',  'hidden': True},
    {'a': 'rengoku_smile', 'b': 'tanjiro_sun',    'result': 'rengoku_legend', 'hidden': True},
    {'a': 'nezuko_awake',  'b': 'tamayo_yushiro', 'result': 'nezuko_sun',     'hidden': True},
]

NUM_RECIPES = len(RECIPES)  # 54

# 히든 레시피 인덱스 집합
HIDDEN_RECIPE_INDICES = frozenset(
    i for i, r in enumerate(RECIPES) if r.get('hidden', False)
)

# =====================================================================
# 보스 데이터 (Hard Mode - 2~3배 강화)
# =====================================================================
BOSS_DATA = {
    10: {'name': '하현5 루이',       'hp': 100000},
    20: {'name': '하현1 엔무',       'hp': 200000},
    30: {'name': '상현6 다키',       'hp': 500000},
    40: {'name': '상현5 굣코',       'hp': 1000000},
    50: {'name': '상현4 한텐구',     'hp': 3000000},
    60: {'name': '상현3 아카자',     'hp': 10000000},
    70: {'name': '상현2 도우마',     'hp': 20000000},
    80: {'name': '상현1 코쿠시보',   'hp': 30000000},
    90: {'name': '키부츠지 무잔',    'hp': 60000000},
}

# 90라운드 이후 보스: 무잔 재등장 + 라운드 지수 스케일링
def get_boss_hp(round_num):
    """보스 체력 계산 (무한 모드) — 90 이후 60M × 1.03^(round-90)"""
    if round_num in BOSS_DATA:
        return BOSS_DATA[round_num]['hp']
    if round_num > 90 and round_num % GAME_CONFIG['bossInterval'] == 0:
        base_hp = BOSS_DATA[90]['hp']
        return int(base_hp * (1.03 ** (round_num - 90)))
    return 0

# =====================================================================
# 행동 공간 정의
# =====================================================================
# 0: WAIT
# 1: SUMMON
# 2 ~ 58: PLACE(unit_keys[i-2])
# 59 ~ 115: SELL(unit_keys[i-59])
# 116 ~ 169: COMBINE(recipes[i-116])
# 170: PLACE_BEST_DPS
# 171: COMBINE_BEST_TIER
# 172: SUMMON_UNTIL_FULL
OBS_STRATEGY_DIM = 6
OBS_UNIT_COUNT_START = 10 + OBS_STRATEGY_DIM
OBS_DIM = OBS_UNIT_COUNT_START + NUM_UNIT_TYPES  # 73

# =====================================================================
# 시너지 (Synergy) - T6 유닛 조합 보너스
# 3명이 필드에 모두 배치되면 해당 유닛 공격력 1.2배
# 모든 T6 유닛이 최소 2개 시너지에 포함
# =====================================================================
SYNERGIES = [
    # 카마도 가족 (Kamado Family)
    {'name': '카마도 혈통', 'units': ['tanjiro_final', 'nezuko_sun', 'tanjiro_king']},
    # 동기조 (Same Generation)
    {'name': '동기조의 유대', 'units': ['tanjiro_final', 'inosuke_king', 'zenitsu_7th']},
    # 코쿠시보전 (Upper Moon 1 Battle)
    {'name': '상현1 토벌대', 'units': ['gyomei_mark', 'sanemi_wind_god', 'muichiro_transparent']},
    # 전설의 쌍둥이 (Legendary Twins)
    {'name': '쌍둥이의 인연', 'units': ['yoriichi', 'koku', 'twin_destiny']},
    # 탄지로의 스승들 (Tanjiro's Masters)
    {'name': '귀살대 핵심', 'units': ['tanjiro_final', 'giyu_calm', 'rengoku_legend']},
    # 주 합동 작전 (Hashira Alliance)
    {'name': '주 연합전선', 'units': ['giyu_calm', 'sanemi_wind_god', 'love_snake_couple']},
    # 불꽃의 의지 (Will of Flame)
    {'name': '불꽃의 의지', 'units': ['rengoku_legend', 'nezuko_sun', 'love_snake_couple']},
    # 상현1전 (Dark Moon)
    {'name': '달의 호흡', 'units': ['koku', 'muichiro_transparent', 'gyomei_mark']},
    # 귀의 왕 계보 (Demon King Lineage)
    {'name': '귀의 왕 계보', 'units': ['twin_destiny', 'yoriichi', 'tanjiro_king']},
    # 수주의 후예 (Water Legacy)
    {'name': '물의 계보', 'units': ['giyu_calm', 'inosuke_king', 'zenitsu_7th']},
]

SYNERGY_DPS_MULTIPLIER = 1.2

ACTION_WAIT = 0
ACTION_SUMMON = 1
ACTION_PLACE_START = 2
ACTION_PLACE_END = 2 + NUM_UNIT_TYPES - 1            # 58
ACTION_SELL_START = 2 + NUM_UNIT_TYPES                # 59
ACTION_SELL_END = 2 + 2 * NUM_UNIT_TYPES - 1         # 115
ACTION_COMBINE_START = 2 + 2 * NUM_UNIT_TYPES         # 116
ACTION_COMBINE_END = ACTION_COMBINE_START + NUM_RECIPES - 1  # 169
ACTION_MACRO_PLACE_BEST = ACTION_COMBINE_END + 1             # 170
ACTION_MACRO_COMBINE_BEST = ACTION_MACRO_PLACE_BEST + 1      # 171
ACTION_MACRO_SUMMON_ALL = ACTION_MACRO_COMBINE_BEST + 1      # 172
NUM_ACTIONS = ACTION_MACRO_SUMMON_ALL + 1                    # 173

# 소환 확률 (JS 코드와 동일)
SUMMON_PROBS = {1: 0.70, 2: 0.20, 3: 0.10}


def get_normal_enemy_hp(round_num):
    """일반 적 체력 계산 (Hard Mode - game.js spawnEnemy 공식)
    하드 모드: 기본 공식 + round² × 150 + 전체 1.5배 + 90 이후 복리
    """
    base_hp = round_num * 200
    if round_num > 10:
        base_hp += round_num * round_num * 30
    if round_num >= 20:
        base_hp = base_hp * 1.5
    # 하드 모드 추가 스케일링
    if round_num > 1:
        base_hp += round_num * round_num * 150
    base_hp = base_hp * 1.5
    # 90라운드 이후 지수적 증가
    if round_num > 90:
        base_hp = base_hp * (1.03 ** (round_num - 90))
    return int(base_hp)


def get_kill_gold(round_num):
    """적 처치 시 골드 보상 (Hard Mode - 상향, 90라운드 이후 5라운드당 1.1배)"""
    reward = 7 + round_num // 4
    reward = min(reward, 20)
    if round_num > 90:
        scale_ticks = (round_num - 90) // 5
        reward = int(reward * (1.1 ** scale_ticks))
    return reward


def get_boss_kill_gold(round_num):
    """보스 처치 시 골드 보상 (90라운드 이후 5라운드당 1.1배)"""
    reward = 1000
    if round_num > 90:
        scale_ticks = (round_num - 90) // 5
        reward = int(reward * (1.1 ** scale_ticks))
    return reward


def get_required_dps(round_num):
    """해당 라운드 생존에 필요한 대략적 DPS (Hard Mode)"""
    is_boss = (round_num % GAME_CONFIG['bossInterval'] == 0)
    if is_boss:
        boss_hp = get_boss_hp(round_num)
        if boss_hp == 0:
            boss_hp = 1000
        return boss_hp / float(GAME_CONFIG['roundTime'])
    else:
        enemy_hp = get_normal_enemy_hp(round_num)
        spawn_dur = max(GAME_CONFIG['roundTime'] - 5, 1)
        num_enemies = spawn_dur / GAME_CONFIG['spawnInterval']
        total_hp = enemy_hp * num_enemies
        return total_hp / float(GAME_CONFIG['roundTime'])
