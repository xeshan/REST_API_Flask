import boto3
import os
aws_region = os.environ.get("dynamo_region")
if not aws_region:
    aws_region = os.environ.get("AWS_REGION")
    if not aws_region:
        aws_region = "us-east-1"

dynamodb = boto3.resource('dynamodb', aws_region)  # staging dynamodb

# dynamodb = boto3.resource('dynamodb', endpoint_url='http://localhost:8000')
##dynamodb = boto3.resource('dynamodb', 'us-west-1') # QA dynamodb
