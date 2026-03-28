import git
import os
import requests
import re

from pathlib import Path
import shutil

from lastpymile_npm.entities.package import Package
from lastpymile_npm.entities.repository import Repository
from lastpymile_npm.utils.utils import Utils

from multiprocessing import Process, Queue, Manager

from lastpymile_npm.container.file_container import FileContainer

from multiprocessing import Pool, Semaphore

from lastpymile_npm.container.dict_container import DictionaryContainer

import json

from lastpymile_npm.encoders.json_encoder_extender import JSONEncoderExtender

from datetime import datetime

import logging
logger = logging.getLogger("lastpymile_npm.lastpymile")

class LastPyMile:

    json_phantom_files = ""
    dict_phantom_files = None

    average_phantom_files_package = 0
    average_phantom_lines_package = 0
    dict_phantom_filenames = None
    dict_phantom_file_extensions = None

    def _compute_commit(self, dir_cloned_repo_main, commit, branch, value, sema, dict_hashes_repository, dict_lines_repository):
        logger.debug("Compute " + str(value) + " started...")
        # Generate the directory in which the repository will be copied from the main one
        dir_new_cloned_repo = dir_cloned_repo_main + str(value)

        # Generate a new temporary directory for the commit
        Utils.create_directory(dir_new_cloned_repo)

        # Copy the main repository into a new folder
        repo_copy = Repository()
        repo_copy.copy_from_main_repo_directory(dir_cloned_repo_main, dir_new_cloned_repo)

        # Checkout commit
        logger.info("Processing commit " + str(commit) + " of branch " + str(branch) + ", in folder: " + repo_copy.dir_cloned_repo)

        try:
            repo_copy.checkout_commit(commit)

            # Compute the hashes of the files in the repository folder
            for root, dirs, files in os.walk(repo_copy.dir_cloned_repo):
                if ".git" not in root:
                    for file in files:
                        # Check if the file is empty or not (we do not process empty files)
                        if os.stat(root + "/" + file).st_size != 0:
                            checksum = Utils.calculate_sha256_checksum(root, file)

                            # global dict_hashes_repository
                            # Check if the key exists in dictionary
                            if checksum not in dict_hashes_repository:
                                dict_hashes_repository[checksum] = file

                            if checksum not in dict_lines_repository:
                                # pass
                                fc = FileContainer()
                                fc.name = file
                                # fc.lines = fc.read_file_as_dict(root, file)
                                fc.lines_list = fc.read_file_as_array(root, file)
                                dict_lines_repository[checksum] = fc
                                # dict_lines_repository[checksum].name = file
                                # dict_lines_repository[checksum].lines = read_file_as_dict(root, file)
                                # print("Checksum: " + str(checksum) + ", for file " + str(file))
                                # print(len(dict_hashes_repository))
        except Exception as e:
            logger.info("Cannot switch to commit " + commit.hexsha)

        # Remove the folder
        # shutil.rmtree(dir_new_cloned_repo, ignore_errors=True)
        Utils.remove_directory(dir_new_cloned_repo)

        sema.release()


    def _scan_all_artifacts_versions_from_registry(self, manager, dir_extracted_package, package_main):

        # Retrieve all the versions of a package
        artifact_versions = package_main.get_all_versions_list()

        dict_artifacts = manager.dict()
        for version in artifact_versions:

            # Generating a directory for the package to be extracted
            dir_artifact_version = dir_extracted_package + "/" + version
            Utils.create_directory(dir_artifact_version)

            # Downloading a specific version of an artifact
            logger.info("Downloading package version " + str(version))
            package_main.set_version(version)
            package_main.download(dir_artifact_version)

            # Collecting all the hashes and lines for a specific version of an artifact
            dict_hashes_artifact = manager.dict()
            dict_lines_artifact = manager.dict()
            dc = DictionaryContainer()
            for root, dirs, files in os.walk(dir_artifact_version):
                for file in files:
                    # Compute hash and add it to the dictionary
                    checksum = Utils.calculate_sha256_checksum(root, file)
                    dict_hashes_artifact[checksum] = file

                    # Building a container for the lines and adding them to the dictionary
                    fc = FileContainer()
                    fc.name = file
                    #fc.lines_list = fc.read_file_as_array(root, file) # Uncomment for list version
                    fc.lines = fc.read_file_as_dict(root, file) # Uncomment for dictionary version
                    dict_lines_artifact[checksum] = fc

                    # Add both dictionaries to the main container
                    dc.dict_hashes_artifact = dict_hashes_artifact
                    dc.dict_lines_artifact = dict_lines_artifact

            dict_artifacts[version] = dc

            # Removing the previously generated directory
            Utils.remove_directory(dir_artifact_version)

        return dict_artifacts


    def _scan_specific_local_artifact_version(self, manager, version, specific_artifact_package, dir_extracted_package, package_main):

        dict_artifacts = manager.dict()

        # Generating a directory for the package to be extracted
        dir_artifact_version = dir_extracted_package + "/" + version
        Utils.create_directory(dir_artifact_version)

        package_main.extract(specific_artifact_package, dir_artifact_version)

        # Collecting all the hashes and lines for a specific version of an artifact
        dict_hashes_artifact = manager.dict()
        dict_lines_artifact = manager.dict()
        dc = DictionaryContainer()
        for root, dirs, files in os.walk(dir_artifact_version):
            for file in files:
                # Compute hash and add it to the dictionary
                checksum = Utils.calculate_sha256_checksum(root, file)
                dict_hashes_artifact[checksum] = file

                # Building a container for the lines and adding them to the dictionary
                fc = FileContainer()
                fc.name = file
                #fc.lines_list = fc.read_file_as_array(root, file) # Uncomment for list version
                fc.lines = fc.read_file_as_dict(root, file) # Uncomment for dictionary version
                dict_lines_artifact[checksum] = fc

                # Add both dictionaries to the main container
                dc.dict_hashes_artifact = dict_hashes_artifact
                dc.dict_lines_artifact = dict_lines_artifact

        dict_artifacts[version] = dc

        # Removing the previously generated directory
        Utils.remove_directory(dir_artifact_version)

        return dict_artifacts

    def _find_phantom_lines(self, lines_artifact_version, dict_lines_repository):
        phantom_lines_for_file = []

        # Checking every line in the artifact with the lines in the repository
        for line in lines_artifact_version:
            if line != '':
                found = False
                for key in dict_lines_repository.keys():
                    fc = dict_lines_repository.get(key)
                    # print("Checking " + str(fc.lines_list) + " with " + line)
                    if line in fc.lines_list:
                        found = True
                        break

                if not found:
                    phantom_lines_for_file.append(line)

        return phantom_lines_for_file

    def _find_phantom_lines_dict(self, lines_artifact_version, dict_lines_repository):
        phantom_lines_for_file = {}

        # Checking every line in the artifact with the lines in the repository
        for line_num in lines_artifact_version.keys():
            line = lines_artifact_version[line_num]
            if line != '':
                found = False
                for key in dict_lines_repository.keys():
                    fc = dict_lines_repository.get(key)
                    # print("Checking " + str(fc.lines_list) + " with " + line)
                    if line in fc.lines_list:
                        found = True
                        break

                if not found:
                    phantom_lines_for_file[line_num] = line

        return phantom_lines_for_file

    def get_json_phantom_files(self):
        return self.json_phantom_files

    def run(self, package_name, specific_repository_url, specific_artifact_package, package_version):

        # Start time of the processing
        start_time = datetime.now()

        # Package and repository metadata
        package_main = Package()
        repo_main = Repository()

        dir_extracted_package = "../package_extracted"

        logger.info("The package to be analyzed: " + package_name)

        """
            PROCESSING ALL THE COMMITS OF THE REPOSITORY AND COLLECTING HASHES AND LINES
        """

        # Get the information about the location of the repository
        repo_main.init_repository(package_name)
        if specific_repository_url is None:
            repo_main.parse_json()
        else:
            repo_main.set_repository_url(specific_repository_url)

        logger.info("Github URL of the package: " + repo_main.repository_url)

        dir_main = "../repocloned"
        dir_cloned_repo_main = dir_main + '/repo'

        # Generate the directory in which the repository will be cloned
        Utils.create_directory(dir_cloned_repo_main)
        # Utils.create_directory_alt(dir_cloned_repo_main)

        # Clone the repository
        # repo_main.clone("https://SimoneScalco@bitbucket.org/SimoneScalco/prova.git", dir_cloned_repo_main)
        repo_main.clone("", dir_cloned_repo_main)
        logger.debug("Cloning from " + repo_main.repository_url)

        # Get the list of branches of the repository
        branches_list = repo_main.get_all_branches_list()
        logger.debug("Branches list: " + str(branches_list))

        tags_list = repo_main.get_all_tags_list()
        logger.debug("Tags: " + str(tags_list))

        # New manager for the shared dictionaries (it helps by managing a shared dictionary among all processes)
        manager = Manager()

        # Dictionaries for storing the hashes and lines of the repository
        dict_hashes_repository = manager.dict()
        dict_lines_repository = manager.dict()

        # Array of already processed commits
        processed_commits = []

        # Procedure for collecting hashes and lines of all files in all commits
        value = 0
        for branch in branches_list:
            #if value == 1:
            #    break
            if str(branch) != "origin/HEAD":
                logger.info("Processing branch " + str(branch))

                # Checking out a specific branch
                repo_main.checkout_branch(branch)
                commits = repo_main.get_all_commits_from_branch(branch)

                # pool = Pool(2)  # use all available cores, otherwise specify the number you want as an argument
                # print("Pool initialized")
                # Semaphore for multiprocessing
                sema = Semaphore(30)

                # Processing each commit of the branch in parallel
                processes = []
                for commit in commits:
                    #if value == 1:
                    #    break
                    # Check if the commit is already processed
                    if commit.hexsha not in processed_commits:

                        processed_commits.append(commit.hexsha)
                        value = value + 1

                        if value % 30 == 0:
                            for p in processes:
                                p.join()
                                p.close()
                                processes.remove(p)
                            try:
                                repo_main.checkout_commit(commit)
                            except Exception as e:
                                logger.error("Cannot checkout commit " + commit.hexsha)

                        sema.acquire()
                        p = Process(target=self._compute_commit, args=(
                            dir_cloned_repo_main, commit, branch, value, sema, dict_hashes_repository,
                            dict_lines_repository))
                        processes.append(p)
                        p.start()

                # repo_main.stash()
                # pool.close()
                # pool.join()

                # for p in processes:
                #    p.start()

                for p in processes:
                    # print("Process " + str(p.name) + " joined")
                    p.join()


        """
            COLLECT HASHES AND LINES FOUND IN EACH VERSION OF AN ARTIFACT
        """
        # Get the information about the latest version available for the package
        package_main.init_package(package_name)
        package_main.parse_json()
        logger.debug("Package " + package_name + ", latest version available: " + package_main.latest_version)

        # Generates the new folder for storing the extracted package
        Utils.create_directory(dir_extracted_package)

        if specific_artifact_package is not None:
            # Collect hashes and lines found in a specific version of an artifact provided locally by the user
            dict_artifacts = self._scan_specific_local_artifact_version(manager, package_version, specific_artifact_package, dir_extracted_package, package_main)

        else:
            # Collect hashes and lines found in each version of a package found in the NPM registry
            dict_artifacts = self._scan_all_artifacts_versions_from_registry(manager, dir_extracted_package, package_main)

        # Remove directory of the extracted artifacts
        Utils.remove_directory(dir_extracted_package)
        Utils.remove_directory(dir_main)

        """
            PRINTING THE HASHES OF THE REPOSITORY AND THE HASHES OF THE ARTIFACT
        """
        logger.debug("")
        logger.debug("==================== HASHES OF THE REPOSITORY ====================")
        for hash in dict_hashes_repository.keys():
            logger.debug(hash + " " + str(dict_hashes_repository[hash]))

        for version in dict_artifacts.keys():
            logger.debug("")
            logger.debug("==================== HASHES OF ARTIFACT " + version + " ====================")

            dict_hashes_artifact_version = dict_artifacts[version].dict_hashes_artifact

            for hash in dict_hashes_artifact_version.keys():
                logger.debug(hash + " " + str(dict_hashes_artifact_version[hash]))

        """for version in dict_artifacts.keys():
            print("\n\n==================== LINES OF ARTIFACT " + version + " ====================")
    
            dict_lines_artifact_version = dict_artifacts[version].dict_lines_artifact
    
            for hash in dict_lines_artifact_version.keys():
                fc = dict_lines_artifact_version.get(hash)
                if fc.name == "package.json":
                    print(hash + " " + fc.name + ", " + str(fc.lines_list))
    
        print("\n\n==================== LINES IN REPOSITORY ====================")
        for hash in dict_lines_repository.keys():
            fc = dict_lines_repository.get(hash)
            lines_list = fc.lines_list
            if fc.name == "package.json":
                print(hash)
                print(lines_list)"""

        """
            FINDING NEW HASHES AND LINES IN ARTIFACTS
        """
        self.dict_phantom_files = manager.dict()
        for version in dict_artifacts.keys():

            # Extract the lines in a specific version of an artifact
            logger.info("Processing version " + version)
            dict_lines_artifact_version = dict_artifacts[version].dict_lines_artifact

            # Process the hashes in the artifact version
            self.dict_phantom_files[version] = manager.dict()
            for hash in dict_lines_artifact_version.keys():

                logger.info("Processing file " + hash + ", " + dict_lines_artifact_version[hash].name)
                # If the hash is not found in the repository dictionary, then it is a phantom file
                if hash not in dict_hashes_repository:
                    #lines_artifact_version = dict_lines_artifact_version[hash].lines_list
                    lines_artifact_version = dict_lines_artifact_version[hash].lines

                    # Checking phantom lines in the artifact version
                    logger.info("Finding phantom lines for file: " + hash + ", " + dict_lines_artifact_version[hash].name)
                    #phantom_lines_for_file = self._find_phantom_lines(lines_artifact_version, dict_lines_repository) # Uncomment for array version
                    phantom_lines_for_file = self._find_phantom_lines_dict(lines_artifact_version, dict_lines_repository) # Uncomment for dictionary version

                    # Building a container for the new set of phantom hash and lines
                    fc = FileContainer()
                    fc.name = dict_lines_artifact_version[hash].name
                    #fc.lines_list = phantom_lines_for_file # Uncomment for array version
                    fc.lines = phantom_lines_for_file # Uncomment for dictionary version

                    logger.info("Extracting API calls from file " + hash + ", " + fc.name)
                    #api_calls = {}
                    for key in phantom_lines_for_file.keys():
                        line = phantom_lines_for_file.get(key)
                        api_call_extracted = Utils.extract_api_calls(line)

                        api_calls = []
                        if api_call_extracted is not None:
                            #api_calls[key] = api_call_extracted
                            for single_api_call_extracted in api_call_extracted:
                                api_calls.append(single_api_call_extracted)

                        phantom_lines_for_file[key] = [phantom_lines_for_file[key]]
                        phantom_lines_for_file[key].extend(api_calls)

                    #fc.api_calls = api_calls

                    self.dict_phantom_files[version][hash] = fc

            #for hash in dict_phantom_files[version].keys():
            #    fc = dict_phantom_files[version][hash]
            #    print(hash + " " + fc.name)

        """
            PRINTING THE PHANTOM FILE HASHES
        """
        for version in self.dict_phantom_files.keys():
            logger.debug("")
            logger.debug("==================== UNIQUE HASHES IN ARTIFACT " + version + " ====================")
            for hash in self.dict_phantom_files[version].keys():
                fc = self.dict_phantom_files[version][hash]
                logger.debug(hash + " " + fc.name)
                #logger.debug("Phantom lines: " + str(len(fc.lines_list))) # Uncomment for array version
                logger.debug("Phantom lines: " + str(len(fc.lines.keys()))) # Uncomment for dictionary version

        # Calculating processing time
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()


        """
            STATISTICS AREA
        """
        logger.debug("")
        logger.info("========================= STATISTICS =========================")
        logger.info("Number of tags: " + str(len(tags_list)))
        logger.info("Processed commits: " + str(len(processed_commits)))

        # Average phantom files in a package and average phantom lines in a package
        count_phantom_files = 0
        count_phantom_lines = 0
        # Counting the total number of phantom files
        for version in self.dict_phantom_files.keys():

            count_phantom_files = count_phantom_files + len(self.dict_phantom_files[version].keys())

            # Counting the total number of phantom lines
            for hash in self.dict_phantom_files[version].keys():
                fc = self.dict_phantom_files[version][hash]
                #count_phantom_lines = count_phantom_lines + len(fc.lines_list) # Uncomment for array version
                count_phantom_lines = count_phantom_lines + len(fc.lines) # Uncomment for dictionary version
            # print("Count phantom files: " + str(count_phantom_files))

        # Calculating the average phantom files in a package and average phantom lines in a package
        self.average_phantom_files_package = count_phantom_files / len(self.dict_phantom_files.keys())
        self.average_phantom_lines_package = count_phantom_lines / len(self.dict_phantom_files.keys())
        logger.info("Total phantom files: " + str(count_phantom_files))
        logger.info("Total phantom lines: " + str(count_phantom_lines))
        logger.info("Average phantom files: " + str(self.average_phantom_files_package))
        logger.info("Average phantom lines: " + str(self.average_phantom_lines_package))

        # Most common phantom files (based on filenames or file extentions)
        self.dict_phantom_filenames = manager.dict()
        self.dict_phantom_file_extensions = manager.dict()
        for version in self.dict_phantom_files.keys():
            for hash in self.dict_phantom_files[version].keys():

                fc = self.dict_phantom_files[version][hash]

                # Split filename and file extension
                filename, file_extension = os.path.splitext(fc.name)

                # Check if filename is not in the dictionary of filenames
                if filename not in self.dict_phantom_filenames.keys():
                    self.dict_phantom_filenames[filename] = 0

                # Check if file extension is not in the dictionary of file extensions
                if file_extension not in self.dict_phantom_file_extensions.keys():
                    self.dict_phantom_file_extensions[file_extension] = 0

                # Update the filename and file extension entries in the dictionary
                self.dict_phantom_filenames[filename] = self.dict_phantom_filenames[filename] + 1
                self.dict_phantom_file_extensions[file_extension] = self.dict_phantom_file_extensions[file_extension] + 1

        for filename in self.dict_phantom_filenames.keys():
            logger.info("Phantom files for filename '" + filename + "': " + str(self.dict_phantom_filenames[filename]))

        for file_extension in self.dict_phantom_file_extensions.keys():
            logger.info("Phantom files for extension '" + file_extension + "': " + str(self.dict_phantom_file_extensions[file_extension]))


        """
            WRITING THE OUTPUT FILE
        """

        # Building main output dictionary
        dict_output = manager.dict()
        dict_output['start_time'] = start_time.isoformat()
        dict_output['end_time'] = end_time.isoformat()
        dict_output['processing_time'] = processing_time
        dict_output['total_phantom_files'] = count_phantom_files
        dict_output['total_phantom_lines'] = count_phantom_lines
        dict_output['average_phantom_files_per_package'] = self.average_phantom_files_package
        dict_output['average_phantom_lines_per_package'] = self.average_phantom_lines_package
        dict_output['phantom_files_per_filename'] = self.dict_phantom_filenames
        dict_output['phantom_files_per_extension'] = self.dict_phantom_file_extensions
        dict_output['number_of_tags'] = len(tags_list)
        dict_output['number_of_branches'] = len(branches_list)
        dict_output['package'] = self.dict_phantom_files

        # Checking and eventually generating the output directory
        output_directory = "results/"
        Utils.create_and_check_existing_directory(output_directory)

        # Writing the output JSON into a file
        output_file_path = output_directory + package_name + ".json"
        with open(output_file_path, "w") as output_file:
            json.dump(dict_output, output_file, cls=JSONEncoderExtender, sort_keys=False, indent=4)

            logger.info("The output can be found at: " + os.path.abspath(output_file_path))