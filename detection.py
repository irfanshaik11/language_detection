import urllib3
import subprocess
import threading
from multiprocessing.pool import ThreadPool
import random
from audio_detection_main import Audio_Detector
from API.azure_api import Video_Upload_API
import cleanup
import ffmpeg_calls
import json
import os.path 

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# setup log file
import logging
logging.basicConfig(filename='./logs/example.log',level=logging.DEBUG)
# Log format
#logging.debug('This message should go to the log file')
#logging.info('So should this')
#logging.warning('And this, too')


initial_directory = "./S3-Files" #directory containing mp4 files to be processed
shortened_files_directory = "./Wav-Clips" #directory containing files to be uploaded to azure
wav_files_directory = "./Wav-Encoded"
reprocessed_files_directory = "./Reprocessed_Files" #directory containing files that were inaccurate on the first reading
detection_results_json_directory = "./DetectionResultsJson"
MINIMUM_FILE_LENGTH_THRESHOLD = 300 # in seconds

## -- USER MUST SET THESE
VideoIndexer_Account_ID = "" #VI account id credential
VideoIndexer_Access_Key = "" #VI access key credential
account_type = "" #if trial put "trial" otherwise put region from videoindexer API
DELETE_ALL_FILES_AFTER_PROCESSING = False

AUDIO_DETECTOR = Audio_Detector(initial_directory , shortened_files_directory, wav_files_directory)
VI_API = Video_Upload_API(VideoIndexer_Account_ID, VideoIndexer_Access_Key, account_type)

def write_json_to_file(data, outputfile):
    try:
        file = open(outputfile, 'w')
        json.dump(data, file)
        file.close()
    except Exception, e:
        print(e)

def clean_all_directories():
    cleanup.remove_all_files_in_directory(initial_directory)
    cleanup.remove_all_files_in_directory(shortened_files_directory)
    cleanup.remove_all_files_in_directory(wav_files_directory)
    cleanup.remove_all_files_in_directory(reprocessed_files_directory)
    cleanup.remove_all_files_in_directory(detection_results_json_directory)

def get_confidence_by_random_samples():

  return ""

def get_confidence_by_random_segment():
  return ""

def retrieve_confidence(id, filename):
    #----- Retrieves Confidence For All Files Uploaded
    log.info("Getting confidence for file: " + filename + " id: " + id)
    
    language, confidence, response_json = VI_API.new_get_language(str(id))

    log.info("File: " + filename + " language: " + str(language) + " confidence: " + str(confidence))
    
    ## -------- Reuploads video using a 5 min segment comprising random 20 second samples if the confidence is too low ----------------------
    cnt = 2
    try:
        if confidence < 0.50:
            log.info("Low confidence score, redoing processing -- this will take ~10 mins")
            #Get the full audio filename corresponding to the clip
            stream_number = str(filename.split("_")[1][-1])
            encoded_file_name = stream_number + "output.wav"
            encoded_file_path = wav_files_directory  + "/" + encoded_file_name
            

            file_length = ffmpeg_calls.retrieve_len(encoded_file_path)
            #print("Failed to find video length")

            new_language, new_confidence, new_json = 0, 0, {}

            if file_length > MINIMUM_FILE_LENGTH_THRESHOLD:
                # Take the shorter length
                temp_cut_size = min(file_length, 2400)
                log.info("Going to cut " + str(temp_cut_size) + " from the file")

                #random_startpoint = random.randint(60, int(file_length - (temp_cut_size + 10)))

                # generate 20 second ranges between the beginning of the video and the cutsize.
                x = range(10,temp_cut_size, 20)

                arr = random.sample(x, 15)

                cutpoints_file = open(wav_files_directory + "/" + "cutpoints_random_sample.txt", "w")
                num_cuts = int(MINIMUM_FILE_LENGTH_THRESHOLD / len(arr))

                log.info("Number of cuts " + str(num_cuts))


                for i in range(len(arr)):
                    cutpoints_file.write("file " + str(encoded_file_name) + "\n")
                    cutpoints_file.write("inpoint " + str(arr[i] - num_cuts) + "\n")
                    cutpoints_file.write("outpoint " + str(arr[i]) + "\n")

                cutpoints_file.close()

                log.info("Trying to create the shortened file from the cutpoints")
                ffmpeg_calls.create_shortened_file(wav_files_directory, reprocessed_files_directory, filename, "cutpoints_random_sample.txt")

                temp_id = VI_API.upload_video_file(filename, reprocessed_files_directory + "/" + filename)
                new_language, new_confidence, new_json = VI_API.new_get_language(temp_id)

                if new_confidence > confidence:
                    confidence = new_confidence
                    language = new_language
                    response_json = new_json
                    VI_API.clean_index([id])
                else:
                    if temp_id != "None":
                        VI_API.clean_index([temp_id])

        
        log.info("Writing the results to json ... ")
        write_json_to_file(response_json, detection_results_json_directory + "/" + filename.split(".")[0] + ".json")
        log.info("Wrote result to: " + detection_results_json_directory + "/" + filename.split(".")[0] + ".json")
        
        return {
            "streamName": filename, 
            "language": str(language), 
            "confidence": str(confidence), 
            "resultJsonFile": filename.split(".")[0] + ".json"
        }

    except Exception as e:
        print("ERROR: Failed to get new confidence for file " + filename)
        print e
        return {}

    

def do_pre_processing():
  # ------------- Creates a Shortened Version of Initial File --------------------------
    try:
        AUDIO_DETECTOR.pre_process_video_file(file)  ##ff is the name of the shortened file
        return True
    except Exception as e:
        log.debug("Audio Detection Failed")
        print.debug(e)
        return False

def index_audio_clips(original_input_file, clip_directory):
  # ------------------ Indexes Shortened File in shortened_files_directory -------------

    VI_API.index_files(clip_directory)

    # ------------------------ Retrieves Dict of Video IDs
    Dict_of_filenames = VI_API.get_video_ids() #Dict[id] = filename

    # ------------------------ Collects the Relevant IDs from this Dict

    indexed_files = {}

    for i in Dict_of_filenames.keys():
        # Make sure the stream file uploaded to azure matches the initial file.
        original_file_name = original_input_file.split(".")[0]

        if original_file_name in Dict_of_filenames[i]: 
            # Add the the id of the uploaded file and map it to the filename
            indexed_files[i] = Dict_of_filenames[i]
        
    if indexed_files.keys() == []:
        log.warning("Could not find the Indexed Files we just uploaded!!")
        return {}

    return indexed_files

def do_detection(inputfile):   #call with the name of the file (eg "test.mp4")
    results = []

    if not os.path.isfile(initial_directory + "/" + inputfile):
        log.info("FILE "  + initial_directory + "/" + inputfile + " DOES NOT EXIST!")
        return []

    # ------------- Creates a Shortened Version of Initial File --------------------------
    try:
        AUDIO_DETECTOR.pre_process_video_file(inputfile)  ##ff is the name of the shortened file
    except Exception as e:
        log.debug("Audio Detection Failed")
        log.debug(e)
        return []

    try:
        relevant_files = index_audio_clips(inputfile, shortened_files_directory)
    except Exception as e:
        log.debug("Indexing phase failed because of error ")
        log.debug(e)
        return results

    # --------------------- Prints Confidence for Every Written File ----------------------

    # -------------- Run above function concurrently with multiple threads
    threads = []

    if len(relevant_files.keys()) <= 0:
        pass
    else:
        # For each file we've uploaded, create a thread to retrieve the confidence from the api.
        pool = ThreadPool(len(relevant_files.keys()))
        for id in relevant_files.keys():
            # print("Getting confidence for file " + relevant_files[id])
            threads.append(pool.apply_async(retrieve_confidence, (str(id), relevant_files[id],)))
        log.info(threads)
        results = [r.get() for r in threads]
        pool.close()
        pool.join()
     
    ## ---------------- Deletes all files ---------------------------------
    if DELETE_ALL_FILES_AFTER_PROCESSING == True:
        try:
            clean_all_directories()
        except Exception as e:
            log.debug("failed to delete all files")
            print e

    log.info("results " + str(results))
    return results
