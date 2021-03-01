""" I/O functions of the aecg package: tools for annotated ECG HL7 XML files

This module implements helper functions to parse and read annotated
electrocardiogram (ECG) stored in XML files following HL7
specification.

See authors, license and disclaimer at the top level directory of this project.

"""

# Imports =====================================================================
from typing import Dict, Tuple
from lxml import etree
from aecg import validate_xpath, new_validation_row, VALICOLS, \
    TIME_CODES, SEQUENCE_CODES, \
    Aecg, AecgLead, AecgAnnotationSet

import copy
import logging
import pandas as pd
import re
import zipfile


# Python logging ==============================================================
logger = logging.getLogger(__name__)


def parse_annotations(xml_filename: str,
                      zip_filename: str,
                      aecg_doc: etree._ElementTree,
                      aecgannset: AecgAnnotationSet,
                      path_prefix: str,
                      annsset_xmlnode_path: str,
                      valgroup: str = "RHYTHM",
                      log_validation: bool = False) -> Tuple[
                          AecgAnnotationSet, pd.DataFrame]:
    """Parses `aecg_doc` XML document and extracts annotations

    Args:
        xml_filename (str): Filename of the aECG XML file.
        zip_filename (str): Filename of zip file containint the aECG XML file.
            If '', then xml file is not stored in a zip file.
        aecg_doc (etree._ElementTree): XML document of the aECG XML file.
        aecgannset (AecgAnnotationSet): Annotation set to which append found
            annotations.
        path_prefix (str): Prefix of xml path from which start searching for
            annotations.
        annsset_xmlnode_path (str): Path to xml node of the annotation set
            containing the annotations.
        valgroup (str, optional): Indicates whether to search annotations in
            rhythm or derived waveform. Defaults to "RHYTHM".
        log_validation (bool, optional): Indicates whether to maintain the
            validation results in `aecg.validatorResults`. Defaults to
            False.

    Returns:
        Tuple[AecgAnnotationSet, pd.DataFrame]: Annotation set updated with
        found annotations and dataframe with results of validation.
    """
    anngrpid = 0
    # Annotations stored within a beat
    beatnodes = aecg_doc.xpath((
        path_prefix +
        "/component/annotation/code[@code=\'MDC_ECG_BEAT\']").replace(
        '/', '/ns:'), namespaces={'ns': 'urn:hl7-org:v3'})
    beatnum = 0
    valpd = pd.DataFrame()
    if len(beatnodes) > 0:
        logger.info(
            f'{xml_filename},{zip_filename},'
            f'{valgroup} {len(beatnodes)} annotated beats found')
    for beatnode in beatnodes:
        for rel_path in ["../component/annotation/"
                         "code[contains(@code, \"MDC_ECG_\")]"]:
            annsnodes = beatnode.xpath(rel_path.replace('/', '/ns:'),
                                       namespaces={'ns': 'urn:hl7-org:v3'})
            rel_path2 = "../value"
            for annsnode in annsnodes:
                ann = {"anngrpid": anngrpid, "beatnum": "", "code": "",
                       "codetype": "",
                       "wavecomponent": "", "wavecomponent2": "",
                       "timecode": "",
                       "value": "", "value_unit": "",
                       "low": "", "low_unit": "",
                       "high": "", "high_unit": "",
                       "lead": ""}
                # Annotation code
                valrow2 = validate_xpath(
                    annsnode,
                    ".",
                    "urn:hl7-org:v3",
                    "code",
                    new_validation_row(xml_filename,
                                       valgroup,
                                       "ANNSET_BEAT_ANNS"),
                    failcat="WARNING")
                valrow2["XPATH"] = annsset_xmlnode_path + "/" + rel_path
                if valrow2["VALIOUT"] == "PASSED":
                    ann["code"] = valrow2["VALUE"]

                # Annotation type from top level value
                valrow2 = validate_xpath(annsnode,
                                         "../value",
                                         "urn:hl7-org:v3",
                                         "code",
                                         new_validation_row(
                                             xml_filename, valgroup,
                                             "ANNSET_BEAT_ANNS"),
                                         failcat="WARNING")
                valrow2["XPATH"] = annsset_xmlnode_path + "/value"

                if log_validation:
                    valpd = valpd.append(pd.DataFrame(
                        [valrow2], columns=VALICOLS), ignore_index=True)

                if valrow2["VALIOUT"] == "PASSED":
                    ann["codetype"] = valrow2["VALUE"]

                # Annotations type
                valrow2 = validate_xpath(
                    annsnode,
                    rel_path2,
                    "urn:hl7-org:v3",
                    "code",
                    new_validation_row(xml_filename,
                                       valgroup,
                                       "ANNSET_BEAT_ANNS"),
                    failcat="WARNING")
                valrow2["XPATH"] = annsset_xmlnode_path + "/" + rel_path + \
                    "/" + rel_path2

                if valrow2["VALIOUT"] == "PASSED":
                    ann["beatnum"] = beatnum
                    ann["codetype"] = valrow2["VALUE"]
                    if log_validation:
                        valpd = valpd.append(
                            pd.DataFrame([valrow2], columns=VALICOLS),
                            ignore_index=True)

                    subannsnodes = annsnode.xpath(
                        rel_path.replace('/', '/ns:'),
                        namespaces={'ns': 'urn:hl7-org:v3'})
                    if len(subannsnodes) == 0:
                        subannsnodes = [annsnode]
                    else:
                        subannsnodes += [annsnode]
                    # Exclude annotations reporting interval values only
                    subannsnodes = [
                        sa for sa in subannsnodes
                        if not sa.get("code").startswith("MDC_ECG_TIME_PD_")]
                    for subannsnode in subannsnodes:
                        # Annotations type
                        valrow2 = validate_xpath(subannsnode,
                                                 rel_path2,
                                                 "urn:hl7-org:v3",
                                                 "code",
                                                 new_validation_row(
                                                     xml_filename,
                                                     valgroup,
                                                     "ANNSET_BEAT_ANNS"),
                                                 failcat="WARNING")
                        valrow2["XPATH"] = annsset_xmlnode_path + "/" + \
                            rel_path + "/" + rel_path2

                        if valrow2["VALIOUT"] == "PASSED":
                            ann["wavecomponent"] = valrow2["VALUE"]
                        if log_validation:
                            valpd = valpd.append(
                                pd.DataFrame([valrow2], columns=VALICOLS),
                                ignore_index=True)

                        # Annotations value
                        valrow2 = validate_xpath(subannsnode,
                                                 rel_path2,
                                                 "urn:hl7-org:v3",
                                                 "value",
                                                 new_validation_row(
                                                     xml_filename,
                                                     valgroup,
                                                     "ANNSET_BEAT_ANNS"),
                                                 failcat="WARNING")
                        valrow2["XPATH"] = annsset_xmlnode_path + "/" + \
                            rel_path + "/" + rel_path2
                        if valrow2["VALIOUT"] == "PASSED":
                            ann["value"] = valrow2["VALUE"]
                        if log_validation:
                            valpd = valpd.append(
                                pd.DataFrame([valrow2], columns=VALICOLS),
                                ignore_index=True)

                        # Annotations value units
                        valrow2 = validate_xpath(subannsnode,
                                                 rel_path2,
                                                 "urn:hl7-org:v3",
                                                 "unit",
                                                 new_validation_row(
                                                     xml_filename,
                                                     valgroup,
                                                     "ANNSET_BEAT_ANNS"),
                                                 failcat="WARNING")
                        valrow2["XPATH"] = annsset_xmlnode_path + "/" + \
                            rel_path + "/" + rel_path2
                        if valrow2["VALIOUT"] == "PASSED":
                            ann["value_unit"] = valrow2["VALUE"]
                        if log_validation:
                            valpd = valpd.append(
                                pd.DataFrame([valrow2], columns=VALICOLS),
                                ignore_index=True)

                        # annotations info from supporting ROI
                        rel_path3 = "../support/supportingROI/component/"\
                                    "boundary/value"
                        for n in ["", "low", "high"]:
                            if n != "":
                                rp = rel_path3 + "/" + n
                            else:
                                rp = rel_path3
                            valrow3 = validate_xpath(
                                subannsnode,
                                rp,
                                "urn:hl7-org:v3",
                                "value",
                                new_validation_row(xml_filename,
                                                   valgroup,
                                                   "ANNSET_BEAT_ANNS"),
                                failcat="WARNING")
                            valrow3["XPATH"] = annsset_xmlnode_path + "/" + \
                                rel_path + "/" + rp
                            if valrow3["VALIOUT"] == "PASSED":
                                if n != "":
                                    ann[n] = valrow3["VALUE"]
                                else:
                                    ann["value"] = valrow3["VALUE"]
                            if log_validation:
                                valpd = valpd.append(
                                    pd.DataFrame([valrow3], columns=VALICOLS),
                                    ignore_index=True)
                            valrow3 = validate_xpath(
                                subannsnode,
                                rp,
                                "urn:hl7-org:v3",
                                "unit",
                                new_validation_row(xml_filename,
                                                   valgroup,
                                                   "ANNSET_BEAT_ANNS"),
                                failcat="WARNING")
                            valrow3["XPATH"] = annsset_xmlnode_path + "/" + \
                                rel_path + "/" + rp
                            if valrow3["VALIOUT"] == "PASSED":
                                if n != "":
                                    ann[n + "_unit"] = valrow3["VALUE"]
                                else:
                                    ann["value_unit"] = valrow3["VALUE"]
                            if log_validation:
                                valpd = valpd.append(
                                    pd.DataFrame([valrow3], columns=VALICOLS),
                                    ignore_index=True)

                        # annotations time encoding, lead and other info used
                        # by value and supporting ROI
                        rel_path4 = "../support/supportingROI/component/"\
                                    "boundary/code"
                        roinodes = subannsnode.xpath(
                            rel_path4.replace('/', '/ns:'),
                            namespaces={'ns': 'urn:hl7-org:v3'})
                        for roinode in roinodes:
                            valrow4 = validate_xpath(
                                roinode,
                                ".",
                                "urn:hl7-org:v3",
                                "code",
                                new_validation_row(xml_filename,
                                                   valgroup,
                                                   "ANNSET_BEAT_ANNS"),
                                failcat="WARNING")
                            valrow4["XPATH"] = annsset_xmlnode_path + "/" + \
                                rel_path + "/" + rel_path4
                            if valrow4["VALIOUT"] == "PASSED":
                                if valrow4["VALUE"] in ["TIME_ABSOLUTE",
                                                        "TIME_RELATIVE"]:
                                    ann["timecode"] = valrow4["VALUE"]
                                else:
                                    ann["lead"] = valrow4["VALUE"]
                            if log_validation:
                                valpd = valpd.append(
                                    pd.DataFrame([valrow4], columns=VALICOLS),
                                    ignore_index=True)

                        aecgannset.anns.append(copy.deepcopy(ann))

                else:
                    # Annotations type
                    valrow2 = validate_xpath(annsnode,
                                             ".",
                                             "urn:hl7-org:v3",
                                             "code",
                                             new_validation_row(xml_filename,
                                                                valgroup,
                                                                "ANNSET_BEAT_"
                                                                "ANNS"),
                                             failcat="WARNING")
                    valrow2["XPATH"] = annsset_xmlnode_path + "/" + rel_path +\
                        "/" + rel_path2
                    if valrow2["VALIOUT"] == "PASSED":
                        ann["beatnum"] = beatnum
                        ann["codetype"] = valrow2["VALUE"]
                        if log_validation:
                            valpd = valpd.append(
                                pd.DataFrame([valrow2], columns=VALICOLS),
                                ignore_index=True)

                        # Annotations value
                        valrow2 = validate_xpath(annsnode,
                                                 rel_path2,
                                                 "urn:hl7-org:v3",
                                                 "value",
                                                 new_validation_row(
                                                     xml_filename,
                                                     valgroup,
                                                     "ANNSET_BEAT_ANNS"),
                                                 failcat="WARNING")
                        valrow2["XPATH"] = annsset_xmlnode_path + "/" + \
                            rel_path + "/" + rel_path2
                        if valrow2["VALIOUT"] == "PASSED":
                            ann["value"] = valrow2["VALUE"]
                        if log_validation:
                            valpd = valpd.append(
                                pd.DataFrame([valrow2], columns=VALICOLS),
                                ignore_index=True)

                        # Annotations value units
                        valrow2 = validate_xpath(annsnode,
                                                 rel_path2,
                                                 "urn:hl7-org:v3",
                                                 "unit",
                                                 new_validation_row(
                                                     xml_filename,
                                                     valgroup,
                                                     "ANNSET_BEAT_ANNS"),
                                                 failcat="WARNING")
                        valrow2["XPATH"] = annsset_xmlnode_path + "/" + \
                            rel_path + "/" + rel_path2
                        if valrow2["VALIOUT"] == "PASSED":
                            ann["value_unit"] = valrow2["VALUE"]
                        if log_validation:
                            valpd = valpd.append(
                                pd.DataFrame([valrow2], columns=VALICOLS),
                                ignore_index=True)

                        # annotations time encoding, lead and other info used
                        # by value and supporting ROI
                        rel_path4 = "../support/supportingROI/component/" \
                                    "boundary/code"
                        roinodes = annsnode.xpath(
                            rel_path4.replace('/', '/ns:'),
                            namespaces={'ns': 'urn:hl7-org:v3'})
                        for roinode in roinodes:
                            valrow4 = validate_xpath(roinode,
                                                     ".",
                                                     "urn:hl7-org:v3",
                                                     "code",
                                                     new_validation_row(
                                                         xml_filename,
                                                         valgroup,
                                                         "ANNSET_BEAT_ANNS"),
                                                     failcat="WARNING")
                            valrow4["XPATH"] = annsset_xmlnode_path + "/" + \
                                rel_path + "/" + rel_path4
                            if valrow4["VALIOUT"] == "PASSED":
                                if valrow4["VALUE"] in ["TIME_ABSOLUTE",
                                                        "TIME_RELATIVE"]:
                                    ann["timecode"] = valrow4["VALUE"]
                                else:
                                    ann["lead"] = valrow4["VALUE"]
                            if log_validation:
                                valpd = valpd.append(
                                    pd.DataFrame([valrow4],
                                                 columns=VALICOLS),
                                    ignore_index=True)

                        aecgannset.anns.append(copy.deepcopy(ann))

                    else:
                        if log_validation:
                            valpd = valpd.append(
                                pd.DataFrame([valrow2], columns=VALICOLS),
                                ignore_index=True)
            anngrpid = anngrpid + 1
        beatnum = beatnum + 1
    if len(beatnodes) > 0:
        logger.info(
            f'{xml_filename},{zip_filename},'
            f'{valgroup} {beatnum} annotated beats and {anngrpid} '
            f'annotations groups found')
    anngrpid_from_beats = anngrpid
    # Annotations stored without an associated beat
    for codetype_path in ["/component/annotation/code["
                          "(contains(@code, \"MDC_ECG_\") and"
                          " not (@code=\'MDC_ECG_BEAT\'))]"]:
        annsnodes = aecg_doc.xpath(
            (path_prefix + codetype_path).replace('/', '/ns:'),
            namespaces={'ns': 'urn:hl7-org:v3'})
        rel_path2 = "../value"
        for annsnode in annsnodes:
            ann = {"anngrpid": anngrpid, "beatnum": "", "code": "",
                   "codetype": "",
                   "wavecomponent": "", "wavecomponent2": "",
                   "timecode": "",
                   "value": "", "value_unit": "",
                   "low": "", "low_unit": "",
                   "high": "", "high_unit": "",
                   "lead": ""}
            # Annotations code
            valrow2 = validate_xpath(annsnode,
                                     ".",
                                     "urn:hl7-org:v3",
                                     "code",
                                     new_validation_row(xml_filename, valgroup,
                                                        "ANNSET_NOBEAT_ANNS"),
                                     failcat="WARNING")
            valrow2["XPATH"] = annsset_xmlnode_path

            if log_validation:
                valpd = valpd.append(pd.DataFrame([valrow2], columns=VALICOLS),
                                     ignore_index=True)
            if valrow2["VALIOUT"] == "PASSED":
                ann["code"] = valrow2["VALUE"]

            # Annotation type from top level value
            valrow2 = validate_xpath(annsnode,
                                     "../value",
                                     "urn:hl7-org:v3",
                                     "code",
                                     new_validation_row(xml_filename, valgroup,
                                                        "ANNSET_NOBEAT_ANNS"),
                                     failcat="WARNING")
            valrow2["XPATH"] = annsset_xmlnode_path + "/value"

            if log_validation:
                valpd = valpd.append(pd.DataFrame([valrow2], columns=VALICOLS),
                                     ignore_index=True)
            if valrow2["VALIOUT"] == "PASSED":
                ann["codetype"] = valrow2["VALUE"]

            subannsnodes = annsnode.xpath(
                (".." + codetype_path).replace('/', '/ns:'),
                namespaces={'ns': 'urn:hl7-org:v3'})
            if len(subannsnodes) == 0:
                subannsnodes = [annsnode]
            for subannsnode in subannsnodes:

                subsubannsnodes = subannsnode.xpath(
                    (".." + codetype_path).replace('/', '/ns:'),
                    namespaces={'ns': 'urn:hl7-org:v3'})

                tmpnodes = [subannsnode]
                if len(subsubannsnodes) > 0:
                    tmpnodes = tmpnodes + subsubannsnodes

                for subsubannsnode in tmpnodes:
                    ann["wavecomponent"] = ""
                    ann["wavecomponent2"] = ""
                    ann["timecode"] = ""
                    ann["value"] = ""
                    ann["value_unit"] = ""
                    ann["low"] = ""
                    ann["low_unit"] = ""
                    ann["high"] = ""
                    ann["high_unit"] = ""

                    roi_base = "../support/supportingROI/component/boundary"
                    rel_path3 = roi_base + "/value"

                    valrow2 = validate_xpath(
                        subsubannsnode,
                        ".",
                        "urn:hl7-org:v3",
                        "code",
                        new_validation_row(xml_filename,
                                           valgroup,
                                           "ANNSET_NOBEAT_"
                                           "ANNS"),
                        failcat="WARNING")
                    valrow2["XPATH"] = annsset_xmlnode_path + "/.." + \
                        codetype_path + "/code"
                    if valrow2["VALIOUT"] == "PASSED":
                        if not ann["codetype"].endswith("WAVE"):
                            ann["codetype"] = valrow2["VALUE"]
                    if log_validation:
                        valpd = valpd.append(
                            pd.DataFrame([valrow2], columns=VALICOLS),
                            ignore_index=True)

                    # Annotations type
                    valrow2 = validate_xpath(
                        subsubannsnode,
                        rel_path2,
                        "urn:hl7-org:v3",
                        "code",
                        new_validation_row(xml_filename,
                                           valgroup,
                                           "ANNSET_NOBEAT_"
                                           "ANNS"),
                        failcat="WARNING")
                    valrow2["XPATH"] = annsset_xmlnode_path + "/.." + \
                        codetype_path + "/" + rel_path2
                    if valrow2["VALIOUT"] == "PASSED":
                        ann["wavecomponent"] = valrow2["VALUE"]
                        # if ann["wavecomponent"] == "":
                        #     ann["wavecomponent"] = valrow2["VALUE"]
                        # else:
                        #     ann["wavecomponent2"] = valrow2["VALUE"]
                    if log_validation:
                        valpd = valpd.append(
                            pd.DataFrame([valrow2], columns=VALICOLS),
                            ignore_index=True)

                    # Annotations value
                    valrow2 = validate_xpath(
                        subsubannsnode,
                        rel_path2,
                        "urn:hl7-org:v3",
                        "",
                        new_validation_row(xml_filename,
                                           valgroup,
                                           "ANNSET_NOBEAT_"
                                           "ANNS"),
                        failcat="WARNING")
                    valrow2["XPATH"] = annsset_xmlnode_path + "/.." + \
                        codetype_path + "/" + rel_path2
                    if valrow2["VALIOUT"] == "PASSED":
                        ann["value"] = valrow2["VALUE"]
                    if log_validation:
                        valpd = valpd.append(
                            pd.DataFrame([valrow2], columns=VALICOLS),
                            ignore_index=True)

                    # Annotations value as attribute
                    valrow2 = validate_xpath(
                        subsubannsnode,
                        rel_path2,
                        "urn:hl7-org:v3",
                        "value",
                        new_validation_row(xml_filename,
                                           valgroup,
                                           "ANNSET_NOBEAT_"
                                           "ANNS"),
                        failcat="WARNING")
                    valrow2["XPATH"] = annsset_xmlnode_path + "/.." + \
                        codetype_path + "/" + rel_path2
                    if valrow2["VALIOUT"] == "PASSED":
                        ann["value"] = valrow2["VALUE"]
                    if log_validation:
                        valpd = valpd.append(
                            pd.DataFrame([valrow2], columns=VALICOLS),
                            ignore_index=True)
                    # Annotations value units
                    valrow2 = validate_xpath(
                        subsubannsnode,
                        rel_path2,
                        "urn:hl7-org:v3",
                        "unit",
                        new_validation_row(xml_filename,
                                           valgroup,
                                           "ANNSET_NOBEAT_"
                                           "ANNS"),
                        failcat="WARNING")
                    valrow2["XPATH"] = annsset_xmlnode_path + "/.." + \
                        codetype_path + "/" + rel_path2
                    if valrow2["VALIOUT"] == "PASSED":
                        ann["value_unit"] = valrow2["VALUE"]
                    if log_validation:
                        valpd = valpd.append(
                            pd.DataFrame([valrow2], columns=VALICOLS),
                            ignore_index=True)

                    # annotations info from supporting ROI
                    for n in ["", "low", "high"]:
                        if n != "":
                            rp = rel_path3 + "/" + n
                        else:
                            rp = rel_path3
                        valrow3 = validate_xpath(
                            subsubannsnode,
                            rp,
                            "urn:hl7-org:v3",
                            "value",
                            new_validation_row(xml_filename,
                                               valgroup,
                                               "ANNSET_NOBEAT_"
                                               "ANNS"),
                            failcat="WARNING")
                        valrow3["XPATH"] = annsset_xmlnode_path + "/.." + \
                            codetype_path + "/" + rp
                        if valrow3["VALIOUT"] == "PASSED":
                            if n != "":
                                ann[n] = valrow3["VALUE"]
                            else:
                                ann["value"] = valrow3["VALUE"]
                        else:
                            roi_base = "../component/annotation/support/"\
                                       "supportingROI/component/boundary"
                            # Annotations type
                            valrow2 = validate_xpath(subsubannsnode,
                                                     "../component/annotation/"
                                                     "value",
                                                     "urn:hl7-org:v3",
                                                     "code",
                                                     new_validation_row(
                                                         xml_filename,
                                                         valgroup,
                                                         "ANNSET_NOBEAT_ANNS"),
                                                     failcat="WARNING")
                            valrow2["XPATH"] = annsset_xmlnode_path + "/.." + \
                                codetype_path + "/" + \
                                "../component/annotation/value"
                            if valrow2["VALIOUT"] == "PASSED":
                                ann["wavecomponent2"] = valrow2["VALUE"]
                            if log_validation:
                                valpd = valpd.append(
                                    pd.DataFrame([valrow2], columns=VALICOLS),
                                    ignore_index=True)
                            # annotation values

                            if n != "":
                                rp = roi_base + "/value/" + n
                            else:
                                rp = roi_base + "/value"
                            valrow3 = validate_xpath(subsubannsnode,
                                                     rp,
                                                     "urn:hl7-org:v3",
                                                     "value",
                                                     new_validation_row(
                                                         xml_filename,
                                                         valgroup,
                                                         "ANNSET_NOBEAT_ANNS"),
                                                     failcat="WARNING")
                            valrow3["XPATH"] = annsset_xmlnode_path + "/.." + \
                                codetype_path + "/" + rp
                            if valrow3["VALIOUT"] == "PASSED":
                                if n != "":
                                    ann[n] = valrow3["VALUE"]
                                else:
                                    ann["value"] = valrow3["VALUE"]
                        if log_validation:
                            valpd = valpd.append(
                                pd.DataFrame([valrow3], columns=VALICOLS),
                                ignore_index=True)
                        valrow3 = validate_xpath(
                            subsubannsnode,
                            rp,
                            "urn:hl7-org:v3",
                            "unit",
                            new_validation_row(xml_filename,
                                               valgroup,
                                               "ANNSET_NOBEAT"
                                               "_ANNS"),
                            failcat="WARNING")
                        valrow3["XPATH"] = annsset_xmlnode_path + "/.." + \
                            codetype_path + "/" + rp

                        if valrow3["VALIOUT"] == "PASSED":
                            if n != "":
                                ann[n + "_unit"] = valrow3["VALUE"]
                            else:
                                ann["value_unit"] = valrow3["VALUE"]
                        if log_validation:
                            valpd = valpd.append(
                                pd.DataFrame([valrow3], columns=VALICOLS),
                                ignore_index=True)

                    # annotations time encoding, lead and other info used by
                    # value and supporting ROI
                    for rel_path4 in ["../support/supportingROI/component/"
                                      "boundary",
                                      "../component/annotation/support/"
                                      "supportingROI/component/boundary"]:
                        roinodes = subsubannsnode.xpath(
                            rel_path4.replace('/', '/ns:'),
                            namespaces={'ns': 'urn:hl7-org:v3'})
                        for roinode in roinodes:
                            valrow4 = validate_xpath(roinode,
                                                     "./code",
                                                     "urn:hl7-org:v3",
                                                     "code",
                                                     new_validation_row(
                                                         xml_filename,
                                                         valgroup,
                                                         "ANNSET_NOBEAT_ANNS"),
                                                     failcat="WARNING")
                            valrow4["XPATH"] = annsset_xmlnode_path + "/.." + \
                                codetype_path + "/" + rel_path4
                            if valrow4["VALIOUT"] == "PASSED":
                                if valrow4["VALUE"] in ["TIME_ABSOLUTE",
                                                        "TIME_RELATIVE"]:
                                    ann["timecode"] = valrow4["VALUE"]
                                else:
                                    ann["lead"] = valrow4["VALUE"]
                            if log_validation:
                                valpd = valpd.append(
                                    pd.DataFrame([valrow4], columns=VALICOLS),
                                    ignore_index=True)
                    aecgannset.anns.append(copy.deepcopy(ann))
            anngrpid = anngrpid + 1

    logger.info(
        f'{xml_filename},{zip_filename},'
        f'{valgroup} {anngrpid-anngrpid_from_beats} annotations groups'
        f' without an associated beat found')

    return aecgannset, valpd


def parse_generalinfo(aecg_doc: etree._ElementTree,
                      aecg: Aecg,
                      log_validation: bool = False) -> Aecg:
    """Parses `aecg_doc` XML document and extracts general information

    This function parses the `aecg_doc` xml document searching for general
    information that includes in the returned `Aecg`: unique identifier (UUID),
    ECG date and time of collection (EGDTC), and device information.

    Args:
        aecg_doc (etree._ElementTree): aECG XML document
        aecg (Aecg): The aECG object to update
        log_validation (bool, optional): Indicates whether to maintain the
            validation results in `aecg.validatorResults`. Defaults to
            False.

    Returns:
        Aecg: `aecg` updated with the information found in the xml document.
    """
    # =======================================
    # UUID
    # =======================================
    valrow = validate_xpath(aecg_doc,
                            "./*[local-name() = \"id\"]",
                            "",
                            "root",
                            new_validation_row(aecg.filename,
                                               "GENERAL",
                                               "UUID"))
    if log_validation:
        aecg.validatorResults = aecg.validatorResults.append(
            pd.DataFrame([valrow], columns=VALICOLS), ignore_index=True)
    if valrow["VALIOUT"] == "PASSED":
        logger.info(
            f'{aecg.filename},{aecg.zipContainer},'
            f'UUID found: {valrow["VALUE"]}')
        aecg.UUID = valrow["VALUE"]
    else:
        logger.critical(
            f'{aecg.filename},{aecg.zipContainer},'
            f'UUID not found')

    valrow = validate_xpath(aecg_doc,
                            "./*[local-name() = \"id\"]",
                            "",
                            "extension",
                            new_validation_row(aecg.filename,
                                               "GENERAL",
                                               "UUID"))
    if log_validation:
        aecg.validatorResults = aecg.validatorResults.append(
            pd.DataFrame([valrow], columns=VALICOLS), ignore_index=True)
    if valrow["VALIOUT"] == "PASSED":
        logger.debug(
            f'{aecg.filename},{aecg.zipContainer},'
            f'UUID extension found: {valrow["VALUE"]}')
        aecg.UUID += valrow["VALUE"]
        logger.info(
            f'{aecg.filename},{aecg.zipContainer},'
            f'UUID updated to: {aecg.UUID}')
    else:
        logger.debug(
            f'{aecg.filename},{aecg.zipContainer},'
            f'UUID extension not found')

    # =======================================
    # EGDTC
    # =======================================
    valpd = pd.DataFrame()
    egdtc_found = False
    for n in ["low", "center", "high"]:
        valrow = validate_xpath(aecg_doc,
                                "./*[local-name() = \"effectiveTime\"]/"
                                "*[local-name() = \"" + n + "\"]",
                                "",
                                "value",
                                new_validation_row(aecg.filename, "GENERAL",
                                                   "EGDTC_" + n),
                                "WARNING")
        if valrow["VALIOUT"] == "PASSED":
            egdtc_found = True
            logger.info(
                f'{aecg.filename},{aecg.zipContainer},'
                f'EGDTC {n} found: {valrow["VALUE"]}')
            aecg.EGDTC[n] = valrow["VALUE"]
        if log_validation:
            valpd = valpd.append(pd.DataFrame([valrow], columns=VALICOLS),
                                 ignore_index=True)
    if not egdtc_found:
        logger.critical(
            f'{aecg.filename},{aecg.zipContainer},'
            f'EGDTC not found')
    if log_validation:
        aecg.validatorResults = aecg.validatorResults.append(valpd,
                                                             ignore_index=True)

    # =======================================
    # DEVICE
    # =======================================
    # DEVICE = {"manufacturer": "", "model": "", "software": ""}

    valrow = validate_xpath(aecg_doc,
                            "./component/series/author/"
                            "seriesAuthor/manufacturerOrganization/name",
                            "urn:hl7-org:v3",
                            "",
                            new_validation_row(aecg.filename, "GENERAL",
                                               "DEVICE_manufacturer"),
                            "WARNING")
    if valrow["VALIOUT"] == "PASSED":
        tmp = valrow["VALUE"].replace("\n", "|")
        logger.info(
            f'{aecg.filename},{aecg.zipContainer},'
            f'DEVICE manufacturer found: {tmp}')
        aecg.DEVICE["manufacturer"] = valrow["VALUE"]
    else:
        logger.warning(
            f'{aecg.filename},{aecg.zipContainer},'
            f'DEVICE manufacturer not found')
    if log_validation:
        aecg.validatorResults = aecg.validatorResults.append(
            pd.DataFrame([valrow], columns=VALICOLS), ignore_index=True)

    valrow = validate_xpath(aecg_doc,
                            "./component/series/author/"
                            "seriesAuthor/manufacturedSeriesDevice/"
                            "manufacturerModelName",
                            "urn:hl7-org:v3",
                            "",
                            new_validation_row(aecg.filename, "GENERAL",
                                               "DEVICE_model"),
                            "WARNING")
    if valrow["VALIOUT"] == "PASSED":
        tmp = valrow["VALUE"].replace("\n", "|")
        logger.info(
            f'{aecg.filename},{aecg.zipContainer},'
            f'DEVICE model found: {tmp}')
        aecg.DEVICE["model"] = valrow["VALUE"]
    else:
        logger.warning(
            f'{aecg.filename},{aecg.zipContainer},'
            f'DEVICE model not found')
    if log_validation:
        aecg.validatorResults = aecg.validatorResults.append(
            pd.DataFrame([valrow], columns=VALICOLS), ignore_index=True)

    valrow = validate_xpath(aecg_doc,
                            "./component/series/author/"
                            "seriesAuthor/manufacturedSeriesDevice/"
                            "softwareName",
                            "urn:hl7-org:v3",
                            "",
                            new_validation_row(aecg.filename, "GENERAL",
                                               "DEVICE_software"),
                            "WARNING")
    if valrow["VALIOUT"] == "PASSED":
        tmp = valrow["VALUE"].replace("\n", "|")
        logger.info(
            f'{aecg.filename},{aecg.zipContainer},'
            f'DEVICE software found: {tmp}')
        aecg.DEVICE["software"] = valrow["VALUE"]
    else:
        logger.warning(
            f'{aecg.filename},{aecg.zipContainer},'
            f'DEVICE software not found')
    if log_validation:
        aecg.validatorResults = aecg.validatorResults.append(
            pd.DataFrame([valrow], columns=VALICOLS), ignore_index=True)

    return aecg


def parse_subjectinfo(aecg_doc: etree._ElementTree,
                      aecg: Aecg,
                      log_validation: bool = False) -> Aecg:
    """Parses `aecg_doc` XML document and extracts subject information

    This function parses the `aecg_doc` xml document searching for subject
    information that includes in the returned `Aecg`: subject unique identifier
    (USUBJID), gender, birthtime, and race.

    Args:
        aecg_doc (etree._ElementTree): aECG XML document
        aecg (Aecg): The aECG object to update
        log_validation (bool, optional): Indicates whether to maintain the
            validation results in `aecg.validatorResults`. Defaults to
            False.

    Returns:
        Aecg: `aecg` updated with the information found in the xml document.
    """
    # =======================================
    # USUBJID
    # =======================================
    valpd = pd.DataFrame()
    for n in ["root", "extension"]:
        valrow = validate_xpath(aecg_doc,
                                "./componentOf/timepointEvent/componentOf/"
                                "subjectAssignment/subject/trialSubject/id",
                                "urn:hl7-org:v3",
                                n,
                                new_validation_row(aecg.filename,
                                                   "SUBJECTINFO",
                                                   "USUBJID_" + n))
        if valrow["VALIOUT"] == "PASSED":
            logger.info(
                f'{aecg.filename},{aecg.zipContainer},'
                f'DM.USUBJID ID {n} found: {valrow["VALUE"]}')
            aecg.USUBJID[n] = valrow["VALUE"]
        else:
            if n == "root":
                logger.warning(
                    f'{aecg.filename},{aecg.zipContainer},'
                    f'DM.USUBJID ID {n} not found')
            else:
                logger.warning(
                    f'{aecg.filename},{aecg.zipContainer},'
                    f'DM.USUBJID ID {n} not found')
        if log_validation:
            valpd = valpd.append(pd.DataFrame([valrow], columns=VALICOLS),
                                 ignore_index=True)
    if (aecg.USUBJID["root"] == "") and (aecg.USUBJID["extension"] == ""):
        logger.error(
            f'{aecg.filename},{aecg.zipContainer},'
            f'DM.USUBJID cannot be established.')

    if log_validation:
        aecg.validatorResults = aecg.validatorResults.append(valpd,
                                                             ignore_index=True)

    # =======================================
    # SEX / GENDER
    # =======================================
    valrow = validate_xpath(aecg_doc,
                            "./componentOf/timepointEvent/componentOf/"
                            "subjectAssignment/subject/trialSubject/"
                            "subjectDemographicPerson/"
                            "administrativeGenderCode",
                            "urn:hl7-org:v3",
                            "code",
                            new_validation_row(aecg.filename, "SUBJECTINFO",
                                               "SEX"),
                            failcat="WARNING")
    if valrow["VALIOUT"] == "PASSED":
        logger.info(
            f'{aecg.filename},{aecg.zipContainer},'
            f'DM.SEX found: {valrow["VALUE"]}')
        aecg.SEX = valrow["VALUE"]
    else:
        logger.debug(
            f'{aecg.filename},{aecg.zipContainer},'
            f'DM.SEX not found')
    if log_validation:
        aecg.validatorResults = aecg.validatorResults.append(
            pd.DataFrame([valrow], columns=VALICOLS), ignore_index=True)

    # =======================================
    # BIRTHTIME
    # =======================================
    valrow = validate_xpath(aecg_doc,
                            "./componentOf/timepointEvent/componentOf/"
                            "subjectAssignment/subject/trialSubject/"
                            "subjectDemographicPerson/birthTime",
                            "urn:hl7-org:v3",
                            "value",
                            new_validation_row(aecg.filename, "SUBJECTINFO",
                                               "BIRTHTIME"),
                            failcat="WARNING")
    if valrow["VALIOUT"] == "PASSED":
        logger.info(
            f'{aecg.filename},{aecg.zipContainer},'
            f'DM.BIRTHTIME found.')
        aecg.BIRTHTIME = valrow["VALUE"]
        # age_in_years = aecg.subject_age_in_years()
    else:
        logger.debug(
            f'{aecg.filename},{aecg.zipContainer},'
            f'DM.BIRTHTIME not found')
    if log_validation:
        aecg.validatorResults = aecg.validatorResults.append(
            pd.DataFrame([valrow], columns=VALICOLS), ignore_index=True)

    # =======================================
    # RACE
    # =======================================
    valrow = validate_xpath(aecg_doc,
                            "./componentOf/timepointEvent/componentOf/"
                            "subjectAssignment/subject/trialSubject/"
                            "subjectDemographicPerson/raceCode",
                            "urn:hl7-org:v3",
                            "code",
                            new_validation_row(aecg.filename, "SUBJECTINFO",
                                               "RACE"),
                            failcat="WARNING")
    if valrow["VALIOUT"] == "PASSED":
        logger.info(
            f'{aecg.filename},{aecg.zipContainer},'
            f'DM.RACE found:  {valrow["VALUE"]}')
    else:
        logger.debug(
            f'{aecg.filename},{aecg.zipContainer},'
            f'DM.RACE not found')
        aecg.RACE = valrow["VALUE"]
    if log_validation:
        aecg.validatorResults = aecg.validatorResults.append(
            pd.DataFrame([valrow], columns=VALICOLS), ignore_index=True)

    return aecg


def parse_trtainfo(aecg_doc: etree._ElementTree,
                   aecg: Aecg,
                   log_validation: bool = False) -> Aecg:
    """Parses `aecg_doc` XML document and extracts subject information

    This function parses the `aecg_doc` xml document searching for treatment
    information that includes in the returned `Aecg`.

    Args:
        aecg_doc (etree._ElementTree): aECG XML document
        aecg (Aecg): The aECG object to update
        log_validation (bool, optional): Indicates whether to maintain the
            validation results in `aecg.validatorResults`. Defaults to
            False.

    Returns:
        Aecg: `aecg` updated with the information found in the xml document.
    """
    valrow = validate_xpath(aecg_doc,
                            "./componentOf/timepointEvent/componentOf/"
                            "subjectAssignment/definition/"
                            "treatmentGroupAssignment/code",
                            "urn:hl7-org:v3",
                            "code",
                            new_validation_row(aecg.filename, "STUDYINFO",
                                               "TRTA"),
                            failcat="WARNING")
    if valrow["VALIOUT"] == "PASSED":
        logger.info(
            f'{aecg.filename},{aecg.zipContainer},'
            f'TRTA information found: {valrow["VALUE"]}')
        aecg.TRTA = valrow["VALUE"]
    else:
        logger.debug(
            f'{aecg.filename},{aecg.zipContainer},'
            f'TRTA information not found')
    if log_validation:
        aecg.validatorResults = aecg.validatorResults.append(
            pd.DataFrame([valrow], columns=VALICOLS), ignore_index=True)

    return aecg


def parse_studyinfo(aecg_doc: etree._ElementTree,
                    aecg: Aecg,
                    log_validation: bool = False) -> Aecg:
    """Parses `aecg_doc` XML document and extracts study information

    This function parses the `aecg_doc` xml document searching for study
    information that includes in the returned `Aecg`: study unique identifier
    (STUDYID), and study title.

    Args:
        aecg_doc (etree._ElementTree): aECG XML document
        aecg (Aecg): The aECG object to update
        log_validation (bool, optional): Indicates whether to maintain the
            validation results in `aecg.validatorResults`. Defaults to
            False.

    Returns:
        Aecg: `aecg` updated with the information found in the xml document.
    """
    valpd = pd.DataFrame()
    for n in ["root", "extension"]:
        valrow = validate_xpath(aecg_doc,
                                "./componentOf/timepointEvent/componentOf/"
                                "subjectAssignment/componentOf/"
                                "clinicalTrial/id",
                                "urn:hl7-org:v3",
                                n,
                                new_validation_row(aecg.filename,
                                                   "STUDYINFO",
                                                   "STUDYID_" + n),
                                failcat="WARNING")
        if valrow["VALIOUT"] == "PASSED":
            logger.info(
                f'{aecg.filename},{aecg.zipContainer},'
                f'STUDYID {n} found: {valrow["VALUE"]}')
            aecg.STUDYID[n] = valrow["VALUE"]
        else:
            logger.debug(
                f'{aecg.filename},{aecg.zipContainer},'
                f'STUDYID {n} not found')
        if log_validation:
            valpd = valpd.append(pd.DataFrame([valrow], columns=VALICOLS),
                                 ignore_index=True)
    if log_validation:
        aecg.validatorResults = \
            aecg.validatorResults.append(valpd, ignore_index=True)

    valrow = validate_xpath(aecg_doc,
                            "./componentOf/timepointEvent/componentOf/"
                            "subjectAssignment/componentOf/"
                            "clinicalTrial/title",
                            "urn:hl7-org:v3",
                            "",
                            new_validation_row(aecg.filename, "STUDYINFO",
                                               "STUDYTITLE"),
                            failcat="WARNING")
    if valrow["VALIOUT"] == "PASSED":
        tmp = valrow["VALUE"].replace("\n", "")
        logger.info(
            f'{aecg.filename},{aecg.zipContainer},'
            f'STUDYTITLE found: {tmp}')
        aecg.STUDYTITLE = valrow["VALUE"]
    else:
        logger.debug(
            f'{aecg.filename},{aecg.zipContainer},'
            f'STUDYTITLE not found')

    if log_validation:
        aecg.validatorResults = aecg.validatorResults.append(
            pd.DataFrame([valrow], columns=VALICOLS), ignore_index=True)

    return aecg


def parse_timepoints(aecg_doc: etree._ElementTree,
                     aecg: Aecg,
                     log_validation: bool = False) -> Aecg:
    """Parses `aecg_doc` XML document and extracts timepoints information

    This function parses the `aecg_doc` xml document searching for timepoints
    information that includes in the returned `Aecg`: absolute timepoint or
    study event information (TPT), relative timepoint or study event relative
    to a reference event (RTPT), and protocol timepoint information (PTPT).

    Args:
        aecg_doc (etree._ElementTree): aECG XML document
        aecg (Aecg): The aECG object to update
        log_validation (bool, optional): Indicates whether to maintain the
            validation results in `aecg.validatorResults`. Defaults to
            False.

    Returns:
        Aecg: `aecg` updated with the information found in the xml document.
    """
    # =======================================
    # TPT
    # =======================================
    valpd = pd.DataFrame()
    for n in ["code", "displayName"]:
        valrow = validate_xpath(aecg_doc,
                                "./componentOf/timepointEvent/code",
                                "urn:hl7-org:v3",
                                n,
                                new_validation_row(aecg.filename,
                                                   "STUDYINFO",
                                                   "TPT_" + n),
                                failcat="WARNING")
        if valrow["VALIOUT"] == "PASSED":
            logger.info(
                f'{aecg.filename},{aecg.zipContainer},'
                f'TPT {n} found: {valrow["VALUE"]}')
            aecg.TPT[n] = valrow["VALUE"]
        else:
            logger.debug(
                f'{aecg.filename},{aecg.zipContainer},'
                f'TPT {n} not found')
        if log_validation:
            valpd = valpd.append(pd.DataFrame([valrow], columns=VALICOLS),
                                 ignore_index=True)
    if log_validation:
        aecg.validatorResults = \
            aecg.validatorResults.append(valpd, ignore_index=True)

    valrow = validate_xpath(aecg_doc,
                            "./componentOf/timepointEvent/reasonCode",
                            "urn:hl7-org:v3",
                            "code",
                            new_validation_row(aecg.filename, "STUDYINFO",
                                               "TPT_reasonCode"),
                            failcat="WARNING")
    if valrow["VALIOUT"] == "PASSED":
        logger.info(
            f'{aecg.filename},{aecg.zipContainer},'
            f'TPT reasonCode found: {valrow["VALUE"]}')
        aecg.TPT["reasonCode"] = valrow["VALUE"]
    else:
        logger.debug(
            f'{aecg.filename},{aecg.zipContainer},'
            f'TPT reasonCode not found')
    if log_validation:
        aecg.validatorResults = aecg.validatorResults.append(
            pd.DataFrame([valrow], columns=VALICOLS), ignore_index=True)

    valpd = pd.DataFrame()
    for n in ["low", "high"]:
        valrow = validate_xpath(aecg_doc,
                                "./componentOf/timepointEvent/"
                                "effectiveTime/" + n,
                                "urn:hl7-org:v3",
                                "value",
                                new_validation_row(aecg.filename,
                                                   "STUDYINFO",
                                                   "TPT_" + n),
                                failcat="WARNING")
        if valrow["VALIOUT"] == "PASSED":
            logger.info(
                f'{aecg.filename},{aecg.zipContainer},'
                f'TPT {n} found: {valrow["VALUE"]}')
            aecg.TPT[n] = valrow["VALUE"]
        else:
            logger.debug(
                f'{aecg.filename},{aecg.zipContainer},'
                f'TPT {n} not found')
        if log_validation:
            valpd = valpd.append(pd.DataFrame([valrow], columns=VALICOLS),
                                 ignore_index=True)
    if log_validation:
        aecg.validatorResults = \
            aecg.validatorResults.append(valpd, ignore_index=True)

    # =======================================
    # RTPT
    # =======================================
    valpd = pd.DataFrame()
    for n in ["code", "displayName"]:
        valrow = validate_xpath(aecg_doc,
                                "./definition/relativeTimepoint/code",
                                "urn:hl7-org:v3",
                                "code",
                                new_validation_row(aecg.filename,
                                                   "STUDYINFO",
                                                   "RTPT_" + n),
                                failcat="WARNING")
        if valrow["VALIOUT"] == "PASSED":
            logger.info(
                f'{aecg.filename},{aecg.zipContainer},'
                f'RTPT {n} found: {valrow["VALUE"]}')
            aecg.RTPT[n] = valrow["VALUE"]
        else:
            logger.debug(
                f'{aecg.filename},{aecg.zipContainer},'
                f'RTPT {n} not found')
        if log_validation:
            valpd = valpd.append(pd.DataFrame([valrow], columns=VALICOLS),
                                 ignore_index=True)
    if log_validation:
        aecg.validatorResults = \
            aecg.validatorResults.append(valpd, ignore_index=True)

    valrow = validate_xpath(aecg_doc,
                            "./definition/relativeTimepoint/componentOf/"
                            "pauseQuantity",
                            "urn:hl7-org:v3",
                            "value",
                            new_validation_row(aecg.filename, "STUDYINFO",
                                               "RTPT_pauseQuantity"),
                            failcat="WARNING")
    if valrow["VALIOUT"] == "PASSED":
        logger.info(
            f'{aecg.filename},{aecg.zipContainer},'
            f'RTPT pauseQuantity value found: {valrow["VALUE"]}')
        aecg.RTPT["pauseQuantity"] = valrow["VALUE"]
    else:
        logger.debug(
            f'{aecg.filename},{aecg.zipContainer},'
            f'RTPT pauseQuantity value not found')
    if log_validation:
        aecg.validatorResults = \
            aecg.validatorResults.append(pd.DataFrame([valrow],
                                                      columns=VALICOLS),
                                         ignore_index=True)

    valrow = validate_xpath(aecg_doc,
                            "./definition/relativeTimepoint/componentOf/"
                            "pauseQuantity",
                            "urn:hl7-org:v3",
                            "unit",
                            new_validation_row(aecg.filename, "STUDYINFO",
                                               "RTPT_pauseQuantity_unit"),
                            failcat="WARNING")
    if valrow["VALIOUT"] == "PASSED":
        logger.info(
            f'{aecg.filename},{aecg.zipContainer},'
            f'RTPT pauseQuantity unit found: {valrow["VALUE"]}')
        aecg.RTPT["pauseQuantity_unit"] = valrow["VALUE"]
    else:
        logger.debug(
            f'{aecg.filename},{aecg.zipContainer},'
            f'RTPT pauseQuantity unit not found')
    if log_validation:
        aecg.validatorResults = \
            aecg.validatorResults.append(pd.DataFrame([valrow],
                                                      columns=VALICOLS),
                                         ignore_index=True)

    # =======================================
    # PTPT
    # =======================================
    valpd = pd.DataFrame()
    for n in ["code", "displayName"]:
        valrow = validate_xpath(aecg_doc,
                                "./definition/relativeTimepoint/"
                                "componentOf/protocolTimepointEvent/code",
                                "urn:hl7-org:v3",
                                n,
                                new_validation_row(aecg.filename,
                                                   "STUDYINFO",
                                                   "PTPT_" + n),
                                failcat="WARNING")
        if valrow["VALIOUT"] == "PASSED":
            logger.info(
                f'{aecg.filename},{aecg.zipContainer},'
                f'PTPT {n} found: {valrow["VALUE"]}')
            aecg.PTPT[n] = valrow["VALUE"]
        else:
            logger.debug(
                f'{aecg.filename},{aecg.zipContainer},'
                f'PTPT {n} not found')
        if log_validation:
            valpd = valpd.append(pd.DataFrame([valrow], columns=VALICOLS),
                                 ignore_index=True)
    if log_validation:
        aecg.validatorResults = \
            aecg.validatorResults.append(valpd, ignore_index=True)

    valrow = validate_xpath(aecg_doc,
                            "./definition/relativeTimepoint/componentOf/"
                            "protocolTimepointEvent/component/"
                            "referenceEvent/code",
                            "urn:hl7-org:v3",
                            "code",
                            new_validation_row(aecg.filename, "STUDYINFO",
                                               "PTPT_referenceEvent"),
                            failcat="WARNING")
    if valrow["VALIOUT"] == "PASSED":
        logger.info(
            f'{aecg.filename},{aecg.zipContainer},'
            f'PTPT referenceEvent code found: {valrow["VALUE"]}')
        aecg.PTPT["referenceEvent"] = valrow["VALUE"]
    else:
        logger.debug(
            f'{aecg.filename},{aecg.zipContainer},'
            f'PTPT referenceEvent code not found')
    if log_validation:
        aecg.validatorResults = \
            aecg.validatorResults.append(pd.DataFrame([valrow],
                                                      columns=VALICOLS),
                                         ignore_index=True)

    valrow = validate_xpath(aecg_doc,
                            "./definition/relativeTimepoint/componentOf/"
                            "protocolTimepointEvent/component/"
                            "referenceEvent/code",
                            "urn:hl7-org:v3",
                            "displayName",
                            new_validation_row(aecg.filename, "STUDYINFO",
                                               "PTPT_referenceEvent_"
                                               "displayName"),
                            failcat="WARNING")
    if valrow["VALIOUT"] == "PASSED":
        logger.info(
            f'{aecg.filename},{aecg.zipContainer},'
            f'PTPT referenceEvent displayName found: '
            f'{valrow["VALUE"]}')
        aecg.PTPT["referenceEvent_displayName"] = valrow["VALUE"]
    else:
        logger.debug(
            f'{aecg.filename},{aecg.zipContainer},'
            f'PTPT referenceEvent displayName not found')
    if log_validation:
        aecg.validatorResults = \
            aecg.validatorResults.append(pd.DataFrame([valrow],
                                                      columns=VALICOLS),
                                         ignore_index=True)
    return aecg


def parse_rhythm_waveform_info(aecg_doc: etree._ElementTree,
                               aecg: Aecg,
                               log_validation: bool = False) -> Aecg:
    """Parses `aecg_doc` XML document and extracts rhythm waveform information

    This function parses the `aecg_doc` xml document searching for rhythm
    waveform information that includes in the returned `Aecg`: waveform
    identifier, code, display name, and date and time of collection.

    Args:
        aecg_doc (etree._ElementTree): aECG XML document
        aecg (Aecg): The aECG object to update
        log_validation (bool, optional): Indicates whether to maintain the
            validation results in `aecg.validatorResults`. Defaults to
            False.

    Returns:
        Aecg: `aecg` updated with the information found in the xml document.
    """
    valpd = pd.DataFrame()
    for n in ["root", "extension"]:
        valrow = validate_xpath(aecg_doc,
                                "./component/series/id",
                                "urn:hl7-org:v3",
                                n,
                                new_validation_row(aecg.filename, "RHYTHM",
                                                   "ID_" + n),
                                failcat="WARNING")
        if valrow["VALIOUT"] == "PASSED":
            logger.info(
                f'{aecg.filename},{aecg.zipContainer},'
                f'RHYTHM ID {n} found: {valrow["VALUE"]}')
            aecg.RHYTHMID[n] = valrow["VALUE"]
        else:
            if n == "root":
                logger.warning(
                    f'{aecg.filename},{aecg.zipContainer},'
                    f'RHYTHM ID {n} not found')
            else:
                logger.warning(
                    f'{aecg.filename},{aecg.zipContainer},'
                    f'RHYTHM ID {n} not found')
        if log_validation:
            valpd = valpd.append(pd.DataFrame([valrow], columns=VALICOLS),
                                 ignore_index=True)
    if log_validation:
        aecg.validatorResults = \
            aecg.validatorResults.append(valpd, ignore_index=True)

    valrow = validate_xpath(aecg_doc,
                            "./component/series/code",
                            "urn:hl7-org:v3",
                            "code",
                            new_validation_row(aecg.filename, "RHYTHM",
                                               "CODE"),
                            failcat="WARNING")
    if valrow["VALIOUT"] == "PASSED":
        logger.debug(
            f'{aecg.filename},{aecg.zipContainer},'
            f'RHYTHM code found: {valrow["VALUE"]}')
        aecg.RHYTHMCODE["code"] = valrow["VALUE"]
        if aecg.RHYTHMCODE["code"] != "RHYTHM":
            logger.warning(
                f'{aecg.filename},{aecg.zipContainer},'
                f'RHYTHM unexpected code found: {valrow["VALUE"]}')
            valrow["VALIOUT"] = "WARNING"
            valrow["VALIMSG"] = "Unexpected value found"
    else:
        logger.warning(
            f'{aecg.filename},{aecg.zipContainer},'
            f'RHYTHM code not found')
    if log_validation:
        aecg.validatorResults = aecg.validatorResults.append(
            pd.DataFrame([valrow], columns=VALICOLS), ignore_index=True)

    valrow = validate_xpath(aecg_doc,
                            "./component/series/code",
                            "urn:hl7-org:v3",
                            "displayName",
                            new_validation_row(aecg.filename, "RHYTHM",
                                               "CODE_displayName"),
                            failcat="WARNING")
    if valrow["VALIOUT"] == "PASSED":
        logger.debug(
            f'{aecg.filename},{aecg.zipContainer},'
            f'RHYTHM displayName found: {valrow["VALUE"]}')
        aecg.RHYTHMCODE["displayName"] = valrow["VALUE"]
    else:
        logger.debug(
            f'{aecg.filename},{aecg.zipContainer},'
            f'RHYTHM displayName not found')
    if log_validation:
        aecg.validatorResults = aecg.validatorResults.append(
            pd.DataFrame([valrow], columns=VALICOLS), ignore_index=True)

    valpd = pd.DataFrame()
    for n in ["low", "high"]:
        valrow = validate_xpath(aecg_doc,
                                "./component/series/effectiveTime/" + n,
                                "urn:hl7-org:v3",
                                "value",
                                new_validation_row(aecg.filename, "RHYTHM",
                                                   "EGDTC_" + n),
                                failcat="WARNING")
        if valrow["VALIOUT"] == "PASSED":
            logger.info(
                f'{aecg.filename},{aecg.zipContainer},'
                f'RHYTHMEGDTC {n} found: {valrow["VALUE"]}')
            aecg.RHYTHMEGDTC[n] = valrow["VALUE"]
        else:
            logger.debug(
                f'{aecg.filename},{aecg.zipContainer},'
                f'RHYTHMEGDTC {n} not found')
        if log_validation:
            valpd = valpd.append(pd.DataFrame([valrow], columns=VALICOLS),
                                 ignore_index=True)
    if log_validation:
        aecg.validatorResults = \
            aecg.validatorResults.append(valpd, ignore_index=True)
    return aecg


def parse_derived_waveform_info(aecg_doc: etree._ElementTree,
                                aecg: Aecg,
                                log_validation: bool = False) -> Aecg:
    """Parses `aecg_doc` XML document and extracts derived waveform information

    This function parses the `aecg_doc` xml document searching for derived
    waveform information that includes in the returned `Aecg`: waveform
    identifier, code, display name, and date and time of collection.

    Args:
        aecg_doc (etree._ElementTree): aECG XML document
        aecg (Aecg): The aECG object to update
        log_validation (bool, optional): Indicates whether to maintain the
            validation results in `aecg.validatorResults`. Defaults to
            False.

    Returns:
        Aecg: `aecg` updated with the information found in the xml document.
    """
    valpd = pd.DataFrame()
    for n in ["root", "extension"]:
        valrow = validate_xpath(aecg_doc,
                                "./component/series/derivation/"
                                "derivedSeries/id",
                                "urn:hl7-org:v3",
                                n,
                                new_validation_row(aecg.filename, "DERIVED",
                                                   "ID_" + n),
                                failcat="WARNING")
        if valrow["VALIOUT"] == "PASSED":
            logger.info(
                f'{aecg.filename},{aecg.zipContainer},'
                f'DERIVED ID {n} found: {valrow["VALUE"]}')
            aecg.DERIVEDID[n] = valrow["VALUE"]
        else:
            if n == "root":
                logger.warning(
                    f'{aecg.filename},{aecg.zipContainer},'
                    f'DERIVED ID {n} not found')
            else:
                logger.warning(
                    f'{aecg.filename},{aecg.zipContainer},'
                    f'DERIVED ID {n} not found')
        if log_validation:
            valpd = valpd.append(pd.DataFrame([valrow], columns=VALICOLS),
                                 ignore_index=True)
    if log_validation:
        aecg.validatorResults = \
            aecg.validatorResults.append(valpd, ignore_index=True)

    valrow = validate_xpath(aecg_doc,
                            "./component/series/derivation/"
                            "derivedSeries/code",
                            "urn:hl7-org:v3",
                            "code",
                            new_validation_row(aecg.filename, "DERIVED",
                                               "CODE"),
                            failcat="WARNING")
    if valrow["VALIOUT"] == "PASSED":
        logger.debug(
            f'{aecg.filename},{aecg.zipContainer},'
            f'DERIVED code found: {valrow["VALUE"]}')
        aecg.DERIVEDCODE["code"] = valrow["VALUE"]
        if aecg.DERIVEDCODE["code"] != "REPRESENTATIVE_BEAT":
            logger.warning(
                f'{aecg.filename},{aecg.zipContainer},'
                f'DERIVED unexpected code found: {valrow["VALUE"]}')
            valrow["VALIOUT"] = "WARNING"
            valrow["VALIMSG"] = "Unexpected value found"
    else:
        logger.warning(
            f'{aecg.filename},{aecg.zipContainer},'
            f'DERIVED code not found')
    if log_validation:
        aecg.validatorResults = aecg.validatorResults.append(
            pd.DataFrame([valrow], columns=VALICOLS), ignore_index=True)

    valrow = validate_xpath(aecg_doc,
                            "./component/series/derivation/"
                            "derivedSeries/code",
                            "urn:hl7-org:v3",
                            "displayName",
                            new_validation_row(aecg.filename, "DERIVED",
                                               "CODE_displayName"),
                            failcat="WARNING")
    if valrow["VALIOUT"] == "PASSED":
        logger.debug(
            f'{aecg.filename},{aecg.zipContainer},'
            f'DERIVED displayName found: {valrow["VALUE"]}')
        aecg.DERIVEDCODE["displayName"] = valrow["VALUE"]
    else:
        logger.debug(
            f'{aecg.filename},{aecg.zipContainer},'
            f'DERIVED displayName not found')
    if log_validation:
        aecg.validatorResults = aecg.validatorResults.append(
            pd.DataFrame([valrow], columns=VALICOLS), ignore_index=True)

    valpd = pd.DataFrame()
    for n in ["low", "high"]:
        valrow = validate_xpath(aecg_doc,
                                "./component/series/derivation/"
                                "derivedSeries/effectiveTime/" + n,
                                "urn:hl7-org:v3",
                                "value",
                                new_validation_row(aecg.filename, "DERIVED",
                                                   "EGDTC_" + n),
                                failcat="WARNING")
        if valrow["VALIOUT"] == "PASSED":
            logger.info(
                f'{aecg.filename},{aecg.zipContainer},'
                f'DERIVEDEGDTC {n} found: {valrow["VALUE"]}')
            aecg.DERIVEDEGDTC[n] = valrow["VALUE"]
        else:
            logger.debug(
                f'{aecg.filename},{aecg.zipContainer},'
                f'DERIVEDEGDTC {n} not found')
        if log_validation:
            valpd = valpd.append(pd.DataFrame([valrow], columns=VALICOLS),
                                 ignore_index=True)
    if log_validation:
        aecg.validatorResults = \
            aecg.validatorResults.append(valpd, ignore_index=True)

    return aecg


def parse_rhythm_waveform_timeseries(aecg_doc: etree._ElementTree,
                                     aecg: Aecg,
                                     include_digits: bool = False,
                                     log_validation: bool = False) -> Aecg:
    """Parses `aecg_doc` XML document and extracts rhythm's timeseries

    This function parses the `aecg_doc` xml document searching for rhythm
    waveform timeseries (sequences) information that includes in the returned
    :any:`Aecg`. Each found sequence is stored as an :any:`AecgLead` in the
    :any:`Aecg.RHYTHMLEADS` list of the returned :any:`Aecg`.

    Args:
        aecg_doc (etree._ElementTree): aECG XML document
        aecg (Aecg): The aECG object to update
        include_digits (bool, optional): Indicates whether to include the
            digits information in the returned `Aecg`.
        log_validation (bool, optional): Indicates whether to maintain the
            validation results in `aecg.validatorResults`. Defaults to
            False.

    Returns:
        Aecg: `aecg` updated with the information found in the xml document.
    """
    path_prefix = './component/series/component/sequenceSet/' \
                  'component/sequence'
    seqnodes = aecg_doc.xpath((path_prefix + '/code').replace('/', '/ns:'),
                              namespaces={'ns': 'urn:hl7-org:v3'})
    if len(seqnodes) > 0:
        logger.info(
            f'{aecg.filename},{aecg.zipContainer},'
            f'RHYTHM sequenceSet(s) found: '
            f'{len(seqnodes)} sequenceSet nodes')
    else:
        logger.warning(
            f'{aecg.filename},{aecg.zipContainer},'
            f'RHYTHM sequenceSet not found')

    for xmlnode in seqnodes:
        xmlnode_path = aecg_doc.getpath(xmlnode)
        valrow = validate_xpath(aecg_doc,
                                xmlnode_path,
                                "urn:hl7-org:v3",
                                "code",
                                new_validation_row(aecg.filename, "RHYTHM",
                                                   "SEQUENCE_CODE"),
                                failcat="WARNING")
        valpd = pd.DataFrame()
        if valrow["VALIOUT"] == "PASSED":
            if not valrow["VALUE"] in SEQUENCE_CODES:
                logger.warning(
                    f'{aecg.filename},{aecg.zipContainer},'
                    f'RHYTHM unexpected sequenceSet code '
                    f'found: {valrow["VALUE"]}')
                valrow["VALIOUT"] = "WARNING"
                valrow["VALIMSG"] = "Unexpected sequence code found"
            if valrow["VALUE"] in TIME_CODES:
                logger.info(
                    f'{aecg.filename},{aecg.zipContainer},'
                    f'RHYTHM sequenceSet code found: {valrow["VALUE"]}')
                aecg.RHYTHMTIME["code"] = valrow["VALUE"]
                # Retrieve time head info from value node
                rel_path = "../value/head"
                valrow2 = validate_xpath(
                    xmlnode,
                    rel_path,
                    "urn:hl7-org:v3",
                    "value",
                    new_validation_row(
                        aecg.filename, "RHYTHM", "SEQUENCE_TIME_HEAD"),
                    failcat="WARNING")
                valrow2["XPATH"] = xmlnode_path + "/" + rel_path
                if valrow2["VALIOUT"] == "PASSED":
                    logger.info(
                        f'{aecg.filename},{aecg.zipContainer},'
                        f'RHYTHM SEQUENCE_TIME_HEAD found: {valrow2["VALUE"]}')
                    aecg.RHYTHMTIME["head"] = valrow2["VALUE"]
                else:
                    logger.debug(
                        f'{aecg.filename},{aecg.zipContainer},'
                        f'RHYTHM SEQUENCE_TIME_HEAD not found')
                if log_validation:
                    valpd = valpd.append(
                        pd.DataFrame([valrow2], columns=VALICOLS),
                        ignore_index=True)
                # Retrieve time increment info from value node
                rel_path = "../value/increment"
                for n in ["value", "unit"]:
                    valrow2 = validate_xpath(
                        xmlnode,
                        rel_path,
                        "urn:hl7-org:v3",
                        n,
                        new_validation_row(
                            aecg.filename, "RHYTHM", "SEQUENCE_TIME_" + n),
                        failcat="WARNING")
                    valrow2["XPATH"] = xmlnode_path + "/" + rel_path
                    if valrow2["VALIOUT"] == "PASSED":
                        logger.info(
                            f'{aecg.filename},{aecg.zipContainer},'
                            f'RHYTHM SEQUENCE_TIME_{n} found: '
                            f'{valrow2["VALUE"]}')
                        if n == "value":
                            aecg.RHYTHMTIME["increment"] = float(
                                valrow2["VALUE"])
                        else:
                            aecg.RHYTHMTIME[n] = valrow2["VALUE"]
                    if log_validation:
                        valpd = \
                            valpd.append(pd.DataFrame([valrow2],
                                                      columns=VALICOLS),
                                         ignore_index=True)
            else:
                logger.info(
                    f'{aecg.filename},{aecg.zipContainer},'
                    f'RHYTHM sequenceSet code found: '
                    f'{valrow["VALUE"]}')
                logger.info(
                    f'{aecg.filename},{aecg.zipContainer},'
                    f'LEADNAME from RHYTHM sequenceSet code: '
                    f'{valrow["VALUE"]}')
                # Assume is a lead
                aecglead = AecgLead()
                aecglead.leadname = valrow["VALUE"]
                # Inherit last parsed RHYTHMTIME
                aecglead.LEADTIME = copy.deepcopy(aecg.RHYTHMTIME)
                # Retrive lead origin info
                rel_path = "../value/origin"
                for n in ["value", "unit"]:
                    valrow2 = validate_xpath(
                        xmlnode,
                        rel_path,
                        "urn:hl7-org:v3",
                        n,
                        new_validation_row(
                            aecg.filename, "RHYTHM",
                            "SEQUENCE_LEAD_ORIGIN_" + n),
                        failcat="WARNING")
                    valrow2["XPATH"] = xmlnode_path + "/" + rel_path
                    if valrow2["VALIOUT"] == "PASSED":
                        logger.info(
                            f'{aecg.filename},{aecg.zipContainer},'
                            f'RHYTHM SEQUENCE_LEAD_ORIGIN_{n} '
                            f'found: {valrow2["VALUE"]}')
                        if n == "value":
                            try:
                                aecglead.origin = float(valrow2["VALUE"])
                            except Exception as ex:
                                valrow2["VALIOUT"] == "ERROR"
                                valrow2["VALIMSG"] = "SEQUENCE_LEAD_"\
                                                     "ORIGIN is not a "\
                                                     "number"
                        else:
                            aecglead.origin_unit = valrow2["VALUE"]
                    else:
                        logger.debug(
                            f'{aecg.filename},{aecg.zipContainer},'
                            f'RHYTHM SEQUENCE_LEAD_ORIGIN_{n} not found')
                    if log_validation:
                        valpd = valpd.append(
                            pd.DataFrame([valrow2], columns=VALICOLS),
                            ignore_index=True)
                # Retrive lead scale info
                rel_path = "../value/scale"
                for n in ["value", "unit"]:
                    valrow2 = validate_xpath(
                        xmlnode,
                        rel_path,
                        "urn:hl7-org:v3",
                        n,
                        new_validation_row(
                            aecg.filename, "RHYTHM",
                            "SEQUENCE_LEAD_SCALE_" + n),
                        failcat="WARNING")
                    valrow2["XPATH"] = xmlnode_path + "/" + rel_path
                    if valrow2["VALIOUT"] == "PASSED":
                        logger.info(
                            f'{aecg.filename},{aecg.zipContainer},'
                            f'RHYTHM SEQUENCE_LEAD_SCALE_{n} '
                            f'found: {valrow2["VALUE"]}')
                        if n == "value":
                            try:
                                aecglead.scale = float(valrow2["VALUE"])
                            except Exception as ex:
                                logger.error(
                                    f'{aecg.filename},{aecg.zipContainer},'
                                    f'RHYTHM SEQUENCE_LEAD_SCALE '
                                    f'value is not a valid number: \"{ex}\"')
                                valrow2["VALIOUT"] == "ERROR"
                                valrow2["VALIMSG"] = "SEQUENCE_LEAD_"\
                                                     "SCALE is not a "\
                                                     "number"
                        else:
                            aecglead.scale_unit = valrow2["VALUE"]
                    else:
                        logger.debug(
                            f'{aecg.filename},{aecg.zipContainer},'
                            f'RHYTHM SEQUENCE_LEAD_SCALE_{n} not found')
                    if log_validation:
                        valpd = valpd.append(
                            pd.DataFrame([valrow2], columns=VALICOLS),
                            ignore_index=True)
                # Include digits if requested
                if include_digits:
                    rel_path = "../value/digits"
                    valrow2 = validate_xpath(
                        xmlnode,
                        rel_path,
                        "urn:hl7-org:v3",
                        "",
                        new_validation_row(
                            aecg.filename, "RHYTHM", "SEQUENCE_LEAD_DIGITS"),
                        failcat="WARNING")
                    valrow2["XPATH"] = xmlnode_path + "/" + rel_path
                    if valrow2["VALIOUT"] == "PASSED":
                        try:
                            # Convert string of digits to list of integers
                            # remove new lines
                            sdigits = valrow2["VALUE"].replace("\n", " ")
                            # remove carriage retruns
                            sdigits = sdigits.replace("\r", " ")
                            # remove tabs
                            sdigits = sdigits.replace("\t", " ")
                            # collapse 2 or more spaces into 1 space char
                            # and remove leading/trailing white spaces
                            sdigits = re.sub("\\s+", " ", sdigits).strip()
                            # Convert string into list of integers
                            aecglead.digits = [int(s) for s in
                                               sdigits.split(' ')]
                            logger.info(
                                f'{aecg.filename},{aecg.zipContainer},'
                                f'DIGITS added to lead'
                                f' {aecglead.leadname} (n: '
                                f'{len(aecglead.digits)})')
                        except Exception as ex:
                            logger.error(
                                f'{aecg.filename},{aecg.zipContainer},'
                                f'Error parsing DIGITS from '
                                f'string to list of integers: \"{ex}\"')
                            valrow2["VALIOUT"] == "ERROR"
                            valrow2["VALIMSG"] = "Error parsing SEQUENCE_"\
                                                 "LEAD_DIGITS from string"\
                                                 " to list of integers"
                    else:
                        logger.error(
                            f'{aecg.filename},{aecg.zipContainer},'
                            f'DIGITS not found for lead {aecglead.leadname}')
                    if log_validation:
                        valpd = valpd.append(
                            pd.DataFrame([valrow2], columns=VALICOLS),
                            ignore_index=True)
                else:
                    logger.info(
                        f'{aecg.filename},{aecg.zipContainer},'
                        f'DIGITS were not requested by the user')
                aecg.RHYTHMLEADS.append(copy.deepcopy(aecglead))
        else:
            logger.warning(
                f'{aecg.filename},{aecg.zipContainer},'
                f'RHYTHM sequenceSet code not found')

        if log_validation:
            aecg.validatorResults = aecg.validatorResults.append(
                pd.DataFrame([valrow], columns=VALICOLS),
                ignore_index=True)
            if valpd.shape[0] > 0:
                aecg.validatorResults = \
                    aecg.validatorResults.append(valpd, ignore_index=True)

    return aecg


def parse_derived_waveform_timeseries(aecg_doc: etree._ElementTree,
                                      aecg: Aecg,
                                      include_digits: bool = False,
                                      log_validation: bool = False):
    """Parses `aecg_doc` XML document and extracts derived's timeseries

    This function parses the `aecg_doc` xml document searching for derived
    waveform timeseries (sequences) information that includes in the returned
    :any:`Aecg`. Each found sequence is stored as an :any:`AecgLead` in the
    :any:`Aecg.DERIVEDLEADS` list of the returned :any:`Aecg`.

    Args:
        aecg_doc (etree._ElementTree): aECG XML document
        aecg (Aecg): The aECG object to update
        include_digits (bool, optional): Indicates whether to include the
            digits information in the returned `Aecg`.
        log_validation (bool, optional): Indicates whether to maintain the
            validation results in `aecg.validatorResults`. Defaults to
            False.

    Returns:
        Aecg: `aecg` updated with the information found in the xml document.
    """
    path_prefix = './component/series/derivation/derivedSeries/component'\
                  '/sequenceSet/component/sequence'
    seqnodes = aecg_doc.xpath((path_prefix + '/code').replace('/', '/ns:'),
                              namespaces={'ns': 'urn:hl7-org:v3'})
    if len(seqnodes) > 0:
        logger.info(
            f'{aecg.filename},{aecg.zipContainer},'
            f'DERIVED sequenceSet(s) found: '
            f'{len(seqnodes)} sequenceSet nodes')
    else:
        logger.warning(
            f'{aecg.filename},{aecg.zipContainer},'
            f'DERIVED sequenceSet not found')

    for xmlnode in seqnodes:
        xmlnode_path = aecg_doc.getpath(xmlnode)
        valrow = validate_xpath(aecg_doc,
                                xmlnode_path,
                                "urn:hl7-org:v3",
                                "code",
                                new_validation_row(aecg.filename, "DERIVED",
                                                   "SEQUENCE_CODE"),
                                failcat="WARNING")
        valpd = pd.DataFrame()
        if valrow["VALIOUT"] == "PASSED":
            if not valrow["VALUE"] in SEQUENCE_CODES:
                logger.warning(
                    f'{aecg.filename},{aecg.zipContainer},'
                    f'DERIVED unexpected sequenceSet code '
                    f'found: {valrow["VALUE"]}')
                valrow["VALIOUT"] = "WARNING"
                valrow["VALIMSG"] = "Unexpected sequence code found"
            if valrow["VALUE"] in TIME_CODES:
                logger.info(
                    f'{aecg.filename},{aecg.zipContainer},'
                    f'DERIVED sequenceSet code found: {valrow["VALUE"]}')
                aecg.DERIVEDTIME["code"] = valrow["VALUE"]
                # Retrieve time head info from value node
                rel_path = "../value/head"
                valrow2 = validate_xpath(
                    xmlnode,
                    rel_path,
                    "urn:hl7-org:v3",
                    "value",
                    new_validation_row(aecg.filename, "DERIVED",
                                       "SEQUENCE_TIME_HEAD"),
                    failcat="WARNING")
                valrow2["XPATH"] = xmlnode_path + "/" + rel_path
                if valrow2["VALIOUT"] == "PASSED":
                    logger.info(
                        f'{aecg.filename},{aecg.zipContainer},'
                        f'DERIVED SEQUENCE_TIME_HEAD found: '
                        f'{valrow2["VALUE"]}')
                    aecg.DERIVEDTIME["head"] = valrow2["VALUE"]
                else:
                    logger.debug(
                        f'{aecg.filename},{aecg.zipContainer},'
                        f'DERIVED SEQUENCE_TIME_HEAD not found')
                if log_validation:
                    valpd = valpd.append(
                        pd.DataFrame([valrow2], columns=VALICOLS),
                        ignore_index=True)
                # Retrieve time increment info from value node
                rel_path = "../value/increment"
                for n in ["value", "unit"]:
                    valrow2 = validate_xpath(
                        xmlnode,
                        rel_path,
                        "urn:hl7-org:v3",
                        n,
                        new_validation_row(aecg.filename, "DERIVED",
                                           "SEQUENCE_TIME_" + n),
                        failcat="WARNING")
                    valrow2["XPATH"] = xmlnode_path + "/" + rel_path
                    if valrow2["VALIOUT"] == "PASSED":
                        logger.info(
                            f'{aecg.filename},{aecg.zipContainer},'
                            f'DERIVED SEQUENCE_TIME_{n} found: '
                            f'{valrow2["VALUE"]}')
                        if n == "value":
                            aecg.DERIVEDTIME["increment"] =\
                                float(valrow2["VALUE"])
                        else:
                            aecg.DERIVEDTIME[n] = valrow2["VALUE"]
                    if log_validation:
                        valpd = valpd.append(
                            pd.DataFrame([valrow2], columns=VALICOLS),
                            ignore_index=True)
            else:
                logger.debug(
                    f'{aecg.filename},{aecg.zipContainer},'
                    f'DERIVED sequenceSet code found: {valrow["VALUE"]}')
                logger.info(
                    f'{aecg.filename},{aecg.zipContainer},'
                    f'LEADNAME from DERIVED sequenceSet code: '
                    f'{valrow["VALUE"]}')
                # Assume is a lead
                aecglead = AecgLead()
                aecglead.leadname = valrow["VALUE"]
                # Inherit last parsed DERIVEDTIME
                aecglead.LEADTIME = copy.deepcopy(aecg.DERIVEDTIME)
                # Retrive lead origin info
                rel_path = "../value/origin"
                for n in ["value", "unit"]:
                    valrow2 = validate_xpath(
                        xmlnode,
                        rel_path,
                        "urn:hl7-org:v3",
                        n,
                        new_validation_row(aecg.filename, "DERIVED",
                                           "SEQUENCE_LEAD_ORIGIN_" + n),
                        failcat="WARNING")
                    valrow2["XPATH"] = xmlnode_path + "/" + rel_path
                    if valrow2["VALIOUT"] == "PASSED":
                        logger.info(
                            f'{aecg.filename},{aecg.zipContainer},'
                            f'DERIVED SEQUENCE_LEAD_ORIGIN_{n} '
                            f'found: {valrow2["VALUE"]}')
                        if n == "value":
                            try:
                                aecglead.origin = float(valrow2["VALUE"])
                            except Exception as ex:
                                valrow2["VALIOUT"] == "ERROR"
                                valrow2["VALIMSG"] = \
                                    "SEQUENCE_LEAD_ORIGIN is not a number"
                        else:
                            aecglead.origin_unit = valrow2["VALUE"]
                    else:
                        logger.debug(
                            f'{aecg.filename},{aecg.zipContainer},'
                            f'DERIVED SEQUENCE_LEAD_ORIGIN_{n} not found')
                    if log_validation:
                        valpd = valpd.append(
                            pd.DataFrame([valrow2], columns=VALICOLS),
                            ignore_index=True)
                # Retrive lead scale info
                rel_path = "../value/scale"
                for n in ["value", "unit"]:
                    valrow2 = validate_xpath(
                        xmlnode,
                        rel_path,
                        "urn:hl7-org:v3",
                        n,
                        new_validation_row(aecg.filename, "DERIVED",
                                           "SEQUENCE_LEAD_SCALE_" + n),
                        failcat="WARNING")
                    valrow2["XPATH"] = xmlnode_path + "/" + rel_path
                    if valrow2["VALIOUT"] == "PASSED":
                        logger.info(
                            f'{aecg.filename},{aecg.zipContainer},'
                            f'DERIVED SEQUENCE_LEAD_SCALE_{n} '
                            f'found: {valrow2["VALUE"]}')
                        if n == "value":
                            try:
                                aecglead.scale = float(valrow2["VALUE"])
                            except Exception as ex:
                                logger.error(
                                    f'{aecg.filename},{aecg.zipContainer},'
                                    f'DERIVED SEQUENCE_LEAD_SCALE'
                                    f' value is not a valid number: \"{ex}\"')
                                valrow2["VALIOUT"] == "ERROR"
                                valrow2["VALIMSG"] = "SEQUENCE_LEAD_SCALE"\
                                                     " is not a number"
                        else:
                            aecglead.scale_unit = valrow2["VALUE"]
                    else:
                        logger.debug(
                            f'{aecg.filename},{aecg.zipContainer},'
                            f'DERIVED SEQUENCE_LEAD_SCALE_{n} not found')
                    if log_validation:
                        valpd = valpd.append(
                            pd.DataFrame([valrow2], columns=VALICOLS),
                            ignore_index=True)
                # Include digits if requested
                if include_digits:
                    rel_path = "../value/digits"
                    valrow2 = validate_xpath(
                        xmlnode,
                        rel_path,
                        "urn:hl7-org:v3",
                        "",
                        new_validation_row(aecg.filename, "DERIVED",
                                           "SEQUENCE_LEAD_DIGITS"),
                        failcat="WARNING")
                    valrow2["XPATH"] = xmlnode_path + "/" + rel_path
                    if valrow2["VALIOUT"] == "PASSED":
                        try:
                            # Convert string of digits to list of integers
                            # remove new lines
                            sdigits = valrow2["VALUE"].replace("\n", " ")
                            # remove carriage retruns
                            sdigits = sdigits.replace("\r", " ")
                            # remove tabs
                            sdigits = sdigits.replace("\t", " ")
                            # collapse 2 or more spaces into 1 space char
                            # and remove leading/trailing white spaces
                            sdigits = re.sub("\\s+", " ", sdigits).strip()
                            # Convert string into list of integers
                            aecglead.digits = [int(s) for s in
                                               sdigits.split(' ')]
                            logger.info(
                                f'{aecg.filename},{aecg.zipContainer},'
                                f'DIGITS added to lead'
                                f' {aecglead.leadname} (n: '
                                f'{len(aecglead.digits)})')
                        except Exception as ex:
                            logger.error(
                                f'{aecg.filename},{aecg.zipContainer},'
                                f'Error parsing DIGITS from '
                                f'string to list of integers: \"{ex}\"')
                            valrow2["VALIOUT"] == "ERROR"
                            valrow2["VALIMSG"] = "Error parsing SEQUENCE_"\
                                                 "LEAD_DIGITS from string"\
                                                 " to list of integers"
                    else:
                        logger.error(
                            f'{aecg.filename},{aecg.zipContainer},'
                            f'DIGITS not found for lead {aecglead.leadname}')
                    if log_validation:
                        valpd = valpd.append(
                            pd.DataFrame([valrow2], columns=VALICOLS),
                            ignore_index=True)
                else:
                    logger.info(
                        f'{aecg.filename},{aecg.zipContainer},'
                        f'DIGITS were not requested by the user')
                aecg.DERIVEDLEADS.append(copy.deepcopy(aecglead))
        else:
            logger.warning(
                f'{aecg.filename},{aecg.zipContainer},'
                f'RHYTHM sequenceSet code not found')

        if log_validation:
            aecg.validatorResults = aecg.validatorResults.append(
                pd.DataFrame([valrow], columns=VALICOLS),
                ignore_index=True)
            if valpd.shape[0] > 0:
                aecg.validatorResults = \
                    aecg.validatorResults.append(valpd, ignore_index=True)

    return aecg


def parse_waveform_annotations(aecg_doc: etree._ElementTree,
                               aecg: Aecg,
                               anngrp: Dict,
                               log_validation: bool = False):
    """Parses `aecg_doc` XML document and extracts waveform annotations

    This function parses the `aecg_doc` xml document searching for
    waveform annotation sets that includes in the returned
    :any:`Aecg`. As indicated in the `anngrp` parameter, each annotation set
    is stored as an :any:`AecgAnnotationSet` in the :any:`Aecg.RHYTHMANNS`
    or :any:`Aecg.DERIVEDANNS` list of the returned :any:`Aecg`.

    Args:
        aecg_doc (etree._ElementTree): aECG XML document
        aecg (Aecg): The aECG object to update
        anngrp (Dict): includes a `valgroup` key indicating whether the
            rhythm or derived waveform annotations should be located, and a
            `path_prefix` with the xml path prefix for which start searching
            for annotation sets in the `aecg_doc` xml document.
        log_validation (bool, optional): Indicates whether to maintain the
            validation results in `aecg.validatorResults`. Defaults to
            False.

    Returns:
        Aecg: `aecg` updated with the information found in the xml document.
    """
    val_grp = anngrp["valgroup"]
    logger.debug(
            f'{aecg.filename},{aecg.zipContainer},'
            f'{val_grp}: searching annotations started')
    path_prefix = anngrp["path_prefix"]
    anns_setnodes = aecg_doc.xpath(path_prefix.replace('/', '/ns:'),
                                   namespaces={'ns': 'urn:hl7-org:v3'})
    if len(anns_setnodes) == 0:
        logger.warning(
            f'{aecg.filename},{aecg.zipContainer},'
            f'{anngrp["valgroup"]}: no annotation nodes found')
    for xmlnode in anns_setnodes:
        aecgannset = AecgAnnotationSet()
        xmlnode_path = aecg_doc.getpath(xmlnode)
        # Annotation set: human author information
        valrow = validate_xpath(
            aecg_doc,
            xmlnode_path + "/author/assignedEntity/assignedAuthorType/"
                           "assignedPerson/name",
            "urn:hl7-org:v3",
            "",
            new_validation_row(aecg.filename, "RHYTHM", "ANNSET_AUTHOR_NAME"),
            failcat="WARNING")
        if valrow["VALIOUT"] == "PASSED":
            logger.info(
                f'{aecg.filename},{aecg.zipContainer},'
                f'{val_grp} annotations author: {valrow["VALUE"]}')
            aecgannset.person = valrow["VALUE"]
        else:
            logger.debug(
                f'{aecg.filename},{aecg.zipContainer},'
                f'{val_grp} annotations author not found')
        if log_validation:
            aecg.validatorResults = aecg.validatorResults.append(
                pd.DataFrame([valrow], columns=VALICOLS),
                ignore_index=True)
        # Annotation set: device author information
        valrow = validate_xpath(aecg_doc,
                                xmlnode_path + "/author/assignedEntity"
                                               "/assignedAuthorType/"
                                               "assignedDevice/"
                                               "manufacturerModelName",
                                "urn:hl7-org:v3",
                                "",
                                new_validation_row(
                                    aecg.filename,
                                    "RHYTHM",
                                    "ANNSET_AUTHOR_DEVICE_MODEL"),
                                failcat="WARNING")
        if valrow["VALIOUT"] == "PASSED":
            tmp = valrow["VALUE"].replace("\n", "")
            logger.info(
                f'{aecg.filename},{aecg.zipContainer},'
                f'{val_grp} annotations device model: {tmp}')
            aecgannset.device["model"] = valrow["VALUE"]
        else:
            logger.debug(
                f'{aecg.filename},{aecg.zipContainer},'
                f'{val_grp} annotations device model not found')
        if log_validation:
            aecg.validatorResults = aecg.validatorResults.append(
                pd.DataFrame([valrow], columns=VALICOLS),
                ignore_index=True)
        valrow = validate_xpath(aecg_doc,
                                xmlnode_path +
                                "/author/assignedEntity/"
                                "assignedAuthorType/assignedDevice/"
                                "playedManufacturedDevice/"
                                "manufacturerOrganization/name",
                                "urn:hl7-org:v3",
                                "",
                                new_validation_row(
                                    aecg.filename,
                                    "RHYTHM",
                                    "ANNSET_AUTHOR_DEVICE_NAME"),
                                failcat="WARNING")
        if valrow["VALIOUT"] == "PASSED":
            tmp = valrow["VALUE"].replace("\n", "")
            logger.info(
                f'{aecg.filename},{aecg.zipContainer},'
                f'{val_grp} annotations device name: {tmp}')
            aecgannset.device["name"] = valrow["VALUE"]
        else:
            logger.debug(
                f'{aecg.filename},{aecg.zipContainer},'
                f'{val_grp} annotations device name not found')
        if log_validation:
            aecg.validatorResults = aecg.validatorResults.append(
                pd.DataFrame([valrow], columns=VALICOLS),
                ignore_index=True)

        aecgannset, valpd = parse_annotations(aecg.filename, aecg.zipContainer,
                                              aecg_doc,
                                              aecgannset,
                                              path_prefix,
                                              xmlnode_path,
                                              anngrp["valgroup"],
                                              log_validation)
        if len(aecgannset.anns) == 0:
            logger.debug(
                f'{aecg.filename},{aecg.zipContainer},'
                f'{val_grp} no annotations set found')

        if log_validation:
            aecg.validatorResults = \
                aecg.validatorResults.append(valpd, ignore_index=True)
        if anngrp["valgroup"] == "RHYTHM":
            aecg.RHYTHMANNS.append(copy.deepcopy(aecgannset))
        else:
            aecg.DERIVEDANNS.append(copy.deepcopy(aecgannset))

    logger.debug(
            f'{aecg.filename},{aecg.zipContainer},'
            f'{val_grp}: searching annotations finished')
    return aecg


def parse_rhythm_waveform_annotations(aecg_doc: etree._ElementTree,
                                      aecg: Aecg,
                                      log_validation: bool = False) -> Aecg:
    """Parses `aecg_doc` XML document and extracts rhythm waveform annotations

    This function parses the `aecg_doc` xml document searching for rhtyhm
    waveform annotation sets that includes in the returned
    :any:`Aecg`. Each annotation set is stored as an :any:`AecgAnnotationSet`
    in the :any:`Aecg.RHYTHMANNS` list of the returned :any:`Aecg`.

    Args:
        aecg_doc (etree._ElementTree): aECG XML document
        aecg (Aecg): The aECG object to update
        log_validation (bool, optional): Indicates whether to maintain the
            validation results in `aecg.validatorResults`. Defaults to
            False.

    Returns:
        Aecg: `aecg` updated with the information found in the xml document.
    """
    aecg = parse_waveform_annotations(
        aecg_doc, aecg,
        {"valgroup": "RHYTHM",
         "path_prefix": "./component/series/subjectOf/annotationSet"},
        log_validation)
    return aecg


def parse_derived_waveform_annotations(aecg_doc: etree._ElementTree,
                                       aecg: Aecg,
                                       log_validation: bool = False) -> Aecg:
    """Parses `aecg_doc` XML document and extracts derived waveform annotations

    This function parses the `aecg_doc` xml document searching for derived
    waveform annotation sets that includes in the returned
    :any:`Aecg`. Each annotation set is stored as an :any:`AecgAnnotationSet`
    in the :any:`Aecg.DERIVEDANNS` list of the returned :any:`Aecg`.

    Args:
        aecg_doc (etree._ElementTree): aECG XML document
        aecg (Aecg): The aECG object to update
        log_validation (bool, optional): Indicates whether to maintain the
            validation results in `aecg.validatorResults`. Defaults to
            False.

    Returns:
        Aecg: `aecg` updated with the information found in the xml document.
    """
    aecg = parse_waveform_annotations(
        aecg_doc, aecg,
        {"valgroup": "DERIVED",
         "path_prefix": "./component/series/derivation/"
                        "derivedSeries/subjectOf/annotationSet"},
        log_validation)
    return aecg


def read_aecg(xml_filename: str, zip_container: str = "",
              include_digits: bool = False,
              aecg_schema_filename: str = "",
              ns_clean: bool = True, remove_blank_text: bool = True,
              in_memory_xml: bool = False,
              log_validation: bool = False) -> Aecg:
    """Reads an aECG HL7 XML file and returns an `Aecg` object.

    Args:
        xml_filename (str): Path to the aECG xml file.
        zip_container (str, optional): Zipfile containing the aECG xml. Empty
            string if path points to an xml file in the system. Defaults to "".
        include_digits (bool, optional): Waveform values are not read nor
            parsed if False. Defaults to False.
        aecg_schema_filename (str, optional): xsd file to instantiate the
            lxml.etree.XMLSchema object for validating the aECG xml document.
            Schema validation is not performed if empty string is provided.
            Defaults to "".
        ns_clean (bool, optional): Indicates whether to clean up namespaces
            during XML parsing. Defaults to True.
        remove_blank_text (bool, optional): Indicates whether to clean up blank
            text during parsing. Defaults to True.
        in_memory_xml (bool, optional): If True, keeps a copy of the parsed XML
            in :attr:`xmldoc`.
        log_validation (bool, optional): If True, populates
            :attr:`validatorResults` with parsing information retrieved while
            reading and parsing the aECG xml file.
    Returns:
        Aecg: An aECG object instantiated with the information read from
        the `xml_filename` file.
    """

    # =======================================
    # Initialize Aecg object
    # =======================================
    aecg = Aecg()
    aecg.filename = xml_filename
    aecg.zipContainer = zip_container

    # =======================================
    # Read XML document
    # =======================================
    aecg_doc = None
    parser = etree.XMLParser(ns_clean=ns_clean,
                             remove_blank_text=remove_blank_text)
    if zip_container == "":
        logger.info(
                f'{aecg.filename},{aecg.zipContainer},'
                f'Reading aecg from {xml_filename} [no zip container]')
        valrow = new_validation_row(xml_filename, "READFILE", "FILENAME")
        valrow["VALUE"] = xml_filename
        try:
            aecg_doc = etree.parse(xml_filename, parser)
            valrow["VALIOUT"] = "PASSED"
            valrow["VALIMSG"] = ""
            logger.debug(
                f'{aecg.filename},{aecg.zipContainer},'
                f'XML file loaded and parsed')
            if log_validation:
                aecg.validatorResults = aecg.validatorResults.append(
                    pd.DataFrame([valrow], columns=VALICOLS),
                    ignore_index=True)
        except Exception as ex:
            msg = f'Could not open or parse XML file: \"{ex}\"'
            logger.error(
                f'{aecg.filename},{aecg.zipContainer},{msg}')
            valrow["VALIOUT"] = "ERROR"
            valrow["VALIMSG"] = msg
            if log_validation:
                aecg.validatorResults = aecg.validatorResults.append(
                    pd.DataFrame([valrow], columns=VALICOLS),
                    ignore_index=True)
        # Add row with zipcontainer rule as PASSED because there is no zip
        # container to test
        valrow = new_validation_row(xml_filename, "READFILE", "ZIPCONTAINER")
        valrow["VALIOUT"] = "PASSED"
        if log_validation:
            aecg.validatorResults = aecg.validatorResults.append(
                pd.DataFrame([valrow], columns=VALICOLS), ignore_index=True)
    else:
        logger.info(
            f'{aecg.filename},{aecg.zipContainer},'
            f'Reading aecg from {xml_filename} '
            f'[zip container: {zip_container}]')
        valrow = new_validation_row(xml_filename, "READFILE", "ZIPCONTAINER")
        valrow["VALUE"] = zip_container
        try:
            with zipfile.ZipFile(zip_container, "r") as zf:
                logger.debug(
                    f'{aecg.filename},{aecg.zipContainer},'
                    f'Zip file opened')
                valrow2 = new_validation_row(xml_filename, "READFILE",
                                             "FILENAME")
                valrow2["VALUE"] = xml_filename
                try:
                    aecg0 = zf.read(xml_filename)
                    logger.debug(
                        f'{aecg.filename},{aecg.zipContainer},'
                        f'XML file read from zip file')
                    try:
                        aecg_doc = etree.fromstring(aecg0, parser)
                        logger.debug(
                            f'{aecg.filename},{aecg.zipContainer},'
                            f'XML file loaded and parsed')
                    except Exception as ex:
                        msg = f'Could not parse XML file: \"{ex}\"'
                        logger.error(
                            f'{aecg.filename},{aecg.zipContainer},{msg}')
                        valrow2["VALIOUT"] = "ERROR"
                        valrow2["VALIMSG"] = msg
                        if log_validation:
                            aecg.validatorResults = \
                                aecg.validatorResults.append(
                                    pd.DataFrame([valrow2], columns=VALICOLS),
                                    ignore_index=True)
                    valrow2["VALIOUT"] = "PASSED"
                    valrow2["VALIMSG"] = ""
                    if log_validation:
                        aecg.validatorResults = aecg.validatorResults.append(
                            pd.DataFrame([valrow2], columns=VALICOLS),
                            ignore_index=True)
                except Exception as ex:
                    msg = f'Could not find or read XML file in the zip file: '\
                          f'\"{ex}\"'
                    logger.error(
                        f'{aecg.filename},{aecg.zipContainer},{msg}')
                    valrow2["VALIOUT"] = "ERROR"
                    valrow2["VALIMSG"] = msg
                    if log_validation:
                        aecg.validatorResults = aecg.validatorResults.append(
                            pd.DataFrame([valrow2], columns=VALICOLS),
                            ignore_index=True)
            valrow["VALIOUT"] = "PASSED"
            valrow["VALIMSG"] = ""
            if log_validation:
                aecg.validatorResults = aecg.validatorResults.append(
                    pd.DataFrame([valrow], columns=VALICOLS),
                    ignore_index=True)
        except Exception as ex:
            msg = f'Could not open zip file container: \"{ex}\"'
            logger.error(
                f'{aecg.filename},{aecg.zipContainer},{msg}')
            valrow["VALIOUT"] = "ERROR"
            valrow["VALIMSG"] = msg
            if log_validation:
                aecg.validatorResults = aecg.validatorResults.append(
                    pd.DataFrame([valrow], columns=VALICOLS),
                    ignore_index=True)

    if aecg_doc is not None:
        aecg.xmlfound = True
        if not isinstance(aecg_doc, etree._ElementTree):
            aecg_doc = etree.ElementTree(aecg_doc)

    if (aecg.xmlfound and
            (not log_validation or
                ((aecg.validatorResults.shape[0] == 1 and
                  aecg.validatorResults["VALIOUT"][0] == "PASSED") or
                 (aecg.validatorResults.shape[0] == 2 and
                  aecg.validatorResults["VALIOUT"][0] == "PASSED" and
                  aecg.validatorResults["VALIOUT"][1] == "PASSED")))):
        # =======================================
        # ECG file loaded and parsed to XML doc successfully
        # =======================================
        aecg.xmlfound = True

        # =======================================
        # Keep parsed XML if requested
        # =======================================
        if in_memory_xml:
            logger.debug(
                f'{aecg.filename},{aecg.zipContainer},'
                f'XML document cached in memory')
            aecg.xmldoc = aecg_doc
        else:
            logger.debug(
                f'{aecg.filename},{aecg.zipContainer},'
                f'XML document not cached in memory')

        # =======================================
        # Validate XML doc if schema was provided
        # =======================================
        valrow = new_validation_row(xml_filename, "SCHEMA", "VALIDATION")
        valrow["VALIOUT"] = "WARNING"
        valrow["VALIMSG"] = "Schema not provided for validation"
        if aecg_schema_filename is not None and aecg_schema_filename != "":
            valrow["VALUE"] = aecg_schema_filename
            try:
                aecg_schema_doc = etree.parse(aecg_schema_filename)
                try:
                    aecg_schema = etree.XMLSchema(aecg_schema_doc)
                    if aecg_schema.validate(aecg_doc):
                        logger.info(
                            f'{aecg.filename},{aecg.zipContainer},'
                            f'XML file passed Schema validation')
                        aecg.isValid = "Y"
                        valrow["VALIOUT"] = "PASSED"
                        valrow["VALIMSG"] = ""
                    else:
                        msg = f'XML file did not pass Schema validation'
                        logger.warning(
                            f'{aecg.filename},{aecg.zipContainer},{msg}')
                        aecg.isValid = "N"
                        valrow["VALIOUT"] = "ERROR"
                        valrow["VALIMSG"] = msg
                except Exception as ex:
                    msg = f'XML Schema is not valid: \"{ex}\"'
                    logger.error(
                            f'{aecg.filename},{aecg.zipContainer},{msg}')
                    valrow["VALIOUT"] = "ERROR"
                    valrow["VALIMSG"] = msg
            except Exception as ex:
                msg = f'Schema file not found or parsing of schema failed: '\
                      f'\"{ex}\"'
                logger.error(
                            f'{aecg.filename},{aecg.zipContainer},{msg}')
                valrow["VALIOUT"] = "ERROR"
                valrow["VALIMSG"] = msg
        else:
            logger.warning(
                f'{aecg.filename},{aecg.zipContainer},'
                f'Schema not provided for XML validation')

        if log_validation:
            aecg.validatorResults = aecg.validatorResults.append(
                pd.DataFrame([valrow], columns=VALICOLS), ignore_index=True)

        # =======================================
        # UUID and EGDTC and DEVICE
        # =======================================
        aecg = parse_generalinfo(aecg_doc, aecg, log_validation)

        # =======================================
        # USUBJID, SEX/GENDER, BIRTHTIME, RACE
        # =======================================
        aecg = parse_subjectinfo(aecg_doc, aecg, log_validation)

        # =======================================
        # TRTA
        # =======================================
        aecg = parse_trtainfo(aecg_doc, aecg, log_validation)

        # =======================================
        # CLINICAL TRIAL
        # =======================================
        aecg = parse_studyinfo(aecg_doc, aecg, log_validation)

        # =======================================
        # Timepoints
        # =======================================
        aecg = parse_timepoints(aecg_doc, aecg, log_validation)

        # =======================================
        # Rhythm Waveforms information
        # =======================================
        aecg = parse_rhythm_waveform_info(aecg_doc, aecg, log_validation)

        # =======================================
        # Derived Waveforms information
        # =======================================
        aecg = parse_derived_waveform_info(aecg_doc, aecg, log_validation)

        # =======================================
        # Rhythm Waveforms timeseries
        # =======================================
        aecg = parse_rhythm_waveform_timeseries(aecg_doc, aecg, include_digits,
                                                log_validation)

        # =======================================
        # Derived Waveforms timeseries
        # =======================================
        aecg = parse_derived_waveform_timeseries(aecg_doc, aecg,
                                                 include_digits,
                                                 log_validation)

        # =======================================
        # Rhythm and Derived Waveforms annotations
        # =======================================
        aecg = parse_rhythm_waveform_annotations(
            aecg_doc, aecg, log_validation)
        aecg = parse_derived_waveform_annotations(
            aecg_doc, aecg, log_validation)

    return aecg
