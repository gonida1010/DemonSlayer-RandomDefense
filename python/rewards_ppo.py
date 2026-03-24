# -*- coding: utf-8 -*-
"""
rewards_ppo.py - MaskablePPO 전용 리워드 설정

PPO 특성:
  - On-policy → 안정적이지만 샘플 효율 낮음
  - 큰 보상 신호에 잘 반응 → 조합 보상을 지배적으로 설정
  - 엔트로피 보너스로 탐색 유도 가능 → 보상은 명확하게
"""


# =================================================================
# 행동별 보상 (Action Rewards)
# =================================================================

# 대기 (WAIT)
def wait_penalty(summons_possible, empty_slots):
    """소환 가능한데 대기하면 페널티"""
    if summons_possible > 0 and empty_slots > 0:
        return -0.02 * min(summons_possible, empty_slots)
    return 0.0


# 소환 (SUMMON)
SUMMON_REWARD = 0.04  # 행동 보상 비중 축소


# 배치 (PLACE)
def place_reward(tier):
    """배치: 낮은 보상 (조합 > 배치 유도)"""
    return 0.1 * tier  # T1=0.1 ~ T6=0.6


# 판매 (SELL)
def sell_penalty(tier):
    """판매: 전략적으로만 사용, 별도 보상 없음"""
    return 0.0


# 조합 (COMBINE) - PPO의 핵심 보상
def combine_reward(result_tier):
    """조합: 생존 보상을 압도하지 않도록 축소
    T2=0.72, T3=1.62, T4=2.88, T5=4.50, T6=6.48
    """
    return 0.18 * result_tier * result_tier


# =================================================================
# 시뮬레이션 보상 (Simulation Rewards)
# =================================================================

# 적 처치
ENEMY_KILL_REWARD = 0.02      # 일반 적 처치
BOSS_KILL_REWARD = 18.0       # 생존 핵심 목표 강화

# 위험도 패널티
def danger_penalty(enemy_ratio, dt):
    """적 누적 비율에 따른 연속 패널티"""
    return -0.05 * enemy_ratio * enemy_ratio * dt


# 라운드 생존
def round_survival_reward(round_num):
    """라운드 생존 보상 (무한 모드: 후반 가중치)"""
    base = 1.5 + round_num / 20.0
    if round_num % 10 == 0:
        base += 2.0
    if round_num > 90:
        base += (round_num - 90) * 0.1  # 90라운드 이후 추가 보상
    return base


# 게임 오버 / 보스 미처치
GAME_OVER_PENALTY = -10.0
BOSS_TIMEOUT_PENALTY = -10.0

# 유효하지 않은 행동
INVALID_ACTION_PENALTY = -0.01

# 히든 조합 배율
HIDDEN_COMBINE_MULTIPLIER = 1.5
