import os
import re
import subprocess
import shutil

#Logging
import logging
logging.basicConfig(filename='./logs/example.log',level=logging.DEBUG)
# Log format
#logging.debug('This message should go to the log file')
#logging.info('So should this')
#logging.warning('And this, too')



def clean(initial_directory, shortened_files_directory, wav_files_directory, reprocessed_files, results_json_directory):
#------- Deletes All Files in Start & Cut_WAV_Dir ----------------------------------
    # deletedfiles = subprocess.check_output(["rm", "-r", initial_directory + "/*"])
    for i in os.listdir(initial_directory):
        os.remove(initial_directory + "/"+ i)

    # deletedfilesindir2 = subprocess.check_output(["rm", "-r", shortened_files_directory + "/*"])
    for i in os.listdir(shortened_files_directory):
        os.remove(shortened_files_directory + "/" + i)

    for i in os.listdir(wav_files_directory):
        os.remove(wav_files_directory + "/" + i)


    for i in os.listdir(wav_files_directory):
        os.remove(wav_files_directory + "/" + i)

    for i in os.listdir(reprocessed_files):
        os.remove(reprocessed_files + "/" + i)

    for i in os.listdir(results_json_directory):
        os.remove(reprocessed_files + "/" + i)

def remove_all_files_in_directory(directory):
    if not os.path.isdir(directory):
        log.warning("Directory does not exist")
        return

    for i in os.listdir(directory):
        os.remove(directory + "/"+ i)


def copy_file(src, dest):
    if not os.path.isfile(src):
        log.warning("file does not exist")
        return

    shutil.copy2(src, dest)

# ------- Deletes All Output.wav files
#     deletedfilesindir2 = subprocess.check_output(["rm", "-r", "*.wav"])
