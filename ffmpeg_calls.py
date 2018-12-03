import subprocess
import os

import logging
logging.basicConfig(filename='./logs/example.log',level=logging.DEBUG)
# Log format
#logging.debug('This message should go to the log file')
#logging.info('So should this')
#logging.warning('And this, too')


def retrieve_len(filepath):
    log.info("Retrieving length for " + filepath)
    temp = float(subprocess.check_output(["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(filepath)]))
    return int(temp)

def create_shortened_file(cutpoints_file_directory, target_directory, outputfile, cutpoints_filename="cutpoints.txt"):
    cutpoints_filepath = cutpoints_file_directory + "/" + cutpoints_filename
    output_filepath = target_directory + "/" + outputfile
    log.info("Ran command")
    log.info("ffmpeg -f concat -i "+ cutpoints_filepath + " " + output_filepath + " -y")
    subprocess.check_output(["ffmpeg", "-f", "concat", "-i", cutpoints_filepath, output_filepath, "-y"])

def dump_streams_metadata(filepath, WAV_directory):
    # print("ffmpeg is calling" + filepath)
    # os.system("ffmpeg -i \"" + str(filepath) + "\" &>streams.txt")  #

    command = ['ffprobe', '-i', filepath]
    p = subprocess.Popen(command, stderr=subprocess.PIPE)
    text = p.stderr.readlines()
    w = open(WAV_directory + "/" +"streams.txt", "w+")
    for l in text:
        w.write(str(l) + "\n")
    w.close()

def shorten_file(end_directory, starttime, filename, cuttosize, i, outfile_name = None):
    strm = "0:" + i

    if outfile_name == None:
        end_file = end_directory + "/" + i + "output.wav"
    else:
        end_file = end_directory + "/" + outfile_name


    print ("ffmpeg -ss " + str(starttime) + " -i \"" + str(filename) + "\" -t " + str(
        cuttosize) + " -map " + strm + " " + end_file + " -y")

    axws = "ffmpeg -ss " + str(starttime) + " -i \"" + str(filename) + "\" -t " + str(
        cuttosize) + " -map " + strm + " " + end_file + " -y"
    os.system(axws)

def shorten_file_with_specified_outfile(starttime, filename, cuttosize, i, outfile):
    strm = "0:" + i
    axws = "ffmpeg -ss " + str(starttime) + " -i \"" + str(filename) + "\" -t " + str(
        cuttosize) + " -map " + strm + " " + "" + outfile + " -y"
    os.system(axws)
