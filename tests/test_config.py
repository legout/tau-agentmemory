# pyright: reportMissingImports=false
from tau_agentmemory.config import Config, load_config


def test_config_defaults_when_file_is_missing(tmp_path):
    assert load_config(environ={}, home=tmp_path) == Config(
        url="http://localhost:3111",
        secret=None,
        project_name=None,
    )


def test_dotenv_values_override_defaults(tmp_path):
    config_dir = tmp_path / ".agentmemory"
    config_dir.mkdir()
    (config_dir / ".env").write_text(
        "# comment\n"
        "AGENTMEMORY_URL=http://file.example/\n"
        "malformed\n"
        "export AGENTMEMORY_SECRET=nope\n"
        "AGENTMEMORY_SECRET=file-secret\n",
        encoding="utf-8",
    )

    assert load_config(environ={}, home=tmp_path) == Config(
        url="http://file.example", secret="file-secret"
    )


def test_project_name_resolves_env_over_dotenv_with_derived_default(tmp_path):
    config_dir = tmp_path / ".agentmemory"
    config_dir.mkdir()
    (config_dir / ".env").write_text(
        "AGENTMEMORY_PROJECT_NAME=file-project\n", encoding="utf-8"
    )

    derived = load_config(environ={}, home=tmp_path)
    overridden = load_config(
        environ={"AGENTMEMORY_PROJECT_NAME": "env-project"}, home=tmp_path
    )
    empty = load_config(environ={"AGENTMEMORY_PROJECT_NAME": ""}, home=tmp_path)

    assert derived.project_name == "file-project"
    assert overridden.project_name == "env-project"
    assert empty.project_name is None  # blank falls back to derived


def test_environment_values_take_individual_precedence(tmp_path):
    config_dir = tmp_path / ".agentmemory"
    config_dir.mkdir()
    (config_dir / ".env").write_text(
        "AGENTMEMORY_URL=http://file.example\nAGENTMEMORY_SECRET=file-secret\n",
        encoding="utf-8",
    )

    assert load_config(
        environ={"AGENTMEMORY_URL": "http://env.example/"}, home=tmp_path
    ) == Config(url="http://env.example", secret="file-secret")


def test_require_https_is_disabled_by_default(tmp_path):
    assert load_config(environ={}, home=tmp_path).require_https is False


def test_only_exact_one_enables_require_https_per_key_precedence(tmp_path):
    config_dir = tmp_path / ".agentmemory"
    config_dir.mkdir()
    (config_dir / ".env").write_text(
        "AGENTMEMORY_REQUIRE_HTTPS=yes\n", encoding="utf-8"
    )

    from_env = load_config(
        environ={"AGENTMEMORY_REQUIRE_HTTPS": "1"}, home=tmp_path
    )
    non_exact = load_config(environ={}, home=tmp_path)
    explicit_zero = load_config(
        environ={"AGENTMEMORY_REQUIRE_HTTPS": "0"}, home=tmp_path
    )

    assert from_env.require_https is True
    assert non_exact.require_https is False
    assert explicit_zero.require_https is False


def test_require_https_resolves_from_dotenv_with_env_precedence(tmp_path):
    config_dir = tmp_path / ".agentmemory"
    config_dir.mkdir()
    (config_dir / ".env").write_text("AGENTMEMORY_REQUIRE_HTTPS=1\n", encoding="utf-8")

    from_file = load_config(environ={}, home=tmp_path)
    overridden = load_config(
        environ={"AGENTMEMORY_REQUIRE_HTTPS": "0"}, home=tmp_path
    )

    assert from_file == Config(
        url="http://localhost:3111", secret=None, require_https=True
    )
    assert overridden.require_https is False
