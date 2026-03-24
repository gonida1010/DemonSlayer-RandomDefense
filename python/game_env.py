"""
game_env.py - 귀멸의 칼날 랜덤 디펜스 강화학습 환경 (하드 모드 - 무한 라운드)
Gymnasium 호환 환경 (MaskablePPO / RecurrentPPO / DQN 지원)

하드 모드 핵심:
- 무한 라운드 (90라운드 클리어 없음, 최대한 오래 생존)
- 하드 모드 적 체력 공식 (노멀 대비 2~3배)
- 90라운드 이후 지수적 난이도 상승
- 알고리즘별 리워드 파일 분리 (rewards_ppo/dqn/recurrent)
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
    ACTION_MACRO_PLACE_BEST, ACTION_MACRO_COMBINE_BEST,
    ACTION_MACRO_SUMMON_ALL, OBS_UNIT_COUNT_START,
    get_normal_enemy_hp, get_kill_gold, get_boss_hp, get_boss_kill_gold,
    get_required_dps,
    HIDDEN_RECIPE_INDICES, SYNERGIES, SYNERGY_DPS_MULTIPLIER,
)


class DemonSlayerEnv(gym.Env):
    """
    귀멸의 칼날 랜덤 디펜스 - 강화학습 환경 (하드 모드, 무한 라운드)

        관측 공간 (73차원):
      [0]  round / 200 (무한 모드: 200으로 정규화)
      [1]  gold / 10000
      [2]  time_remaining / 60
      [3]  enemy_count / max_enemies
      [4]  boss_alive (0 or 1)
      [5]  boss_hp_ratio
      [6]  field_dps / 500000
      [7]  field_unit_count / 30
      [8]  empty_grid_slots / 36
      [9]  valid_combine_count / 54
            [10] required_dps / 500000
            [11] current_dps / required_dps
            [12] rounds_until_boss / bossInterval
            [13] active_synergy_count / total_synergies
            [14] high_tier_ratio (T4+) 
            [15] best_valid_combine_tier / 6
            [16..72] 유닛 타입별 보유 수 (그리드+필드) / 10

        행동 공간 (173개 이산 행동):
      0: 대기 (WAIT)
      1: 소환 (SUMMON)
      2~58:  배치 (PLACE unit_type)
      59~115: 판매 (SELL unit_type)
      116~169: 조합 (COMBINE recipe)
            170: 최고 DPS 유닛 배치
            171: 최고 티어 조합 실행
            172: 골드 소진까지 소환
    """

    metadata = {'render_modes': []}

    STEP_DURATION = 2.0
    TICK_SIZE = 0.5
    GRID_SIZE = 36
    COMBAT_EFFICIENCY = 0.85

    def __init__(self, render_mode=None, reward_module='rewards_ppo',
                 auto_remap_invalid_actions=False):
        super().__init__()
        self.action_space = spaces.Discrete(NUM_ACTIONS)
        self.observation_space = spaces.Box(
            low=0.0, high=1.0, shape=(OBS_DIM,), dtype=np.float32
        )
        self.render_mode = render_mode
        self.auto_remap_invalid_actions = auto_remap_invalid_actions

        # 리워드 모듈 동적 로드
        import importlib
        self.rewards = importlib.import_module(reward_module)

        # 연쇄 조합 추적 (RecurrentPPO용)
        self._recent_combines = 0
        self.invalid_action_remaps = 0

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)

        self.round = 1
        self.gold = GAME_CONFIG['initialGold']
        self.time_remaining = float(GAME_CONFIG['roundTime'])

        self.grid = [None] * self.GRID_SIZE
        self.field_units = []
        self.enemies = []

        self.game_over = False
        self.boss_spawned = False
        self.spawn_acc = 0.0
        self.total_steps = 0
        self._recent_combines = 0
        self.invalid_action_remaps = 0

        self._field_dps_cache = 0.0
        self._field_boss_dps_cache = 0.0
        self._update_field_dps()

        return self._get_obs(), {}

    # =================================================================
    # Gymnasium 인터페이스
    # =================================================================

    def step(self, action):
        assert not self.game_over, "Episode ended"
        self.total_steps += 1

        # 연쇄 조합 카운터 감쇠
        if int(action) < ACTION_COMBINE_START or int(action) > ACTION_COMBINE_START + NUM_RECIPES - 1:
            self._recent_combines = max(0, self._recent_combines - 1)

        action_reward = self._execute_action(int(action))
        sim_reward = self._simulate(self.STEP_DURATION)

        reward = action_reward + sim_reward
        terminated = self.game_over
        truncated = False

        info = {
            'round': self.round,
            'gold': self.gold,
            'field_dps': self._field_dps_cache,
            'enemy_count': len(self.enemies),
            'invalid_action_remaps': self.invalid_action_remaps,
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

        if np.any(mask[ACTION_PLACE_START:ACTION_PLACE_START + NUM_UNIT_TYPES]):
            mask[ACTION_MACRO_PLACE_BEST] = True

        if np.any(mask[ACTION_COMBINE_START:ACTION_COMBINE_START + NUM_RECIPES]):
            mask[ACTION_MACRO_COMBINE_BEST] = True

        if mask[ACTION_SUMMON]:
            mask[ACTION_MACRO_SUMMON_ALL] = True

        return mask

    # =================================================================
    # 관측 생성 (67차원, 무한 모드 정규화)
    # =================================================================

    def _get_obs(self):
        obs = np.zeros(OBS_DIM, dtype=np.float32)

        obs[0] = min(self.round / 200.0, 1.0)  # 무한 모드: 200으로 정규화
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

        required_dps = max(get_required_dps(self.round), 1.0)
        obs[10] = min(required_dps / 500000.0, 1.0)
        obs[11] = min(self._field_dps_cache / required_dps, 3.0) / 3.0
        rounds_until_boss = (GAME_CONFIG['bossInterval'] - (self.round % GAME_CONFIG['bossInterval'])) % GAME_CONFIG['bossInterval']
        obs[12] = rounds_until_boss / float(GAME_CONFIG['bossInterval'])
        obs[13] = self._get_active_synergy_count() / float(len(SYNERGIES) or 1)

        all_owned_units = [slot for slot in self.grid if slot is not None] + list(self.field_units)
        high_tier_units = sum(1 for key in all_owned_units if UNIT_DATA[key]['tier'] >= 4)
        obs[14] = (high_tier_units / len(all_owned_units)) if all_owned_units else 0.0

        best_combine_tier = self._get_best_valid_combine_tier()
        obs[15] = best_combine_tier / 6.0

        # 유닛 타입별 보유 수 (그리드 + 필드)
        counts = [0] * NUM_UNIT_TYPES
        for slot in self.grid:
            if slot is not None:
                counts[UNIT_KEY_TO_IDX[slot]] += 1
        for key in self.field_units:
            counts[UNIT_KEY_TO_IDX[key]] += 1
        for i in range(NUM_UNIT_TYPES):
            obs[OBS_UNIT_COUNT_START + i] = min(counts[i] / 10.0, 1.0)

        return obs

    # =================================================================
    # 행동 실행 (리워드 모듈 사용)
    # =================================================================

    def _execute_action(self, action):
        if action < 0 or action >= NUM_ACTIONS:
            return self.rewards.INVALID_ACTION_PENALTY

        mask = self.action_masks()
        if not mask[action]:
            if not self.auto_remap_invalid_actions:
                return self.rewards.INVALID_ACTION_PENALTY

            remapped_action = self._select_fallback_action(mask)
            self.invalid_action_remaps += 1
            remap_penalty = self.rewards.INVALID_ACTION_PENALTY * 0.5
            return remap_penalty + self._execute_valid_action(remapped_action)

        return self._execute_valid_action(action)

    def _execute_valid_action(self, action):
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

        if action == ACTION_MACRO_PLACE_BEST:
            return self._place_best_dps_unit()

        if action == ACTION_MACRO_COMBINE_BEST:
            return self._combine_best_tier_recipe()

        if action == ACTION_MACRO_SUMMON_ALL:
            return self._summon_until_depleted()

        return self.rewards.INVALID_ACTION_PENALTY

    def _select_fallback_action(self, mask):
        """마스킹이 없는 알고리즘용 유효 행동 보정.

        초반 학습이 invalid action에 매몰되지 않도록,
        현재 상태에서 가장 무난한 유효 행동으로 치환한다.
        """
        # 초반에는 배치 우선: DPS를 빠르게 올려 라운드 1~3 생존을 안정화
        if self._field_dps_cache <= 0 or len(self.field_units) < 4:
            best_place = self._best_place_action(mask)
            if best_place is not None:
                return best_place

        best_combine = self._best_combine_action(mask)
        if best_combine is not None:
            return best_combine

        best_place = self._best_place_action(mask)
        if best_place is not None:
            return best_place

        if mask[ACTION_SUMMON]:
            return ACTION_SUMMON

        if mask[ACTION_WAIT]:
            return ACTION_WAIT

        sell_slice = mask[ACTION_SELL_START:ACTION_SELL_START + NUM_UNIT_TYPES]
        sell_indices = np.flatnonzero(sell_slice)
        if len(sell_indices) > 0:
            # 마지막 수단: 가장 낮은 티어부터 판매
            sell_idx = min(
                sell_indices,
                key=lambda idx: (
                    UNIT_DATA[UNIT_KEYS[idx]]['tier'],
                    UNIT_DATA[UNIT_KEYS[idx]]['dps'],
                ),
            )
            return ACTION_SELL_START + int(sell_idx)

        return ACTION_WAIT

    def _best_place_action(self, mask):
        place_slice = mask[ACTION_PLACE_START:ACTION_PLACE_START + NUM_UNIT_TYPES]
        place_indices = np.flatnonzero(place_slice)
        if len(place_indices) == 0:
            return None

        best_idx = max(
            place_indices,
            key=lambda idx: (
                UNIT_DATA[UNIT_KEYS[idx]]['tier'],
                UNIT_DATA[UNIT_KEYS[idx]]['dps'],
            ),
        )
        return ACTION_PLACE_START + int(best_idx)

    def _best_combine_action(self, mask):
        combine_slice = mask[ACTION_COMBINE_START:ACTION_COMBINE_START + NUM_RECIPES]
        combine_indices = np.flatnonzero(combine_slice)
        if len(combine_indices) == 0:
            return None

        best_idx = max(
            combine_indices,
            key=lambda idx: (
                UNIT_DATA[RECIPES[idx]['result']]['tier'],
                1 if RECIPES[idx].get('hidden', False) else 0,
                UNIT_DATA[RECIPES[idx]['result']]['dps'],
            ),
        )
        return ACTION_COMBINE_START + int(best_idx)

    def _wait_penalty(self):
        cost = GAME_CONFIG['unitSummonCost']
        summons_possible = self.gold // cost
        has_empty = sum(1 for s in self.grid if s is None)
        return self.rewards.wait_penalty(summons_possible, has_empty)

    def _summon(self, grant_reward=True):
        cost = GAME_CONFIG['unitSummonCost']
        if self.gold < cost:
            return self.rewards.INVALID_ACTION_PENALTY

        empty_indices = [i for i, s in enumerate(self.grid) if s is None]
        if not empty_indices:
            return self.rewards.INVALID_ACTION_PENALTY

        self.gold -= cost

        roll = self.np_random.integers(1, 101)
        if roll <= 10:
            tier = 3
        elif roll <= 30:
            tier = 2
        else:
            tier = 1

        pool = TIER_POOL[tier]
        unit_key = pool[self.np_random.integers(0, len(pool))]
        slot = empty_indices[self.np_random.integers(0, len(empty_indices))]
        self.grid[slot] = unit_key

        return self.rewards.SUMMON_REWARD if grant_reward else 0.0

    def _place(self, unit_key):
        if unit_key not in self.grid:
            return self.rewards.INVALID_ACTION_PENALTY

        idx = self.grid.index(unit_key)
        self.grid[idx] = None
        self.field_units.append(unit_key)
        self._update_field_dps()

        tier = UNIT_DATA[unit_key]['tier']
        return self.rewards.place_reward(tier)

    def _sell(self, unit_key):
        if unit_key not in self.grid:
            return self.rewards.INVALID_ACTION_PENALTY

        idx = self.grid.index(unit_key)
        self.grid[idx] = None
        tier = UNIT_DATA[unit_key]['tier']
        sell_price = tier * 50
        self.gold += sell_price
        return self.rewards.sell_penalty(tier)

    def _combine(self, recipe_idx):
        if recipe_idx < 0 or recipe_idx >= NUM_RECIPES:
            return self.rewards.INVALID_ACTION_PENALTY

        recipe = RECIPES[recipe_idx]
        a, b, result = recipe['a'], recipe['b'], recipe['result']

        if a == b:
            if self.grid.count(a) < 2:
                return self.rewards.INVALID_ACTION_PENALTY
            idx_a = self.grid.index(a)
            self.grid[idx_a] = None
            idx_b = self.grid.index(a)
            self.grid[idx_b] = None
        else:
            if a not in self.grid or b not in self.grid:
                return self.rewards.INVALID_ACTION_PENALTY
            idx_a = self.grid.index(a)
            self.grid[idx_a] = None
            idx_b = self.grid.index(b)
            self.grid[idx_b] = None

        empty_indices = [i for i, s in enumerate(self.grid) if s is None]
        if empty_indices:
            self.grid[empty_indices[0]] = result
        else:
            self.field_units.append(result)
            self._update_field_dps()

        result_tier = UNIT_DATA[result]['tier']
        self._recent_combines += 1

        # 히든 레시피 보너스 (1.5x)
        is_hidden = recipe_idx in HIDDEN_RECIPE_INDICES
        hidden_mult = self.rewards.HIDDEN_COMBINE_MULTIPLIER if is_hidden else 1.0

        # 리워드 모듈이 consecutive_combines 인자를 지원하면 전달
        import inspect
        sig = inspect.signature(self.rewards.combine_reward)
        if len(sig.parameters) > 1:
            return self.rewards.combine_reward(result_tier, self._recent_combines) * hidden_mult
        return self.rewards.combine_reward(result_tier) * hidden_mult

    def _place_best_dps_unit(self):
        best_unit = max(
            (key for key in self.grid if key is not None),
            default=None,
            key=lambda key: (
                UNIT_DATA[key]['dps'],
                UNIT_DATA[key]['tier'],
            ),
        )
        if best_unit is None:
            return self.rewards.INVALID_ACTION_PENALTY
        return self._place(best_unit)

    def _combine_best_tier_recipe(self):
        best_recipe_idx = self._get_best_valid_combine_recipe_idx()
        if best_recipe_idx is None:
            return self.rewards.INVALID_ACTION_PENALTY
        return self._combine(best_recipe_idx)

    def _summon_until_depleted(self):
        summoned = 0
        while self.gold >= GAME_CONFIG['unitSummonCost'] and any(slot is None for slot in self.grid):
            result = self._summon(grant_reward=False)
            if result == self.rewards.INVALID_ACTION_PENALTY:
                break
            summoned += 1

        if summoned == 0:
            return self.rewards.INVALID_ACTION_PENALTY

        return self.rewards.SUMMON_REWARD * min(summoned, 4) * 0.5

    def _get_best_valid_combine_recipe_idx(self):
        grid_counts = {}
        for slot in self.grid:
            if slot is not None:
                grid_counts[slot] = grid_counts.get(slot, 0) + 1

        valid_recipe_indices = []
        for i, recipe in enumerate(RECIPES):
            a, b = recipe['a'], recipe['b']
            if a == b:
                is_valid = grid_counts.get(a, 0) >= 2
            else:
                is_valid = grid_counts.get(a, 0) >= 1 and grid_counts.get(b, 0) >= 1
            if is_valid:
                valid_recipe_indices.append(i)

        if not valid_recipe_indices:
            return None

        return max(
            valid_recipe_indices,
            key=lambda idx: (
                UNIT_DATA[RECIPES[idx]['result']]['tier'],
                1 if RECIPES[idx].get('hidden', False) else 0,
                UNIT_DATA[RECIPES[idx]['result']]['dps'],
            ),
        )

    def _get_best_valid_combine_tier(self):
        best_recipe_idx = self._get_best_valid_combine_recipe_idx()
        if best_recipe_idx is None:
            return 0
        return UNIT_DATA[RECIPES[best_recipe_idx]['result']]['tier']

    def _get_active_synergy_count(self):
        field_set = set(self.field_units)
        return sum(1 for synergy in SYNERGIES if all(unit in field_set for unit in synergy['units']))

    # =================================================================
    # 게임 시뮬레이션
    # =================================================================

    def _simulate(self, duration):
        total_reward = 0.0
        remaining = duration

        while remaining > 0 and not self.game_over:
            dt = min(self.TICK_SIZE, remaining)
            total_reward += self._tick(dt)
            remaining -= dt

        return total_reward

    def _tick(self, dt):
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

        # --- 2. 전투 ---
        reward += self._apply_combat(dt)

        # --- 3. 위험도 패널티 ---
        if self.enemies:
            danger = len(self.enemies) / GAME_CONFIG['maxEnemies']
            reward += self.rewards.danger_penalty(danger, dt)

        # --- 4. 시간 경과 ---
        self.time_remaining -= dt

        # --- 5. 라운드 종료 ---
        if self.time_remaining <= 0:
            reward += self._process_round_end()

        # --- 6. 적 수 초과 ---
        if len(self.enemies) > GAME_CONFIG['maxEnemies']:
            self.game_over = True
            reward += self.rewards.GAME_OVER_PENALTY

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
        """보스 생성 (무한 모드: 90 이후도 스케일링)"""
        boss_hp = get_boss_hp(self.round)
        if boss_hp > 0:
            self.enemies.append({
                'hp': boss_hp,
                'max_hp': boss_hp,
                'is_boss': True,
            })

    def _apply_combat(self, dt):
        reward = 0.0
        has_boss = any(e['is_boss'] for e in self.enemies)
        raw_dps = self._field_boss_dps_cache if has_boss else self._field_dps_cache
        total_dps = raw_dps * self.COMBAT_EFFICIENCY
        damage_pool = total_dps * dt

        if damage_pool <= 0 or not self.enemies:
            return reward

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
                self.gold += get_boss_kill_gold(self.round)
                reward += self.rewards.BOSS_KILL_REWARD
            else:
                self.gold += get_kill_gold(self.round)
                reward += self.rewards.ENEMY_KILL_REWARD

        return reward

    def _process_round_end(self):
        """라운드 종료 처리 (무한 모드: 클리어 없음)"""
        reward = 0.0
        is_boss_round = (self.round % GAME_CONFIG['bossInterval'] == 0)
        boss_alive = any(e['is_boss'] for e in self.enemies)

        if is_boss_round and boss_alive:
            self.game_over = True
            reward += self.rewards.BOSS_TIMEOUT_PENALTY
        else:
            self.round += 1
            self.time_remaining = float(GAME_CONFIG['roundTime'])
            self.boss_spawned = False
            self.spawn_acc = 0.0
            reward += self.rewards.round_survival_reward(self.round)

            # RecurrentPPO 전용: 필드 구성 보너스
            if hasattr(self.rewards, 'field_composition_bonus'):
                tier_counts = {}
                for key in self.field_units:
                    t = UNIT_DATA[key]['tier']
                    tier_counts[t] = tier_counts.get(t, 0) + 1
                reward += self.rewards.field_composition_bonus(tier_counts)

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
        """필드 유닛 DPS 캐시 갱신 (일반 + 보스용 분리, 시너지 적용)"""
        # 시너지 보너스 적용 대상 유닛 키 집합
        boosted = self._get_synergy_boosted_units()

        raw_dps = 0.0
        boss_dps = 0.0
        for key in self.field_units:
            d = UNIT_DATA[key]
            dps = d['dps']
            if key in boosted:
                dps *= SYNERGY_DPS_MULTIPLIER
            raw_dps += dps
            boss_dps += dps * self._range_efficiency(d['range'])
        self._field_dps_cache = raw_dps           # 일반 적 대상
        self._field_boss_dps_cache = boss_dps     # 보스 대상

    def _get_synergy_boosted_units(self):
        """활성된 시너지의 구성원 유닛 키 집합 반환"""
        field_set = set(self.field_units)
        boosted = set()
        for synergy in SYNERGIES:
            units = synergy['units']
            if all(u in field_set for u in units):
                boosted.update(units)
        return boosted

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
    kwargs={'reward_module': 'rewards_ppo'},
)


if __name__ == '__main__':
    import sys
    reward_mod = sys.argv[1] if len(sys.argv) > 1 else 'rewards_ppo'
    print(f"리워드 모듈: {reward_mod}")

    env = DemonSlayerEnv(reward_module=reward_mod)
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
          f"Total Reward={total_reward:.1f}")
