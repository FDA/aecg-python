"""Unit tests for aecg package: tools for annotated ECG HL7 XML files.

**Authors**

***Jose Vicente Ruiz*** <jose.vicenteruiz@fda.hhs.gov><br>

    Division of Cardiology and Nephrology
    Office of Cardiology, Hematology, Endocrinology and Nephrology
    Office of New Drugs
    Center for Drug Evaluation and Research
    U.S. Food and Drug Administration


* LICENSE *
===========
This code is in the public domain within the United States, and copyright and
related rights in the work worldwide are waived through the CC0 1.0 Universal
Public Domain Dedication. This example is distributed in the hope that it will
be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See DISCLAIMER section
below, the COPYING file in the root directory of this project and
https://creativecommons.org/publicdomain/zero/1.0/ for more details.

* Disclaimer *
==============
FDA assumes no responsibility whatsoever for use by other parties of the
Software, its source code, documentation or compiled executables, and makes no
guarantees, expressed or implied, about its quality, reliability, or any other
characteristic. Further, FDA makes no representations that the use of the
Software will not infringe any patent or proprietary rights of third parties.
The use of this code in no way implies endorsement by the FDA or confers any
advantage in regulatory decisions.

"""


import os
import sys

import aecg


def test_read_from_nonexisting_zipfile():
    """
    Test reading an xml file stored in a zip file that is not available
    """
    # Setup
    the_xml_filename = os.path.normpath(
        os.path.join(
            os.path.dirname(aecg.core.__file__),
            "data/hl7/2003-12 Schema/example/Example aECG.xml"))
    the_zip_container = os.path.normpath(
        os.path.join(
            os.path.dirname(aecg.core.__file__), "data/nonexisiting.zip"))
    aecg_schema_filename = os.path.normpath(
        os.path.join(
            os.path.dirname(aecg.core.__file__),
            "data/hl7/2003-12 Schema/schema/PORT_MT020001.xsd"))
    tmp_str = the_zip_container.replace("\\", "\\\\")
    truth_validation_row = {
        "EGXFN": the_xml_filename,
        "XPATH": "",
        "VALIGRP": "READFILE",
        "PARAM": "ZIPCONTAINER",
        "VALUE": the_zip_container,
        "VALIOUT": "ERROR",
        "VALIMSG": f"Could not open zip file container: \"[Errno 2] No such "
                   f"file or directory: \'{tmp_str}\'\""
    }

    # Exercise
    the_aecg = aecg.io.read_aecg(the_xml_filename, the_zip_container,
                                 False,
                                 aecg_schema_filename,
                                 log_validation=True)
    # Verify
    assert the_aecg.filename == the_xml_filename
    assert the_aecg.zipContainer == the_zip_container
    assert not the_aecg.xmlfound
    assert the_aecg.validatorResults.iloc[0].to_dict() == truth_validation_row

    # Cleanup -- not needed
# end test_read_from_nonexisting_zipfile


def test_read_from_nonexisting_zipfile_novalidator():
    """
    Test reading an xml file stored in a zip file that is not available without
    storing the results from the validation process
    """
    # Setup
    the_xml_filename = os.path.normpath(
        os.path.join(
            os.path.dirname(aecg.core.__file__),
            "data/hl7/2003-12 Schema/example/Example aECG.xml"))
    the_zip_container = os.path.normpath(
        os.path.join(
            os.path.dirname(aecg.core.__file__),
            "data/nonexisiting.zip"))
    aecg_schema_filename = os.path.normpath(
        os.path.join(
            os.path.dirname(aecg.core.__file__),
            "data/hl7/2003-12 Schema/schema/PORT_MT020001.xsd"))
    # Exercise
    the_aecg = aecg.io.read_aecg(the_xml_filename, the_zip_container,
                                 False,
                                 aecg_schema_filename,
                                 log_validation=False)

    # Verify
    assert the_aecg.filename == the_xml_filename
    assert the_aecg.zipContainer == the_zip_container
    assert not the_aecg.xmlfound

    # Cleanup -- not needed
# end test_read_from_nonexisting_zipfile_novalidator


def test_read_nonexisting_xmlfile_from_existing_zipfile():
    """
    Test reading an xml file that is not stored in an available zip file
    """
    # Setup
    the_xml_filename = "nonexisting.xml"
    the_zip_container = os.path.normpath(
        os.path.join(
            os.path.dirname(aecg.core.__file__), "data/hl7.zip"))
    aecg_schema_filename = os.path.normpath(
        os.path.join(
            os.path.dirname(aecg.core.__file__),
            "data/hl7/2003-12 Schema/schema/PORT_MT020001.xsd"))
    truth_validation_row0 = {
        "EGXFN": the_xml_filename,
        "XPATH": "",
        "VALIGRP": "READFILE",
        "PARAM": "FILENAME",
        "VALUE": the_xml_filename,
        "VALIOUT": "ERROR",
        "VALIMSG": "Could not find or read XML file in the zip file: \"\""
                   "There is no item named \'nonexisting.xml\' in the "
                   "archive\"\""
    }
    truth_validation_row1 = {
        "EGXFN": the_xml_filename,
        "XPATH": "",
        "VALIGRP": "READFILE",
        "PARAM": "ZIPCONTAINER",
        "VALUE": the_zip_container,
        "VALIOUT": "PASSED",
        "VALIMSG": ""
    }

    # Exercise
    the_aecg = aecg.io.read_aecg(the_xml_filename, the_zip_container,
                                 False,
                                 aecg_schema_filename,
                                 log_validation=True)

    # Verify
    assert the_aecg.filename == the_xml_filename
    assert the_aecg.zipContainer == the_zip_container
    assert the_aecg.validatorResults.iloc[0].to_dict() == truth_validation_row0
    assert the_aecg.validatorResults.iloc[1].to_dict() == truth_validation_row1
    assert not the_aecg.xmlfound

    # Cleanup -- not needed
# end test_read_nonexisting_xmlfile_from_existing_zipfile


def test_read_nonexisting_xmlfile_from_existing_zipfile_novalidator():
    """
    Test reading an xml file that is not stored in an available zip file
    without storing the results from the validation process
    """
    # Setup
    the_xml_filename = "nonexisting.xml"
    the_zip_container = "aecg/data/hl7.zip"
    aecg_schema_filename = "aecg/data/hl7/2003-12 Schema/schema/"\
                           "PORT_MT020001.xsd"

    # Exercise
    the_aecg = aecg.io.read_aecg(the_xml_filename, the_zip_container,
                                 False,
                                 aecg_schema_filename,
                                 log_validation=False)

    # Verify
    assert the_aecg.filename == the_xml_filename
    assert the_aecg.zipContainer == the_zip_container
    assert not the_aecg.xmlfound

    # Cleanup -- not needed
# end test_read_nonexisting_xmlfile_from_existing_zipfile_novalidator


def test_read_existing_xmlfile_from_existing_zipfile():
    """
    Test reading an xml file stored in a zip file
    """
    # Setup
    the_xml_filename = "hl7/2003-12 Schema/example/Example aECG.xml"
    the_zip_container = os.path.normpath(
        os.path.join(
            os.path.dirname(aecg.core.__file__),
            "data/hl7.zip"))
    aecg_schema_filename = os.path.normpath(
        os.path.join(
            os.path.dirname(aecg.core.__file__),
            "data/hl7/2003-12 Schema/schema/PORT_MT020001.xsd"))
    truth_validation_row0 = {
        "EGXFN": the_xml_filename,
        "XPATH": "",
        "VALIGRP": "READFILE",
        "PARAM": "FILENAME",
        "VALUE": the_xml_filename,
        "VALIOUT": "PASSED",
        "VALIMSG": ""
    }
    truth_validation_row1 = {
        "EGXFN": the_xml_filename,
        "XPATH": "",
        "VALIGRP": "READFILE",
        "PARAM": "ZIPCONTAINER",
        "VALUE": the_zip_container,
        "VALIOUT": "PASSED",
        "VALIMSG": ""
    }

    # Exercise
    the_aecg = aecg.io.read_aecg(the_xml_filename, the_zip_container,
                                 False,
                                 aecg_schema_filename,
                                 log_validation=True)

    # Verify
    assert the_aecg.filename == the_xml_filename
    assert the_aecg.zipContainer == the_zip_container
    assert the_aecg.validatorResults.iloc[0].to_dict() == truth_validation_row0
    assert the_aecg.validatorResults.iloc[1].to_dict() == truth_validation_row1
    assert the_aecg.xmlfound

    # Cleanup -- not needed
# end test_read_existing_xmlfile_from_existing_zipfile


def test_read_existing_xmlfile_from_existing_zipfile_novalidator():
    """
    Test reading an xml file stored in a zip file without
    storing the results from the validation process
    """
    # Setup
    the_xml_filename = "hl7/2003-12 Schema/example/Example aECG.xml"
    the_zip_container = os.path.normpath(
        os.path.join(
            os.path.dirname(aecg.core.__file__), "data/hl7.zip"))
    aecg_schema_filename = os.path.normpath(
        os.path.join(
            os.path.dirname(aecg.core.__file__),
            "data/hl7/2003-12 Schema/schema/PORT_MT020001.xsd"))

    # Exercise
    the_aecg = aecg.io.read_aecg(the_xml_filename, the_zip_container,
                                 False,
                                 aecg_schema_filename,
                                 log_validation=False)

    # Verify
    assert the_aecg.filename == the_xml_filename
    assert the_aecg.zipContainer == the_zip_container
    assert the_aecg.xmlfound

    # Cleanup -- not needed
# end test_read_existing_xmlfile_from_existing_zipfile_novalidator


def test_read_nonexisting_xmlfile():
    """
    Test reading an xml file from not available path
    """
    # Setup
    the_xml_filename = os.path.normpath(
        os.path.join(
            os.path.dirname(aecg.core.__file__),
            "data/nonexisting.xml"))
    the_zip_container = ""
    aecg_schema_filename = os.path.normpath(
        os.path.join(
            os.path.dirname(aecg.core.__file__),
            "data/hl7/2003-12 Schema/schema/PORT_MT020001.xsd"))
    tmp_str = 'file:/' + the_xml_filename.replace("\\", "/")
    if not sys.platform.startswith('win32'):
        tmp_str = the_xml_filename.replace("\\", "/")
    valimsg = f"Could not open or parse XML file: \"Error reading file "\
        f"\'{the_xml_filename}\': failed to load external "\
        f"entity \"{tmp_str}\"\""
    truth_validation_row0 = {
        "EGXFN": the_xml_filename,
        "XPATH": "",
        "VALIGRP": "READFILE",
        "PARAM": "FILENAME",
        "VALUE": the_xml_filename,
        "VALIOUT": "ERROR",
        "VALIMSG": valimsg
    }
    truth_validation_row1 = {
        "EGXFN": the_xml_filename,
        "XPATH": "",
        "VALIGRP": "READFILE",
        "PARAM": "ZIPCONTAINER",
        "VALUE": the_zip_container,
        "VALIOUT": "PASSED",
        "VALIMSG": ""
    }

    # Exercise
    the_aecg = aecg.io.read_aecg(the_xml_filename, the_zip_container,
                                 False,
                                 aecg_schema_filename,
                                 log_validation=True)

    # Verify
    assert the_aecg.filename == the_xml_filename
    assert the_aecg.zipContainer == the_zip_container
    assert the_aecg.validatorResults.iloc[0].to_dict() == truth_validation_row0
    assert the_aecg.validatorResults.iloc[1].to_dict() == truth_validation_row1
    assert not the_aecg.xmlfound

    # Cleanup -- not needed
# end test_read_nonexisting_xmlfile


def test_read_nonexisting_xmlfile_novalidator():
    """
    Test reading an xml file from not available path without
    storing the results from the validation process
    """
    # Setup
    the_xml_filename = "aecg/data/nonexisting.xml"
    the_zip_container = ""
    aecg_schema_filename = "aecg/data/hl7/2003-12 Schema/schema/"\
                           "PORT_MT020001.xsd"

    # Exercise
    the_aecg = aecg.io.read_aecg(the_xml_filename, the_zip_container,
                                 False,
                                 aecg_schema_filename,
                                 log_validation=False)

    # Verify
    assert the_aecg.filename == the_xml_filename
    assert the_aecg.zipContainer == the_zip_container
    assert not the_aecg.xmlfound

    # Cleanup -- not needed
# end test_read_nonexisting_xmlfile_novalidator


def test_read_existing_xmlfile():
    """
    Test reading an xml file from file (i.e., not stored in a zip file)
    """
    # Setup
    the_xml_filename = os.path.normpath(
        os.path.join(
            os.path.dirname(aecg.core.__file__),
            "data/hl7/2003-12 Schema/example/Example aECG.xml"))
    the_zip_container = ""
    aecg_schema_filename = os.path.normpath(
        os.path.join(
            os.path.dirname(aecg.core.__file__),
            "data/hl7/2003-12 Schema/schema/PORT_MT020001.xsd"))
    truth_validation_row0 = {
        "EGXFN": the_xml_filename,
        "XPATH": "",
        "VALIGRP": "READFILE",
        "PARAM": "FILENAME",
        "VALUE": the_xml_filename,
        "VALIOUT": "PASSED",
        "VALIMSG": ""
    }
    truth_validation_row1 = {
        "EGXFN": the_xml_filename,
        "XPATH": "",
        "VALIGRP": "READFILE",
        "PARAM": "ZIPCONTAINER",
        "VALUE": the_zip_container,
        "VALIOUT": "PASSED",
        "VALIMSG": ""
    }

    # Exercise
    the_aecg = aecg.io.read_aecg(the_xml_filename, the_zip_container,
                                 False,
                                 aecg_schema_filename,
                                 log_validation=True)

    # Verify
    assert the_aecg.filename == the_xml_filename
    assert the_aecg.zipContainer == the_zip_container
    assert the_aecg.validatorResults.iloc[0].to_dict() == truth_validation_row0
    assert the_aecg.validatorResults.iloc[1].to_dict() == truth_validation_row1
    assert the_aecg.xmlfound

    # Cleanup -- not needed
# end test_read_existing_xmlfile


def test_read_existing_xmlfile_novalidator():
    """
    Test reading an xml file from file (i.e., not stored in a zip file)
    """
    # Setup
    the_xml_filename = os.path.normpath(
        os.path.join(
            os.path.dirname(aecg.core.__file__),
            "data/hl7/2003-12 Schema/example/Example aECG.xml"))
    the_zip_container = ""
    aecg_schema_filename = os.path.normpath(
        os.path.join(
            os.path.dirname(aecg.core.__file__),
            "data/hl7/2003-12 Schema/schema/PORT_MT020001.xsd"))

    # Exercise
    the_aecg = aecg.io.read_aecg(the_xml_filename, the_zip_container,
                                 False,
                                 aecg_schema_filename,
                                 log_validation=False)

    # Verify
    assert the_aecg.filename == the_xml_filename
    assert the_aecg.zipContainer == the_zip_container
    assert the_aecg.xmlfound

    # Cleanup -- not needed
# end test_read_existing_xmlfile_novalidator


def test_validate_xml_vs_xsd_schema_without_schema():
    """
    Test validating an xml file without providing an schema
    """
    # Setup
    the_xml_filename = os.path.normpath(
        os.path.join(
            os.path.dirname(aecg.core.__file__),
            "data/hl7/2003-12 Schema/example/Example aECG.xml"))
    the_zip_container = ""
    the_xml_schema_filename = ""
    truth_validation_row = {
        "EGXFN": the_xml_filename,
        "XPATH": "",
        "VALIGRP": "SCHEMA",
        "PARAM": "VALIDATION",
        "VALUE": the_xml_schema_filename,
        "VALIOUT": "WARNING",
        "VALIMSG": "Schema not provided for validation"
    }

    # Exercise
    the_aecg = aecg.io.read_aecg(the_xml_filename, the_zip_container,
                                 False,
                                 the_xml_schema_filename,
                                 log_validation=True)

    # Verify
    assert the_aecg.filename == the_xml_filename
    assert the_aecg.zipContainer == the_zip_container
    assert the_aecg.xmlfound
    assert the_aecg.validatorResults[
            the_aecg.validatorResults["VALIGRP"] == "SCHEMA"
        ].iloc[0].to_dict() == truth_validation_row
    assert the_aecg.isValid == ""

    # Cleanup -- not needed
# end text_validate_xml_vs_xsd_schema_success


def test_validate_xml_vs_xsd_schema_success():
    """
    Test validating an xml file compliant with a given schema
    """
    # Setup
    the_xml_filename = os.path.normpath(
        os.path.join(
            os.path.dirname(aecg.core.__file__),
            "data/hl7/2003-12 Schema/example/Example aECG.xml"))
    the_zip_container = ""
    the_xml_schema_filename = os.path.normpath(
        os.path.join(
            os.path.dirname(aecg.core.__file__),
            "data/hl7/2003-12 Schema/schema/PORT_MT020001.xsd"))
    truth_validation_row = {
        "EGXFN": the_xml_filename,
        "XPATH": "",
        "VALIGRP": "SCHEMA",
        "PARAM": "VALIDATION",
        "VALUE": the_xml_schema_filename,
        "VALIOUT": "PASSED",
        "VALIMSG": ""
    }

    # Exercise
    the_aecg = aecg.io.read_aecg(the_xml_filename, the_zip_container,
                                 False,
                                 the_xml_schema_filename,
                                 log_validation=True)

    # Verify
    assert the_aecg.filename == the_xml_filename
    assert the_aecg.zipContainer == the_zip_container
    assert the_aecg.xmlfound
    assert the_aecg.validatorResults[
            the_aecg.validatorResults["VALIGRP"] == "SCHEMA"
        ].iloc[0].to_dict() == truth_validation_row
    assert the_aecg.isValid == "Y"

    # Cleanup -- not needed
# end text_validate_xml_vs_xsd_schema_success


def test_validate_xml_vs_xsd_schema_nosuccess():
    """
    Test validating an xml file NOT compliant with a given schema
    """
    # Setup
    the_xml_filename = os.path.normpath(
        os.path.join(
            os.path.dirname(aecg.core.__file__),
            "data/examples/empty.xml"))
    the_zip_container = ""
    the_xml_schema_filename = os.path.normpath(
        os.path.join(
            os.path.dirname(aecg.core.__file__),
            "data/hl7/2003-12 Schema/schema/PORT_MT020001.xsd"))
    truth_validation_row = {
        "EGXFN": the_xml_filename,
        "XPATH": "",
        "VALIGRP": "SCHEMA",
        "PARAM": "VALIDATION",
        "VALUE": the_xml_schema_filename,
        "VALIOUT": "ERROR",
        "VALIMSG": "XML file did not pass Schema validation"
    }

    # Exercise
    the_aecg = aecg.io.read_aecg(the_xml_filename, the_zip_container,
                                 False,
                                 the_xml_schema_filename,
                                 log_validation=True)

    # Verify
    assert the_aecg.filename == the_xml_filename
    assert the_aecg.zipContainer == the_zip_container
    assert the_aecg.xmlfound
    assert the_aecg.validatorResults[
            the_aecg.validatorResults["VALIGRP"] == "SCHEMA"
        ].iloc[0].to_dict() == truth_validation_row
    assert the_aecg.isValid == "N"

    # Cleanup -- not needed
# end text_validate_xml_vs_xsd_schema_nosuccess


def test_validate_xml_vs_bad_xsd_schema():
    """
    Test validating an xml file with an unvalid schema
    """
    # Setup
    the_xml_filename = os.path.normpath(
        os.path.join(
            os.path.dirname(aecg.core.__file__),
            "data/hl7/2003-12 Schema/example/Example aECG.xml"))
    the_zip_container = ""
    the_xml_schema_filename = os.path.normpath(
        os.path.join(
            os.path.dirname(aecg.core.__file__),
            "data/examples/badschema.xsd"))
    truth_validation_row = {
        "EGXFN": the_xml_filename,
        "XPATH": "",
        "VALIGRP": "SCHEMA",
        "PARAM": "VALIDATION",
        "VALUE": the_xml_schema_filename,
        "VALIOUT": "ERROR",
        "VALIMSG": "XML Schema is not valid: \"Element "
                   "\'{http://www.w3.org/2001/XMLSchema}schema\': The content"
                   " is not valid. Expected is ((include | import | redefine "
                   "| annotation)*, (((simpleType | complexType | group | "
                   "attributeGroup) | element | attribute | notation), "
                   "annotation*)*)., line 5\""
    }

    # Exercise
    the_aecg = aecg.io.read_aecg(the_xml_filename, the_zip_container,
                                 False,
                                 the_xml_schema_filename,
                                 log_validation=True)

    # Verify
    assert the_aecg.filename == the_xml_filename
    assert the_aecg.zipContainer == the_zip_container
    assert the_aecg.xmlfound
    assert the_aecg.validatorResults[
            the_aecg.validatorResults["VALIGRP"] == "SCHEMA"
        ].iloc[0].to_dict() == truth_validation_row
    assert the_aecg.isValid == ""

    # Cleanup -- not needed
# end text_validate_xml_vs_xsd_schema_nosuccess


def test_new_validation_row():
    """
    Test creating a new validation row
    """
    # Setup
    truth_validation_row = {
        "EGXFN": "hl7/2003-12 Schema/example/Example aECG.xml",
        "XPATH": "",
        "VALIGRP": "READFILE",
        "PARAM": "FILENAME",
        "VALUE": "",
        "VALIOUT": "",
        "VALIMSG": ""
    }

    # Exercise
    validation_row = aecg.new_validation_row(
        "hl7/2003-12 Schema/example/Example aECG.xml",
        "READFILE",
        "FILENAME")

    # Verify
    assert validation_row == truth_validation_row

    # Cleanup -- not needed
# end test_utils_new_validation_row
