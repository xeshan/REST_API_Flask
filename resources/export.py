from db import dynamodb
from boto3.dynamodb.conditions import Key, Attr
from flask_restful import Resource, reqparse, request
import uuid
from time import strftime
import datetime
from models.export import ExportModel
import os
import boto3, json
import traceback

from shared import logging
log = logging.Logger('api-export')

class Export(Resource):

    parser = reqparse.RequestParser()
    for args in ['export_id', 'created_at', 'export_status', 'snapshot_id', 'download_link', 'send_email', 'email_account', 'display_name', 'hub_request', 'processor_flag']:
        parser.add_argument(args,
            help = "'{}' can't blank".format(args)
        )

    table = dynamodb.Table('exports')
    
    def get(self, site_id, export_id):
        export = ExportModel.find_by_export(site_id, export_id)

        if export:
            return export
        return {'message':'Export not found'}, 404
            
    def post(self, site_id):
        data = Export.parser.parse_args()
        log.debug(data)
        try:
            res = Export.init_export(site_id, data)
        except Exception as e:
            traceback.print_exc()
            return {"message": "An error occured queue an export"}, 500
        return res, 201

    def put(self, site_id, export_id):
        export = ExportModel.find_by_export(site_id, export_id)
        data = Export.parser.parse_args()
        utc_time = datetime.datetime.utcnow()       
        
        updated_export = ExportModel(
            site_id, 
            export_id, 
            data['snapshot_id'], 
            data['created_at'], 
            data['export_status'],
            data['download_link'],
            data['send_email'],
            data['email_account'],
            data['display_name'],
            data['hub_request']
        )

        if export:
            try:
                response = updated_export.update(export)
                return data, 200
            except:
                return {'message': "An error occurred updating the export"}, 500

        return {'message': "export for '{}' not exists".format(site_id)}, 404

    @classmethod
    def trigger_export(self, site_id, export_id, data):
        info = {}
        info["site_id"] = site_id
        info["export_id"] = export_id
        info["snapshot_id"] = data['snapshot_id']
        info["wpmudev_apikey"] = request.headers['Snapshot-APIKey']
        info['send_email'] = data['send_email']
        info['email_account'] = data['email_account']
        info['display_name'] = data['display_name']
        info['hub_request'] = data['hub_request']
        info['processor_flag'] = data['processor_flag']

        if data['processor_flag']:
            info['processor_flag'] = data['processor_flag']
        client = boto3.client('lambda')
        response = client.invoke(
            FunctionName = os.environ.get('export'),
            InvocationType = 'Event',
            Payload = str.encode(json.dumps(info))
        )

    @classmethod
    def init_export(self, site_id, data):
        export_id = str(uuid.uuid4())[-12:]
        utc_time = datetime.datetime.utcnow()
        created_at = utc_time.strftime("%Y-%m-%d %H:%M:%S")        
        if not data['export_status']:
            data['export_status'] = "queued_for_export"

        if not data['email_account']:
            data['email_account'] = False
        if not data['display_name']:
            data['display_name'] = False
        if not data['hub_request']:
            data['hub_request'] = False

        export = ExportModel(
            site_id, 
            export_id, 
            data['snapshot_id'], 
            created_at, 
            data['export_status'],
            "null", 
            data['send_email'], 
            data['email_account'],
            data['display_name'],
            data['hub_request']
        ) 
        try:
            Export.trigger_export(site_id, export_id, data)        
            export.insert()     

        except Exception as e:
            log.error(f"An error occured queue an export: { e }")
            traceback.print_exc()
            raise e

        return export.json()


class Exportlist(Resource):
    def get(self, site_id, snapshot_id):
        response = Export.table.query(
            IndexName='site_snap_id-index',
            KeyConditionExpression= "site_id= :site_id and snapshot_id= :snap_id",
            ExpressionAttributeValues= {
                ":site_id":site_id,
                ":snap_id":snapshot_id
            }
        )
        if response['Items']:
            return response['Items']
