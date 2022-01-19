from db import dynamodb
from boto3.dynamodb.conditions import Key, Attr
from flask_restful import Resource, reqparse, request
import uuid
from time import strftime
import datetime
from models.site_config import SiteConfigModel
import os
import requests

from shared import logging
log = logging.Logger('api-siteconfig')

class SiteConfig(Resource):

    parser = reqparse.RequestParser()
    for args in ['user_id', 'bu_region', 'bu_frequency', 'rotation_frequency', 'created_at', 'updated_at', 'excluded_files']:
        parser.add_argument(args,
            required = True,
            help = "'{}' can't blank".format(args)
        )

    for args in ['bu_frequency_weekday', 'bu_frequency_monthday', 'bu_time']:
        parser.add_argument(args)

    table = dynamodb.Table('s4-config')
                
    def post(self, user_id):
        data = SiteConfig.parser.parse_args()
        con_id = str(uuid.uuid4())[:13]
        sconfig = SiteConfigModel(
            con_id,
            data['user_id'],
            data['bu_region'], 
            data['bu_frequency'], 
            data['rotation_frequency'],
            data['created_at'],
            data['updated_at'],
            data['excluded_files'],
            data['bu_frequency_weekday'],
            data['bu_frequency_monthday'],
            data['bu_time']
            )
        log.debug(f"Inserting site config: { sconfig.json() }")
        sconfig.insert()
        try:
            sconfig.insert()
        except:
            return {"message": "An error occured inserting an site config"}, 201
        return sconfig.json(), 201

