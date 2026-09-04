"""hotupdate 模块的单元测试(不依赖 GUI 线程循环)。"""
import time
from pathlib import Path

import pytest

from mixdict.core.registry import SourcesRegistry
from mixdict.hotupdate import UPDATE_STYLE, Watcher

pytestmark = pytest.mark.usefixtures("isolated_user_sources")


class TestFilesState:
    """Watcher.get_files_state() 的测试。"""

    def _watcher(self) -> Watcher:
        # Bypass __init__ to avoid starting daemon threads.
        return Watcher.__new__(Watcher)

    def test_recursive_files_with_mtime(self, tmp_path):
        a = tmp_path / "a.css"
        a.write_text("body {}")
        sub = tmp_path / "sub"
        sub.mkdir()
        b = sub / "b.js"
        b.write_text("console.log(1)")

        state = self._watcher().get_files_state(tmp_path)
        assert set(state) == {a, b}
        assert all(isinstance(value, float) for value in state.values())

    def test_empty_directory(self, tmp_path):
        assert self._watcher().get_files_state(tmp_path) == {}


class TestDiffFiles:
    """Watcher.diff_files() 的测试。"""

    def _watcher(self) -> Watcher:
        return Watcher.__new__(Watcher)

    def test_changed_and_added_are_returned(self):
        old = {Path("a"): 1.0, Path("b"): 2.0}
        new = {Path("a"): 1.5, Path("b"): 2.0, Path("c"): 3.0}
        assert set(self._watcher().diff_files(old, new)) == {Path("a"), Path("c")}

    def test_unchanged_not_returned(self):
        old = {Path("a"): 1.0, Path("b"): 2.0}
        new = {Path("a"): 1.0, Path("b"): 2.0}
        assert self._watcher().diff_files(old, new) == []

    def test_removed_files_ignored(self):
        old = {Path("a"): 1.0, Path("b"): 2.0}
        new = {Path("a"): 1.0}
        assert self._watcher().diff_files(old, new) == []


class TestUpdateStyle:
    """UPDATE_STYLE 应能强制浏览器重新加载 CSS。"""

    def test_is_cache_buster(self):
        assert "?t=" in UPDATE_STYLE
        assert "Date.now" in UPDATE_STYLE


class FakeWindow:
    """Record `evaluate_js()` calls instead of talking to a real GUI."""

    def __init__(self):
        self.calls = []

    def evaluate_js(self, js: str):
        self.calls.append(js)


class TestWatchGui:
    """Watcher.watch_gui() 的端到端冒烟(真实 daemon 线程 + 短超时轮询)。"""

    def _start_watcher(self, monkeypatch, tmp_path) -> FakeWindow:
        from mixdict import resources

        fake_window = FakeWindow()
        monkeypatch.setattr(resources, "web_path", lambda name: tmp_path)
        Watcher(fake_window, SourcesRegistry(), interval=0.02)
        return fake_window

    @staticmethod
    def _wait_until(predicate, timeout: float = 2.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if predicate():
                return
            time.sleep(0.02)
        raise AssertionError("Timed out waiting for watcher to react.")

    def test_css_change_triggers_style_reload(self, monkeypatch, tmp_path):
        fake_window = self._start_watcher(monkeypatch, tmp_path)
        (tmp_path / "a.css").write_text("body {}")
        self._wait_until(lambda: any(UPDATE_STYLE in call for call in fake_window.calls))

    def test_js_change_triggers_full_reload(self, monkeypatch, tmp_path):
        # dcedb1c 后:html/js 热更新只整页 reload,不再紧跟 UPDATE_STYLE。
        fake_window = self._start_watcher(monkeypatch, tmp_path)
        (tmp_path / "a.js").write_text("console.log(1)")
        self._wait_until(lambda: any("location.reload()" in call for call in fake_window.calls))
        assert not any(UPDATE_STYLE in call for call in fake_window.calls)


def write_plugin(directory: Path, name: str, reg_name: str) -> Path:
    """Write a minimal user dictionary source file and return its path."""
    directory.mkdir(parents=True, exist_ok=True)
    file = directory / name
    content = (
        "from mixdict.core.sources.base import DictionarySource\n"
        "\n"
        "\n"
        "class Source(DictionarySource):\n"
        "    def __init__(self):\n"
        f"        super().__init__(reg_name={reg_name!r}, name='测试')\n"
        "\n"
        "    def _lookup(self, word: str) -> dict:\n"
        "        return {'word': word}\n"
    )
    file.write_text(content, encoding="utf-8")
    return file


class TestWatchUserSources:
    """Watcher.watch_user_sources() 的端到端测试(真实 daemon 线程 + 短超时轮询)。

    User implementation keeps the scan loop inside the thread (no extracted
    method), so these tests drive it by writing real files and polling.
    """

    @staticmethod
    def _start_watcher(monkeypatch, tmp_path) -> tuple[SourcesRegistry, Path]:
        from mixdict import resources

        user_dir = tmp_path / "user_sources"
        user_dir.mkdir()
        monkeypatch.setattr(resources, "user_sources_dir", lambda: user_dir)
        registry = SourcesRegistry()  # 构造时读到空目录,不含内置之外的源。
        Watcher(FakeWindow(), registry, interval=0.02)
        return registry, user_dir

    @staticmethod
    def _wait_until(predicate, timeout: float = 3.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if predicate():
                return
            time.sleep(0.02)
        raise AssertionError("Timed out waiting for watcher to react.")

    def test_new_file_registers_source(self, monkeypatch, tmp_path):
        registry, user_dir = self._start_watcher(monkeypatch, tmp_path)
        write_plugin(user_dir, "new.py", "NewPlugin")
        self._wait_until(lambda: registry.get("NewPlugin") is not None)

    def test_rename_file_keeps_source_alive(self, monkeypatch, tmp_path):
        # 顺序 bug 回归:旧文件消失且新文件接管同名 reg_name,源不应被误注销。
        registry, user_dir = self._start_watcher(monkeypatch, tmp_path)
        write_plugin(user_dir, "old.py", "Renamed")
        self._wait_until(lambda: registry.get("Renamed") is not None)

        (user_dir / "old.py").unlink()
        write_plugin(user_dir, "new.py", "Renamed")
        # 等到 watcher 完整处理完"删旧 + 增新",再断言源仍存活。
        self._wait_until(
            lambda: registry.user_sources_reg_map.get(user_dir / "new.py") == "Renamed"
            and user_dir / "old.py" not in registry.user_sources_reg_map
        )
        assert registry.get("Renamed") is not None
