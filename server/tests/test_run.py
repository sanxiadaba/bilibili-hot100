"""启动器（run.py）的回归测试：子进程重执行与依赖标记。"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import run


class ReexecTests(unittest.TestCase):
    def test_reexec_propagates_child_exit_code(self):
        """用其他解释器重执行时，父进程必须带着子进程退出码结束，不能继续 main。"""
        with (
            patch.object(
                run, "venv_python", return_value=Path(sys.executable).with_name("other-python")
            ),
            patch.object(run.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)),
            self.assertRaises(SystemExit) as raised,
        ):
            run.ensure_venv()

        self.assertEqual(raised.exception.code, 0)


class RequirementsMarkerTests(unittest.TestCase):
    def test_changed_requirements_trigger_install(self):
        """requirements.txt 变化后必须重新 pip install，不能用 import 检查蒙混过关。"""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            venv = root / ".venv"
            (venv / "Scripts").mkdir(parents=True)
            (venv / ".requirements").write_text("stale-digest", encoding="utf-8")
            requirements = root / "requirements.txt"
            requirements.write_text("fastapi==0.140.1\nnew-package==1.0\n", encoding="utf-8")

            calls: list[list[str]] = []

            def fake_run(command, **_kwargs):
                calls.append(list(command))
                return subprocess.CompletedProcess(command, 0)

            with (
                patch.object(run, "VENV", venv),
                patch.object(run, "REQUIREMENTS", requirements),
                patch.object(run, "venv_python", return_value=Path(sys.executable)),
                patch.object(run.subprocess, "run", side_effect=fake_run),
            ):
                run.ensure_venv()

            pip_calls = [command for command in calls if "pip" in command]
            self.assertTrue(pip_calls, calls)
            self.assertEqual(
                (venv / ".requirements").read_text(encoding="utf-8").strip(),
                run.hashlib.sha256(
                    requirements.read_bytes() + f"{sys.version_info[:2]}".encode()
                ).hexdigest(),
            )


if __name__ == "__main__":
    unittest.main()
