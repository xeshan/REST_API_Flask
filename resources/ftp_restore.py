from db import dynamodb
from boto3.dynamodb.conditions import Key, Attr
from flask_restful import Resource, reqparse, request
import json
import uuid
from time import strftime
import datetime
from models.ftp_restore import FtpRestoreModel, FtpRestoreUpdateModel
import pysftp
from ftplib import FTP
import boto3
import uuid
import os
from resources.export import Export
from shared import logging
log = logging.Logger('api-ftprestore')

class FtpRestore(Resource):

    parser = reqparse.RequestParser()

    for args in ['ftp_conntype', 'ftp_host', 'ftp_port', 'ftp_user', 'ftp_password', 'snapshot_id', 'ftp_rootdir', 'site_url']:
        parser.add_argument(args,
            required = True,
            help = "'{}' can't blank".format(args)        	
        	)

    def post(self, site_id):
        data = FtpRestore.parser.parse_args()
        log.debug(f"data received: {data}")
        ftp_id = str(uuid.uuid4())[-12:]
        data['created_at'] = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        s3_res = boto3.resource('s3')
        s4_restore_fname = 'snapshot-restorer-' + str(uuid.uuid4().hex)[:13] + '.php'
        s3_res.meta.client.download_file(
            's4-ftprestore-script',
            'snapshot-restorer.php',
            '/tmp/' + s4_restore_fname
        )

        fconn = FtpRestore.conn_test(data['ftp_host'], data['ftp_user'], data['ftp_password'], data['ftp_conntype'], data['ftp_port'], data['ftp_rootdir'], '/tmp/' + s4_restore_fname)
        if fconn[1] == 400:
        	return {'Error': "Invalid FTP credentials"}, 400
        
        res = FtpRestore.trigger_export(site_id, data)
        log.log(f"response from export trigger {res}")
        is_completed = False
        is_failed = False
        current_stage = "queued_for_restore"
        progress = False

        ftpcreds = FtpRestoreModel(ftp_id, site_id, data['created_at'], data['ftp_conntype'], data['ftp_host'], data['ftp_port'], data['ftp_user'], data['ftp_password'], data['ftp_rootdir'], is_completed, is_failed, current_stage, progress)
        ftpcreds.insert()
        SQS_URL = 'https://sqs.us-west-1.amazonaws.com/066804445912/s4-ftprestore'
        sqs = boto3.client('sqs')
        qdata = {}
        qdata['site_id'] = site_id
        qdata['export_id'] = res['export_id']
        qdata['fname'] = s4_restore_fname
        qdata['api_key'] = request.headers['Snapshot-APIKey']
        qdata['ftp_id'] = ftp_id
        qdata['site_url'] = data['site_url']
        # sqs.send_message(
        #     QueueUrl=SQS_URL,
        #     MessageBody=json.dumps(qdata)
        #     )

        client = boto3.client('lambda')
        response = client.invoke(
            FunctionName = os.environ.get('ftprestore'),
            InvocationType = 'Event',
            Payload = str.encode(json.dumps(qdata))
        )

        log.log(f"quu")
        hdata={}
        hdata['ftp_id'] = ftp_id
        hdata['is_completed'] = False
        hdata['is_failed'] = False
        hdata['current_stage'] = "restore_triggered"
        hdata['progress'] = int(0)

        return json.dumps(hdata), 200

    @classmethod
    def trigger_export(self, site_id, data):
        export_data = {}
        export_data['site_id'] = site_id
        export_data['snapshot_id'] = data.get('snapshot_id')
        export_data['send_email'] = '0'
        export_data['email_account'] = None
        export_data['display_name'] = None
        export_data['hub_request'] = None
        export_data['export_status'] = None
        export_data['processor_flag'] = False
        return Export.init_export(site_id, export_data)

    def conn_test(ftp_host, ftp_user, ftp_passwd, conn_type, ftp_port, remote_path, local_path):
        if conn_type == 'ftp':
            log.log("ftp connection test")
            try:
                ftp = FTP(ftp_host, ftp_user, ftp_passwd)
                ftp.encoding = "utf-8"
                ftp.cwd(remote_path)
                fname = local_path.split('/')[2]
                with open(local_path,'rb') as file:
                    ftp.storbinary(f"STOR {fname}", file)                
            except Exception as e:
                print(e)
                return {'Error': "Invalid credentials"}, 400
            else:
                ftp.close()
                return {'Message': "Valid credentials"}, 200
        elif conn_type == 'sftp':
            log.log("sftp connection test")
            cnopts = pysftp.CnOpts()
            cnopts.hostkeys = None
            try:
                with pysftp.Connection(ftp_host, username=ftp_user, password=ftp_passwd, port=int(ftp_port), cnopts=cnopts) as sftp:
                    with sftp.cd(remote_path):
                        sftp.put(local_path)
                    sftp.close()

            except Exception as e:
                log.error(f"Invalid credentials: { e }")
                return {'Error': 'Invalid credentials'}, 400
            else:
                return {'Message': 'Valid credentials'}, 200

    def get(self, site_id, ftp_id):
        ftp_inst = FtpRestoreModel.find_by_siteid(site_id, ftp_id)
        if ftp_inst:
            return ftp_inst[0]

class FtpRestoreUpdate(Resource):
    print("FtpRestoreUpdate ..... ")
    parser = reqparse.RequestParser()

    for args in ['current_stage', 'is_completed', 'is_failed', 'progress']:
        parser.add_argument(args)

    def put(self, site_id, ftp_id):
        creds = FtpRestoreModel.find_by_siteid(site_id, ftp_id)
        if not creds:
            return {'error': 'no ftp creds found'}

        data = FtpRestoreUpdate.parser.parse_args()

        if not data['current_stage']:
            data['current_stage'] = creds[0]['current_stage']
        if not data['is_completed']:
            data['is_completed'] = creds[0]['is_completed']
        if not data['is_failed']:
            data['is_failed'] = creds[0]['is_failed']
        if not data['progress']:
            data['progress'] = creds[0]['progress']

        updated_creds = FtpRestoreUpdateModel(site_id, ftp_id, data['is_completed'], data['is_failed'], data['current_stage'] ,  data['progress'])
        response = updated_creds.update(creds[0])
        if creds:
            try:
                response = updated_creds.update(creds[0])
                print(f"ftp creds update response > {response}")
                return data, 200
            except:
                return {'message': "An error occurred updating the ftp credentials"}, 500

    def get(self, site_id, ftp_id):
        print("FtpRestoreUpdate get ")
        ftp_inst = FtpRestoreModel.find_by_siteid(site_id, ftp_id)
        if ftp_inst:
            print(ftp_inst[0])
            del[ftp_inst[0]['ftp_user']]
            del[ftp_inst[0]['ftp_password']]
            del[ftp_inst[0]['ftp_conntype']]
            del[ftp_inst[0]['ftp_rootdir']]
            del[ftp_inst[0]['ftp_port']]
            del[ftp_inst[0]['ftp_host']]
            return ftp_inst[0]

