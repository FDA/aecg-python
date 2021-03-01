""" Command line tools for annotated ECG HL7 XML files

This submodule provides command line utilities and functions for indexing sets
of aECG files.

See authors, license and disclaimer at the top level directory of this project.

"""

import aecg
import aecg.tools.indexer
import aecg.io
import aecg.utils
import argparse
import datetime
import logging
import logging.config
import matplotlib.pyplot as plt
import os
import pandas as pd

from tqdm.cli import tqdm

__toolname__ = "aecg.tools.aecg_clt"


def valid_appnum(appnum: str) -> str:
    """Checks whether the provided appnum is a valid 6-digit integer

    Args:
        appnum (str): Application number

    Raises:
        argparse.ArgumentTypeError: Raises error if appnum cannot be coded as
            a 6-digit positive integer (i.e., appnum is in the [0, 999999]
            range)

    Returns:
        str: 6-digit application number
    """
    try:
        apn = int(appnum)
        if (apn < 0) or (apn > 999999):
            raise argparse.ArgumentTypeError(
                    f"{appnum} is not a valid 6-digits application number.")
    except ValueError:
        raise argparse.ArgumentTypeError(
                f"{appnum} is not a valid 6-digits application number.")

    return appnum


def inspect_aecg(args):
    logger = logging.getLogger(__toolname__ + '.inspect_aecg')
    logger.info(
        f"{args.aecg_xml},{args.aecg_zip},Inspecting: '{args.aecg_xml}'")
    zipfile = ''
    if args.aecg_zip is not None:
        zipfile = args.aecg_zip
    the_aecg = aecg.io.read_aecg(
        args.aecg_xml,
        zip_container=zipfile,
        include_digits=True,
        aecg_schema_filename=aecg.get_aecg_schema_location())
    logger.info(
        f"{args.aecg_xml},{args.aecg_zip},Inspection finished")


def print_aecg(args):
    logger = logging.getLogger(__toolname__ + '.print_aecg')
    logger.info(
        f"{args.aecg_xml},{args.aecg_zip},Printing: '{args.aecg_xml}'")
    zipfile = ''
    if args.aecg_zip is not None:
        zipfile = args.aecg_zip
    the_aecg = aecg.io.read_aecg(
        args.aecg_xml,
        zip_container=zipfile,
        include_digits=True,
        aecg_schema_filename=aecg.get_aecg_schema_location())
    ecgwf = the_aecg.rhythm_as_df()
    fig = aecg.utils.plot_aecg(
        ecgwf, the_aecg.rhythm_anns_in_ms(),
        aecg.utils.ECG_plot_layout.STACKED)
    fig.savefig('aecg_rhythm.' + args.format, dpi=300)
    logger.info(
        f"{args.aecg_xml},{args.aecg_zip},"
        f"Rhythm strip printed to aecg_rhythm.{args.format}")
    ecgwf = the_aecg.derived_as_df()
    fig = aecg.utils.plot_aecg(
        ecgwf, the_aecg.derived_anns_in_ms(),
        aecg.utils.ECG_plot_layout.STACKED)
    fig.savefig('aecg_derived.' + args.format, dpi=300)
    logger.info(
        f"{args.aecg_xml},{args.aecg_zip},"
        f"Derived beat printed to aecg_derived.{args.format}")


def index_study_path(args):
    logger = logging.getLogger(__toolname__ + '.index_study_path_aecg')
    startmsg = f"Indexing: '{args.dir}' to: '{args.oxlsx}'"
    print(f"{startmsg}")
    logger.info(
        f",,{startmsg}")
    studyindex_info = aecg.tools.indexer.StudyInfo()
    studyindex_info.StudyDir = os.path.normpath(args.dir)
    studyindex_info.IndexFile = os.path.normpath(args.oxlsx)
    studyindex_info.Description = args.description
    studyindex_info.Version = aecg.__version__
    studyindex_info.AppType = args.apptype
    studyindex_info.AppNum = f"{int(args.appnum):06d}"
    studyindex_info.StudyID = args.studyid
    studyindex_info.NumSubj = args.numsubj
    studyindex_info.NECGSubj = args.necgsubj
    studyindex_info.TotalECGs = args.totalecgs
    studyindex_info.AnMethod = aecg.tools.indexer.AnnotationMethod[
        args.annmethod].name
    studyindex_info.AnLead = args.annlead
    studyindex_info.AnNbeats = args.nbeatsann
    studyindex_info.StudyDir = args.dir
    studyindex_info.Sponsor = args.sponsor

    n_cores = args.nprocs
    pbar = tqdm(desc=f"Indexing {studyindex_info.StudyDir} directory")
    mycb = aecg.tools.indexer.IndexingProgressCallBack(pbar)
    studyindex_df = aecg.tools.indexer.index_study(
        studyindex_info,
        args.allintervals == "Y",
        n_cores, mycb)
    pbar.close()

    return studyindex_df


def main():
    # Default logging configuration file
    logging_conf_file = os.path.normpath(
        os.path.join(
            os.path.dirname(aecg.core.__file__),
            'cfg/aecg_logging.conf'))

    # Command line options, arguments and sub-commands
    options = argparse.ArgumentParser()
    # Print version
    options.add_argument(
        "--version",
        help=f'Print the version of the software package',
        action='version',
        version=f'aecg package version {aecg.__version__}')
    # Logging configuration file argument
    options.add_argument(
        "-l", "--logconffile", type=str,
        help=f'logging configuration file (default: {logging_conf_file})',
        default=logging_conf_file)

    # Check aecg file subcommand
    commands = options.add_subparsers()

    # Inspect aECG xml file
    parser_inspect = commands.add_parser(
        "inspect",
        help="Reads and parses an aECG XML file")
    parser_inspect.add_argument(
        "aecg_xml",
        type=str,
        help="Filename of the aECG XML file to be inspected")
    parser_inspect.add_argument(
        "--aecg_zip",
        type=str,
        help="Filename of the zip file containing the aECG XML file to be "
             "inspected")
    parser_inspect.set_defaults(func=inspect_aecg)

    # Plot an aECG xml file
    parser_inspect = commands.add_parser(
        "print",
        help="Reads an aECG XML file and prints it to png file(s)")
    parser_inspect.add_argument(
        "aecg_xml",
        type=str,
        help="Filename of the aECG XML file to be printed out")
    parser_inspect.add_argument(
        "--aecg_zip",
        type=str,
        help="Filename of the zip file containing the aECG XML file to be "
             "printed")
    parser_inspect.add_argument(
        "--format",
        type=str,
        choices=['png', 'pdf'],
        default='png',
        help="Format of the output files where to print the aECG "
             "(default: png) ")
    parser_inspect.set_defaults(func=print_aecg)

    # Index aECG xml files in a directory
    parser_index = commands.add_parser(
        "index",
        help="Creates an index by parsing aECG XML files found in the "
             "specified directory and/or its zip files")
    parser_index.add_argument(
        "--dir",
        required=True,
        type=str,
        help="Directory to be indexed (required)")
    parser_index.add_argument(
        "--apptype",
        required=True,
        type=str,
        help="Application type (e.g., BLA, IND, NDA, IDE). Use UNK if the "
             "application type is unknown or does not apply (required)")
    parser_index.add_argument(
        "--appnum",
        required=True,
        type=valid_appnum,
        help="6-digit application number. Use 0 if unknown or does not apply"
             " (required)")
    parser_index.add_argument(
        "--studyid",
        required=True,
        type=str,
        help="Study identifier (required)")
    parser_index.add_argument(
        "--numsubj",
        required=True,
        type=int,
        help="Number of subjects per protocol or study report (required)")
    parser_index.add_argument(
        "--necgsubj",
        required=True,
        type=int,
        help="Number of ECGs per subjects per protocol or study report"
             " (required)")
    parser_index.add_argument(
        "--totalecgs",
        required=True,
        type=int,
        help="Total number of ECGs collected per protocol or study report"
             " (required)")
    parser_index.add_argument(
        "--annmethod",
        required=True,
        type=str,
        help="Annotation method, e.g., RHYTHM or DERIVED (required)")
    parser_index.add_argument(
        "--annlead",
        required=True,
        type=str,
        help="Primary annotated lead, e.g., I, II, V5, GLOBAL (required)")
    parser_index.add_argument(
        "--nbeatsann",
        required=True,
        type=int,
        help="Number of annotated beats (required)")
    parser_index.add_argument(
        "--sponsor",
        required=True,
        type=str,
        help="Sponsor, applicant or laboratory name (required)")
    parser_index.add_argument(
        "--description",
        type=str,
        default="Index automatically generated",
        help="Description of the study (default: Index automatically "
             "generated)")
    parser_index.add_argument(
        "-a", "--allintervals",
        choices=["N", "Y"],
        default="N",
        help='Include all individual intervals found if set to "Y" '
             '(default: N)')
    parser_index.add_argument(
        "--oxlsx",
        type=str,
        default="study_index.xlsx",
        help="Output xlsx file to which save the study Info and Index sheets "
             "(default: study_index.xlsx)")
    parser_index.add_argument(
        "--nprocs",
        type=int,
        default=1,
        help="Number of process to run in parallel for indexing "
             "(default: 1)")
    parser_index.set_defaults(func=index_study_path)

    # Parse command line
    args = options.parse_args()
    # Load logging configuration
    logging.config.fileConfig(args.logconffile)
    logger = logging.getLogger(__toolname__)

    # Print to console logging filename/s (if any)
    for h in logger.root.handlers:
        if isinstance(h, logging.FileHandler):
            print(
                f"Logging to {h.baseFilename} file with a "
                f"{type(h).__name__}")

    # Execute command functions
    args.func(args)


if __name__ == "__main__":
    main()
