# pyright: reportMissingImports=false
from tau_agentmemory.config import Config, load_config


def test_config_defaults_when_file_is_missing(tmp_path):
    assert load_config(environ={}, home=tmp_path) == Config(
        url="http://localhost:3111", secret=None
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
