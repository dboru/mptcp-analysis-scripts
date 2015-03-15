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
import sys
import tcp
import time

##################################################
##                  ARGUMENTS                   ##
##################################################

parser = argparse.ArgumentParser(
    description="Summarize stat files generated by analyze")
parser.add_argument("-s",
                    "--stat", help="directory where the stat files are stored", default=co.DEF_STAT_DIR+'_'+co.DEF_IFACE)
parser.add_argument('-S',
                    "--sums", help="directory where the summary graphs will be stored", default=co.DEF_SUMS_DIR+'_'+co.DEF_IFACE)
parser.add_argument("-a",
                    "--app", help="application results to summarize", default="")
parser.add_argument(
    "time", help="aggregate data in specified time, in format START,STOP")
parser.add_argument("-d",
                    "--dirs", help="list of directories of dataset 1 to aggregate", nargs="+")
parser.add_argument("-t",
                    "--dirs-two", help="list of directories of dataset 2 to aggregate", nargs="+")
parser.add_argument("-c",
                    "--cond", help="(exact) condition to show", default="")
parser.add_argument("-p",
                    "--prot", help="(exact) protocol to show", default="")
parser.add_argument("-r",
                    "--remove", help="if set, remove outliers from dataset", action="store_true")
parser.add_argument("-l",
                    "--load-apps", help="list of applications whose data is loaded", nargs="+")
parser.add_argument("-U",
                    "--upload", help="only load upload intensive apps", action="store_true")
parser.add_argument("-D",
                    "--download", help="only load download intensive apps", action="store_true")

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
sums_dir_exp = os.path.abspath(os.path.expanduser(args.sums))

co.check_directory_exists(sums_dir_exp)

if args.prot or args.cond:
    sums_dir_exp = os.path.join(sums_dir_exp, args.prot + args.cond)
    co.check_directory_exists(sums_dir_exp)

apps_to_load = []
if args.load_apps:
    apps_to_load = args.load_apps
elif args.upload:
    apps_to_load = ['drive', 'dropbox', 'facebook', 'messenger']
elif args.download:
    apps_to_load = ['dailymotion', 'firefox', 'spotify', 'youtube']

##################################################
##                 GET THE DATA                 ##
##################################################


def get_app_name_index(fname):
    """ Return the app name index in fname """
    dash_index = fname.index("-")
    us_1_index = fname[:dash_index].rindex("_")
    us_2_index = fname[:us_1_index].rindex("_")
    us_3_index = fname[:us_2_index].rindex("_")
    return us_3_index + 1, us_2_index


def get_experiment_condition(fname):
    """ Return a string of the format protocol_condition (e.g. tcp_both4TCD100m) """
    app_index, end_app_index = get_app_name_index(fname)
    dash_index = fname.index("-")
    end_index = fname[:dash_index].rindex("_")
    return fname[:app_index] + fname[end_app_index + 1:end_index]


def get_app_name(fname):
    """ Return a string of the name of the application """
    dash_index = fname.index("-")
    us_1_index = fname[:dash_index].rindex("_")
    us_2_index = fname[:us_1_index].rindex("_")
    us_3_index = fname[:us_2_index].rindex("_")
    return fname[us_3_index + 1:us_2_index]


def is_app_name(fname, app_name):
    """ Return if string of the name of the application is app_name """
    if not args.app:
        return True
    if app_name in fname:
        app_index = fname.index(app_name)
        end_index = fname[app_index:].index("_")
        return fname[app_index:(app_index + end_index)] == app_name
    return False


def check_in_list(dirpath, dirs):
    """ Check if dirpath is one of the dir in dirs, True if dirs is empty """
    if not dirs:
        return True
    return os.path.basename(dirpath) in dirs


def check_conditions(fname):
    """ Check if conditions are respected to take into account the trace """
    condition = get_experiment_condition(fname)
    return condition.startswith(args.prot) and condition.endswith(args.cond)


def fetch_data(dir_exp):
    co.check_directory_exists(dir_exp)
    dico = {"dirs": {}, "dirs_two": {}}
    for dirpath, dirnames, filenames in os.walk(dir_exp):
        if check_in_list(dirpath, args.dirs) or check_in_list(dirpath, args.dirs_two):
            for fname in filenames:
                fname_date = co.get_date_as_int(fname)
                if is_app_name(fname, args.app) and (fname_date and (int(start_time) <= fname_date <= int(stop_time))) and check_conditions(fname) and (not apps_to_load or get_app_name(fname) in apps_to_load):
                    try:
                        stat_file = open(os.path.join(dirpath, fname), 'r')
                        if check_in_list(dirpath, args.dirs):
                            dataset_name = "dirs"
                        elif check_in_list(dirpath, args.dirs_two):
                            dataset_name = "dirs_two"
                        dico[dataset_name][fname] = pickle.load(stat_file)
                        stat_file.close()
                    except IOError as e:
                        print(str(e) + ': skip stat file ' + fname, file=sys.stderr)
    return dico

datasets = fetch_data(stat_dir_exp)

##################################################
##               PLOTTING RESULTS               ##
##################################################

def cellular_percentage_boxplot(limit_duration=0, limit_bytes=10000):
    base_graph_name_bytes = "boxplot_cellular_" + start_time + '_' + stop_time
    base_graph_path_bytes = os.path.join(sums_dir_exp, base_graph_name_bytes)

    results = {"both3": {}, "both4": {}}
    for cond in results:
        results[cond] = {co.S2D: {}, co.D2S: {}}

    for dataset_name, connections in datasets.iteritems():
        for fname, data in connections.iteritems():
            condition = get_experiment_condition(fname)
            if 'both' in condition and 'mptcp_fm_' in condition and 'TC' not in condition:
                condition = condition[9:]
                app = get_app_name(fname)
                for conn_id, conn in data.iteritems():
                    if app not in results[condition][co.S2D]:
                        for direction in results[condition].keys():
                            results[condition][direction][app] = {}
                    if dataset_name not in results[condition][co.S2D][app]:
                        for direction in results[condition].keys():
                            results[condition][direction][app][dataset_name] = []

                    # Only interested on MPTCP connections
                    if isinstance(conn, mptcp.MPTCPConnection):
                        if conn.attr[co.DURATION] < limit_duration:
                            continue
                        conn_bytes_s2d = {'rmnet': 0, 'wifi': 0}
                        conn_bytes_d2s = {'rmnet': 0, 'wifi': 0}
                        for interface in conn.attr[co.S2D]:
                            conn_bytes_s2d[interface] += conn.attr[co.S2D][interface]
                        for interface in conn.attr[co.D2S]:
                            conn_bytes_d2s[interface] += conn.attr[co.D2S][interface]
                        for flow_id, flow in conn.flows.iteritems():
                            if co.REINJ_ORIG_BYTES_S2D not in flow.attr or co.REINJ_ORIG_BYTES_D2S not in flow.attr:
                                break
                            interface = flow.attr[co.IF]
                            conn_bytes_s2d[interface] -= flow.attr[co.REINJ_ORIG_BYTES_S2D]
                            conn_bytes_d2s[interface] -= flow.attr[co.REINJ_ORIG_BYTES_D2S]

                        if conn_bytes_s2d['rmnet'] + conn_bytes_s2d['wifi'] > limit_bytes:
                            frac_cell_s2d = ((conn_bytes_s2d['rmnet'] + 0.0) / (conn_bytes_s2d['rmnet'] + conn_bytes_s2d['wifi']))
                            results[condition][co.S2D][app][dataset_name].append(frac_cell_s2d)

                        if conn_bytes_d2s['rmnet'] + conn_bytes_d2s['wifi'] > limit_bytes:
                            frac_cell_d2s = ((conn_bytes_d2s['rmnet'] + 0.0) / (conn_bytes_d2s['rmnet'] + conn_bytes_d2s['wifi']))
                            results[condition][co.D2S][app][dataset_name].append(frac_cell_d2s)

    grouped_boxplot(results, base_graph_path_bytes)


def grouped_boxplot(results, base_graph_path_bytes):
    # function for setting the colors of the box plots pairs
    def setBoxColors(bp):
        plt.setp(bp['boxes'][0], color='blue')
        plt.setp(bp['caps'][0], color='blue')
        plt.setp(bp['caps'][1], color='blue')
        plt.setp(bp['whiskers'][0], color='blue')
        plt.setp(bp['whiskers'][1], color='blue')
        plt.setp(bp['fliers'][0], color='blue')
        plt.setp(bp['fliers'][1], color='blue')
        plt.setp(bp['medians'][0], color='blue')

        plt.setp(bp['boxes'][1], color='red')
        plt.setp(bp['caps'][2], color='red')
        plt.setp(bp['caps'][3], color='red')
        plt.setp(bp['whiskers'][2], color='red')
        plt.setp(bp['whiskers'][3], color='red')
        # plt.setp(bp['fliers'][2], color='red')
        # plt.setp(bp['fliers'][3], color='red')
        plt.setp(bp['medians'][1], color='red')

    for condition, results_condition in results.iteritems():
        for direction, results_direction in results_condition.iteritems():

            fig = plt.figure()
            ax = plt.axes()
            plt.hold(True)

            nb_apps = len(results_direction)
            nb_datasets = 2 # Should be dependent of results...
            labels = []
            position_labels = []

            count = 0
            for app, results_app in results_direction.iteritems():
                positions = [((nb_datasets + 1) * count) + 1, ((nb_datasets + 1) * count) + 2]
                data = [results_app['dirs'], results_app['dirs_two']]
                bp = plt.boxplot(data, positions=positions, widths=0.6)
                setBoxColors(bp)
                labels.append(app)
                position_labels.append(((nb_datasets + 1.0) * count) + ((nb_datasets + 1.0) / 2.0))
                count += 1

            # set axes limits and labels
            plt.xlim(0, nb_apps * (nb_datasets + 1))
            plt.ylim(0, 1.0)
            ax.set_xticklabels(labels)
            ax.set_xticks(position_labels)

            # draw temporary red and blue lines and use them to create a legend
            hB, = plt.plot([1, 1], 'b-')
            hR, = plt.plot([1, 1], 'r-')
            plt.legend((hB, hR), ('Normal', 'Shaping'))
            hB.set_visible(False)
            hR.set_visible(False)

            plt.savefig(base_graph_path_bytes + "_" + condition + "_" + direction + ".pdf")
            plt.close('all')


cellular_percentage_boxplot()
