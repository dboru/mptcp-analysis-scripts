#! /usr/bin/python
# -*- coding: utf-8 -*-
#
#  Copyright 2015 Matthieu Baerts & Quentin De Coninck
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

##################################################
##                   IMPORTS                    ##
##################################################

import argparse
import common as co
import matplotlib
# Do not use any X11 backend
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import mptcp
import numpy as np
import os
import os.path
import pickle
import tcp
import sys

##################################################
##                  CONSTANTS                   ##
##################################################

# The default stat directory
DEF_STAT_DIR = 'stats'

##################################################
##                  ARGUMENTS                   ##
##################################################

parser = argparse.ArgumentParser(
    description="Summarize stat files generated by analyze")
parser.add_argument("-s",
                    "--stat", help="directory where the stat files are stored", default=DEF_STAT_DIR)
parser.add_argument("-a",
                    "--app", help="application results to summarize", default="")
parser.add_argument(
    "time", help="aggregate data in specified time, in format START,STOP")

args = parser.parse_args()

split_agg = args.time.split(',')

if not len(split_agg) == 2 or not co.is_number(split_agg[0]) or not co.is_number(split_agg[1]):
    print("The aggregation argument is not well formatted", file=sys.stderr)
    parser.print_help()
    exit(1)

start_time = split_agg[0]
stop_time = split_agg[1]

if int(start_time) > int(stop_time):
    print("The start time is posterior to the stop time", file=sys.stderr)
    parser.print_help()
    exit(2)

stat_dir_exp = os.path.abspath(os.path.expanduser(args.stat))

##################################################
##                 GET THE DATA                 ##
##################################################

co.check_directory_exists(stat_dir_exp)
connections = {}
for dirpath, dirnames, filenames in os.walk(stat_dir_exp):
    for fname in filenames:
        if args.app in fname:
            try:
                stat_file = open(os.path.join(dirpath, fname), 'r')
                connections[fname] = pickle.load(stat_file)
                stat_file.close()
            except IOError as e:
                print(str(e) + ': skip stat file ' + fname, file=sys.stderr)

##################################################
##               PLOTTING RESULTS               ##
##################################################


def get_experiment_condition(fname):
    """ Return a string of the format protocol_condition (e.g. tcp_both4TCD100m) """
    app_index = fname.index(args.app)
    dash_index = fname.index("-")
    end_index = fname[:dash_index].rindex("_")
    return fname[:app_index] + fname[app_index + len(args.app) + 1:end_index]


def count_interesting_connections(data):
    """ Return the number of interesting connections in data """
    count = 0
    tot = 0
    for k, v in data.iteritems():
        if isinstance(v, mptcp.MPTCPConnection):
            for subflow_id, flow in v.flows.iteritems():
                if flow.attr[co.IF]:
                    count += 1
                if flow.attr[co.DADDR]:
                    tot += 1

        elif isinstance(v, tcp.TCPConnection):
            # Check the key k
            # An interesting flow has an IF field
            if v.flow.attr[co.IF]:
                count += 1
            # All flows have a DADDR field
            if v.flow.attr[co.DADDR]:
                tot += 1
    return tot, count

def bar_chart_count_connections():
    aggl_res = {}
    tot_lbl = 'Total Connections'
    tot_flw_lbl = 'Total Flows'
    tot_int_lbl = 'Interesting Flows'
    label_names = ['Total Connections', 'Total Flows', 'Interesting Flows']
    color = ['b', 'g', 'r']
    ecolor = ['g', 'r', 'b']
    ylabel = 'Number of connections'
    title = 'Counts of total and interesting connections of ' + args.app
    graph_fname = "count_" + args.app + "_" + start_time + "_" + stop_time + '.pdf'

    # Need to agglomerate same tests
    for fname, data in connections.iteritems():
        condition = get_experiment_condition(fname)
        tot_flow, tot_int = count_interesting_connections(data)
        if condition in aggl_res:
            aggl_res[condition][tot_lbl] += [len(data)]
            aggl_res[condition][tot_flw_lbl] += [tot_flow]
            aggl_res[condition][tot_int_lbl] += [tot_int]
        else:
            aggl_res[condition] = {
                tot_lbl: [len(data)], tot_flw_lbl: [tot_flow], tot_int_lbl: [tot_int]}

    co.plot_bar_chart(aggl_res, label_names, color, ecolor, ylabel, title, graph_fname)


def bar_chart_bandwidth():
    aggl_res = {}
    tot_lbl = 'Bytes s2d'
    tot_flw_lbl = 'Bytes d2s'
    label_names = ['Bytes s2d', 'Bytes d2s']
    color = ['b', 'g']
    ecolor = ['g', 'r']
    ylabel = 'Bytes'
    title = 'Number of bytes transfered of ' + args.app
    graph_fname = "bytes_" + args.app + "_" + start_time + "_" + stop_time + '.pdf'

    # Need to agglomerate same tests
    for fname, data in connections.iteritems():
        condition = get_experiment_condition(fname)
        s2d = 0
        d2s = 0
        for conn_id, conn in data.iteritems():
            if isinstance(conn, mptcp.MPTCPConnection):
                data = conn.attr
            elif isinstance(conn, tcp.TCPConnection):
                data = conn.flow.attr
            here = [i for i in data.keys() if i in [co.BYTES_S2D, co.BYTES_D2S]]
            if not len(here) == 2:
                continue
            s2d += data[co.BYTES_S2D]
            d2s += data[co.BYTES_D2S]


        if condition in aggl_res:
            aggl_res[condition][tot_lbl] += [s2d]
            aggl_res[condition][tot_flw_lbl] += [d2s]
        else:
            aggl_res[condition] = {
                tot_lbl: [s2d], tot_flw_lbl: [d2s]}

    co.plot_bar_chart(aggl_res, label_names, color, ecolor, ylabel, title, graph_fname)


def bar_chart_bandwidth_smart():
    aggl_res = {}
    tot_lbl = 'Bytes s2d'
    tot_flw_lbl = 'Bytes d2s'
    label_names = ['Bytes s2d', 'Bytes d2s']
    color = ['b', 'g']
    ecolor = ['g', 'r']
    ylabel = 'Bytes'
    title = 'Number of bytes transfered of ' + args.app
    graph_fname = "bytes_" + args.app + "_" + start_time + "_" + stop_time + '.pdf'

    # Need to agglomerate same tests
    for fname, data in connections.iteritems():
        condition = get_experiment_condition(fname)
        for conn_id, conn in data.iteritems():
            if isinstance(conn, mptcp.MPTCPConnection):
                data = conn.attr
            elif isinstance(conn, tcp.TCPConnection):
                data = conn.flow.attr
            here = [i for i in data.keys() if i in [co.BYTES_S2D, co.BYTES_D2S]]
            if not len(here) == 2:
                continue
            if condition in aggl_res:
                aggl_res[condition][tot_lbl] += [data[co.BYTES_S2D]]
                aggl_res[condition][tot_flw_lbl] += [data[co.BYTES_D2S]]
            else:
                aggl_res[condition] = {
                    tot_lbl: [data[co.BYTES_S2D]], tot_flw_lbl: [data[co.BYTES_D2S]]}

    co.plot_bar_chart(aggl_res, label_names, color, ecolor, ylabel, title, graph_fname)


def bar_chart_bandwidth_s2d_interface():
    aggl_res = {}
    wifi = "Wi-Fi"
    rmnet = "rmnet"
    label_names = [wifi, rmnet]
    color = ['r', 'b']
    ecolor = ['b', 'r']
    ylabel = "Bytes"
    title = "Number of bytes transfered from source to destination by interface of " + args.app
    graph_fname = "iface_s2d_" + args.app + "_" + start_time + "_" + stop_time + '.pdf'

    for fname, data in connections.iteritems():
        condition = get_experiment_condition(fname)
        wifi_bytes = 0
        rmnet_bytes = 0
        for conn_id, conn in data.iteritems():
            if not co.S2D in conn.attr.keys():
                continue
            if co.WIFI in conn.attr[co.S2D].keys():
                wifi_bytes += conn.attr[co.S2D][co.WIFI]
            if co.RMNET in conn.attr[co.S2D].keys():
                rmnet_bytes += conn.attr[co.S2D][co.RMNET]

        if condition in aggl_res:
            aggl_res[condition][wifi] += [wifi_bytes]
            aggl_res[condition][rmnet] += [rmnet_bytes]
        else:
            aggl_res[condition] = {
                wifi: [wifi_bytes], rmnet: [rmnet_bytes]}

    co.plot_bar_chart(aggl_res, label_names, color, ecolor, ylabel, title, graph_fname)


def bar_chart_bandwidth_d2s_interface():
    aggl_res = {}
    wifi = "Wi-Fi"
    rmnet = "rmnet"
    label_names = [wifi, rmnet]
    color = ['r', 'b']
    ecolor = ['b', 'r']
    ylabel = "Bytes"
    title = "Number of bytes transfered from destination to source by interface of " + args.app
    graph_fname = "iface_d2s_" + args.app + "_" + start_time + "_" + stop_time + '.pdf'

    for fname, data in connections.iteritems():
        condition = get_experiment_condition(fname)
        wifi_bytes = 0
        rmnet_bytes = 0
        for conn_id, conn in data.iteritems():
            if not co.D2S in conn.attr.keys():
                continue
            if co.WIFI in conn.attr[co.D2S].keys():
                wifi_bytes += conn.attr[co.D2S][co.WIFI]
            if co.RMNET in conn.attr[co.D2S].keys():
                rmnet_bytes += conn.attr[co.D2S][co.RMNET]

        if condition in aggl_res:
            aggl_res[condition][wifi] += [wifi_bytes]
            aggl_res[condition][rmnet] += [rmnet_bytes]
        else:
            aggl_res[condition] = {
                wifi: [wifi_bytes], rmnet: [rmnet_bytes]}

    co.plot_bar_chart(aggl_res, label_names, color, ecolor, ylabel, title, graph_fname)


def bar_chart_duration():
    aggl_res = {}
    tot_int_lbl = 'Duration'
    label_names = ['Duration']
    color = ['r']
    ecolor = ['b']
    ylabel = 'Number of seconds'
    title = 'Time of connections of ' + args.app
    graph_fname = "duration_" + args.app + "_" + start_time + "_" + stop_time + '.pdf'

    # Need to agglomerate same tests
    for fname, data in connections.iteritems():
        condition = get_experiment_condition(fname)
        for conn_id, conn in data.iteritems():
            if isinstance(conn, mptcp.MPTCPConnection):
                data = conn.attr
            elif isinstance(conn, tcp.TCPConnection):
                data = conn.flow.attr
            here = [i for i in data.keys() if i in [co.DURATION]]
            if not len(here) == 1:
                continue
            if condition in aggl_res:
                aggl_res[condition][tot_int_lbl] += [data[co.DURATION]]
            else:
                aggl_res[condition] = {tot_int_lbl: [data[co.DURATION]]}

    co.plot_bar_chart(aggl_res, label_names, color, ecolor, ylabel, title, graph_fname)


def bar_chart_duration_all():
    aggl_res = {}
    tot_int_lbl = 'Duration'
    label_names = ['Duration']
    color = ['r']
    ecolor = ['b']
    ylabel = 'Number of seconds'
    title = 'Time of scenario of ' + args.app
    graph_fname = "duration_all_" + args.app + "_" + start_time + "_" + stop_time + '.pdf'

    # Need to agglomerate same tests
    for fname, data in connections.iteritems():
        condition = get_experiment_condition(fname)
        start = float("inf")
        stop = 0
        for conn_id, conn in data.iteritems():
            if isinstance(conn, mptcp.MPTCPConnection):
                for flow_id, flow in conn.flows.iteritems():
                    here = [i for i in flow.attr.keys() if i in [co.DURATION]]
                    if not len(here) == 1:
                            continue
                    start = min(start, flow.attr[co.START])
                    stop = max(stop, flow.attr[co.START] + flow.attr[co.DURATION])

            elif isinstance(conn, tcp.TCPConnection):
                here = [i for i in conn.flow.attr.keys() if i in [co.DURATION]]
                if not len(here) == 1:
                        continue
                start = min(start, conn.flow.attr[co.START])
                stop = max(stop, conn.flow.attr[co.START] + conn.flow.attr[co.DURATION])

        if stop - start >= 0:
            if condition in aggl_res:
                aggl_res[condition][tot_int_lbl] += [stop - start]
            else:
                aggl_res[condition] = {tot_int_lbl: [stop - start]}

    co.plot_bar_chart(aggl_res, label_names, color, ecolor, ylabel, title, graph_fname)

bar_chart_count_connections()
bar_chart_bandwidth()
bar_chart_duration()
bar_chart_bandwidth_s2d_interface()
bar_chart_bandwidth_d2s_interface()
bar_chart_duration_all()
print("End of summary")
