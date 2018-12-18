#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, division
from subprocess import call

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import argparse
import pprint
import json
import sys
import os
import re

# "templateId": "COMBAT_SETTINGS",

# FAST_MOVE_COLUMNS = ['uniqueId', 'name', 'type', 'power', 'energyDelta', 'durationTurns']
# CHARGED_MOVE_COLUMNS = ['uniqueId', 'name', 'type', 'power', 'energyDelta']
FAST_MOVE_COLUMNS = ['name', 'type_name', 'power', 'energyDelta', 'durationTurns']
CHARGED_MOVE_COLUMNS = ['name', 'type_name', 'power', 'energyDelta']

def filter_moves_from_game_master(game_master_path):
	with open(game_master_path, 'r') as f:
		gm = json.load(f)
	fast_moves = []
	charged_moves = []
	lost_fast_moves = []
	for item in gm['itemTemplates']:
		if 'combatMove' in item:
			cm = item['combatMove']
			id_match = re.match(r'(\w+?)(_FAST)?$', cm['uniqueId'])
			name = id_match.group(1)
			name = re.sub(r'_', ' ', name)
			name = name.title()
			cm['name'] = name
			cm['type_name'] = re.match(r'POKEMON_TYPE_(\w+)', cm['type']).group(1).title()
			if id_match.group(2) == '_FAST':
				if 'durationTurns' not in cm:
					# There doesn't seem to be a default. Fury Cutter and Lick are much
					# faster than Bite. But they all don't have durationTurns.
					# I don't think we can derive the values from the Gym system,
					# they look quite different.
					lost_fast_moves.append(cm)
				else:
					fast_moves.append(cm)
			else:
				charged_moves.append(cm)
	print("Lost fast moves:\n", file=sys.stderr) #!#
	pprint.pprint(lost_fast_moves, sys.stderr)

	fast_df = pd.DataFrame(fast_moves)
	charged_df = pd.DataFrame(charged_moves)
	fast_df = fast_df[FAST_MOVE_COLUMNS]
	charged_df = charged_df[CHARGED_MOVE_COLUMNS]
	return fast_df, charged_df

def main(args):
	fast_df, charged_df = filter_moves_from_game_master(args.game_master)

	fast_df['DPT'] = fast_df['power'] / fast_df['durationTurns']
	fast_df['EPT'] = fast_df['energyDelta'] / fast_df['durationTurns']
	charged_df['DP100E'] = np.floor(charged_df['power'] / np.abs(charged_df['energyDelta']) * 100).astype(int)
	charged_df['DPE'] = charged_df['power'] / np.abs(charged_df['energyDelta'])

	print('\nBest DPT moves:')
	best_fast_dpt = fast_df.sort_values(by='DPT', ascending=False)
	# with open(args.save_fast_dpt, 'w') as f:
	#     f.write(best_fast_dpt.__repr__())
	best_fast_dpt.to_csv(args.save_fast_dpt, sep=',', index=False)
	print(best_fast_dpt.head(10))

	print('\nBest EPT moves:')
	best_fast_ept = fast_df.sort_values(by='EPT', ascending=False)
	# with open(args.save_fast_ept, 'w') as f:
	#     f.write(best_fast_ept.__repr__())
	best_fast_ept.to_csv(args.save_fast_ept, sep=',', index=False)
	print(best_fast_ept.head(10))

	print('\nBest charge moves for PvP (DPE):')
	best_charged_dpe = charged_df.sort_values(by='DPE', ascending=False)
	# with open(args.save_charged_dpe, 'w') as f:
	#     f.write(best_charged_dpe.__repr__())
	best_charged_dpe.to_csv(args.save_charged_dpe, sep=',', index=False)
	print(best_charged_dpe.head(30))


def parse_args():
	parser = argparse.ArgumentParser(description='')
	parser.add_argument('--game-master', default=os.path.join(os.path.dirname(__file__), 'data', 'GAME_MASTER.json'))
	parser.add_argument('--save-fast-dpt', default=os.path.join(os.path.dirname(__file__), 'data', 'pvp_fast_moves_by_dpt.csv'))
	parser.add_argument('--save-fast-ept', default=os.path.join(os.path.dirname(__file__), 'data', 'pvp_fast_moves_by_ept.csv'))
	parser.add_argument('--save-charged-dpe', default=os.path.join(os.path.dirname(__file__), 'data', 'pvp_charged_moves_by_dpe.csv'))
	args = parser.parse_args()
	return args

if __name__ == '__main__':
	args = parse_args()
	main(args)