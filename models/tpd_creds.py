from db import dynamodb
from boto3.dynamodb.conditions import Key, Attr
from time import strftime
import datetime

class TpdCredsModel:
    def __init__(self, tpd_id, site_id, created_at, aws_storage, tpd_accesskey, tpd_secretkey, tpd_region, tpd_path, tpd_name, tpd_limit, tpd_type, tpd_acctoken_gdrive, tpd_retoken_gdrive, domfolder_gdrive, tpd_email_gdrive):
        self.tpd_id = tpd_id
        self.site_id = site_id
        self.created_at = created_at
        self.aws_storage = aws_storage
        self.tpd_accesskey = tpd_accesskey
        self.tpd_secretkey = tpd_secretkey
        self.tpd_region = tpd_region
        self.tpd_path = tpd_path
        self.tpd_name = tpd_name
        self.tpd_limit = tpd_limit
        self.tpd_type = tpd_type
        self.tpd_acctoken_gdrive = tpd_acctoken_gdrive
        self.tpd_retoken_gdrive = tpd_retoken_gdrive
        self.domfolder_gdrive = domfolder_gdrive
        self.tpd_email_gdrive = tpd_email_gdrive
        
    table = dynamodb.Table('tpd_creds')

    def json(self):
        return  {
                'tpd_id': self.tpd_id,
                'site_id': self.site_id,
                'aws_storage': self.aws_storage,
                'tpd_accesskey': self.tpd_accesskey,
                'tpd_secretkey': self.tpd_secretkey,
                'tpd_region': self.tpd_region,
                'tpd_path': self.tpd_path,
                'tpd_name': self.tpd_name,
                'tpd_limit': self.tpd_limit,
                'tpd_type': self.tpd_type,
                'tpd_acctoken_gdrive': self.tpd_acctoken_gdrive,
                'tpd_retoken_gdrive': self.tpd_retoken_gdrive,
                'domfolder_gdrive': self.domfolder_gdrive,
                'tpd_email_gdrive': self.tpd_email_gdrive
                }

    @classmethod
    def find_by_tpdid(cls, site_id, tpd_id):
        response = TpdCredsModel.table.query(
            IndexName='site_id-tpd_id-index',
            KeyConditionExpression= "site_id= :site_id and tpd_id = :tpd_id",
            ExpressionAttributeValues= {
                ":site_id":site_id,
                ":tpd_id":tpd_id
                }
            )
        if response['Items']:
            return response['Items']



    @classmethod
    def find_by_tpdactive(cls, site_id):
        response = TpdCredsModel.table.query(
            IndexName='site_id-aws_storage-index',
            KeyConditionExpression= "site_id= :site_id and aws_storage = :tpd_status",
            ExpressionAttributeValues= {
                ":site_id":site_id,
                ":tpd_status":"1"
                }
            )
        if response['Items']:
            return response['Items']

    @classmethod
    def find_by_siteid(cls, site_id):
        response = TpdCredsModel.table.query(
            KeyConditionExpression= "site_id= :site_id",
            ExpressionAttributeValues= {
                ":site_id":site_id
                }
            )
        if response['Items']:
            return response['Items']
            
    def insert(self):

        self.table.put_item(
            Item={
                'tpd_id': self.tpd_id,
                'site_id': self.site_id,
                'created_at': self.created_at,
                'aws_storage': self.aws_storage,
                'tpd_accesskey' : self.tpd_accesskey,
                'tpd_secretkey' : self.tpd_secretkey,
                'tpd_region': self.tpd_region,
                'tpd_path': self.tpd_path,
                'tpd_name': self.tpd_name,
                'tpd_limit': self.tpd_limit,
                'tpd_type': self.tpd_type,
                'tpd_acctoken_gdrive': self.tpd_acctoken_gdrive,
                'tpd_retoken_gdrive': self.tpd_retoken_gdrive,
                'domfolder_gdrive': self.domfolder_gdrive,
                'tpd_email_gdrive': self.tpd_email_gdrive
            })      


    def update(self, creds):
        print(creds)
        self.table.update_item(
            Key = {
            'site_id': creds['site_id'],
            'created_at': creds['created_at']
            },
            UpdateExpression = 'SET tpd_secretkey = :t_sk, tpd_region = :t_reg, tpd_path = :t_path, aws_storage = :aws_storage, tpd_limit = :t_lmt, tpd_name = :t_name, tpd_acctoken_gdrive = :t_actoken, tpd_retoken_gdrive = :t_retoken, domfolder_gdrive = :df_gd',
            ExpressionAttributeValues = {
                ':t_sk': self.tpd_secretkey,
                ':t_reg': self.tpd_region,
                ':t_path': self.tpd_path,
                ':aws_storage': self.aws_storage,
                ':t_lmt': self.tpd_limit,
                ':t_name': self.tpd_name,
                ':t_actoken': self.tpd_acctoken_gdrive,
                ':t_retoken': self.tpd_retoken_gdrive,
                ':df_gd': self.domfolder_gdrive
            }
        )       
