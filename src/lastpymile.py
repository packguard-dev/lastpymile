from argparse import ArgumentParser,ArgumentTypeError
import logging, coloredlogs
import os, pathlib
import json

from lastpymile.utils import Utils
from lastpymile.maliciouscodepackageanalyzer import MaliciousCodePackageAnalyzer


class LastPyMileApplication():
  
  @staticmethod
  def __packageType(package):
    if len(package.split(":")) >2:
      raise ArgumentTypeError("Invlaid package name ")
    return package
  
  @staticmethod
  def __logLevelType(x):
    x = int(x)
    if x==0:
      return 100
    elif x==1:
      return logging.CRITICAL
    elif x==2:
      return logging.ERROR
    elif x==3:
      return logging.WARNING
    elif x==4:
      return logging.INFO
    elif x==5:
      return logging.DEBUG
    else:
      raise ArgumentTypeError("Log level must be between 0 and 5")
  
  def __init__(self):
    parser = ArgumentParser()

    # --- target: either a PyPI package name OR a local archive ---
    target_group = parser.add_mutually_exclusive_group(required=True)
    target_group.add_argument(
      'package',
      type=str,
      nargs='?',
      help='PyPI package name, optionally with version: <package_name>:<package_version>. '
           'If no version is specified the latest version is retrieved. '
           'Mutually exclusive with --archive.',
    )
    target_group.add_argument(
      '-a', '--archive',
      type=str,
      default=None,
      metavar='ARCHIVE_PATH',
      help='Path to a local package archive file (.whl, .tar.gz, .zip, etc.) to scan '
           'instead of downloading from PyPI. Mutually exclusive with positional package.',
    )

    parser.add_argument(
      '--github',
      type=str,
      default=None,
      metavar='GITHUB_URL',
      help='GitHub repository URL to use as the source reference when scanning a local '
           'archive (--archive). Has no effect when scanning a PyPI package.',
    )
    parser.add_argument(
      '--package-name',
      type=str,
      default=None,
      metavar='NAME',
      help='Override the package name when scanning a local archive (--archive). '
           'Defaults to the archive filename stem.',
    )
    parser.add_argument(
      '-lv', '--loglevel',
      type=LastPyMileApplication.__logLevelType,
      default=logging.INFO,
      help='Log level. From 0(no log) to 5(debug). default(3)',
    )
    parser.add_argument(
      '-f', '--reportfile',
      type=str,
      default=None,
      help='Write the report to the specified file',
    )
    parser.add_argument(
      '-o',
      action='store_true',
      help='Print the report to the screen',
    )


    args = parser.parse_args()

    l=logging.getLogger("lastpymile")
    coloredlogs.install(logger=l,level=args.loglevel)
    
    
    rl=logging.getLogger("lastpymile_report")
    rl.setLevel(logging.DEBUG) 


    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    ch.setFormatter(CustomFormatter())
    rl.addHandler(ch)

    try:
      
      current_folder=pathlib.Path().resolve()
      tmp_folder=os.path.join(current_folder,"tmp")
      if not os.path.exists(tmp_folder):
        os.makedirs(tmp_folder)

      if args.archive is not None:
        # ---- Local archive mode ----
        package_analysis = MaliciousCodePackageAnalyzer.createAnalysisForLocalArchive(
          archive_path=args.archive,
          github_url=args.github,
          package_name=args.package_name,
          checked=True,
        )
      else:
        # ---- PyPI package mode ----
        pakage=args.package.split(":")
        pakage_name=pakage[0]
        pakage_version=pakage[1] if len(pakage)==2 else None
        package_analysis = MaliciousCodePackageAnalyzer.createAnaliysisForPackage(pakage_name,pakage_version, checked=True)

      if package_analysis is not None:
        analysis_report=package_analysis.startAnalysis()
        json_report=json.dumps(analysis_report,indent=3)
        if args.reportfile is not None:
          with open(args.reportfile, "w") as f:
            f.write(json_report)
        if args.reportfile is None or args.o is True:
          print(json_report)
        
    except Exception as e:
      import traceback
      l.critical("Exception in main code: {}\n{}".format(e,traceback.format_exc()))


class CustomFormatter(logging.Formatter):

    white= "\u001b[37m"
    grey = "\x1b[38;21m"
    green = "\u001b[32m"
    orange = "\u001b[35m"
    yellow = "\x1b[33;21m"
    red = "\x1b[31;21m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"
    
    format = "Lastymile Report: %(message)s"

    FORMATS = {
        logging.DEBUG: white + format + reset,
        logging.INFO: green + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

if __name__ == "__main__":
  LastPyMileApplication()
  

    

  