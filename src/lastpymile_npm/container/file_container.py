
import json


class FileContainer:

    name = ""
    lines_list = []
    lines = {}
    api_calls = {}

    def read_file_as_dict(self, root, file):
        dict_lines_repository = {}
        count = 1
        import codecs
        with codecs.open(root + "/" + file, 'r', encoding='utf-8', errors='ignore') as f:
            # with open(root + "/" + file) as f:
            for line in f:
                # print(line.rstrip())
                line = line.replace("\t", "  ")
                line = line.strip()
                dict_lines_repository[count] = line.rstrip()
                count = count + 1
        return dict_lines_repository

    def read_file_as_array(self, root, file):

        lines_repository = []

        import codecs
        with codecs.open(root + "/" + file, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                # print(line.rstrip())
                line = line.replace("\t", "  ")
                line = line.strip()
                lines_repository.append(line.rstrip())

        return lines_repository

    def to_dictionary(self):
        return vars(self)