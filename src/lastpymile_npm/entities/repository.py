
import requests
import re
import git

from distutils.dir_util import copy_tree

from lastpymile_npm.utils.utils import Utils

import logging
logger = logging.getLogger("lastpymile_npm.entities.repository")

class Repository:

    base_url = "https://registry.npmjs.org/"

    repository_metadata_json = ""
    repository_url = ""

    response = ""
    dir_cloned_repo = ""

    repo = ""

    def init_repository(self, package_name):
        self.response = requests.get(self.base_url + package_name)

    def parse_json(self):
        self.repository_metadata_json = self.response.json()

        try:
            # Extract the URL
            repository_info = self.repository_metadata_json['repository']['url']

            # Check if link contains the github domain
            if "github.com" not in repository_info:
                raise Exception

            # Parse the URL
            self.repository_url = Utils.normalize_url(repository_info)
            logger.debug("JSON response for repository URL: " + str(repository_info))
            logger.debug("Parsed repository URL: " + self.repository_url)

        except Exception as e:
            logger.error("No valid repository link found")
            exit()

    def set_repository_url(self, repository_url):
        self.repository_url = repository_url
        logger.info("Using provided repository URL: " + self.repository_url)

    def clone(self, repo_url, dir_cloned_repo):
        if repo_url=="":
            repo_url = self.repository_url

        self.dir_cloned_repo = dir_cloned_repo

        git.Repo.clone_from(repo_url, self.dir_cloned_repo)
        self.repo = git.Repo(self.dir_cloned_repo)

    def set_repo_directory(self, dir_cloned_repo):
        self.dir_cloned_repo = dir_cloned_repo
        self.repo = git.Repo(self.dir_cloned_repo)

    def copy_from_main_repo_directory(self, dir_cloned_repo_main, dir_new_repo):
        self.dir_cloned_repo = dir_new_repo
        copy_tree(dir_cloned_repo_main, dir_new_repo)
        self.repo = git.Repo(self.dir_cloned_repo)

    def get_all_branches_list(self):
        return git.Repo(self.dir_cloned_repo).remote().refs

    def get_all_tags_list(self):
        return self.repo.tags

    def get_all_commits_from_branch(self, branch, cloned_repo):
        return list(cloned_repo.iter_commits(branch))[:]

    def checkout_commit(self, commit_id):
        self.repo.git.checkout(commit_id)

    def get_all_commits_from_branch(self, branch):
        return list(self.repo.iter_commits(branch))[:]

    def checkout_branch(self, branch):
        self.repo.git.checkout(branch)

    def fetch(self):
        for remote in self.repo.remotes:
            remote.fetch()

    def stash(self):
        self.repo.git.stash()
