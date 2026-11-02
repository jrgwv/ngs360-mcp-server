"""The stdio token can come from the env, a locked-down file, or the macOS Keychain, never a config file."""

import os
import subprocess

import pytest

from ngs360_mcp_server import client as client_mod
from ngs360_mcp_server.client import load_stored_token

TOKEN_VARS = ("NGS360_API_TOKEN", "NGS360_API_TOKEN_FILE", "NGS360_API_TOKEN_KEYCHAIN")


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for var in TOKEN_VARS:
        monkeypatch.delenv(var, raising=False)


def test_none_configured_is_empty():
    assert load_stored_token() == ""


def test_direct_env_wins(monkeypatch):
    monkeypatch.setenv("NGS360_API_TOKEN", "  key-direct  ")
    monkeypatch.setenv("NGS360_API_TOKEN_FILE", "/does/not/matter")
    assert load_stored_token() == "key-direct"


def test_file_is_read_and_trimmed(monkeypatch, tmp_path):
    f = tmp_path / "key"
    f.write_text("key-from-file\n")
    f.chmod(0o600)
    monkeypatch.setenv("NGS360_API_TOKEN_FILE", str(f))
    assert load_stored_token() == "key-from-file"


def test_world_readable_file_is_refused(monkeypatch, tmp_path):
    f = tmp_path / "key"
    f.write_text("key")
    f.chmod(0o644)
    monkeypatch.setenv("NGS360_API_TOKEN_FILE", str(f))
    with pytest.raises(RuntimeError, match="readable by other users"):
        load_stored_token()


def test_missing_file_explains(monkeypatch, tmp_path):
    monkeypatch.setenv("NGS360_API_TOKEN_FILE", str(tmp_path / "nope"))
    with pytest.raises(RuntimeError, match="cannot be read"):
        load_stored_token()


def test_keychain_lookup(monkeypatch):
    calls = {}

    def fake_run(cmd, **kw):
        calls["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, 0, stdout="key-from-keychain\n", stderr="")

    monkeypatch.setattr(client_mod.subprocess, "run", fake_run)
    monkeypatch.setenv("NGS360_API_TOKEN_KEYCHAIN", "ngs360-mcp")
    assert load_stored_token() == "key-from-keychain"
    # No shell: the item name is a plain argv element.
    assert calls["cmd"][:2] == ["security", "find-generic-password"]
    assert "ngs360-mcp" in calls["cmd"]


def test_keychain_miss_explains(monkeypatch):
    def fake_run(cmd, **kw):
        return subprocess.CompletedProcess(cmd, 44, stdout="", stderr="not found")

    monkeypatch.setattr(client_mod.subprocess, "run", fake_run)
    monkeypatch.setenv("NGS360_API_TOKEN_KEYCHAIN", "absent")
    with pytest.raises(RuntimeError, match="No Keychain item"):
        load_stored_token()
