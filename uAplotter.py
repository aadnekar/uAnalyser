import argparse
import numpy as np
import matplotlib.pyplot as plt

parser = argparse.ArgumentParser(
    description="Command line tool for plotting results from uAnalyser tool, authored by Ådne Karstad @aadnekar"
)

parser.add_argument(
    "--path",
    nargs="+",
    required=False,
    help="relative path to source file to analyse. Provide several path's to compare results.",
)
parser.add_argument(
    "--output",
    "-o",
    type=str,
    help="file path to output file",
)
args = parser.parse_args()

if args.path:
    SOURCE_FILE = args.path[0]
else:
    SOURCE_FILE = "./results.csv"
    # SOURCE_FILE = "./final_results9.csv"
if args.output:
    RESULTS_DIR = args.output
else:
    RESULTS_DIR = "./plots"


MILLI_VOLTAGE = 3.7 * 1000

# COLORS = ["#E8A87C", "#C38D9E", "#E27D60", "#41B3A3"]
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

# [pin, power, ms]
main_dict = {"on": [], "off": []}
startup_on = []
startup_off = []
simulated_activity_on = []
simulated_activity_off = []
system_activity_on = []
system_activity_off = []
sleep_on = []
sleep_off = []


def from_current_to_mW(uA_current: float):
    # Dette er watt = arbeid over tid
    # milli * milli = mikro, derfor divdere med 1000 for å få mW
    return round((from_uA_to_mA(uA_current) * MILLI_VOLTAGE) / 1000, 3)


def from_uA_to_mA(uA: float):
    return uA / 1000


def from_ms_to_s(ms: float):
    return round(ms / 1000, 3)


def readfile(filename: str):
    for index, line in enumerate(open(filename, "r")):
        if index == 0:
            continue

        # Remove \n and split data
        item_list = line[:-1].split(",")
        for index, item in enumerate(item_list):
            if index == 0:
                item_list[index] = item[len("csvdata/") : -len(".csv")]
            elif index == 1:
                item_list[index] = str(item)
            elif index == 2:
                item_list[index] = from_current_to_mW(float(item))
            elif index == 3:
                item_list[index] = from_ms_to_s(float(item))
        if "on" in item_list[0]:
            main_dict["on"].append(item_list)
        else:
            main_dict["off"].append(item_list)


def setup_section_data(tls="on"):
    global simulated_activity_on, simulated_activity_off
    global system_activity_on, system_activity_off
    global startup_on, startup_off
    global sleep_on, sleep_off

    simulated_activity_on = [
        p for p in [vals for vals in main_dict["on"]] if p[1] == "application"
    ]
    simulated_activity_off = [
        p for p in [vals for vals in main_dict["off"]] if p[1] == "application"
    ]

    system_activity_on = [
        p for p in [vals for vals in main_dict["on"]] if p[1] == "system"
    ]
    system_activity_off = [
        p for p in [vals for vals in main_dict["off"]] if p[1] == "system"
    ]

    startup_on = [p for p in [vals for vals in main_dict["on"]] if p[1] == "startup"]
    startup_off = [p for p in [vals for vals in main_dict["off"]] if p[1] == "startup"]

    sleep_on = [p for p in [vals for vals in main_dict["on"]] if p[1] == "sleep"]
    sleep_off = [p for p in [vals for vals in main_dict["off"]] if p[1] == "sleep"]

    # pin5 = [p for p in [vals for vals in main_dict[tls]] if p[1] == "pin5"]


def get_E_sorted_and_filtered_by(tls: str, constant: str, l: list):
    return [
        # elem[2] = mW
        # elem[3] = s
        # 10^3 * 10^3 = 10^6 ==> mJoule / 1000 => Joule
        (elem[2] * elem[3]) / 1000
        for elem in sorted(
            l, key=lambda elems: get_label_value(tls, constant, elems[0])
        )
        if constant in elem[0]
    ]


def get_time_sorted_and_filtered_by(tls: str, constant: str, l: list):
    return [
        elem[3]
        for elem in sorted(
            l, key=lambda elems: get_label_value(tls, constant, elems[0])
        )
        if constant in elem[0]
    ]


def get_label(tls: str, constant: str, label: str):
    if "B" in constant:
        return label[len(f"{tls}_{constant}_") :]
    else:
        return label[len(f"{tls}_") : -len(f"_{constant}")]


def get_label_value(tls: str, constant: str, label: str):
    if "B" in constant:
        return int(label[len(f"{tls}_{constant}_") : -len("I")])
    else:
        return int(label[len(f"{tls}_") : -len(f"B_{constant}")])


def plot_E_grouped(constant: str):
    tls_on = "on"
    tls_off = "off"

    local_startup_on = get_E_sorted_and_filtered_by(tls_on, constant, startup_on)
    local_startup_off = get_E_sorted_and_filtered_by(tls_off, constant, startup_off)

    local_simulated_activity_on = get_E_sorted_and_filtered_by(
        tls_on, constant, simulated_activity_on
    )
    local_simulated_activity_off = get_E_sorted_and_filtered_by(
        tls_off, constant, simulated_activity_off
    )

    local_system_activity_on = get_E_sorted_and_filtered_by(
        tls_on, constant, system_activity_on
    )
    local_system_activity_off = get_E_sorted_and_filtered_by(
        tls_off, constant, system_activity_on
    )

    local_sleep_on = get_E_sorted_and_filtered_by(tls_on, constant, sleep_on)
    local_sleep_off = get_E_sorted_and_filtered_by(tls_off, constant, sleep_off)

    labels = [
        get_label(tls_on, constant, elem[0])
        for elem in sorted(
            simulated_activity_on,
            key=lambda elems: get_label_value(tls_on, constant, elems[0]),
        )
        if constant in elem[0]
    ]
    width = 0.75
    x = np.arange(len(labels)) * 2

    fig, ax = plt.subplots(figsize=(4, 3), constrained_layout=True)

    ax.bar(x - width / 2, local_startup_on, width, label="Startup", color=COLORS[0])
    ax.bar(x + width / 2, local_startup_off, width, color=COLORS[0])

    ax.bar(
        x - width / 2,
        local_simulated_activity_on,
        width,
        label="Application",
        color=COLORS[1],
        bottom=local_startup_on,
    )
    ax.bar(
        x + width / 2,
        local_simulated_activity_off,
        width,
        # label="inner",
        color=COLORS[1],
        bottom=local_startup_off,
    )

    ax.bar(
        x - width / 2,
        local_system_activity_on,
        width,
        label="System",
        color=COLORS[2],
        bottom=[a + b for a, b in zip(local_startup_on, local_simulated_activity_on)],
    )
    ax.bar(
        x + width / 2,
        local_system_activity_off,
        width,
        # label="outer",
        color=COLORS[2],
        bottom=[a + b for a, b in zip(local_startup_off, local_simulated_activity_off)],
    )

    ax.bar(
        x - width / 2,
        local_sleep_on,
        width,
        label="idle",
        color=COLORS[4],
        bottom=[
            a + b + c
            for a, b, c in zip(
                local_startup_on, local_simulated_activity_on, local_system_activity_on
            )
        ],
    )
    ax.bar(
        x + width / 2,
        local_sleep_off,
        width,
        # label="sleep",
        color=COLORS[4],
        bottom=[
            a + b + c
            for a, b, c in zip(
                local_startup_off,
                local_simulated_activity_off,
                local_system_activity_off,
            )
        ],
    )

    ax.set_ylabel("Energy consumption (Joule)")

    x_coords = []
    x = [x_coords.extend([i - (width / 2), i, i + (width / 2)]) for i in x]
    print(x_coords)

    ax.set_xticks(x_coords)
    plt.xticks(rotation=90)

    x_labels = []
    for l in labels:
        x_labels.extend(["On", l, "Off"])

    print(x_labels)

    ax.set_xticklabels(x_labels)

    labels = ax.get_xticklabels()
    for label_i in range(1, len(labels), 3):
        labels[label_i].set_fontweight("bold")

    ax.legend(bbox_to_anchor=(0, 1, 1, 0), loc="lower left", mode="expand", ncol=2)

    plt.savefig(
        f"{RESULTS_DIR}/grouped_{constant}.png",
        transparent=True,
        orientation="portrait",
    )


def plot_time_grouped(constant: str):
    # Data wanted in the plot
    tls_on = "on"
    tls_off = "off"

    local_startup_on = get_time_sorted_and_filtered_by(tls_on, constant, startup_on)
    local_startup_off = get_time_sorted_and_filtered_by(tls_off, constant, startup_off)

    local_simulated_activity_on = get_time_sorted_and_filtered_by(
        tls_on, constant, simulated_activity_on
    )
    local_simulated_activity_off = get_time_sorted_and_filtered_by(
        tls_off, constant, simulated_activity_off
    )

    local_system_activity_on = get_time_sorted_and_filtered_by(
        tls_on, constant, system_activity_on
    )
    local_system_activity_off = get_time_sorted_and_filtered_by(
        tls_off, constant, system_activity_off
    )

    local_sleep_on = get_time_sorted_and_filtered_by(tls_on, constant, sleep_on)
    local_sleep_off = get_time_sorted_and_filtered_by(tls_off, constant, sleep_off)

    labels = [
        get_label(tls_on, constant, elem[0])
        for elem in sorted(
            simulated_activity_on,
            key=lambda elems: get_label_value(tls_on, constant, elems[0]),
        )
        if constant in elem[0]
    ]

    # Startplotting
    width = 0.5
    x = np.arange(len(labels))
    print(x)

    fig, ax = plt.subplots(figsize=(4, 3), constrained_layout=True)

    ax.bar(x - width / 2, local_startup_on, width, label="Startup", color=COLORS[0])
    ax.bar(x + width / 2, local_startup_off, width, color=COLORS[0])

    ax.bar(
        x - width / 2,
        local_simulated_activity_on,
        width,
        label="Application",
        color=COLORS[1],
        bottom=local_startup_on,
    )
    ax.bar(
        x + width / 2,
        local_simulated_activity_off,
        width,
        # label="inner",
        color=COLORS[1],
        bottom=local_startup_off,
    )

    ax.bar(
        x - width / 2,
        local_system_activity_on,
        width,
        label="System",
        color=COLORS[2],
        bottom=[a + b for a, b in zip(local_startup_on, local_simulated_activity_on)],
    )
    ax.bar(
        x + width / 2,
        local_system_activity_off,
        width,
        # label="outer",
        color=COLORS[2],
        bottom=[a + b for a, b in zip(local_startup_off, local_simulated_activity_off)],
    )

    ax.bar(
        x - width / 2,
        local_sleep_on,
        width,
        label="idle",
        color=COLORS[4],
        bottom=[
            a + b + c
            for a, b, c in zip(
                local_startup_on, local_simulated_activity_on, local_system_activity_on
            )
        ],
    )
    ax.bar(
        x + width / 2,
        local_sleep_off,
        width,
        # label="after",
        color=COLORS[4],
        bottom=[
            a + b + c
            for a, b, c in zip(
                local_startup_off,
                local_simulated_activity_off,
                local_system_activity_off,
            )
        ],
    )

    ax.set_ylabel("Time (seconds)")

    x_coords = []
    x = [x_coords.extend([i - (width / 2), i, i + (width / 2)]) for i in x]
    print(x_coords)

    ax.set_xticks(x_coords)
    plt.xticks(rotation=90)

    x_labels = []
    for l in labels:
        x_labels.extend(["On", l, "Off"])

    print(x_labels)

    ax.set_xticklabels(x_labels)

    labels = ax.get_xticklabels()
    for label_i in range(1, len(labels), 3):
        labels[label_i].set_fontweight("bold")

    ax.legend(bbox_to_anchor=(0, 1, 1, 0), loc="lower left", mode="expand", ncol=2)

    plt.savefig(
        f"{RESULTS_DIR}/grouped_time_{constant}.png",
        transparent=True,
        orientation="portrait",
    )


def plot_normalised_Energy_consumption(index: int, constant: str):
    tls_on = "on"
    tls_off = "off"

    local_startup_on = get_E_sorted_and_filtered_by(tls_on, constant, startup_on)
    local_startup_off = get_E_sorted_and_filtered_by(tls_off, constant, startup_off)

    local_simulated_on = get_E_sorted_and_filtered_by(
        tls_on, constant, simulated_activity_on
    )
    local_simulated_off = get_E_sorted_and_filtered_by(
        tls_off, constant, simulated_activity_off
    )

    local_system_on = get_E_sorted_and_filtered_by(tls_on, constant, system_activity_on)
    local_system_off = get_E_sorted_and_filtered_by(
        tls_off, constant, system_activity_on
    )

    local_idle_on = get_E_sorted_and_filtered_by(tls_on, constant, sleep_on)
    local_idle_off = get_E_sorted_and_filtered_by(tls_off, constant, sleep_off)

    normalized_on = [
        local_startup_on[index] / local_startup_on[index],
        local_simulated_on[index] / local_simulated_on[index],
        local_system_on[index] / local_system_on[index],
        local_idle_on[index] / local_idle_on[index],
    ]
    normalized_off = [
        local_startup_off[index] / local_startup_on[index],
        local_simulated_off[index] / local_simulated_on[index],
        local_system_off[index] / local_system_on[index],
        local_idle_off[index] / local_idle_on[index],
    ]

    labels = ["Startup", "Application", "System", "idle"]

    width = 0.75
    x = np.arange(len(normalized_on))

    fig, ax = plt.subplots(figsize=(4, 3), constrained_layout=True)
    plt.rcParams.update({"font.size": 11})

    ax.bar(
        x - width / 2,
        normalized_on,
        width,
        label="TLS",
        color=COLORS[0],
    )
    ax.bar(
        x + width / 2,
        normalized_off,
        width,
        label="NoTLS",
        color=COLORS[2],
    )

    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    plt.xticks(rotation=90)

    ax.legend(bbox_to_anchor=(0, 1, 1, 0), loc="lower left", mode="expand", ncol=2)

    ax.set_ylabel("Normalized Energy")

    file_name_constant = [
        get_label(tls_on, constant, elem[0])
        for elem in sorted(
            simulated_activity_on,
            key=lambda elems: get_label_value(tls_on, constant, elems[0]),
        )
        if constant in elem[0]
    ][index]

    plt.savefig(
        f"{RESULTS_DIR}/normalized_{file_name_constant}.png",
        transparent=True,
        orientation="portrait",
    )


def profile_plot(filename: str):
    time = []
    current = []

    for index, measure in enumerate(open(filename, "r")):
        if index == 0:
            continue

        measure = measure[0 : -len("\n")].split(",")
        if measure[2][3] == "1":
            time.append(float(measure[0]))
            current.append(float(measure[1]))

    fig, ax = plt.subplots(figsize=(4, 3))

    ax.plot(time, current)

    plt.savefig(f"./power_profile_plots/1.png")


if __name__ == "__main__":

    if args.path:
        profile_plot(SOURCE_FILE)
        # print(SOURCE_FILE)
    else:
        readfile(SOURCE_FILE)
        setup_section_data()
        for constant in ["1000I", "3000B"]:
            plot_E_grouped(constant)
            plot_time_grouped(constant)

        for constant in ["1000I", "3000B"]:
            for index in range(3):
                plot_normalised_Energy_consumption(index=index, constant=constant)
