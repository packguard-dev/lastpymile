
import multiprocessing, json
from lastpymile_npm.container.file_container import FileContainer


class JSONEncoderExtender(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, multiprocessing.managers.DictProxy):
            return dict(o)

        if isinstance(o, FileContainer):
            return o.to_dictionary()

        return json.JSONEncoder.default(self, o)