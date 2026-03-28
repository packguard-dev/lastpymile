from lastpymile_npm.lastpymile import LastPyMile

import logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger("lastpymile_npm.main")

import argparse

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='LastJSmile')

    parser.add_argument(
        '-l',
        '--link',
        required=False,
        type=str,
        help='Specify the link of the repository'
    )

    parser.add_argument(
        '-a',
        '--artifact',
        required=False,
        type=str,
        help='Specify the local copy of the artifact'
    )

    parser.add_argument(
        'package',
        type=str,
        help='Specify the name of the package'
    )

    # Parse arguments
    args = parser.parse_args()
    input_package = args.package

    specific_repository_url = args.link
    specific_artifact_package = args.artifact

    package_name = ""
    package_version = ""
    if ":" in input_package:
        package_name = input_package[0:input_package.rfind(":")]
        package_version = input_package[input_package.rfind(":")+1:len(input_package)]

    else:
        package_name = input_package

    if specific_artifact_package is not None:
        if package_version == "":
            logger.error("Specify package version.")
            exit()

    logger.info("Package name: " + package_name)
    if package_version != "":
        logger.info("Package version: " + package_version)

    lpm = LastPyMile()
    lpm.run(package_name, specific_repository_url, specific_artifact_package, package_version)
