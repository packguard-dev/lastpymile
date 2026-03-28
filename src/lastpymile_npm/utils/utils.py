import urllib.parse
from pathlib import Path
import shutil
import hashlib
import re
import urllib.request
import numpy as np

class Utils(object):

    @staticmethod
    def create_directory(directory):

        dir_path = Path(directory)
        if dir_path.exists() and dir_path.is_dir():
            shutil.rmtree(dir_path)

        Path(directory).mkdir(parents=True, exist_ok=True)

    @staticmethod
    def remove_directory(directory):
        shutil.rmtree(directory, ignore_errors=True)

    @staticmethod
    def create_and_check_existing_directory(directory):
        Path(directory).mkdir(parents=True, exist_ok=True)

    @staticmethod
    def calculate_sha256_checksum(directory, file):
        filename = directory + '/' + file
        sha256_hash = hashlib.sha256()
        with open(filename, "rb") as f:
            # Read and update hash string value in blocks of 4K
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
            # print(filename)
            # print(sha256_hash.hexdigest())
            return sha256_hash.hexdigest()

    @staticmethod
    def normalize_path(url):

        start_index_path = url.rfind('github.com')+10
        old_path = url[start_index_path:]

        new_path = ""
        for c in old_path:
            # Replace characters in path
            if c != ":":
                new_path = new_path + c
            else:
                new_path = new_path + "/"

        url = url.replace(old_path, new_path)

        return url

    @staticmethod
    def normalize_url(url):

        if url.startswith('https://') or url.startswith('http://'):
            return url

        if "@" in url:
            url = url.split("@",1)[1]

        if url.startswith('git+ssh://'):
            url = url.replace('git+ssh://', '')

        if url.startswith('git@'):
            url = url.replace('git@', '')

        if url.startswith('git+'):
            url = url.replace('git+', '')

        if url.startswith('git://'):
            url = url.replace('git://', '')

        if not re.match('(?:http|https)://', url):
            url = 'http://{}'.format(url)

        url = Utils.normalize_path(url)

        return url

    @staticmethod
    def extract_api_calls(line):
        pattern = "([.a-zA-Z0-9i\_]+)\("
        match = re.findall(pattern, line)
        if match:
            return match

        return None

    @staticmethod
    def compute_levenshtein_distance(token1, token2):
        distances = np.zeros((len(token1) + 1, len(token2) + 1))

        for t1 in range(len(token1) + 1):
            distances[t1][0] = t1

        for t2 in range(len(token2) + 1):
            distances[0][t2] = t2

        a = 0
        b = 0
        c = 0

        for t1 in range(1, len(token1) + 1):
            for t2 in range(1, len(token2) + 1):
                if (token1[t1 - 1] == token2[t2 - 1]):
                    distances[t1][t2] = distances[t1 - 1][t2 - 1]
                else:
                    a = distances[t1][t2 - 1]
                    b = distances[t1 - 1][t2]
                    c = distances[t1 - 1][t2 - 1]

                    if (a <= b and a <= c):
                        distances[t1][t2] = a + 1
                    elif (b <= a and b <= c):
                        distances[t1][t2] = b + 1
                    else:
                        distances[t1][t2] = c + 1

        #Utils.printDistances(distances, len(token1), len(token2))
        return distances[len(token1)][len(token2)]