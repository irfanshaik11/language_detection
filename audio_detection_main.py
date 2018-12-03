from voice_activity_detector import VoiceActivityDetector
import os
import datetime
import subprocess
import random
import re
import threading
import cleanup

import ffmpeg_calls

import logging
logging.basicConfig(filename='./logs/example.log',level=logging.DEBUG)
#Log format
#logging.debug('This message should go to the log file')
#logging.info('So should this')
#logging.warning('And this, too')

class Audio_Detector():
    def __init__(self, initial_directory, targetdirectory, wav_directory):
        self.initial_directory = initial_directory
        self.targetdirectory = targetdirectory
        self.wav_directory = wav_directory

    def shorten_given_file(self, sourcefile, lengthoffile, cuttosize = 1200, randomtoken = True, outfile = None):  #takes a file and cuts a random 20 minute sample of each of its audio channels
        # if the file is shorter than the specified cut size, the output will be a wav of the entire given audio stream

        # --------- Prints metadata to streams.txt ------------------------

        filetype = sourcefile.split(".")[-1]
        if filetype == "mp4":
            try:
                ffmpeg_calls.dump_streams_metadata(sourcefile, self.wav_directory)
            except Exception as e:
                log.debug("Could not create streams.txt file")
                log.debug(e)
                raise Exception

            # ---------- Finds number of Streams by Reading Streams.txt file ----------------------
            textfile = open(self.wav_directory + "/streams.txt", 'r')
            file_metadata = textfile.read()
            textfile.close()
            detected_streams = re.findall("Stream #0:(.+)Audio:", file_metadata)

            if lengthoffile <= cuttosize:
                rnd = 0
            else:
                if randomtoken == False:
                    rnd = 0
                else:
                    rnd = random.randint(60, int(lengthoffile - (cuttosize + 10)))

            outputarrs = []

            threads = []
            if detected_streams == []:
                log.warning("No Audio Streams Found")
                raise Exception

        elif filetype=="wav":
            stream_file_name = sourcefile.split("/")[-1]
            stream_number = stream_file_name.split("output")[0]
            detected_streams = [stream_number]

        for stream in detected_streams:
            #i stores the number of an audio stream
            i = stream[0] 
            starttime = str(datetime.timedelta(seconds=rnd)) #start time is the rnd seconds token turned to a format ffmpeg can read (HR:MN:SC)
            starttime = "0" + starttime


            # Encode every streams into a wav file using threads.
            if outfile == None:
                threads.append(threading.Thread(target=ffmpeg_calls.shorten_file, args=(self.wav_directory,starttime, sourcefile, cuttosize, i)))
                # ffmpeg_calls.shorten_file(starttime, destination_file, cuttosize, i)
                log.info(i + "output.wav created in " + self.wav_directory)
                outputarrs.append(self.wav_directory + "/" + str(i) + "output" + ".wav")
            else:
                threads.append(threading.Thread(target=ffmpeg_calls.shorten_file_with_specified_outfile, args=(starttime, sourcefile, cuttosize, i, outfile)))
                # ffmpeg_calls.shorten_file_with_specified_outfile(starttime, destination_file, cuttosize, i, outfile)
                log.info(outfile + " created")

        for i in threads:
            i.start()
        for i in threads:
            i.join()

        #returns the names of the wav files created
        return outputarrs 

    def create_cutpoints_file(self, arr, destination_file): #returns a text file with the most dense segments listed
        if destination_file[-10:] != "output.wav": #if the file being cut is not an [0-9]output.wav file, the file will simply output a [0-9]output.wav file
            destination_file = "output.wav"      #otherwise the output file will be the same [0-9]output.wav file that was fed into the function
        file = open(self.wav_directory + "/" + "cutpoints.txt", "w")
        num_cuts = int(300/len(arr))
        file_name = destination_file.split("/")[-1]
        for i in range(len(arr)):
            file.write("file " + file_name + "\n")

            file.write("inpoint " + str(arr[i]-num_cuts) + "\n")
            file.write("outpoint " + str(arr[i]) + "\n")
        file.close()
        log.info("created text file with cutpoints")
        return 0
        
    def create_voice_activity_clip(self, filename, outfile_name):
          log.info("Running VAD on " + str(filename))
          try:
              v = VoiceActivityDetector(filename)
          except Exception as e:
              log.info("ERROR at VAD " + str(filename) + " " + e)
              pass

          # convert phase recognition array to second format
          log.info("Converting windows to readible labels for " + str(filename))
          try:
              voice_activity_regions = v.convert_windows_to_readible_labels(v.detect_speech())
          except:
              log.debug("ERROR at convert windows to readable labels for file" + str(filename))
              raise Exception

          voice_activity_regions_array = []

          # Flattening the list
          for region in voice_activity_regions:
              voice_activity_regions_array = voice_activity_regions_array + list(region.values())


          if voice_activity_regions_array != []:
            log.info("No voice activity detecvted for this clip.")

            log.info("Finished creating array of voice activity regions")

            try:
                #generate a vector of seconds, which is where the array should be cut
                cut_areas = self.get_most_dense_range(voice_activity_regions_array)
                #creates a textfile.txt cut areas file in the wav directory
                self.create_cutpoints_file(cut_areas, filename) 
            except Exception as e:
                log.debug("could not create a text file with cut areas")
                log.debug(e)
                raise Exception

            if outfile_name == None: #allows you to specify an outfile name, if none is given creates a name
                file = "cut_stream" + filename[-11] + "_" + self.inputfile[:-4] + ".wav"  # creates cut_name for files
            else:
                file = outfile_name

            #creates a concatenated video file with high phrase density
            try:
                ffmpeg_calls.create_shortened_file(self.wav_directory, self.targetdirectory, file)
            except subprocess.CalledProcessError as e:
                log.debug(e)

            log.info("Created: " + self.targetdirectory + "/" + file)

          return file

    def get_most_dense_range(self, arr, randtoken = False, videolength = 1200):
        fr_len = 20 #length each segment should be
        num_cuts = int(120/fr_len) #number of segments that should be combined to give a 300 second clip
        densities = []
        for i in range(fr_len, videolength):
            _len = len([j for j in arr if i - fr_len <= j <= i])
            densities.append(_len)
        densities = sorted(densities, reverse=True)
        max_densities = densities[0:num_cuts]
        ## below loop translates if the max_densities (which are scalars) to the corresponding times where the phrase frequencies occur
        cut_areas = []

        if randtoken is False:
            for i in range(fr_len, videolength):
                if len(cut_areas) >= num_cuts:
                    break
                _len = len([j for j in arr if i - fr_len <= j <= i])
                if _len in max_densities:
                    cut_areas.append(i)
        if randtoken == True:

            randlocs = random.sample(range(fr_len, videolength, fr_len), num_cuts)
            for i in randlocs:
                cut_areas.append(i)

        return cut_areas

    # This function takes a video file, parses out its respective audio channels, runs voice activity detection on
    # those channels, and then generates a 5 minute clips for each channel representing audio with the highest voice
    # activit.
    def pre_process_video_file(self, inputfile = "audio.mp4", outfile_name = None, randtoken = False, callnumber = 1):

        log.info("input before file " + inputfile)
        #initialize inputs
        self.inputfile = inputfile
        self.source_file = self.initial_directory + "/" + self.inputfile

        log.info("inputfile " + self.inputfile)
        log.info("source file " + self.source_file)
        # ------------ Find the length of your file -------------
        lengthoffile = int(ffmpeg_calls.retrieve_len(self.source_file))

        log.info("Length of file " + str(lengthoffile))

        if lengthoffile == 0:
            log.info("ERROR: Length of file is 0" + inputfile)
            raise Exception

        #TODO: create a different function for second time processing.
        # Transcodes the video file into a wav file for audio analysis
        # and outputs it to the Wav-Encoded directory.
        if callnumber >= 2:
            wav_encoded_files = [self.initial_directory + "/" + inputfile]
        else:
            try:
                wav_encoded_files = self.shorten_given_file(self.source_file, lengthoffile=lengthoffile, cuttosize=2400) #shortens a given file and returns filepath
            except Exception as e:
                log.debug("ERROR: Can't shorten given file")
                log.debug(e)
                raise Exception
                
        log.info("wav_encoded_files " + str(wav_encoded_files))

        # Only do audio analysis on a file longer than 5 minutes.
        if lengthoffile > 300:
            threads = []
            for wav_file in wav_encoded_files:
                threads.append(threading.Thread(target=self.create_voice_activity_clip, args = (wav_file, outfile_name,)))
                
            print(threads)
            for i in threads:
                i.start()
            for i in threads:
                i.join()
        else:
            log.warning("File is short. Uploading the wav file without audio analysis")
            # Copies all the output.wav files to the Wav-Clips to be uploaded without further
            # processing for a file that is 5 or fewer minutes long.
            for filename in os.listdir(self.wav_directory):
                if "output.wav" in filename:
                    dest_path = self.targetdirectory + "/" + "cut_stream" + filename[-11] + "_" + self.inputfile[:-4] + ".wav"
                    cleanup.copy_file(self.wav_directory + "/" + filename, dest_path)


        
        

