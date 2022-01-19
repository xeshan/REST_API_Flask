from db import dynamodb
from boto3.dynamodb.conditions import Key, Attr
from time import strftime
import datetime

class ExportModel:
	def __init__(self, site_id, export_id, snapshot_id, created_at, export_status, download_link, send_email, email_account, display_name, hub_request):
		self.site_id = site_id
		self.export_id = export_id
		self.snapshot_id = snapshot_id
		self.created_at = created_at
		self.export_status = export_status
		self.download_link = download_link
		self.send_email = send_email
		self.email_account = email_account
		self.display_name = display_name
		self.hub_request = hub_request
		
	table = dynamodb.Table('exports')

	def json(self):
		return	{
				'site_id':self.site_id,
				'export_id':self.export_id,
				'snapshot_id':self.snapshot_id,
				'created_at':self.created_at,
				'export_status': self.export_status,
				'send_email': self.send_email,
				'email_account': self.email_account,
				'display_name': self.display_name,
				'hub_request': self.hub_request
				}

	@classmethod
	def find_by_export(cls, site_id, export_id):
		response =  ExportModel.table.get_item(
			Key = {
				'site_id': site_id,
				'export_id': export_id
			}
		)
		if "Item" in response.keys():
			return response['Item']
			
	def insert(self):
		self.table.put_item(
			Item={
				'site_id' : self.site_id,
				'snapshot_id' : self.snapshot_id,
				'export_id' : self.export_id,
				'created_at': self.created_at,
				'export_status': self.export_status,
				'send_email': self.send_email,
				'email_account': self.email_account,
				'display_name': self.display_name,
				'hub_request': self.hub_request		
			})

	def update(self, export):
		ExportModel.table.update_item(
			Key = {
			'site_id': export['site_id'],
			'export_id': export['export_id']
			},
			UpdateExpression = 'SET export_status = :e_status, download_link = :d_link',
			ExpressionAttributeValues = {
				':e_status': self.export_status,
				':d_link': self.download_link														
			}
		)
		
		