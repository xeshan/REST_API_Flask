from db import dynamodb
from boto3.dynamodb.conditions import Key, Attr
from time import strftime
import datetime
import uuid

class ScheduleModel:
	def __init__(self, site_id, schedule_id, site_name, bu_frequency, bu_status, bu_region, bu_time, bu_files, bu_tables, bu_frequency_weekday, bu_frequency_monthday, bu_exclusion_enabled):
		self.site_id = site_id
		self.schedule_id = schedule_id		
		self.site_name = site_name
		self.bu_frequency = bu_frequency
		self.bu_status = bu_status
		self.bu_region = bu_region
		self.bu_time = bu_time
		self.bu_files = bu_files
		self.bu_tables = bu_tables
		self.bu_frequency_weekday = bu_frequency_weekday
		self.bu_frequency_monthday = bu_frequency_monthday 
		self.bu_exclusion_enabled = bu_exclusion_enabled

	table =  dynamodb.Table('schedules')


	def json(self):
			return {
					'site_id':self.site_id,
					'schedule_id':self.schedule_id,
					'site_name':self.site_name, 
					'bu_frequency':self.bu_frequency,
					'bu_status':self.bu_status,
					'bu_region':self.bu_region,
					'bu_time': self.bu_time,
					'bu_files': self.bu_files,
					'bu_tables': self.bu_tables,
					'bu_frequency_weekday': self.bu_frequency_weekday,
					'bu_frequency_monthday': self.bu_frequency_monthday,
					'bu_exclusion_enabled': self.bu_exclusion_enabled
					 }	
	
	@classmethod
	def find_by_name(cls, site_id, schedule_id):
		response =  ScheduleModel.table.get_item(
			Key = {
				'site_id': site_id,
				'schedule_id': schedule_id
			}
		)
		if "Item" in response.keys():
			return response['Item']

	@classmethod
	def find_by_frequency(cls, site_id, bu_frequency):
		response = ScheduleModel.table.query(
			IndexName='bu_frequency-index',
			KeyConditionExpression= "site_id= :site_id and bu_frequency= :bu_frequency",
			ExpressionAttributeValues= {
				":site_id":site_id,
				":bu_frequency":bu_frequency
				}
			)
		if response['Items']:
			return response['Items']

	def insert(self):
		utc_time = datetime.datetime.utcnow()
		
		self.table.put_item(
			Item={
				'site_id': self.site_id,
				'schedule_id': self.schedule_id,
				'site_name': self.site_name,
				'bu_frequency': self.bu_frequency,
				'bu_status': self.bu_status,
				'created_at': utc_time.strftime("%Y-%m-%d %H:%M:%S"),
				'bu_time': self.bu_time,
				'bu_region': self.bu_region,
				'bu_files': self.bu_files,
				'bu_tables': self.bu_tables,
				'bu_frequency_weekday': self.bu_frequency_weekday,
				'bu_frequency_monthday': self.bu_frequency_monthday,
				'bu_exclusion_enabled': self.bu_exclusion_enabled
				}
			)

	def update(self, schedule):
		ScheduleModel.table.update_item(
			Key = {
			'site_id': schedule['site_id'],
			'schedule_id': schedule['schedule_id']
			},
			UpdateExpression = 'SET bu_frequency = :bu_f, bu_status = :bu_s, bu_time = :bu_t, bu_region = :bu_reg, bu_files = :bu_fls, bu_tables = :bu_tab, bu_frequency_weekday = :bu_wd, bu_frequency_monthday = :bu_md, bu_exclusion_enabled = :bu_ex_en',
			ExpressionAttributeValues = {
				':bu_f': self.bu_frequency,
				':bu_s': self.bu_status,
				':bu_reg': self.bu_region,
				':bu_t': self.bu_time,
				':bu_fls': self.bu_files,
				':bu_tab': self.bu_tables,
				':bu_wd': self.bu_frequency_weekday,
				':bu_md': self.bu_frequency_monthday,
				':bu_ex_en': self.bu_exclusion_enabled															
			}
		)

