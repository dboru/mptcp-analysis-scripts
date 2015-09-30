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

results_duration = {co.S2D: [], co.D2S: []}
min_duration = 0.001
for fname, conns in multiflow_connections.iteritems():
    for conn_id, conn in conns.iteritems():
        # Restrict to only 2SFs, but we can also see with more than 2
        if co.START in conn.attr and len(conn.flows) >= 2:
            # Rely here on MPTCP duration, maybe should be duration at TCP level?
            conn_duration = conn.attr[co.DURATION]
            if conn_duration < min_duration:
                continue
            for direction in co.DIRECTIONS:
                if co.BURSTS in conn.attr[direction]:
                    results_duration[direction].append((conn_duration, len(conn.attr[direction][co.BURSTS])))

base_graph_name = 'bursts_conn_duration'
for direction in co.DIRECTIONS:
    plt.figure()
    plt.clf()
    fig, ax = plt.subplots()

    x_val = [x[0] for x in results_duration[direction]]
    y_val = [x[1] for x in results_duration[direction]]

    ax.scatter(x_val, y_val, label='Connections', color='blue', alpha=.5)

    ax.set_xscale('log')
    ax.set_yscale('log')
    plt.ylim(1, plt.ylim()[1])

    # Put a legend to the right of the current axis
    ax.legend(loc='best', fontsize='large', scatterpoints=1)
    plt.xlabel('Duration [s]', fontsize=24)
    plt.ylabel('# of bursts', fontsize=24)
    plt.grid()

    # plt.annotate('1', xy=(0.57, 0.96),  xycoords="axes fraction",
    #         xytext=(0.85, 0.85), textcoords='axes fraction',
    #         arrowprops=dict(facecolor='black', shrink=0.05),
    #         horizontalalignment='right', verticalalignment='bottom', size='large'
    #         )
    #
    # plt.annotate('2', xy=(0.38, 0.04),  xycoords="axes fraction",
    #         xytext=(0.125, 0.2), textcoords='axes fraction',
    #         arrowprops=dict(facecolor='black', shrink=0.05),
    #         horizontalalignment='left', verticalalignment='top', size='large'
    #         )

    graph_fname = base_graph_name + "_" + direction + ".pdf"
    graph_full_path = os.path.join(sums_dir_exp, graph_fname)

    plt.savefig(graph_full_path)

    plt.clf()
    plt.close('all')
