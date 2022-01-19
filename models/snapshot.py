from db import dynamodb
from boto3.dynamodb.conditions import Key, Attr
from time import strftime
import datetime

class SnapshotModel:
	def __init__(self, site_id, snapshot_id, schedule_id, user_id, bu_snapshot_name, created_at, snapshot_status, last_snap, bu_frequency, site_name, excluded_files, snapshot_size, bu_region, plugin_v, is_automate, tpd_exp_status, tpd_exp_done):
		self.site_id = site_id
		self.snapshot_id = snapshot_id
		self.schedule_id = schedule_id
		self.user_id = user_id
		self.bu_snapshot_name = bu_snapshot_name
		self.created_at = created_at
		self.snapshot_status = snapshot_status
		self.last_snap = last_snap
		self.bu_frequency = bu_frequency
		self.site_name = site_name
		self.excluded_files = excluded_files
		self.snapshot_size = snapshot_size
		self.bu_region = bu_region
		self.plugin_v = plugin_v
		self.is_automate = is_automate
		self.tpd_exp_status = tpd_exp_status
		self.tpd_exp_done = tpd_exp_done
		
	table = dynamodb.Table('snapshots')

	def json(self):
		return	{
				'site_id':self.site_id,
				'snapshot_id':self.snapshot_id,
				'schedule_id':self.schedule_id,
				'user_id':self.user_id,
				'bu_snapshot_name':self.bu_snapshot_name,
				'created_at':self.created_at,
				'snapshot_status': self.snapshot_status,
				'last_snap': self.last_snap,
				'bu_frequency': self.bu_frequency,
				'site_name': self.site_name,
				'excluded_files': self.excluded_files,
				'snapshot_size': self.snapshot_size,
				'bu_region': self.bu_region,
				'plugin_v': self.plugin_v,
				'is_automate': self.is_automate,
				'tpd_exp_status': self.tpd_exp_status,
				'tpd_exp_done': self.tpd_exp_done
				}

	@classmethod
	def find_by_snapshot(cls, site_id, snapshot_id):
		response =  SnapshotModel.table.get_item(
			Key = {
				'site_id': site_id,
				'snapshot_id': snapshot_id
			}
		)
		if "Item" in response.keys():
			return response['Item']

	@classmethod
	def snapshot_by_user(cls, user_id):
		response = SnapshotModel.table.query(
			IndexName='user_id-index',
			KeyConditionExpression= "user_id= :user_id",
			ExpressionAttributeValues= {
				":user_id":user_id
				}
			)
		if response['Items']:
			return response['Items']

	@classmethod
	def find_by_schedule(cls, schedule_id, created_at):
		response =  SnapshotModel.table.get_item(
				Key = {
					'schedule_id': schedule_id,
					'created_at': created_at
				}
			)
		if "Item" in response.keys():
			return response['Item']
			
	def insert(self):
		self.table.put_item(
			Item={
				'site_id' : self.site_id,
				'snapshot_id' : self.snapshot_id,
				'schedule_id' : self.schedule_id,
				'bu_snapshot_name': self.bu_snapshot_name,
				'user_id' : self.user_id,
				'created_at': self.created_at,
				'snapshot_status': self.snapshot_status,
				'last_snap': self.last_snap,
				'bu_frequency': self.bu_frequency,
				'site_name': self.site_name,
				'excluded_files': self.excluded_files,
				'snapshot_size': self.snapshot_size,
				'bu_region': self.bu_region,
				'plugin_v': self.plugin_v,
				'is_automate': self.is_automate,
				'tpd_exp_status': self.tpd_exp_status,
				'tpd_exp_done': self.tpd_exp_done
			})

	def update(self, snapshot):
		SnapshotModel.table.update_item(
			Key = {
			'site_id': snapshot['site_id'],
			'snapshot_id': snapshot['snapshot_id']
			},
			UpdateExpression = 'SET bu_snapshot_name = :bu_sname, snapshot_status = :s_status, last_snap = :lst_snap, snapshot_size = :s_size, plugin_v = :p_v, tpd_exp_status = :t_e_s, tpd_exp_done = :t_e_d',
			ExpressionAttributeValues = {
				':bu_sname': self.bu_snapshot_name,
				':s_status': self.snapshot_status,
				':lst_snap': self.last_snap,
				':s_size': self.snapshot_size,
				':p_v': self.plugin_v,
				':t_e_s': self.tpd_exp_status,
				':t_e_d': self.tpd_exp_done														
			}
		)
		
		