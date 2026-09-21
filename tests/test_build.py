"""Test source assembly and build-wrapper behavior without a batari Basic install."""

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCES = (
    "rescue_terri.26b",
    "src/gameplay.26b",
    "src/screens.26b",
    "src/music.26b",
    "src/room_exits.26b",
    "src/rooms.26b",
)
FAKE_COMPILER = """#!/bin/sh
set -eu
printf '%s\\n' "$@" > compiler-args.txt
printf '%s\\n' "${FAKE_DIAGNOSTICS:-}"
case "${FAKE_MODE:-success}" in
  fail)
    printf 'partial ROM' > "$1.bin"
    exit 7
    ;;
  missing) exit 0 ;;
  assembly_error)
    printf 'partial ROM' > "$1.bin"
    printf '%s\\n' 'Complete. (5)'
    exit 0
    ;;
esac
cp "$1" "$1.bin"
for ext in asm lst sym; do
  printf '%s\\n' "$ext" > "$1.$ext"
done
for intermediate in bB.asm 2600basic_variable_redefs.h includes.bB; do
  printf '%s\\n' "$intermediate" > "$intermediate"
done
printf '%s\\n' 'Complete. (0)'
"""


class BuildTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="rescue terri build ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "project with spaces"
        self.root.mkdir()
        for name in ("build.sh", "run.sh", *SOURCES):
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, target)
        self.compiler = Path(self.temp.name) / "fake compiler"
        self.compiler.mkdir()
        executable = self.compiler / "2600basic.sh"
        executable.write_text(FAKE_COMPILER)
        executable.chmod(0o755)
        self.combined = self.root / ".cache/combined/rescue_terri.26b"
        self.rom = self.root / "bin/rescue_terri.26b.bin"
        self.a26 = self.root / "bin/rescue_terri.a26"

    def run_game(self, *args, **variables):
        app = Path(self.temp.name) / "Stella App/Stella.app"
        executable = app / "Contents/MacOS/Stella"
        executable.parent.mkdir(parents=True, exist_ok=True)
        executable.touch()
        executable.chmod(0o755)
        opener = self.compiler / "open"
        opener.write_text(
            '#!/bin/sh\nprintf "%s\\n" "$@" > "$FAKE_OPEN_LOG"\n'
            'exit "${FAKE_OPEN_STATUS:-0}"\n'
        )
        opener.chmod(0o755)
        return subprocess.run(
            ["sh", str(self.root / "run.sh"), *args],
            cwd=self.temp.name,
            env={
                **os.environ,
                "bB": str(self.compiler),
                "STELLA_APP": str(app),
                "PATH": str(self.compiler) + os.pathsep + os.environ["PATH"],
                "FAKE_OPEN_LOG": str(self.root / "open-args.txt"),
                **variables,
            },
            capture_output=True,
            text=True,
        )

    def build(self, *args, **variables):
        return subprocess.run(
            ["sh", str(self.root / "build.sh"), *map(str, args)],
            cwd=self.temp.name,
            env={**os.environ, "bB": str(self.compiler), **variables},
            capture_output=True,
            text=True,
        )

    def assert_success(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def compiler_args(self):
        return (self.root / "compiler-args.txt").read_text().splitlines()

    def test_default_build_combines_sources_in_order(self):
        before = {name: (self.root / name).read_bytes() for name in SOURCES}
        expected = b"".join(before.values())
        self.assert_success(self.build())
        self.assertEqual(self.combined.read_bytes(), expected)
        self.assertEqual(self.rom.read_bytes(), expected)
        self.assertEqual(self.a26.read_bytes(), expected)
        self.assertEqual(self.compiler_args(), [".cache/combined/rescue_terri.26b"])
        for name, content in before.items():
            self.assertEqual((self.root / name).read_bytes(), content)
        for ext in ("asm", "lst", "sym"):
            self.assertTrue((self.root / f"bin/rescue_terri.26b.{ext}").is_file())
        for name in ("bB.asm", "2600basic_variable_redefs.h", "includes.bB"):
            self.assertTrue((self.root / ".cache" / name).is_file())
            self.assertFalse((self.root / name).exists())
        start = 1
        records = []
        for name, content in before.items():
            records.append(f"{start}\t{self.root / name}")
            start += len(content.splitlines())
        actual = (self.combined.parent / "source-map.tsv").read_text().splitlines()
        self.assertEqual(actual, records)

    def test_explicit_main_paths_and_compiler_flags(self):
        for args in (
            ("-O",),
            ("rescue_terri.26b", "-O"),
            ("./rescue_terri.26b", "-O"),
            (str(self.root / "rescue_terri.26b"), "-O"),
        ):
            with self.subTest(args=args):
                self.assert_success(self.build(*args))
                self.assertEqual(
                    self.compiler_args(), [".cache/combined/rescue_terri.26b", "-O"]
                )

    def test_standalone_source_does_not_need_fragments(self):
        source = self.root / "standalone.26b"
        source.write_text("main\n  drawscreen\n  goto main\n")
        (self.root / "src/music.26b").unlink()
        self.assert_success(self.build(source))
        self.assertEqual(self.compiler_args(), ["standalone.26b"])
        self.assertEqual(
            (self.root / "bin/standalone.26b.bin").read_bytes(), source.read_bytes()
        )
        self.assertEqual(
            (self.root / "bin/standalone.a26").read_bytes(), source.read_bytes()
        )

    def test_missing_fragment_does_not_compile_stale_combined_source(self):
        self.assert_success(self.build())
        original = self.rom.read_bytes()
        (self.root / "compiler-args.txt").unlink()
        (self.root / "src/music.26b").unlink()
        result = self.build()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Missing source fragment:", result.stderr)
        self.assertFalse((self.root / "compiler-args.txt").exists())
        self.assertEqual(self.rom.read_bytes(), original)
        self.assertEqual(self.a26.read_bytes(), original)

    def test_individual_fragments_are_rejected(self):
        result = self.build("src/music.26b")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Build the whole game", result.stderr)
        self.assertFalse((self.root / "compiler-args.txt").exists())

    def test_missing_entry_source_is_reported(self):
        (self.root / "rescue_terri.26b").unlink()
        result = self.build()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Source file not found", result.stderr)
        self.assertFalse((self.root / "compiler-args.txt").exists())

    def test_diagnostics_map_to_local_file_and_line(self):
        start = 1
        diagnostics = []
        expected = []
        for name in SOURCES:
            for local_line in (1, 5):
                for prefix in ("", "line "):
                    diagnostics.append(f"{prefix}{start + local_line - 1}: Error: test diagnostic")
                    expected.append(f"{self.root / name}:{local_line}: Error: test diagnostic")
            start += len((self.root / name).read_text().splitlines())
        result = self.build(FAKE_DIAGNOSTICS="\n".join(diagnostics), FAKE_MODE="fail")
        self.assertEqual(result.returncode, 7)
        self.assertEqual(result.stdout.splitlines(), expected)
        self.assertEqual(
            (self.root / ".cache/build.log").read_text().splitlines(), diagnostics
        )

    def test_failed_compile_preserves_last_successful_rom(self):
        self.assert_success(self.build())
        original = self.rom.read_bytes()
        result = self.build(FAKE_MODE="fail")
        self.assertEqual(result.returncode, 7)
        self.assertEqual(self.rom.read_bytes(), original)
        self.assertEqual(self.a26.read_bytes(), original)

    def test_missing_rom_is_a_failure_even_with_old_compiler_output(self):
        self.assert_success(self.build())
        original = self.rom.read_bytes()
        self.build(FAKE_MODE="fail")
        self.assertTrue(Path(str(self.combined) + ".bin").exists())
        result = self.build(FAKE_MODE="missing")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Compiler did not produce a ROM", result.stderr)
        self.assertFalse(Path(str(self.combined) + ".bin").exists())
        self.assertEqual(self.rom.read_bytes(), original)
        self.assertEqual(self.a26.read_bytes(), original)

    def test_masked_assembly_error_does_not_publish_partial_rom(self):
        self.assert_success(self.build())
        original = self.rom.read_bytes()
        result = self.build(FAKE_MODE="assembly_error")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("DASM did not report successful assembly", result.stderr)
        self.assertEqual(self.rom.read_bytes(), original)
        self.assertEqual(self.a26.read_bytes(), original)

    def test_fragment_without_final_newline_does_not_merge_statements(self):
        source = self.root / "src/music.26b"
        source.write_text(source.read_text().rstrip("\n"))
        self.assert_success(self.build())
        expected = "".join(
            line + "\n"
            for name in SOURCES
            for line in (self.root / name).read_text().splitlines()
        )
        self.assertEqual(self.combined.read_text(), expected)

    def test_vscode_task_always_builds_the_whole_game(self):
        config = json.loads((ROOT / ".vscode/tasks.json").read_text())
        task = config["tasks"][0]
        self.assertEqual(task["group"], {"kind": "build", "isDefault": True})
        self.assertEqual(task["command"], "/bin/sh")
        self.assertEqual(task["args"], ["${workspaceFolder}/build.sh"])
        self.assertEqual(task["options"]["cwd"], "${workspaceFolder}")
        pattern = task["problemMatcher"]["pattern"]
        match = re.match(pattern["regexp"], "/project with spaces/src/music.26b:12: error")
        self.assertIsNotNone(match)
        self.assertEqual(match.group(pattern["file"]), "/project with spaces/src/music.26b")
        self.assertEqual(match.group(pattern["line"]), "12")
        self.assertEqual(match.group(pattern["message"]), "error")

    def test_run_builds_before_launching_stella_with_complete_rom(self):
        self.assert_success(self.run_game())
        self.assertEqual(self.compiler_args(), [".cache/combined/rescue_terri.26b"])
        self.assertEqual(
            (self.root / "open-args.txt").read_text().splitlines(),
            ["-a", str(Path(self.temp.name) / "Stella App/Stella.app"), str(self.a26)],
        )
        self.assertEqual(self.a26.read_bytes(), self.combined.read_bytes())

    def test_run_does_not_launch_stale_rom_after_failed_build(self):
        self.assert_success(self.build())
        result = self.run_game(FAKE_MODE="fail")
        self.assertEqual(result.returncode, 7)
        self.assertTrue(self.a26.exists())
        self.assertFalse((self.root / "open-args.txt").exists())

    def test_run_reports_missing_stella(self):
        result = self.run_game(STELLA_APP=str(self.root / "missing.app"))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Stella.app not found", result.stderr)
        self.assertFalse((self.root / "compiler-args.txt").exists())
        self.assertFalse((self.root / "open-args.txt").exists())

    def test_run_propagates_launch_failure(self):
        self.assertEqual(self.run_game(FAKE_OPEN_STATUS="9").returncode, 9)

    def test_run_rejects_another_source_filename(self):
        self.assertEqual(self.run_game("standalone.26b").returncode, 2)
        self.assertFalse((self.root / "open-args.txt").exists())

    def test_vscode_run_task_uses_build_and_run_script(self):
        config = json.loads((ROOT / ".vscode/tasks.json").read_text())
        task = next(t for t in config["tasks"] if t["label"] == "Build and Run Rescue Terri")
        self.assertEqual(task["type"], "process")
        self.assertEqual(task["command"], "/bin/sh")
        self.assertEqual(task["args"], ["${workspaceFolder}/run.sh"])
        self.assertEqual(task["options"]["cwd"], "${workspaceFolder}")
        self.assertEqual(task["problemMatcher"], config["tasks"][0]["problemMatcher"])


if __name__ == "__main__":
    unittest.main()
