import click
import os
import ssl
import yaml
import pkg_resources
import subprocess
import logging
from socketio.server import serve
logging.basicConfig(level = logging.INFO)

@click.group()
def servercli():
  pass

@servercli.command()
@click.option('--config','-c')
def server(config):
  if config:
    os.environ['RECASTCONTROLCENTER_CONFIG'] = config
  import server
  serve(server.flask_app, port = os.environ['RECAST_SERVER_PORT'], host = '0.0.0.0', transports = 'xhr-polling',
        certfile = os.environ['RECAST_SSL_CERTFILE'], keyfile = os.environ['RECAST_SSL_KEYFILE'], ssl_version=ssl.PROTOCOL_SSLv23)

@servercli.command()
@click.option('--config','-c')
def celery(config):
  if config:
    os.environ['RECASTCONTROLCENTER_CONFIG'] = config
  import recastconfig
  subprocess.call(['celery','worker','-A',recastconfig.config['RECAST_CELERYAPP'],'-I','recastcontrolcenter.backendtasks','-l','debug'])
