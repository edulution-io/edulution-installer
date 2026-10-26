from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8000
    edulution_config_path: Path = Path("/var/lib/edulution/binduser-config.json")
    idle_shutdown: float = 1800
    playbook_dir: Path = Path("/opt/edulution-installer/playbooks")
    private_data_dir: Path = Path("/opt/edulution-installer/ansible")
    api_token_file: Path = Path("/opt/edulution-installer/api-token")

    class Config:
        env_prefix = "EDULUTION_"


settings = Settings()
