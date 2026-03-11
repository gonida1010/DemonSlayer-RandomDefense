"""
game_env.py - 귀멸의 칼날 랜덤 디펜스 강화학습 환경
Gymnasium 호환 환경 (MaskablePPO 지원)

핵심 게임 로직을 Python으로 시뮬레이션:
- 유닛 소환/조합/배치/판매
- 적 스폰 및 DPS 기반 전투
- 라운드 진행 및 보스전
- 승리 조건: 90라운드 무잔 처치
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
    귀멸의 칼날 랜덤 디펜스 - 강화학습 환경

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
    STEP_DURATION = 3.0
    TICK_SIZE = 0.5  # 시뮬레이션 틱 크기 (초)
    GRID_SIZE = 36   # 6x6 그리드

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
    # 관측 생성
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
    # 행동 실행
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

        return -0.01  # 알수없는 행동

    def _wait_penalty(self):
        """WAIT 행동의 기회비용 패널티.

        골드가 충분한데 빈칸도 있으면서 WAIT하면 패널티.
        에이전트가 골드를 쓰지 않고 비축하는 것을 방지.
        """
        cost = GAME_CONFIG['unitSummonCost']  # 150
        summons_possible = self.gold // cost
        has_empty = sum(1 for s in self.grid if s is None)

        if summons_possible > 0 and has_empty > 0:
            # 소환 가능한 횟수에 비례하는 패널티 (max -0.5)
            wasted = min(summons_possible, has_empty)
            return -0.05 * wasted
        return 0.0

    def _summon(self):
        """유닛 소환: 150G 소모 → 랜덤 T1~T3 유닛"""
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

        # 보상: 기본 소환 보상 + 그리드 채움 보너스
        base_reward = 0.1 + 0.1 * tier  # T1=0.2, T2=0.3, T3=0.4

        # 그리드 채움 보상: 유닛이 많을수록 조합 가능성 ↑
        grid_units = sum(1 for s in self.grid if s is not None)
        grid_bonus = 0.02 * grid_units  # 유닛 1개당 +0.02 (max 36개 = +0.72)

        return base_reward + grid_bonus

    def _place(self, unit_key):
        """그리드에서 필드로 유닛 배치 - 티어+DPS 보상"""
        if unit_key not in self.grid:
            return -0.01

        idx = self.grid.index(unit_key)
        self.grid[idx] = None
        self.field_units.append(unit_key)
        self._update_field_dps()

        data = UNIT_DATA[unit_key]
        # 티어 기반 보상: 모든 유닛 배치가 의미 있도록
        # T1=0.15, T2=0.3, T3=0.45, T4=0.6, T5=0.75, T6=0.9
        tier_reward = 0.15 * data['tier']
        # DPS 기여 보상 + 사거리 효율
        dps_reward = min(data['dps'] / 100000.0, 0.5)
        range_bonus = self._range_efficiency(data['range'])
        return tier_reward + dps_reward * range_bonus

    def _sell(self, unit_key):
        """그리드에서 유닛 판매 - 티어 비례 패널티"""
        if unit_key not in self.grid:
            return -0.01

        idx = self.grid.index(unit_key)
        self.grid[idx] = None
        tier = UNIT_DATA[unit_key]['tier']
        sell_price = tier * 50
        self.gold += sell_price
        # 티어가 높을수록 판매 패널티 급증 → 조합 결과물 판매 방지
        # T1:-0.1, T2:-0.2, T3:-0.4, T4:-0.8, T5:-1.6, T6:-3.2
        return -0.1 * (2 ** (tier - 1))

    def _combine(self, recipe_idx):
        """레시피에 따라 두 유닛 조합"""
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

        result_tier = UNIT_DATA[result]['tier']
        # 고티어 조합에 기하급수적 보상 → T4:1.6, T5:3.2, T6:6.4
        return 0.2 * (2 ** (result_tier - 1))

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
            # 보스 라운드에서는 일반 적 미생성
        else:
            if self.time_remaining > 5:
                self.spawn_acc += dt
                interval = GAME_CONFIG['spawnInterval']
                while self.spawn_acc >= interval:
                    self.spawn_acc -= interval
                    self._spawn_normal_enemy()

        # --- 2. 전투 (DPS 적용) ---
        reward += self._apply_combat(dt)

        # --- 3. 시간 경과 ---
        self.time_remaining -= dt

        # --- 4. 라운드 종료 체크 ---
        if self.time_remaining <= 0:
            reward += self._process_round_end()

        # --- 5. 적 수 초과 체크 ---
        if len(self.enemies) > GAME_CONFIG['maxEnemies']:
            self.game_over = True
            reward -= 5.0

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
        """DPS 기반 전투: 보스 라운드에서는 사거리 효율 적용"""
        reward = 0.0

        has_boss = any(e['is_boss'] for e in self.enemies)
        total_dps = self._field_boss_dps_cache if has_boss else self._field_dps_cache
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
                reward += 5.0  # 보스킬 보상 증가
                # 90라운드 보스(무잔) 처치 = 스토리 클리어
                if self.round >= 90:
                    self.game_cleared = True
                    reward += 100.0  # 클리어 보상 대폭 증가
            else:
                self.gold += get_kill_gold(self.round)

        return reward

    def _process_round_end(self):
        """라운드 종료 처리"""
        reward = 0.0
        is_boss_round = (self.round % GAME_CONFIG['bossInterval'] == 0)
        boss_alive = any(e['is_boss'] for e in self.enemies)

        if is_boss_round and boss_alive:
            # 보스 미처치 → 게임오버
            self.game_over = True
            reward -= 5.0
        else:
            # 다음 라운드로
            self.round += 1
            self.time_remaining = float(GAME_CONFIG['roundTime'])
            self.boss_spawned = False
            self.spawn_acc = 0.0
            # 후반 라운드일수록 높은 생존 보상 (R1=1.0, R50=2.5, R89=4.5)
            reward += 1.0 + (self.round / 30.0)

            # 후반 DPS 보너스: R60+ 에서 DPS가 높을수록 추가 보상
            # 무잔 요구 DPS(333k) 이상으로 밀어붙이기 위한 인센티브
            if self.round >= 60:
                # boss DPS 기준 (실제 보스전 성능)
                dps_ratio = min(self._field_boss_dps_cache / 400000.0, 1.0)
                reward += dps_ratio * 2.0  # max +2.0/라운드

            # 라운드 91 이상 도달 시 (있을 수 없는 케이스지만 안전장치)
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
