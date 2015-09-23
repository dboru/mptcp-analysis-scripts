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

import argparse
import common as co
import os
import pickle
import sys

parser = argparse.ArgumentParser(
    description="Summarize stat files generated by analyze")
parser.add_argument("mptcp_ack", help="directory where the MPTCP acksizes are stored")
parser.add_argument("tcp_ack", help="directory where the TCP acksizes are stored")
parser.add_argument('-g',
                    "--graph", help="directory where the graphs will be stored", default=co.DEF_SUMS_DIR + '_acksize')

args = parser.parse_args()

MPTCP = 'mptcp'
TCP = 'tcp'

co.check_directory_exists(args.graph)

mptcp_dir_exp = os.path.abspath(os.path.expanduser(args.mptcp_ack))
tcp_dir_exp = os.path.abspath(os.path.expanduser(args.tcp_ack))
sums_dir_exp = os.path.abspath(os.path.expanduser(args.graph))


def fetch_data(dir_exp, dir_exp_two):
    co.check_directory_exists(dir_exp)
    co.check_directory_exists(dir_exp_two)
    dico = {MPTCP: {}, TCP: {}}
    for dirpath, dirnames, filenames in os.walk(dir_exp):
        for fname in filenames:
            try:
                ack_file = open(os.path.join(dirpath, fname), 'r')
                dico[MPTCP][fname] = pickle.load(ack_file)
                ack_file.close()
            except IOError as e:
                print(str(e) + ': skip stat file ' + fname, file=sys.stderr)

    for dirpath, dirnames, filenames in os.walk(dir_exp_two):
        for fname in filenames:
            try:
                ack_file = open(os.path.join(dirpath, fname), 'r')
                dico[TCP][fname] = pickle.load(ack_file)
                ack_file.close()
            except IOError as e:
                print(str(e) + ': skip stat file ' + fname, file=sys.stderr)

    return dico

acks = fetch_data(mptcp_dir_exp, tcp_dir_exp)

sums_acks = {MPTCP: {co.S2D: {}, co.D2S: {}}, TCP: {co.S2D: {}, co.D2S: {}}}

multiflow_conn = set()

for fname, acks_fname in acks[TCP].iteritems():
    for direction, acks_direction in acks_fname.iteritems():
        for conn_id, acks_conn in acks_direction.iteritems():
            if len(acks_conn) >= 2:
                multiflow_conn.add(conn_id)
                for flow_id, acks_flow in acks_conn.iteritems():
                    for value_ack, nb_ack in acks_flow.iteritems():
                        if int(value_ack) > 100000000:
                            print(fname, conn_id, flow_id)
                            continue
                        if int(value_ack) not in sums_acks[TCP][direction]:
                            sums_acks[TCP][direction][int(value_ack)] = int(nb_ack)
                        else:
                            sums_acks[TCP][direction][int(value_ack)] += int(nb_ack)

for fname, acks_fname in acks[MPTCP].iteritems():
    for direction, acks_direction in acks_fname.iteritems():
        for conn_id, acks_conn in acks_direction.iteritems():
            if conn_id in multiflow_conn:
                for value_ack, nb_ack in acks_conn.iteritems():
                    if int(value_ack) > 100000000:
                        print(fname, conn_id)
                        continue
                    if int(value_ack) < -10000000:
                        print(fname, conn_id, int(value_ack))
                        continue
                    if int(value_ack) not in sums_acks[MPTCP][direction]:
                        sums_acks[MPTCP][direction][int(value_ack)] = int(nb_ack)
                    else:
                        sums_acks[MPTCP][direction][int(value_ack)] += int(nb_ack)


to_plot = {MPTCP: {co.S2D: [], co.D2S: []}, TCP: {co.S2D: [], co.D2S: []}}
count = {MPTCP: {co.S2D: 0, co.D2S: 0}, TCP: {co.S2D: 0, co.D2S: 0}}
totot = {MPTCP: {co.S2D: 0, co.D2S: 0}, TCP: {co.S2D: 0, co.D2S: 0}}

for protocol, acks_protocol in sums_acks.iteritems():
    for direction, acks_direction in acks_protocol.iteritems():
        total_bytes = 0
        for value_ack, nb_ack in sorted(acks_direction.iteritems()):
            count[protocol][direction] += nb_ack
            if value_ack < 0:
                print(protocol, value_ack)
                continue
            total_bytes += value_ack * nb_ack
            to_plot[protocol][direction].append([value_ack, total_bytes])
            totot[protocol][direction] += value_ack * nb_ack

        for i in range(0, len(to_plot[protocol][direction])):
            to_plot[protocol][direction][i][1] = (to_plot[protocol][direction][i][1] + 0.0) / total_bytes

for protocol, tot_prot in totot.iteritems():
    for direction, tot_dir  in tot_prot.iteritems():
        print(protocol, direction, tot_dir)

for direction in co.DIRECTIONS:
    graph_filepath = os.path.join(sums_dir_exp, "acks_size_" + direction + ".pdf")
    # Plot results
    co.plot_line_graph([to_plot[MPTCP][direction], to_plot[TCP][direction]], ["MPTCP acks", "TCP acks"], ["g-o", "r-^"], "Acks size (Bytes)", "Bytes percentage", "", graph_filepath, y_log=True)
    #co.plot_line_graph([to_plot[MPTCP][direction]], ["MPTCP acks"], ["g-"], "Acks size (Bytes)", "Bytes percentage", "", graph_filepath, y_log=True)
