# -*- coding: utf-8 -*-
"""配置层：路径、凭证、业务常量。凭证从 pipeline/.env 读取，不入库。

业务常量（轮次/维度/分值/提示词）优先读 pipeline/course.yaml；
文件不存在时回退到内置默认值。复用者开新课只改 course.yaml。
"""
import os
from pathlib import Path

try:
    import yaml
except ImportError:  # 无 pyyaml 时只能用内置默认值
    yaml = None

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
SCENARIOS_DIR = DATA_DIR / "scenarios"
SKILLS_DIR = DATA_DIR / "skills"
RESULTS_DIR = DATA_DIR / "results"
AGENTIC_DIR = RESULTS_DIR / "agentic"        # 子进程最终输出 JSON（待 collect）
AGENTIC_WORK_DIR = RESULTS_DIR / "agentic_work"  # 子进程中间文档（揭晓环节素材）
OUTPUT_DIR = BASE_DIR / "output"
ENV_FILE = BASE_DIR / ".env"
COURSE_FILE = BASE_DIR / "course.yaml"


def _load_env(path: Path) -> None:
    """极简 .env 加载：KEY=VALUE，# 开头为注释。已存在的环境变量优先。"""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


_load_env(ENV_FILE)

# --- 飞书应用（复用 PPE-CloudSmart-GiftBox 的应用凭证）---
FEISHU_APP_ID = os.environ.get("FEISHU_APP_ID", "")
FEISHU_APP_SECRET = os.environ.get("FEISHU_APP_SECRET", "")
FEISHU_BASE_URL = os.environ.get("FEISHU_BASE_URL", "https://open.feishu.cn/open-apis")
# 建表后尝试把该用户加为 full_access 协作者，保证链接能打开
OWNER_OPEN_ID = os.environ.get("OWNER_OPEN_ID", "ou_89af8cc25e4b597f19aaf55830a60c30")

# --- LLM（OpenAI 兼容接口）---
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.deepseek.com")
LLM_MODEL = os.environ.get("LLM_MODEL", "deepseek-v4-flash")
LLM_TEMPERATURE = float(os.environ.get("LLM_TEMPERATURE", "0.7"))
LLM_MAX_TOKENS = int(os.environ.get("LLM_MAX_TOKENS", "1200"))

# --- 业务常量（course.yaml 优先，内置默认值兜底）---
_DEFAULT_ROUNDS = {
    "day1": {"dir": "text-based", "label": "城堡情境"},
    "day2": {"dir": "real-based", "label": "现实情境"},
}
_DEFAULT_DIMS = ["自然", "技巧", "远见"]
_DEFAULT_SYSTEM_PROMPT = """你在参与一场组织理解力实验。你将代入一个场景中的主人公，在留白处给出这个人物的回应（话语、动作或简短心理活动，视语境而定）。

有一份「心法」规定了你是谁、你如何理解组织中的权力与人情、你的策略与分寸。你必须完全依照这份心法来回应，而不是依照你自己的偏好。

要求：
- 只输出主人公在留白处的回应本身，不要解释、不要评论、不要复述场景
- 语气与长度与场景语境相称，像一个真人在那个处境里会说的话
- 用中文回应"""
_DEFAULT_USER_TEMPLATE = """【心法】
{skill}

【场景】
{scenario}

请写出主人公在 {placeholder} 处的回应。"""


def _load_course() -> dict:
    if not COURSE_FILE.exists():
        return {}
    if yaml is None:
        raise SystemExit("检测到 course.yaml 但未安装 pyyaml：pip install pyyaml")
    with open(COURSE_FILE, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


_course = _load_course()
# 轮次 → 场景目录与展示名
ROUNDS = _course.get("rounds", _DEFAULT_ROUNDS)
# 评分维度（盲评维度，各 min-max 分）
DIMS = _course.get("dims", _DEFAULT_DIMS)
_score = _course.get("score", {})
SCORE_MIN, SCORE_MAX = int(_score.get("min", 1)), int(_score.get("max", 5))
# 单选选项的方向标注（如 5（非常好）），course.yaml score.labels 可覆盖
SCORE_LABELS = {int(k): str(v) for k, v in
                _score.get("labels", {1: "很差", 2: "较差", 3: "一般", 4: "较好", 5: "非常好"}).items()}
# 简单心法走裸 API 时的提示词模板
_prompts = _course.get("prompts", {})
SYSTEM_PROMPT = _prompts.get("system", _DEFAULT_SYSTEM_PROMPT)
USER_TEMPLATE = _prompts.get("user", _DEFAULT_USER_TEMPLATE)

# 基线（裸模型对照）：一份空壳成品 skill，开关控制是否上场
_baseline = _course.get("baseline", {})
BASELINE_ENABLED = bool(_baseline.get("enabled", False))
BASELINE_KEY = _baseline.get("key", "baseline")

# 场景文件中主人公回应的占位符
RESPONSE_PLACEHOLDER = "[[response]]"


def ensure_dirs() -> None:
    for d in (RESULTS_DIR, OUTPUT_DIR):
        d.mkdir(parents=True, exist_ok=True)


def require_feishu() -> None:
    if not FEISHU_APP_ID or not FEISHU_APP_SECRET:
        raise SystemExit("缺少飞书应用凭证：请在 pipeline/.env 配置 FEISHU_APP_ID / FEISHU_APP_SECRET")


def require_llm() -> None:
    if not LLM_API_KEY:
        raise SystemExit("缺少 LLM 凭证：请在 pipeline/.env 配置 LLM_API_KEY")
