from update import templates


def test_repo_template_is_in_history():
    assert templates.sha256(templates.target_compose()) in templates.history()


def test_target_version(monkeypatch):
    monkeypatch.delenv("INSTALLER_VERSION", raising=False)
    assert templates.target_version() == "dev"
    monkeypatch.setenv("INSTALLER_VERSION", "2.2.0")
    assert templates.target_version() == "2.2.0"
