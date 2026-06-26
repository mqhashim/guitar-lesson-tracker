import os
from os import path


# TODO: make singleton


class BaseManager:
    def __init__(self, base: str) -> None:
        self.default_path = os.environ.get("GTT_DEFAULT_PATH", "~/.guitar")
        self.path = path.join(self.default_path, base)
        if not path.isdir(self.path):
            if path.exists(self.path):
                # TODO: proper exception
                raise Exception("file with name already exists")
            os.makedirs(self.path, exist_ok=True)

    # TODO:  figure out how to auto create dirs when opening
    def _get_filename(self, f_name: str):
        return path.join(self.path, f_name)

    def open(self, f_name: str, mode: str = "r"):

        with open(self._get_filename(f_name), mode) as f:
            yield f

    # TODO: finalize
    def register(self, base: str):
        pass

    def reset(self):
        os.removedirs(self.default_path)


# TODO: figure out how to have components initialize themselves, so that the init
# auto figures out which directories/bases are available
# TODO: find a way to ensure paths arent outside default path
# TODO: figure out tagging files?
