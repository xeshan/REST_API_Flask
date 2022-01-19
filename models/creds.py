from db import dynamodb
from boto3.dynamodb.conditions import Key, Attr
from time import strftime
import datetime

class CredsModel:
    def __init__(self, site_id, schedule_id, wpmu_apikey, created_at, bu_region, rotation_frequency):
        self.site_id = site_id
        self.schedule_id = schedule_id
        self.wpmu_apikey = wpmu_apikey
        self.created_at = created_at
        self.bu_region = bu_region
        self.rotation_frequency = rotation_frequency
        
    table = dynamodb.Table('creds')

    def json(self):
        return  {
                'site_id':self.site_id,
                'schedule_id':self.schedule_id,
                'wpmu_apikey':self.wpmu_apikey,
                'created_at':self.created_at,
                'bu_region':self.bu_region,
                'rotation_frequency':self.rotation_frequency
                }

    @classmethod
    def find_by_wpmu_apikey(cls, site_id, wpmu_apikey):
        response = CredsModel.table.query(
            IndexName='sid_apikey-index',
            KeyConditionExpression= "site_id= :site_id and wpmu_apikey= :wpmu_apikey",
            ExpressionAttributeValues= {
                ":site_id":site_id,
                ":wpmu_apikey":wpmu_apikey
                }
            )
        if response['Items']:
            return response['Items']

    @classmethod
    def find_by_siteid_region(cls, site_id):
        response = CredsModel.table.query(
            KeyConditionExpression= "site_id= :site_id",
            ExpressionAttributeValues= {
                ":site_id":site_id
                }
            )
        if response['Items']:
            return response['Items']

    @classmethod
    def find_by_siteid(cls, site_id):
        response = CredsModel.table.query(
            KeyConditionExpression= "site_id= :site_id",
            ExpressionAttributeValues= {
                ":site_id":site_id
                }
            )
        if response['Items']:
            return response['Items']
            
    def insert(self):
        creds = CredsModel.find_by_wpmu_apikey(self.site_id, self.wpmu_apikey)

        if not creds:
            self.table.put_item(
                Item={
                    'site_id' : self.site_id,
                    'schedule_id': self.schedule_id,
                    'wpmu_apikey' : self.wpmu_apikey,
                    'created_at' : self.created_at,
                    'bu_region': self.bu_region,
                    'rotation_frequency': self.rotation_frequency
                })      

    def update(self, creds):
        print(creds)
        self.table.update_item(
            Key = {
            'site_id': creds['site_id'],
            'schedule_id': creds['schedule_id']
            },
            UpdateExpression = 'SET wpmu_apikey = :wpmu_ak, bu_region = :bu_rg, rotation_frequency = :rt_fre',
            ExpressionAttributeValues = {
                ':wpmu_ak': self.wpmu_apikey,
                ':bu_rg': self.bu_region,
                ':rt_fre': self.rotation_frequency
            }
        )       