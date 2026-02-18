from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8000
    playbook_dir: Path = Path("/opt/edulution-installer/playbooks")
    private_data_dir: Path = Path("/opt/edulution-installer/ansible")
    shutdown_delay: int = 5

    class Config:
        env_prefix = "EDULUTION_"


settings = Settings()
