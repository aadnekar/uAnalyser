import argparse
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

if args.path:
    SOURCE_FILE = args.path
else:
    SOURCE_FILE = "./results.csv"

RESULTS_DIR = "./plots"

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
PROTOCOL_SORTING_ORDER = {"no_tls": 1, "tls": 2, "no_tls_e2e": 3, "tls_e2e": 4}

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


def parse_file_data_to_dictionary():
    file = open(SOURCE_FILE, "r")
    print("Reading file containing fields:")
    print(file.readline())

    data_dictionary = {}

    for data_line in file.readlines():
        if len(data_line) < 5:
            print(data_line)
            continue
        label, section, count, average_current, total_current, time = data_line.split(
            ","
        )

        if data_dictionary.get(label) == None:
            data_dictionary[label] = {}

        data_dictionary[label][section] = [
            float(count),
            float(average_current),
            float(total_current),
            float(time),
        ]

    # print("VERBIOSA START")
    # for key, label_values in data_dictionary.items():
    #     print("\n\n#########",key,"#########")
    #     for section_key, section_value in label_values.items():
    #         print("#########",section_key,"#########")
    #         print(section_value)
    # print("VERBIOSA END")

    return data_dictionary


def util_from_uA_to_mA(uA: float):
    return uA / 1000


def util_from_ms_to_s(ms: float):
    return round(ms / 1000, 4)


def util_is_tls_label(label_snippet):
    return label_snippet == "tls"


def util_sorter(label_list):
    protocol_value = PROTOCOL_SORTING_ORDER["_".join(label_list[:-2])]
    operations = int(label_list[-2])
    payload = int(label_list[-1][:-1])
    return (operations, payload, protocol_value)


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
        # uA at the beginning, so average uA over all the samples
        average_uA, _, ms = label_values[section][1:4]
        # mA * mV = uW (divide by million to get Watt)
        # 10^-3 * 10^-3 = 10^-6
        Watt = (util_from_uA_to_mA(average_uA) * MILLI_VOLTAGE) / 10 ** 6
        # Watt * ms = mJ
        Joule = (Watt * ms) / 10 ** 3
        data.append(Joule)

    return sort_values_by_label(labels, data)


def get_average_power_of_section(data_dictionary, section):
    data = []
    labels = []
    for label, label_values in data_dictionary.items():
        labels.append(label)
        # uA at the beginning, so average uA over all the samples
        average_uA, _, ms = label_values[section][1:4]
        # mA * mV = uW (divide by million to get Watt)
        # 10^-3 * 10^-3 = 10^-6
        Watt = (util_from_uA_to_mA(average_uA) * MILLI_VOLTAGE) / 10 ** 6
        data.append(Watt)

    return sort_values_by_label(labels, data)


def plot_total(data_dictionary):
    labels = get_labels(data_dictionary)
    list_of_total = get_joules_of_section(data_dictionary, SECTIONS[TOTAL])

    print(labels)
    print(list_of_total)

    width = 0.75
    x = np.arange(start=0, stop=len(data_dictionary))

    fig, ax = plt.subplots(figsize=(4, 3), constrained_layout=True)

    ax.bar(x, list_of_total, width)

    ax.set_xticks(x)
    ax.set_xticklabels(labels)

    plt.show()


def plot_joules_with_sectors_stacked_single(data_dictionary):
    labels = get_labels(data_dictionary)
    labels = [label[len("no_tls_") :] for _, label in enumerate(labels)]

    section_labels = []
    sections = [
        get_joules_of_section(data_dictionary, section)
        for section in SECTIONS.values()
        if section != SECTIONS[TOTAL]
    ]
    section_labels = [label for label in SECTIONS.values() if label != SECTIONS[TOTAL]]

    width = 0.5
    x = np.arange(len(labels))

    fig, ax = plt.subplots(figsize=(4, 3), constrained_layout=True)

    accumulated = [0] * len(labels)

    for index, (section, section_label) in enumerate(zip(sections, section_labels)):
        # no_tls = [sample for index, sample in enumerate(section) if index % 2 == 0]
        # tls = [sample for index, sample in enumerate(section) if index % 2 != 0]

        ax.bar(
            x - width / 2,
            section,
            width,
            bottom=accumulated,
            label=section_label,
            color=COLORS[index],
        )
        # ax.bar(x + width / 2, tls, width, bottom=tls_accumulated, color=COLORS[index])

        accumulated = [
            accumulated + sample for accumulated, sample in zip(accumulated, section)
        ]

    ax.set_ylabel("Energy consumption (Joule)")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.legend(bbox_to_anchor=(0, 1, 1, 0), loc="lower left", mode="expand", ncol=2)

    plt.xticks(rotation=-45)
    plt.show()


######## ENERGY SINGLE ########


def plot_joules_single_section_main(data_dictionary):
    labels = get_labels(data_dictionary)
    labels = [label[len("no_tls_") :] for _, label in enumerate(labels)]

    section_labels = []
    sections_energy = [
        get_joules_of_section(data_dictionary, section)
        for section in SECTIONS.values()
        if section != SECTIONS[TOTAL]
    ]
    sections_power = [
        get_average_power_of_section(data_dictionary, section)
        for section in SECTIONS.values()
        if section != SECTIONS[TOTAL]
    ]
    section_labels = [label for label in SECTIONS.values() if label != SECTIONS[TOTAL]]

    for section_power, section_energy, section_label in zip(
        sections_power, sections_energy, section_labels
    ):
        plot_joules_single_section_single_TLS_configuration(
            section_label, section_energy, labels
        )
        plot_average_power_single_TLS_configration(section_label, section_power, labels)


def plot_joules_single_section_single_TLS_configuration(
    section_label, section_data, labels
):
    width = 1
    x = np.arange(len(labels)) * 2
    fig, ax = plt.subplots(figsize=(4, 3), constrained_layout=True)
    ax.set_ylabel("Energy consumption (Joule)")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    plt.xticks(rotation=-90)

    ax.bar(x, section_data, width)

    plt.savefig(
        f"plots/{section_label}-energy.png",
        transparent=False,
        orientation="portrait",
    )


def plot_average_power_single_TLS_configration(section_label, section_data, labels):
    width = 1
    x = np.arange(len(labels)) * 2
    fig, ax = plt.subplots(figsize=(4, 3), constrained_layout=True)
    ax.set_ylabel("Average Power (Watt)")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    plt.xticks(rotation=-90)

    ax.bar(x, section_data, width)

    plt.savefig(
        f"plots/{section_label}-average-power.png",
        transparent=False,
        orientation="portrait",
    )


######## ENERGY SINGLE END ########

######## TIME SINGLE ########


def plot_time_single_section_main(data_dictionary):
    labels = get_labels(data_dictionary)
    labels = [label[len("no_tls_") :] for _, label in enumerate(labels)]

    section_labels = []
    sections = [
        get_time_of_section(data_dictionary, section)
        for section in SECTIONS.values()
        if section != SECTIONS[TOTAL]
    ]
    section_labels = [label for label in SECTIONS.values() if label != SECTIONS[TOTAL]]

    for section_data, section_label in zip(sections, section_labels):
        plot_time_single_section_single_TLS_configuration(
            section_label, section_data, labels
        )


def plot_time_single_section_single_TLS_configuration(
    section_label, section_data, labels
):
    width = 1
    x = np.arange(len(labels)) * 2
    fig, ax = plt.subplots(figsize=(4, 3), constrained_layout=True)
    ax.set_ylabel("Time (Seconds)")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    plt.xticks(rotation=-90)

    ax.bar(x, section_data, width)

    plt.savefig(
        f"plots/{section_label}-time.png",
        transparent=False,
        orientation="portrait",
    )


######## TIME SINGLE END ########


def util_filter_labels(labels, filters: list):
    return [
        label
        for label in labels
        if all([_filter in label.split(" ") for _filter in filters])
    ]


def plot_joules_with_sectors_stacked(data_dictionary):
    all_labels = [
        " ".join(label.split(" ")[1:])
        for label in util_filter_labels(ALL_CONFIGURATION_LABELS, ["tls"])
    ]

    for number_of_operations in OPERATIONS:
        labels = util_filter_labels(all_labels, filters=[number_of_operations])
        x_labels = list(
            chain.from_iterable(
                [
                    ("no tls", "tls", f"\n{label}", "no tls e2e", "tls e2e")
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
        fig, ax = plt.subplots(figsize=(14, 6), constrained_layout=True)

        no_tls_accumulated = [0] * len(labels)
        tls_accumulated = [0] * len(labels)
        no_tls_e2e_accumulated = [0] * len(labels)
        tls_e2e_accumulated = [0] * len(labels)
        for index, section in enumerate(SECTIONS.values()):
            # if section == SECTIONS[TOTAL] or section == SECTIONS[SETUP]:
            if section != SECTIONS[COMPUTE]:
                continue

            joules = get_joules_of_section(
                data_dictionary, section, filters=[number_of_operations]
            )

            no_tls_joules = [value for value in joules[0::4]]
            tls_joules = [value for value in joules[1::4]]
            no_tls_e2e_joules = [value for value in joules[2::4]]
            tls_e2e_joules = [value for value in joules[3::4]]

            ax.bar(
                x - width - width / 2,
                no_tls_joules,
                width,
                bottom=no_tls_accumulated,
                color=COLORS[index],
                label=section,
            )
            ax.bar(
                x - width / 2,
                tls_joules,
                width,
                bottom=tls_accumulated,
                color=COLORS[index],
            )

            ax.bar(
                x + width / 2,
                no_tls_e2e_joules,
                width,
                bottom=no_tls_e2e_accumulated,
                color=COLORS[index],
            )

            ax.bar(
                x + width + width / 2,
                tls_e2e_joules,
                width,
                bottom=tls_e2e_accumulated,
                color=COLORS[index],
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

        ax.set_ylabel("Energy consumption (Joule)")
        plt.xticks(xticks, x_labels)
        # plt.xticks(rotation=-45)

        ax.legend(bbox_to_anchor=(0, 1, 1, 0), loc="lower left", mode="expand", ncol=2)

        plt.savefig(
            f"plots/energy_stacked_{number_of_operations}-operations.png",
            transparent=False,
            orientation="portrait",
        )


def plot_time_with_sectors_stacked(data_dictionary):
    all_labels = [
        " ".join(label.split(" ")[1:])
        for label in util_filter_labels(ALL_CONFIGURATION_LABELS, ["tls"])
    ]

    for number_of_operations in OPERATIONS:

        labels = util_filter_labels(all_labels, filters=[number_of_operations])
        x_labels = list(
            chain.from_iterable(
                [
                    ("no tls", "tls", f"\n{label}", "no tls e2e", "tls e2e")
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
        fig, ax = plt.subplots(figsize=(14, 6), constrained_layout=True)

        no_tls_accumulated = [0] * len(labels)
        tls_accumulated = [0] * len(labels)
        no_tls_e2e_accumulated = [0] * len(labels)
        tls_e2e_accumulated = [0] * len(labels)
        for index, section in enumerate(SECTIONS.values()):
            if section == SECTIONS[TOTAL]:
                continue

            times = get_time_of_section(
                data_dictionary, section, filters=[number_of_operations]
            )

            no_tls_times = [value for value in times[0::4]]
            tls_times = [value for value in times[1::4]]
            no_tls_e2e_times = [value for value in times[2::4]]
            tls_e2e_times = [value for value in times[3::4]]

            ax.bar(
                x - width - width/2,
                no_tls_times,
                width,
                bottom=no_tls_accumulated,
                color=COLORS[index],
                label=section,
            )
            ax.bar(
                x - width / 2,
                tls_times,
                width,
                bottom=tls_accumulated,
                color=COLORS[index],
            )
            ax.bar(
                x + width / 2,
                no_tls_e2e_times,
                width,
                bottom=no_tls_e2e_accumulated,
                color=COLORS[index],
            )
            ax.bar(
                x + width + width/2,
                tls_e2e_times,
                width,
                bottom=tls_e2e_accumulated,
                color=COLORS[index],
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

        ax.set_ylabel("Time consumption (Seconds)")
        plt.xticks(xticks, x_labels)
        # plt.xticks(rotation=-45)
        axXTicks = ax.get_xticks()
        axlabels = ax.get_xticklabels()
        for index in range(0, len(axlabels), 3):
            # axlabels[axlabel_index].set_rotation(45)
            print(axXTicks[index])
            print(axlabels[index])
            # axlabels[index].major = False
            # axlabels[axlabel_index + 2].set_rotation(45)

        ax.legend(bbox_to_anchor=(0, 1, 1, 0), loc="lower left", mode="expand", ncol=2)

        plt.savefig(
            f"plots/time_stacked_{number_of_operations}-operations.png",
            transparent=False,
            orientation="portrait",
        )


def plot_time_payload_relation(data_dictionary, section):
    """
    Should line up and graph the difference of processing time with regards to payload size
    """

    labels = get_payload_labels(data_dictionary)
    data = get_time_of_section(data_dictionary, section)

    for sample, label in zip(data, labels):
        print(label, "<-------->", sample)

    width = 0.5
    fig, ax = plt.subplots(figsize=(4, 3), constrained_layout=True)
    x = np.arange(len(data_dictionary))

    ax.bar(x, data, width)

    ax.set_ylabel("Time")
    ax.set_xlabel("Payload Size")

    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    # ax.legend(bbox_to_anchor=(0, 1, 1, 0), loc="lower left", mode="expand", ncol=2)

    plt.xticks(rotation=-45)
    plt.show()


def test_label_plotting():
    values = [50, 40, 60, 90, 30, 60]
    values_more = [10, 15, 10, 15, 10, 15]
    conf = ["no_tls", "tls"]
    payload_label = ["256B", "708B", "1024B"]
    sections = ["Values", "More Values"]

    width = 0.5
    x = np.arange(len(values) / 2) * 2
    spaces = list(chain.from_iterable([(i - width / 2, i, i + width / 2) for i in x]))

    fig, ax = plt.subplots(figsize=(4, 3), constrained_layout=True)

    values_1 = [val for val in values[0::2]]
    values_2 = [val for val in values[1::2]]
    more_values_1 = [val for val in values_more[0::2]]
    more_values_2 = [val for val in values_more[1::2]]

    ax.bar(x - width / 2, values_1, width, color=COLORS[0], label=sections[0])
    ax.bar(x + width / 2, values_2, width, color=COLORS[0])
    ax.bar(
        x - width / 2,
        more_values_1,
        width,
        bottom=values_1,
        color=COLORS[1],
        label=sections[1],
    )
    ax.bar(x + width / 2, more_values_2, width, bottom=values_2, color=COLORS[1])

    x_labels = list(
        chain.from_iterable(
            [(conf[0], f"\n{label}", conf[1]) for label in payload_label]
        )
    )
    # x_labels = [f"{conf[0]}{' '*8}{conf[1]}\n{' '*8}{label}" for label in payload_label]
    plt.xticks(spaces, x_labels)
    # ax.set_xticks(x)

    plt.legend()
    plt.show()


def test_spaces():
    width = 0.5
    x = np.arange(3) * 2
    print(x)

    x_left = np.linspace(x[0] - width / 2, x[-1] - width / 2, len(x))
    x_right = np.linspace(x[0] + width / 2, x[-1] + width / 2, len(x))

    spaces = [(i - width / 2, i, i + width / 2) for i in x]
    spaces2 = list(chain.from_iterable([(i - width / 2, i, i + width / 2) for i in x]))

    print(spaces)
    print(spaces2)

    print(len(x))


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

    # plot_total(data_dictionary)
    # plot_joules_with_sectors_stacked_single(data_dictionary)
    plot_joules_with_sectors_stacked(data_dictionary)
    plot_time_with_sectors_stacked(data_dictionary)

    # plot_joules_single_section_main(data_dictionary)
    # plot_time_single_section_main(data_dictionary)

    # plot_time_payload_relation(data_dictionary, SECTIONS[SEND])
    # plot_time_payload_relation(data_dictionary, SECTIONS[MODEM])

    # test_label_plotting()
    # test_spaces()

    # log_theoretical_and_real_value_differences(data_dictionary)


if __name__ == "__main__":
    MAIN()
