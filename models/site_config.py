from db import dynamodb
from boto3.dynamodb.conditions import Key, Attr
from time import strftime
import datetime

class SiteConfigModel:
	def __init__(self, con_id, user_id, bu_region, bu_frequency, rotation_frequency, created_at, updated_at, excluded_files, bu_frequency_weekday, bu_frequency_monthday, bu_time):
		self.con_id = con_id
		self.user_id = user_id
		self.bu_region = bu_region
		self.bu_frequency = bu_frequency
		self.rotation_frequency = rotation_frequency
		self.created_at = created_at
		self.updated_at = updated_at
		self.excluded_files = excluded_files
		self.bu_frequency_weekday = bu_frequency_weekday
		self.bu_frequency_monthday = bu_frequency_monthday
		self.bu_time = bu_time
		
	table = dynamodb.Table('s4_config')

	def json(self):
		return	{
				'con_id': self.con_id,
				'user_id': self.user_id,
				'bu_region': self.bu_region,
				'bu_frequency': self.bu_frequency,
				'rotation_frequency': self.rotation_frequency,
				'created_at': self.created_at,
				'updated_at': self.updated_at,
				'excluded_files': self.excluded_files,
				'bu_frequency_weekday': self.bu_frequency_weekday,
				'bu_frequency_monthday': self.bu_frequency_monthday,
				'bu_time': self.bu_time
				}

			
	def insert(self):
		self.table.put_item(
			Item={
				'con_id': self.con_id,
				'user_id': self.user_id,
				'bu_region': self.bu_region,
				'bu_frequency': self.bu_frequency,
				'rotation_frequency': self.rotation_frequency,
				'created_at': self.created_at,
				'updated_at': self.updated_at,
				'excluded_files': self.excluded_files,
				'bu_frequency_weekday': self.bu_frequency_weekday,
				'bu_frequency_monthday': self.bu_frequency_monthday,
				'bu_time': self.bu_time
			})

		
		