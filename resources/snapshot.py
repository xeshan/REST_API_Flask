from db import dynamodb
from boto3.dynamodb.conditions import Key, Attr
from flask_restful import Resource, reqparse, request
import uuid
from time import strftime
import datetime
from models.snapshot import SnapshotModel
from resources.tpd_creds import TpdActiveList
import os
import boto3
import pandas as pd
import requests
from flask import request
import shutil
import os.path as path
import time
import json
from datetime import timedelta
import time

from shared import logging
log = logging.Logger('api-schedule')

class Snapshot(Resource):

    parser = reqparse.RequestParser()
    for args in ['schedule_id', 'user_id', 'snapshot_id', 'created_at', 'snapshot_status', 'last_snap', 'bu_frequency', 'site_name', 'bu_region']:
        parser.add_argument(args,
            required = True,
            help = "'{}' can't blank".format(args)
        )

    for args in ['bu_snapshot_name', 'excluded_files', 'snapshot_size', 'plugin_v', 'is_automate', 'tpd_exp_status', 'tpd_exp_done']:
        parser.add_argument(args)

    table = dynamodb.Table('snapshots')
    
    def get(self, site_id, snapshot_id):
        snapshot = SnapshotModel.find_by_snapshot(site_id, snapshot_id)
        if snapshot:
            if snapshot['excluded_files'] != None:
                snapshot['excluded_files'] = snapshot['excluded_files'].replace('\'','')
            return snapshot

        return {'message':'Snapshot not found'}, 404
            
    def post(self, site_id):
        data = Snapshot.parser.parse_args()
        
        if data['schedule_id'] != "manual":
            data['bu_snapshot_name'] = "null"

        API_URL = os.environ["api_url"]
        headers = {'content-type': 'application/json', 'Snapshot-APIKey': request.headers['Snapshot-APIKey']}

        creds = TpdActiveList.get_by_site_id(site_id)
        
        if creds:
            data['tpd_exp_status'] = creds

        snapshot = SnapshotModel(
            site_id, 
            data['snapshot_id'], 
            data['schedule_id'], 
            data['user_id'],
            data['bu_snapshot_name'],
            data['created_at'],
            data['snapshot_status'],
            data['last_snap'],
            data['bu_frequency'],
            data['site_name'],
            data['excluded_files'],
            data['snapshot_size'],
            data['bu_region'],
            data['plugin_v'],
            data['is_automate'],
            data['tpd_exp_status'],
            data['tpd_exp_done']
            )
        log.debug(f"Inserting snapshot: { snapshot.json() }")
        try:
            snapshot.insert()
        except:
            return {"message": "An error occured inserting an snapshot"}, 201
        return snapshot.json(), 201
    
    def delete(self, site_id, snapshot_id):
        
        snapshot = SnapshotModel.find_by_snapshot(site_id, snapshot_id)
        if snapshot is None:
            return {'message': "Snapshot for site id '{}' not exists".format(site_id)}, 404

        print("#################### request started for snapshot #################### > " + str(snapshot))
        print("snapshot going to del > " + str(snapshot))
        s3_client = boto3.client('s3')
        s3_res = boto3.resource('s3')

        key_del = []
        # time.sleep(3)
        site_name_ping = snapshot['site_name']
        if "/" in snapshot['site_name']:
            snapshot['site_name'] = snapshot['site_name'].split("/")[0] + "-" + snapshot['site_name'].split("/")[1]
            print("sub site > " + str(snapshot['site_name']))
            
        pre_created_date = snapshot['created_at'].split(" ")
        pre_time = pre_created_date[1].split(":")
        bucket_key = snapshot['user_id'] + "/" + snapshot['site_id'] + "/" + snapshot['site_name']+ "/" + pre_created_date[0] + "/" + pre_time[0] + "-" + pre_time[1]
        if snapshot['bu_region'] == "US":
            bucket_for_snapshot = os.environ["BUCKET_FOR_SNAPS"]
        else:
            bucket_for_snapshot = os.environ["BUCKET_FOR_SNAPS_EU"]

        manifest_dir = '/tmp/' + snapshot_id + '/'
        if path.exists(manifest_dir) == False:
            os.makedirs(manifest_dir)

        if snapshot['last_snap'] == "1" and 'snap-cleanup' not in request.headers:
            print("promoting 2nd last backup to latest")
    
            API_URL = os.environ["api_url"]
            s3_res.meta.client.download_file(bucket_for_snapshot, bucket_key + "/src/manifest.csv", manifest_dir + "manifest.csv")
            df = pd.read_csv(manifest_dir + 'manifest.csv', index_col=0, dtype='category')
            snapshot_ids = df.columns.values.tolist()
            print("list of snapshots ids > " + str(snapshot_ids))
            if snapshot_ids[-2] != "name":
                headers = {'content-type': 'application/json', 'Snapshot-APIKey': request.headers['Snapshot-APIKey']}
                second_last_snapshot = SnapshotModel.find_by_snapshot(site_id, snapshot_ids[-2])
                print("second last snapshot is > ")
                print(second_last_snapshot)
                second_last_snapshot['last_snap'] = "1"
                print("second_last_snapshot is " + str(second_last_snapshot))
                dt = datetime.datetime.strptime(second_last_snapshot['created_at'], '%Y-%m-%d %H:%M:%S')
                unix_timestamp = time.mktime(dt.timetuple())
                try:
                    resp = Snapshot.update_snapshot(site_id, snapshot_ids[-2], second_last_snapshot)
                    log.debug(f"Updated snapshot: { resp }")
                except:
                    log.warning(f"Error updating snapshot")

            shutil.rmtree(manifest_dir)

        if 'snap-rotation' not in request.headers:
            try:
                s3_res.meta.client.download_file(bucket_for_snapshot, bucket_key + "/src/manifest.csv", manifest_dir + "manifest.csv")
            except Exception as e:
                print(e)
                snap_del = True
            else:
                df = pd.read_csv(manifest_dir + 'manifest.csv', index_col=0, dtype='category')
                snap_ids = df.columns.values.tolist()
                snap = SnapshotModel.find_by_snapshot(site_id, snap_ids[-1])
                snd_last_snap = SnapshotModel.find_by_snapshot(site_id, snap_ids[-2])
                if snap['last_snap'] != 1 and snap_ids[-2] == "name":
                    snap_del = True
                elif snap['last_snap'] != 1 and snd_last_snap == 1:
                    snap_del = True


        if snapshot['last_snap'] == "1" or 'snap-cleanup' in request.headers or 'snapshot_failed' in snapshot['snapshot_status'] or ('snap_del' in locals() and snap_del == True):
            print("cleanup process")
            Snapshot.table.delete_item(
                Key = {
                    'site_id' : snapshot['site_id'],
                    'snapshot_id': snapshot['snapshot_id']
                }
            )

            src_snap_key = bucket_key + "/src/"
            check_content = s3_client.list_objects(Bucket=bucket_for_snapshot, Prefix=src_snap_key)
            if check_content.get('Contents'):
                for key in s3_client.list_objects(Bucket=bucket_for_snapshot, Prefix=src_snap_key)['Contents']:
                    file_name = key['Key'].split("/")[-1]
                    key_del.append(key['Key'])

            db_snap_key = bucket_key + "/db/"
            check_content = s3_client.list_objects(Bucket=bucket_for_snapshot, Prefix=db_snap_key)
            if check_content.get('Contents'):
                for key in s3_client.list_objects(Bucket=bucket_for_snapshot, Prefix=db_snap_key)['Contents']:
                    file_name = key['Key'].split("/")[-1]
                    key_del.append(key['Key'])

            print("#### files going to cleanup #### ")
            print(key_del)
            if key_del:
                for key in key_del:
                    s3_res.Object(bucket_for_snapshot, key).delete()

            if 'second_last_snapshot' not in locals() or 'snap-cleanup' in request.headers:
                data_wpmudev = {'domain': site_name_ping, 'last_backup_time': int(0)}
            else:
                data_wpmudev = {'domain': site_name_ping, 'last_backup_time': unix_timestamp}

            print(data_wpmudev)

            res = Snapshot.ping_dev_site(request.headers['Snapshot-APIKey'], data_wpmudev)
            print(f"dev site ping response > {res.content}")

            print("#################### snapshot delete request ended ########################")
            return {'message': "Snapshot deleted"}
        else:
            return{'error': "cannot delete other than latest backup"}, 400

    def put(self, site_id, snapshot_id):
        data = Snapshot.parser.parse_args()
        try:
            res = Snapshot.update_snapshot(site_id, snapshot_id, data)
        except:
            return {'message': "An error occurred updating the snapshot"}, 500

        if not res:
            return {'message': "snapshot for '{}' not exists".format(site_id)}, 404
        return res, 200

    def update_snapshot(site_id, snapshot_id, data):
        snapshot = SnapshotModel.find_by_snapshot(site_id, snapshot_id)
        utc_time = datetime.datetime.utcnow()       
        
        updated_snapshot = SnapshotModel(site_id, snapshot_id, data['schedule_id'], data['user_id'], data['bu_snapshot_name'], data['created_at'], data['snapshot_status'], data['last_snap'], data['bu_frequency'], data['site_name'], data['excluded_files'], data['snapshot_size'], data['bu_region'], data['plugin_v'], data['is_automate'], data['tpd_exp_status'], data['tpd_exp_done'])
        
        if snapshot:
            try:
                response = updated_snapshot.update(snapshot)
                return data
            except Exception as e:
                log.error(f"Error updating snapshot: { e } ({ snapshot })")
                raise e
        return None

    @classmethod
    def ping_dev_site(self, api_key, data_wpmudev):
        url = os.environ["WPMUDEV_CUSTOM_API_SERVER"] + "/snapshot/v2/site/settings"
        headers = {
            'Authorization': api_key,
            'User-Agent': "Snapshot Serverless API/1.0",
            'Accept': "*/*",
            'Host': os.environ["WPMUDEV_CUSTOM_API_SERVER"].split('/')[2],
            'Accept-Encoding': "gzip, deflate",   'Connection': "keep-alive"
        }
        response = requests.post(url, headers=headers, params=data_wpmudev)
        if response.status_code != 200:
            print(f"error to pring dev site > {response.content}")
        else:
            return response


class Snapshotlist(Resource):
    def get(self, site_id, schedule_id):
        response = Snapshot.table.query(
            IndexName='site_sch_id-index',
            KeyConditionExpression= "site_id= :site_id and schedule_id= :sch_id",
            ExpressionAttributeValues= {
                ":site_id":site_id,
                ":sch_id":schedule_id
                }
            )
        if response['Items']:
            for x in response['Items']:
                # del x['user_id']
                del x['schedule_id']
                del x['site_id']
            return response['Items']

    def delete(self, site_id):
        
        response = Snapshot.table.query(
            KeyConditionExpression= Key('site_id').eq(site_id)
            )

        s3_client = boto3.client('s3')
        s3_res = boto3.resource('s3')
        
        if response['Items']:
            for snapshot in response['Items']:
                print("snapshot id >>> ")
                print(snapshot['snapshot_id'])
                Snapshot.table.delete_item(
                    Key = {
                        'site_id' : snapshot['site_id'],
                        'snapshot_id': snapshot['snapshot_id']
                    }
                )

                key_del = []
                # time.sleep(3)

                site_name_ping = snapshot['site_name']
                if "/" in snapshot['site_name']:
                    snapshot['site_name'] = snapshot['site_name'].split("/")[0] + "-" + snapshot['site_name'].split("/")[1]
                    print("sub site > " + str(snapshot['site_name']))
            
                pre_created_date = snapshot['created_at'].split(" ")
                pre_time = pre_created_date[1].split(":")
                bucket_key = snapshot['user_id'] + "/" + snapshot['site_id'] + "/" + snapshot['site_name']+ "/" + pre_created_date[0] + "/" + pre_time[0] + "-" + pre_time[1]
                if snapshot['bu_region'] == "US":
                    bucket_for_snapshot = os.environ["BUCKET_FOR_SNAPS"]
                else:
                    bucket_for_snapshot = os.environ["BUCKET_FOR_SNAPS_EU"]

                src_snap_key = bucket_key + "/src/"
                print(bucket_for_snapshot)
                print(src_snap_key)
                print(s3_client.list_objects(Bucket=bucket_for_snapshot, Prefix=src_snap_key))
                check_content = s3_client.list_objects(Bucket=bucket_for_snapshot, Prefix=src_snap_key)
                if check_content.get('Contents'):
                    for key in s3_client.list_objects(Bucket=bucket_for_snapshot, Prefix=src_snap_key)['Contents']:
                        file_name = key['Key'].split("/")[-1]
                        key_del.append(key['Key'])


                db_snap_key = bucket_key + "/db/"
                check_content = s3_client.list_objects(Bucket=bucket_for_snapshot, Prefix=db_snap_key)
                if check_content.get('Contents'):
                    for key in s3_client.list_objects(Bucket=bucket_for_snapshot, Prefix=db_snap_key)['Contents']:
                        file_name = key['Key'].split("/")[-1]
                        key_del.append(key['Key'])

                print("#### files going to cleanup #### ")
                print(key_del)

                if key_del:
                    for key in key_del:
                        s3_res.Object(bucket_for_snapshot, key).delete()

            data_wpmudev = {'domain': site_name_ping, 'last_backup_time': int(0)}
            res = Snapshot.ping_dev_site(request.headers['Snapshot-APIKey'], data_wpmudev)
            print(f"dev site ping response > {res.content}")

            return {'message': "all snapshots deleted for site id '{}' ".format(site_id)}, 200
        return {'message': "site id '{}' have no snapshot ".format(site_id)}, 404
                

class SnapshotLsSid(Resource):
    def get(self, site_id):
        response = SnapshotModel.table.query(
            KeyConditionExpression=Key('site_id').eq(site_id)
            )
        if response['Items']:
            for x in response['Items']:
                print("snapshot id > " + str(x['snapshot_id']) + " schedule id > " + str(x['schedule_id']))
                # del x['user_id']
                if x['excluded_files'] != None:
                    print(x['excluded_files'].replace('\'',''))
                    x['excluded_files'] = x['excluded_files'].replace('\'','')
            return response['Items']
        return {'message': "snapshot not found for site id {}".format(site_id)}

class SnapshotLsLS(Resource):
    def get(self, site_id):
        res = SnapshotLsLS.get_by_site_id(site_id)
        if not res:
            return {'message': "no snapshot"}, 404
        return res

    def get_by_site_id(site_id):
        response = Snapshot.table.query(
            IndexName='siteid_lastsnap-index',
            KeyConditionExpression= "site_id= :site_id and last_snap = :last_s",
            ExpressionAttributeValues= {
                ":site_id":site_id,
                ":last_s":"1"
                }
            )
        if response['Items']:
            return response['Items']        
        return None

class SnapshotBySchedule(Resource):
    def get(self, schedule_id, created_at):
        response = Snapshot.table.query(
            IndexName='sch_id-created_at-index',
            KeyConditionExpression= Key('schedule_id').eq(schedule_id) & Key('created_at').begins_with(created_at)
        )
        if response['Items']:
            return response['Items']        
        return {'message': "no snapshot"}, 404

class SnapshotLsSidCr(Resource):
    RESP_SNAPSHOT_RUNNING = "another backup running"
    RESP_NO_SNAPSHOT = "no snapshot"

    def get(self, site_id, created_at):
        res = SnapshotLsSidCr.get_by_site_id_and_date(site_id, created_at)
        if not res or res == SnapshotLsSidCr.RESP_NO_SNAPSHOT:
            return {'message': "no snapshot"}, 404
        if res == SnapshotLsSidCr.RESP_SNAPSHOT_RUNNING:
            return {'message': "another backup running"}, 400
        return res

    def get_by_site_id_and_date(site_id, created_at):
        response = Snapshot.table.query(
            IndexName='site_id-created_at-index',
            KeyConditionExpression= "site_id= :site_id and created_at <= :cr_at",
            Limit= 1,
            ScanIndexForward= False,    
            ExpressionAttributeValues= {
                ":site_id":site_id,
                ":cr_at":created_at
                }
            )
        print(response['Items'])
        print((datetime.datetime.utcnow() - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"))
        if response['Items']:
            print(response['Items'][0]['created_at'])
            if "snapshot_failed" in response['Items'][0]['snapshot_status'] or response['Items'][0]['snapshot_status'] == "snapshot_completed" or (datetime.datetime.utcnow() - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S") > response['Items'][0]['created_at']:
                return response['Items']
            return SnapshotLsSidCr.RESP_SNAPSHOT_RUNNING
        return SnapshotLsSidCr.RESP_NO_SNAPSHOT

class SnapshotLsUserid(Resource):
    def get(self, user_id):
        snapshots = SnapshotModel.snapshot_by_user(user_id)

        if snapshots:
            return snapshots
        return {'message':'Snapshot not found'}, 404



