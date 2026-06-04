from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def ensure_runtime_environment() -> None:
    target_root = _resolve_target_root()
    venv_dir = Path(os.environ.get("DATA_PIPELINE_VENV_DIR", str(target_root / ".venv")))
    venv_python = venv_dir / "bin" / "python"
    if _is_current_python(venv_python):
        return
    if not venv_python.exists():
        install_script = _resolve_install_script()
        env = os.environ.copy()
        env.setdefault("DATA_PIPELINE_DATA_ROOT", str(target_root.parent))
        subprocess.run(["bash", str(install_script)], check=True, env=env)
    os.execv(str(venv_python), [str(venv_python), *sys.argv])


def _resolve_target_root() -> Path:
    env_root = os.environ.get("DATA_PIPELINE_DATA_ROOT")
    if env_root:
        return Path(env_root).resolve() / "data-pipeline"
    workspace_root = Path("/data/workspace/data/my-farm-advisor")
    if workspace_root.exists():
        return workspace_root / "data-pipeline"
    repo_data_root = Path(__file__).resolve().parents[4] / "data" / "my-farm-advisor"
    return repo_data_root / "data-pipeline"


def _resolve_install_script() -> Path:
    env_script = os.environ.get("DATA_PIPELINE_INSTALL_SCRIPT")
    if env_script:
        candidate = Path(env_script).resolve()
        if candidate.exists():
            return candidate
    candidates = [
        Path("/data/workspace/skills/my-farm-advisor/data-pipeline/scripts/install.sh"),
        Path(__file__).resolve().parents[2] / "scripts" / "install.sh",
        Path.cwd() / "skills" / "my-farm-advisor" / "data-pipeline" / "scripts" / "install.sh",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError("Unable to locate data-pipeline install.sh")


def _is_current_python(venv_python: Path) -> bool:
    try:
        current_executable = Path(sys.executable)
        if current_executable == venv_python:
            return True
        return sys.prefix == str(venv_python.parent.parent)
    except FileNotFoundError:
        return False
