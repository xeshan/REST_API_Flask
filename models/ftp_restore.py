from db import dynamodb
from boto3.dynamodb.conditions import Key, Attr
from time import strftime
import datetime

class FtpRestoreModel:
    def __init__(self, ftp_id, site_id, created_at, ftp_conntype, ftp_host, ftp_port, ftp_user, ftp_password, ftp_rootdir, is_completed, is_failed, current_stage, progress):
        self.ftp_id = ftp_id
        self.site_id = site_id
        self.ftp_conntype = ftp_conntype
        self.ftp_host = ftp_host
        self.created_at = created_at
        self.ftp_port = ftp_port
        self.ftp_user = ftp_user
        self.ftp_password = ftp_password
        self.ftp_rootdir = ftp_rootdir
        self.is_completed = is_completed
        self.is_failed = is_failed
        self.current_stage = current_stage
        self.progress = progress

    table = dynamodb.Table('ftp_creds')

    def json(self):
        return  {
                'ftp_id': self.ftp_id,
                'site_id': self.site_id,
                'ftp_conntype': self.ftp_conntype,
                'ftp_host': self.ftp_host,
                'ftp_port': self.ftp_port,
                'ftp_user': self.ftp_user,
                'ftp_password': self.ftp_password,
                'ftp_rootdir': self.ftp_rootdir,
                'is_completed': self.is_completed,
                'is_failed': self.is_failed,
                'current_stage': self.current_stage,
                'progress': self.progress
                }

    def insert(self):

        self.table.put_item(
            Item={
                'ftp_id': self.ftp_id,
                'site_id': self.site_id,
                'ftp_conntype': self.ftp_conntype,
                'ftp_host': self.ftp_host,
                'created_at': self.created_at,
                'ftp_port': self.ftp_port,
                'ftp_user' : self.ftp_user,
                'ftp_password' : self.ftp_password,
                'ftp_rootdir': self.ftp_rootdir,
                'is_completed': self.is_completed,
                'is_failed': self.is_failed,
                'current_stage': self.current_stage,
                'progress': self.progress
            })      

    @classmethod
    def find_by_siteid(cls, site_id, ftp_id):
        response = FtpRestoreModel.table.query(
            IndexName='site_id-ftp_id-index',
            KeyConditionExpression= "site_id= :site_id and ftp_id= :ftp_id",
            ExpressionAttributeValues= {
                ":site_id":site_id,
                ":ftp_id":ftp_id
                }
            )
        if response['Items']:
            return response['Items']

class FtpRestoreUpdateModel:
    def __init__(self, ftp_id, site_id, is_completed, is_failed, current_stage, progress):
        self.site_id = site_id
        self.ftp_id = ftp_id
        self.is_completed = is_completed
        self.is_failed = is_failed
        self.current_stage = current_stage
        self.progress = progress

    table = dynamodb.Table('ftp_creds')

    def json(self):
        return  {
                'site_id': self.site_id,
                'ftp_id': self.ftp_id,
                'is_completed': self.is_completed,
                'is_failed': self.is_failed,
                'current_stage': self.current_stage,
                'progress': self.progress
                }

    def update(self, creds):
        print(f"recevied creds > {creds}")
        self.table.update_item(
            Key = {
            'site_id': creds['site_id'],
            'created_at': creds['created_at']
            },
            UpdateExpression = 'SET is_completed = :i_c, is_failed = :i_f, current_stage = :c_s, progress = :prog',
            ExpressionAttributeValues = {
                ':i_c': self.is_completed,
                ':i_f': self.is_failed,
                ':c_s': self.current_stage,
                ':prog': self.progress
            }
        ) 