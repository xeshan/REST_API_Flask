from db import dynamodb
from boto3.dynamodb.conditions import Key, Attr
from flask_restful import Resource, reqparse, request
from time import strftime
import datetime
from models.schedule import ScheduleModel
import boto3
import uuid
import os
import json
from models.creds import CredsModel
from resources.creds import Credsregion, Creds
from resources.snapshot import SnapshotLsLS, SnapshotLsSidCr
import requests
import time
import traceback

from shared import logging
log = logging.Logger('api-schedule')

from shared import wpmudev

class Schedule(Resource):

    parser = reqparse.RequestParser()
    for args in ['site_name','bu_frequency', 'bu_status', 'bu_time', 'bu_files', 'bu_tables', 'bu_exclusion_enabled']:
        parser.add_argument(args,
            required = True,
            help = "'{}' can't blank".format(args)
        )

    for args in ['bu_frequency_weekday','bu_frequency_monthday','bu_snapshot_name', 'bu_region', 'is_automate']:
        parser.add_argument(args)

    for args in ['plugin_v']:
        parser.add_argument(args,
            required = True,
            help = "old plugin version"
        )       

    table =  dynamodb.Table('schedules')

    def get(self, site_id, schedule_id):
        schedule = ScheduleModel.find_by_name(site_id, schedule_id)

        if schedule:
            return schedule 
        return {'message': 'Schedule not found'}, 404

    def post(self, site_id):
        data = Schedule.parser.parse_args()
        schedule_id = str(uuid.uuid4())[:13]
        log.debug("#### post data ####")
        log.debug(data)
        API_URL = os.environ["api_url"]
        headers = {'content-type': 'application/json', 'Snapshot-APIKey': request.headers['Snapshot-APIKey']}

        if not data['bu_region']:
            creds = Credsregion.get_by_site_id(site_id)
            if creds and creds.get("bu_region") != "null":
                data["bu_region"] = creds.get("bu_region")
            else:
                return {"message": "bu_region is null or not found"}, 400

        if not data['bu_frequency_weekday']: 
            data['bu_frequency_weekday'] = "null" 
        if not data['bu_frequency_monthday']:
            data['bu_frequency_monthday'] = "null"
        if not data['bu_snapshot_name']:
            data['bu_snapshot_name'] = "null" 
        if not data['is_automate']:
            data['is_automate'] = "0"

        if data['bu_frequency'] == "manual":
            last_snapshots = SnapshotLsLS.get_by_site_id(site_id)
            current_utc_time = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M")
            if last_snapshots:
                for x in last_snapshots:
                    created_at = datetime.datetime.strptime(x['created_at'], '%Y-%m-%d %H:%M:%S').strftime("%Y-%m-%d %H:%M")
                    if data['bu_frequency'] == x['bu_frequency']:
                        if created_at == current_utc_time:
                            return {"message": "backup can't run in same minute"}, 400


            dt = datetime.datetime.utcnow() + datetime.timedelta(days=1)
            dt_check = dt.strftime('%Y-%m-%d')
            current = SnapshotLsSidCr.get_by_site_id_and_date(site_id, dt_check)
            if current == SnapshotLsSidCr.RESP_SNAPSHOT_RUNNING:
                return {"message": "another backup is already running"}, 400
                        
            data['site_id'] = site_id
            data['wpmudev_apikey'] = request.headers['Snapshot-APIKey']
            client = boto3.client('lambda')
            response = client.invoke(
                FunctionName = os.environ.get('trigger'),
                InvocationType = 'Event',
                Payload = str.encode(json.dumps(data))
            )
            Schedule.update_creds(site_id, schedule_id, request.headers['Snapshot-APIKey'])
            return {"message": "manual backup process started"}, 200 

        if ScheduleModel.find_by_frequency(site_id, data['bu_frequency']):
            return {'warning': "schedule for '{}' already exists".format(data['site_name'])}, 400

        log.debug(data)
        schedule = ScheduleModel(site_id, schedule_id, data['site_name'], data['bu_frequency'], data['bu_status'], data['bu_region'], data['bu_time'], data['bu_files'], data['bu_tables'], data['bu_frequency_weekday'], data['bu_frequency_monthday'], data['bu_exclusion_enabled'])

        try:
            schedule.insert()
            Schedule.update_creds(site_id, schedule_id, request.headers['Snapshot-APIKey'])
        except Exception as e:
            log.error(f"Error inserting schedule: { e }")
            traceback.print_exc()
            return {"message": "An error occurred inserting the schedule"}, 500  

        return schedule.json(), 201

    def delete(self, site_id, schedule_id):
        schedule = ScheduleModel.find_by_name(site_id, schedule_id)
        if schedule is None:
            return {'message': "Schedule not exists"}, 404

        Schedule.table.delete_item(
            Key = {
                'site_id': schedule['site_id'],
                'schedule_id': schedule['schedule_id']
            } 
        )
        return {'message': 'Schedule deleted'}

    def put(self, site_id, schedule_id):
        data = Schedule.parser.parse_args()
        return Schedule.update_schedule(site_id, schedule_id, data, request.headers['Snapshot-APIKey'])

    def update_creds(site_id, schedule_id, wpmu_apikey):
        utc_time = datetime.datetime.utcnow()
        creds_data = {}
        creds_data['site_id'] = site_id
        creds_data['schedule_id'] = schedule_id
        creds_data['wpmu_apikey'] = wpmu_apikey
        creds_data['created_at'] = utc_time.strftime("%Y-%m-%d %H:%M:%S")
        return Creds.update_creds(site_id, creds_data)

    def update_schedule(site_id, schedule_id, data, apikey):
        log.debug(f"About to update schedule with { data }")
        schedule = ScheduleModel.find_by_name(site_id, schedule_id)
        API_URL = os.environ["api_url"]
        headers = {'content-type': 'application/json', 'Snapshot-APIKey': apikey}

        if not data.get("bu_region"):
            creds = Credsregion.get_by_site_id(site_id)
            if creds and creds.get("bu_region") != "null":
                data["bu_region"] = creds.get("bu_region")
            else:
                return {"message": "bu_region is null or not found"}, 400

        utc_time = datetime.datetime.utcnow()       
        updated_schedule = ScheduleModel(site_id, schedule_id, data['site_name'], data['bu_frequency'], data['bu_status'], data['bu_region'], data['bu_time'],  data['bu_files'], data['bu_tables'],data['bu_frequency_weekday'], data['bu_frequency_monthday'], data['bu_exclusion_enabled'])
        if schedule:
            try:
                response = updated_schedule.update(schedule)
                if not f"{ data.get('bu_frequency_monthday') }".isnumeric():
                    data['bu_frequency_monthday'] = '0'
                data_wpmudev = {'domain': data['site_name'], 'schedule_frequency': data['bu_frequency'], 'schedule_time': data['bu_time'],  'schedule_frequency_weekday': data['bu_frequency_weekday'], 'schedule_frequency_monthday': data['bu_frequency_monthday'], 'schedule_is_active': data['bu_status']}
                res = wpmudev.post(request.headers['Snapshot-APIKey'], data_wpmudev)
                if res:
                    log.debug(f"DEV site ping response: { res.content }")
                else:
                    log.error(f"DEV site response error: { res }")
                return data, 200
            except Exception as e:
                log.error(f"Error updating schedule: { e }")
                traceback.print_exc()
                return {'message': "An error occurred updating the schedule"}, 500

        return {'message': "Schedule for '{}' not exists".format(data['site_name'])}, 404


class Schedulelist(Resource):
    def get(self, site_id):
        response = ScheduleModel.table.query(
            KeyConditionExpression=Key('site_id').eq(site_id)
        )
        if response['Items']:
            return response['Items']
        return {'message': "Schedule not found for site id {}".format(site_id)}, 404

