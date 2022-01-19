from db import dynamodb
from boto3.dynamodb.conditions import Key, Attr
from flask_restful import Resource, reqparse, request
import uuid
from time import strftime
import datetime
from models.creds import CredsModel
from models.schedule import ScheduleModel
import os
import requests
import json
import traceback

from shared import logging
log = logging.Logger('api-creds')

class Creds(Resource):

    parser = reqparse.RequestParser()
    for args in ['schedule_id','created_at','wpmu_apikey', 'bu_region', 'rotation_frequency']:
        parser.add_argument(args)

    table = dynamodb.Table('creds')
    
    def get(self, site_id, api_key):
        creds = CredsModel.find_by_wpmu_apikey(site_id, api_key)

        if creds:
            return creds
        return {'message':'creds not found'}, 404
            
    def post(self, site_id):
        data = Creds.parser.parse_args()
        log.debug(data);

        if data['bu_region']: 
            if data['bu_region'] == 'US' or data['bu_region'] == 'EU':
                print("equal")
            else:
                return {"message": "Backup region should be US or EU"}, 400

        if data['rotation_frequency']: 
            if data['rotation_frequency'].isnumeric() == False:
                return {"message": "Invalid rotation_frequency"}, 400
            elif int(data['rotation_frequency']) not in range(1, 31):
                return {"message": "Rotation frequency range should between 1 to 30"}, 400

        try:
            res = Creds.update_creds(site_id, data)
        except Exception as e:
            traceback.print_exc()
            return {"message": "An error occured inserting creds"}, 500
        return res, 201

    def update_creds(site_id, data):
        try:
            find_by_siteid = CredsModel.find_by_siteid(site_id)

            if not data['schedule_id']:
                data['schedule_id'] = "null"
            if not data['created_at']:
                data['created_at'] = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            
            if find_by_siteid:
                if not data['wpmu_apikey'] and 'wpmu_apikey' not in find_by_siteid[0]:
                    data['wpmu_apikey'] = "null"
                elif not data['wpmu_apikey'] and find_by_siteid[0]['wpmu_apikey'] != 'null':
                    data['wpmu_apikey'] = find_by_siteid[0]['wpmu_apikey']
                elif not data['wpmu_apikey'] and find_by_siteid[0]['wpmu_apikey'] == 'null':
                    data['wpmu_apikey'] = "null"

                bu_region = data.get("bu_region")
                if not bu_region and 'bu_region' not in find_by_siteid[0]:
                    bu_region = "null"
                elif not bu_region and find_by_siteid[0]['bu_region'] != 'null':
                    bu_region = find_by_siteid[0]['bu_region']
                elif not bu_region and find_by_siteid[0]['bu_region'] == 'null':
                    bu_region = "null"

                print(f"data is > {data}")
                print(find_by_siteid)
                rotation_frequency = data.get("rotation_frequency")
                print(rotation_frequency)
                if not rotation_frequency and 'rotation_frequency' not in find_by_siteid[0]:
                    rotation_frequency = "null"
                elif not rotation_frequency and find_by_siteid[0]['rotation_frequency'] != 'null':
                    rotation_frequency = find_by_siteid[0]['rotation_frequency']
                elif not rotation_frequency and find_by_siteid[0]['rotation_frequency'] == 'null':
                    rotation_frequency = "null"

                data['bu_region'] = bu_region
                data['rotation_frequency'] = rotation_frequency
                creds = CredsModel(site_id, data['schedule_id'], data['wpmu_apikey'], data['created_at'], data['bu_region'], data['rotation_frequency'])

                creds.update(find_by_siteid[0])

            else:
                bu_region = data.get("bu_region")
                if not data['wpmu_apikey']:
                    data['wpmu_apikey'] = 'null'
                if not bu_region:
                    bu_region = 'null'
                data['bu_region'] = bu_region
                creds = CredsModel(site_id, data['schedule_id'], data['wpmu_apikey'], data['created_at'], data['bu_region'], data['rotation_frequency'])

                creds.insert()

        except Exception as e:
            log.error(f"Error updating creds: { e }")
            traceback.print_exc()
            raise e
        else:
            from resources.schedule import Schedule
            schedule_id = data.get("schedule_id")
            schedule_data = ScheduleModel.find_by_name(site_id, schedule_id)
            if schedule_data:
                schedule_data["plugin_v"] = "null"
                del(schedule_data["bu_region"])
                Schedule.update_schedule(site_id, schedule_id, schedule_data, request.headers['Snapshot-APIKey'])

        return creds.json()

class Credsregion(Resource):

    def get(self, site_id):
        creds = Credsregion.get_by_site_id(site_id)
        if not creds:
            return {'message':'region not found'}, 404
        return creds

    def get_by_site_id(site_id):
        creds = CredsModel.find_by_siteid_region(site_id)

        if creds and 'bu_region' in creds[0] and creds[0]['bu_region'] != "null":
            del creds[0]['wpmu_apikey']
            del creds[0]['schedule_id']
            if 'rotation_frequency' in creds[0] and creds[0]['rotation_frequency'] == "null":
                del creds[0]['rotation_frequency']
            return creds[0]
        return None
