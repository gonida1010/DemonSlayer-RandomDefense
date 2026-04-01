# -*- coding: utf-8 -*-
"""
rewards_ppo.py - MaskablePPO 전용 리워드 설정

PPO 특성:
  - On-policy → 안정적이지만 샘플 효율 낮음
  - 큰 보상 신호에 잘 반응
  - 엔트로피 보너스로 탐색 유도 가능 → 보상은 명확하게

핵심 원칙:
  - 배치(PLACE) ≈ 조합(COMBINE) 수준의 보상 → 만들기만 하고 안 놓는 문제 해결
  - 그리드에 유닛 방치 시 매 틱 패널티 → 배치 유도
  - 조합은 "결과 유닛의 DPS 기여 잠재력"으로 보상
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
SUMMON_REWARD = 0.1


# 배치 (PLACE) - 핵심 보상: 조합과 동급으로 상향
def place_reward(tier, unit_dps=None, range_efficiency=1.0, boss_alive=False, enemy_ratio=0.0):
    """배치 보상.
    일반 라운드에서는 빠른 전력 투입을 보상하고,
    보스전에서는 사거리 기반 실효 DPS가 낮은 배치를 감점한다.
    """
    reward = 0.14 * tier * tier + 0.22 * tier
    if tier >= 5:
        reward += 1.0 + (tier - 5) * 1.0

    if unit_dps is not None:
        reward += min(unit_dps / 20000.0, 1.0) * 0.18

    if boss_alive:
        efficiency_gap = range_efficiency - 0.9
        dps_weight = 1.0 + min((unit_dps or 0.0) / 30000.0, 1.0)
        if efficiency_gap >= 0:
            reward += efficiency_gap * 1.1 * dps_weight
        else:
            reward += efficiency_gap * 2.2 * dps_weight
    else:
        reward += min(enemy_ratio, 1.0) * 0.1

    return reward


# 판매 (SELL)
def sell_penalty(tier):
    """판매: 막힌 저티어 정리 외에는 매우 불리하도록 설정.
    저티어 정리 여지는 남기되, 고티어/조합 재료 판매를 강하게 억제한다.
    """
    return -(0.04 + 0.06 * tier + 0.03 * tier * tier)


# 조합 (COMBINE)
def combine_reward(result_tier, consecutive_combines=0):
    """조합: 시너지 루트와 최고 티어 진입을 강하게 장려.
    연쇄 조합을 보상하되, 조합만 반복하는 편향을 막기 위해 보너스는 완만히 상한 처리한다.
    """
    base = 0.18 * result_tier * result_tier + 0.08 * result_tier

    tier_bonus = 0.0
    if result_tier >= 4:
        tier_bonus += 0.35 * (result_tier - 3)
    if result_tier >= 5:
        tier_bonus += 1.4 + (result_tier - 5) * 1.4

    chain_bonus = min(max(consecutive_combines - 1, 0), 3) * 0.25
    return base + tier_bonus + chain_bonus


# =================================================================
# 시뮬레이션 보상 (Simulation Rewards)
# =================================================================

# 적 처치
ENEMY_KILL_REWARD = 0.02
BOSS_KILL_REWARD = 18.0

# 위험도 패널티
def danger_penalty(enemy_ratio, dt):
    """적 누적 비율에 따른 연속 패널티"""
    return -0.05 * enemy_ratio * enemy_ratio * dt


# 그리드 방치 패널티 (매 틱마다)
def grid_idle_penalty(grid_unit_tiers, dt):
    """그리드에 유닛을 방치하면 매 틱 패널티.
    높은 티어일수록 페널티가 큼 (DPS 손실이 크므로).
    grid_unit_tiers: 그리드에 있는 유닛들의 티어 리스트
    """
    if not grid_unit_tiers:
        return 0.0
    penalty = 0.0
    for tier in grid_unit_tiers:
        penalty += 0.02 * tier * tier  # T1=-0.02, T3=-0.18, T5=-0.50, T6=-0.72
    return -penalty * dt


# 라운드 생존
def round_survival_reward(round_num):
    """라운드 생존 보상 (무한 모드: 후반 가중치)"""
    base = 1.5 + round_num / 20.0
    if round_num % 10 == 0:
        base += 2.0
    if round_num > 90:
        base += (round_num - 90) * 0.1
    return base


# 게임 오버 / 보스 미처치
GAME_OVER_PENALTY = -100.0
BOSS_TIMEOUT_PENALTY = -3.0

# 유효하지 않은 행동
INVALID_ACTION_PENALTY = -0.1

# 히든 조합 배율
HIDDEN_COMBINE_MULTIPLIER = 1.5

# 보스 집중 공격
FOCUS_BOSS_REWARD = 0.5

# 보스 카이팅 (전체 유닛 보스 위치로 재배치)
KITE_REWARD = 1.0


def speed_state_reward(game_speed, enemy_ratio, boss_alive, time_remaining, dt):
    """현재 배속 유지에 대한 shaping.
    일반 라운드는 5x 고정 운영을 선호하고,
    보스전에서만 1x~2x 감속을 통해 반응성을 확보하도록 유도.
    """
    if boss_alive:
        if game_speed <= 2.0:
            return 0.08 * dt
        if game_speed == 3.0:
            return -0.005 * dt
        if game_speed >= 5.0:
            return -0.08 * dt
        return -0.03 * dt

    if game_speed >= 5.0:
        return 0.02 * dt if (enemy_ratio <= 0.45 and time_remaining > 5.0) else 0.01 * dt
    if game_speed >= 3.0:
        return -0.005 * dt
    return -0.03 * dt


def boss_damage_progress_reward(hp_drop_ratio, round_num):
    """보스 HP 감소에 따른 중간 보상.
    hp_drop_ratio: 이번 틱에서 줄어든 HP 비율 (0~1)
    """
    base = hp_drop_ratio * 10.0
    if round_num > 50:
        base *= 1.0 + (round_num - 50) * 0.02
    return base
