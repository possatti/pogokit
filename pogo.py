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

try:
	import fuzzywuzzy as fw
	from fuzzywuzzy import fuzz
	from fuzzywuzzy import process as fwprocess
	FUZZY_ENABLED = True
except:
	FUZZY_ENABLED = False

"""
## Additional resources

Spreadsheet with moves data (good for double checking). But I found Fire Spin to
be wrong, 3 turns instead of 2, so I think it's outdated.
 - https://www.reddit.com/r/TheSilphRoad/comments/a5r1kf/pvp_move_data_from_game_master/

Excelent discussion on how to measure how good a fast move is. I like the metric
zepdoos defines, it makes much sense.
 - https://www.reddit.com/r/TheSilphRoad/comments/a6o3md/comprehensive_graphical_comparison_of_pvp_fast/
"""

FAST_MOVE_COLUMN_ORDER_PRE = ['uniqueId', 'name', 'type', 'power', 'energyDelta', 'durationTurns']
FAST_MOVE_COLUMN_ORDER = ['uniqueId', 'name', 'type', 'power', 'energyDelta', 'durationTurns', 'DPT', 'EPT', 'zepdoos']
FAST_MOVE_VISIBLE_COLUMNS = ['name', 'type_name', 'power', 'energyDelta', 'durationTurns', 'DPT', 'EPT', 'zepdoos']

CHARGED_MOVE_COLUMN_ORDER_PRE = ['uniqueId', 'name', 'type', 'power', 'energyDelta']
CHARGED_MOVE_COLUMN_ORDER = ['uniqueId', 'name', 'type', 'power', 'energyDelta', 'DP100E', 'DPE']
CHARGED_MOVE_VISIBLE_COLUMNS = ['name', 'type_name', 'power', 'energyDelta', 'DP100E', 'DPE']

POKEMON_COLUMN_ORDER = ['dex', 'pokemonId', 'name', 'type', 'type2', 'quickMoves', 'cinematicMoves', 'stamina', 'attack', 'defense']

SHORTER_COLUMN_NAMES = {
	'energyDelta': 'ΔE',
	'durationTurns': 'turns',
}

def type_from_gm_template_id(template_id):
	return re.match(r'^POKEMON_TYPE_(\w+)$', template_id).group(1).title()

def process_game_master(game_master_path):
	with open(game_master_path, 'r') as f:
		gm = json.load(f)
	pokemons = []
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
					# TODO: Double check if I can assume 1 turn.
					cm['durationTurns'] = 1
				fast_moves.append(cm)
			else:
				charged_moves.append(cm)
		elif 'pokemonSettings' in item:
			pok = item['pokemonSettings']
			p = {}
			for field in ['pokemonId', 'type', 'quickMoves', 'cinematicMoves']:
				p[field] = pok[field]
			p['type2'] = None
			if 'type2' in pok:
				p['type2'] = pok['type2']
			template_match = re.match(r'V(\d+)_POKEMON_.+?(ALOLA)?$', item['templateId'])
			p['dex'] = int(template_match.group(1))
			p['name'] = re.sub(r'_', ' ', pok['pokemonId']).title()
			# if template_match.group(2):
			# 	p['name'] = 'Alolan ' + p['name']
			p['stamina'] = pok['stats']['baseStamina']
			p['attack'] = pok['stats']['baseAttack']
			p['defense'] = pok['stats']['baseDefense']
			pokemons.append(p)

	fast_df = pd.DataFrame(fast_moves)[FAST_MOVE_COLUMN_ORDER_PRE]
	charged_df = pd.DataFrame(charged_moves)[CHARGED_MOVE_COLUMN_ORDER_PRE]
	pokemon_df = pd.DataFrame(pokemons)[POKEMON_COLUMN_ORDER]
	return fast_df, charged_df, pokemon_df

def calc_fast_attack_stats(fast_df, zepdoos_c=1.4):
	# FIXME: I shouldn't be doing it inplace as well.
	fast_df['type_name'] = fast_df['type'].apply(type_from_gm_template_id)
	fast_df['DPT'] = fast_df['power'] / fast_df['durationTurns']
	fast_df['EPT'] = fast_df['energyDelta'] / fast_df['durationTurns']
	fast_df['zepdoos'] = fast_df['DPT'] + zepdoos_c*fast_df['EPT']
	return fast_df

def calc_charged_attack_stats(charged_df):
	# FIXME: I shouldn't be doing it inplace as well.
	charged_df['type_name'] = charged_df['type'].apply(type_from_gm_template_id)
	charged_df['DP100E'] = np.floor(charged_df['power'] / np.abs(charged_df['energyDelta']) * 100).astype(int)
	charged_df['DPE'] = charged_df['power'] / np.abs(charged_df['energyDelta'])
	return charged_df

def best_pvp_moves(args):
	fast_df, charged_df, _ = process_game_master(args.game_master)
	fast_df = calc_fast_attack_stats(fast_df)
	charged_df = calc_charged_attack_stats(charged_df)

	print('\nBest DPT moves:')
	best_fast_dpt = fast_df.sort_values(by='DPT', ascending=False)
	with pd.option_context('display.max_rows', None, 'display.max_columns', None):
		table = best_fast_dpt[FAST_MOVE_VISIBLE_COLUMNS].rename(columns=SHORTER_COLUMN_NAMES).reset_index(drop=True)
		print(table.head(10))
		with open(args.save_fast_dpt, 'w') as f:
			print(table, file=f)

	print('\nBest EPT moves:')
	best_fast_ept = fast_df.sort_values(by='EPT', ascending=False)
	with pd.option_context('display.max_rows', None, 'display.max_columns', None):
		table = best_fast_ept[FAST_MOVE_VISIBLE_COLUMNS].rename(columns=SHORTER_COLUMN_NAMES).reset_index(drop=True)
		print(table.head(10))
		with open(args.save_fast_ept, 'w') as f:
			print(table, file=f)

	print('\nBest zepdoos moves:')
	best_fast_zepdoos = fast_df.sort_values(by='zepdoos', ascending=False)
	with pd.option_context('display.max_rows', None, 'display.max_columns', None):
		table = best_fast_zepdoos[FAST_MOVE_VISIBLE_COLUMNS].rename(columns=SHORTER_COLUMN_NAMES).reset_index(drop=True)
		print(table)
		with open(args.save_fast_zepdoos, 'w') as f:
			print(table, file=f)

	print('\nBest charge moves for PvP (DPE):')
	best_charged_dpe = charged_df.sort_values(by='DPE', ascending=False)
	with pd.option_context('display.max_rows', None, 'display.max_columns', None):
		table = best_charged_dpe[CHARGED_MOVE_VISIBLE_COLUMNS].rename(columns=SHORTER_COLUMN_NAMES).reset_index(drop=True)
		print(table.head(30))
		with open(args.save_charged_dpe, 'w') as f:
			print(table, file=f)

def show_pvp_pokemon_info(rows, fast_df, charged_df, maximum_movesets=10):
	for row in rows.itertuples():
		complete_type = type_from_gm_template_id(row.type)
		if row.type2:
			complete_type += '-' + type_from_gm_template_id(row.type2)
		print('\n# {:0>3} {} ({})'.format(row.dex, row.name, complete_type))
		print('Attributes:  ATK={}  DEF={}  STA={}'.format(row.attack, row.defense, row.stamina))

		fast_moves = fast_df.loc[fast_df['uniqueId'].isin(row.quickMoves)]
		fast_moves = fast_moves.sort_values(by='zepdoos', ascending=False, inplace=False)
		print('\nFast moves:')
		for move in fast_moves.itertuples():
			print(' - {: <17} (TURNS={} DPT={} EPT={} ZEPDOOS={:4.1f})'.format(move.name, move.durationTurns, move.DPT, move.EPT, move.zepdoos))

		charged_moves = charged_df.loc[charged_df['uniqueId'].isin(row.cinematicMoves)]
		charged_moves = charged_moves.sort_values(by='DPE', ascending=False, inplace=False)
		print('\nCharged moves:')
		for move in charged_moves.itertuples():
			print(' - {: <17} (ΔE={} DP100E={})'.format(move.name, move.energyDelta, move.DP100E))

		movesets = []
		for fast_move in row.quickMoves:
			for charged_move in row.cinematicMoves:
				fast = fast_moves.loc[fast_moves['uniqueId']==fast_move].iloc[0]
				charged = charged_moves.loc[charged_moves['uniqueId']==charged_move].iloc[0]
				movesets.append({
					'fast_name': fast['name'],
					'charged_name': charged['name'],
					'DPT': fast['DPT']+charged['DPE']*fast['EPT'],
				})
		movesets = pd.DataFrame(movesets)
		movesets = movesets.sort_values(by='DPT', ascending=False)
		print('\nBest movesets:')
		for moveset in movesets.iloc[:maximum_movesets].itertuples():
			print(' - {m.fast_name: >17} - {m.charged_name: <17} (DPT={m.DPT:.3f})'.format(m=moveset))
		if len(movesets) > maximum_movesets:
			print(' - {} others'.format(len(movesets) - maximum_movesets))
		print()


def interactive_pvp_mon_search(args):
	fast_df, charged_df, pok_df = process_game_master(args.game_master)
	fast_df = calc_fast_attack_stats(fast_df)
	charged_df = calc_charged_attack_stats(charged_df)

	# Interactive loop.
	do_quit = False
	while not do_quit:
		if args.query:
			raw_query = args.query
			do_quit = True
		else:
			sys.stderr.write('>> pok: ')
			sys.stderr.flush()
			raw_query = sys.stdin.readline()
		query = raw_query.strip()

		if query.isdigit():
			dex_number = int(query)
			rows = pok_df.loc[pok_df['dex']==dex_number]
			show_pvp_pokemon_info(rows, fast_df, charged_df)
		else:
			rows = pok_df.loc[pok_df['name']==query.title()]
			if len(rows) > 0:
				show_pvp_pokemon_info(rows, fast_df, charged_df)
			elif query == 'q' or query == 'quit' or raw_query == '':
				do_quit = True
			elif query == '':
				print('`q` or `quit` to quit', file=sys.stderr)
			elif re.match(r'^\s+$', raw_query):
				continue
			else:
				if FUZZY_ENABLED:
					possibilities = fw.process.extract(query, pok_df['name'])
					possible_names = set(p[0] for p in possibilities)
					print('Couldn\'t find `{}`. Maybe you meant: {}'.format(query, ', '.join(possible_names)))
				else:
					print('Couldn\'t find any pokemon named `{}`.'.format(query.title()))


def parse_args():
	parser = argparse.ArgumentParser(description='')
	subparsers = parser.add_subparsers(help='Available commands.', dest='command')
	subparsers.required = True

	common_parser = argparse.ArgumentParser(add_help=False)
	common_parser.add_argument('--game-master', default=os.path.join(os.path.dirname(__file__), 'data', 'GAME_MASTER.json'))

	best_moves_parser = subparsers.add_parser('best_pvp_moves', parents=[common_parser], help='Print best moves.')
	best_moves_parser.add_argument('--save-fast-dpt', default=os.path.join(os.path.dirname(__file__), 'data', 'pvp_fast_moves_by_dpt.txt'))
	best_moves_parser.add_argument('--save-fast-ept', default=os.path.join(os.path.dirname(__file__), 'data', 'pvp_fast_moves_by_ept.txt'))
	best_moves_parser.add_argument('--save-fast-zepdoos', default=os.path.join(os.path.dirname(__file__), 'data', 'pvp_fast_moves_by_zepdoos.txt'))
	best_moves_parser.add_argument('--save-charged-dpe', default=os.path.join(os.path.dirname(__file__), 'data', 'pvp_charged_moves_by_dpe.txt'))

	pvp_mon_parser = subparsers.add_parser('pvp_mon', parents=[common_parser], help='Build all the input files.')
	pvp_mon_parser.add_argument('--query')

	args = parser.parse_args()
	# if not args.command:
	# 	parser.print_help(file=sys.stderr)
	return args


if __name__ == '__main__':
	args = parse_args()
	if args.command == 'best_pvp_moves':
		best_pvp_moves(args)
	elif args.command == 'pvp_mon':
		interactive_pvp_mon_search(args)