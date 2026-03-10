"""
train.py - 귀멸의 칼날 랜덤 디펜스 RL 학습 스크립트

MaskablePPO (sb3-contrib)를 사용한 강화학습 훈련.
목표: 스토리 모드 90라운드 클리어.

사용법:
  python train.py                      # config.py 설정으로 즉시 학습
  python train.py --eval model.zip     # 모델 평가만 실행
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
import config as cfg


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
                if self.episode_count % cfg.PRINT_INTERVAL == 0:
                    recent = self.episode_rounds[-50:]
                    print(f"  [Episode {self.episode_count}] "
                          f"Avg Round: {np.mean(recent):.1f} | "
                          f"Max Round: {np.max(recent)} | "
                          f"Clears: {self.episode_cleared}")

        return True


# =====================================================================
# 학습 설정 및 실행
# =====================================================================
def _resolve_device():
    """GPU 사용 가능 여부 확인 후 디바이스 결정"""
    import torch
    device = cfg.DEVICE
    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cuda" and torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        vram = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        return device, f"{gpu_name} ({vram:.1f} GB)"
    return "cpu", "CPU"


def _find_latest_checkpoint(save_dir):
    """저장 디렉토리에서 가장 최신(스텝 수 높은) 체크포인트를 자동 탐색"""
    import glob, re
    pattern = os.path.join(save_dir, 'demon_slayer_rl_*_steps.zip')
    files = glob.glob(pattern)
    if not files:
        # final 모델도 확인
        final = os.path.join(save_dir, 'demon_slayer_final.zip')
        if os.path.exists(final):
            return final
        return None
    # 파일명에서 스텝 수 추출 후 최대값 선택
    def extract_steps(f):
        m = re.search(r'_(\d+)_steps\.zip$', f)
        return int(m.group(1)) if m else 0
    latest = max(files, key=extract_steps)
    return latest


def train(args):
    timesteps = args.timesteps or cfg.TOTAL_TIMESTEPS
    n_envs = args.n_envs or cfg.N_ENVS
    lr = args.lr or cfg.LEARNING_RATE
    save_dir = args.save_dir or cfg.SAVE_DIR
    log_dir = args.log_dir or cfg.LOG_DIR
    device, device_info = _resolve_device()

    print("=" * 60)
    print("  귀멸의 칼날 랜덤 디펜스 - RL 학습")
    print("=" * 60)
    print(f"  디바이스: {device_info}")
    print(f"  총 타임스텝: {timesteps:,}")
    print(f"  병렬 환경 수: {n_envs}")
    print(f"  학습률: {lr}")
    print(f"  저장 경로: {save_dir}")
    print("=" * 60)

    os.makedirs(save_dir, exist_ok=True)
    os.makedirs(log_dir, exist_ok=True)

    # 환경 생성 (병렬)
    if n_envs > 1:
        env = SubprocVecEnv([make_env(seed=i) for i in range(n_envs)])
    else:
        env = DummyVecEnv([make_env(seed=0)])

    # 모델 생성 또는 로드
    resume_path = args.resume
    if resume_path is not None:
        # --resume만 입력 시 (경로 없음) → 최신 체크포인트 자동 탐색
        if resume_path == '__latest__':
            resume_path = _find_latest_checkpoint(save_dir)
            if resume_path is None:
                print("[!] 저장된 체크포인트 없음 → 새로 학습 시작")
        if resume_path:
            print(f"기존 모델 로드: {resume_path}")
            model = MaskablePPO.load(resume_path, env=env, device=device)
        model.learning_rate = lr
    else:
        model = MaskablePPO(
            "MlpPolicy",
            env,
            learning_rate=lr,
            n_steps=cfg.N_STEPS,
            batch_size=cfg.BATCH_SIZE,
            n_epochs=cfg.N_EPOCHS,
            gamma=cfg.GAMMA,
            gae_lambda=cfg.GAE_LAMBDA,
            clip_range=cfg.CLIP_RANGE,
            ent_coef=cfg.ENT_COEF,
            vf_coef=cfg.VF_COEF,
            max_grad_norm=cfg.MAX_GRAD_NORM,
            verbose=1,
            device=device,
            tensorboard_log=log_dir,
            policy_kwargs={
                'net_arch': dict(pi=cfg.NET_ARCH_PI, vf=cfg.NET_ARCH_VF),
            },
        )

    # 콜백 설정
    callbacks = CallbackList([
        GameMetricsCallback(verbose=1),
        CheckpointCallback(
            save_freq=max(cfg.CHECKPOINT_FREQ // n_envs, 1000),
            save_path=save_dir,
            name_prefix='demon_slayer_rl',
        ),
    ])

    # progress_bar: tqdm + rich 설치 여부에 따라 자동 결정
    use_progress_bar = cfg.PROGRESS_BAR
    if use_progress_bar:
        try:
            import tqdm  # noqa: F401
            import rich  # noqa: F401
        except ImportError:
            print("[!] tqdm/rich 미설치 → 진행률 바 비활성화 (pip install tqdm rich)")
            use_progress_bar = False

    # 학습 시작
    print("\n학습 시작...")
    model.learn(
        total_timesteps=timesteps,
        callback=callbacks,
        progress_bar=use_progress_bar,
    )

    # 최종 모델 저장
    final_path = os.path.join(save_dir, 'demon_slayer_final')
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
        description='귀멸의 칼날 랜덤 디펜스 RL 학습 (설정: config.py)'
    )
    parser.add_argument(
        '--timesteps', type=int, default=None,
        help=f'총 학습 타임스텝 (config 기본: {cfg.TOTAL_TIMESTEPS:,})'
    )
    parser.add_argument(
        '--n-envs', type=int, default=None,
        help=f'병렬 환경 수 (config 기본: {cfg.N_ENVS})'
    )
    parser.add_argument(
        '--lr', type=float, default=None,
        help=f'학습률 (config 기본: {cfg.LEARNING_RATE})'
    )
    parser.add_argument(
        '--resume', nargs='?', const='__latest__', default=None,
        help='이어서 학습 (경로 생략 시 최신 체크포인트 자동 탐색)'
    )
    parser.add_argument(
        '--save-dir', type=str, default=None,
        help=f'모델 저장 디렉토리 (config 기본: {cfg.SAVE_DIR})'
    )
    parser.add_argument(
        '--log-dir', type=str, default=None,
        help=f'TensorBoard 로그 디렉토리 (config 기본: {cfg.LOG_DIR})'
    )
    parser.add_argument(
        '--eval', type=str, default=None,
        help='평가할 모델 경로 (학습 건너뛰고 평가만 실행)'
    )
    parser.add_argument(
        '--eval-episodes', type=int, default=None,
        help=f'평가 에피소드 수 (config 기본: {cfg.EVAL_EPISODES})'
    )

    args = parser.parse_args()
    eval_episodes = args.eval_episodes or cfg.EVAL_EPISODES

    if args.eval:
        evaluate(args.eval, n_episodes=eval_episodes)
    else:
        model_path = train(args)
        print("\n학습 완료. 평가 시작...")
        evaluate(model_path, n_episodes=eval_episodes)


if __name__ == '__main__':
    main()
