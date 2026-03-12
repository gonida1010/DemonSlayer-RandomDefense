"""
game_env.py - 귀멸의 칼날 랜덤 디펜스 강화학습 환경 v4
Gymnasium 호환 환경 (MaskablePPO 지원)

v4 핵심 변경:
- 관측 67차원 복원 (개별 유닛 카운트 → 조합 가치 평가 핵심)
- 조합 = 지배적 보상 (0.5 × tier²: T4=8.0, T5=12.5, T6=18.0)
- 배치/소환 = 최소 보상 (배치보다 조합 동기 부여)
- 위험도 연속 패널티 + 적 처치 미세 보상 유지
"""
import gymnasium as gym
import numpy as np
from gymnasium import spaces

from game_data import (
    GAME_CONFIG, UNIT_DATA, UNIT_KEYS, UNIT_KEY_TO_IDX,
    RECIPES, NUM_RECIPES, BOSS_DATA, TIER_POOL, SUMMON_PROBS,
    NUM_ACTIONS, OBS_DIM, NUM_UNIT_TYPES,
    ACTION_WAIT, ACTION_SUMMON,
    ACTION_PLACE_START, ACTION_SELL_START, ACTION_COMBINE_START,
    get_normal_enemy_hp, get_kill_gold,
)


class DemonSlayerEnv(gym.Env):
    """
    귀멸의 칼날 랜덤 디펜스 - 강화학습 환경 v4

    관측 공간 (67차원):
      [0]  round / 90
      [1]  gold / 10000
      [2]  time_remaining / 60
      [3]  enemy_count / max_enemies
      [4]  boss_alive (0 or 1)
      [5]  boss_hp_ratio
      [6]  field_dps / 500000
      [7]  field_unit_count / 30
      [8]  empty_grid_slots / 36
      [9]  valid_combine_count / 54
      [10..66] 유닛 타입별 보유 수 (그리드+필드) / 10

    행동 공간 (170개 이산 행동):
      0: 대기 (WAIT)
      1: 소환 (SUMMON)
      2~58:  배치 (PLACE unit_type)
      59~115: 판매 (SELL unit_type)
      116~169: 조합 (COMBINE recipe)
    """

    metadata = {'render_modes': []}

    # 에이전트 결정 간격 (초) - 이 시간만큼 게임이 진행됨
    STEP_DURATION = 2.0  # 실제 게임에서의 빠른 판단을 반영
    TICK_SIZE = 0.5  # 시뮬레이션 틱 크기 (초)
    GRID_SIZE = 36   # 6x6 그리드
    COMBAT_EFFICIENCY = 0.75  # 투사체 비행/사거리 손실 반영 (75%)

    def __init__(self, render_mode=None):
        super().__init__()
        self.action_space = spaces.Discrete(NUM_ACTIONS)
        self.observation_space = spaces.Box(
            low=0.0, high=1.0, shape=(OBS_DIM,), dtype=np.float32
        )
        self.render_mode = render_mode

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)

        self.round = 1
        self.gold = GAME_CONFIG['initialGold']
        self.time_remaining = float(GAME_CONFIG['roundTime'])

        # 그리드: 36칸, None = 빈칸, str = unit_key
        self.grid = [None] * self.GRID_SIZE
        # 필드: 배치된 유닛 키 리스트
        self.field_units = []
        # 적 리스트: [{'hp': int, 'max_hp': int, 'is_boss': bool}]
        self.enemies = []

        self.game_over = False
        self.game_cleared = False
        self.boss_spawned = False
        self.spawn_acc = 0.0     # 스폰 누적 시간
        self.total_steps = 0

        # 캐시
        self._field_dps_cache = 0.0
        self._field_boss_dps_cache = 0.0
        self._update_field_dps()

        return self._get_obs(), {}

    # =================================================================
    # Gymnasium 인터페이스
    # =================================================================

    def step(self, action):
        assert not (self.game_over or self.game_cleared), "Episode ended"
        self.total_steps += 1

        # 1. 행동 실행
        action_reward = self._execute_action(int(action))

        # 2. 게임 시뮬레이션 (STEP_DURATION 초)
        sim_reward = self._simulate(self.STEP_DURATION)

        reward = action_reward + sim_reward
        terminated = self.game_over or self.game_cleared
        truncated = False

        info = {
            'round': self.round,
            'gold': self.gold,
            'field_dps': self._field_dps_cache,
            'enemy_count': len(self.enemies),
            'game_cleared': self.game_cleared,
        }

        return self._get_obs(), reward, terminated, truncated, info

    def action_masks(self):
        """MaskablePPO용 유효 행동 마스크 반환"""
        mask = np.zeros(NUM_ACTIONS, dtype=bool)

        # WAIT: 항상 유효
        mask[ACTION_WAIT] = True

        # SUMMON: 골드 충분 + 빈칸 존재
        has_empty = None in self.grid
        if self.gold >= GAME_CONFIG['unitSummonCost'] and has_empty:
            mask[ACTION_SUMMON] = True

        # PLACE / SELL: 그리드에 해당 유닛이 있으면 유효
        grid_counts = {}
        for slot in self.grid:
            if slot is not None:
                grid_counts[slot] = grid_counts.get(slot, 0) + 1

        for key, count in grid_counts.items():
            idx = UNIT_KEY_TO_IDX[key]
            mask[ACTION_PLACE_START + idx] = True   # PLACE
            mask[ACTION_SELL_START + idx] = True     # SELL

        # COMBINE: 두 재료가 모두 그리드에 있어야 함
        for i, recipe in enumerate(RECIPES):
            a, b = recipe['a'], recipe['b']
            if a == b:
                if grid_counts.get(a, 0) >= 2:
                    mask[ACTION_COMBINE_START + i] = True
            else:
                if grid_counts.get(a, 0) >= 1 and grid_counts.get(b, 0) >= 1:
                    mask[ACTION_COMBINE_START + i] = True

        return mask

    # =================================================================
    # 관측 생성 (v4: 67차원 개별 유닛 카운트 복원)
    # =================================================================

    def _get_obs(self):
        obs = np.zeros(OBS_DIM, dtype=np.float32)

        obs[0] = self.round / 90.0
        obs[1] = min(self.gold / 10000.0, 1.0)
        obs[2] = max(self.time_remaining, 0.0) / 60.0
        obs[3] = min(len(self.enemies) / GAME_CONFIG['maxEnemies'], 1.0)

        # 보스 정보
        boss = None
        for e in self.enemies:
            if e['is_boss']:
                boss = e
                break
        obs[4] = 1.0 if boss else 0.0
        obs[5] = (boss['hp'] / boss['max_hp']) if boss else 0.0

        obs[6] = min(self._field_dps_cache / 500000.0, 1.0)
        obs[7] = min(len(self.field_units) / 30.0, 1.0)
        obs[8] = sum(1 for s in self.grid if s is None) / 36.0

        # 유효 조합 수
        valid_combines = sum(1 for m in self.action_masks()[ACTION_COMBINE_START:]
                            if m)
        obs[9] = min(valid_combines / 54.0, 1.0)

        # 유닛 타입별 보유 수 (그리드 + 필드)
        counts = [0] * NUM_UNIT_TYPES
        for slot in self.grid:
            if slot is not None:
                counts[UNIT_KEY_TO_IDX[slot]] += 1
        for key in self.field_units:
            counts[UNIT_KEY_TO_IDX[key]] += 1
        for i in range(NUM_UNIT_TYPES):
            obs[10 + i] = min(counts[i] / 10.0, 1.0)

        return obs

    # =================================================================
    # 행동 실행 (v4: 조합 지배적 보상)
    # =================================================================

    def _execute_action(self, action):
        if action == ACTION_WAIT:
            return self._wait_penalty()

        if action == ACTION_SUMMON:
            return self._summon()

        if ACTION_PLACE_START <= action <= ACTION_PLACE_START + NUM_UNIT_TYPES - 1:
            unit_key = UNIT_KEYS[action - ACTION_PLACE_START]
            return self._place(unit_key)

        if ACTION_SELL_START <= action <= ACTION_SELL_START + NUM_UNIT_TYPES - 1:
            unit_key = UNIT_KEYS[action - ACTION_SELL_START]
            return self._sell(unit_key)

        if ACTION_COMBINE_START <= action <= ACTION_COMBINE_START + NUM_RECIPES - 1:
            recipe_idx = action - ACTION_COMBINE_START
            return self._combine(recipe_idx)

        return -0.01

    def _wait_penalty(self):
        """WAIT 패널티: 소환 가능한데 대기하면 가벼운 패널티"""
        cost = GAME_CONFIG['unitSummonCost']
        summons_possible = self.gold // cost
        has_empty = sum(1 for s in self.grid if s is None)

        if summons_possible > 0 and has_empty > 0:
            return -0.02 * min(summons_possible, has_empty)
        return 0.0

    def _summon(self):
        """유닛 소환: 재료 확보를 격려 (조합의 전제조건)"""
        cost = GAME_CONFIG['unitSummonCost']
        if self.gold < cost:
            return -0.01

        empty_indices = [i for i, s in enumerate(self.grid) if s is None]
        if not empty_indices:
            return -0.01

        self.gold -= cost

        # 확률에 따라 티어 결정 (JS와 동일)
        roll = self.np_random.integers(1, 101)
        if roll <= 10:
            tier = 3
        elif roll <= 30:
            tier = 2
        else:
            tier = 1

        # 해당 티어에서 랜덤 유닛 선택
        pool = TIER_POOL[tier]
        unit_key = pool[self.np_random.integers(0, len(pool))]

        # 랜덤 빈칸에 배치
        slot = empty_indices[self.np_random.integers(0, len(empty_indices))]
        self.grid[slot] = unit_key

        return 0.15  # 조합 재료 확보 유도

    def _place(self, unit_key):
        """배치: 의도적으로 낮은 보상 (조합 > 즉시 배치 유도)"""
        if unit_key not in self.grid:
            return -0.01

        idx = self.grid.index(unit_key)
        self.grid[idx] = None
        self.field_units.append(unit_key)
        self._update_field_dps()

        tier = UNIT_DATA[unit_key]['tier']
        # T1=0.1, T2=0.2, ..., T6=0.6 (조합 보상 대비 매우 작음)
        return 0.1 * tier

    def _sell(self, unit_key):
        """판매: 티어 비례 선형 패널티"""
        if unit_key not in self.grid:
            return -0.01

        idx = self.grid.index(unit_key)
        self.grid[idx] = None
        tier = UNIT_DATA[unit_key]['tier']
        sell_price = tier * 50
        self.gold += sell_price
        return -0.1 * tier  # T1:-0.1 ~ T6:-0.6

    def _combine(self, recipe_idx):
        """조합: tier² 스케일 (지배적 보상 신호)"""
        if recipe_idx < 0 or recipe_idx >= NUM_RECIPES:
            return -0.01

        recipe = RECIPES[recipe_idx]
        a, b, result = recipe['a'], recipe['b'], recipe['result']

        # 재료 확인
        if a == b:
            if self.grid.count(a) < 2:
                return -0.01
            idx_a = self.grid.index(a)
            self.grid[idx_a] = None
            idx_b = self.grid.index(a)
            self.grid[idx_b] = None
        else:
            if a not in self.grid or b not in self.grid:
                return -0.01
            idx_a = self.grid.index(a)
            self.grid[idx_a] = None
            idx_b = self.grid.index(b)
            self.grid[idx_b] = None

        # 결과물 생성 (첫 번째 빈칸에)
        empty_indices = [i for i, s in enumerate(self.grid) if s is None]
        if empty_indices:
            self.grid[empty_indices[0]] = result
        else:
            # 빈칸 없으면 필드에 직접 배치
            self.field_units.append(result)
            self._update_field_dps()

        # 보상: 0.5 × tier² (조합이 지배적 보상 신호)
        # T2=2.0, T3=4.5, T4=8.0, T5=12.5, T6=18.0
        result_tier = UNIT_DATA[result]['tier']
        return 0.5 * result_tier * result_tier

    # =================================================================
    # 게임 시뮬레이션
    # =================================================================

    def _simulate(self, duration):
        """주어진 시간만큼 게임 시뮬레이션 진행"""
        total_reward = 0.0
        remaining = duration

        while remaining > 0 and not self.game_over and not self.game_cleared:
            dt = min(self.TICK_SIZE, remaining)
            total_reward += self._tick(dt)
            remaining -= dt

        return total_reward

    def _tick(self, dt):
        """한 틱(dt초)의 게임 로직 실행"""
        reward = 0.0
        is_boss_round = (self.round % GAME_CONFIG['bossInterval'] == 0)

        # --- 1. 적 스폰 ---
        if is_boss_round:
            if not self.boss_spawned:
                self._spawn_boss()
                self.boss_spawned = True
        else:
            if self.time_remaining > 5:
                self.spawn_acc += dt
                interval = GAME_CONFIG['spawnInterval']
                while self.spawn_acc >= interval:
                    self.spawn_acc -= interval
                    self._spawn_normal_enemy()

        # --- 2. 전투 (DPS 적용) ---
        reward += self._apply_combat(dt)

        # --- 3. 위험도 패널티 (적 누적 시 연속 손해) ---
        if self.enemies:
            danger = len(self.enemies) / GAME_CONFIG['maxEnemies']
            reward -= 0.05 * danger * danger * dt

        # --- 4. 시간 경과 ---
        self.time_remaining -= dt

        # --- 5. 라운드 종료 체크 ---
        if self.time_remaining <= 0:
            reward += self._process_round_end()

        # --- 6. 적 수 초과 체크 ---
        if len(self.enemies) > GAME_CONFIG['maxEnemies']:
            self.game_over = True
            reward -= 3.0

        return reward

    def _spawn_normal_enemy(self):
        """일반 적 생성"""
        hp = get_normal_enemy_hp(self.round)
        self.enemies.append({
            'hp': hp,
            'max_hp': hp,
            'is_boss': False,
        })

    def _spawn_boss(self):
        """보스 생성"""
        if self.round in BOSS_DATA:
            boss_hp = BOSS_DATA[self.round]['hp']
            self.enemies.append({
                'hp': boss_hp,
                'max_hp': boss_hp,
                'is_boss': True,
            })

    def _apply_combat(self, dt):
        """
        DPS 기반 전투: 투사체 비행/사거리 손실 반영
        실제 게임에서는 투사체가 날아가서 맞아야 데미지 적용되므로
        시뮬레이션 DPS의 75%만 실제 적용
        """
        reward = 0.0

        has_boss = any(e['is_boss'] for e in self.enemies)
        raw_dps = self._field_boss_dps_cache if has_boss else self._field_dps_cache
        total_dps = raw_dps * self.COMBAT_EFFICIENCY
        damage_pool = total_dps * dt

        if damage_pool <= 0 or not self.enemies:
            return reward

        # 약한 적부터 공격 (효율적 처치)
        self.enemies.sort(key=lambda e: (not e['is_boss'], e['hp']))

        killed = []
        for enemy in self.enemies:
            if damage_pool <= 0:
                break
            if enemy['hp'] <= damage_pool:
                damage_pool -= enemy['hp']
                killed.append(enemy)
            else:
                enemy['hp'] -= damage_pool
                damage_pool = 0

        for enemy in killed:
            self.enemies.remove(enemy)
            if enemy['is_boss']:
                self.gold += 1000
                reward += 10.0  # 보스킬 보상
                # 90라운드 보스(무잔) 처치 = 스토리 클리어
                if self.round >= 90:
                    self.game_cleared = True
                    reward += 50.0  # 클리어 보상
            else:
                self.gold += get_kill_gold(self.round)
                reward += 0.02  # 소량 적 처치 보상 (~0.9/라운드)

        return reward

    def _process_round_end(self):
        """라운드 종료 처리"""
        reward = 0.0
        is_boss_round = (self.round % GAME_CONFIG['bossInterval'] == 0)
        boss_alive = any(e['is_boss'] for e in self.enemies)

        if is_boss_round and boss_alive:
            # 보스 미처치 → 게임오버
            self.game_over = True
            reward -= 3.0
        else:
            # 다음 라운드로
            self.round += 1
            self.time_remaining = float(GAME_CONFIG['roundTime'])
            self.boss_spawned = False
            self.spawn_acc = 0.0
            # 라운드 생존 보상: 완만한 증가 (조합 보상 대비 작게)
            # R2=1.07, R10=1.33, R25=1.83, R50=2.67, R90=4.0
            reward += 1.0 + self.round / 30.0

            if self.round > 90:
                self.game_over = True

        return reward

    # 적 궤도 반지름 (mapRadius(300) - 20)
    ENEMY_ORBIT_R = 280.0

    @staticmethod
    def _range_efficiency(unit_range):
        """사거리 기반 보스전 실효 DPS 비율.

        보스는 단일 대상으로 궤도를 순회하므로,
        사거리가 짧은 유닛은 보스를 때리는 시간이 적음.
        일반 적은 다수라 항상 누군가 사거리 안 → 100%.

        efficiency = 0.5 + 0.5 * min(1.0, range / 200)
          T1(80): 70%  T2(100): 75%  T3(120): 80%
          T4(150): 87%  T5(180): 95%  T6(230): 100%
        """
        return 0.5 + 0.5 * min(1.0, unit_range / 200.0)

    def _update_field_dps(self):
        """필드 유닛 DPS 캐시 갱신 (일반 + 보스용 분리)"""
        raw_dps = 0.0
        boss_dps = 0.0
        for key in self.field_units:
            d = UNIT_DATA[key]
            dps = d['dps']
            raw_dps += dps
            boss_dps += dps * self._range_efficiency(d['range'])
        self._field_dps_cache = raw_dps           # 일반 적 대상
        self._field_boss_dps_cache = boss_dps     # 보스 대상

    # =================================================================
    # 유틸리티
    # =================================================================

    def get_game_summary(self):
        """현재 게임 상태 요약 (디버깅/로깅용)"""
        grid_units = [s for s in self.grid if s is not None]
        tier_counts = {}
        for key in grid_units + self.field_units:
            t = UNIT_DATA[key]['tier']
            tier_counts[t] = tier_counts.get(t, 0) + 1

        return {
            'round': self.round,
            'gold': self.gold,
            'time': round(self.time_remaining, 1),
            'enemies': len(self.enemies),
            'grid_units': len(grid_units),
            'field_units': len(self.field_units),
            'field_dps': round(self._field_dps_cache, 0),
            'tier_counts': tier_counts,
        }


# =====================================================================
# 환경 등록 (Gymnasium)
# =====================================================================
gym.register(
    id='DemonSlayerDefense-v0',
    entry_point='game_env:DemonSlayerEnv',
)


if __name__ == '__main__':
    # 간단한 테스트: 랜덤 에이전트로 1 에피소드 실행
    env = DemonSlayerEnv()
    obs, info = env.reset(seed=42)
    print(f"초기 상태: {env.get_game_summary()}")

    total_reward = 0
    steps = 0

    while True:
        mask = env.action_masks()
        valid_actions = np.where(mask)[0]
        action = env.np_random.choice(valid_actions)

        obs, reward, terminated, truncated, info = env.step(action)
        total_reward += reward
        steps += 1

        if steps % 100 == 0:
            summary = env.get_game_summary()
            print(f"  Step {steps}: R{summary['round']} "
                  f"Gold={summary['gold']} "
                  f"DPS={summary['field_dps']} "
                  f"Enemies={summary['enemies']} "
                  f"Reward={total_reward:.1f}")

        if terminated or truncated:
            break

    summary = env.get_game_summary()
    print(f"\n게임 종료! Steps={steps} Round={summary['round']} "
          f"Cleared={info.get('game_cleared', False)} "
          f"Total Reward={total_reward:.1f}")
