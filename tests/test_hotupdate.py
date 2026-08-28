"""hotupdate 模块的单元测试(不依赖 GUI 线程循环)。"""
from pathlib import Path

from simplenetdict.hotupdate import UPDATE_STYLE, Watcher


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


class TestWatchGui:
    """Watcher.watch_gui() 循环行为测试(短间隔 + 临时 web 目录)。"""

    def test_gui_changes_trigger_reloads(self, monkeypatch, tmp_path):
        import time

        from simplenetdict import resources
        from simplenetdict.hotupdate import UPDATE_STYLE, Watcher

        calls = []
        fake_window = type("FakeWindow", (), {"evaluate_js": lambda self, js: calls.append(js)})()
        monkeypatch.setattr(resources, "web_path", lambda name: tmp_path)
        Watcher(fake_window, interval=0.05)

        # CSS 变更只触发样式重载。
        (tmp_path / "a.css").write_text("body {}")
        time.sleep(0.3)
        assert any(UPDATE_STYLE in call for call in calls)

        # HTML 变更触发整页刷新。
        (tmp_path / "b.html").write_text("<html></html>")
        time.sleep(0.3)
        assert any("location.reload()" in call for call in calls)

    def test_js_change_triggers_full_reload(self, monkeypatch, tmp_path):
        import time

        from simplenetdict import resources
        from simplenetdict.hotupdate import UPDATE_STYLE, Watcher

        calls = []
        fake_window = type("FakeWindow", (), {"evaluate_js": lambda self, js: calls.append(js)})()
        monkeypatch.setattr(resources, "web_path", lambda name: tmp_path)
        Watcher(fake_window, interval=0.05)

        # JS 变更触发整页刷新(而非仅样式重载)。
        (tmp_path / "a.js").write_text("console.log(1)")
        time.sleep(0.3)
        assert any("location.reload()" in call for call in calls)
        assert not any(UPDATE_STYLE in call for call in calls)
