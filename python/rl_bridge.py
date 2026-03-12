"""
rl_bridge.py - 학습된 RL 모델로 실제 게임 제어

학습된 모델을 로드하고 WebSocket을 통해 실제 브라우저 게임을 제어합니다.

사용법:
  1. 서버 시작: node server.js
  2. 브라우저에서 http://localhost:3000/?rl=true 접속
  3. 이 스크립트 실행: python rl_bridge.py --model models/demon_slayer_final.zip

의존성: pip install python-socketio[client] websocket-client
"""
import argparse
import time
import numpy as np

try:
    import socketio
except ImportError:
    print("socketio 패키지가 필요합니다: pip install python-socketio[client] websocket-client")
    exit(1)

from sb3_contrib import MaskablePPO
from game_data import (
    UNIT_DATA, UNIT_KEYS, UNIT_KEY_TO_IDX, RECIPES,
    GAME_CONFIG, NUM_ACTIONS, OBS_DIM, NUM_UNIT_TYPES,
    ACTION_WAIT, ACTION_SUMMON,
    ACTION_PLACE_START, ACTION_SELL_START, ACTION_COMBINE_START,
)


class RLBridge:
    """학습된 모델로 실제 게임을 제어하는 브릿지"""

    def __init__(self, model_path):
        self.model = MaskablePPO.load(model_path)
        self.sio = socketio.Client()
        self.game_state = None
        self.game_ready = False

        self._setup_events()

    def _setup_events(self):
        @self.sio.on('connect')
        def on_connect():
            print("서버 연결 성공!")
            self.sio.emit('rl_connect', {'speed': 10})

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

    def connect(self, url='http://localhost:3000'):
        print(f"서버 연결 시도: {url}")
        self.sio.connect(url)

    def state_to_obs(self, state):
        """게임 상태 → 관측 벡터 변환 (game_env._get_obs() v4: 67차원)"""
        obs = np.zeros(OBS_DIM, dtype=np.float32)

        obs[0] = state.get('round', 1) / 90.0
        obs[1] = min(state.get('gold', 0) / 10000.0, 1.0)
        obs[2] = max(state.get('timeRemaining', 0), 0) / 60.0
        obs[3] = min(state.get('enemyCount', 0) / state.get('maxEnemies', GAME_CONFIG['maxEnemies']), 1.0)

        enemies = state.get('enemies', [])
        boss = next((e for e in enemies if e.get('isBoss')), None)
        obs[4] = 1.0 if boss else 0.0
        obs[5] = (boss['hp'] / boss['maxHp']) if boss else 0.0

        obs[6] = min(state.get('totalFieldDps', 0) / 500000.0, 1.0)
        field_units = state.get('fieldUnits', [])
        obs[7] = min(len(field_units) / 30.0, 1.0)

        grid_state = state.get('gridState', [])
        empty_count = sum(1 for s in grid_state if s is None)
        obs[8] = empty_count / 36.0

        # 유효 조합 수 (서버에서 계산해서 보내줌)
        obs[9] = min(state.get('validCombines', 0) / 54.0, 1.0)

        # 유닛 타입별 보유 수 (그리드 + 필드)
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
        for i in range(NUM_UNIT_TYPES):
            obs[10 + i] = min(counts[i] / 10.0, 1.0)

        return obs

    def get_action_mask(self, state):
        """게임 상태에서 유효 행동 마스크 생성"""
        mask = np.zeros(NUM_ACTIONS, dtype=bool)
        mask[ACTION_WAIT] = True

        grid_state = state.get('gridState', [])
        gold = state.get('gold', 0)
        has_empty = any(s is None for s in grid_state)

        if gold >= GAME_CONFIG['unitSummonCost'] and has_empty:
            mask[ACTION_SUMMON] = True

        # 그리드 유닛 카운트
        grid_counts = {}
        for slot in grid_state:
            if slot and 'key' in slot:
                key = slot['key']
                grid_counts[key] = grid_counts.get(key, 0) + 1

        for key, count in grid_counts.items():
            idx = UNIT_KEY_TO_IDX.get(key)
            if idx is not None:
                mask[ACTION_PLACE_START + idx] = True
                mask[ACTION_SELL_START + idx] = True

        for i, recipe in enumerate(RECIPES):
            a, b = recipe['a'], recipe['b']
            if a == b:
                if grid_counts.get(a, 0) >= 2:
                    mask[ACTION_COMBINE_START + i] = True
            else:
                if grid_counts.get(a, 0) >= 1 and grid_counts.get(b, 0) >= 1:
                    mask[ACTION_COMBINE_START + i] = True

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

        return {'type': 'wait', 'params': {}}

    def run(self, decision_interval=0.02):
        """메인 루프: 상태 수신 → 행동 결정 → 명령 전송

        decision_interval: 행동 간격(초). 5배속 기준 0.02초 권장.
        게임 내 3초(학습 STEP_DURATION) = 5배속 시 실시간 0.6초
        → 0.02초 간격이면 0.6초에 30번 행동 가능
        """
        print("게임 브라우저가 준비될 때까지 대기...")
        print("  브라우저에서 http://localhost:3000/?rl=true 접속하세요")

        while not self.game_ready:
            time.sleep(0.5)

        print("=" * 55)
        print("  에이전트가 게임을 제어합니다!")
        print("  종료: Ctrl+C")
        print("=" * 55)

        step = 0
        last_round = 0
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

            # 새 라운드 알림
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
            action, _ = self.model.predict(obs, action_masks=mask, deterministic=True)

            command = self.action_to_command(int(action))
            self.sio.emit('rl_action', command)

            step += 1
            # 행동 로그 (WAIT 제외)
            if command['type'] != 'wait':
                params_str = ', '.join(f"{k}={v}" for k, v in command.get('params', {}).items())
                print(f"  [{step:>5}] {command['type'].upper():>7}  {params_str}")

            time.sleep(decision_interval)

        print("RL 브릿지 종료")

    def disconnect(self):
        if self.sio.connected:
            self.sio.disconnect()


def main():
    parser = argparse.ArgumentParser(description='RL 브릿지 - 학습된 모델로 실제 게임 제어')
    parser.add_argument('--model', type=str, required=True, help='학습된 모델 경로 (.zip)')
    parser.add_argument('--url', type=str, default='http://localhost:3000', help='서버 URL')
    parser.add_argument('--interval', type=float, default=0.5, help='결정 간격 (초)')
    args = parser.parse_args()

    bridge = RLBridge(args.model)
    try:
        bridge.connect(args.url)
        bridge.run(decision_interval=args.interval)
    except KeyboardInterrupt:
        print("\n사용자 중단")
    finally:
        bridge.disconnect()


if __name__ == '__main__':
    main()
