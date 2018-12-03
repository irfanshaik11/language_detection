# Functions to interact with AWS S3 and Dynamo DB
import boto3
import json
import time
import botocore

S3_BUCKET_NAME = "mediator-lang-detect-filedrop"
S3 = boto3.resource('s3')
SQS = boto3.client(service_name='sqs')
DYNAMODB = boto3.resource('dynamodb')
QUEUENAME = "Lang-Detection-Audio-Processing-Request"

#------------- Dynamo DB

def db_put_item(table, item):
    table.put_item(
	   Item=item
	)

def db_get_item(table, key):
    response = table.get_item(
	    Key=key
	)
    item = response['Item']
    print(item)

def db_update_item(table, key, field, val):
    table.update_item(
	    Key=key,
	    UpdateExpression='SET #field = :val1',
	    ExpressionAttributeValues={
	        ':val1': val
    	},
		ExpressionAttributeNames={
			"#field": field
		}
	)

#------------- S3
def download_file_from_s3(bucket_name, file_name, destination):
    try:
        S3.Bucket(bucket_name).download_file(file_name, destination)
        return True
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            print("The object does not exist.")
        return False


def upload_file_to_s3(bucket_name, file_name):
    try:
        S3.meta.client.upload_file(file_name, bucket_name, file_name.split('/')[-1])
        return True
    except Exception as e:
        print(e)
        return False

#------------- SQS

def getSQSQueueUrl():
    response = SQS.get_queue_url(QueueName=QUEUENAME)
    return response['QueueUrl']

def getSQSMessage(queue_url):
    SQS.receive_message(
            QueueUrl=queue_url,
            AttributeNames=[
                'All'
            ],
            MessageAttributeNames=[
                'All',
            ],
            MaxNumberOfMessages=1,
            VisibilityTimeout=0,
            WaitTimeSeconds=0
        )

def deleteSQSMessage(queue_url, receipt_handle):
    SQS.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)
    return True














