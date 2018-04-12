from xml.dom import minidom
import sys
import re
import urllib2
import urllib
import json
import datetime

minimalRateToPass = 80
passedStatus = 1
failedStatus = 5
projectId = str(0)
authKey = "Your Basic Authorization Key"
testRailAdress = "https://example.testrail.net"
headers = {"Content-Type": "application/json",
           "Authorization": authKey}


def openXML(filename):
    try:
        if len(sys.argv) > 3:
            xmldoc = minidom.parse(
                sys.argv[2] + "/" + sys.argv[3] + '/' + filename)
        else:
            xmldoc = minidom.parse(filename)
        print("Test results file opened...")
        return(xmldoc.getElementsByTagName('testsuite'))
    except:
        print("\n")
        print("------------- Error: can't open test-results.xml -------------")
        print("\n")


def parseXML(testSuites):
    results = {}
    for i in testSuites:
        name = i.getAttribute('name')
        file = str(i.getAttribute('file'))
        if len(file) > 0:
            testCases = i.getElementsByTagName("testcase")
            for m in testCases:
                if str(file) not in results:
                    results[str(file)] = []
                if len(m.childNodes) == 1:
                    results[str(file)].append(
                        [m.getAttribute('name'), passedStatus])
                else:
                    results[str(file)].append([m.getAttribute('name'), failedStatus, str(m.childNodes[1].firstChild.nodeValue).replace(
                        '\n', '').replace('  ', '').replace('at Context.<anonymous>', '').replace('AssertionError: ', '')])
    print("Test results are parsed...")
    return(results)


def passRate(parsedResults):
    rates = {}
    for i in parsedResults:
        numberOfPassed = 0.0
        numberOfFailed = 0.0
        for m in parsedResults[i]:
            if m[1] == 1:
                numberOfPassed += 1
            else:
                numberOfFailed += 1
            if numberOfPassed == 0:
                rate = 0
            else:
                rate = int(
                    round((100 - (numberOfFailed / (numberOfPassed + numberOfFailed)) * 100.0), 0))
            rates[i] = rate
        print("Pass rate: " + str(rate))
    return(rates)


def jsonGenerator(testResults, passRate):
    toSend = {}
    for test in testResults:
        fileName = re.findall(r'(C\d*.*)', test)[0]

        json = {}
        if passRate[test] < minimalRateToPass:
            json["status_id"] = failedStatus
        else:
            json["status_id"] = passedStatus
        json["comment"] = "Pass Rate: " + \
            str(passRate[test]) + " %" + "\n" + "File: " + fileName
        print(json["comment"])
        json["elapsed"] = " "
        json["defects"] = " "
        json["version"] = " "
        if len(sys.argv) > 1:
            json["custom_tester"] = sys.argv[1]
        else:
            json["custom_tester"] = "Specify the tester"
        json["custom_step_results"] = []
        for step in testResults[test]:
            stepsResults = {}
            stepStatus = str(step[1])
            stepName = str(step[0])
            stepsResults["status_id"] = stepStatus
            stepsResults["content"] = stepName
            stepsResults["expected"] = ""
            if len(step) > 2:
                stepComment = str(step[2])
                stepsResults["actual"] = stepComment
            else:
                stepsResults["actual"] = ""
            json["custom_step_results"].append(stepsResults)
        toSend[test] = json
    print("JSON Generated and ready to send...")
    return(toSend)


def newRun(casesId, name):
    url = testRailAdress + "/index.php?/api/v2/add_run/" + projectId
    data = {
        "suite_id": 1,
        "name": str(name),
        "assignedto_id": 1,
        "include_all": False,
        "case_ids": casesId
    }
    try:
        request = urllib2.Request(url, json.dumps(data), headers)
        result = urllib2.urlopen(request)
        result = json.loads(result.read())
        print("New Test Run Generated... id: " + str(result["id"]))
        return(result["id"])
    except:
        print("\n")
        print("------------- Error: Failed for New Test Run Generation -------------")
        print("\n")


def sendResults(testruns):
    casesId = []
    for data in testruns:
        try:
            caseId = re.findall(r'/(C\d*)_', data)[0].replace('C', '')
            casesId.append(caseId)
        except:
            print("\n")
            print("------------- Error: Check " + data +
                  " name, add C***** in the beginning -------------")
            print("\n")
            continue
    date = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
    testName = sys.argv[1] + " tests | " + date
    id = newRun(casesId, testName)
    for caseId in casesId:
        url = testRailAdress + "/index.php?/api/v2/add_result_for_case/"
        url = url + str(id) + "/" + caseId
        try:
            request = urllib2.Request(url, json.dumps(testruns[data]), headers)
            result = urllib2.urlopen(request)
            print("Test Results for CaseId: " + caseId + " Uploaded...")
        except:
            print("\n")
            print(
                "------------- Error: Failed to Send Result -------------")
            print("\n")


openedXML = openXML('test-results.xml')
testResults = parseXML(openedXML)
rate = passRate(testResults)
data = jsonGenerator(testResults, rate)
sendResults(data)
