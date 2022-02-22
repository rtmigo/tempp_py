import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from kitest._errors import GradleRunFailed, UnexpectedOutput


def _replace_in_string(text: str, replacements: dict[str, str]) -> str:
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    return text


def _header(txt: str) -> str:
    return f"<{txt}> ".ljust(80, '-')


def _replace_in_dir(parent: Path, replacements: dict[str, str]):
    for p in parent.rglob('*'):
        if p.is_file():
            old_text = p.read_text()
            new_text = _replace_in_string(old_text, replacements)
            if new_text != old_text:
                p.write_text(new_text)
                print(_header(p.name))
                print(new_text)
                print(_header("/" + p.name))
                print()


def _create_temp_project(src_template_name: str,
                         dst_dir: Path,
                         replacements: dict[str, str]):
    src_dir = Path(__file__).parent / "data" / src_template_name
    if not src_dir.exists():
        raise FileNotFoundError(src_dir)
    if dst_dir.exists():
        raise FileExistsError(dst_dir)
    shutil.copytree(src_dir, dst_dir)
    _replace_in_dir(dst_dir, replacements)


def _get_gradle_run_output(project_dir: Path) -> str:
    result = subprocess.run(["gradle", "run", "-q"],
                            cwd=project_dir,
                            capture_output=True)
    if result.returncode != 0:
        raise GradleRunFailed(
            f"Error code: {result.returncode}\n"
            f"<stdout>{(result.stdout or b'').decode()}</stdout>\n"
            f"<stderr>{(result.stderr or b'').decode()}</stderr>")
    return result.stdout.decode()


class TempDirRemover:
    """When `path` is `None`, creates a temporary directory and removes it
    afterwards.

    When `path` is not `None`, does nothing with the path.
    """
    def __init__(self, path: Optional[Path]):
        self.autoremove = False
        self.path: Optional[Path] = path

    def __enter__(self) -> Path:
        if self.path is not None and self.path.exists():
            raise FileExistsError(self.path)
        if self.path is None:
            self.path = Path(tempfile.mkdtemp())
            self.autoremove = True
        return self.path

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.autoremove:
            if self.path.exists():
                shutil.rmtree(self.path)


def verify_kotlin_sample_project(main_code: str,
                                 repo_url: str,
                                 package_name: str,
                                 expected_output: str,
                                 temp_project_dir: Path = None):
    with TempDirRemover(temp_project_dir) as temp_dir_autoremoved:
        _create_temp_project(src_template_name="dependency_from_github",
                             dst_dir=temp_dir_autoremoved,
                             replacements={"__PACKAGE__": package_name,
                                           "__REPO_URL__": repo_url,
                                           "__MAIN_KT__": main_code})

        output = _get_gradle_run_output(temp_project_dir)
        if output != expected_output:
            raise UnexpectedOutput(output)
