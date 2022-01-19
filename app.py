import sys
sys.path.append("code/common")
from flask import Flask, request
from flask_restful import Api
from resources.schedule import Schedule, Schedulelist
from resources.snapshot import Snapshot, Snapshotlist, SnapshotLsSid, SnapshotLsLS, SnapshotBySchedule, SnapshotLsSidCr, SnapshotLsUserid
from resources.export import Export, Exportlist
from resources.creds import Creds, Credsregion
from resources.tpd_creds import TpdCreds, CredsAuthchk, TpdBucketList, TpdActiveList, GenerateToken, ValidateRefreshToken, TpdList
from resources.ftp_restore import FtpRestore, FtpRestoreUpdate
from resources.site_config import SiteConfig
import requests
import os 

app = Flask(__name__)
app.secret_key = 'not_so_easy'
api = Api(app)

from shared import env
from shared import logging
log = logging.Logger('api')

api.add_resource(Schedule, '/<string:site_id>/schedules', methods=['POST'], endpoint="schedules")
api.add_resource(Schedule, '/<string:site_id>/schedules/<string:schedule_id>', endpoint="schedule")  
api.add_resource(Schedulelist, '/<string:site_id>/schedules')
api.add_resource(Snapshot, '/<string:site_id>/snapshots', methods=['POST'], endpoint="snapshots")
api.add_resource(Snapshot, '/<string:site_id>/snapshots/<string:snapshot_id>', endpoint="snapshot" )
api.add_resource(Snapshotlist, '/<string:site_id>/snapshotsls/<string:schedule_id>')
api.add_resource(Snapshotlist, '/<string:site_id>/snapshotsls', methods=['DELETE'], endpoint="snapshotlsdel")
api.add_resource(SnapshotLsSid, '/<string:site_id>/snapshots')
api.add_resource(SnapshotLsLS, '/<string:site_id>/lastsnapshot')
api.add_resource(SnapshotLsUserid, '/<string:user_id>/snapshotsbyuser')
api.add_resource(SnapshotBySchedule, '/<string:schedule_id>/snapshotsbysch/<string:created_at>')
api.add_resource(SnapshotLsSidCr, '/<string:site_id>/snapshotslscr/<string:created_at>')
api.add_resource(Export, '/<string:site_id>/exports', methods=['POST'], endpoint="exports")
api.add_resource(Export, '/<string:site_id>/exports/<string:export_id>', endpoint="export")
api.add_resource(Exportlist, '/<string:site_id>/exportsls/<string:snapshot_id>')
api.add_resource(Creds, '/<string:site_id>/creds', methods=['POST'], endpoint="creds")
api.add_resource(Creds, '/<string:site_id>/creds/<string:api_key>', endpoint="cred")
api.add_resource(Credsregion, '/<string:site_id>/credsls', endpoint="credsregion")
api.add_resource(TpdCreds, '/<string:site_id>/tpd_creds', methods=['POST'], endpoint="tpd_creds_post")
api.add_resource(TpdCreds, '/<string:site_id>/tpd_creds', methods=['GET'], endpoint="tpd_creds_get")
api.add_resource(TpdCreds, '/<string:site_id>/tpd_creds/<string:tpd_id>', endpoint="tpd_creds")
api.add_resource(TpdList, '/<string:site_id>/tpd_credsls', endpoint="tpdcreds")
api.add_resource(CredsAuthchk, '/<string:site_id>/creds_authchk', endpoint="creds_authchk")
api.add_resource(TpdBucketList, '/<string:site_id>/tpd_bucketls', endpoint="bucket_list")
api.add_resource(TpdActiveList, '/<string:site_id>/tpd_activels')
api.add_resource(GenerateToken, '/<string:site_id>/generatetoken')
api.add_resource(ValidateRefreshToken, '/<string:site_id>/valretoken')
api.add_resource(FtpRestore, '/<string:site_id>/ftp_restore', methods=['POST'], endpoint="fr_post")
api.add_resource(FtpRestore, '/<string:site_id>/ftp_restor/<string:ftp_id>', endpoint="fr_get")
api.add_resource(FtpRestoreUpdate, '/<string:site_id>/ftp_restore/<string:ftp_id>', methods=['PUT'], endpoint="ftp_update")
api.add_resource(FtpRestoreUpdate, '/<string:site_id>/ftp_restore/<string:ftp_id>', methods=['GET'])
api.add_resource(SiteConfig, '/<string:user_id>/config', methods=['POST'], endpoint="config")



@app.before_request
def auth_check():
    log_route()
    auth_token = os.environ["auth_token"]
    url = os.environ["WPMUDEV_CUSTOM_API_SERVER"]
    if 'livesite_on_dev_test' in request.headers:
        url = "https://premium.wpmudev.org/api"

    hub_api_url = url + "/snapshot/v2/auth-check"
    api_host = url.split('/')[2]
    site_id = request.path.split("/")[1]
    if 'Snapshot-APIKey' not in request.headers:
        log.error(f"Missing API key in headers: { request.headers }")
        return { 'message' : "Unauthorized" }, 401

    api_key = request.headers['Snapshot-APIKey']
    querystring = {'site_id':site_id, 'api_key':api_key}
    headers = {
        'Authorization': auth_token,
        'User-Agent': "Snapshot Serverless API/1.0",
        'Accept': "*/*",
        'Host': api_host,
        'Accept-Encoding': "gzip, deflate",   'Connection': "keep-alive"
    }
    response = requests.get(hub_api_url, headers=headers, params=querystring)
    if response.status_code != 200:
        log.warning(f"Auth check failed: { response }")
        hub_api_url = url + "/snapshot/v2/auth-user-check"
        querystring = {'user_id':site_id, 'api_key':api_key}
        response = requests.get(hub_api_url, headers=headers, params=querystring)
        if response.status_code != 200:
            log.error(f"User auth check failed: { response }")
            return { 'message' : "Unauthorized" }, 401

def log_route():
    deployment_version = env.get_env_var('DEPLOYMENT_VERSION')
    log.debug(f"REQUEST (ver: { deployment_version }): {request.path} {request.method}")


if __name__ == '__main__':
    from db import dynamodb
    app.run(port=5000,debug=True)

