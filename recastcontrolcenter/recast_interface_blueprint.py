import json
import requests
import os
import glob
import zipfile
import pickle
import pkg_resources
import recastconfig
import importlib
from flask import Blueprint, render_template, jsonify, request, session
import recastcontrolcenter.backendtasks as asynctasks
from recastbackend.catalogue import getBackends



import logging
log = logging.getLogger(__name__)

celery_app  = importlib.import_module(recastconfig.config['RECAST_CELERYAPP']).app
celery_app.set_current()

import recastapi.request.get
import recastapi.analysis.get
import recastbackend.jobstate

recast = Blueprint('recast', __name__, template_folder='recast_interface_templates')

@recast.route('/request/<reqid>')
def recast_request_view(reqid):
  request_info = recastapi.request.get.request(reqid)

  analysis_id = recastapi.request.get.request(reqid)['analysis_id']
  analysis_info = recastapi.analysis.get.analysis(analysis_id)

  parpoints = recastapi.request.get.point_requests_for_scan(reqid)['_items']
  basic_req_data = {
    p['id']:recastapi.request.get.basic_requests_for_point(p['id'])['_items']
        for p in parpoints
  }


  backends = getBackends(analysis_id)

  from recastbackend.jobstate import get_flattened_jobs
  processing_info = {}
  for k,v in basic_req_data.iteritems():
      for basic_req in v:
          processing_info[basic_req['id']] = get_flattened_jobs(celery_app,basic_req['id'],backends)

  log.info('proc info is %s',processing_info)

  return render_template('recast_request.html', request_info  = request_info,
                                                parpoints = enumerate(parpoints),
                                                basic_req_data = basic_req_data,
                                                analysis_info = analysis_info,
                                                backends      = backends,
                                                processing_info   = processing_info)

@recast.route('/requests')
def recast_requests_view():
  requests_info = recastapi.request.get.request()
  backend_data = {}
  for req in requests_info:
      backend_data[req['id']] = getBackends(req['analysis_id'])
  return render_template('recast_all_requests.html',
    requests_info = reversed(requests_info),
    backend_data = backend_data
  )

@recast.route('/processBasicRequest', methods=['GET'])
def process_request_point():
  backend = request.args['backend']
  basicreqid = request.args['basicreqid']
  analysisid = int(request.args['analysisid'])

  from recastbackend.submission import submit_recast_request
  jobguid,result = submit_recast_request(basicreqid,analysisid,backend)

  log.info('jobguid is: %s, celery id is: %s',jobguid,result)
  return jsonify(jobguid=jobguid)


def zipdir(path, zip):
    for root, dirs, files in os.walk(path):
        for file in files:
            zip.write(os.path.join(root, file),os.path.join(root, file).split('/',2)[-1])

@recast.route('/updateResponse/<request_uuid>')
def uploadresults(request_uuid):
  if not session.has_key('user'):
    return jsonify(error = 'not authorized')

  return jsonify(error = 'not implemented')

@recast.route('/uploadzenodo/<request_uuid>')
def uploadresultszenodo(request_uuid):
  if not session.has_key('user'):
    return jsonify(error = 'not authorized')
  return jsonify(error = 'not implemented')
