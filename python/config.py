# -*- coding: utf-8 -*-
import os


"""
config.py - 강화학습 설정 파일 (하드 모드 + 다중 알고리즘)

지원 알고리즘:
  1. MaskablePPO  - On-policy, 액션 마스킹 네이티브
  2. RecurrentPPO - LSTM 기반, 순차 의사결정
  3. DQN          - Off-policy, 경험 리플레이

학습 명령어:
  python train.py --algorithm ppo                    # PPO 학습 시작
  python train.py --algorithm ppo --resume           # PPO 이어서 학습
  python train.py --algorithm recurrent              # RecurrentPPO 학습
  python train.py --algorithm recurrent --resume     # RecurrentPPO 이어서 학습
  python train.py --algorithm dqn                    # DQN 학습
  python train.py --algorithm dqn --resume           # DQN 이어서 학습
  python train.py --eval models/ppo/best_model.zip   # 모델 평가
"""

# =============================================================
# 1. 공통 설정
# =============================================================
TOTAL_TIMESTEPS = 100_000_000       # 총 학습 타임스텝
N_ENVS = 6                          # 병렬 환경 수 (CPU 코어에 맞게 조정)
EVAL_EPISODES = 100                 # 평가 에피소드 수
DEVICE = "auto"                     # "auto", "cuda", "cpu"
PROGRESS_BAR = True                 # tqdm 진행률 바
PRINT_INTERVAL = 30000              # 커스텀 콘솔 출력 간격 (episode 기준)
LOG_INTERVAL = 10                   # SB3 표 로그 출력 간격 (iteration 기준)

# =============================================================
# 2. 저장 / 로깅 경로 (알고리즘별 분리)
# =============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_DIR_BASE = os.path.join(BASE_DIR, "models")
LOG_DIR_BASE = os.path.join(BASE_DIR, "tb_logs")

# =============================================================
# 3. MaskablePPO 하이퍼파라미터
# =============================================================
PPO_CONFIG = {
  'learning_rate': 2.5e-4,
  'n_steps': 4096,
  'batch_size': 2048,
  'n_epochs': 8,
  'gamma': 0.995,
  'gae_lambda': 0.97,
  'clip_range': 0.18,
  'clip_range_vf': None,
  'ent_coef': 0.025,
  'vf_coef': 0.45,
  'target_kl': 0.04,
  'max_grad_norm': 0.5,
  'net_arch_pi': [512, 256],
  'net_arch_vf': [512, 256],
}

# =============================================================
# 4. RecurrentPPO 하이퍼파라미터
# =============================================================
RECURRENT_CONFIG = {
    'learning_rate': 2.5e-4,
    'n_steps': 2048,             # LSTM은 더 짧은 롤아웃이 안정적
    'batch_size': 1024,
    'n_epochs': 5,               # LSTM은 적은 에포크
    'gamma': 0.99,
    'gae_lambda': 0.95,
    'clip_range': 0.2,
    'ent_coef': 0.02,
    'vf_coef': 0.5,
    'max_grad_norm': 0.5,
    'lstm_hidden_size': 256,     # LSTM 히든 크기
    'n_lstm_layers': 1,          # LSTM 레이어 수
    'net_arch_pi': [256],        # LSTM 뒤 추가 레이어
    'net_arch_vf': [256],
}

# =============================================================
# 5. DQN 하이퍼파라미터
# =============================================================
DQN_CONFIG = {
    'learning_rate': 1e-4,
    'buffer_size': 500_000,      # 리플레이 버퍼 크기
    'learning_starts': 10_000,   # 학습 시작 전 탐색 스텝
    'batch_size': 256,
    'tau': 0.005,                # 소프트 업데이트 계수
    'gamma': 0.999,
    'train_freq': 4,             # 4 스텝마다 학습
    'gradient_steps': 1,
    'target_update_interval': 1000,
    'exploration_fraction': 0.2,
    'exploration_initial_eps': 1.0,
    'exploration_final_eps': 0.05,
    'max_grad_norm': 10.0,
    'net_arch': [512, 512, 256],  # DQN은 더 깊은 네트워크
}
