"""
train.py - 귀멸의 칼날 랜덤 디펜스 RL 학습 스크립트

MaskablePPO (sb3-contrib)를 사용한 강화학습 훈련.
목표: 스토리 모드 90라운드 클리어.

사용법:
  python train.py                    # 기본 학습 시작
  python train.py --timesteps 2000000  # 타임스텝 지정
  python train.py --resume model.zip   # 이전 모델 이어 학습
"""
import os
import sys
import argparse
import numpy as np

from sb3_contrib import MaskablePPO
from sb3_contrib.common.wrappers import ActionMasker
from stable_baselines3.common.callbacks import (
    BaseCallback, CheckpointCallback, CallbackList
)
from stable_baselines3.common.vec_env import SubprocVecEnv, DummyVecEnv
from stable_baselines3.common.monitor import Monitor

from game_env import DemonSlayerEnv


# =====================================================================
# 행동 마스크 함수 (ActionMasker 래퍼용)
# =====================================================================
def mask_fn(env):
    return env.action_masks()


def make_env(seed=0):
    """환경 생성 팩토리"""
    def _init():
        env = DemonSlayerEnv()
        env = ActionMasker(env, mask_fn)
        env = Monitor(env)
        env.reset(seed=seed)
        return env
    return _init


# =====================================================================
# 커스텀 콜백: 학습 메트릭 로깅
# =====================================================================
class GameMetricsCallback(BaseCallback):
    """에피소드 종료 시 게임 진행 상황 로깅"""

    def __init__(self, verbose=0):
        super().__init__(verbose)
        self.episode_rounds = []
        self.episode_cleared = 0
        self.episode_count = 0
        self.best_avg_round = 0

    def _on_step(self):
        # Monitor에서 에피소드 종료 정보 확인
        for info in self.locals.get('infos', []):
            if 'episode' in info:
                self.episode_count += 1
                ep_round = info.get('round', 0)
                ep_cleared = info.get('game_cleared', False)

                self.episode_rounds.append(ep_round)
                if ep_cleared:
                    self.episode_cleared += 1

                # 최근 100 에피소드 통계
                if len(self.episode_rounds) >= 100:
                    recent = self.episode_rounds[-100:]
                    avg_round = np.mean(recent)
                    max_round = np.max(recent)
                    clear_rate = self.episode_cleared / max(self.episode_count, 1)

                    self.logger.record('game/avg_round_100', avg_round)
                    self.logger.record('game/max_round_100', max_round)
                    self.logger.record('game/clear_rate', clear_rate)
                    self.logger.record('game/total_episodes', self.episode_count)

                    if avg_round > self.best_avg_round:
                        self.best_avg_round = avg_round
                        self.logger.record('game/best_avg_round', self.best_avg_round)

                # 주기적 출력
                if self.episode_count % 50 == 0:
                    recent = self.episode_rounds[-50:]
                    print(f"  [Episode {self.episode_count}] "
                          f"Avg Round: {np.mean(recent):.1f} | "
                          f"Max Round: {np.max(recent)} | "
                          f"Clears: {self.episode_cleared}")

        return True


# =====================================================================
# 학습 설정 및 실행
# =====================================================================
def train(args):
    print("=" * 60)
    print("  귀멸의 칼날 랜덤 디펜스 - RL 학습")
    print("=" * 60)
    print(f"  총 타임스텝: {args.timesteps:,}")
    print(f"  병렬 환경 수: {args.n_envs}")
    print(f"  저장 경로: {args.save_dir}")
    print("=" * 60)

    os.makedirs(args.save_dir, exist_ok=True)
    os.makedirs(args.log_dir, exist_ok=True)

    # 환경 생성 (병렬)
    if args.n_envs > 1:
        env = SubprocVecEnv([make_env(seed=i) for i in range(args.n_envs)])
    else:
        env = DummyVecEnv([make_env(seed=0)])

    # 모델 생성 또는 로드
    if args.resume:
        print(f"기존 모델 로드: {args.resume}")
        model = MaskablePPO.load(args.resume, env=env)
        model.learning_rate = args.lr
    else:
        model = MaskablePPO(
            "MlpPolicy",
            env,
            learning_rate=args.lr,
            n_steps=2048,               # 스텝 수 / 환경
            batch_size=256,             # 미니배치 크기
            n_epochs=10,                # 에포크 수
            gamma=0.998,                # 할인 계수 (장기 보상)
            gae_lambda=0.95,            # GAE 람다
            clip_range=0.2,             # PPO 클립 범위
            ent_coef=0.01,              # 엔트로피 계수 (탐색 유도)
            vf_coef=0.5,                # 가치 함수 계수
            max_grad_norm=0.5,          # 그래디언트 클리핑
            verbose=1,
            tensorboard_log=args.log_dir,
            policy_kwargs={
                'net_arch': dict(pi=[256, 256], vf=[256, 256]),
            },
        )

    # 콜백 설정
    callbacks = CallbackList([
        GameMetricsCallback(verbose=1),
        CheckpointCallback(
            save_freq=max(50000 // args.n_envs, 1000),
            save_path=args.save_dir,
            name_prefix='demon_slayer_rl',
        ),
    ])

    # 학습 시작
    print("\n학습 시작...")
    model.learn(
        total_timesteps=args.timesteps,
        callback=callbacks,
        progress_bar=True,
    )

    # 최종 모델 저장
    final_path = os.path.join(args.save_dir, 'demon_slayer_final')
    model.save(final_path)
    print(f"\n최종 모델 저장: {final_path}.zip")

    env.close()
    return final_path


# =====================================================================
# 평가 (학습된 모델 테스트)
# =====================================================================
def evaluate(model_path, n_episodes=20):
    print(f"\n모델 평가: {model_path}")
    print(f"평가 에피소드: {n_episodes}")
    print("-" * 50)

    env = DemonSlayerEnv()
    model = MaskablePPO.load(model_path)

    rounds_reached = []
    clears = 0
    total_rewards = []

    for ep in range(n_episodes):
        obs, info = env.reset(seed=ep * 100)
        total_reward = 0
        done = False

        while not done:
            mask = env.action_masks()
            action, _ = model.predict(obs, action_masks=mask, deterministic=True)
            obs, reward, terminated, truncated, info = env.step(action)
            total_reward += reward
            done = terminated or truncated

        final_round = info.get('round', 0)
        cleared = info.get('game_cleared', False)
        rounds_reached.append(final_round)
        total_rewards.append(total_reward)
        if cleared:
            clears += 1

        status = "CLEAR!" if cleared else f"R{final_round}"
        summary = env.get_game_summary()
        print(f"  Episode {ep+1:2d}: {status:8s} | "
              f"DPS={summary['field_dps']:>10,.0f} | "
              f"Gold={summary['gold']:>5d} | "
              f"Reward={total_reward:>8.1f}")

    print("-" * 50)
    print(f"평균 라운드: {np.mean(rounds_reached):.1f}")
    print(f"최고 라운드: {np.max(rounds_reached)}")
    print(f"클리어 횟수: {clears}/{n_episodes} "
          f"({100*clears/n_episodes:.1f}%)")
    print(f"평균 보상: {np.mean(total_rewards):.1f}")


# =====================================================================
# 메인 진입점
# =====================================================================
def main():
    parser = argparse.ArgumentParser(
        description='귀멸의 칼날 랜덤 디펜스 RL 학습'
    )
    parser.add_argument(
        '--timesteps', type=int, default=5_000_000,
        help='총 학습 타임스텝 (기본: 5,000,000)'
    )
    parser.add_argument(
        '--n-envs', type=int, default=4,
        help='병렬 환경 수 (기본: 4)'
    )
    parser.add_argument(
        '--lr', type=float, default=3e-4,
        help='학습률 (기본: 3e-4)'
    )
    parser.add_argument(
        '--resume', type=str, default=None,
        help='이어서 학습할 모델 경로 (.zip)'
    )
    parser.add_argument(
        '--save-dir', type=str, default='./models',
        help='모델 저장 디렉토리 (기본: ./models)'
    )
    parser.add_argument(
        '--log-dir', type=str, default='./tb_logs',
        help='TensorBoard 로그 디렉토리 (기본: ./tb_logs)'
    )
    parser.add_argument(
        '--eval', type=str, default=None,
        help='평가할 모델 경로 (학습 건너뛰고 평가만 실행)'
    )
    parser.add_argument(
        '--eval-episodes', type=int, default=20,
        help='평가 에피소드 수 (기본: 20)'
    )

    args = parser.parse_args()

    if args.eval:
        evaluate(args.eval, n_episodes=args.eval_episodes)
    else:
        model_path = train(args)
        print("\n학습 완료. 평가 시작...")
        evaluate(model_path, n_episodes=args.eval_episodes)


if __name__ == '__main__':
    main()
