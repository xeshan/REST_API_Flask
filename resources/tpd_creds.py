from db import dynamodb
from boto3.dynamodb.conditions import Key, Attr
from flask_restful import Resource, reqparse, request
import uuid
from time import strftime
import datetime
from models.tpd_creds import TpdCredsModel
import os
import requests
import json
import boto3
from botocore.exceptions import ClientError
import uuid

class TpdCreds(Resource):

    parser = reqparse.RequestParser()

    for args in ['aws_storage','tpd_accesskey','tpd_secretkey', 'tpd_region', 'tpd_path', 'tpd_name', 'tpd_limit', 'tpd_save', 'tpd_type', 'tpd_acctoken_gdrive', 'tpd_retoken_gdrive', 'domfolder_gdrive', 'tpd_email_gdrive']:
        parser.add_argument(args)


    table = dynamodb.Table('tpd_creds')
    
    def get(self, site_id):
        creds = TpdCredsModel.find_by_siteid(site_id)

        if creds:
            return creds
        return {'message':'creds not found'}, 404
            
    def post(self, site_id):
        data = TpdCreds.parser.parse_args()
        print("data received")
        print(data)
        if not data['tpd_limit'] or not data['tpd_save']:
            return {'Message': 'tpd_limit and tpd_save cant blank'}, 400

        if data['tpd_type'] == 'gdrive' and not data['tpd_retoken_gdrive']:
            return {'Message': 'tpd_retoken_gdrive cant blank'}, 400

        tpd_id = str(uuid.uuid4())[:13]

        creds = TpdCredsModel.find_by_siteid(site_id)
        if creds:
            for cr in creds:
                if data['tpd_type'] == 'gdrive':
                    if cr['tpd_path'] == data['tpd_path']:
                        return {"Message": "Same destination already exists"}, 400
                else:
                    if cr['tpd_path'] == data['tpd_path'] and data['tpd_accesskey'] == cr['tpd_accesskey']:
                        return {"Message": "Same destination already exists"}, 400

        try:
            if data['tpd_type'] == 'aws':
                s3_creds = boto3.client('s3', aws_access_key_id=data['tpd_accesskey'], aws_secret_access_key=data['tpd_secretkey'])
            elif data['tpd_type'] == 'wasabi':
                if data['tpd_region'] == 'us-east-1':
                    endpoint_url = 'https://s3.wasabisys.com'
                else:
                    endpoint_url = 'https://s3.' + data['tpd_region'] + '.wasabisys.com' 
                s3_creds = boto3.client('s3', endpoint_url = endpoint_url, aws_access_key_id=data['tpd_accesskey'], aws_secret_access_key=data['tpd_secretkey'], region_name=data['tpd_region'])
            elif data['tpd_type'] == 'backblaze':
                endpoint_url = 'https://s3.' + data['tpd_region'] + '.backblazeb2.com'
                s3_creds = boto3.client('s3', endpoint_url = endpoint_url, aws_access_key_id=data['tpd_accesskey'], aws_secret_access_key=data['tpd_secretkey'])
            elif data['tpd_type'] == 'digitalocean':
                endpoint_url = 'https://' + data['tpd_region'] + '.digitaloceanspaces.com'
                s3_creds = boto3.client('s3', endpoint_url = endpoint_url, aws_access_key_id=data['tpd_accesskey'], aws_secret_access_key=data['tpd_secretkey'])
            elif data['tpd_type'] == 'googlecloud':
                endpoint_url = 'https://storage.googleapis.com'
                s3_creds = boto3.client('s3', endpoint_url = endpoint_url, aws_access_key_id=data['tpd_accesskey'], aws_secret_access_key=data['tpd_secretkey'])
            elif data['tpd_type'] == 's3_other':
                endpoint_url = data['tpd_region']
                try:
                    if "-" in endpoint_url.split(".")[1]:
                        tpd_region_name =  endpoint_url.split(".")[1]
                    else:
                        tpd_region_name = 'us-east-1'

                    if 'wasabisys' in endpoint_url:
                        s3_creds = boto3.client('s3', endpoint_url = endpoint_url, aws_access_key_id=data['tpd_accesskey'], aws_secret_access_key=data['tpd_secretkey'], region_name=tpd_region_name)
                    else:
                        s3_creds = boto3.client('s3', endpoint_url = endpoint_url, aws_access_key_id=data['tpd_accesskey'], aws_secret_access_key=data['tpd_secretkey'])                    
                except Exception as e:
                    print(e)
                    raise Exception

            if data['tpd_type'] != 'gdrive':
                bucket_list = s3_creds.list_buckets()
                print(bucket_list)
        except ClientError as e:
            print(e)
            return {'Error': 'AWS credentials are not valid'}, 401
        except Exception as e:
            print(e)
            return {'Error': 'something wrong with AWS credentials'}, 401
        else:
            if data['tpd_save'] and data['tpd_save'] == "0":
                if data['tpd_type'] != 'gdrive':
                    bucket_lists=[]
                    if data['tpd_region'] == "us-east-1" or 'tpd_region_name' in locals() and tpd_region_name == "us-east-1":
                        bucket_flag = None
                    else:
                        if data['tpd_type'] == "s3_other":
                            bucket_flag = tpd_region_name
                        else:
                            bucket_flag = data['tpd_region']

                    for bucket in bucket_list['Buckets']:
                        if s3_creds.get_bucket_location(Bucket=bucket['Name'])['LocationConstraint'] and data['tpd_type'] == "googlecloud":
                            bucket_location = s3_creds.get_bucket_location(Bucket=bucket['Name'])['LocationConstraint'].lower()
                        else:
                            bucket_location = s3_creds.get_bucket_location(Bucket=bucket['Name'])['LocationConstraint']

                        if bucket_location == bucket_flag:
                        # print(bucket['Name'])
                            bucket_lists.append(bucket['Name']) 
                    return bucket_lists, 200                    
                elif data['tpd_type'] == 'gdrive': 
                    res = ValidateRefreshToken.velidate_token(data['tpd_acctoken_gdrive'])
                    # print(res)
                    if res.status_code != 200:
                        return {'Error': 'Invalid access token'}, 401
                    else:
                        print("gdive drive validation")
                        headers_gdrive = {"Authorization": "Bearer " + str(data['tpd_acctoken_gdrive'])}
                        print(headers_gdrive)
                        param = {"q":"'%s' in parents" %data['tpd_path'], "supportsAllDrives":"true"}
                        gapi_url = "https://www.googleapis.com/drive/v2/files"   
                        gres = requests.get(url=gapi_url, params= param, headers=headers_gdrive)
                        print(gres.status_code)
                        if gres.status_code != 200:
                            return {'Error': 'Invalid drive id'}, 400
                        else:
                            return {'Error': 'Access token and drive id is valid'}, 200             
            elif data['tpd_type'] == 'gdrive' and data['tpd_acctoken_gdrive']:
                res = ValidateRefreshToken.velidate_token(data['tpd_acctoken_gdrive'])
                # print(res)
                if res.status_code != 200:
                    return {'Error': 'Invalid access token'}, 401
                else:
                    print("gdive drive validation")
                    headers_gdrive = {"Authorization": "Bearer " + str(data['tpd_acctoken_gdrive'])}
                    print(headers_gdrive)
                    param = {"q":"'%s' in parents" %data['tpd_path'], "supportsAllDrives":"true"}
                    gapi_url = "https://www.googleapis.com/drive/v2/files"   
                    gres = requests.get(url=gapi_url, params= param, headers=headers_gdrive)
                    print(gres.status_code)
                    print(json.loads(gres.content))
                    if gres.status_code != 200:
                        return {'Error': 'Invalid drive id'}, 400
        try:
            data['created_at'] = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            creds = TpdCredsModel(tpd_id, site_id, data['created_at'], data['aws_storage'], data['tpd_accesskey'], data['tpd_secretkey'], data['tpd_region'], data['tpd_path'], data['tpd_name'], data['tpd_limit'], data['tpd_type'], data['tpd_acctoken_gdrive'], data['tpd_retoken_gdrive'], data['domfolder_gdrive'], data['tpd_email_gdrive'])
            creds.insert()
        except Exception as e:
            print(e)
            return {"Message": "An error occured inserting creds"}, 500
        return creds.json(), 201

    def put(self, site_id, tpd_id):
        CLIENT_ID = os.environ["GDRIVE_CLIENT_ID"]
        CLIENT_SECRET = os.environ["GDRIVE_CLIENT_SECRET"]

        creds = TpdCredsModel.find_by_tpdid(site_id, tpd_id)
        print("creds are >>>")
        print(creds)
        data = TpdCreds.parser.parse_args()
        print("data received")
        print(data)

        if creds[0]['tpd_type'] != 'gdrive':
            if data['tpd_accesskey'] != creds[0]['tpd_accesskey'] or creds[0]['tpd_path'] != data['tpd_path']:
                tpd_dest_validation = True
        else:
            if creds[0]['tpd_path'] != data['tpd_path']:
                tpd_dest_validation = True  

        if 'tpd_dest_validation' in locals() and tpd_dest_validation == True:
            cre = TpdCredsModel.find_by_siteid(site_id)
            if cre:
                for cr in cre:
                    if data['tpd_type'] == 'gdrive':
                        if cr['tpd_path'] == data['tpd_path']:
                            return {"Message": "Same destination already exists"}, 400
                    else:
                        if cr['tpd_path'] == data['tpd_path'] and data['tpd_accesskey'] == cr['tpd_accesskey']:
                            return {"Message": "Same destination already exists"}, 400

        if data['aws_storage'] == None:
            data['aws_storage'] = creds[0]['aws_storage']
        if data['tpd_secretkey'] == None:
            data['tpd_secretkey'] = creds[0]['tpd_secretkey']
        if data['tpd_region'] == None:
            data['tpd_region'] = creds[0]['tpd_region']     
        if data['tpd_path'] == None:
            data['tpd_path'] = creds[0]['tpd_path']
        if data['tpd_limit'] == None:
            data['tpd_limit'] = creds[0]['tpd_limit']
        if data['tpd_name'] == None:
            data['tpd_name'] = creds[0]['tpd_name']

        if creds[0]['tpd_type'] == 'gdrive':
            if 'tpd_acctoken_gdrive' not in creds[0] or data['tpd_acctoken_gdrive'] == None:
                data['tpd_acctoken_gdrive'] = creds[0]['tpd_acctoken_gdrive']

            if 'tpd_retoken_gdrive' not in creds[0] or data['tpd_retoken_gdrive'] == None:
                data['tpd_retoken_gdrive'] = creds[0]['tpd_retoken_gdrive']

            if 'domfolder_gdrive' not in creds[0] or data['domfolder_gdrive'] == None:
                data['domfolder_gdrive'] = creds[0]['domfolder_gdrive']

            if 'tpd_email_gdrive' not in creds[0] or data['tpd_email_gdrive'] == None:
                data['tpd_email_gdrive'] = creds[0]['tpd_email_gdrive']

        else:
            data['tpd_acctoken_gdrive'] = None
            data['tpd_retoken_gdrive'] = None
            data['domfolder_gdrive'] = None
            data['tpd_email_gdrive'] = None

        data['tpd_type'] = creds[0]['tpd_type']
        if 'tpd_accesskey' not in data.keys():
            data['tpd_accesskey'] = creds[0]['tpd_accesskey']

        print("data after all checks")
        print(data)

        if data['tpd_type'] == 'aws':
            s3_creds = boto3.client('s3', aws_access_key_id=data['tpd_accesskey'], aws_secret_access_key=data['tpd_secretkey'])
        elif data['tpd_type'] == 'wasabi':
            if data['tpd_region'] == 'us-east-1':
                endpoint_url = 'https://s3.wasabisys.com'
            else:
                endpoint_url = 'https://s3.' + data['tpd_region'] + '.wasabisys.com' 
            s3_creds = boto3.client('s3', endpoint_url = endpoint_url, aws_access_key_id=data['tpd_accesskey'], aws_secret_access_key=data['tpd_secretkey'], region_name=data['tpd_region'])
        elif data['tpd_type'] == 'backblaze':
            endpoint_url = 'https://s3.' + data['tpd_region'] + '.backblazeb2.com'
            s3_creds = boto3.client('s3', endpoint_url = endpoint_url, aws_access_key_id=data['tpd_accesskey'], aws_secret_access_key=data['tpd_secretkey'])
        elif data['tpd_type'] == 'digitalocean':
            endpoint_url = 'https://' + data['tpd_region'] + '.digitaloceanspaces.com'
            s3_creds = boto3.client('s3', endpoint_url = endpoint_url, aws_access_key_id=data['tpd_accesskey'], aws_secret_access_key=data['tpd_secretkey'])
        elif data['tpd_type'] == 'googlecloud':
            endpoint_url = 'https://storage.googleapis.com'
            s3_creds = boto3.client('s3', endpoint_url = endpoint_url, aws_access_key_id=data['tpd_accesskey'], aws_secret_access_key=data['tpd_secretkey'])
        elif data['tpd_type'] == 's3_other':
            endpoint_url = data['tpd_region'] 
            if "-" in endpoint_url.split(".")[1]:
                tpd_region_name =  endpoint_url.split(".")[1]
            else:
                tpd_region_name = 'us-east-1'

            if 'wasabisys' in endpoint_url:
                s3_creds = boto3.client('s3', endpoint_url = endpoint_url, aws_access_key_id=data['tpd_accesskey'], aws_secret_access_key=data['tpd_secretkey'], region_name=tpd_region_name)
            else:
                s3_creds = boto3.client('s3', endpoint_url = endpoint_url, aws_access_key_id=data['tpd_accesskey'], aws_secret_access_key=data['tpd_secretkey'])
            
        # s3_creds = boto3.client('s3', aws_access_key_id=creds[0]['tpd_accesskey'], aws_secret_access_key=data['tpd_secretkey'])
        if data['tpd_type'] != 'gdrive':
            try:
                bucket_list = s3_creds.list_buckets()
            except ClientError as e:
                print(e)
                return {'Error': f"{data['tpd_type']} credentials are not valid"}, 401
            except Exception as e:
                print(e)
                return {'Error': f"something wrong with {data['tpd_type']} credentials"}, 401
            else:
                bucket_lists=[]
                if data['tpd_region'] == "us-east-1" or 'tpd_region_name' in locals() and tpd_region_name == "us-east-1":
                    bucket_flag = None
                else:
                    if data['tpd_type'] == "s3_other":
                        bucket_flag = tpd_region_name
                    else:
                        bucket_flag = data['tpd_region']

                for bucket in bucket_list['Buckets']:
                    if s3_creds.get_bucket_location(Bucket=bucket['Name'])['LocationConstraint'] and data['tpd_type'] == "googlecloud":
                        bucket_location = s3_creds.get_bucket_location(Bucket=bucket['Name'])['LocationConstraint'].lower()
                    else:
                        bucket_location = s3_creds.get_bucket_location(Bucket=bucket['Name'])['LocationConstraint']

                    if bucket_location == bucket_flag:
                    # print(bucket['Name'])
                        bucket_lists.append(bucket['Name'])                     
                if not bucket_lists:
                    return {'Error': 'no bucket found for selected region'}, 404
        elif data['tpd_type'] == 'gdrive': 
            res = ValidateRefreshToken.velidate_token(data['tpd_acctoken_gdrive'])
            # print(res)

            if res.status_code != 200:
                print("token expired")
                data['tpd_acctoken_gdrive'] = ValidateRefreshToken.refresh_token(CLIENT_ID, CLIENT_SECRET, data['tpd_retoken_gdrive'])
                # return {'Error': 'Invalid access token'}, 401

            print("gdive drive validation")
            headers_gdrive = {"Authorization": "Bearer " + str(data['tpd_acctoken_gdrive'])}
            print(headers_gdrive)
            param = {"q":"'%s' in parents" %data['tpd_path'], "supportsAllDrives":"true"}
            gapi_url = "https://www.googleapis.com/drive/v2/files"   
            gres = requests.get(url=gapi_url, params= param, headers=headers_gdrive)
            print(gres.status_code)
            if gres.status_code != 200:
                return {'Error': 'Invalid drive id'}, 400
            if gres.status_code == 200 and data['tpd_path'] != creds[0]['tpd_path']:
                data['domfolder_gdrive'] = None

        # utc_time = datetime.datetime.utcnow()     

        updated_creds = TpdCredsModel(tpd_id, site_id, creds[0]['created_at'], data['aws_storage'], data['tpd_accesskey'], data['tpd_secretkey'], data['tpd_region'], data['tpd_path'], data['tpd_name'], data['tpd_limit'], data['tpd_type'], data['tpd_acctoken_gdrive'], data['tpd_retoken_gdrive'], data['domfolder_gdrive'], data['tpd_email_gdrive'])
        response = updated_creds.update(creds[0])
        if creds:
            try:
                response = updated_creds.update(creds[0])
                print(f"creds update response > {response}")
                return data, 200
            except:
                return {'message': "An error occurred updating the credentials"}, 500

        return {'message': "credentials for '{}' not exists".format(site_id)}, 404

    def delete(self, site_id, tpd_id):
        creds = TpdCredsModel.find_by_tpdid(site_id, tpd_id)
        print(creds)
        if creds:
            TpdCreds.table.delete_item(
                Key = {
                    'site_id' : site_id,
                    'created_at': creds[0]['created_at']
                }
            )
            return "credentials deleted", 200
        else:
            return "credentials not found", 404


class CredsAuthchk(Resource):

    def post(self, site_id):
        data = TpdBucketList.parser.parse_args()
        print("data received")
        print(data)
        if data['tpd_type'] == 'aws':
            s3_creds = boto3.client('s3', aws_access_key_id=data['tpd_accesskey'], aws_secret_access_key=data['tpd_secretkey'])
        elif data['tpd_type'] == 'wasabi':
            if data['tpd_region'] == 'us-east-1':
                endpoint_url = 'https://s3.wasabisys.com'
            else:
                endpoint_url = 'https://s3.' + data['tpd_region'] + '.wasabisys.com' 
            s3_creds = boto3.client('s3', endpoint_url = endpoint_url, aws_access_key_id=data['tpd_accesskey'], aws_secret_access_key=data['tpd_secretkey'], region_name=data['tpd_region'])
        elif data['tpd_type'] == 'backblaze':
            endpoint_url = 'https://s3.' + data['tpd_region'] + '.backblazeb2.com'
            s3_creds = boto3.client('s3', endpoint_url = endpoint_url, aws_access_key_id=data['tpd_accesskey'], aws_secret_access_key=data['tpd_secretkey'])
        elif data['tpd_type'] == 'digitalocean':
            endpoint_url = 'https://' + data['tpd_region'] + '.digitaloceanspaces.com'
            s3_creds = boto3.client('s3', endpoint_url = endpoint_url, aws_access_key_id=data['tpd_accesskey'], aws_secret_access_key=data['tpd_secretkey'])
        elif data['tpd_type'] == 'googlecloud':
            endpoint_url = 'https://storage.googleapis.com'
            s3_creds = boto3.client('s3', endpoint_url = endpoint_url, aws_access_key_id=data['tpd_accesskey'], aws_secret_access_key=data['tpd_secretkey'])
        elif data['tpd_type'] == 's3_other':
            endpoint_url = data['tpd_region']
            try:
                if "-" in endpoint_url.split(".")[1]:
                    tpd_region_name =  endpoint_url.split(".")[1]
                else:
                    tpd_region_name = 'us-east-1'

                if 'wasabisys' in endpoint_url:
                    s3_creds = boto3.client('s3', endpoint_url = endpoint_url, aws_access_key_id=data['tpd_accesskey'], aws_secret_access_key=data['tpd_secretkey'], region_name=tpd_region_name)
                else:
                    s3_creds = boto3.client('s3', endpoint_url = endpoint_url, aws_access_key_id=data['tpd_accesskey'], aws_secret_access_key=data['tpd_secretkey'])                    
            except Exception as e:
                print(e)

        # s3_creds = boto3.client('s3', aws_access_key_id=data['tpd_accesskey'], aws_secret_access_key=data['tpd_secretkey'])
        try:
            bucket_list = s3_creds.list_buckets()
        except ClientError as e:
            print(e)
            return {'Error': f"{data['tpd_type']} credentials are not valid"}, 401
        except Exception as e:
            print(e)
            return {'Error': f"something wrong with {data['tpd_type']} credentials"}, 401
        else:
            return {'Message': f"{data['tpd_type']} valid credentials"}, 200

class TpdBucketList(Resource):

    parser = reqparse.RequestParser()

    for args in ['aws_storage','tpd_accesskey','tpd_secretkey', 'tpd_region', 'tpd_path', 'tpd_name', 'tpd_limit', 'tpd_save', 'tpd_type']:
        parser.add_argument(args)


    def post(self, site_id):
        data = TpdBucketList.parser.parse_args()
        print("data received")
        print(data)     

        if data['tpd_type'] == 'aws':
            s3_creds = boto3.client('s3', aws_access_key_id=data['tpd_accesskey'], aws_secret_access_key=data['tpd_secretkey'])
        elif data['tpd_type'] == 'wasabi':
            if data['tpd_region'] == 'us-east-1':
                endpoint_url = 'https://s3.wasabisys.com'
            else:
                endpoint_url = 'https://s3.' + data['tpd_region'] + '.wasabisys.com'
            s3_creds = boto3.client('s3', endpoint_url = endpoint_url, aws_access_key_id=data['tpd_accesskey'], aws_secret_access_key=data['tpd_secretkey'], region_name=data['tpd_region'])
        elif data['tpd_type'] == 'backblaze':
            endpoint_url = 'https://s3.' + data['tpd_region'] + '.backblazeb2.com'
            s3_creds = boto3.client('s3', endpoint_url = endpoint_url, aws_access_key_id=data['tpd_accesskey'], aws_secret_access_key=data['tpd_secretkey'])
        elif data['tpd_type'] == 'digitalocean':
            endpoint_url = 'https://' + data['tpd_region'] + '.digitaloceanspaces.com'
            s3_creds = boto3.client('s3', endpoint_url = endpoint_url, aws_access_key_id=data['tpd_accesskey'], aws_secret_access_key=data['tpd_secretkey'])
        elif data['tpd_type'] == 'googlecloud':
            endpoint_url = 'https://storage.googleapis.com'
            s3_creds = boto3.client('s3', endpoint_url = endpoint_url, aws_access_key_id=data['tpd_accesskey'], aws_secret_access_key=data['tpd_secretkey'])
        elif data['tpd_type'] == 's3_other':
            print("s3 other called")
            endpoint_url = data['tpd_region']
            try:
                # s3_creds = boto3.client('s3', endpoint_url = endpoint_url, aws_access_key_id=data['tpd_accesskey'], aws_secret_access_key=data['tpd_secretkey'])
                # print("2nd try block")
                if "-" in endpoint_url.split(".")[1]:
                    tpd_region_name =  endpoint_url.split(".")[1]
                else:
                    tpd_region_name = 'us-east-1'

                if 'wasabisys' in endpoint_url:
                    s3_creds = boto3.client('s3', endpoint_url = endpoint_url, aws_access_key_id=data['tpd_accesskey'], aws_secret_access_key=data['tpd_secretkey'], region_name=tpd_region_name)
                else:
                    s3_creds = boto3.client('s3', endpoint_url = endpoint_url, aws_access_key_id=data['tpd_accesskey'], aws_secret_access_key=data['tpd_secretkey'])                    
            except Exception as e:
                print(e)
                return {'Error': f"something wrong with {data['tpd_type']} credentials"}, 400
        try:
            bucket_list = s3_creds.list_buckets()
        except ClientError as e:
            print(e)
            return {'Error': f"{data['tpd_type']} credentials are not valid"}, 400
        except Exception as e:
            print(e)    
            return {'Error': f"something wrong with {data['tpd_type']} credentials"}, 400
        else:
            bucket_lists=[]
            if data['tpd_region'] == "us-east-1" or 'tpd_region_name' in locals() and tpd_region_name == "us-east-1":
                bucket_flag = None
            else:
                if data['tpd_type'] == "s3_other":
                    bucket_flag = tpd_region_name
                else:
                    bucket_flag = data['tpd_region']

            for bucket in bucket_list['Buckets']:
                if s3_creds.get_bucket_location(Bucket=bucket['Name'])['LocationConstraint'] and data['tpd_type'] == "googlecloud":
                    bucket_location = s3_creds.get_bucket_location(Bucket=bucket['Name'])['LocationConstraint'].lower()
                else:
                    bucket_location = s3_creds.get_bucket_location(Bucket=bucket['Name'])['LocationConstraint']


                if bucket_location == bucket_flag:
                # print(bucket['Name'])
                    bucket_lists.append(bucket['Name']) 
            return bucket_lists, 200


class TpdActiveList(Resource):
    def get(self, site_id):
        res = TpdActiveList.get_by_site_id(site_id)
        if not res:
            return {'message':'creds not found'}, 404
        return res

    def get_by_site_id(site_id):
        creds = TpdCredsModel.find_by_tpdactive(site_id)
        print(creds)
        creds_ls ={}
        tpd_gdrive = {}
        tpd_s3 = {}
        if creds:
            for x in creds:
                if x['tpd_type'] == 'gdrive':
                    tpd_gdrive[x['tpd_name']] = "null"
                else:
                    tpd_s3[x['tpd_name']] = "null"
                
            creds_ls['tpd_gdrive'] =  tpd_gdrive
            creds_ls['tpd_s3'] = tpd_s3
            print(creds_ls)

            return creds_ls
        return None

class GenerateToken(Resource):
    parser = reqparse.RequestParser()

    for args in ['tpd_auth_code']:
        parser.add_argument(args)

    def post(self, site_id):
        data = GenerateToken.parser.parse_args()
        print("data received")
        print(data)
        res = GenerateToken.generate_token(data['tpd_auth_code'])
        if res.status_code == 200:
            print(json.loads(res.content)['access_token'])

            authorization_header = {"Authorization": "OAuth %s" % json.loads(res.content)['access_token']}
            req = requests.get("https://www.googleapis.com/oauth2/v2/userinfo", headers=authorization_header)
            print(req.content)

            print(json.loads(req.content)['email'])

            token_data = json.loads(res.content)
            token_data['email'] = json.loads(req.content)['email']
            return token_data, 200
        else:
            return json.loads(res.content), 401             

    @classmethod
    def generate_token(cls, tpd_auth_code):
        code = tpd_auth_code
        CLIENT_ID = os.environ["GDRIVE_CLIENT_ID"]
        CLIENT_SECRET = os.environ["GDRIVE_CLIENT_SECRET"]
        ACCESS_TOKEN_URL = 'https://oauth2.googleapis.com/token'
        REDIRECT_URI = os.environ["GDRIVE_REDIRECT_URI"]
        post_data = {'grant_type': 'authorization_code','code': code,'client_id': CLIENT_ID,'client_secret': CLIENT_SECRET, 'redirect_uri': REDIRECT_URI}
        res = requests.post(ACCESS_TOKEN_URL, data=post_data)
        return res


class ValidateRefreshToken(Resource):
    parser = reqparse.RequestParser()

    for args in ['access_token', 'refresh_token']:
        parser.add_argument(args)

    def post(cls, site_id):
        data = ValidateRefreshToken.parser.parse_args()
        print(data)
        CLIENT_ID = os.environ["GDRIVE_CLIENT_ID"]
        CLIENT_SECRET = os.environ["GDRIVE_CLIENT_SECRET"]

        res = ValidateRefreshToken.velidate_token(data['access_token'])
        # print(res)
        if res.status_code != 200:
            print("token expired")
            data['access_token'] = ValidateRefreshToken.refresh_token(CLIENT_ID, CLIENT_SECRET, data['refresh_token'])

        return data['access_token']


    @classmethod
    def refresh_token(cls, client_id, client_secret, refresh_token):
            params = {
                    "grant_type": "refresh_token",
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "refresh_token": refresh_token
            }

            authorization_url = "https://www.googleapis.com/oauth2/v4/token"
            r = requests.post(authorization_url, data=params)
            if r.ok:
                    return r.json()['access_token']
            else:
                    return None
    
    @classmethod
    def velidate_token(cls, access_token):
        # headers = {"Authorization": "Bearer " + access_token}

        # r = requests.get("https://www.googleapis.com/drive/v3/drives", headers=headers)
        authorization_header = {"Authorization": "OAuth %s" % access_token}
        req = requests.get("https://www.googleapis.com/oauth2/v2/userinfo", headers=authorization_header)

        return req

class TpdList(Resource):

    def delete(self, site_id):      
        creds = TpdCredsModel.find_by_siteid(site_id)
        if creds:
            for cred in creds:
                print(cred)
                TpdCreds.table.delete_item(
                    Key = {
                        'site_id' : site_id,
                        'created_at': cred['created_at']
                    }
                )
            return "all configured TPD deleted", 200
        else:
            return "TPD not found", 404
