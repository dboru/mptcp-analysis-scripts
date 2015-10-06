#! /usr/bin/python
# -*- coding: utf-8 -*-
#
#  Copyright 2015 Quentin De Coninck
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#
#  To install on this machine: matplotlib, numpy

from __future__ import print_function

import argparse
import common as co
import common_graph as cog
import matplotlib
# Do not use any X11 backend
matplotlib.use('Agg')
matplotlib.rcParams['pdf.fonttype'] = 42
matplotlib.rcParams['ps.fonttype'] = 42
import matplotlib.pyplot as plt
import mptcp
import numpy as np
import os
import tcp

##################################################
##                  ARGUMENTS                   ##
##################################################

parser = argparse.ArgumentParser(
    description="Summarize stat files generated by analyze")
parser.add_argument("-s",
                    "--stat", help="directory where the stat files are stored", default=co.DEF_STAT_DIR + '_' + co.DEF_IFACE)
parser.add_argument('-S',
                    "--sums", help="directory where the summary graphs will be stored", default=co.DEF_SUMS_DIR + '_' + co.DEF_IFACE)
parser.add_argument("-d",
                    "--dirs", help="list of directories to aggregate", nargs="+")

args = parser.parse_args()
stat_dir_exp = os.path.abspath(os.path.expanduser(args.stat))
sums_dir_exp = os.path.abspath(os.path.expanduser(args.sums))
co.check_directory_exists(sums_dir_exp)

##################################################
##                 GET THE DATA                 ##
##################################################

connections = cog.fetch_valid_data(stat_dir_exp, args)
multiflow_connections, singleflow_connections = cog.get_multiflow_connections(connections)

##################################################
##               PLOTTING RESULTS               ##
##################################################


def plot(connections, multiflow_connections, sums_dir_exp):
    ALERT_DURATION = 3600
    ALERT_BYTES = 50000000
    data_duration = []
    subflows_duration = []
    data_bytes = []
    subflows_bytes = []
    data_packets = []
    color = 'red'
    base_graph_name_duration = "summary_cdf_duration"
    base_graph_path_duration = os.path.join(sums_dir_exp, base_graph_name_duration)
    base_graph_name_bytes = "summary_cdf_bytes"
    base_graph_path_bytes = os.path.join(sums_dir_exp, base_graph_name_bytes)
    max_duration = 0.0
    fname_max_duration = None
    conn_id_max_duration = None
    max_bytes = 0
    fname_max_bytes = None
    conn_id_max_bytes = None

    for fname, conns in connections.iteritems():
        for conn_id, conn in conns.iteritems():
            if isinstance(conn, mptcp.MPTCPConnection) and co.DURATION in conn.attr:
                duration = conn.attr[co.DURATION]
                bytes = 0
                data_pkts = 0
                for direction in co.DIRECTIONS:
                    bytes += conn.attr[direction][co.BYTES_MPTCPTRACE]
                    if co.BURSTS in conn.attr[direction]:
                        for flow_id, seq_burst, pkt_burst, duration, time in conn.attr[direction][co.BURSTS]:
                            data_pkts += pkt_burst

                if duration >= ALERT_DURATION:
                    print("DURATION", fname, conn_id, duration)
                if bytes >= ALERT_BYTES:
                    print("BYTES", fname, conn_id, bytes)

                if duration > max_duration:
                    max_duration = duration
                    fname_max_duration = fname
                    conn_id_max_duration = conn_id

                if bytes > max_bytes:
                    max_bytes = bytes
                    fname_max_bytes = fname
                    conn_id_max_bytes = conn_id

                data_duration.append(duration)
                data_bytes.append(bytes)
                data_packets.append(data_pkts)

                for flow_id, flow in conn.flows.iteritems():
                    if co.DURATION in flow.attr:
                        subflows_duration.append(flow.attr[co.DURATION])
                        subflow_bytes = 0
                        for direction in co.DIRECTIONS:
                            subflow_bytes += flow.attr[direction][co.BYTES_DATA]
                        subflows_bytes.append(subflow_bytes)


    # co.plot_cdfs_natural(data_duration, color, 'Seconds [s]', base_graph_path_duration)
    # co.plot_cdfs_natural(data_duration, color, 'Seconds [s]', base_graph_path_duration + '_log', xlog=True)
    print("MAX DURATION", max_duration, fname_max_duration, conn_id_max_duration)
    print("MAX BYTES", max_bytes, fname_max_bytes, conn_id_max_bytes)

    print("PERCENTAGE 0 s", len([x for x in data_duration if x <= 0.00001]) * 100.0 / len(data_duration))
    print("PERCENTAGE <=10 s", len([x for x in data_duration if x <= 10.0]) * 100.0 / len(data_duration))
    print("PERCENTAGE >=100 s", len([x for x in data_duration if x >= 100.0]) * 100.0 / len(data_duration))

    print("PERCENTAGE <= 1KB", len([x for x in data_bytes if x <= 1000]) * 100.0 / len(data_bytes))
    print("PERCENTAGE <= 2KB", len([x for x in data_bytes if x <= 2000]) * 100.0 / len(data_bytes))
    print("PERCENTAGE <= 5KB", len([x for x in data_bytes if x <= 5000]) * 100.0 / len(data_bytes))
    print("PERCENTAGE <= 10KB", len([x for x in data_bytes if x <= 10000]) * 100.0 / len(data_bytes))
    print("PERCENTAGE [9;11] B", len([x for x in data_bytes if x <= 11 and x >= 9]) * 100.0 / len(data_bytes))

    print("PERCENTAGE <= 2 packs", len([x for x in data_packets if x <= 2]) * 100.0 / len(data_packets))
    print("PERCENTAGE <= 3 packs", len([x for x in data_packets if x <= 3]) * 100.0 / len(data_packets))
    print("PERCENTAGE <= 5 packs", len([x for x in data_packets if x <= 5]) * 100.0 / len(data_packets))
    print("PERCENTAGE <= 10 packs", len([x for x in data_packets if x <= 10]) * 100.0 / len(data_packets))

    plt.figure()
    plt.clf()
    fig, ax = plt.subplots()

    graph_fname = os.path.splitext(base_graph_path_duration)[0] + "_cdf_log.pdf"
    sample = np.array(sorted(data_duration))
    sorted_array = np.sort(sample)
    yvals = np.arange(len(sorted_array)) / float(len(sorted_array))
    if len(sorted_array) > 0:
        # Add a last point
        sorted_array = np.append(sorted_array, sorted_array[-1])
        yvals = np.append(yvals, 1.0)
        ax.plot(sorted_array, yvals, color=color, linewidth=2, label="MPTCP Connections")

        # Shrink current axis's height by 10% on the top
        # box = ax.get_position()
        # ax.set_position([box.x0, box.y0,
        #                  box.width, box.height * 0.9])

    # sample = np.array(sorted(subflows_duration))
    # sorted_array = np.sort(sample)
    # yvals = np.arange(len(sorted_array)) / float(len(sorted_array))
    # if len(sorted_array) > 0:
    #     # Add a last point
    #     sorted_array = np.append(sorted_array, sorted_array[-1])
    #     yvals = np.append(yvals, 1.0)
    #     ax.plot(sorted_array, yvals, color='blue', linestyle='--', linewidth=2, label="Subflows")

        # Shrink current axis's height by 10% on the top
        # box = ax.get_position()
        # ax.set_position([box.x0, box.y0,
        #                  box.width, box.height * 0.9])

    ax.set_xscale('log')

    # Put a legend above current axis
    # ax.legend(loc='lower center', bbox_to_anchor=(0.5, 1.05), fancybox=True, shadow=True, ncol=ncol)
    ax.legend(loc='lower right')

    plt.xlabel('Time [s]', fontsize=24)
    plt.ylabel("CDF", fontsize=24)
    plt.savefig(graph_fname)
    plt.close('all')

    base_graph_path_duration_hist = os.path.splitext(base_graph_path_duration)[0] + '_hist'
    plt.figure()
    plt.hist(subflows_duration, bins=np.logspace(-3, 5, 81), log=True)
    plt.xlabel("Duration of connections [s]", fontsize=24)
    plt.ylabel("Connections", fontsize=24)
    plt.gca().set_xscale("log")
    plt.savefig(base_graph_path_duration_hist + "_log.pdf")
    plt.close()
    plt.figure()
    plt.hist(subflows_duration, bins=np.logspace(-3, 5, 81))
    plt.xlabel("Duration of connections [s]", fontsize=24)
    plt.ylabel("Connections", fontsize=24)
    # plt.gca().set_xscale("log")
    plt.savefig(base_graph_path_duration_hist + ".pdf")
    plt.close()

    plt.figure()
    plt.clf()
    fig, ax = plt.subplots()

    graph_fname = os.path.splitext(base_graph_path_bytes)[0] + "_cdf_log.pdf"
    sample = np.array(sorted(data_bytes))
    sorted_array = np.sort(sample)
    yvals = np.arange(len(sorted_array)) / float(len(sorted_array))
    if len(sorted_array) > 0:
        # Add a last point
        sorted_array = np.append(sorted_array, sorted_array[-1])
        yvals = np.append(yvals, 1.0)
        ax.plot(sorted_array, yvals, color=color, linewidth=2, label="MPTCP Connections")

        # Shrink current axis's height by 10% on the top
        # box = ax.get_position()
        # ax.set_position([box.x0, box.y0,
        #                  box.width, box.height * 0.9])

    # sample = np.array(sorted(subflows_bytes))
    # sorted_array = np.sort(sample)
    # yvals = np.arange(len(sorted_array)) / float(len(sorted_array))
    # if len(sorted_array) > 0:
    #     # Add a last point
    #     sorted_array = np.append(sorted_array, sorted_array[-1])
    #     yvals = np.append(yvals, 1.0)
    #     ax.plot(sorted_array, yvals, color='blue', linestyle='--', linewidth=2, label="Subflows")

        # Shrink current axis's height by 10% on the top
        # box = ax.get_position()
        # ax.set_position([box.x0, box.y0,
        #                  box.width, box.height * 0.9])

    ax.set_xscale('log')

    # Put a legend above current axis
    # ax.legend(loc='lower center', bbox_to_anchor=(0.5, 1.05), fancybox=True, shadow=True, ncol=ncol)
    ax.legend(loc='lower right')

    plt.xlabel('Bytes', fontsize=24)
    plt.ylabel("CDF", fontsize=24)
    plt.savefig(graph_fname)
    plt.close('all')

plot(connections, multiflow_connections, sums_dir_exp)
