# -*- coding: utf-8 -*-
"""
rewards_dqn.py - DQN 전용 리워드 설정

DQN 특성:
  - Off-policy → 경험 리플레이 활용, 샘플 효율 높음
  - 작고 밀집된(dense) 보상에 잘 반응 → 보상을 세분화
  - Q-value 과대평가 경향 → 보상 스케일을 작게 유지
  - 탐색은 epsilon-greedy로 수행 → 보상은 일관성 있게
"""


# =================================================================
# 행동별 보상 (Action Rewards)
# =================================================================

# 대기 (WAIT)
def wait_penalty(summons_possible, empty_slots):
    """소환 가능한데 대기하면 더 세밀한 페널티"""
    if summons_possible > 0 and empty_slots > 0:
        return -0.03 * min(summons_possible, empty_slots)
    return -0.005  # DQN은 항상 약간의 시간 비용 부여


# 소환 (SUMMON)
SUMMON_REWARD = 0.02  # 행동 보상 비중 축소


# 배치 (PLACE)
def place_reward(tier):
    """배치: DPS 즉시 기여 보상 (DQN에서 즉시 결과 중시)"""
    return 0.15 * tier  # T1=0.15 ~ T6=0.90


# 판매 (SELL)
def sell_penalty(tier):
    """판매: 보상 없이 중립 처리"""
    return 0.0


# 조합 (COMBINE)
def combine_reward(result_tier):
    """조합: 선형 + 보너스 (DQN에 맞는 더 균일한 보상 분포)
    T2=0.6, T3=1.2, T4=2.3, T5=3.9, T6=5.5
    """
    base = result_tier * 0.3
    bonus = max(0, (result_tier - 3)) * 0.8
    return base + bonus


# =================================================================
# 시뮬레이션 보상 (Simulation Rewards)
# =================================================================

# 적 처치
ENEMY_KILL_REWARD = 0.03      # 일반 적 (DQN: 즉시 보상 중요)
BOSS_KILL_REWARD = 12.0       # 생존 목표 강화

# 위험도 패널티
def danger_penalty(enemy_ratio, dt):
    """적 누적 비율에 따른 선형 패널티 (DQN은 선형이 학습 안정적)"""
    return -0.08 * enemy_ratio * dt


# 라운드 생존
def round_survival_reward(round_num):
    """라운드 생존 보상 (DQN: 단계적 보너스)"""
    base = 1.0 + round_num / 30.0
    # 10라운드 단위 마일스톤 보너스
    if round_num % 10 == 0:
        base += 2.5
    if round_num > 90:
        base += (round_num - 90) * 0.05
    return base


# 게임 오버 / 보스 미처치
GAME_OVER_PENALTY = -10.0
BOSS_TIMEOUT_PENALTY = -10.0

# 유효하지 않은 행동
INVALID_ACTION_PENALTY = -0.02  # DQN에서 무효 행동 더 강하게 패널티

# 히든 조합 배율
HIDDEN_COMBINE_MULTIPLIER = 1.5
