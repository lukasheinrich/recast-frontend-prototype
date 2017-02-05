from celery import shared_task
import recastapi.request
import recastapi.analysis
import os
import sys
import json
import requests
import logging
import yaml
import re
import StringIO

log = logging.getLogger(__name__)


@shared_task
def upload_in_background(requestuuid, username, description, nevents, xsec, zipfilename):
    print 'uploading in background with\n{}\n{}\n{}\n{}\n{}\n{}'.format(requestuuid, username, description, nevents, xsec, zipfilename)
    print 'process id:', os.getpid()
    try:
        r = recastapi.request.add_parameter_point(
            requestuuid, username, description, nevents, xsec, zipfilename)

    except:
        print "Unexpected error:", sys.exc_info()[0]
        raise
    print "upload status: {}".format(r.ok)

import recastconfig
ACCESS_TOKEN = recastconfig.config['RECAST_ZENODO_TOKEN']


def createdeposition(requestuuid, **kwargs):
    log.info('hello')

    url = "http://sandbox.zenodo.org/api/deposit/depositions/?access_token={}".format(
        ACCESS_TOKEN)

    headers = {"Content-Type": "application/json"}
    data = {"metadata":
            {
                "access_right": "embargoed",
                "embargo_date": "2016-01-01",
                "upload_type": "dataset",
                "creators": [{"name": "Heinrich, Lukas", "affiliation": "NYU"}]
            }
            }
    data['metadata'].update(**kwargs)

    r = requests.post(url, data=json.dumps(data), headers=headers)
    assert r.ok
    log.info('response: {} {}'.format(r.status_code, r.reason))
    log.info('content:{}'.format(r.content))
    deposition_id = r.json()['id']
    log.info('deposition id is: {}'.format(deposition_id))
    return deposition_id


def upload(deposition_id, filename, file):
    url = "http://sandbox.zenodo.org/api/deposit/depositions/{}/files?access_token={}".format(
        deposition_id, ACCESS_TOKEN)
    data = {'filename': filename}
    files = {'file': file}
    r = requests.post(url, data=data, files=files)
    log.info('response: {} {}'.format(r.status_code, r.reason))
    log.info('content:{}'.format(r.content))
    assert r.ok


def publish(deposition_id):
    print deposition_id
    url = "http://sandbox.zenodo.org/api/deposit/depositions/{}/actions/publish?access_token={}".format(
        deposition_id, ACCESS_TOKEN)
    r = requests.post(url)
    log.info('response: {} {}'.format(r.status_code, r.reason))
    log.info('content:{}'.format(r.content))
    assert r.ok


def uploadzenodo_request(requestuuid):
    request_info = recastapi.request.request(requestuuid)

    # the request should be a supplement to the theorist's paper that
    # generated the request
    supplement_to = []
    match = re.search("([0-9]{4}.[0-9]{4})",
                      request_info['additional-information'])
    if match:
        arxiv_id = match.group(1)
        supplement_to += [{"relation": "isSupplementTo",
                           "identifier": arxiv_id}]

    # upload request
    depoid = createdeposition(requestuuid,
                              title="RECAST request {}".format(requestuuid),
                              description="RECAST request {}".format(
                                  requestuuid),
                              related_identifiers=supplement_to
                              )

    request_info_stream = StringIO.StringIO(
        yaml.safe_dump(request_info, encoding='utf-8'))
    upload(depoid, 'requestinfo.yaml', request_info_stream)
    publish(depoid)


def uploadzenodo_response(rootdir, requestuuid):
    request_info = recastapi.request.request(requestuuid)

    # the response should be a supplement to the original analysis by the
    # experiment that's being recast
    analysis_info = recastapi.analysis.analysis(request_info['analysis-uuid'])
    supplement_to = []
    if 'doi' in analysis_info:
        supplement_to += [{"relation": "isSupplementTo",
                           "identifier": analysis_info['doi'].split(':')[-1]}]

    # upload response
    depoid = createdeposition(requestuuid,
                              title="RECAST request response {}".format(
                                  requestuuid),
                              description="RECAST request response {}".format(
                                  requestuuid),
                              related_identifiers=supplement_to
                              )
    absroot = os.path.abspath(rootdir)
    all_files = [root.rstrip('/') + '/' + f for root,
                 subdir, files in os.walk(absroot) for f in files]
    for file in all_files:
        truncated = file.replace('{}/'.format(absroot), '')
        upload(depoid, truncated, open(file, 'rb'))

    publish(depoid)


@shared_task
def uploadallzenodo(rootdir, requestuuid):
    uploadzenodo_request(requestuuid)
    uploadzenodo_response(rootdir, requestuuid)
