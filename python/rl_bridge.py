"""
rl_bridge.py - 학습된 RL 모델로 실제 게임 제어 + AI 대전

학습된 모델을 로드하고 WebSocket을 통해 실제 브라우저 게임을 제어합니다.
AI 대전 모드에서는 내부 game_env를 사용해 병렬 게임을 시뮬레이션합니다.

사용법 (일반 RL 모드):
    1. cd /d c:\\Pyg\\DemonSlayer_RandomDefense\\MyDefenseGame
    2. npm start
    3. http://localhost:3000/?rl=true 접속
    4. python rl_bridge.py --model models/ppo/best_model.zip

    python rl_bridge.py --model models/recurrent/demon_slayer_final.zip --algorithm recurrent
    python rl_bridge.py --model models/dqn/demon_slayer_final.zip --algorithm dqn

사용법 (AI 대전 지원 - 서버가 자동 호출):
    python rl_bridge.py --model models/ppo/demon_slayer_final.zip --ai-battle
"""
import argparse
import time
import threading
import numpy as np

try:
    import socketio
except ImportError:
    print("socketio 패키지가 필요합니다: pip install python-socketio[client] websocket-client")
    exit(1)

from socketio.exceptions import ConnectionError as SocketConnectionError

from sb3_contrib import MaskablePPO, RecurrentPPO
from stable_baselines3 import DQN
from game_data import (
    UNIT_DATA, UNIT_KEYS, UNIT_KEY_TO_IDX, RECIPES,
    GAME_CONFIG, NUM_ACTIONS, OBS_DIM, NUM_UNIT_TYPES,
    ACTION_WAIT, ACTION_SUMMON,
    ACTION_PLACE_START, ACTION_SELL_START, ACTION_COMBINE_START,
    ACTION_MACRO_PLACE_BEST, ACTION_MACRO_COMBINE_BEST,
    ACTION_MACRO_SUMMON_ALL, ACTION_FOCUS_BOSS, ACTION_KITE_TO_BOSS,
    ACTION_SET_SPEED_1X, ACTION_SET_SPEED_2X, ACTION_SET_SPEED_3X, ACTION_SET_SPEED_5X,
    OBS_UNIT_COUNT_START,
    get_required_dps, SYNERGIES,
)

ALGO_CLASSES = {
    'ppo': MaskablePPO,
    'recurrent': RecurrentPPO,
    'dqn': DQN,
}


def _get_owned_unit_counts(grid_state, field_units):
    counts = {}
    for slot in grid_state:
        if slot and 'key' in slot:
            key = slot['key']
            counts[key] = counts.get(key, 0) + 1
    for unit in field_units:
        key = unit.get('key') if isinstance(unit, dict) else unit
        if key:
            counts[key] = counts.get(key, 0) + 1
    return counts


def _is_recipe_valid(recipe, owned_counts):
    a, b = recipe['a'], recipe['b']
    if a == b:
        return owned_counts.get(a, 0) >= 2
    return owned_counts.get(a, 0) >= 1 and owned_counts.get(b, 0) >= 1


def _apply_dqn_mask(model, obs, mask, device='cpu'):
    """DQN 행동 선택 시 마스크 적용 (유효하지 않은 행동의 Q값 → -inf)"""
    import torch
    obs_tensor = torch.as_tensor(obs).float()
    if obs_tensor.dim() == 1:
        obs_tensor = obs_tensor.unsqueeze(0)
    q_values = model.q_net(obs_tensor.to(model.device))
    q_values = q_values.detach().cpu().numpy().flatten()
    q_values[~np.array(mask, dtype=bool)] = -np.inf
    return int(np.argmax(q_values))


class RLBridge:
    """학습된 모델로 실제 게임을 제어하는 브릿지"""

    def __init__(self, model_path, algorithm='ppo'):
        self.algorithm = algorithm
        cls = ALGO_CLASSES.get(algorithm, MaskablePPO)
        self.model = cls.load(model_path)
        self.sio = socketio.Client()
        self.game_state = None
        self.game_ready = False
        self.ai_battle_active = False

        # RecurrentPPO LSTM 상태 추적
        self.lstm_states = None
        self.episode_start = np.ones(1, dtype=bool)

        self._setup_events()

    def _setup_events(self):
        @self.sio.on('connect')
        def on_connect():
            print("서버 연결 성공!")
            self.sio.emit('rl_connect', {'speed': 1})

        @self.sio.on('rl_game_ready')
        def on_game_ready():
            print("게임 브라우저 준비 완료! 에이전트 시작...")
            self.game_ready = True

        @self.sio.on('rl_state')
        def on_state(state):
            self.game_state = state

        @self.sio.on('disconnect')
        def on_disconnect():
            print("서버 연결 해제")
            self.game_ready = False

        @self.sio.on('rl_load_model')
        def on_load_model(data):
            model_path = data.get('path', '')
            algo = data.get('algorithm', self.algorithm)
            print(f"\n모델 변경 요청: {model_path} ({algo})")
            try:
                cls = ALGO_CLASSES.get(algo, MaskablePPO)
                self.model = cls.load(model_path)
                self.algorithm = algo
                self.lstm_states = None
                self.episode_start = np.ones(1, dtype=bool)
                print(f"  모델 로드 성공!")
                self.sio.emit('rl_model_loaded', {
                    'success': True,
                    'path': model_path,
                    'algorithm': algo,
                })
            except Exception as e:
                print(f"  모델 로드 실패: {e}")
                self.sio.emit('rl_model_loaded', {
                    'success': False,
                    'error': str(e),
                })

        @self.sio.on('ai_battle_start')
        def on_ai_battle_start(data):
            print("AI 대전 요청 수신! 병렬 시뮬레이션 시작...")
            self.ai_battle_active = True
            thread = threading.Thread(target=self._run_ai_battle, daemon=True)
            thread.start()

    def connect(self, url='http://localhost:3000'):
        print(f"서버 연결 시도: {url}")
        try:
            self.sio.connect(url)
        except SocketConnectionError as exc:
            print("서버 연결 실패")
            print(f"  주소: {url}")
            print(f"  원인: {exc}")
            print("  해결: 프로젝트 루트에서 서버를 먼저 실행하세요.")
            print("  명령어: npm start")
            raise SystemExit(1) from exc

    def state_to_obs(self, state):
        """게임 상태 → 관측 벡터 변환 (하드 모드: round/200.0)"""
        obs = np.zeros(OBS_DIM, dtype=np.float32)

        obs[0] = state.get('round', 1) / 200.0
        obs[1] = min(state.get('gold', 0) / 10000.0, 1.0)
        obs[2] = max(state.get('timeRemaining', 0), 0) / 60.0
        obs[3] = min(state.get('enemyCount', 0) / state.get('maxEnemies', GAME_CONFIG['maxEnemies']), 1.0)

        enemies = state.get('enemies', [])
        boss = next((e for e in enemies if e.get('isBoss')), None)
        obs[4] = 1.0 if boss else 0.0
        obs[5] = (boss['hp'] / boss['maxHp']) if boss else 0.0

        obs[6] = min(state.get('totalFieldDps', 0) / 500000.0, 1.0)
        field_units = state.get('fieldUnits', [])
        obs[7] = min(len(field_units) / 40.0, 1.0)

        grid_state = state.get('gridState', [])
        empty_count = sum(1 for s in grid_state if s is None)
        obs[8] = empty_count / 36.0

        obs[9] = min(state.get('validCombines', 0) / 54.0, 1.0)

        required_dps = max(get_required_dps(state.get('round', 1)), 1.0)
        obs[10] = min(required_dps / 500000.0, 1.0)
        obs[11] = min(state.get('totalFieldDps', 0) / required_dps, 3.0) / 3.0

        round_num = state.get('round', 1)
        rounds_until_boss = (GAME_CONFIG['bossInterval'] - (round_num % GAME_CONFIG['bossInterval'])) % GAME_CONFIG['bossInterval']
        obs[12] = rounds_until_boss / float(GAME_CONFIG['bossInterval'])

        field_keys = [u.get('key') if isinstance(u, dict) else u for u in field_units]
        field_set = set(field_keys)
        active_synergies = sum(1 for synergy in SYNERGIES if all(unit in field_set for unit in synergy['units']))
        obs[13] = active_synergies / float(len(SYNERGIES) or 1)
        owned_counts = _get_owned_unit_counts(grid_state, field_units)

        counts = [0] * NUM_UNIT_TYPES
        for slot in grid_state:
            if slot and 'key' in slot:
                idx = UNIT_KEY_TO_IDX.get(slot['key'])
                if idx is not None:
                    counts[idx] += 1
        for u in field_units:
            key = u.get('key') if isinstance(u, dict) else u
            idx = UNIT_KEY_TO_IDX.get(key)
            if idx is not None:
                counts[idx] += 1

        owned_keys = [slot['key'] for slot in grid_state if slot and 'key' in slot] + [key for key in field_keys if key]
        high_tier_units = sum(1 for key in owned_keys if UNIT_DATA[key]['tier'] >= 4)
        obs[14] = (high_tier_units / len(owned_keys)) if owned_keys else 0.0

        best_combine_tier = 0
        for recipe in RECIPES:
            if _is_recipe_valid(recipe, owned_counts):
                best_combine_tier = max(best_combine_tier, UNIT_DATA[recipe['result']]['tier'])
        obs[15] = best_combine_tier / 6.0

        # 보스 집중 공격 상태
        obs[16] = 1.0 if state.get('focusBoss', False) else 0.0

        # 카이팅 쿨다운 상태
        obs[17] = min(state.get('kiteCooldown', 0) / 0.3, 1.0)

        # 현재 게임 배속 상태
        obs[18] = min(float(state.get('timeScale', 1.0) or 1.0) / 5.0, 1.0)

        for i in range(NUM_UNIT_TYPES):
            obs[OBS_UNIT_COUNT_START + i] = min(counts[i] / 10.0, 1.0)

        return obs

    def get_action_mask(self, state):
        """게임 상태에서 유효 행동 마스크 생성"""
        mask = np.zeros(NUM_ACTIONS, dtype=bool)
        mask[ACTION_WAIT] = True

        grid_state = state.get('gridState', [])
        field_units = state.get('fieldUnits', [])
        gold = state.get('gold', 0)
        has_empty = any(s is None for s in grid_state)

        if gold >= GAME_CONFIG['unitSummonCost'] and has_empty:
            mask[ACTION_SUMMON] = True

        owned_counts = _get_owned_unit_counts(grid_state, field_units)
        field_full = len(field_units) >= GAME_CONFIG.get('maxFieldUnits', 40)

        for key in {slot['key'] for slot in grid_state if slot and 'key' in slot}:
            idx = UNIT_KEY_TO_IDX.get(key)
            if idx is not None:
                if not field_full:
                    mask[ACTION_PLACE_START + idx] = True
                mask[ACTION_SELL_START + idx] = True

        for i, recipe in enumerate(RECIPES):
            if _is_recipe_valid(recipe, owned_counts):
                mask[ACTION_COMBINE_START + i] = True

        if np.any(mask[ACTION_PLACE_START:ACTION_PLACE_START + NUM_UNIT_TYPES]):
            mask[ACTION_MACRO_PLACE_BEST] = True

        if np.any(mask[ACTION_COMBINE_START:ACTION_COMBINE_START + len(RECIPES)]):
            mask[ACTION_MACRO_COMBINE_BEST] = True

        if mask[ACTION_SUMMON]:
            mask[ACTION_MACRO_SUMMON_ALL] = True

        # FOCUS_BOSS: 보스가 살아있고 필드 유닛이 있을 때
        enemies = state.get('enemies', [])
        boss_alive = any(e.get('isBoss') for e in enemies)
        field_units = state.get('fieldUnits', [])
        if boss_alive and len(field_units) > 0:
            mask[ACTION_FOCUS_BOSS] = True

        # KITE_TO_BOSS: 보스가 살아있고 필드 유닛이 있고 쿨다운이 끝났을 때
        if boss_alive and len(field_units) > 0 and state.get('kiteCooldown', 0) <= 0:
            mask[ACTION_KITE_TO_BOSS] = True

        current_speed = float(state.get('timeScale', 1.0) or 1.0)
        if current_speed != 1.0:
            mask[ACTION_SET_SPEED_1X] = True
        if current_speed != 2.0:
            mask[ACTION_SET_SPEED_2X] = True
        if current_speed != 3.0:
            mask[ACTION_SET_SPEED_3X] = True
        if current_speed != 5.0:
            mask[ACTION_SET_SPEED_5X] = True

        return mask

    def action_to_command(self, action):
        """행동 인덱스 → 게임 명령 변환"""
        if action == ACTION_WAIT:
            return {'type': 'wait', 'params': {}}
        if action == ACTION_SUMMON:
            return {'type': 'summon', 'params': {}}
        if ACTION_PLACE_START <= action < ACTION_PLACE_START + NUM_UNIT_TYPES:
            key = UNIT_KEYS[action - ACTION_PLACE_START]
            return {'type': 'place', 'params': {'unitKey': key}}
        if ACTION_SELL_START <= action < ACTION_SELL_START + NUM_UNIT_TYPES:
            key = UNIT_KEYS[action - ACTION_SELL_START]
            return {'type': 'sell', 'params': {'unitKey': key}}
        if ACTION_COMBINE_START <= action < ACTION_COMBINE_START + len(RECIPES):
            recipe = RECIPES[action - ACTION_COMBINE_START]
            return {'type': 'combine', 'params': {'a': recipe['a'], 'b': recipe['b']}}
        if action == ACTION_MACRO_PLACE_BEST:
            return {'type': 'place_best_dps', 'params': {}}
        if action == ACTION_MACRO_COMBINE_BEST:
            return {'type': 'combine_best_tier', 'params': {}}
        if action == ACTION_MACRO_SUMMON_ALL:
            return {'type': 'summon_all', 'params': {}}
        if action == ACTION_FOCUS_BOSS:
            return {'type': 'focus_boss', 'params': {}}
        if action == ACTION_KITE_TO_BOSS:
            return {'type': 'kite_to_boss', 'params': {}}
        if action == ACTION_SET_SPEED_1X:
            return {'type': 'set_speed', 'params': {'speed': 1}}
        if action == ACTION_SET_SPEED_2X:
            return {'type': 'set_speed', 'params': {'speed': 2}}
        if action == ACTION_SET_SPEED_3X:
            return {'type': 'set_speed', 'params': {'speed': 3}}
        if action == ACTION_SET_SPEED_5X:
            return {'type': 'set_speed', 'params': {'speed': 5}}
        return {'type': 'wait', 'params': {}}

    def predict_action(self, obs, mask):
        """알고리즘별 행동 예측"""
        if self.algorithm == 'ppo':
            action, _ = self.model.predict(obs, action_masks=mask, deterministic=True)
        elif self.algorithm == 'recurrent':
            action, self.lstm_states = self.model.predict(
                obs, state=self.lstm_states,
                episode_start=self.episode_start,
                deterministic=True
            )
            self.episode_start = np.zeros(1, dtype=bool)
        elif self.algorithm == 'dqn':
            action = _apply_dqn_mask(self.model, obs, mask)
        else:
            action, _ = self.model.predict(obs, deterministic=True)
        return int(action)

    # =====================================================================
    # AI 대전: 내부 game_env 시뮬레이션
    # =====================================================================
    def _run_ai_battle(self):
        """병렬 game_env 시뮬레이션으로 AI 대전 수행"""
        from game_env import DemonSlayerEnv

        algo_reward = {
            'ppo': 'rewards_ppo',
            'recurrent': 'rewards_recurrent',
            'dqn': 'rewards_dqn',
        }
        env = DemonSlayerEnv(reward_module=algo_reward.get(self.algorithm, 'rewards_ppo'))
        obs, info = env.reset()

        # LSTM 상태 초기화 (RecurrentPPO용)
        self.lstm_states = None
        self.episode_start = np.ones(1, dtype=bool)

        step_count = 0
        done = False

        while not done and self.ai_battle_active and self.sio.connected:
            mask = env.action_masks()
            action = self.predict_action(obs, mask)
            obs, reward, terminated, truncated, info = env.step(action)
            done = terminated or truncated
            step_count += 1

            # 5스텝마다 진행 상황 브라우저에 전송
            if step_count % 5 == 0 or done:
                summary = env.get_game_summary()
                self.sio.emit('ai_battle_state', {
                    'round': summary['round'],
                    'fieldDps': summary['field_dps'],
                    'gold': summary['gold'],
                    'fieldUnits': summary['field_units'],
                    'isGameOver': done,
                    'steps': step_count,
                })

        # 최종 결과 전송
        final = env.get_game_summary()
        self.sio.emit('ai_battle_result', {
            'finalRound': final['round'],
            'fieldDps': final['field_dps'],
            'steps': step_count,
        })
        print(f"AI 대전 완료: Round {final['round']}, DPS={final['field_dps']:,.0f}")
        self.ai_battle_active = False

    # =====================================================================
    # 일반 RL 모드: 브라우저 게임 제어
    # =====================================================================
    def run(self, decision_interval=0.02):
        """메인 루프: 상태 수신 → 행동 결정 → 명령 전송"""
        print("게임 브라우저가 준비될 때까지 대기...")
        print("  브라우저에서 http://localhost:3000/?rl=true 접속하세요")

        while not self.game_ready:
            time.sleep(0.5)

        print("=" * 55)
        print("  에이전트가 게임을 제어합니다!")
        print(f"  알고리즘: {self.algorithm.upper()}")
        print("  종료: Ctrl+C")
        print("=" * 55)

        step = 0
        last_round = 0
        self.lstm_states = None
        self.episode_start = np.ones(1, dtype=bool)

        while self.sio.connected:
            if not self.game_state:
                time.sleep(0.05)
                continue

            state = self.game_state

            if state.get('isGameOver'):
                print(f"\n{'=' * 55}")
                print(f"  게임 종료! 최종 라운드: {state.get('round')}")
                print(f"  총 행동 수: {step}")
                print(f"{'=' * 55}")
                break

            cur_round = state.get('round', 0)
            if cur_round != last_round:
                dps = state.get('totalFieldDps', 0)
                gold = state.get('gold', 0)
                field_cnt = len(state.get('fieldUnits', []))
                grid_filled = sum(1 for s in state.get('gridState', []) if s is not None)
                print(f"\n── Round {cur_round} ──  DPS={dps:,.0f}  Gold={gold}  "
                      f"Field={field_cnt}  Grid={grid_filled}/36")
                last_round = cur_round

            obs = self.state_to_obs(state)
            mask = self.get_action_mask(state)
            action = self.predict_action(obs, mask)

            command = self.action_to_command(action)
            self.sio.emit('rl_action', command)

            step += 1
            if command['type'] != 'wait':
                params_str = ', '.join(f"{k}={v}" for k, v in command.get('params', {}).items())
                print(f"  [{step:>5}] {command['type'].upper():>7}  {params_str}")

            speed_scale = max(float(state.get('timeScale', 1.0) or 1.0), 1.0)
            boss_alive = any(enemy.get('isBoss') for enemy in state.get('enemies', []))
            field_count = len(state.get('fieldUnits', []))

            effective_interval = max(0.005, decision_interval / speed_scale)
            if boss_alive and field_count > 0:
                effective_interval = min(effective_interval, 0.02)

            time.sleep(effective_interval)

        print("RL 브릿지 종료")

    def disconnect(self):
        self.ai_battle_active = False
        if self.sio.connected:
            self.sio.disconnect()


def main():
    parser = argparse.ArgumentParser(description='RL 브릿지 - 학습된 모델로 게임 제어 / AI 대전')
    parser.add_argument('--model', type=str, required=True, help='학습된 모델 경로 (.zip)')
    parser.add_argument('--algorithm', type=str, default='ppo',
                        choices=['ppo', 'recurrent', 'dqn'],
                        help='알고리즘 (기본: ppo)')
    parser.add_argument('--url', type=str, default='http://localhost:3000', help='서버 URL')
    parser.add_argument('--interval', type=float, default=0.05, help='기본 결정 간격 (초, 배속에 따라 추가 단축)')
    parser.add_argument('--ai-battle', action='store_true',
                        help='AI 대전 대기 모드 (서버에서 요청 시 시뮬레이션 수행)')
    args = parser.parse_args()

    bridge = RLBridge(args.model, algorithm=args.algorithm)
    try:
        bridge.connect(args.url)
        if args.ai_battle:
            print("AI 대전 대기 모드. 브라우저에서 AI 대전 시작 대기 중...")
            while bridge.sio.connected:
                time.sleep(1)
        else:
            bridge.run(decision_interval=args.interval)
    except KeyboardInterrupt:
        print("\n사용자 중단")
    finally:
        bridge.disconnect()


if __name__ == '__main__':
    main()
