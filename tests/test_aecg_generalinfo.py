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

import aecg


def test_read_generalinfo_uuid_found():
    """
    Test reading UUID from an xml file
    """
    # Setup
    the_xml_filename = os.path.normpath(
        os.path.join(
            os.path.dirname(aecg.core.__file__),
            "data/examples/minimum_aecg.xml"))
    the_zip_container = ""
    the_xml_schema_filename = os.path.normpath(
        os.path.join(
            os.path.dirname(aecg.core.__file__),
            "data/hl7/2003-12 Schema/schema/PORT_MT020001.xsd"))
    truth_validation_row = {
        "EGXFN": the_xml_filename,
        "XPATH": "./*[local-name() = \"id\"]",
        "VALIGRP": "GENERAL",
        "PARAM": "UUID",
        "VALUE": "61d1a24f-b47e-41aa-ae95-f8ac302f4eeb",
        "VALIOUT": "PASSED",
        "VALIMSG": ""
    }

    # Exercise
    the_aecg = aecg.io.read_aecg(the_xml_filename, the_zip_container,
                                 False,
                                 the_xml_schema_filename,
                                 log_validation=True)

    # utils.print_fulldf(the_aecg.validatorResults)

    # Verify
    assert the_aecg.filename == the_xml_filename
    assert the_aecg.zipContainer == the_zip_container
    assert the_aecg.xmlfound
    assert the_aecg.isValid == "Y"
    assert the_aecg.validatorResults[
            (the_aecg.validatorResults["VALIGRP"] == "GENERAL") &
            (the_aecg.validatorResults["PARAM"] == "UUID")
        ].iloc[0].to_dict() == truth_validation_row

    # Cleanup -- not needed
# end test_read_generalinfo_uuid_found


def test_read_generalinfo_uuid_root_missing():
    """
    Reading UUID from an xml file where root attribute is missing in the id

    Note that if the id node is missing or the root attribute is included, then
    the aecg file will not pass the schema validation. So, no other uuid test
    cases are needed.
    """
    # Setup
    the_xml_filename = os.path.normpath(
        os.path.join(
            os.path.dirname(aecg.core.__file__),
            "data/examples/minimum_aecg_nouuid.xml"))
    the_zip_container = ""
    the_xml_schema_filename = os.path.normpath(
        os.path.join(
            os.path.dirname(aecg.core.__file__),
            "data/hl7/2003-12 Schema/schema/PORT_MT020001.xsd"))
    truth_validation_row = {
        "EGXFN": the_xml_filename,
        "XPATH": "./*[local-name() = \"id\"]",
        "VALIGRP": "GENERAL",
        "PARAM": "UUID",
        "VALUE": "",
        "VALIOUT": "ERROR",
        "VALIMSG": "Node found but attribute is missing"
    }

    # Exercise

    the_aecg = aecg.io.read_aecg(the_xml_filename, the_zip_container,
                                 False,
                                 the_xml_schema_filename,
                                 log_validation=True)

    # utils.print_fulldf(the_aecg.validatorResults)

    # Verify
    assert the_aecg.filename == the_xml_filename
    assert the_aecg.zipContainer == the_zip_container
    assert the_aecg.xmlfound
    assert the_aecg.isValid == "Y"
    assert the_aecg.validatorResults[
            (the_aecg.validatorResults["VALIGRP"] == "GENERAL") &
            (the_aecg.validatorResults["PARAM"] == "UUID")
        ].iloc[0].to_dict() == truth_validation_row

    # Cleanup -- not needed
# end test_read_generalinfo_uuid_root_missing


def test_read_generalinfo_egdtc_centered_found():
    """
    Test reading EGDTC from an xml file documented as centered time
    """
    # Setup
    the_xml_filename = os.path.normpath(
        os.path.join(
            os.path.dirname(aecg.core.__file__),
            "data/examples/minimum_aecg.xml"))
    the_zip_container = ""
    the_xml_schema_filename = os.path.normpath(
        os.path.join(
            os.path.dirname(aecg.core.__file__),
            "data/hl7/2003-12 Schema/schema/PORT_MT020001.xsd"))
    truth_validation_row = {
        "EGXFN": the_xml_filename,
        "XPATH": "./*[local-name() = \"effectiveTime\"]/"
                 "*[local-name() = \"center\"]",
        "VALIGRP": "GENERAL",
        "PARAM": "EGDTC_center",
        "VALUE": "20021122091000",
        "VALIOUT": "PASSED",
        "VALIMSG": ""
    }

    # Exercise

    the_aecg = aecg.io.read_aecg(the_xml_filename, the_zip_container,
                                 False,
                                 the_xml_schema_filename,
                                 log_validation=True)

    # utils.print_fulldf(the_aecg.validatorResults)

    # Verify
    assert the_aecg.filename == the_xml_filename
    assert the_aecg.zipContainer == the_zip_container
    assert the_aecg.xmlfound
    assert the_aecg.isValid == "Y"
    assert the_aecg.validatorResults[
            (the_aecg.validatorResults["VALIGRP"] == "GENERAL") &
            (the_aecg.validatorResults["PARAM"] == "EGDTC_center")
        ].iloc[0].to_dict() == truth_validation_row

    # Cleanup -- not needed
# end test_read_generalinfo_egdtc_centered_found


def test_read_generalinfo_egdtc_low_found():
    """
    Test reading EGDTC from an xml file documented as low time
    """
    # Setup
    the_xml_filename = os.path.normpath(
        os.path.join(
            os.path.dirname(aecg.core.__file__),
            "data/examples/minimum_aecg_effectiveTime_low.xml"))
    the_zip_container = ""
    the_xml_schema_filename = os.path.normpath(
        os.path.join(
            os.path.dirname(aecg.core.__file__),
            "data/hl7/2003-12 Schema/schema/PORT_MT020001.xsd"))
    truth_validation_row = {
        "EGXFN": the_xml_filename,
        "XPATH":
            "./*[local-name() = \"effectiveTime\"]/*[local-name() = \"low\"]",
        "VALIGRP": "GENERAL",
        "PARAM": "EGDTC_low",
        "VALUE": "20021122091000",
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
    assert the_aecg.isValid == "Y"
    assert the_aecg.validatorResults[
            (the_aecg.validatorResults["VALIGRP"] == "GENERAL") &
            (the_aecg.validatorResults["PARAM"] == "EGDTC_low")
        ].iloc[0].to_dict() == truth_validation_row

    # Cleanup -- not needed
# end test_read_generalinfo_egdtc_low_found


def test_read_generalinfo_egdtc_high_found():
    """
    Test reading EGDTC from an xml file documented as high time
    """
    # Setup
    the_xml_filename = os.path.normpath(
        os.path.join(
            os.path.dirname(aecg.core.__file__),
            "data/examples/minimum_aecg_effectiveTime_high.xml"))
    the_zip_container = ""
    the_xml_schema_filename = os.path.normpath(
        os.path.join(
            os.path.dirname(aecg.core.__file__),
            "data/hl7/2003-12 Schema/schema/PORT_MT020001.xsd"))
    truth_validation_row = {
        "EGXFN": the_xml_filename,
        "XPATH":
            "./*[local-name() = \"effectiveTime\"]/*[local-name() = \"high\"]",
        "VALIGRP": "GENERAL",
        "PARAM": "EGDTC_high",
        "VALUE": "20021122091010",
        "VALIOUT": "PASSED",
        "VALIMSG": ""
    }

    # Exercise

    the_aecg = aecg.io.read_aecg(the_xml_filename, the_zip_container,
                                 False,
                                 the_xml_schema_filename,
                                 log_validation=True)

    # utils.print_fulldf(the_aecg.validatorResults)

    # Verify
    assert the_aecg.filename == the_xml_filename
    assert the_aecg.zipContainer == the_zip_container
    assert the_aecg.xmlfound
    assert the_aecg.isValid == "Y"
    assert the_aecg.validatorResults[
            (the_aecg.validatorResults["VALIGRP"] == "GENERAL") &
            (the_aecg.validatorResults["PARAM"] == "EGDTC_high")
        ].iloc[0].to_dict() == truth_validation_row

    # Cleanup -- not needed
# end test_read_generalinfo_egdtc_high_found
