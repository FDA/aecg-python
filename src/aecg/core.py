""" Core functions of the aecg package: tools for annotated ECG HL7 XML files

This submodule implements helper functions to validate and read annotated
electrocardiogram (ECG) stored in XML files following HL7
specification.

See authors, license and disclaimer at the top level directory of this project.

"""

# Imports =====================================================================
from typing import Dict
from lxml import etree
from scipy.interpolate import interp1d

import datetime
import logging
import numpy as np
import os
import pandas as pd


# Python logging ==============================================================
logger = logging.getLogger(__name__)

# CONSTANTS ===================================================================

#: Defines column names for the validationResults DataFrame
VALICOLS = ["EGXFN", "VALIGRP", "PARAM",
            "VALUE", "XPATH", "VALIMSG", "VALIOUT"]

#: Codes used in sequences
TIME_CODES = ["TIME_ABSOLUTE", "TIME_RELATIVE"]

#: Lead codes defined in the aECG HL7 standard and accepted by the aecg package
STD_LEADS = ["MDC_ECG_LEAD_I", "MDC_ECG_LEAD_II", "MDC_ECG_LEAD_III",
             "MDC_ECG_LEAD_AVR", "MDC_ECG_LEAD_AVL", "MDC_ECG_LEAD_AVF",
             "MDC_ECG_LEAD_V1", "MDC_ECG_LEAD_V2", "MDC_ECG_LEAD_V3",
             "MDC_ECG_LEAD_V4", "MDC_ECG_LEAD_V5", "MDC_ECG_LEAD_V6",
             "MDC_ECG_LEAD_X", "MDC_ECG_LEAD_Y", "MDC_ECG_LEAD_Z",
             "MDC_ECG_LEAD_AVRneg", "MDC_ECG_LEAD_AVRNEG",
             "MDC_ECG_LEAD_aVR", "MDC_ECG_LEAD_aVL", "MDC_ECG_LEAD_aVF", ]

#: Lead codes not in the aECG HL7 standard but accepted by the aecg package
KNOWN_NON_STD_LEADS = ["MORTARA_ECG_LEAD_TEA", "FDA_ECG_LEAD_VCGMAG"]

#: Codes accepted by the aecg package
SEQUENCE_CODES = TIME_CODES + STD_LEADS + KNOWN_NON_STD_LEADS

#: Display names for the lead codes defined in `aecg.core`
STD_LEADS_DISPLAYNAMES = {"MDC_ECG_LEAD_I": "I",
                          "MDC_ECG_LEAD_II": "II",
                          "MDC_ECG_LEAD_III": "III",
                          "MDC_ECG_LEAD_AVR": "aVR",
                          "MDC_ECG_LEAD_AVL": "aVL",
                          "MDC_ECG_LEAD_AVF": "aVF",
                          "MDC_ECG_LEAD_AVRneg": "-aVR",
                          "MDC_ECG_LEAD_AVRNEG": "-aVR",
                          "MDC_ECG_LEAD_V1": "V1",
                          "MDC_ECG_LEAD_V2": "V2",
                          "MDC_ECG_LEAD_V3": "V3",
                          "MDC_ECG_LEAD_V4": "V4",
                          "MDC_ECG_LEAD_V5": "V5",
                          "MDC_ECG_LEAD_V6": "V6",
                          "MORTARA_ECG_LEAD_TEA": "Mortara TEA",
                          "FDA_ECG_LEAD_VCGMAG": "VCGMAG",
                          "MDC_ECG_LEAD_aVR": "aVR",
                          "MDC_ECG_LEAD_aVL": "aVL",
                          "MDC_ECG_LEAD_aVF": "aVF", }


# XML and XPATH functions =====================================================

def new_validation_row(egxfile: str, valgroup: str, param: str) -> Dict:
    """Returns a new empty validation row

    Args:
        egxfile (str): filename of the xml file containing the aECG
        valgroup (str): validation group
        param (str): String with the parameter being assessed by the validator
    Returns:
        Dict: New empty validation row.
    """

    validation_row = {
        "EGXFN": egxfile,
        "XPATH": "",
        "VALIGRP": valgroup,
        "PARAM": param,
        "VALUE": "",
        "VALIOUT": "",
        "VALIMSG": ""
    }
    return validation_row


def validate_xpath(xmlnode: etree._ElementTree, xpath: str, ns: str, attr: str,
                   valrow: Dict, failcat: str = "ERROR") -> Dict:
    """ Populates valrow with validation results

    Populates valrow with validation results of the attribute in the node
    specified by xpath expression

    Args:
        xmlnode (etree._ElementTree): root or parent xmlnode
        xpath (str): xpath expression to search for
        ns (str): namespace for xpath
        attr (str): String with the attribute for wihc retrieve the value. If
            empty, the text value of the first node (if found) is used instead.
        valrow (Dict): initialized validation row where populate validation
            result.
        failcat (str): string with validation output category when validation
            fails (i.e., ERROR or WARNING)
    Returns:
        Dict: Validation row populated with the validation results.
    """

    valrow["XPATH"] = xpath
    if ns != "":
        valnodes = xmlnode.xpath(xpath.replace("/", "/ns:"),
                                 namespaces={"ns": ns})
    else:
        valnodes = xmlnode.xpath(xpath)

    valrow["VALIOUT"] = "ERROR"
    valrow[
        "VALIMSG"] = "Validation unknown error parsing xpath expression in XML"
    if len(valnodes) == 1:
        valnode = valnodes[0]
        if attr == "":
            txt = valnode.text
            if txt is None:
                txt = ""
                valrow["VALIOUT"] = failcat
                valrow[
                    "VALIMSG"] = "Node found but value is missing or empty" \
                                 " string"
            else:
                valrow["VALIOUT"] = "PASSED"
                valrow["VALIMSG"] = ""
            valrow["VALUE"] = txt
        else:
            txt = valnode.get(attr)
            if txt is None:
                txt = ""
                valrow["VALIOUT"] = failcat
                valrow["VALIMSG"] = "Node found but attribute is missing"
            else:
                valrow["VALIOUT"] = "PASSED"
                valrow["VALIMSG"] = ""
            valrow["VALUE"] = txt
    else:
        if len(valnodes) > 1:
            valrow["VALIOUT"] = failcat
            valrow["VALIMSG"] = "Multiple nodes in XML"
        else:
            valrow["VALIOUT"] = failcat
            valrow["VALIMSG"] = "Node not found"

    return valrow


# Other helper functions =====================================================


def get_aecg_schema_location() -> str:
    """ Returns the full path to the HL7 aECG xsd schema files included in aecg
    """
    xsd_filename = os.path.normpath(
        os.path.join(
            os.path.dirname(__file__),
            "data/hl7/2003-12 Schema/schema/PORT_MT020001.xsd"))

    return xsd_filename

# aECG classes ================================================================


class AecgLead:
    """
    Sampled voltage values and related information recorded from an ECG lead.

    Args:

    Attributes:

        leadname: Lead name as originally included in the aECG xml file.
        origin: Origin of the value scale, i.e., the physical quantity
            that a zero-digit would represent in the sequence of digit values.
        origin_unit: Units of the origin value.
        scale: A ratio-scale quantity that is factored out of the sequence of
            digit values.
        scale_unit: Units of the scale value.
        digits: List of sampled values.
        LEADTIME: (optional) Time when the lead was recorded
    """

    def __init__(self):
        self.leadname = ""
        self.origin = 0
        self.origin_unit = "uV"
        self.scale = 1
        self.scale_unit = "uV"
        self.digits = []
        self.LEADTIME = {"code": "", "head": "", "increment": "", "unit": ""}

    def display_name(self):
        if self.leadname in STD_LEADS:
            return STD_LEADS_DISPLAYNAMES[self.leadname.upper()]
        return self.leadname


class AecgAnnotationSet:
    """
    Annotation set for a given ECG waveform.

    Args:

    Attributes:

        person: Name of the person who performed the annotations.
        device: Model and name of the device used to perform the annotations.
        anns: Annotations
    """

    def __init__(self):
        self.person = ""
        self.device = {"model": "", "name": ""}
        self.anns = []


class Aecg:
    """
    An annotated ECG (aECG)

    Attributes:

        filename (str): filename including path to the XML file where the Aecg
            is stored. This could be in the filesystem or within the zip file
            specified in the zipContainer attribute.
        zipContainer (str): filename of the zip file where the XML specified by
            the filename attribute is stored. If empty string ("") then the
            filename is stored in the filesystem and not in a zip file.
        isValid (str): Indicates whether the original XML file passed XML
             schema validation ("Y"), failed ("N") or has not been validated
             ("").
        xmlfound (bool): Indicates whether the XML file was found, loaded and
            parsed into an xml document
        xmldoc (etree._ElementTree): The XML document containing the annotated
            ECG information.
        UUID (str): Annotated ECG universal unique identifier
        EGDTC (Dict): Date and time of collection of the annotated ECG.
        DEVICE (Dict): Dictionary containing device information (i.e.,
            manufacturer, model, software)
        USUBJID (Dict): Unique subject identifier.
        SEX (str): Sex of the subject.
        BIRTHTIME (str): Birthtime in HL7 date and time format.
        RACE (str): Race of the subject.
        TRTA (str): Assigned treatment.
        STUDYID (Dict): Study identifier.
        STUDYTITLE (str): Title of the study.
        TPT (Dict): Absolute timepoint or study event information.
        RTPT (Dict): Relative timepoint or study event relative to a reference
            event.
        PTPT (Dict): Protocol timepoint information.
        RHYTHMID (Dict): Unique identifier of the rhythm waveform.
        RHYTHMCODE (Dict): Code of the rhythm waveform (it should be "RHYTHM").
        RHYTHMEGDTC (Dict): Date and time of collection of the rhythm waveform.
        RHYTHMTIME (Dict): Time and sampling frequency information of the
            rhythm waveform.
        RHYTHMLEADS (List[AecgLead]): ECG leads of the rhythm waveform.
        RHYTHMANNS (List[AecgAnnotationSet]): Annotation sets for the RHYTHM
            waveform.
        DERIVEDID (Dict): Unique identifier of the derived ECG waveform
        DERIVEDCODE (Dict): Code of the derived waveform (supported code is
            "REPRESENTATIVE_BEAT").
        DERIVEDEGDTC (Dict): Date and time of collection of the derived
            waveform.
        DERIVEDTIME (Dict): Time and sampling frequency information of the
            derived waveform.
        DERIVEDLEADS (List[AecgLead]): ECG leads of the derived waveform.
        DERIVEDANNS (List[AecgAnnotationSet]): Annotation sets for the derived
            waveform.
        validatorResults (pd.DataFrame): validation log generated when
            reading the file.

    """

    def __init__(self):

        # Datasource
        self.filename = ""
        self.zipContainer = ""
        self.isValid = ""
        self.xmlfound = False
        self.xmldoc = None

        # General ECG information
        self.UUID = ""
        self.EGDTC = {"low": "", "center": "", "high": ""}
        self.DEVICE = {"manufacturer": "", "model": "", "software": ""}

        # Subject information
        self.USUBJID = {"extension": "", "root": ""}
        self.SEX = ""
        self.BIRTHTIME = ""
        self.RACE = ""

        # Treatment information
        self.TRTA = ""

        # Clinical trial information
        self.STUDYID = {"extension": "", "root": ""}
        self.STUDYTITLE = ""

        # Absolute timepoint information
        self.TPT = {"code": "", "low": "", "high": "", "displayName": "",
                    "reasonCode": ""}

        # Relative timepoint information
        self.RTPT = {"code": "", "displayName": "", "pauseQuantity": "",
                     "pauseQuantity_unit": ""}

        # Protocol timepoint information
        self.PTPT = {"code": "", "displayName": "", "referenceEvent": "",
                     "referenceEvent_displayName": ""}

        # Rhythm waveforms and annotations
        self.RHYTHMID = {"extension": "", "root": ""}
        self.RHYTHMCODE = {"code": "", "displayName": ""}
        self.RHYTHMEGDTC = {"low": "", "high": ""}

        self.RHYTHMTIME = {"code": "", "head": "", "increment": "", "unit": ""}
        self.RHYTHMLEADS = []

        self.RHYTHMANNS = []

        # Derived waveforms and annotations
        self.DERIVEDID = {"extension": "", "root": ""}
        self.DERIVEDCODE = {"code": "", "displayName": ""}
        self.DERIVEDEGDTC = {"low": "", "high": ""}

        self.DERIVEDTIME = {"code": "", "head": "",
                            "increment": "", "unit": ""}
        self.DERIVEDLEADS = []

        self.DERIVEDANNS = []

        # Validator results when reading and parsing the aECG XML
        self.validatorResults = pd.DataFrame()

    def xmlstring(self):
        """Returns the :attr:`xmldoc` as a string

        Returns:
            str: Pretty string of :attr:`xmldoc`
        """
        if self.xmldoc is not None:
            return etree.tostring(self.xmldoc, pretty_print=True).\
                decode("utf-8")
        else:
            return "N/A"

    def rhythm_as_df(self, new_fs: float = None) -> pd.DataFrame:
        """Returns the rhythm waveform as a dataframe

        Transform the rhythm waveform in a matrix with time in ms and
        digits values as physical values in mV. If `new_fs` is provided,
        the transformation also resamples the waveform to the sampling
        frequency specified in `new_fs` in Hz.

        Args:
            new_fs (float, optional): New sampling frequency in Hz. Defaults to
                None.

        Returns:
            pd.DataFrame: rhythm waveform in a matrix with time in ms and
            digits values as physical values in mV.
        """
        ecg_data = pd.DataFrame()
        if len(self.RHYTHMLEADS) > 0:
            ecg_start_time = parse_hl7_datetime(self.RHYTHMEGDTC["low"])
            tmp = [lead_mv_per_ms(ecg_start_time, ecg_lead, new_fs)
                   for ecg_lead in self.RHYTHMLEADS]
            # Few aECGs have duplicate leads, so we drop them before returning
            # the final dataframe
            tmp_df = pd.concat(tmp).drop_duplicates()
            ecg_data = tmp_df.pivot(index="TIME", columns="LEADNAM",
                                    values="VALUE").reset_index()
        return ecg_data

    def derived_as_df(self, new_fs: float = None) -> pd.DataFrame:
        """Returns the derived waveform as a dataframe

        Transform the derived waveform in a matrix with time in ms and
        digits values as physical values in mV. If `new_fs` is provided,
        the transformation also resamples the waveform to the sampling
        frequency specified in `new_fs` in Hz.

        Args:
            new_fs (float, optional): New sampling frequency in Hz. Defaults to
                None.

        Returns:
            pd.DataFrame: derived waveform in a matrix with time in ms and
            digits values as physical values in mV.
        """
        ecg_data = pd.DataFrame()
        if len(self.DERIVEDLEADS) > 0:
            ecg_start_time = parse_hl7_datetime(self.DERIVEDEGDTC["low"])
            tmp = [lead_mv_per_ms(ecg_start_time, ecg_lead, new_fs)
                   for ecg_lead in self.DERIVEDLEADS]
            # Few aECGs have duplicate leads, so we drop them before returning
            # the final dataframe
            tmp_df = pd.concat(tmp).drop_duplicates()
            ecg_data = tmp_df.pivot(index="TIME",
                                    columns="LEADNAM",
                                    values="VALUE").reset_index()
        return ecg_data

    def anns_to_ms(self, start_time: str, leads_start_times: pd.DataFrame,
                   ecganns: pd.DataFrame) -> pd.DataFrame:
        """ Returns a data frame with the annotation data in ms from start time

        Args:
            start_time (str): Start date and time in HL7 format of the
                rhythm or derived waveform
            leads_start_times (pd.DataFrame): Dataframe with start times of
                each lead in the aecg
            ecganns (pd.DataFrame): Dataframe wit the interval annotations from
                the rhythm or derived waveform

        Returns:
            pd.DataFrame: dataframe with the following columns ANNGRPID,
                BEATNUM, LEADNAM, ECGLIBANNTYPE, ANNTYPE, TIME (in ms)
        """

        res = pd.DataFrame()
        ecglib_suffix = {"value": "PEAK", "low": "ON", "high": "OFF"}
        for idx, ann in ecganns.iterrows():
            if ann["lead"] != "":
                if ann["lead"] in STD_LEADS:
                    leadnam = STD_LEADS_DISPLAYNAMES[ann["lead"].upper()]
                else:
                    leadnam = ann["lead"]
            else:
                leadnam = "GLOBAL"
            lead_st = leads_start_times[
                leads_start_times["leadname"] == ann["lead"]]
            if lead_st.shape[0] > 0:
                start_time = lead_st["time"].values[0]

            for param in ["value", "low", "high"]:
                if ann[param] != "":
                    lead_ann = pd.DataFrame(data=[["", "", "GLOBAL", "",
                                                   "UKNOWN", ""]],
                                            columns=["ANNGRPID", "BEATNUM",
                                                     "LEADNAM",
                                                     "ECGLIBANNTYPE",
                                                     "ANNTYPE", "TIME"])
                    lead_ann["ANNGRPID"] = ann["anngrpid"]
                    lead_ann["BEATNUM"] = ann["beatnum"]
                    lead_ann["LEADNAM"] = leadnam
                    lead_ann["ANNTYPE"] = ann["codetype"]
                    if ann["wavecomponent"] != "MDC_ECG_WAVC_TYPE":
                        lead_ann["ANNTYPE"] = ann["wavecomponent"]
                    lead_ann["HL7LEADNAM"] = ann["lead"]
                    if ann["wavecomponent2"] == "MDC_ECG_WAVC_PEAK":
                        annsufix = "PEAK"
                    else:
                        annsufix = ecglib_suffix[param]
                    if (ann["codetype"] == "MDC_ECG_WAVC_PWAVE") or \
                            (ann["wavecomponent"] == "MDC_ECG_WAVC_PWAVE") or \
                            (ann["wavecomponent2"] == "MDC_ECG_WAVC_PWAVE"):
                        lead_ann["ECGLIBANNTYPE"] = "P" + annsufix
                    elif ann["codetype"] == "MDC_ECG_WAVC_QRSWAVE" or \
                            (ann["wavecomponent"] ==
                                "MDC_ECG_WAVC_QRSWAVE") or \
                            (ann["wavecomponent2"] == "MDC_ECG_WAVC_QRSWAVE"):
                        if param != "value":
                            lead_ann["ECGLIBANNTYPE"] = "Q" + annsufix
                        else:
                            lead_ann["ECGLIBANNTYPE"] = "R" + annsufix
                    elif ann["codetype"] == "MDC_ECG_WAVC_RWAVE" or \
                            (ann["wavecomponent"] == "MDC_ECG_WAVC_RWAVE") or \
                            (ann["wavecomponent2"] == "MDC_ECG_WAVC_RWAVE"):
                        lead_ann["ECGLIBANNTYPE"] = "R" + annsufix
                    elif ann["codetype"] == "MDC_ECG_WAVC_TWAVE" or \
                            (ann["wavecomponent"] == "MDC_ECG_WAVC_TWAVE") or \
                            (ann["wavecomponent2"] == "MDC_ECG_WAVC_TWAVE"):
                        lead_ann["ECGLIBANNTYPE"] = "T" + annsufix
                    elif ann["codetype"] == "MDC_ECG_WAVC_TYPE" and \
                            ((ann["wavecomponent"] == "MDC_ECG_WAVC_PRSEG") or
                                (ann["wavecomponent2"] ==
                                    "MDC_ECG_WAVC_PRSEG")):
                        if param == "low":
                            lead_ann["ECGLIBANNTYPE"] = "P" + annsufix
                        elif param == "high":
                            lead_ann["ECGLIBANNTYPE"] = "QON"
                    elif ann["codetype"] == "MDC_ECG_WAVC_TYPE" and \
                            ((ann["wavecomponent"] ==
                                "MDC_ECG_WAVC_QRSTWAVE") or
                                (ann["wavecomponent2"] ==
                                    "MDC_ECG_WAVC_QRSTWAVE")
                             ):
                        if param == "low":
                            lead_ann["ECGLIBANNTYPE"] = "Q" + annsufix
                        else:
                            lead_ann["ECGLIBANNTYPE"] = "T" + annsufix
                    elif ann["codetype"] == "MDC_ECG_WAVC_QRSTWAVE" and\
                        ann["wavecomponent"] == "MDC_ECG_WAVC_QRSTWAVE" and\
                            ann["wavecomponent2"] == "":
                        if param == "low":
                            lead_ann["ECGLIBANNTYPE"] = "Q" + annsufix
                        elif param == "high":
                            lead_ann["ECGLIBANNTYPE"] = "T" + annsufix

                    elif ann["codetype"] == "MDC_ECG_WAVC_QWAVE" and \
                            ((ann["wavecomponent"] == "MDC_ECG_WAVC_QWAVE") or
                                (ann["wavecomponent2"] ==
                                    "MDC_ECG_WAVC_QWAVE")):
                        if param == "low":
                            lead_ann["ECGLIBANNTYPE"] = "Q" + annsufix
                        else:
                            lead_ann["ECGLIBANNTYPE"] = "Q" + annsufix
                    elif ann["codetype"] == "MDC_ECG_WAVC_TYPE" and \
                            ((ann["wavecomponent"] == "MDC_ECG_WAVC_QSWAVE") or
                                (ann["wavecomponent2"] ==
                                    "MDC_ECG_WAVC_QSWAVE")):
                        if param == "low":
                            lead_ann["ECGLIBANNTYPE"] = "Q" + annsufix
                        else:
                            lead_ann["ECGLIBANNTYPE"] = "Q" + annsufix
                    elif ann["codetype"] == "MDC_ECG_WAVC_SWAVE" and \
                            ((ann["wavecomponent"] == "MDC_ECG_WAVC_PEAK") or
                                (ann["wavecomponent2"] ==
                                    "MDC_ECG_WAVC_PEAK")):
                        lead_ann["ECGLIBANNTYPE"] = "S" + annsufix
                    elif ann["codetype"] == "MDC_ECG_WAVC_STJ" and \
                            ((ann["wavecomponent"] == "MDC_ECG_WAVC_PEAK") or
                                (ann["wavecomponent2"] ==
                                    "MDC_ECG_WAVC_PEAK")):
                        lead_ann["ECGLIBANNTYPE"] = "QOFF"
                    else:
                        if (ann["wavecomponent"] != "MDC_ECG_WAVC_TYPE") and \
                                (ann["wavecomponent"] != "MDC_ECG_WAVC"):
                            lead_ann["ECGLIBANNTYPE"] = \
                                ann["wavecomponent"].split("_")[3] + annsufix
                        elif (ann["wavecomponent2"] !=
                                "MDC_ECG_WAVC_TYPE") and \
                                (ann["wavecomponent2"] != "MDC_ECG_WAVC"):
                            lead_ann["ECGLIBANNTYPE"] = \
                                ann["wavecomponent2"].split("_")[3] + annsufix
                        else:
                            lead_ann["ECGLIBANNTYPE"] = \
                                ann["codetype"].split("_")[3] + annsufix

                    if ann["timecode"] == "TIME_ABSOLUTE":
                        try:
                            lead_ann["TIME"] = (
                                parse_hl7_datetime(ann[param]) -
                                parse_hl7_datetime(start_time)
                                ).total_seconds() * 1e3
                        except Exception as ex:
                            # If parsing parse_hl7_datetime fails is likely
                            # due to misslabeling of timecode as
                            # "TIME_ABSOLUTE" but reported as "TIME_RELATIVE".
                            # Let's try parsing the value as relative time
                            # instead.
                            param_u = param + "_unit"
                            if ann[param_u] == "ms":
                                lead_ann["TIME"] = float(ann[param])
                            elif ann[param_u] == "us":
                                lead_ann["TIME"] = float(ann[param]) * 1e-3
                            elif ann[param_u] == "s":
                                lead_ann["TIME"] = float(ann[param]) * 1e3
                    elif ann["timecode"] == "TIME_RELATIVE":
                        param_u = param + "_unit"
                        if ann[param_u] == "ms":
                            lead_ann["TIME"] = float(ann[param])
                        elif ann[param_u] == "us":
                            lead_ann["TIME"] = float(ann[param]) * 1e-3
                        elif ann[param_u] == "s":
                            lead_ann["TIME"] = float(ann[param]) * 1e3
                    else:  # Assuming TIME_ABSOLUTE
                        lead_ann["TIME"] = (parse_hl7_datetime(ann[param]) -
                                            parse_hl7_datetime(
                                                start_time)
                                            ).total_seconds() * 1e3
                    res = pd.concat(
                        [res, lead_ann], ignore_index=True).sort_values(
                            by=["ANNGRPID", "BEATNUM", "LEADNAM", "TIME"])
        if res.shape[0] > 0:
            # Remove annotations for which time location was not reported
            if res.dtypes["TIME"] == np.float64:
                res = res[res["TIME"].notna()]
            else:
                res = res[res["TIME"].notna() & (res["TIME"].map(str) != "")]

        return res

    def rhythm_anns_in_ms(self) -> pd.DataFrame:
        """Returns annotations in ms in the rhythm waveform

        Returns:
            pd.DataFrame: dataframe with the following columns ANNGRPID,
                BEATNUM, LEADNAM, ECGLIBANNTYPE, ANNTYPE, TIME (in ms)
        """
        res = pd.DataFrame()
        if len(self.RHYTHMANNS) > 0:
            leads_start_times = pd.DataFrame(
                [[lead.leadname, lead.LEADTIME['code'], lead.LEADTIME['head']]
                    for lead in self.RHYTHMLEADS],
                columns=["leadname", "code", "time"])
            ecganns = pd.DataFrame(self.RHYTHMANNS[0].anns)
            ecganns = ecganns[ecganns["wavecomponent"].str.contains(
                                "MDC_ECG_WAVC")]
            res = self.anns_to_ms(
                self.RHYTHMEGDTC["low"], leads_start_times, ecganns)
        # Return annotations dataframe
        return res

    def derived_anns_in_ms(self) -> pd.DataFrame:
        """Returns annotations in ms in the derived waveform

        Returns:
            pd.DataFrame: dataframe with the following columns ANNGRPID,
                BEATNUM, LEADNAM, ECGLIBANNTYPE, ANNTYPE, TIME (in ms)
        """
        res = pd.DataFrame()
        if len(self.DERIVEDANNS) > 0:
            leads_start_times = pd.DataFrame(
                [[lead.leadname, lead.LEADTIME['code'], lead.LEADTIME['head']]
                    for lead in self.DERIVEDLEADS],
                columns=["leadname", "code", "time"])
            ecganns = pd.DataFrame(self.DERIVEDANNS[0].anns)
            ecganns = ecganns[ecganns["wavecomponent"].str.contains(
                                "MDC_ECG_WAVC")]
            res = self.anns_to_ms(
                self.DERIVEDEGDTC["low"], leads_start_times, ecganns)
        # Return annotations dataframe
        return res

    def subject_age_in_years(self) -> int:
        """ Returns the subject's age in years as EGDTC - BIRTHTIME

            Returns:
                int: EGDTC - BIRTHTIME in years or -1 if EGDTC or BIRTHTIME are
                missing or not formated properly as dates
        """
        age = -1
        try:
            egdtc = ""
            for n in self.EGDTC:
                if self.EGDTC[n] != "":
                    egdtc = self.EGDTC[n]
                    break
            if (egdtc != "") and (self.BIRTHTIME != ""):
                bd = parse_hl7_datetime(self.BIRTHTIME)
                ecgd = parse_hl7_datetime(egdtc)
                anniversary = datetime.datetime(ecgd.year, bd.month, bd.day)
                age = (ecgd.year - bd.year)
                if ecgd < anniversary:
                    age -= 1
                logger.info(
                    f'{self.filename},{self.zipContainer},'
                    f'Estimated DM.AGE in years: {age}')
            else:
                logger.debug(
                    f'{self.filename},{self.zipContainer},'
                    f'Not enough data to estimate DM.AGE')
        except Exception as ex:
            logger.debug(
                    f'{self.filename},{self.zipContainer},'
                    f'Error estimating DM.AGE: \"{ex}\"')

        return age


class Error(Exception):
    """Base class for exceptions in this module."""
    pass


class UnknownUnitsError(Error):
    """Exception raised for errors when parsing units.

    Attributes:
        message -- explanation of the error
    """

    def __init__(self, message):
        self.message = message

# Conversion and transformation functions =====================================


def parse_hl7_datetime(hl7time: str) -> datetime.datetime:
    """Converts an HL7 date and time string to date and time values

    Args:
        hl7time (str): HL7 date/time string

    Returns:
        datetime.datetime: Date and time
    """

    splitted_datetime = hl7time.split(".")
    datatime_str = splitted_datetime[0]
    if len(splitted_datetime) > 1:
        mstz_str = splitted_datetime[1]
    else:
        mstz_str = []

    year = datatime_str[0:4]
    isodatetime_str = year
    # f"{year}-{month}-{day} {hh}:{min}:{sec}.{ms}"
    if len(datatime_str) > 4:
        # month
        isodatetime_str = isodatetime_str + "-" + datatime_str[4:6]
        if len(datatime_str) > 6:
            # day
            isodatetime_str = isodatetime_str + "-" + datatime_str[6:8]
            if len(datatime_str) > 8:
                # hh
                isodatetime_str = isodatetime_str + " " + datatime_str[8:10]
                if len(datatime_str) > 10:
                    # min
                    isodatetime_str = isodatetime_str + ":" +\
                        datatime_str[10:12]
                    if len(datatime_str) > 12:
                        # sec
                        isodatetime_str = isodatetime_str + ":" + \
                            datatime_str[12:14]
                        if len(mstz_str) > 0:
                            # ms
                            isodatetime_str = isodatetime_str + "." +\
                                mstz_str[0:3]

    return datetime.datetime.fromisoformat(isodatetime_str)


def lead_values_mv(aecglead: AecgLead) -> np.array:
    """Transforms the digits in `aecglead` to physical values in mV

    Args:
        aecglead (AecgLead): An `AecgLead` object

    Raises:
        UnknownUnitsError: [description]
        UnknownUnitsError: [description]

    Returns:
        np.array: Array of values contained in the `aecglead` in mV
    """
    # Convert origin to mV
    if aecglead.origin_unit == "uV":
        origin = aecglead.origin * 1e-3
    elif aecglead.oirigin_unit == "V":
        origin = aecglead.origin * 1e3
    elif aecglead.oirigin_unit == "mV":
        origin = aecglead.origin
    elif aecglead.oirigin_unit == "nV":
        origin = aecglead.origin * 1e-6
    else:
        raise UnknownUnitsError(
            f"Unknown unit in origin of {aecglead.leadname}")
    # Convert scale to mV
    if aecglead.scale_unit == "uV":
        scale = aecglead.scale * 1e-3
    elif aecglead.scale_unit == "V":
        scale = aecglead.scale * 1e3
    elif aecglead.scale_unit == "mV":
        scale = aecglead.scale
    elif aecglead.scale_unit == "nV":
        scale = aecglead.scale * 1e-6
    else:
        raise UnknownUnitsError(
            f"Unknown unit in scale of {aecglead.leadname}")
    # Return digits in mV
    return np.array([d * scale + origin for d in aecglead.digits])


def lead_mv_per_ms(start_time: datetime.datetime, ecg_lead: AecgLead,
                   new_fs: float = None) -> pd.DataFrame:
    """Returns a matrix with time in ms and lead values in mV

    Args:
        start_time (datetime.datetime): Start time of the record
        ecg_lead (AecgLead): An `AecgLead` object
        new_fs (float, optional): Sampling frequency of the output. If None,
            original sampling frequency is maintained. Defaults to None.

    Raises:
        UnknownUnitsError: Exception raised is AecgLead units are not in
        seconds (s), microseconds (us) or milliseconds (ms).

    Returns:
        pd.DataFrame: matrix with leadname, time in ms from `start_time` and
        lead values in mV
    """
    ecg_data = pd.DataFrame(data=lead_values_mv(ecg_lead),
                            columns=["VALUE"])
    ecg_data["LEADNAM"] = ecg_lead.display_name()
    timefactor = 1.0
    if ecg_lead.LEADTIME["unit"] == "us":
        timefactor = 1e-3
    elif ecg_lead.LEADTIME["unit"] == "s":
        timefactor = 1e3
    elif ecg_lead.LEADTIME["unit"] == "ms":
        timefactor = 1.0
    else:
        raise UnknownUnitsError(
            f"Unknown time unit ({ecg_lead.LEADTIME['unit']}) "
            f"for {ecg_lead.display_name()}")
    increment = ecg_lead.LEADTIME["increment"] * timefactor
    if ecg_lead.LEADTIME["code"] == "TIME_ABSOLUTE":
        ecg_data["TIME"] = ecg_data.index * increment + (parse_hl7_datetime(
            ecg_lead.LEADTIME["head"]) - start_time).total_seconds() * 1e3
    else:
        # Although a numeric is expected for TIME_RELATIVE values,
        # some aECG include an HL7 datetime string instead (likely due to an
        # error in the TIME encoding).
        try:
            # So, let's try decoding as absolute time first
            ecg_data["TIME"] = ecg_data.index * increment +\
                (parse_hl7_datetime(ecg_lead.LEADTIME["head"]) -
                 start_time).total_seconds() * 1e3
        except ValueError as ex:
            # The value was not a datetime, so let's parse it as numeric (i.e.,
            # as specificied in the file)
            ecg_data["TIME"] = ecg_data.index * increment + \
                float(ecg_lead.LEADTIME["head"]) * timefactor

    if new_fs is not None:
        # Check whether resampling is needed
        fs = 1 / increment
        if abs(fs - new_fs) > 0.00001:
            # Resample the ecg data
            total_time_in_s = ((ecg_data.TIME.iloc[-1] -
                                ecg_data.TIME.iloc[-0])/1000.0 +
                               increment)
            new_num_samples = int(total_time_in_s /
                                  (1 / new_fs))
            new_time = np.linspace(ecg_data.TIME.iloc[0],
                                   ecg_data.TIME.iloc[-1],
                                   new_num_samples)
            new_ecg_data = pd.DataFrame(
                data=interp1d(
                    ecg_data.TIME.values,
                    ecg_data["VALUE"].values,
                    kind='cubic')(new_time),
                columns=["VALUE"])
            new_ecg_data["LEADNAM"] = ecg_lead.display_name()
            new_ecg_data["TIME"] = new_time
            ecg_data = new_ecg_data

    return ecg_data
