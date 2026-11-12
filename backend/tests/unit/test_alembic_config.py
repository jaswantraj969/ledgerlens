import warnings
from pathlib import Path

from alembic.config import Config

BACKEND = Path(__file__).resolve().parents[2]


def test_alembic_config_has_a_path_separator_and_no_deprecation_warning() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        config = Config(str(BACKEND / "alembic.ini"))
        assert config.get_main_option("path_separator") == "os"
        assert config.get_prepend_sys_paths_list() == ["src"]
