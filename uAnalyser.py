""" 
Written by Ådne Karstad (aadnekar) October 2021
Used in collaboration with Nordic Semiconductor and NTNU
"""

import argparse
from math import sqrt
import os
import sys
from colored import fg
from enum import Enum

SUCCESS_COLOR = fg('green')
ERROR_COLOR = fg('red')
INFO_COLOR = fg('blue')

parser = argparse.ArgumentParser(
    description="Command line tool for analysing power profile data, authored by Ådne Karstad @aadnekar"
)
parser.add_argument(
    "--path",
    nargs="+",
    required=True,
    help="relative path to source file to analyse. Provide several path's to compare results or a directory to analyse all files in that directory.",
)

parser.add_argument(
    "--output",
    "-o",
    type=str,
    required=True,
    help="path to result file. The file must not exist from before.",
)
args = parser.parse_args()

# Intuitive choice, not generic in other cases
MAX_SLEEP_CURRENT = 20000

SLEEP_THRESHOLD = 9

PIN_MODEM       = 0
APP_STATE_PINS  = [1, 5]
PIN_MAIN        = 5
PIN_GENERAL_1   = 6
PIN_GENERAL_2   = 7


class SECTION(Enum):
    SETUP   = 0
    COMPUTE = 1
    SEND    = 2
    SLEEP   = 3
    SYSTEM  = 4
    MODEM   = 5


RUNNING    = 'RUNNING'
FINISHED   = 'FINISHED'
SETUP      = 'SETUP'
COMPUTE    = 'COMPUTE'
SEND       = 'SEND'
SLEEP      = 'SLEEP'

APP_STATE = {
    RUNNING:  '0010',
    FINISHED: '0001',
    SETUP:    '00',
    COMPUTE:  '01',
    SEND:     '10',
    SLEEP:    '11',
    
}

def application_is_running(pins):
    """returns boolean True if pins indicate the app is stilling running healthy"""
    return pins == APP_STATE[RUNNING]

def application_is_finished(pins):
    """returns boolean True if pins indicate the app has finished in a  healthy mannor"""
    return pins == APP_STATE[FINISHED]

def get_label_from_file_path(file_path: str) -> str:
    return file_path.split('/')[-1].split('.')[0]

def MAIN():
    print(INFO_COLOR + "Starting uAnalyser script")
    if os.path.isfile(args.output):
        """
            If output file exists from before, ask user to overwrite or exit exec
        """
        print(f'The provided result file "{args.output}" already exist.')
        answer = None
        while answer not in ['yes', 'no']:
            answer = input("Do you want to overwrite it? [yes/no]")
        if answer == 'no':
            os.exit(f"Please provide a different output file.")
        os.remove(args.output)
    

    files = []
    for path in args.path:
        if os.path.isdir(path):
            files += [p.path for p in os.scandir(path) if os.path.isfile(p) and p.path.split('.')[-1] == 'csv']
        elif os.path.isfile(path):
            files.append(path)
    print(files)
    for file_index, file_path in enumerate(files):
        if not os.path.exists(file_path):
            sys.exit(f"Path does not exist: {file_path}")

        if not os.path.isfile(file_path):
            sys.exit(f"Path does not point to file: {file_path}")

        file = open(file_path, "r")

        # Track the total current drawn for each section
        current_total   = 0
        current_setup   = 0
        current_compute = 0
        current_send    = 0
        current_sleep   = 0
        current_modem   = 0
        current_system  = 0

        # Track the number of measurements for each section
        counter_total   = 0
        counter_setup   = 0
        counter_compute = 0
        counter_send    = 0
        counter_sleep   = 0
        counter_modem   = 0
        counter_system  = 0

        # Track the total time of each section
        time_total      = 0
        time_setup      = 0
        time_compute    = 0
        time_send       = 0
        time_sleep      = 0
        time_modem      = 0
        time_system     = 0
        
        # [current, counter, time]
        
        # SYSTEM_INDEX_CURRENT = 0
        # SYSTEM_INDEX_COUNT   = 1
        # SYSTEM_INDEX_TIME    = 0
        
        # system_values = {
        #     10:     [0]*3,
        #     20:     [0]*3,
        #     40:     [0]*3,
        #     80:     [0]*3,
        #     160:    [0]*3,
        # }

        # Header line
        print(file.readline())

        # Initial measure
        previous_section = None
        previous_timestamp = None
        previous_current = None
        previous_pins = None
        for line_index, line_data in enumerate(file):
            timestamp, current, pins = [elem for elem in line_data.split(',')[:3]]
            app_health = pins[APP_STATE_PINS[0]:APP_STATE_PINS[1]]

            if application_is_running(app_health) and pins[PIN_MAIN] == '1':
                timestamp       = float(timestamp)
                current         = float(current) if float(current) > 0 else 0
                state           = pins[PIN_GENERAL_1: PIN_GENERAL_2 + 1]
                counter_total   += 1
                current_total   += current
                
                if previous_timestamp is not None:
                    time_delta = timestamp - previous_timestamp
                    time_total += time_delta
                else:
                    time_delta = 0
                
                ###### One of the coming to count ######
                if state == APP_STATE[SETUP]:
                    current_setup   += current
                    counter_setup   += 1
                    if previous_section == SECTION.SETUP:
                        time_setup      += time_delta
                    previous_section = SECTION.SETUP
                
                elif state == APP_STATE[SEND]:
                    current_send   += current
                    counter_send   += 1
                    time_send      += time_delta

                elif state == APP_STATE[COMPUTE]:
                    current_compute   += current
                    counter_compute   += 1
                    if previous_section == SECTION.COMPUTE:
                        time_compute += time_delta
                    previous_section = SECTION.COMPUTE
                
                elif state == APP_STATE[SLEEP]:
                    if pins[PIN_MODEM] == '1':
                        current_modem   += current
                        counter_modem   += 1
                        if previous_section == SECTION.MODEM:
                            time_modem += time_delta
                        previous_section = SECTION.MODEM
                    
                    elif current > SLEEP_THRESHOLD:
                        current_system += current
                        counter_system += 1
                        if previous_section == SECTION.SYSTEM:
                            time_system += time_delta
                        previous_section = SECTION.SYSTEM

                    else:
                        current_sleep   += current
                        counter_sleep   += 1
                        if previous_section == SECTION.SLEEP:
                            time_sleep += time_delta
                        previous_section = SECTION.SLEEP
                                      
                else:
                    print(ERROR_COLOR + f"No state matching the current state in running: state={state}, does not match any of {APP_STATE}")
                        
                previous_timestamp = timestamp
                previous_current = current
                previous_pins = pins
        
                """
                REMEMBER TO CHECK STATE OF LAST SAMPLE TO SEE IF STATE IS DIFFERENT OR EQUAL
                ONLY ADD TO TOTAL TIME OF STATE IF STATE IS EQUAL TO LAST STATE...
                """
        
        # Close the read file
        file.close()

        if file_index == 0:
            out_file = open(args.output, "x")
            out_file.write("Label, Section, Number of samples, Average Current (uA), Total Current (uA) ,Total time(ms)\n")
        else:
            out_file = open(args.output, "a")

        output_line = (
            f"{get_label_from_file_path(file_path)},total,{counter_total},{current_total/counter_total if counter_total else 0},{current_total},{time_total}\n"
            f"{get_label_from_file_path(file_path)},setup,{counter_setup},{current_setup/counter_setup if counter_setup else 0},{current_setup},{time_setup}\n"
            f"{get_label_from_file_path(file_path)},compute,{counter_compute},{current_compute/counter_compute if counter_compute else 0},{current_compute},{time_compute}\n"
            f"{get_label_from_file_path(file_path)},send,{counter_send},{current_send/counter_send if counter_send else 0},{current_send},{time_send}\n"
            f"{get_label_from_file_path(file_path)},sleep,{counter_sleep},{current_sleep/counter_sleep if counter_sleep else 0},{current_sleep},{time_sleep}\n"
            f"{get_label_from_file_path(file_path)},modem,{counter_modem},{current_modem/counter_modem if counter_modem else 0},{current_modem},{time_modem}\n"
            f"{get_label_from_file_path(file_path)},system,{counter_system},{current_system/counter_system if counter_system else 0},{current_system},{time_system}\n"
        )
        print(output_line)
        if args.output:
            out_file.write(output_line)

        if args.output and out_file:
            out_file.close()

        print(
            f"Completed {file_path}: {round((file_index+1)/len(files), 2) * 100}% complete"
        )
        
def sleep_analysis():
    if not os.path.isfile(args.path[0]):
        sys.exit(f"Path is not a file: {args.path[0]}")
    
    file = open(args.path[0], "r")
    print(file.readline())
    
    total_current = 0
    number_of_samples = 0
    time = 0
    
    for line_index, line_data in enumerate(file.readlines()):
        timestamp, current, pins = [elem for elem in line_data.split(',')[:3]]
        app_health = pins[APP_STATE_PINS[0]:APP_STATE_PINS[1]]
        
        if application_is_running(app_health):
            current = float(current) if float(current) > 0 else 0
            timestamp = float(timestamp)
            total_current += current
            
            if previous_timestamp is not None:
                time += timestamp - previous_timestamp
            
            number_of_samples += 1
            
            previous_timestamp = timestamp
            previous_current = current
            previous_pins = pins
        else:
            previous_timestamp = None
            previous_current = None
    
    average_current = total_current / number_of_samples
    
    file.close()
    file = open(args.path[0], "r")
    print(file.readline())
    
    sum_of_absolute_difference = 0
    
    for line_index, line_data in enumerate(file.readlines()):
        timestamp, current, pins = [elem for elem in line_data.split(',')[:3]]
        app_health = pins[APP_STATE_PINS[0]:APP_STATE_PINS[1]]
        
        if application_is_running(app_health):
            current = float(current) if float(current) > 0 else 0
            sum_of_absolute_difference += (current - average_current)**2
            
    
    variance = sum_of_absolute_difference / number_of_samples
    standard_deviation = sqrt(variance)
    
    out_file = open(args.output, "x")
    
    out_string = f"Runtime, Number of samples, Total Current, Average Current, Variance, Standard Deviation, 'x + 3*σ\n"
    out_string += f"{time},{number_of_samples},{total_current},{average_current},{variance},{standard_deviation}, {average_current + 3*standard_deviation}\n"
    
    out_file.write(out_string)
    

if __name__ == "__main__":
    MAIN()
    # sleep_analysis()
