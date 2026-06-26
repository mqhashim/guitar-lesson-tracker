from utils.base_manager import BaseManager

# For now, this handles the graph storage, including mapping
# file ids -> file names. Also, should handle saving the graph


class LessonTracker:
    def __init__(self):
        self.base_name = "lesson"
        self.base_manager = BaseManager(self.base_name)

    def _check_loop(self, edge):
        return False

    def _add_edge(self, edge):
        if not self._check_loop(edge):
            # TODO: do something
            raise NotImplementedError

    def _get_parents(self, node):
        raise NotImplementedError

    def _get_children(self, node):
        raise NotImplementedError

    def _get_missing_reqs(self, node):
        raise NotImplementedError

    def _is_complete(self, node):
        raise NotImplementedError

    def _get_open_nodes(self):
        raise NotImplementedError
