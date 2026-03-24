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
SUMMON_REWARD = 0.04


# 배치 (PLACE) - 핵심 보상: 조합과 동급으로 상향
def place_reward(tier):
    """배치: 조합과 비슷한 수준의 강한 보상
    유닛을 필드에 놓아야 DPS가 올라가고 생존할 수 있음.
    T1=0.5, T2=1.2, T3=2.1, T4=3.2, T5=6.5, T6=10.0
    """
    base = 0.2 * tier * tier + 0.3 * tier
    if tier >= 5:
        base += 2.0 + (tier - 5) * 1.5
    return base


# 판매 (SELL)
def sell_penalty(tier):
    """판매: 전략적으로만 사용, 별도 보상 없음"""
    return 0.0


# 조합 (COMBINE)
def combine_reward(result_tier):
    """조합: 배치보다 약간 낮은 보상 (조합만 하고 배치 안 하는 문제 방지)
    T2=0.72, T3=1.62, T4=2.88, T5=4.50, T6=6.48
    조합은 중요하지만, 배치 없이는 DPS 기여 불가 → 배치보다 낮게 설정
    """
    base = 0.18 * result_tier * result_tier
    high_tier_bonus = 0.0
    if result_tier >= 5:
        high_tier_bonus += 2.0 + (result_tier - 5) * 2.0
    return base + high_tier_bonus


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
GAME_OVER_PENALTY = -10.0
BOSS_TIMEOUT_PENALTY = -10.0

# 유효하지 않은 행동
INVALID_ACTION_PENALTY = -0.01

# 히든 조합 배율
HIDDEN_COMBINE_MULTIPLIER = 1.5

# 보스 집중 공격
FOCUS_BOSS_REWARD = 0.5


def boss_damage_progress_reward(hp_drop_ratio, round_num):
    """보스 HP 감소에 따른 중간 보상.
    hp_drop_ratio: 이번 틱에서 줄어든 HP 비율 (0~1)
    """
    base = hp_drop_ratio * 10.0
    if round_num > 50:
        base *= 1.0 + (round_num - 50) * 0.02
    return base
