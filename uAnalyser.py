""" 
Written by Ådne Karstad (aadnekar) October 2021
Used in collaboration with Nordic Semiconductor and NTNU
"""

import argparse
import os
import sys

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
    help="path to resulting file. The file must not exist from before.",
)
args = parser.parse_args()

TIME_DELTA = 0.01

# Intuitive choice, not generic in other cases
MAX_SLEEP_CURRENT = 20000

if __name__ == "__main__":

    files = []
    for path in args.path:
        if os.path.isdir(path):
            files += [p.path for p in os.scandir(path) if os.path.isfile(p)]
        elif os.path.isfile(path):
            files.append(path)

    for f_index, file_path in enumerate(files):
        if not os.path.exists(file_path):
            sys.exit(f"Path does not exist: {file_path}")

        if not os.path.isfile(file_path):
            sys.exit(f"Path does not point to file: {file_path}")

        file = open(file_path, "r")

        # Track the total current drawn for each section
        current_before = 0
        current_after = 0
        current_pin4 = 0
        # current_pin5 = 0
        current_pin6 = 0
        current_sleep = 0

        # Track the number of measurements for each section
        counter_before = 0
        counter_after = 0
        counter_pin4 = 0
        # counter_pin5 = 0
        counter_pin6 = 0
        counter_sleep = 0

        # Track the total time of each section
        ms_before = 0
        ms_after = 0
        ms_pin4 = 0
        # ms_pin5 = 0
        ms_pin6 = 0
        ms_sleep = 0

        # Header line
        print(file.readline())

        # Initial measure
        prev_measure = None
        prev_pins = None
        for line, measure in enumerate(file):
            measure = [elem for elem in measure.split(",")]
            pins = measure[2]

            if pins[3:7] == "1000":
                # Pin 3 is high
                if current_pin4 > 0:
                    # It's after the main iteration
                    current_after += float(measure[1])
                    counter_after += 1
                    if prev_pins and prev_pins[3] == "1":
                        ms_after += TIME_DELTA
                else:
                    current_before += float(measure[1])
                    counter_before += 1
                    if prev_pins and prev_pins[3] == "1":
                        ms_before += TIME_DELTA

            if pins[4] == "1":
                # Pin 4 is high
                current_pin4 += float(measure[1])
                counter_pin4 += 1
                # Conditional
                if prev_pins and prev_pins[4] == "1":
                    ms_pin4 += TIME_DELTA

            # if pins[5] == "1":
            #     # Pin 5 is high
            #     current_pin5 += float(measure[1])
            #     counter_pin5 += 1
            #     if prev_pins and prev_pins[5] == "1":
            #         ms_pin5 += TIME_DELTA

            if pins[6] == "1" and pins[4] != "1":
                # During "sleep"
                current_current = float(measure[1])
                if current_current > MAX_SLEEP_CURRENT:
                    current_pin6 += current_current
                    counter_pin6 += 1
                    if (
                        prev_pins
                        and prev_pins[6] == "1"
                        and float(prev_measure[1]) > MAX_SLEEP_CURRENT
                    ):
                        ms_pin6 += TIME_DELTA
                else:
                    current_sleep += current_current
                    counter_sleep += 1
                    if (
                        prev_pins
                        and prev_pins[6] == "1"
                        and float(prev_measure[1]) <= MAX_SLEEP_CURRENT
                    ):
                        ms_sleep += TIME_DELTA

            prev_measure = measure
            prev_pins = pins

        # Close the read file
        file.close()

        if args.output:
            # Open file for writing
            if f_index == 0:
                out_file = open(args.output, "x")
                out_file.write("File,Pin,Average uA,Total time(ms)\n")
            else:
                out_file = open(args.output, "a")

        output_line = (
            f"{file_path},before,{round(current_before/counter_before, 3)},{round(ms_before, 3)}\n"
            f"{file_path},after,{round(current_after/counter_after, 3)},{round(ms_after, 3)}\n"
            f"{file_path},pin4,{round(current_pin4/counter_pin4, 3)},{round(ms_pin4, 3)}\n"
            # f"{file_path},pin5,{round(current_pin5/counter_pin5, 3)},{round(ms_pin5, 3)}\n"
            f"{file_path},pin6,{round(current_pin6/counter_pin6, 3)},{round(ms_pin6, 3)}\n"
            f"{file_path},sleep,{round(current_sleep/counter_sleep, 3)},{round(ms_sleep, 3)}\n"
        )

        print(output_line)
        if args.output:
            out_file.write(output_line)

        if args.output and out_file:
            out_file.close()

        print(
            f"Completed {file_path}: {round((f_index+1)/len(files), 2) * 100}% complete"
        )
