""" Indexer tools for annotated ECG HL7 XML files

This submodule provides functions for indexing sets of aECG files.

See authors, license and disclaimer at the top level directory of this project.

"""


from enum import Enum
from typing import Callable
from tqdm import tqdm

import aecg
import aecg.indexing
import aecg.io
import datetime
import pandas as pd


class IndexingProgressCallBack:
    """
    Class to connect and update tqdm progress bars from aecg.indexing
    """
    def __init__(self, pbar: tqdm):
        """
        Args:
            pbar (tqdm): Progress bar
        """
        self.pbar = pbar

    def emit(self, i, j):
        if j != self.pbar.total:
            self.pbar.reset(j)
        self.pbar.update(i)


class AnnotationMethod(Enum):
    RHYTHM = 0
    DERIVED = 1
    HOLTER_RHYTHM = 2
    HOLTER_MEDIAN_BEAT = 3


class StudyInfo:
    """
    General study information

    Attributes:
        IndexFile (str): xslx file where to store the study information,
            including sheets for general informatio, index and other data.
        Description (str): Short study description
        Version (str): version of aecg-python used to generate the file.
        Date (str): date and time when the data was created in ISO 8601 format.
        End_date (str): date and time  in ISO 8601 format when the file was
            last updated.
        AppType (str): Application type (e.g., IND, NDA, BLA, ...)
        AppNum (int): Application number (six digits)
        StudyID (str): Study identifier.
        NumSubj (int): Number of subjects in the study.
        NECGSubj (int): Number of ECGs per subject per protocol.
        TotalECGs (int): Total number of ECGs in the study per protocol.
        AnMethod (AnnotationMethod): Method used for the annotations.
        AnLead (str): Primary lead used for the annotations.
        AnNbeats (int): Number of annotated beats
        StudyDir (str): Path to the directory containing the study aECG files
        Sponsor (str): Name of the sponsor od the study
    """

    def __init__(self):
        date_str = datetime.datetime.now().isoformat()
        self.IndexFile = ""
        self.Description = "Index automatically generated"
        self.Version = aecg.__version__
        self.Date = date_str
        self.End_date = date_str
        self.AppType = ""
        self.AppNum = 0
        self.StudyID = "UNKNOWN-STUDYID"
        self.NumSubj = 0
        self.NECGSubj = 0
        self.TotalECGs = 0
        self.AnMethod = AnnotationMethod.RHYTHM.name
        self.AnLead = aecg.core.STD_LEADS[1]  # Lead II
        self.AnNbeats = 1
        self.StudyDir = "."
        self.Sponsor = "UNKNONW_SPONSOR"


class StudyStats:
    """
    Basic statistics on study

    Attributes:
        num_subjects (int): number of unique subjects (based on USUBJID) found
            in the aECG files in the index
        num_aecgs (int): number of unique aECG waveforms. Note that rhythm and
            derived are counted once if they are paired
        avg_aecgs_subject (float): average number of aECGs per subject
        subjects_less_aecgs (int): Number of subjects with less aECGs than the
            number of aECGs per subject specfied in the study protocol or
            report
        aecgs_no_annotations (int): number of aECGs with no interval
            annotations
        aecgs_less_qt_in_primary_lead (int): number of aECGs with less QT
            intervals in the primary lead than specified per protocol
        aecgs_less_qts (int): number of aECGs with less QT intervals than
            specified per protocol
        aecgs_annotations_multiple_leads (int): number of aECGs with QT
            annotations in multiple leads
        aecgs_annotations_no_primary_lead (int): number of aECGs with QT
            annotations not in the primary lead
        aecgs_with_errors (int): Number of aECG files with errors
        aecgs_potentially_digitized (int): number of aECG files potentially
            digitized (i.e., with more than 5% of samples missing)
    """

    def __init__(
            self, studyInfo: StudyInfo = None,
            index_df: pd.DataFrame = None,
            progress_callback: Callable[[int, int], None] = None):
        if studyInfo is not None and index_df is not None:
            self.calculateStatistics(studyInfo, index_df, progress_callback)

    def calculateStatistics(
            self, studyInfo: StudyInfo, index_df: pd.DataFrame,
            progress_callback: Callable[[int, int], None] = None):

        self.num_subjects = 0
        self.num_aecgs = 0
        self.avg_aecgs_subject = 0
        self.subjects_less_aecgs = studyInfo.NumSubj
        self.subjects_more_aecgs = 0
        self.aecgs_no_annotations = studyInfo.TotalECGs
        self.aecgs_less_qt_in_primary_lead = studyInfo.TotalECGs
        self.aecgs_less_qts = studyInfo.TotalECGs
        self.aecgs_annotations_multiple_leads = studyInfo.TotalECGs
        self.aecgs_annotations_no_primary_lead = studyInfo.TotalECGs
        self.aecgs_with_errors = studyInfo.TotalECGs
        self.aecgs_potentially_digitized = studyInfo.TotalECGs

        num_of_stats = 12

        if progress_callback:
            progress_callback.pbar.unit = " statistics"
        # number of unique subjects in the index
        if "USUBJID" in index_df.columns:
            self.num_subjects = len(pd.unique(
                index_df["USUBJID"][index_df["USUBJID"] != ""]))
        if progress_callback:
            progress_callback.emit(1, num_of_stats)

        # Num of unique aECG waveforms
        if "EGREFID" in index_df.columns:
            self.num_aecgs = index_df[[
                "ZIPFILE", "AECGXML", "EGREFID"]].drop_duplicates().shape[0]
        if progress_callback:
            progress_callback.emit(1, num_of_stats)

        # aECGs per subject
        if self.num_aecgs > 0 and self.num_subjects > 0:
            self.avg_aecgs_subject = index_df[
                (index_df["USUBJID"] != "") & (index_df["EGREFID"] != "")][
                    ["USUBJID", "EGREFID"]
                    ].drop_duplicates().groupby(
                        ["USUBJID"]).count()["EGREFID"].agg(['mean'])[0]
        if progress_callback:
            progress_callback.emit(1, num_of_stats)

        # Other stats
        # Subjects with fewer ECGs
        if self.num_subjects > 0:
            tmp = index_df[
                (index_df["USUBJID"] != "") & (index_df["EGREFID"] != "")][
                    ["USUBJID", "EGREFID"]
                    ].drop_duplicates().groupby(
                        ["USUBJID"]).count()["EGREFID"].reset_index()
            tmp = tmp[
                tmp["EGREFID"] < studyInfo.NECGSubj]
            self.subjects_less_aecgs = tmp.shape[0]
        if progress_callback:
            progress_callback.emit(1, num_of_stats)

        # Subjects with more ECGs
        if self.num_subjects > 0:
            tmp = index_df[
                (index_df["USUBJID"] != "") & (index_df["EGREFID"] != "")][
                    ["USUBJID", "EGREFID"]
                    ].drop_duplicates().groupby(
                        ["USUBJID"]).count()["EGREFID"].reset_index()
            tmp = tmp[
                tmp["EGREFID"] > studyInfo.NECGSubj]
            self.subjects_more_aecgs = tmp.shape[0]
        if progress_callback:
            progress_callback.emit(1, num_of_stats)

        if self.num_aecgs > 0:
            # aECGs without interval annotations
            # Get the ECGs with interval annotations in the
            # waveform specified for annotations per protocol
            annotated = index_df[
                (index_df["ERROR"] == "") &
                (index_df["WFTYPE"] == studyInfo.AnMethod) &
                (index_df["EGANNSFL"] == "Y") &
                (index_df["EGINTSFL"] == "Y") &
                (index_df["PARAMCD"] != "MISSINGSAMPLES") &
                (index_df["PARAMCD"] != "NUMANNOTATEDLEADS")][
                    ["ZIPFILE", "AECGXML", "EGREFID"]].drop_duplicates()
            # The rest of ECGs have no interval annotations
            self.aecgs_no_annotations = self.num_aecgs - annotated.shape[0]
            if progress_callback:
                progress_callback.emit(1, num_of_stats)

            # aECGs without expected number of QTs in primary lead
            primary_lead = studyInfo.AnLead
            num_qts = studyInfo.AnNbeats
            if primary_lead == "GLOBAL":
                primary_lead = ""
            else:
                for lead in aecg.STD_LEADS_DISPLAYNAMES.keys():
                    if primary_lead == aecg.STD_LEADS_DISPLAYNAMES[lead]:
                        primary_lead = lead
                        break

            # num aecgs with at least num_qts in primary lead
            qtscount = index_df[
                (index_df["ERROR"] == "") &
                (index_df["WFTYPE"] == studyInfo.AnMethod) &
                (index_df["DTYPE"] == "COUNT") &
                (index_df["PARAMCD"] == "QT")].reset_index(drop=True)
            qtscount["AVAL"] = pd.to_numeric(qtscount["AVAL"])
            n_aecgs_expected_qts = qtscount[
                (qtscount["HL7LEADNAM"] == primary_lead) &
                (qtscount["AVAL"] >= num_qts)].shape[0]
            self.aecgs_less_qt_in_primary_lead =\
                self.num_aecgs - n_aecgs_expected_qts
            if progress_callback:
                progress_callback.emit(1, num_of_stats)

            # num aecgs with at least num_qts (regardles of lead)
            num_qts_eitherlead = qtscount.groupby(
                ["EGREFID"]).sum()["AVAL"].reset_index()
            n_aecgs_expected_qts_other_leads = num_qts_eitherlead[
                num_qts_eitherlead["AVAL"] >= num_qts].shape[0]
            self.aecgs_less_qts = self.num_aecgs -\
                n_aecgs_expected_qts_other_leads
            if progress_callback:
                progress_callback.emit(1, num_of_stats)

            # aECGs annotated in multiple leads
            leadscount = index_df[
                (index_df["ERROR"] == "") &
                (index_df["WFTYPE"] == studyInfo.AnMethod) &
                (index_df["PARAMCD"] == "NUMANNOTATEDLEADS") &
                (index_df["DTYPE"] == "COUNT")].reset_index(drop=True)
            leadscount["AVAL"] = pd.to_numeric(leadscount["AVAL"])
            self.aecgs_annotations_multiple_leads = leadscount[
                (leadscount["AVAL"] > 1.0)].shape[0]
            if progress_callback:
                progress_callback.emit(1, num_of_stats)

            # aECGs with annotations not in primary lead
            self.aecgs_annotations_no_primary_lead = index_df[
                (index_df["ERROR"] == "") &
                (index_df["WFTYPE"] == studyInfo.AnMethod) &
                (index_df["HL7LEADNAM"] != primary_lead) &
                (index_df["DTYPE"] == "COUNT") &
                (index_df["PARAMCD"] != "MISSINGSAMPLES") &
                (index_df["PARAMCD"] != "NUMANNOTATEDLEADS")][
                    ["AECGXML", "ZIPFILE"]
                ].drop_duplicates().shape[0]
            if progress_callback:
                progress_callback.emit(1, num_of_stats)

            # aECGS with errors
            self.aecgs_with_errors = index_df[index_df["ERROR"] != ""].shape[0]
            if progress_callback:
                progress_callback.emit(1, num_of_stats)

            # Potentially digitized aECGs
            digitizedcount = index_df[
                (index_df["PARAMCD"] == "MISSINGSAMPLES")
                ].reset_index(drop=True)
            digitizedcount["AVAL"] = pd.to_numeric(digitizedcount["AVAL"])
            self.aecgs_potentially_digitized = digitizedcount[
                (digitizedcount["AVAL"] >= 0.05)
                ]["AECGXML"].drop_duplicates().shape[0]
            if progress_callback:
                progress_callback.emit(1, num_of_stats)


def save_study_index(
        studyindex_info: StudyInfo,
        studyindex_df: pd.DataFrame,
        study_stats: StudyStats):
    # Save information to index xlsx file
    with pd.ExcelWriter(studyindex_info.IndexFile) as writer:
        sinfodf = pd.DataFrame.from_dict(
            studyindex_info.__dict__, orient='index'
            ).reset_index().rename(columns={"index": "Property", 0: "Value"})
        sinfodf.to_excel(writer, index=False, sheet_name="Info")

        ecgidx_df = studyindex_df[studyindex_df["ERROR"] == ""][[
            "AECGXML", "ZIPFILE", "EGSTUDYID", "USUBJID",
            "EGREFID", "EGDTC", "EGTPTREF", "WFTYPE"
            ]].drop_duplicates()
        ecgidx_df.to_excel(writer, index=False, sheet_name="Index")

        studyindex_df.to_excel(writer, index=False, sheet_name="Intervals")

        ss_df = pd.DataFrame.from_dict(
            study_stats.__dict__, orient='index'
            ).reset_index().rename(columns={"index": "Property", 0: "Value"})
        ss_df.to_excel(writer, index=False, sheet_name="Stats")


def index_study(
        studyindex_info: StudyInfo,
        include_all_found_intervals: bool = False,
        n_cores: int = 1,
        progress_callback: Callable[[int, int], None] = None
        ) -> pd.DataFrame:
    studyindex_info.Date = datetime.datetime.now().isoformat()
    studyindex_df = pd.DataFrame()
    try:
        directory_indexer = aecg.indexing.DirectoryIndexer()
        directory_indexer.set_aecg_dir(studyindex_info.StudyDir)
        studyindex_df = directory_indexer.index_directory(
            include_all_found_intervals, aecg.get_aecg_schema_location(),
            n_cores, progress_callback)
    except Exception as ex:
        studyindex_df = pd.DataFrame(
            data={
                "STUDYDIR": [studyindex_info.StudyDir],
                "ERROR": [str(ex)]})

    # Remove STUDYDIR column from studyindex_df
    studyindex_df.drop(columns=["STUDYDIR"], inplace=True)

    # Calculate stats
    study_stats = StudyStats(studyindex_info, studyindex_df, progress_callback)
    studyindex_info.End_date = datetime.datetime.now().isoformat()

    save_study_index(studyindex_info, studyindex_df, study_stats)

    return studyindex_df
