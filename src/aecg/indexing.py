""" Indexing functions for annotated ECG HL7 XML files

This submodule provides functions for indexing sets of aECG files.

See authors, license and disclaimer at the top level directory of this project.

"""

from functools import partial
from multiprocessing import Pool
from typing import Callable

import copy
import datetime
import errno
import logging
import numpy as np
import os
import pandas as pd
import zipfile

from aecg import parse_hl7_datetime, Aecg
from aecg.io import read_aecg
from aecg.utils import ratio_of_missing_samples
from aecg.tools.indexer import IndexingProgressCallBack

# Python logging ==============================================================
logger = logging.getLogger(__name__)


def xml_files_df(directory: str,
                 progress_callback:
                     Callable[[int, int], None] = None) -> pd.DataFrame:
    """Returns a dataframe listing xml files found in a directory

    Args:
        directory (str): Directory where to start the recursive search for
            xml files. The search will include subdirectories as well as
            contents of any zip file found during the search.
        progress_callback  (Callable[[int, int], None], optional): callback
            function to report progress. First parameter of the progress
            callback function is the current element and the second one the
            maximum number of elements. The function is called for each file
            found during the search process.

    Returns:
        pd.DataFrame: xml files recursively found in the directory and its zip
        files
    """
    files_df = pd.DataFrame()
    basedir = directory
    # Using lastchar to remove the os.path.sep as needed depending on
    # whether the directory string included an os.path.sep at the end
    lastchar = os.path.sep
    if basedir[-1] == "/" or basedir[-1] == "\\":
        lastchar = basedir[-1]
        basedir = basedir[0:-1]
    # Locate XML files
    xml_files = []
    num_files = 0
    for rootdir, dirs, files in os.walk(directory):
        for fn in files:
            if fn.endswith((".xml", ".XML")):
                newfn = os.path.join(
                    rootdir, fn).replace(basedir + lastchar, "")
                xml_files.append(newfn)
                num_files += 1
                if progress_callback:
                    progress_callback(0, num_files)

    tmp = pd.DataFrame()
    tmp["AECGXML"] = xml_files
    tmp["STUDYDIR"] = directory
    tmp["ZIPFILE"] = ""
    files_df = pd.concat([files_df, tmp], ignore_index=True)

    # Locate additional xml files contained in .zip files
    zip_files = [os.path.join(rootdir, fn).replace(directory + os.path.sep, "")
                 for rootdir, dirs, files in os.walk(directory)
                 for fn in files if fn.endswith((".zip", ".ZIP"))]
    for zipcontainer in zip_files:
        tmp = pd.DataFrame()
        with zipfile.ZipFile(os.path.join(directory, zipcontainer), "r") as zf:
            zf_files = zf.namelist()
            # Get only XML files
            aecg_files = []
            for file in zf_files:
                if file.lower().endswith(".xml"):
                    aecg_files.append(file)
                    num_files += 1
                    if progress_callback:
                        progress_callback(0, num_files)
            tmp["AECGXML"] = aecg_files
        tmp["STUDYDIR"] = directory
        tmp["ZIPFILE"] = zipcontainer
        files_df = pd.concat([files_df, tmp], ignore_index=True)

    return files_df


def get_annotated_leads(anns_df: pd.DataFrame) -> str:
    """Returns a comma separated list of annotated leads in the dataframe

    Args:
        anns_df (pd.DataFrame): Annotations dataframe

    Returns:
        str: Comma separated list of annotated leads found in anns_df
    """
    tmp = ','.join(anns_df["lead"].drop_duplicates().replace(
        r'^\s*$', 'GLOBAL', regex=True).values)
    return tmp


def get_interval_count_and_avg(
        anns_df: pd.DataFrame,
        include_all_found_intervals: bool = False) -> pd.DataFrame:
    """Return dataframe with intervals computed from annotations

    Args:
        anns_df (pd.DataFrame): Intervals dataframe
        include_all_found_intervals (bool, optional): If True, include
            individual intervals in `anns_df` in the output, otherwise return
            only count and average per interval type and lead. Defaults to
            False.

    Returns:
        pd.DataFrame: Number and average value of intervals (e.g, PR, QT) per
        lead.
    """

    res = pd.DataFrame()
    if anns_df.shape[0] > 0:
        qt_count = anns_df[anns_df.AVAL.notna()].groupby(
            ["LEADNAM", "HL7LEADNAM", "PARAMCD"]
            ).count().reset_index()
        qt_count["DTYPE"] = "COUNT"
        qt_count["TIME"] = np.nan
        qt_avg = anns_df[anns_df.AVAL.notna()].groupby(
            ["LEADNAM", "HL7LEADNAM", "PARAMCD"]
            ).mean().reset_index()
        qt_avg["DTYPE"] = "AVERAGE"
        qt_avg["TIME"] = np.nan
        res = pd.concat(
                [qt_count, qt_avg]).reset_index(drop=True)
        if include_all_found_intervals:
            res = pd.concat(
                [anns_df, res]).reset_index(drop=True)
    return res


def get_aecg_intervals(
    anns_df_in_ms: pd.DataFrame,
        include_all_found_intervals: bool = False) -> pd.DataFrame:
    """Calculate intervals (e.g., PR, QT, ...) from annotations

    All intervals are computed regardless of whether intervals are within or
    outside of physiological ranges in this function. Excluding intervals
    (i.e., because of missing annotations, misdetections or other factors)
    is not accounted for and should be done by a different function.

    Args:
        anns_df_in_ms (pd.DataFrame): Annotations per lead in milliseconds
        include_all_found_intervals (bool, optional): If True, include
            individual intervals in `anns_df_in_ms` in the output together with
            the count and averageper interval type and lead. If False, return
            count and average per interval type and lead only.
            Defaults to False.

    Returns:
        pd.DataFrame: Long dataframe with intervals calculated from input
        annotations
    """

    tmp = copy.deepcopy(anns_df_in_ms)
    preceeding_R = np.nan
    current_R = np.nan
    last_rr = np.nan
    last_pon = np.nan
    last_qon = np.nan
    last_qoff = np.nan
    last_toff = np.nan
    last_qt = np.nan
    tmp["RR"] = np.nan
    tmp["PR"] = np.nan
    tmp["QRS"] = np.nan
    tmp["QT"] = np.nan
    tmp["QTRR"] = np.nan  # Preceeding RR interval used for computing QTCF
    tmp["QTCF"] = np.nan
    current_lead = ""
    if anns_df_in_ms.shape[0] > 0:
        tmp.sort_values(by=["LEADNAM", "HL7LEADNAM", "TIME"], inplace=True)
        for idx, ann in tmp.iterrows():
            if current_lead == "" or current_lead != ann["LEADNAM"]:
                # Reset last observed annotations when starting new lead
                current_lead = ann["LEADNAM"]
                preceeding_R = np.nan
                current_R = np.nan
                last_rr = np.nan
                last_pon = np.nan
                last_qon = np.nan
                last_qoff = np.nan
                last_toff = np.nan
                last_qt = np.nan
            if ann["ECGLIBANNTYPE"] == "RPEAK":
                potential_R = ann["TIME"]
                if np.isnan(current_R) or potential_R > current_R:
                    preceeding_R = current_R
                    current_R = potential_R
                    last_rr = current_R - preceeding_R
                    tmp.loc[idx, "RR"] = last_rr
            if ann["ECGLIBANNTYPE"] == "PON":
                last_pon = ann["TIME"]
            if (ann["ECGLIBANNTYPE"] == "QON") or \
                    (ann["ECGLIBANNTYPE"] == "RON" and
                        (np.isnan(last_qon) or
                            (ann["TIME"]-last_qon) > 400.0)):
                last_qon = ann["TIME"]
                tmp.loc[idx, "PR"] = last_qon - last_pon
                last_pon = np.nan
                last_qoff = np.nan
                last_toff = np.nan
                last_qt = np.nan
            if (ann["ECGLIBANNTYPE"] == "QOFF") or \
                    (ann["ECGLIBANNTYPE"] == "STJPEAK"):
                last_qoff = ann["TIME"]
                tmp.loc[idx, "QRS"] = last_qoff - last_qon
            if ann["ECGLIBANNTYPE"] == "TOFF":
                last_toff = ann["TIME"]
                if not np.isnan(last_qon):
                    last_qt = last_toff - last_qon
                else:
                    # There is no QRS onset in current lead, let's try using
                    # QRS onset from global lead
                    global_qons = anns_df_in_ms[
                        (anns_df_in_ms["LEADNAM"] == "GLOBAL") &
                        (anns_df_in_ms["ECGLIBANNTYPE"] == "QON")
                        ]["TIME"].values
                    if len(global_qons) > 0:
                        potential_qts = last_toff - global_qons
                        potential_qts = potential_qts[potential_qts > 0]
                        last_qt = potential_qts[-1]
                    else:
                        if ann["LEADNAM"] == "GLOBAL":
                            # T offset annotated in global lead with no global
                            # QRS. Let's try using QRS onset from other lead
                            # in the same annotation group
                            local_qons = anns_df_in_ms[
                                (anns_df_in_ms["ANNGRPID"] ==
                                    ann["ANNGRPID"]) &
                                (anns_df_in_ms["ECGLIBANNTYPE"] == "QON")
                                ]["TIME"].values
                            if len(local_qons) == 1:
                                potential_qt = last_toff - local_qons[0]
                                if potential_qt > 0:
                                    last_qt = potential_qt
                                    # In this case
                                    tmp.loc[idx, "HL7LEADNAM"] =\
                                        anns_df_in_ms[
                                            (anns_df_in_ms["ANNGRPID"] ==
                                             ann["ANNGRPID"]) &
                                            (anns_df_in_ms["ECGLIBANNTYPE"] ==
                                             "QON") &
                                            (anns_df_in_ms["TIME"] ==
                                             local_qons[0])][
                                                 "HL7LEADNAM"].values[0]
                                    tmp.loc[idx, "LEADNAM"] =\
                                        anns_df_in_ms[
                                            (anns_df_in_ms["ANNGRPID"] ==
                                             ann["ANNGRPID"]) &
                                            (anns_df_in_ms["ECGLIBANNTYPE"] ==
                                             "QON") &
                                            (anns_df_in_ms["TIME"] ==
                                             local_qons[0])][
                                                 "LEADNAM"].values[0]
                tmp.loc[idx, "QT"] = last_qt
                tmp.loc[idx, "QTRR"] = last_rr
                tmp.loc[idx, "QTCF"] = last_qt/(((last_rr)/1000.0)**(1/3))
                # End of the beat -> reset preceeding values so
                # they are ready for next beat
                last_pon = np.nan
                last_qon = np.nan
                if ann["LEADNAM"] == "GLOBAL":
                    last_global_qon = np.nan
                last_qoff = np.nan
                last_toff = np.nan
    tmp = tmp[
        ["LEADNAM", "HL7LEADNAM", "TIME",
         "RR", "PR", "QRS", "QT", "QTRR", "QTCF"]].melt(
             id_vars=["LEADNAM", "HL7LEADNAM", "TIME"],
             value_vars=["RR", "PR", "QRS", "QT", "QTRR", "QTCF"],
             var_name="PARAMCD",
             value_name="AVAL").dropna().sort_values(by=["LEADNAM", "TIME"])
    tmp["DTYPE"] = ""

    res = get_interval_count_and_avg(tmp, include_all_found_intervals)

    return res


def get_aecg_index_data(
    my_aecg: Aecg,
        include_all_found_intervals: bool = False) -> pd.DataFrame:
    """Returns a dataframe with information to be included in the study index

    Args:
        my_aecg (Aecg): An annotated ECG
        include_all_found_intervals (bool, optional): If True, include
            individual intervals found in the annotations of `my_aecg` together
            with the count and average per interval type and lead. If False,
            returns count and average per interval type and lead only. Defaults
            to False.

    Returns:
        pd.DataFrame: Information to be included in the study index
    """

    aecg_data = None

    # Timepoint information
    tpt = ''
    if my_aecg.TPT["displayName"] != '':
        tpt = my_aecg.TPT["displayName"]
    elif my_aecg.TPT["code"] != '':
        tpt = my_aecg.TPT["code"]
    elif my_aecg.RTPT["displayName"] != '':
        tpt = my_aecg.RTPT["displayName"]
    elif my_aecg.RTPT["code"] != '':
        tpt = my_aecg.RTPT["code"]
    elif my_aecg.PTPT["displayName"] != '':
        tpt = my_aecg.PTPT["displayName"]
    elif my_aecg.PTPT["code"] != '':
        tpt = my_aecg.PTPT["code"]

    # Common columns
    tmp = {
        "EGSTUDYID": my_aecg.STUDYID["extension"],
        "USUBJID": my_aecg.USUBJID["extension"],
        "EGREFID": my_aecg.UUID,
        "EGDTC": my_aecg.RHYTHMEGDTC["low"],
        "EGDTC_stop": my_aecg.RHYTHMEGDTC["high"],
        "EGTPTREF": tpt,
        "DEVMANUFACTURER": my_aecg.DEVICE["manufacturer"],
        "DEVMODEL": my_aecg.DEVICE["model"],
        "DEVSOFTWARE": my_aecg.DEVICE["software"],
        "WFTYPE": "",
        "EGERROR": "No waveforms found",
        "EGANNSFL": "N",
        "EGINTSFL": "N"}
    missing_samples_ratio_rhythm = 0.0
    missing_samples_ratio_derived = 0.0
    if len(my_aecg.RHYTHMLEADS) > 0:
        tmp_rhyhtm = my_aecg.rhythm_as_df()
        missing_samples_ratio_rhythm = ratio_of_missing_samples(tmp_rhyhtm)
        if my_aecg.RHYTHMEGDTC["high"] == '':
            base_date = parse_hl7_datetime(my_aecg.RHYTHMEGDTC["low"])
            tmp["EGDTC_stop"] = (base_date + datetime.timedelta(
                milliseconds=tmp_rhyhtm["TIME"].values[-1] -
                tmp_rhyhtm["TIME"].values[0] + 1)
                ).strftime("%Y%m%d%H%M%S.%f%z")

    tmp_derived = copy.deepcopy(tmp)
    tmp_derived["WFTYPE"] = "DERIVED"
    is_rhythm_processed = False
    try:
        if (len(my_aecg.RHYTHMLEADS) == 0) and\
           (len(my_aecg.DERIVEDLEADS) == 0):
            tmp["PARAMCD"] = ""
            tmp["DTYPE"] = ""
            tmp["AVAL"] = ""
            tmp["LEADNAM"] = ""
            tmp["HL7LEADNAM"] = ""
            tmp["TIME"] = ""
            tmp["ERROR"] = ""
            aecg_data = pd.DataFrame([tmp])
        else:
            # Rhythm
            if len(my_aecg.RHYTHMLEADS) > 0:
                tmp["EGERROR"] = ""
                tmp["WFTYPE"] = "RHYTHM"
                num_annotated_leads = 0
                if len(my_aecg.RHYTHMANNS) > 0:
                    anns_df = pd.DataFrame(my_aecg.RHYTHMANNS[0].anns)
                    if anns_df.shape[0] > 0:
                        num_annotated_leads = anns_df[
                            anns_df["code"].str.contains("MDC_ECG_WAVC_") |
                            anns_df["codetype"].str.contains(
                                "MDC_ECG_WAVC_") |
                            anns_df["wavecomponent"].str.contains(
                                "MDC_ECG_WAVC_") |
                            anns_df["wavecomponent2"].str.contains(
                                "MDC_ECG_WAVC_")][
                                ["lead"]].drop_duplicates().shape[0]
                        tmp["EGANNSFL"] = "Y"
                        # Prepare annotations for counting subintervals
                        tmp_anns = my_aecg.rhythm_anns_in_ms()
                        if tmp_anns.shape[0] > 0:
                            tmp["EGINTSFL"] = "Y"
                            # Add intervals
                            intervals = get_aecg_intervals(
                                tmp_anns, include_all_found_intervals)
                            intervals["index"] = 0
                            tmp["index"] = 0
                            aecg_data = pd.DataFrame([tmp]).merge(
                                intervals, on=["index"])
                            aecg_data.drop(columns=["index"], inplace=True)
                        else:
                            aecg_data = pd.DataFrame([tmp])
                    else:
                        aecg_data = pd.DataFrame([tmp])
                else:
                    aecg_data = pd.DataFrame([tmp])
                tmp2 = copy.deepcopy(tmp)
                if 'index' in tmp2.keys():
                    tmp2.pop('index')
                tmp2["PARAMCD"] = "MISSINGSAMPLES"
                tmp2["DTYPE"] = "RATIO"
                tmp2["AVAL"] = missing_samples_ratio_rhythm
                tmp3 = copy.deepcopy(tmp)
                if 'index' in tmp3.keys():
                    tmp3.pop('index')
                tmp3["PARAMCD"] = "NUMANNOTATEDLEADS"
                tmp3["DTYPE"] = "COUNT"
                tmp3["AVAL"] = num_annotated_leads
                aecg_data = pd.concat(
                    [aecg_data,
                     pd.DataFrame([tmp2]),
                     pd.DataFrame([tmp3])],
                    ignore_index=True)
                is_rhythm_processed = True
            # Derived
            num_annotated_leads = 0
            if len(my_aecg.DERIVEDLEADS) > 0:
                tmp_derived_wf = my_aecg.derived_as_df()
                missing_samples_ratio_derived =\
                    ratio_of_missing_samples(tmp_derived_wf)
                tmp_derived["EGERROR"] = ""
                if len(my_aecg.DERIVEDANNS) > 0:
                    anns_df = pd.DataFrame(my_aecg.DERIVEDANNS[0].anns)
                    if anns_df.shape[0] > 0:
                        num_annotated_leads = anns_df[
                            anns_df["code"].str.contains("MDC_ECG_WAVC_") |
                            anns_df["codetype"].str.contains(
                                "MDC_ECG_WAVC_") |
                            anns_df["wavecomponent"].str.contains(
                                "MDC_ECG_WAVC_") |
                            anns_df["wavecomponent2"].str.contains(
                                "MDC_ECG_WAVC_")][
                                ["lead"]].drop_duplicates().shape[0]
                        tmp_derived["EGANNSFL"] = "Y"
                        # Prepare annotations for counting subintervals
                        tmp_anns = my_aecg.derived_anns_in_ms()
                        if tmp_anns.shape[0] > 0:
                            tmp_derived["EGINTSFL"] = "Y"
                            # Add intervals
                            intervals = get_aecg_intervals(
                                tmp_anns, include_all_found_intervals)
                            intervals["index"] = 0
                            tmp_derived["index"] = 0
                            tmp_derived = pd.DataFrame([tmp_derived]).merge(
                                intervals, on=["index"])
                            tmp_derived.drop(columns=["index"], inplace=True)
                if not isinstance(tmp_derived, pd.DataFrame):
                    tmp_derived = pd.DataFrame([tmp_derived])
                if len(my_aecg.RHYTHMLEADS) > 0:
                    aecg_data = pd.concat(
                        [aecg_data, tmp_derived],
                        ignore_index=True)
                else:
                    aecg_data = tmp_derived
                tmp2_derived = copy.deepcopy(tmp_derived)
                if 'index' in tmp2_derived.keys():
                    tmp2_derived.pop('index')
                tmp2_derived["PARAMCD"] = "MISSINGSAMPLES"
                tmp2_derived["DTYPE"] = "RATIO"
                tmp2_derived["AVAL"] = missing_samples_ratio_derived
                tmp2_derived.drop_duplicates(inplace=True)
                tmp3_derived = copy.deepcopy(tmp_derived)
                if 'index' in tmp3_derived.keys():
                    tmp3_derived.pop('index')
                tmp3_derived["PARAMCD"] = "NUMANNOTATEDLEADS"
                tmp3_derived["DTYPE"] = "COUNT"
                tmp3_derived["AVAL"] = num_annotated_leads
                tmp3_derived.drop_duplicates(inplace=True)
                aecg_data = pd.concat(
                    [aecg_data,
                     tmp2_derived,
                     tmp3_derived],
                    ignore_index=True)
    except Exception as ex:
        if is_rhythm_processed:
            tmp_derived["ERROR"] =\
                "Error extracting intervals from annotations"
            aecg_data = pd.concat([aecg_data, tmp_derived], ignore_index=True)
        else:
            tmp["ERROR"] = "Error extracting intervals from annotations"
            aecg_data = tmp

    return aecg_data


def index_study_xml_file(study_aecg_files_df: pd.DataFrame,
                         include_all_found_intervals: bool = False,
                         aecg_schema_filename: str = None,
                         progress_callback: Callable[[int, int], None] = None):
    """Returns a dataframe with the index information of the aECG files

    Args:
        study_aecg_files_df (pd.DataFrame): Study aECG files to include in the
            index
        include_all_found_intervals (bool, optional): If True, individual
            intervals found in the annotations as well as the count and average
            per interval type and lead will be included in the index. If False,
            only count and average per interval type and lead will be included
            in the index. Defaults to False.
        aecg_schema_filename (str, optional): Full path to the aECG HL7 schema
            file. If included, results of validation against the schema will be
            included in the application log. Defaults to None.
        progress_callback (Callable[[int, int], None], optional): callback
            function to report progress. First parameter of the progress
            callback function is the current element and the second one the
            maximum number of elements. If provided, it is called for each
            file processed during the indexing process. Defaults to None.

    Returns:
        pd.DataFrame: index information of aECG files in `study_aecg_files_df`
    """
    all_aecgs_index = []
    for study_aecg_row in study_aecg_files_df.itertuples():
        xml_fn = study_aecg_row.AECGXML
        zip_fn = study_aecg_row.ZIPFILE
        if study_aecg_row.ZIPFILE == "":
            xml_fn = os.path.join(
                study_aecg_row.STUDYDIR,
                study_aecg_row.AECGXML)
        else:
            zip_fn = os.path.join(
                study_aecg_row.STUDYDIR,
                study_aecg_row.ZIPFILE)

        tmp_index = pd.DataFrame({"STUDYDIR": [study_aecg_row.STUDYDIR],
                                  "AECGXML": [study_aecg_row.AECGXML],
                                  "ZIPFILE": [study_aecg_row.ZIPFILE]})

        logger.info(
            f',{zip_fn},'
            f'Indexing {xml_fn} [zip container: {zip_fn}]')
        try:
            # Read aECG XML
            my_aecg = read_aecg(xml_fn,
                                zip_fn,
                                aecg_schema_filename=aecg_schema_filename,
                                in_memory_xml=True,
                                include_digits=True,
                                log_validation=False)
            # aecg index data
            aecg_data = get_aecg_index_data(
                my_aecg, include_all_found_intervals)
            aecg_index = pd.DataFrame()
            # Extend index with study info
            for j, r in aecg_data.iterrows():
                tmp = pd.concat(
                    [tmp_index,
                     aecg_data.loc[j:j, ].reset_index(drop=True)], axis=1)
                tmp["ERROR"] = r.EGERROR
                aecg_index = pd.concat([aecg_index, tmp],
                                       ignore_index=True)
        except Exception as ex:
            aecg_index = tmp_index
            aecg_index["ERROR"] = "Error reading or parsing aECG XML file"

        all_aecgs_index.append(aecg_index)

        if progress_callback:
            progress_callback.emit(0, 0)

    return all_aecgs_index


class DirectoryIndexer:
    """Class for generation of an index of aECG XML files in a directory

        Attributes:
            aecg_dir (str): Directory containing the aECG XML files
            aecg_files (pd.DataFrame): XML files found in :attr:`aecg_dir`
            num_files (int): Number of XML files found in :attr:`aecg_dir`
            aecg_index (List): Index of aECG files found in :attr:`aecg_dir`
            cancel_indexing (bool): Boolean indicating whether running indexing
                processes should stop before completing.
    """

    def __init__(self):
        """Creates a new directory indexer object

        """
        self.cancel_indexing = False
        self.aecg_dir = ""
        self.aecg_files = pd.DataFrame()
        self.num_files = 0
        self.studyindex = []

    def set_aecg_dir(self, aecg_dir: str,
                     progress_callback: Callable[[int, int], None] = None):
        """Sets the directory to be indexed and lists xml files it contains

        This method assigns `aecg_dir` to :attr:`aecg_dir` attribute and then
        calls :func:`~aecg.indexing.xml_files_df` to populate
        :attr:`aecg_files` with the XML files found in `aecg_dir`.

        Args:
            aecg_dir (str): Directory containing the aECG XML files
            progress_callback (Callable[[int, int], None], optional): callback
                function to report progress. First parameter of the progress
                callback function is the current element and the second one the
                maximum number of elements. If provided, it is called for each
                file processed during the indexing process. Defaults to None.

        """
        if (aecg_dir == "") or not os.path.isdir(aecg_dir):
            logger.error(
                f',,Directory requested for indexing not found ({aecg_dir})')
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT),
                                    aecg_dir)
        # Retrieve the XML files to be indexed
        self.aecg_dir = aecg_dir
        self.aecg_files = xml_files_df(self.aecg_dir, progress_callback)
        self.num_files = self.aecg_files.shape[0]

    def index_directory(self,
                        include_all_found_intervals: bool = False,
                        aecg_schema_filename: str = None,
                        num_processes=1,
                        progress_callback: Callable[[int, int], None] = None):
        """Generates an index with the data from aECG XML files in aecg_dir

        This function generates an index with the data from aECG XML files
        stored in :attr:`aecg_dir`, its subdirectories, or in zip files
        contained in those.

        Args:
            include_all_found_intervals (bool, optional): include all intervals
                found when parsing the annotations. If false, only the average
                intervals will be returned. Defaults to False.
            aecg_schema_filename (str, optional): Filename of the xsd file
                of HL7 aECG standard schema to be used for XML schema
                validation of each aECG found. Defaults to None.
            num_processes (int, optional): Number of processes for parallel
                processing of aECG files to be indexed. Use 1 for no parallel
                processing. Defaults to 1.
            progress_callback (Callable[[int, int], None], optional): callback
                function to report progress. First parameter of the progress
                callback function is the current element and the second one the
                maximum number of elements. If provided, it is called each time
                an aECG is processed and added to the index. Defaults to None.

        Returns:
            pd.DataFrame: Study index
        """
        self.cancel_indexing = False
        self.studyindex = []
        aecg_files = self.aecg_files
        aecg_files["STUDYDIR"] = self.aecg_dir
        aecg_files["ERROR"] = "Warning: file not processed"
        # Convert the data frame to a list of data frames
        study_files_split = np.array_split(aecg_files, aecg_files.shape[0])
        if progress_callback and isinstance(
                progress_callback, IndexingProgressCallBack):
            progress_callback.pbar.unit = " aECG files"

        if num_processes > 1:
            logger.debug(f',,Index directory started with {num_processes} '
                         f'parallel processes')
            indexing_func = partial(
                index_study_xml_file,
                include_all_found_intervals=include_all_found_intervals,
                aecg_schema_filename=aecg_schema_filename,
                progress_callback=None)
            with Pool(num_processes) as pool:
                for i, res in enumerate(
                    pool.imap_unordered(
                        indexing_func,
                        study_files_split)):
                    self.studyindex.append(res[0])
                    if progress_callback:
                        progress_callback.emit(1, len(study_files_split))
                    if self.cancel_indexing:
                        break
        else:
            logger.debug(',,Indexing of directory started with 1 process')
            for study_files in study_files_split:
                res = index_study_xml_file(
                    study_files,
                    include_all_found_intervals,
                    aecg_schema_filename)
                self.studyindex.append(res[0])
                if progress_callback:
                    progress_callback.emit(1, len(study_files_split))
                if self.cancel_indexing:
                    break

        if self.cancel_indexing:
            logger.debug(',,Index directory cancelled by user.')

        studyindex_df = pd.concat(
            self.studyindex, ignore_index=True).sort_values(
                            by=["EGSTUDYID", "USUBJID", "EGDTC"],
                            ignore_index=True)

        logger.debug(f',,Index directory finished. {studyindex_df.shape[0]}'
                     f' waveforms found in {aecg_files.shape[0]} XML files.')

        self.cancel_indexing = False

        return studyindex_df
