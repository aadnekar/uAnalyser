import argparse
import os
import sys
import numpy as np
import matplotlib.pyplot as plt
from itertools import chain, product

parser = argparse.ArgumentParser(
    description="Command line tool for plotting results from uAnalyser tool, authored by Ådne Karstad @aadnekar"
)

parser.add_argument(
    "--path",
    "-p",
    help="Relative path to source file",
)

parser.add_argument(
    "--output",
    "-o",
    help="Relative path to output directory",
)

args = parser.parse_args()

COLORS = [
    "#39918c",
    "#d0b49f",
    "#ab6b51",
    "#f9c74f",
    "#2f435a",
    "#90be6d",
    "#43aa8b",
    "#4d908e",
]

MILLI_VOLTAGE = 3.7 * 1000

SOURCE_DIRECTORY = "/home/aadneka/ntnu/uAnalyser"

if args.path:
    SOURCE_FILE = args.path
else:
    SOURCE_FILE = f"/{SOURCE_DIRECTORY}/results.csv"

if args.output:
    if not os.path.isdir(args.output):
        os.mkdir(args.output)
    RESULTS_DIR = args.output
else:
    RESULTS_DIR = f"/{SOURCE_DIRECTORY}/plots"

TOTAL = "TOTAL"
SETUP = "SETUP"
COMPUTE = "COMPUTE"
SEND = "SEND"
SLEEP = "SLEEP"
MODEM = "MODEM"
SYSTEM = "SYSTEM"

SECTIONS = {
    TOTAL: "total",
    COMPUTE: "compute",
    SLEEP: "sleep",
    SEND: "send",
    MODEM: "modem",
    SYSTEM: "system",
    SETUP: "setup",
}

PROTOCOLS = [
    "tls",
    "tls_e2e",
    "no_tls",
    "no_tls_e2e",
]

""" Defines sorting order for sorting values and labels by protocol"""
PROTOCOL_SORTING_ORDER = {"no_tls": 1, "no_tls_e2e": 2, "tls": 3, "tls_e2e": 4}

OPERATIONS = ["10", "15", "20", "25"]

PAYLOAD_SIZE = [
    "256B",
    "708B",
    "1024B",
    "1416B",
    "2048B",
]

ALL_CONFIGURATION_LABELS = [
    " ".join(config_product)
    for config_product in product(PROTOCOLS, OPERATIONS, PAYLOAD_SIZE)
]

COUNT = "COUNT"
AVERAGE_CURRENT = "AVERAGE_CURRENT"
TOTAL_CURRENT = "TOTAL_CURRENT"
TIME = "TIME"

DATA_INDEX = {COUNT: 0, AVERAGE_CURRENT: 1, TOTAL_CURRENT: 2, TIME: 3}


def GET_SECTION_FILTER(section: str):
    return section == SECTIONS[TOTAL] or section == SECTIONS[SEND]
    # return section != SECTIONS[TOTAL]
    # return section != SECTIONS[COMPUTE] and section != SECTIONS[SEND] and section != SECTIONS[SLEEP]
    # return section == SECTIONS[MODEM] or section == SECTIONS[TOTAL] or section == SECTIONS[SETUP]


def util_find_corresponding_protocol_label(label: str):
    return "_".join(label.split("_")[:-2])


def parse_file_data_to_dictionary():
    file = open(SOURCE_FILE, "r")
    print("Reading file containing fields:")
    print(file.readline())

    data_dictionary = {}

    for data_line in file.readlines():
        if len(data_line) < 5:
            print(data_line)
            continue
        label, section, count, average_current, total_current, time, joules = data_line.split(
            ","
        )

        if data_dictionary.get(label) == None:
            data_dictionary[label] = {}

        data_dictionary[label][section] = [
            float(count),
            float(average_current),
            float(total_current),
            float(time),
            float(joules),
        ]

    return data_dictionary


def util_from_uA_to_mA(uA: float):
    return uA / 1000


def util_from_ms_to_s(ms: float):
    return round(ms / 1000, 4)


def util_is_tls_label(label_snippet):
    return label_snippet == "tls"


def util_sorter(label_list):
    protocol_value = (
        PROTOCOL_SORTING_ORDER["_".join(label_list[:-2])] if len(label_list) > 2 else 0
    )
    operations = int(label_list[-2])
    payload = int(label_list[-1][:-1])
    return (operations, payload, protocol_value)


def util_get_joules(average_I: float, duration: float):
    """Calculate joules based of average current drawn and the duration

    Args:
        average_I (float): Average current draw
        duration (float): Time period of the average_I

    Returns:
        float: estimated Joules used for a period of time
    """
    Watts = (util_from_uA_to_mA(average_I) * MILLI_VOLTAGE) / 1e6
    Joules = (Watts * duration) / 1e3
    return Joules


def sort_labels(labels):
    sorter = lambda label: util_sorter(label.split(" "))
    return sorted(labels, key=sorter)


def sort_values_by_label(labels, to_sort):
    """
    Sorting order (most significant to least significant):
        1. PROTOCOL
        2. Operations
        3. Payload size
    """
    sorter = lambda label: util_sorter(label[0].split("_"))
    return [value for (_, value) in sorted(zip(labels, to_sort), key=sorter)]


def get_labels(data_dictionary):
    """
    Extracts all keys, which are taken from the file_names of the csv files their data are
    retrieved from.
    Typically: 'no tls 10 256B' or 'tls 25 1024B'
    """
    return sort_labels([" ".join(label.split("_")) for label in data_dictionary.keys()])


def get_payload_labels(data_dictionary):
    return [label.split("_")[-1] for label in get_labels(data_dictionary)]


def get_time_of_section(data_dictionary, section, filters: list = None):
    data = []
    labels = []
    for label, label_values in data_dictionary.items():
        if filters and not all([_filter in label.split("_") for _filter in filters]):
            continue
        labels.append(label)
        data.append(util_from_ms_to_s(label_values[section][DATA_INDEX[TIME]]))
    return sort_values_by_label(labels, data)


def get_joules_of_section(data_dictionary, section: str, filters: list = None):
    """Get a list of joule values

    Args:
        data_dictionary (dict): _description_
        section (str): _description_
        filter (list, optional): Part of label to filter on. Defaults to None. E.g. ['25', '256B'] or simply ['256B'].

    Returns:
        list: joule values
    """

    data = []
    labels = []
    for label, label_values in data_dictionary.items():
        if filters and not all([_filter in label.split("_") for _filter in filters]):
            continue

        labels.append(label)
        joules = label_values[section][4]
        data.append(joules)
        # print(f"Label={label} used {joules} joules")

    return sort_values_by_label(labels, data)


def util_filter_labels(labels, filters: list):
    return [
        label
        for label in labels
        if all([_filter in label.split(" ") for _filter in filters])
    ]


def plot_joules(data_dictionary):
    all_labels = [
        " ".join(label.split(" ")[1:])
        for label in util_filter_labels(ALL_CONFIGURATION_LABELS, ["tls"])
    ]

    for number_of_operations in OPERATIONS:
        labels = util_filter_labels(all_labels, filters=[number_of_operations])
        x_labels = list(
            chain.from_iterable(
                [
                    (
                        "none",
                        "e2e",
                        f"\n\n{label.split(' ')[-1]}",
                        "tls",
                        "tls+",
                    )
                    for label in labels
                ]
            )
        )

        width = 0.4
        x = np.arange(len(labels)) * 2
        xticks = list(
            chain.from_iterable(
                [
                    (
                        i - width - width / 2,
                        i - width / 2,
                        i,
                        i + width / 2,
                        i + width + width / 2,
                    )
                    for i in x
                ]
            )
        )
        fig, ax = plt.subplots(figsize=(5, 3), constrained_layout=True)
        
        y = np.linspace(start=0, stop=6, num=7)
        plt.yticks(y)

        no_tls_accumulated = [0] * len(labels)
        tls_accumulated = [0] * len(labels)
        no_tls_e2e_accumulated = [0] * len(labels)
        tls_e2e_accumulated = [0] * len(labels)
        for index, section in enumerate(SECTIONS.values()):
            if GET_SECTION_FILTER(section):
                continue

            joules = get_joules_of_section(
                data_dictionary, section, filters=[number_of_operations]
            )
            
            # print(f"joules: {joules}")

            no_tls_joules = [value for value in joules[0::4]]
            tls_joules = [value for value in joules[1::4]]
            no_tls_e2e_joules = [value for value in joules[2::4]]
            tls_e2e_joules = [value for value in joules[3::4]]

            # print(f"Joules for {section} section no_tls protocol: no_tls_joules")
            # print(no_tls_joules)
            
            ax.bar(
                x - width - width / 2,
                no_tls_joules,
                width,
                bottom=no_tls_accumulated,
                color=COLORS[index],
                label=section,
                zorder=3,
            )
            ax.bar(
                x - width / 2,
                tls_joules,
                width,
                bottom=tls_accumulated,
                color=COLORS[index],
                zorder=3,
            )

            ax.bar(
                x + width / 2,
                no_tls_e2e_joules,
                width,
                bottom=no_tls_e2e_accumulated,
                color=COLORS[index],
                zorder=3,
            )

            ax.bar(
                x + width + width / 2,
                tls_e2e_joules,
                width,
                bottom=tls_e2e_accumulated,
                color=COLORS[index],
                zorder=3,
            )

            no_tls_accumulated = [
                accumulated + value
                for accumulated, value in zip(no_tls_accumulated, no_tls_joules)
            ]
            tls_accumulated = [
                accumulated + value
                for accumulated, value in zip(tls_accumulated, tls_joules)
            ]
            no_tls_e2e_accumulated = [
                accumulated + value
                for accumulated, value in zip(no_tls_e2e_accumulated, no_tls_e2e_joules)
            ]
            tls_e2e_accumulated = [
                accumulated + value
                for accumulated, value in zip(tls_e2e_accumulated, tls_e2e_joules)
            ]

        ax.bar(
            x - width - width / 2,
            no_tls_accumulated,
            width,
            fill = False,
            edgecolor="black",
            zorder=3,
        )
        ax.bar(
            x - width / 2,
            tls_accumulated,
            width,
            fill = False,
            edgecolor="black",
            zorder=3,
        )

        ax.bar(
            x + width / 2,
            no_tls_e2e_accumulated,
            width,
            fill = False,
            edgecolor="black",
            zorder=3,
        )

        ax.bar(
            x + width + width / 2,
            tls_e2e_accumulated,
            width,
            fill = False,
            edgecolor="black",
            zorder=3,
        )

        ax.set_ylabel("Energy consumption (Joule)")
        plt.xticks(xticks, x_labels)
        
        ax_labels = ax.get_xticklabels()
        for index in range(2, len(ax_labels), 5):
            ax_labels[index-2].set_rotation(-45)
            ax_labels[index-1].set_rotation(-45)
            ax_labels[index+1].set_rotation(-45)
            ax_labels[index+2].set_rotation(-45)


        ax.legend(
            bbox_to_anchor=(0, 1, 1, 0), loc="lower left", mode="expand", ncol=len(x_labels)
        )

        plt.savefig(
            f"{RESULTS_DIR}/energy_stacked_{number_of_operations}-operations.png",
            transparent=False,
            orientation="portrait",
        )


def plot_time(data_dictionary):
    all_labels = [
        " ".join(label.split(" ")[1:])
        for label in util_filter_labels(ALL_CONFIGURATION_LABELS, ["tls"])
    ]

    for number_of_operations in OPERATIONS:

        labels = util_filter_labels(all_labels, filters=[number_of_operations])
        x_labels = list(
            chain.from_iterable(
                [
                    (
                        "none",
                        "e2e",
                        f"\n\n{label.split(' ')[-1]}",
                        "tls",
                        "tls+",
                    )
                    for label in labels
                ]
            )
        )

        width = 0.4
        x = np.arange(len(labels)) * 2
        xticks = list(
            chain.from_iterable(
                [
                    (
                        i - width - width / 2,
                        i - width / 2,
                        i,
                        i + width / 2,
                        i + width + width / 2,
                    )
                    for i in x
                ]
            )
        )
        fig, ax = plt.subplots(figsize=(5, 3), constrained_layout=True)
        
        y = np.linspace(start=0, stop=400, num=5)
        plt.yticks(y)
        for ytick in y:
            plt.axhline(y=ytick, color='black', linestyle='-', linewidth=0.5)

        no_tls_accumulated = [0] * len(labels)
        tls_accumulated = [0] * len(labels)
        no_tls_e2e_accumulated = [0] * len(labels)
        tls_e2e_accumulated = [0] * len(labels)
        for index, section in enumerate(SECTIONS.values()):
            if GET_SECTION_FILTER(section):
                continue

            times = get_time_of_section(
                data_dictionary, section, filters=[number_of_operations]
            )

            no_tls_times = [value for value in times[0::4]]
            tls_times = [value for value in times[1::4]]
            no_tls_e2e_times = [value for value in times[2::4]]
            tls_e2e_times = [value for value in times[3::4]]

            ax.bar(
                x - width - width / 2,
                no_tls_times,
                width,
                bottom=no_tls_accumulated,
                color=COLORS[index],
                label=section,
                zorder=3,
            )
            ax.bar(
                x - width / 2,
                tls_times,
                width,
                bottom=tls_accumulated,
                color=COLORS[index],
                zorder=3,
            )
            ax.bar(
                x + width / 2,
                no_tls_e2e_times,
                width,
                bottom=no_tls_e2e_accumulated,
                color=COLORS[index],
                zorder=3,
            )
            ax.bar(
                x + width + width / 2,
                tls_e2e_times,
                width,
                bottom=tls_e2e_accumulated,
                color=COLORS[index],
                zorder=3,
            )

            no_tls_accumulated = [
                accumulated + value
                for accumulated, value in zip(no_tls_accumulated, no_tls_times)
            ]
            tls_accumulated = [
                accumulated + value
                for accumulated, value in zip(tls_accumulated, tls_times)
            ]
            no_tls_e2e_accumulated = [
                accumulated + value
                for accumulated, value in zip(no_tls_e2e_accumulated, no_tls_e2e_times)
            ]
            tls_e2e_accumulated = [
                accumulated + value
                for accumulated, value in zip(tls_e2e_accumulated, tls_e2e_times)
            ]
            
        ax.bar(
            x - width - width / 2,
            no_tls_accumulated,
            width,
            fill = False,
            edgecolor="black",
            zorder=3,
        )
        ax.bar(
            x - width / 2,
            tls_accumulated,
            width,
            fill = False,
            edgecolor="black",
            zorder=3,
        )

        ax.bar(
            x + width / 2,
            no_tls_e2e_accumulated,
            width,
            fill = False,
            edgecolor="black",
            zorder=3,
        )

        ax.bar(
            x + width + width / 2,
            tls_e2e_accumulated,
            width,
            fill = False,
            edgecolor="black",
            zorder=3,
        )
        
        ax.set_ylabel("Time consumption (Seconds)")
        
        plt.xticks(xticks, x_labels)
        
        ax_labels = ax.get_xticklabels()
        for index in range(2, len(ax_labels), 5):
            ax_labels[index-2].set_rotation(-45)
            ax_labels[index-1].set_rotation(-45)
            ax_labels[index+1].set_rotation(-45)
            ax_labels[index+2].set_rotation(-45)

        ax.legend(
            bbox_to_anchor=(0, 1, 1, 0), loc="lower left", mode="expand", ncol=len(x_labels)
        )

        plt.savefig(
            f"{RESULTS_DIR}/time_stacked_{number_of_operations}-operations.png",
            transparent=False,
            orientation="portrait",
        )


def log_theoretical_and_real_value_differences(data_dictionary):
    output = f"Configuration,Theoretical,Real Value,Difference\n"
    for label, sections in data_dictionary.items():
        compute_intensity = 2 ** (int(label.split("_")[-2]))
        # theoretical_time = compute_intensity / (64*(10**6))  * 1000
        theoretical_time = compute_intensity / ((64 * (10 ** 6)) - 32768) * 1000

        output += f"{label},{theoretical_time},{sections['compute'][-1]},{theoretical_time - sections['compute'][-1]}\n"

    file = open("theoretical_difference.csv", "x")
    file.write(output)
    file.close()


def detailed_analytics(data_dictionary):
    """
    Verify that sum(sections) == TOTAL, in terms of both time and total current

    For each setion investigate the section/total value

    Also investigate the (compute + send + sleep + system)/ total compared to the setup
    and find out how many cycles are needed to get them equal?
    """

    output_time_header = f"Configuration,sum,comp,send,sleep,system,modem,system\n"
    output_power_header = f"Configuration,sum,comp,send,sleep,system,modem,system\n"

    def get_percent(fraction, total):
        return f"{round((fraction/total) * 100, 2)}\%"

    times_grouped_by_protocol_dict = {}
    joules_grouped_by_protocol_dict = {}

    for protocol in PROTOCOLS:
        times_grouped_by_protocol_dict[protocol] = []
        joules_grouped_by_protocol_dict[protocol] = []

    for label, sections in data_dictionary.items():
        time_total = sections["total"][-1]
        time_sum = sum(
            [
                values[-1]
                for section, values in sections.items()
                if section != SECTIONS[TOTAL]
            ]
        )
        time_compute = sections["compute"][-1]
        time_send = sections["send"][-1]
        time_sleep = sections["sleep"][-1]
        time_system = sections["system"][-1]
        time_modem = sections["modem"][-1]
        time_setup = sections["setup"][-1]
        time_sections = [
            time_sum,
            time_compute,
            time_send,
            time_sleep,
            time_system,
            time_modem,
            time_setup,
        ]

        joules_total = util_get_joules(sections["total"][-3], sections["total"][-1])
        joules_sum = sum(
            [
                util_get_joules(values[-3], values[-1])
                for section, values in sections.items()
                if section != SECTIONS[TOTAL]
            ]
        )
        joules_compute = util_get_joules(
            sections["compute"][-3], sections["compute"][-1]
        )
        joules_send = util_get_joules(sections["send"][-3], sections["send"][-1])
        joules_sleep = util_get_joules(sections["sleep"][-3], sections["sleep"][-1])
        joules_system = util_get_joules(sections["system"][-3], sections["system"][-1])
        joules_modem = util_get_joules(sections["modem"][-3], sections["modem"][-1])
        joules_setup = util_get_joules(sections["setup"][-3], sections["setup"][-1])
        joules_sections = [
            joules_sum,
            joules_compute,
            joules_send,
            joules_sleep,
            joules_system,
            joules_modem,
            joules_setup,
        ]

        label_with_baskslash = " ".join(label.split("_")[-2:])

        times_grouped_by_protocol_dict[
            util_find_corresponding_protocol_label(label)
        ].append(
            f"{label_with_baskslash},"
            + f"{','.join([get_percent(time_section, time_total) for time_section in time_sections])}"
            + "\n"
        )

        joules_grouped_by_protocol_dict[
            util_find_corresponding_protocol_label(label)
        ].append(
            f"{label_with_baskslash},"
            + f"{','.join([get_percent(joules_section, joules_total) for joules_section in joules_sections])}"
            + "\n"
        )

    for output_time_string_list, output_power_string_list in zip(
        times_grouped_by_protocol_dict.values(),
        joules_grouped_by_protocol_dict.values(),
    ):
        output_time_string_list.sort(
            key=lambda o_string: util_sorter(o_string.split(",")[0].split(" "))
        )
        output_power_string_list.sort(
            key=lambda o_string: util_sorter(o_string.split(",")[0].split(" "))
        )

    for protocol, output_string in joules_grouped_by_protocol_dict.items():
        file_path = f"time_distribution_{protocol}.csv"
        file = open(file_path, "x")
        file.write(output_time_header + "".join(output_string))
        file.close()
    for protocol, output_string in joules_grouped_by_protocol_dict.items():
        file_path = f"power_distribution_{protocol}.csv"
        file = open(file_path, "x")
        file.write(output_power_header + "".join(output_string))
        file.close()
    return


def MAIN():
    """
    Dictionary outline:
    label -> section -> [
        index 0: count,
        index 1: average_current,
        index 2: total_current,
        index 3: time
    ]
    """
    data_dictionary = parse_file_data_to_dictionary()
    
    plt.rc('font', size=9) #controls default text size
    plt.rc('axes', titlesize=9) #fontsize of the title
    plt.rc('axes', labelsize=9) #fontsize of the x and y labels
    plt.rc('xtick', labelsize=9) #fontsize of the x tick labels
    plt.rc('ytick', labelsize=9) #fontsize of the y tick labels
    plt.rc('legend', fontsize=9) #fontsize of the legend

    plot_joules(data_dictionary)
    plot_time(data_dictionary)

    # log_theoretical_and_real_value_differences(data_dictionary)

    # detailed_analytics(data_dictionary)


if __name__ == "__main__":
    MAIN()
