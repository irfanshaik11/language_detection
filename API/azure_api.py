import os
import requests
import urllib3
import time
import threading
import subprocess

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

#This file is a video indexer API

import logging
logging.basicConfig(filename='./logs/example.log',level=logging.DEBUG)
#Log format
#logging.debug('This message should go to the log file')
#logging.info('So should this')
#logging.warning('And this, too')


class Video_Upload_API():

    def __init__(self, account_id, subscription_key, account_type="trial"):
        self.subscription_key = subscription_key
        self.access_token = ""
        self.account_type = account_type# also known as location in API
        self.account_id = account_id
        self.subscription_key = subscription_key
        self.video_names = []
        self.API_AUTH_URL = "https://api.videoindexer.ai/auth/{0}/Accounts/{1}".format(account_type, account_id)
        self.API_VIDEO_URL = "https://api.videoindexer.ai/{0}/Accounts/{1}".format(account_type, account_id)
        self.API_VIDEO_INDEX_URL = "https://api.videoindexer.ai/{0}/Accounts/".format(account_id)

    def get_access_token(self):
        querystring = {"allowEdit": "true"}
        headers = {
            'Ocp-Apim-Subscription-Key': self.subscription_key,
            'Host': "api.videoindexer.ai"
        }

        url = '{0}/AccessToken'.format(self.API_AUTH_URL)

        logging.info("calling: " + url)

        response = requests.get(url, headers=headers, params=querystring, verify=False)
        self.access_token = response.text.replace('"', '')

        if len(self.access_token):
            logging.info("Retrieved Access Token")

        return self.access_token

    def get_video_names(self):
        url = "https://api.videoindexer.ai/{0}/Accounts/{1}/Videos?accessToken={2}".format(self.account_type,
                                                                                                   self.account_id,
                                                                                                   self.access_token)
        json_videos = requests.get(url, verify=False)

        for i in json_videos.json()["results"]:
            video_name = str(i["name"])
            if video_name not in self.video_names:
                self.video_names.append(video_name)

    def upload_video_file(self, video_name, file_path, language="auto", indexing_preset="AudioOnly",
                          streaming_preset="Default", replace = False):

        if self.access_token == "":
            self.get_access_token()

        # Upload a video
        upload_video_url = "{0}/Videos?accessToken={1}&name={2}&language={3}&indexingPreset={4}&streamingPreset={5}".format(
            self.API_VIDEO_URL, \
            self.access_token, video_name, language, indexing_preset, streaming_preset)

        f = open(file_path, 'rb')
        files = {'file': f}
        headers = {'Host': 'api.videoindexer.ai'}
        logging.info("Calling request to upload video ... " + file_path)
        response = requests.post(upload_video_url, files=files, headers=headers, verify=False)
        logging.info("Sent request for ... " + file_path)

        if response.ok:
            logging.info("Uploaded video ... determining status")
            self.check_upload_status(response.json()["id"])
        else:
            logging.info("error: ")
            logging.info(response.json())
            #self.check_upload_status(response.json()['id'])
        if "id" in response.json().keys():
            return response.json()["id"] #returns video id
        
        return "None" 

    def check_upload_status(self, upload_id):
        result = {}

        if upload_id:
            progress_url = "{0}/Videos/{1}/Index?accessToken={2}".format(self.API_VIDEO_URL, upload_id,
                                                                         self.access_token)

            while True:
                logging.info("Waiting for " + str(upload_id) + " to finish indexing")
                time.sleep(2)
                response = requests.get(progress_url, verify=False)

                if 'state' in response.json().keys():
                    print(response.json()['state'])

                    if response.json()['state'] == 'Failed':
                        logging.info("Failed to upload video. Please try re-uploading")
                        break

                    if response.json()['state'] == 'Processed':
                        return 0
                        logging.info("*" * 10)
                        logging.info("The source language is: ")
                        result['lang'] = response.json()['videos'][0]['sourceLanguage']
                        logging.info(result['lang'])

                        response = requests.get(progress_url, verify=False)

                        logging.info(response.json()['videos'][0]['insights'].keys())
                        if 'sourceLanguageConfidence' in response.json()['videos'][0]['insights'].keys():
                            result['level'] = response.json()['videos'][0]['insights']['sourceLanguageConfidence']
                            logging.info("Source Language Confidence is: " + str(
                                response.json()['videos'][0]['insights']['sourceLanguageConfidence']))
                        else:
                            logging.info("Language confidence could not be determined.")
                            result['level'] = "Unknown"

                        break
                else:
                    logging.info("State could not be found for " + upload_id + " " + str(response.json().keys()['Message']))

            return result

    def get_language(self, video_id = None): ## deprecated use new_get_language
        if video_id == None:
            logging.info("Error")
            return 1
        if not self.access_token:
            self.get_access_token()
        location = self.account_type
        my_url = "https://api.videoindexer.ai/{0}/Accounts/{1}/Videos/{2}/Index?accessToken={3}&language=English".format(location, self.account_id, video_id, self.access_token)
        response = requests.get(my_url, verify=False)
        if(response.status_code != 200):
            logging.info("Error Number: " + str(response.status_code))
            logging.info(response.json())

        x = response.json()
        language = x["videos"][0]["insights"]["sourceLanguage"]

        if "sourceLanguageConfidence" in x["videos"][0]["insights"].keys():
             confidence = x["videos"][0]["insights"]["sourceLanguageConfidence"]
        else:
            confidence = None

        logging.info("language: " + str(language) + "\naccuracy: " + str(confidence))


        return language,confidence

    #TODO: get the ids of just the files that have been indexed from the Wav-Clips
    def get_video_ids(self):
        if self.access_token == "":
            self.get_access_token()
        
        req = requests.get("https://api.videoindexer.ai/{0}/Accounts/{1}/Videos?accessToken={2}".format(self.account_type,self.account_id,self.access_token), verify = False)
        
        Dict = {}
        try:
            for i in req.json()['results']:
                Dict[str(i["id"])] = str(i["name"])
        except:
            print(req.json())
            raise Exception
        return Dict #returns Dictionary with format "id":"name of file"
        if self.access_token == "":
            self.get_access_token()


    def new_get_video_ids(self):
        if self.access_token == "":
            self.get_access_token()
        type = "LanguageDetection"
        req = requests.get(
            "https://api.videoindexer.ai/{0}/Accounts/{1}/Videos/{2}/ArtifactUrl?type={3}?accessToken={4}".format(self.account_type,self.account_id,video_id,type,self.access_token),
            verify=False)
        Dict = {}
        # print(req.json()['results'])
        for i in req.json()['results']:
            Dict[str(i["id"])] = str(i["name"])
        return Dict;  # returns Dictionary with format "id":"name of file"

    def new_get_language(self, video_id = None):
        if video_id == None:
            logging.debug("Error")
            return 1
        if not self.access_token:
            self.get_access_token()

        location = self.account_type
        accountId = self.account_id
        videoId = video_id
        type = "LanguageDetection"
        accessToken = self.access_token
        response = requests.get(
            "https://api.videoindexer.ai/{0}/Accounts/{1}/Videos/{2}/ArtifactUrl?type={3}&accessToken={4}".format(
                location,accountId,videoId,type,accessToken), verify=False)

        if response.status_code != 200:
            print("Error retrieving response for video from azure: ")
            print(response.json())
            return 0, 0, {}
        
        verbose_language_data_url = response.json()
        #print(y) #prints the retrieved json
        response = requests.get(str(verbose_language_data_url), verify=False)
        response_json = response.json()
        language = response_json["MasterLanguage"]
        confidence = response_json["Confidence"]

        return language, confidence, response_json

    def index_files(self,directory):
        Dict = self.get_video_ids()
        D2 = [j for j in Dict.values()]

        threads = []

        for file in os.listdir(directory):
            if str(file) not in D2:
                video_path = directory + "/" + str(file)
                logging.info("Uploading  " + str(file))
                threads.append(threading.Thread(target=self.upload_video_file, args=(str(file),video_path)))

        for i in threads:
            i.start()

        for i in threads:
            i.join()

        #wait for all child processes to return
        # continue
        return 0

    def clean_index(self, arr):  # arr contains index numbers of files to be deleted
        location = self.account_type
        accountId = self.account_id
        accessToken = self.access_token
        for i in arr:
            videoId = i
            logging.info("Deleting " + videoId)
            req = requests.delete(
                "https://api.videoindexer.ai/{0}/Accounts/{1}/Videos/{2}?accessToken={3}".format(location, accountId,
                                                                                                 videoId, accessToken))

            if str(req.status_code) != str(204):
                logging.warning("Failed to Delete " + videoId)
                
        return 0
