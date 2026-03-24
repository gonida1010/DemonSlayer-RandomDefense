"""
train.py - 귀멸의 칼날 랜덤 디펜스 RL 학습 (하드 모드, 다중 알고리즘)

지원 알고리즘:
  1. MaskablePPO  (sb3-contrib) - On-policy, 액션 마스킹 네이티브
  2. RecurrentPPO (sb3-contrib) - LSTM 기반, 순차 의사결정
  3. DQN          (stable-baselines3) - Off-policy, 경험 리플레이

학습 명령어:
    python train.py --algorithm ppo                          # PPO 새 학습
    python train.py --algorithm ppo --resume                 # PPO 이어서 학습 (best_model 우선)
    python train.py --algorithm ppo --resume model.zip       # PPO 특정 모델부터 이어 학습
    python train.py --algorithm recurrent                    # RecurrentPPO 새 학습
    python train.py --algorithm recurrent --resume           # RecurrentPPO 이어서 학습 (best_model 우선)
    python train.py --algorithm dqn                          # DQN 새 학습
    python train.py --algorithm dqn --resume                 # DQN 이어서 학습 (best_model 우선)
    python train.py --eval models/ppo/best_model.zip         # 모델 평가
    python train.py --algorithm ppo --timesteps 5000000      # 커스텀 타임스텝
"""
import os
import time
import argparse
import numpy as np

from sb3_contrib import MaskablePPO, RecurrentPPO
from sb3_contrib.common.wrappers import ActionMasker
from stable_baselines3 import DQN
from stable_baselines3.common.callbacks import (
    BaseCallback, CallbackList
)
from stable_baselines3.common.vec_env import SubprocVecEnv, DummyVecEnv
from stable_baselines3.common.monitor import Monitor

from game_env import DemonSlayerEnv
import config as cfg


# =====================================================================
# 알고리즘별 리워드 모듈 매핑
# =====================================================================
ALGO_REWARD_MAP = {
    'ppo': 'rewards_ppo',
    'recurrent': 'rewards_recurrent',
    'dqn': 'rewards_dqn',
}


# =====================================================================
# 환경 생성 팩토리
# =====================================================================
def mask_fn(env):
    return env.action_masks()


def make_env(seed=0, reward_module='rewards_ppo', use_masker=True,
             auto_remap_invalid_actions=False):
    """환경 생성 팩토리"""
    def _init():
        env = DemonSlayerEnv(
            reward_module=reward_module,
            auto_remap_invalid_actions=auto_remap_invalid_actions,
        )
        if use_masker:
            env = ActionMasker(env, mask_fn)
        env = Monitor(env)
        env.reset(seed=seed)
        return env
    return _init


# =====================================================================
# 커스텀 콜백: 학습 메트릭 로깅 + 베스트 모델 저장
# =====================================================================
class GameMetricsCallback(BaseCallback):
    """에피소드 종료 시 게임 진행 상황 로깅 + 베스트 모델 자동 저장"""

    def __init__(self, save_dir, algorithm='ppo', verbose=0):
        super().__init__(verbose)
        self.save_dir = save_dir
        self.algorithm = algorithm
        self.episode_rounds = []
        self.episode_rewards = []
        self.episode_remaps = []
        self.episode_count = 0
        self.best_avg_round = 0
        self.best_avg_reward = -float('inf')
        self.best_max_round = 0
        self.best_score = -float('inf')  # 종합 점수 (라운드 + 리워드)
        self.train_start_time = None
        self.total_timesteps_target = 0

    def _on_training_start(self):
        self.train_start_time = time.time()
        self.total_timesteps_target = self.locals.get('total_timesteps', 0)

    def _on_step(self):
        for info in self.locals.get('infos', []):
            if 'episode' in info:
                self.episode_count += 1
                ep_round = info.get('round', 0)
                ep_reward = info['episode']['r']
                self.episode_rounds.append(ep_round)
                self.episode_rewards.append(ep_reward)
                self.episode_remaps.append(info.get('invalid_action_remaps', 0))

                if len(self.episode_rounds) >= 100:
                    recent_rounds = self.episode_rounds[-100:]
                    recent_rewards = self.episode_rewards[-100:]
                    avg_round = np.mean(recent_rounds)
                    max_round = np.max(recent_rounds)
                    avg_reward = np.mean(recent_rewards)
                    avg_remaps = np.mean(self.episode_remaps[-100:])

                    self.logger.record('game/avg_round_100', avg_round)
                    self.logger.record('game/max_round_100', max_round)
                    self.logger.record('game/avg_reward_100', avg_reward)
                    self.logger.record('game/avg_invalid_remaps_100', avg_remaps)
                    self.logger.record('game/total_episodes', self.episode_count)

                    # 베스트 모델 판정: 종합 점수 = avg_round * 10 + avg_reward
                    score = avg_round * 10 + avg_reward
                    is_new_best = False

                    if score > self.best_score:
                        self.best_score = score
                        self.best_avg_round = avg_round
                        self.best_avg_reward = avg_reward
                        is_new_best = True

                    if max_round > self.best_max_round:
                        self.best_max_round = max_round
                        if not is_new_best:
                            is_new_best = True  # 최고 라운드 갱신도 저장

                    self.logger.record('game/best_avg_round', self.best_avg_round)
                    self.logger.record('game/best_avg_reward', self.best_avg_reward)
                    self.logger.record('game/best_max_round', self.best_max_round)
                    self.logger.record('game/best_score', self.best_score)

                    if is_new_best:
                        best_path = os.path.join(self.save_dir, 'best_model')
                        self.model.save(best_path)

                if self.episode_count % cfg.PRINT_INTERVAL == 0:
                    recent_r = self.episode_rounds[-100:]
                    recent_rew = self.episode_rewards[-100:]
                    recent_remaps = self.episode_remaps[-100:]
                    avg_r = np.mean(recent_r)
                    max_r = np.max(recent_r)
                    avg_rew = np.mean(recent_rew)

                    # 시간 & 진행률 계산
                    elapsed = time.time() - self.train_start_time if self.train_start_time else 0
                    current_steps = self.num_timesteps
                    total_target = self.total_timesteps_target

                    if current_steps > 0 and elapsed > 0 and total_target > 0:
                        progress = current_steps / total_target * 100
                        steps_per_sec = current_steps / elapsed
                        remaining_steps = total_target - current_steps
                        eta_sec = remaining_steps / steps_per_sec if steps_per_sec > 0 else 0
                        eta_str = _format_time(eta_sec)
                        elapsed_str = _format_time(elapsed)
                    else:
                        progress = 0
                        eta_str = "계산 중..."
                        elapsed_str = "0s"

                    print(f"\n{'='*65}")
                    print(f"  [{self.algorithm.upper()}] Episode {self.episode_count:,} | "
                          f"Step {current_steps:,}/{total_target:,} ({progress:.1f}%)")
                    print(f"  경과: {elapsed_str} | 예상 잔여: {eta_str}")
                    print(f"  ─── 최근 100 에피소드 ─────────────────────────")
                    print(f"  평균 라운드: {avg_r:.1f} | 최고 라운드: {max_r} | "
                          f"평균 리워드: {avg_rew:.1f}")
                    if recent_remaps:
                        print(f"  평균 Remaps: {np.mean(recent_remaps):.1f}")
                    print(f"  ─── 베스트 모델 ──────────────────────────────")
                    print(f"  Best 평균 라운드: {self.best_avg_round:.1f} | "
                          f"Best 최고 라운드: {self.best_max_round} | "
                          f"Best 평균 리워드: {self.best_avg_reward:.1f}")
                    print(f"  Best Score: {self.best_score:.1f} | "
                          f"저장: {self.save_dir}/best_model.zip")
                    print(f"{'='*65}")

        return True


def _format_time(seconds):
    """초를 읽기 좋은 시간 문자열로 변환"""
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        m, s = divmod(int(seconds), 60)
        return f"{m}m {s}s"
    else:
        h, remainder = divmod(int(seconds), 3600)
        m, s = divmod(remainder, 60)
        return f"{h}h {m}m {s}s"


# =====================================================================
# DQN 전용: 액션 마스킹 래퍼
# =====================================================================
class MaskedDQNWrapper(DQN):
    """DQN에 액션 마스킹을 추가하는 래퍼
    학습 시: 유효하지 않은 행동의 Q값을 -inf로 설정
    """

    def predict(self, observation, state=None, episode_start=None,
                deterministic=False, action_masks=None):
        # 기본 DQN predict 호출
        action, state = super().predict(
            observation, state=state,
            episode_start=episode_start,
            deterministic=deterministic
        )
        # 마스크 적용 (있으면)
        if action_masks is not None:
            import torch
            obs_tensor = torch.as_tensor(observation).float()
            if obs_tensor.dim() == 1:
                obs_tensor = obs_tensor.unsqueeze(0)
            q_values = self.q_net(obs_tensor.to(self.device))
            q_values = q_values.detach().cpu().numpy()

            mask = np.array(action_masks, dtype=bool)
            if mask.ndim == 1:
                mask = mask.reshape(1, -1)
            q_values[~mask] = -np.inf
            action = np.argmax(q_values, axis=1)
            if action.shape[0] == 1:
                action = action[0]

        return action, state


ALGO_CLASSES = {
    'ppo': MaskablePPO,
    'recurrent': RecurrentPPO,
    'dqn': MaskedDQNWrapper,
}


# =====================================================================
# 공통 유틸리티
# =====================================================================
def _resolve_device():
    """GPU 사용 가능 여부 확인"""
    import torch
    device = cfg.DEVICE
    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cuda" and torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        vram = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        return device, f"{gpu_name} ({vram:.1f} GB)"
    return "cpu", "CPU"


def _get_algo_dirs(algorithm):
    """알고리즘별 저장/로그 디렉토리"""
    save_dir = os.path.join(cfg.SAVE_DIR_BASE, algorithm)
    log_dir = os.path.join(cfg.LOG_DIR_BASE, algorithm)
    return save_dir, log_dir


def _find_resume_model(save_dir):
    """이어서 학습할 모델 탐색: best_model 우선, 없으면 final 사용"""
    candidates = [
        os.path.join(save_dir, 'best_model.zip'),
        os.path.join(save_dir, 'demon_slayer_final.zip'),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


# =====================================================================
# MaskablePPO 학습
# =====================================================================
def train_ppo(args, timesteps, device):
    save_dir, log_dir = _get_algo_dirs('ppo')
    os.makedirs(save_dir, exist_ok=True)
    os.makedirs(log_dir, exist_ok=True)
    n_envs = args.n_envs or cfg.N_ENVS
    lr = args.lr or cfg.PPO_CONFIG['learning_rate']
    conf = cfg.PPO_CONFIG

    print(f"  알고리즘: MaskablePPO")
    print(f"  리워드: rewards_ppo.py")
    print(f"  학습률: {lr}")

    if n_envs > 1:
        env = SubprocVecEnv([make_env(seed=i, reward_module='rewards_ppo') for i in range(n_envs)])
    else:
        env = DummyVecEnv([make_env(seed=0, reward_module='rewards_ppo')])

    resume_path = _resolve_resume(args.resume, save_dir)
    if resume_path:
        print(f"  모델 로드: {resume_path}")
        model = MaskablePPO.load(resume_path, env=env, device=device)
        model.learning_rate = lr
    else:
        model = MaskablePPO(
            "MlpPolicy", env,
            learning_rate=lr,
            n_steps=conf['n_steps'],
            batch_size=conf['batch_size'],
            n_epochs=conf['n_epochs'],
            gamma=conf['gamma'],
            gae_lambda=conf['gae_lambda'],
            clip_range=conf['clip_range'],
            ent_coef=conf['ent_coef'],
            vf_coef=conf['vf_coef'],
            max_grad_norm=conf['max_grad_norm'],
            verbose=1,
            device=device,
            tensorboard_log=log_dir,
            policy_kwargs={
                'net_arch': dict(pi=conf['net_arch_pi'], vf=conf['net_arch_vf']),
            },
        )

    callbacks = _build_callbacks(save_dir, n_envs, algorithm='ppo')
    _run_learning(model, timesteps, callbacks)

    final_path = os.path.join(save_dir, 'demon_slayer_final')
    model.save(final_path)
    print(f"\n  버스트 모델: {save_dir}/best_model.zip")
    print(f"  최종 모델: {final_path}.zip")
    env.close()
    return final_path


# =====================================================================
# RecurrentPPO 학습
# =====================================================================
def train_recurrent(args, timesteps, device):
    save_dir, log_dir = _get_algo_dirs('recurrent')
    os.makedirs(save_dir, exist_ok=True)
    os.makedirs(log_dir, exist_ok=True)
    n_envs = args.n_envs or cfg.N_ENVS
    lr = args.lr or cfg.RECURRENT_CONFIG['learning_rate']
    conf = cfg.RECURRENT_CONFIG

    print(f"  알고리즘: RecurrentPPO (LSTM)")
    print(f"  리워드: rewards_recurrent.py")
    print(f"  학습률: {lr}")

    # RecurrentPPO는 ActionMasker 대신 직접 마스킹 처리
    if n_envs > 1:
        env = SubprocVecEnv([
            make_env(
                seed=i,
                reward_module='rewards_recurrent',
                use_masker=False,
                auto_remap_invalid_actions=True,
            )
            for i in range(n_envs)
        ])
    else:
        env = DummyVecEnv([
            make_env(
                seed=0,
                reward_module='rewards_recurrent',
                use_masker=False,
                auto_remap_invalid_actions=True,
            )
        ])

    resume_path = _resolve_resume(args.resume, save_dir)
    if resume_path:
        print(f"  모델 로드: {resume_path}")
        model = RecurrentPPO.load(resume_path, env=env, device=device)
        model.learning_rate = lr
    else:
        model = RecurrentPPO(
            "MlpLstmPolicy", env,
            learning_rate=lr,
            n_steps=conf['n_steps'],
            batch_size=conf['batch_size'],
            n_epochs=conf['n_epochs'],
            gamma=conf['gamma'],
            gae_lambda=conf['gae_lambda'],
            clip_range=conf['clip_range'],
            ent_coef=conf['ent_coef'],
            vf_coef=conf['vf_coef'],
            max_grad_norm=conf['max_grad_norm'],
            verbose=1,
            device=device,
            tensorboard_log=log_dir,
            policy_kwargs={
                'lstm_hidden_size': conf['lstm_hidden_size'],
                'n_lstm_layers': conf['n_lstm_layers'],
                'net_arch': dict(pi=conf['net_arch_pi'], vf=conf['net_arch_vf']),
            },
        )

    callbacks = _build_callbacks(save_dir, n_envs, algorithm='recurrent')
    _run_learning(model, timesteps, callbacks)

    final_path = os.path.join(save_dir, 'demon_slayer_final')
    model.save(final_path)
    print(f"\n  버스트 모델: {save_dir}/best_model.zip")
    print(f"  최종 모델: {final_path}.zip")
    env.close()
    return final_path


# =====================================================================
# DQN 학습
# =====================================================================
def train_dqn(args, timesteps, device):
    save_dir, log_dir = _get_algo_dirs('dqn')
    os.makedirs(save_dir, exist_ok=True)
    os.makedirs(log_dir, exist_ok=True)
    lr = args.lr or cfg.DQN_CONFIG['learning_rate']
    conf = cfg.DQN_CONFIG

    print(f"  알고리즘: DQN (Masked)")
    print(f"  리워드: rewards_dqn.py")
    print(f"  학습률: {lr}")

    # DQN은 병렬 환경 미지원 → 단일 환경
    env = DummyVecEnv([
        make_env(
            seed=0,
            reward_module='rewards_dqn',
            use_masker=False,
            auto_remap_invalid_actions=True,
        )
    ])

    resume_path = _resolve_resume(args.resume, save_dir)
    if resume_path:
        print(f"  모델 로드: {resume_path}")
        model = MaskedDQNWrapper.load(resume_path, env=env, device=device)
        model.learning_rate = lr
    else:
        model = MaskedDQNWrapper(
            "MlpPolicy", env,
            learning_rate=lr,
            buffer_size=conf['buffer_size'],
            learning_starts=conf['learning_starts'],
            batch_size=conf['batch_size'],
            tau=conf['tau'],
            gamma=conf['gamma'],
            train_freq=conf['train_freq'],
            gradient_steps=conf['gradient_steps'],
            target_update_interval=conf['target_update_interval'],
            exploration_fraction=conf['exploration_fraction'],
            exploration_initial_eps=conf['exploration_initial_eps'],
            exploration_final_eps=conf['exploration_final_eps'],
            max_grad_norm=conf['max_grad_norm'],
            verbose=1,
            device=device,
            tensorboard_log=log_dir,
            policy_kwargs={
                'net_arch': conf['net_arch'],
            },
        )

    callbacks = _build_callbacks(save_dir, 1, algorithm='dqn')
    _run_learning(model, timesteps, callbacks)

    final_path = os.path.join(save_dir, 'demon_slayer_final')
    model.save(final_path)
    print(f"\n  버스트 모델: {save_dir}/best_model.zip")
    print(f"  최종 모델: {final_path}.zip")
    env.close()
    return final_path


# =====================================================================
# 공통 헬퍼 함수
# =====================================================================
def _resolve_resume(resume_arg, save_dir):
    """Resume 인자 처리"""
    if resume_arg is None:
        return None
    if resume_arg == '__best__':
        path = _find_resume_model(save_dir)
        if path is None:
            print("  [!] 이어서 학습할 best/final 모델 없음 → 새로 학습 시작")
        return path
    return resume_arg


def _build_callbacks(save_dir, n_envs, algorithm='ppo'):
    """콜백 빌드"""
    return CallbackList([
        GameMetricsCallback(save_dir=save_dir, algorithm=algorithm, verbose=1),
    ])


def _run_learning(model, timesteps, callbacks):
    """학습 실행 (진행률 바 포함)"""
    use_progress_bar = cfg.PROGRESS_BAR
    if use_progress_bar:
        try:
            import tqdm  # noqa: F401
            import rich  # noqa: F401
        except ImportError:
            print("  [!] tqdm/rich 미설치 → 진행률 바 비활성화")
            use_progress_bar = False

    print("\n  학습 시작...")
    model.learn(
        total_timesteps=timesteps,
        callback=callbacks,
        progress_bar=use_progress_bar,
        log_interval=cfg.LOG_INTERVAL,
    )


# =====================================================================
# 평가
# =====================================================================
def evaluate(model_path, algorithm='ppo', n_episodes=20):
    print(f"\n모델 평가: {model_path}")
    print(f"알고리즘: {algorithm}")
    print(f"에피소드: {n_episodes}")
    print("-" * 50)

    reward_module = ALGO_REWARD_MAP.get(algorithm, 'rewards_ppo')
    env = DemonSlayerEnv(
        reward_module=reward_module,
        auto_remap_invalid_actions=(algorithm in {'recurrent', 'dqn'}),
    )

    cls = ALGO_CLASSES.get(algorithm, MaskablePPO)
    model = cls.load(model_path)

    rounds_reached = []
    total_rewards = []

    for ep in range(n_episodes):
        obs, info = env.reset(seed=ep * 100)
        total_reward = 0
        done = False
        lstm_states = None
        episode_start = np.ones(1, dtype=bool)

        while not done:
            mask = env.action_masks()

            if algorithm == 'ppo':
                action, _ = model.predict(obs, action_masks=mask, deterministic=True)
            elif algorithm == 'recurrent':
                action, lstm_states = model.predict(
                    obs, state=lstm_states,
                    episode_start=episode_start,
                    deterministic=True
                )
                episode_start = np.zeros(1, dtype=bool)
            elif algorithm == 'dqn':
                action, _ = model.predict(obs, action_masks=mask, deterministic=True)
            else:
                action, _ = model.predict(obs, deterministic=True)

            obs, reward, terminated, truncated, info = env.step(action)
            total_reward += reward
            done = terminated or truncated

        final_round = info.get('round', 0)
        rounds_reached.append(final_round)
        total_rewards.append(total_reward)

        summary = env.get_game_summary()
        print(f"  Episode {ep+1:2d}: R{final_round:>4d} | "
              f"DPS={summary['field_dps']:>10,.0f} | "
              f"Gold={summary['gold']:>5d} | "
              f"Reward={total_reward:>8.1f}")

    print("-" * 50)
    print(f"평균 라운드: {np.mean(rounds_reached):.1f}")
    print(f"최고 라운드: {np.max(rounds_reached)}")
    print(f"평균 보상: {np.mean(total_rewards):.1f}")


# =====================================================================
# 메인
# =====================================================================
def main():
    parser = argparse.ArgumentParser(
        description='귀멸의 칼날 랜덤 디펜스 RL 학습 (하드 모드, 다중 알고리즘)'
    )
    parser.add_argument(
        '--algorithm', type=str, default='ppo',
        choices=['ppo', 'recurrent', 'dqn'],
        help='학습 알고리즘 선택 (기본: ppo)'
    )
    parser.add_argument(
        '--timesteps', type=int, default=None,
        help=f'총 학습 타임스텝 (기본: {cfg.TOTAL_TIMESTEPS:,})'
    )
    parser.add_argument(
        '--n-envs', type=int, default=None,
        help=f'병렬 환경 수 (기본: {cfg.N_ENVS})'
    )
    parser.add_argument(
        '--lr', type=float, default=None,
        help='학습률 (기본: 알고리즘별 설정)'
    )
    parser.add_argument(
        '--resume', nargs='?', const='__best__', default=None,
        help='이어서 학습 (경로 생략 시 best_model.zip 우선, 없으면 final 모델 사용)'
    )
    parser.add_argument(
        '--eval', type=str, default=None,
        help='평가할 모델 경로 (학습 건너뛰고 평가만)'
    )
    parser.add_argument(
        '--eval-episodes', type=int, default=None,
        help=f'평가 에피소드 수 (기본: {cfg.EVAL_EPISODES})'
    )

    args = parser.parse_args()
    algorithm = args.algorithm
    timesteps = args.timesteps or cfg.TOTAL_TIMESTEPS
    eval_episodes = args.eval_episodes or cfg.EVAL_EPISODES

    if args.eval:
        evaluate(args.eval, algorithm=algorithm, n_episodes=eval_episodes)
        return

    device, device_info = _resolve_device()

    print("=" * 60)
    print("  귀멸의 칼날 랜덤 디펜스 - RL 학습 (하드 모드)")
    print("=" * 60)
    print(f"  디바이스: {device_info}")
    print(f"  총 타임스텝: {timesteps:,}")

    train_fn = {
        'ppo': train_ppo,
        'recurrent': train_recurrent,
        'dqn': train_dqn,
    }[algorithm]

    model_path = train_fn(args, timesteps, device)
    print("\n학습 완료. 평가 시작...")
    evaluate(model_path, algorithm=algorithm, n_episodes=eval_episodes)


if __name__ == '__main__':
    main()
