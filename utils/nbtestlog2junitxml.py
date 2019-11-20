# Generate a junit-xml file from parsing a nbtest log

import re
from xml.etree.ElementTree import Element, ElementTree
from os import path
import string
from enum import Enum


startingPatt = re.compile("^STARTING: ([\w\.\-]+)$")
skippingPatt = re.compile("^SKIPPING: ([\w\.\-]+)$")
exitCodePatt = re.compile("^EXIT CODE: (\d+)$")
timePatt = re.compile("^real\s+([\d\.ms]+)$")
linePatt = re.compile("^" + ("-" * 80) + "$")


def makeTestCaseElement(attrDict):
    return Element("testcase", attrib=attrDict)


def makeSystemOutElement(outputLines):
    e = Element("system-out")
    e.text = "".join(filter(lambda c: c in string.printable, outputLines))
    return e


def makeFailureElement(outputLines):
    e = Element("failure", message="failed")
    e.text = "".join(filter(lambda c: c in string.printable, outputLines))
    return e


def setFileNameAttr(attrDict, fileName):
    attrDict.update(file=fileName,
                    classname="",
                    line="",
                    name="",
                    time=""
                   )


def setTestNameAttr(attrDict, testName):
    attrDict["classname"] = "%s.%s" % \
                            (path.splitext(path.basename(attrDict["file"]))[0],
                             testName)
    attrDict["name"] = testName


def setTimeAttr(attrDict, timeVal):
    (mins, seconds) = timeVal.split("m")
    seconds = float(seconds.strip("s")) + (60 * int(mins))
    attrDict["time"] = str(seconds)


def incrNumAttr(element, attr):
    newVal = int(element.attrib.get(attr)) + 1
    element.attrib[attr] = str(newVal)


def parseLog(logFile, testSuiteElement):
    # Example attrs:
    # errors="0" failures="0" hostname="a437d6835edf" name="pytest" skipped="2" tests="6" time="6.174" timestamp="2019-11-18T19:49:47.946307"

    with open(logFile) as lf:
        testSuiteElement.attrib["tests"] = "0"
        testSuiteElement.attrib["errors"] = "0"
        testSuiteElement.attrib["failures"] = "0"
        testSuiteElement.attrib["skipped"] = "0"
        testSuiteElement.attrib["time"] = "0"
        testSuiteElement.attrib["timestamp"] = ""

        attrDict = {}
        #setFileNameAttr(attrDict, logFile)
        setFileNameAttr(attrDict, "nbtest")

        parseStateEnum = Enum("parseStateEnum",
                              "newTest startingLine finishLine exitCode")
        parseState = parseStateEnum.newTest

        testOutput = ""

        for line in lf.readlines():
            if parseState == parseStateEnum.newTest:
                m = skippingPatt.match(line)
                if m:
                    setTestNameAttr(attrDict, m.group(1))
                    skippedElement = makeTestCaseElement(attrDict)
                    skippedElement.append(Element("skipped", message="", type=""))
                    testSuiteElement.append(skippedElement)
                    incrNumAttr(testSuiteElement, "skipped")
                    incrNumAttr(testSuiteElement, "tests")
                    continue

                m = startingPatt.match(line)
                if m:
                    parseState = parseStateEnum.startingLine
                    testOutput = ""
                    setTestNameAttr(attrDict, m.group(1))
                    continue

                continue

            elif parseState == parseStateEnum.startingLine:
                if linePatt.match(line):
                    parseState = parseStateEnum.finishLine
                    testOutput = ""
                continue

            elif parseState == parseStateEnum.finishLine:
                if linePatt.match(line):
                    parseState = parseStateEnum.exitCode
                else:
                    testOutput += line
                continue

            elif parseState == parseStateEnum.exitCode:
                m = exitCodePatt.match(line)
                if m:
                    testCaseElement = makeTestCaseElement(attrDict)
                    if m.group(1) != "0":
                        failureElement = makeFailureElement(testOutput)
                        testCaseElement.append(failureElement)
                        incrNumAttr(testSuiteElement, "failures")
                    else:
                        systemOutElement = makeSystemOutElement(testOutput)
                        testCaseElement.append(systemOutElement)

                    testSuiteElement.append(testCaseElement)
                    parseState = parseStateEnum.newTest
                    testOutput = ""
                    incrNumAttr(testSuiteElement, "tests")
                    continue

                m = timePatt.match(line)
                if m:
                    setTimeAttr(attrDict, m.group(1))
                    continue

                continue


if __name__ == "__main__":
    import sys

    testSuitesElement = Element("testsuites")
    testSuiteElement = Element("testsuite", name="nbtest", hostname="")
    parseLog(sys.argv[1], testSuiteElement)
    testSuitesElement.append(testSuiteElement)
    ElementTree(testSuitesElement).write(sys.argv[1]+".xml", xml_declaration=True)
