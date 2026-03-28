
import requests
import re

import os, sys, tarfile

from pathlib import Path

import logging
logger = logging.getLogger("lastpymile_npm.entities.package")

class Package:

    base_url = "https://registry.npmjs.org/"

    package_metadata_json = ""
    latest_version = ""
    package_name = ""
    artifact_url = ""

    local_filename = ""

    response = ""

    def init_package(self, package_name):
        self.package_name = package_name
        self.response = requests.get(self.base_url + package_name)

    def parse_json(self):
        self.package_metadata_json = self.response.json()

        try:
            self.latest_version = self.package_metadata_json['dist-tags']['latest']
        except Exception as e:
            logger.error("No latest version found")

    def set_latest_version_info(self):
        url = self.base_url + self.package_name + "/" + self.latest_version
        resp = requests.get(url)
        self.package_metadata_json = resp.json()
        artefact_info = self.package_metadata_json['dist']['tarball']
        self.artifact_url = re.findall("(?P<url>https?://[^\s]+)", artefact_info)[0]
        logger.debug("Artefact URL: " + self.artifact_url)

    def set_version(self, version):
        url = self.base_url + self.package_name + "/" + version
        resp = requests.get(url)
        self.package_metadata_json = resp.json()
        artefact_info = self.package_metadata_json['dist']['tarball']
        self.artifact_url = re.findall("(?P<url>https?://[^\s]+)", artefact_info)[0]
        logger.debug("Artefact URL: " + self.artifact_url)


    def get_all_versions_list(self):
        return self.package_metadata_json['versions']

    def download(self, dir_extracted_package):
        url = self.artifact_url

        local_filename = url.split('/')[-1]
        # NOTE the stream=True parameter below
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(local_filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    # If you have chunk encoded response uncomment if
                    # and set chunk_size parameter to None.
                    # if chunk:
                    f.write(chunk)
        self.local_filename = local_filename
        self.extract(local_filename, dir_extracted_package)
        self.delete_zipped_package(local_filename)



    """
    Extracts the tgz package to a specific location
    """
    def extract(self, tar_url, extract_path):
        #print(tar_url)
        if tar_url == "":
            tar_url = self.local_filename

        tar = tarfile.open(tar_url, 'r')
        for item in tar:
            tar.extract(item, extract_path)
            if item.name.find(".tgz") != -1 or item.name.find(".tar") != -1:
                self.extract(item.name, "./" + item.name[:item.name.rfind('/')])

    """
    Deletes the zipped file of the package
    """
    def delete_zipped_package(self, local_filename):
        file_to_rem = Path(local_filename)
        file_to_rem.unlink()