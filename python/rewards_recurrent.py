# -*- coding: utf-8 -*-
"""
rewards_recurrent.py - RecurrentPPO 전용 리워드 설정

RecurrentPPO 특성:
  - LSTM 기반 → 과거 상태 기억 가능
  - 연속적인 행동 패턴 학습에 강점 → 시퀀스 보상 추가
  - 장기 전략 학습 가능 → 장기 보상 비중 높임
  - 조합 → 배치 → 조합 연쇄 패턴 인식 가능
"""


# =================================================================
# 행동별 보상 (Action Rewards)
# =================================================================

# 대기 (WAIT)
def wait_penalty(summons_possible, empty_slots):
    """소환 가능한데 대기하면 페널티 (LSTM은 시간 단계를 기억)"""
    if summons_possible > 0 and empty_slots > 0:
        return -0.015 * min(summons_possible, empty_slots)
    return 0.0


# 소환 (SUMMON)
SUMMON_REWARD = 0.03


# 배치 (PLACE)
def place_reward(tier, unit_dps=None, range_efficiency=1.0, boss_alive=False, enemy_ratio=0.0):
    """배치: 티어 기반 기본 보상에 전황 문맥을 반영.
    LSTM이 보스전/혼전 타이밍 차이를 시퀀스로 학습할 수 있게
    즉시 전력 기여와 배치 효율을 약하게 가산한다.
    """
    reward = 0.08 * tier + 0.02 * tier * tier

    if unit_dps is not None:
        reward += min(unit_dps / 25000.0, 1.0) * 0.08

    if boss_alive:
        reward += (range_efficiency - 0.85) * (0.45 + min((unit_dps or 0.0) / 40000.0, 0.35))
    else:
        reward += min(enemy_ratio, 1.0) * 0.06

    return reward  # T4~T6 기본 보상은 유지하고 상황 가중치만 추가


# 판매 (SELL)
def sell_penalty(tier):
    """판매: 보상으로 유도하지 않음"""
    return 0.0


# 조합 (COMBINE) - RecurrentPPO의 핵심: 연쇄 조합 보너스
def combine_reward(result_tier, consecutive_combines=0):
    """조합: tier² + 연쇄 조합 보너스
    LSTM이 연속 조합 패턴(소환→소환→조합→조합)을 학습하도록 유도
    consecutive_combines: 최근 5스텝 내 연속 조합 횟수
    """
    base = 0.16 * result_tier * result_tier
    # 연쇄 조합 보너스: 연속으로 조합할수록 추가 보상
    chain_bonus = 0.12 * consecutive_combines * result_tier
    return base + chain_bonus


# =================================================================
# 시뮬레이션 보상 (Simulation Rewards)
# =================================================================

# 적 처치
ENEMY_KILL_REWARD = 0.02
BOSS_KILL_REWARD = 20.0  # 장기 생존 목표 강조

# 위험도 패널티
def danger_penalty(enemy_ratio, dt):
    """적 누적 패널티 (LSTM이 위험 상승 추세를 감지하도록 제곱)"""
    return -0.06 * enemy_ratio * enemy_ratio * dt


# 라운드 생존
def round_survival_reward(round_num):
    """라운드 생존 보상 (LSTM: 장기 생존에 높은 가치)"""
    base = 1.8 + round_num / 18.0
    if round_num % 10 == 0:
        base += 2.5
    if round_num > 90:
        base += (round_num - 90) * 0.15  # 90 이후 강한 보상 증가
    return base


# 전략 보너스 (LSTM 전용)
def field_composition_bonus(tier_counts):
    """필드 유닛 구성 보너스 (다양성 + 고티어 비율)
    LSTM이 필드 구성 전략을 학습할 수 있도록 추가 보상
    """
    bonus = 0.0
    unique_tiers = len([t for t, c in tier_counts.items() if c > 0])
    bonus += unique_tiers * 0.02  # 다양성 보너스

    # 고티어 비율 보너스
    high_tier_count = sum(c for t, c in tier_counts.items() if t >= 4)
    total = sum(tier_counts.values())
    if total > 0:
        bonus += (high_tier_count / total) * 0.1

    return bonus


# 게임 오버 / 보스 미처치
GAME_OVER_PENALTY = -50.0
BOSS_TIMEOUT_PENALTY = -10.0

# 유효하지 않은 행동
INVALID_ACTION_PENALTY = -0.01

# 히든 조합 배율
HIDDEN_COMBINE_MULTIPLIER = 1.5

# 보스 집중 공격 (LSTM이 보스전 타이밍에 집중 패턴 학습)
FOCUS_BOSS_REWARD = 0.6

# 보스 카이팅 (LSTM: 장기 보스전 전략 학습)
KITE_REWARD = 1.2


def speed_state_reward(game_speed, enemy_ratio, boss_alive, time_remaining, dt):
    if boss_alive or enemy_ratio >= 0.55:
        if game_speed <= 2.0:
            return 0.1 * dt
        if game_speed >= 5.0:
            return -0.18 * dt
        return -0.05 * dt

    if enemy_ratio <= 0.2 and time_remaining > 15:
        if game_speed >= 5.0:
            return 0.07 * dt
        if game_speed >= 3.0:
            return 0.04 * dt
        return -0.03 * dt

    if enemy_ratio <= 0.35:
        if game_speed >= 3.0:
            return 0.04 * dt
        if game_speed == 2.0:
            return 0.015 * dt
        return -0.02 * dt

    return 0.03 * dt if game_speed == 2.0 else (-0.025 * dt if game_speed >= 5.0 else 0.0)


def boss_damage_progress_reward(hp_drop_ratio, round_num):
    """보스 HP 감소 진행 보상 (LSTM: 장기 보스전 진행 추적)"""
    base = hp_drop_ratio * 12.0
    if round_num > 50:
        base *= 1.0 + (round_num - 50) * 0.025
    return base
