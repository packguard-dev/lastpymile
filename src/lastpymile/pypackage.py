from __future__ import annotations
import logging
import os,urllib
import requests
import json
from urllib.parse import quote
from lxml import html

from lastpymile.utils import Utils

class PyPackage:
  """
    Class that represent a python package from pypi.org
  """

  # __RELEASE_TYPE_WHEEL="wheel"
  # __RELEASE_TYPE_SOURCE="source"
  # __RELEASE_TYPE_EGG="egg"
  # __RELEASE_TYPE_UNKNOWN="unknown"

  __PYPI_URL="https://pypi.org"

  __logger=logging.getLogger("lastpymile.PyPackage")

  @staticmethod
  def getAllPackagesList() -> list[str]:
    """
      Static method to retrieve all available packages from pypi.org

        Return (list[str]):
          A list of available packages names on pypi.org
    """
    response = requests.get(PyPackage.__PYPI_URL+"/simple")
    tree = html.fromstring(response.content)
    package_list = [package for package in tree.xpath('//a/text()')]
    return package_list
  
  @staticmethod
  def searchPackage(package_name:str, package_version:str=None, checked:bool=False) -> PyPackage:
    """
      Static method to create a PyPackage from its name and an optional version

        Parameters:
          package_name(str): The name of the package
          package_version(str): The version of the package. May be None, in that case the latest version is retrieved
          checked(bool): If True no exceptions are rasied if the pacakge cannot be found and None is returned. Default is False

        Return (PyPackage):
          The PyPackage object

        Raise (PyPackageNotFoundException): If the package couldn't be found
    """
    safe_name=quote(package_name, safe='')
    safe_ver=quote(package_name, safe='') if package_version is not None else None
    partial_url="{}".format(safe_name) if package_version is None else "{}/{}".format(safe_name,safe_ver)
    url="{}/pypi/{}/json".format(PyPackage.__PYPI_URL,partial_url)
    PyPackage.__logger.debug("Downloading package '{}' data from {}".format(package_name,url))
    try:
      return PyPackage(json.loads(Utils.getUrlContent(url)))
    except Exception as e:
      if checked==True:
        return None
      raise PyPackageNotFoundException(safe_name,safe_ver) from e

  def __init__(self,package_data) -> None: 
    self.package_data=package_data
    self.name=self.package_data["info"]["name"]
    self.version=self.package_data["info"]["version"]
    self.releases=None
    self.git_repository_url=None

  def getName(self) -> str:
    """
      Get the package name

        Return (str):
          the package name
    """
    return self.name

  def getVersion(self):
    """
      Get the package version

        Return (str):
          the package version
    """
    return self.version

  def getRelaeses(self) -> list[PyPackageRelease]:
    """
      Get all the available releases for the package

        Return (list):
          the package name
    """
    if self.releases==None:
      self.__loadReleases()
    return self.releases

  def __loadReleases(self) -> None:
    """
      Extract from the package metadata the list of available release files and store them in the self.releases variable
    """
    self.releases=[]
    for release in self.package_data["releases"][self.version]:
      if "url" in release:
        self.releases.append(PyPackageRelease(self, release["url"],release["packagetype"] if "packagetype" in release else None))

  def getGitRepositoryUrl(self) -> str:
    """
      Get the package git repository url, if found

        Return (str):
          the package git repository url if found, otherwise None
    """
    if self.git_repository_url==None:
      self.__loadSourcesRepository()
    return self.git_repository_url

  def __loadSourcesRepository(self):
    """
      Scan the package metadata searching for a source git repository and stor the value in "self.git_repository_url"
    """
    github_link=None
    urls=self.package_data["info"]["project_urls"] if "project_urls" in self.package_data["info"] else None

    if urls is not None:
      for link_name in urls:
        link=urls[link_name]
        if "github" in link and ( github_link == None or len(github_link) > len(link)):
          if github_link == None:
            github_link=link

    self.git_repository_url=github_link
    
  def __str__(self):
    return "PyPackage[name:{}, version:{}, github:{}, release:({}){}]".format(self.name,self.version,self.githubPageLink,self.releaseLink[1],self.releaseLink[0])


class PyPackageRelease():
  """
    Class that represent a python package release
  """

  def __init__(self, pypackage:PyPackage ,url:str):
    self.pypackage=pypackage
    self.url=url

  def getPyPackage(self) -> PyPackage:
    """
      Get the package owner of this release

        Return (PyPackage):
          the package owner of this release
    """
    self.pypackage

  def getDownloadUrl(self) -> str:
    """
      Get the relase download url

        Return (str):
          the relase download url
    """
    return self.url

  def getReleaseFileName(self) -> str:
    """
      Get the relase file name

        Return (str):
          the relase file name
    """
    return os.path.basename(urllib.parse.urlparse(self.url).path)

  def getReleaseFileType(self) -> str:
    """
      Get the relase file type (In practice the filename extension)

        Return (str):
          the the relase file type 
    """
    return self.getReleaseFileName().split(".")[-1]


##################################
##  EXCEPTIONS
##################################

class LocalArchivePyPackage:
  """
    Represents a Python package backed by a local archive file instead of PyPI.
    Version is intentionally absent — the full git history is used as source reference,
    with no version pinning.
    Provides the same interface as PyPackage so it can be used interchangeably
    with MaliciousCodePackageAnalyzer.
  """

  def __init__(self, archive_path: str, name: str = None, github_url: str = None) -> None:
    """
      Parameters:
        archive_path (str): Absolute or relative path to the local archive file (.whl, .tar.gz, .zip, etc.)
        name (str): Package name override. If None, derived from the archive filename.
        github_url (str): Optional GitHub repository URL used as the source reference.
    """
    self.archive_path = os.path.abspath(archive_path)
    if not os.path.isfile(self.archive_path):
      raise FileNotFoundError("Local archive not found: {}".format(self.archive_path))
    basename = os.path.basename(self.archive_path)
    self.name = name if name else basename.split("-")[0]
    self.github_url = github_url

  def getName(self) -> str:
    return self.name

  def getVersion(self) -> str:
    return None

  def getGitRepositoryUrl(self) -> str:
    return self.github_url

  def getRelaeses(self) -> list:
    """Return a single synthetic release pointing to the local archive."""
    return [LocalArchiveRelease(self)]


class LocalArchiveRelease:
  """
    Synthetic release object that wraps a local archive file.
    Mirrors the interface of PyPackageRelease so AbstractPackageAnalysis can use it.
  """

  def __init__(self, local_package: LocalArchivePyPackage) -> None:
    self.local_package = local_package

  def getPyPackage(self) -> LocalArchivePyPackage:
    return self.local_package

  def getDownloadUrl(self) -> str:
    """Returns None — the file is already local, no download needed."""
    return None

  def getReleaseFileName(self) -> str:
    return os.path.basename(self.local_package.archive_path)

  def getReleaseFileType(self) -> str:
    name = self.getReleaseFileName()
    if name.endswith(".tar.gz"):
      return "gz"
    return name.split(".")[-1]

  def getLocalArchivePath(self) -> str:
    return self.local_package.archive_path


class PyPackageNotFoundException(Exception):
  def __init__(self,package_name,package_version=None):
    if package_version is None:            
      super().__init__("Py package '{}' not found".format(package_name))
    else:
      super().__init__("Py package '{}' with version '{}' not found".format(package_name,package_version),False)