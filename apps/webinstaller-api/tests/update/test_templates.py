from update import templates


def test_repo_template_is_in_history():
    assert templates.sha256(templates.target_compose()) in templates.history()


def test_target_version(monkeypatch):
    monkeypatch.delenv("INSTALLER_VERSION", raising=False)
    assert templates.target_version() == "dev"
    monkeypatch.setenv("INSTALLER_VERSION", "2.2.0")
    assert templates.target_version() == "2.2.0"


def test_history_includes_revisions_from_before_the_template_moved():
    # Oldest revision, from when the file lived at public/download/.
    assert "8307565f1215b7bb89e2e5bf20bb4c20e945989713308888b7d8a39540217317" in templates.history()
