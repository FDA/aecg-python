""" Python script that copies example aECG to demonstrate eCTD aECG structure

See authors, license and disclaimer at the top level directory of this project.

"""

from lxml import etree
from copy import deepcopy
from pathlib import Path

import os
import sys

import aecg

aecgdir = os.path.dirname(aecg.core.__file__)

# aECG file to use as input
xml_filename = os.path.normpath(
    os.path.join(
        aecgdir,
        "data/hl7/2003-12 Schema/example/Example aECG.xml"))
if not Path(xml_filename).is_file():
    print(f"aECG filename({xml_filename}) is not available.")
    sys.exit(-1)

# Parse aECG base file
parser = etree.XMLParser(ns_clean=True, remove_blank_text=True)

aecg_doc = etree.parse(xml_filename, parser)

# Define output path
output_path = os.path.normpath(
    os.path.join(
        aecgdir,
        "data/ectd_example/FDA000003/0000/m5/datasets/Test/misc/aecg"))

if not Path(output_path).is_dir():
    Path(output_path).mkdir(parents=True)

# Define output files
output_files = {
    "subject1": [
        {"timepoint": "Predose", "start": 20021122091000},
        {"timepoint": "1hour", "start": 20021122101000},
        {"timepoint": "2hour", "start": 20021122111000}
    ],
    "subject2": [
        {"timepoint": "Predose", "start": 20021122091000},
        {"timepoint": "1hour", "start": 20021122101000},
        {"timepoint": "2hour", "start": 20021122111000}
    ]
}

# Make general changes
studyid = "Test"
studyidnode = aecg_doc.getroot().xpath(
    '//ns:componentOf/ns:clinicalTrial/ns:id',
    namespaces={'ns': 'urn:hl7-org:v3'})
if studyidnode is not None and len(studyidnode) == 1:
    studyidnode[0].set('extension', studyid)

# Create files
for subjectid, files in output_files.items():
    num = 0

    for file in files:
        # Prepare output location and copy base aECG
        output_file = os.path.join(output_path, f"{subjectid}_{num}.xml")
        newaecg = deepcopy(aecg_doc)

        # Base modifications
        rootid = newaecg.getroot().xpath(
            '/ns:AnnotatedECG/ns:id', namespaces={'ns': 'urn:hl7-org:v3'})
        if rootid is not None and len(rootid) == 1:
            rootid[0].set('extension', f"{subjectid}_{num}")

        subjid = newaecg.getroot().xpath(
            '//ns:subjectAssignment/ns:subject/ns:trialSubject/ns:id',
            namespaces={'ns': 'urn:hl7-org:v3'})
        if subjid is not None and len(subjid) == 1:
            subjid[0].set('extension', subjectid)

        # Additional modifications
        for mod, value in file.items():
            # Timepoint
            if mod == "timepoint":
                node = newaecg.getroot().xpath(
                    '//ns:componentOf/ns:timepointEvent/ns:code',
                    namespaces={'ns': 'urn:hl7-org:v3'})

                if node is not None and len(node) == 1:
                    node[0].set('code', value)
                    node[0].set('displayName', value)

            # Effective start / stop
            elif mod == "start":
                node = newaecg.getroot().xpath(
                    '//ns:component/ns:series/ns:effectiveTime/ns:low',
                    namespaces={'ns': 'urn:hl7-org:v3'})
                if node is not None and len(node) == 1:
                    node[0].set('value', str(value))

                node = newaecg.getroot().xpath(
                    '//ns:series/ns:component/ns:sequenceSet/'
                    'ns:component/ns:sequence/ns:value/ns:head',
                    namespaces={'ns': 'urn:hl7-org:v3'})
                if node is not None and len(node) == 1:
                    node[0].set('value', str(value))

                node = newaecg.getroot().xpath(
                    '//ns:component/ns:series/ns:effectiveTime/ns:high',
                    namespaces={'ns': 'urn:hl7-org:v3'})
                if node is not None and len(node) == 1:
                    node[0].set('value', str(value + 10))

                node = newaecg.getroot().xpath(
                    '//ns:component/ns:derivedSeries/ns:effectiveTime/ns:low',
                    namespaces={'ns': 'urn:hl7-org:v3'})
                if node is not None and len(node) == 1:
                    node[0].set('value', str(value))

                node = newaecg.getroot().xpath(
                    '//ns:component/ns:derivedSeries/ns:effectiveTime/ns:high',
                    namespaces={'ns': 'urn:hl7-org:v3'})
                if node is not None and len(node) == 1:
                    node[0].set('value', str(value + 10))

        # Replace the original 2002112209 times with the start times
        xmlstr = etree.tostring(newaecg, pretty_print=True).decode()
        xmlstr = xmlstr.replace("2002112209", str(file["start"])[0:-4])
        # Save
        with open(output_file, "w") as f:
            f.write(xmlstr)

        num = num + 1
