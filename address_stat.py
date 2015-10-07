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
# multiflow_connections, singleflow_connections = cog.get_multiflow_connections(connections)

##################################################
##               PLOTTING RESULTS               ##
##################################################

ip_addrs = {}

for fname, conns in connections.iteritems():
    for conn_id, conn in conns.iteritems():
        port = conn.flows[0].attr.get(co.SOCKS_PORT, conn.attr.get(co.SOCKS_PORT, None))
        # Apache JServ Port
        if port and port == 8009:
            ip_addr = conn.flows[0].attr.get(co.SOCKS_DADDR, conn.attr.get(co.SOCKS_DADDR, None))
            if ip_addr not in ip_addrs:
                ip_addrs[ip_addr] = 1
            else:
                ip_addrs[ip_addr] += 1
            print(fname, conn_id)

print("IP ADDRS", ip_addrs)
