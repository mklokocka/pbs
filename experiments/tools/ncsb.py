#!/usr/bin/python3

import spot
import argparse

parser = argparse.ArgumentParser \
  (description='Apply a (transition-based) version of the NCSB construction',
       allow_abbrev=True)
parser.add_argument('file', type=str, nargs='*',
                    help='automata to process', default='-')
parser.add_argument('--debug', default=0, type=int,
                    choices=[0, 1],
                    help='label states for debugging')

args = parser.parse_args()

for aut in spot.automata(*args.file):
    print(spot.complement_semidet(aut, bool(args.debug)).to_str())
