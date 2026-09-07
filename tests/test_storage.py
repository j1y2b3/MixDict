"""Storage(用户设置持久化)测试:把配置目录指向 tmp_path,避免碰真实用户配置。"""
import json

import pytest


@pytest.fixture
def storage_cls(monkeypatch, tmp_path):
    """把 resources 使用的配置目录指到 tmp_path,返回隔离的 Storage 类。"""
    import platformdirs

    monkeypatch.setattr(platformdirs, "user_config_path", lambda *a, **k: tmp_path)
    from mixdict.storage import Storage

    return Storage


class TestStorage:
    def test_init_creates_config_file(self, storage_cls, tmp_path):
        storage_cls()
        assert (tmp_path / "config.json").exists()

    def test_get_missing_returns_default(self, storage_cls):
        s = storage_cls()
        assert s.get("nope") is None
        assert s.get("nope", 42) == 42

    def test_set_get(self, storage_cls):
        s = storage_cls()
        s.set("current_source", "Youdao")
        assert s.get("current_source") == "Youdao"

    def test_save_then_reload(self, storage_cls):
        s1 = storage_cls()
        s1.set("source", "FreeDict")
        s1.set("n", 3)
        s1.save()

        s2 = storage_cls()  # 重新从磁盘读入
        assert s2.get("source") == "FreeDict"
        assert s2.get("n") == 3

    def test_corrupt_json_ignored(self, storage_cls, tmp_path):
        (tmp_path / "config.json").write_text("{not json!!", encoding="utf-8")
        s = storage_cls()
        assert s.get("anything") is None

    def test_empty_file_ok(self, storage_cls, tmp_path):
        (tmp_path / "config.json").write_text("", encoding="utf-8")
        s = storage_cls()
        assert s.get("anything") is None

    def test_non_dict_root_resets(self, storage_cls, tmp_path):
        (tmp_path / "config.json").write_text("[1, 2]", encoding="utf-8")
        s = storage_cls()
        assert s.get("anything") is None

    def test_non_string_key_handling(self, storage_cls):
        s = storage_cls()
        s.set(123, "v")  # 默认转字符串
        assert s.get("123") == "v"
        s.set(456, "v2", check_key=True)  # check_key=True 时跳过非 str
        assert s.get("456") is None

    def test_backup_previous_on_save(self, storage_cls, tmp_path):
        s1 = storage_cls()
        s1.set("a", 1)
        s1.save()

        s1.set("b", 2)
        s1.save()

        bak = tmp_path / "config.bak.json"
        assert bak.exists()
        assert json.loads(bak.read_text(encoding="utf-8")) == {"a": 1}
