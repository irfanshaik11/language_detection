import boto3
import json
import time
import botocore
import glob
import cleanup
import detection

initial_directory = "./S3-Files" #directory containing mp4 files to be processed
shortened_files_directory = "./Wav-Clips" #directory containing files to be uploaded to azure
wav_files_directory = "./Wav-Encoded"
reprocessed_files_directory = "./Reprocessed_Files" #directory containing files that were inaccurate on the first reading
detection_results_json_directory = "./DetectionResultsJson"


#Logging
import logging
logging.basicConfig(filename='./logs/example.log',level=logging.DEBUG)
# Log format
#logging.debug('This message should go to the log file')
#logging.info('So should this')
#logging.warning('And this, too')


S3_SOURCE_BUCKET_NAME = "mediator-lang-detect-filedrop"
S3_RESULTS_BUCKET_NAME = "mediator-lang-detect-results"
S3 = boto3.resource('s3')
SQS = boto3.client(service_name='sqs')
DYNAMODB = boto3.resource('dynamodb')
ASSET_TABLE = DYNAMODB.Table('language-detection-asset')
LOCAL_DOWNLOAD_DIR = "./S3-Files/"
RESULTS_DIR = "./DetectionResultsJson/"

def db_put_item(table, item):
    table.put_item(
	   Item=item
	)

def db_get_item(table, key):
    response = table.get_item(
	    Key=key
	)

    # Found item
    if 'Item' in response.keys():
        return response['Item']
    
    # Return empty object if no item exists
    return {}
    

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

def check_successful_detection(filename):
    log.info("Trying to retrieve object from DB")
    item = db_get_item(ASSET_TABLE, {'mat-id': filename})
    
    if item:
        if item['Status'] == "Finished":
            return True
        else:
            return False

    return False


def download_file_from_s3(bucket_name, file_name, destination):
    try:
        S3.Bucket(bucket_name).download_file(file_name, destination)
        return True
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            log.info("The object does not exist.")
        return False


def upload_file_to_s3(bucket_name, file_name):
    try:
        S3.meta.client.upload_file(file_name, bucket_name, file_name.split('/')[-1])
        return True
    except Exception as e:
        print(e)
        return False

def uploadResultJson():
    result_json_files = glob.glob(RESULTS_DIR + "*.json")
    if len(result_json_files):
        for file in result_json_files:
            upload_file_to_s3(S3_RESULTS_BUCKET_NAME, file)
            log.info("uploaded " + file)
    else:
        log.info("No results to upload")


def do_language_detection(filename):
    log.info("Doing detection on file " + filename)
    results = []

    successful_detection = check_successful_detection(filename)

    if not successful_detection:
        results = detection.do_detection(filename)
        return results

    # If the file exists, return the results from the database.
    item = db_get_item(ASSET_TABLE, {'mat-id': filename})
    return item['Results']



def processMessage(message):
    """Takes a message from SQS, determines if it is an S3 upload event
	and then downloads the file that was uploaded to S3, and runs the audio
	detection workflow on the file. Then, upload the resulting json to an s3 bucket.
	"""
	
    # This means it is a message from S3
    if("Records" in message.keys()):
        s3Event = message["Records"][0]
        file_uploaded_name = s3Event["s3"]["object"]["key"]

        # Remove plus signs that are substituted in for spaces
        file_uploaded_name = file_uploaded_name.replace('+', ' ')
		
        bucket_name = s3Event["s3"]["bucket"]["name"]
        destination = LOCAL_DOWNLOAD_DIR+file_uploaded_name.split("/")[-1]
		
        log.info("Downloading file to ... " + destination)

        downloadSuccess = download_file_from_s3(bucket_name, file_uploaded_name, destination)

        try:
            if downloadSuccess:
                log.info("Downloaded file")
                db_put_item(ASSET_TABLE, {
                    'mat-id': file_uploaded_name,
                    'Status': "Processing..."
                        })
                log.info("Created record in DB ... starting to process...")

                Results = do_language_detection(file_uploaded_name)
				
                log.info("Finished Processing")

                if Results:
                    #Updating the db_record
                    db_update_item(ASSET_TABLE, {'mat-id': file_uploaded_name}, 'Status', 'Finished')
                    db_update_item(ASSET_TABLE, {'mat-id': file_uploaded_name}, 'Results', Results)
                    log.info("Updated records in DB, successfully completed detection for " + file_uploaded_name)
                    uploadResultJson()
                else:
                    db_update_item(ASSET_TABLE, {'mat-id': file_uploaded_name}, 'Status', 'Failed')

        except Exception as e:
            db_update_item(ASSET_TABLE, {'mat-id': file_uploaded_name}, 'Status', 'Failed')
            db_update_item(ASSET_TABLE, {'mat-id': file_uploaded_name}, 'Results', str(e))
            log.debug("Processing failed")

        log.debug("Processed message. Cleaning up temp files ...")
        detection.clean_all_directories()

    else:
        log.warning("Unrelated message")
        return False

    return True


def listenForSQS():
    """
		This function connects to an sqs queue and listens for a notification from
		an SNS notification which is triggered by an S3 bucket. Once we get the
		message from the SQS queue, we know something has been uploaded. Then we will
		download the file and run our lang-detection workflow.
	"""
    response = SQS.get_queue_url(QueueName='Lang-Detection-Audio-Processing-Request')
    queue_url = response['QueueUrl']

    log.info("Listening for messages ...")
    while True:
        time.sleep(10)
        response = SQS.receive_message(
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
        log.info("Polled Queue ...")

        # print (response)
        if ('Messages' in response.keys()):
            log.info("Found a message!")
            message = response['Messages'][0]
            receipt_handle = message['ReceiptHandle']

            msg_body = json.loads(message['Body'])

            # Download the video
            processMessage(msg_body)

            #Delete the Message
            SQS.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)
            # print(json.dumps(msg_body, indent=4))
        else:
            log.info("Message queue is empty!")


log.info("Started Program")
listenForSQS()



