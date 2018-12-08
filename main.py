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

print(sys.version, file=sys.stderr)
print('Numpy version:', np.version.version, file=sys.stderr)

CP_MULTIPLIERS = {
	1: 0.094,
	1.5: 0.135137432,
	2: 0.16639787,
	2.5: 0.192650919,
	3: 0.21573247,
	3.5: 0.236572661,
	4: 0.25572005,
	4.5: 0.273530381,
	5: 0.29024988,
	5.5: 0.306057377,
	6: 0.3210876,
	6.5: 0.335445036,
	7: 0.34921268,
	7.5: 0.362457751,
	8: 0.37523559,
	8.5: 0.387592406,
	9: 0.39956728,
	9.5: 0.411193551,
	10: 0.42250001,
	10.5: 0.432926419,
	11: 0.44310755,
	11.5: 0.4530599578,
	12: 0.46279839,
	12.5: 0.472336083,
	13: 0.48168495,
	13.5: 0.4908558,
	14: 0.49985844,
	14.5: 0.508701765,
	15: 0.51739395,
	15.5: 0.525942511,
	16: 0.53435433,
	16.5: 0.542635767,
	17: 0.55079269,
	17.5: 0.558830576,
	18: 0.56675452,
	18.5: 0.574569153,
	19: 0.58227891,
	19.5: 0.589887917,
	20: 0.59740001,
	20.5: 0.604818814,
	21: 0.61215729,
	21.5: 0.619399365,
	22: 0.62656713,
	22.5: 0.633644533,
	23: 0.64065295,
	23.5: 0.647576426,
	24: 0.65443563,
	24.5: 0.661214806,
	25: 0.667934,
	25.5: 0.674577537,
	26: 0.68116492,
	26.5: 0.687680648,
	27: 0.69414365,
	27.5: 0.700538673,
	28: 0.70688421,
	28.5: 0.713164996,
	29: 0.71939909,
	29.5: 0.725571552,
	30: 0.7317,
	30.5: 0.734741009,
	31: 0.73776948,
	31.5: 0.740785574,
	32: 0.74378943,
	32.5: 0.746781211,
	33: 0.74976104,
	33.5: 0.752729087,
	34: 0.75568551,
	34.5: 0.758630378,
	35: 0.76156384,
	35.5: 0.764486065,
	36: 0.76739717,
	36.5: 0.770297266,
	37: 0.7731865,
	37.5: 0.776064962,
	38: 0.77893275,
	38.5: 0.781790055,
	39: 0.78463697,
	39.5: 0.787473578,
	40: 0.79030001,
}

# ### Calculate stats from the main series.
calc_max_atk = lambda atk, s_atk: np.max([atk, s_atk], axis=0)
calc_min_atk = lambda atk, s_atk: np.min([atk, s_atk], axis=0)
calc_max_def = lambda n_def, s_def: np.max([n_def, s_def], axis=0)
calc_min_def = lambda n_def, s_def: np.min([n_def, s_def], axis=0)
calc_scaled_attack  = lambda max_atk, min_atk: np.round(2 * (7/8*max_atk + 1/8*min_atk))
# calc_scaled_defense = lambda max_def, min_def: np.round(2 * (7/8*max_def + 1/8*min_def)) # Old. https://www.reddit.com/r/TheSilphRoad/comments/9ofymc/new_defense_stat_formula/
calc_scaled_defense = lambda max_def, min_def: np.round(2 * (5/8*max_def + 3/8*min_def))
calc_speed_mod      = lambda speed: 1 + (speed - 75) / 500
# calc_stamina = lambda hp: hp * 2 # Old. https://www.reddit.com/r/TheSilphRoad/comments/9ofymc/new_defense_stat_formula/
calc_stamina = lambda hp: np.floor(hp * 1.75 + 50).astype(int)
calc_base_attack  = lambda scaled_attack,  speed_mod: np.round(scaled_attack  * speed_mod).astype(int)
calc_base_defense = lambda scaled_defense, speed_mod: np.round(scaled_defense * speed_mod).astype(int)

def cp_formula(attack, defense, stamina, cp_multiplier):
	"""Also include IV on attributes."""
	return np.floor((attack * (defense**0.5) * (stamina**0.5) * cp_multiplier**2) / 10).astype(int)

def main(args):

	# id,identifier,species_id,height,weight,base_experience,order,is_default
	pokemon_df = pd.read_csv('data/pokemon.csv', index_col='id')
	# pokemon_id,stat_id,base_stat,effort
	pokemon_stats_df = pd.read_csv('data/pokemon_stats.csv')
	# id,damage_class_id,identifier,is_battle_only,game_index
	stats_df = pd.read_csv('data/stats.csv', index_col='id')

	veekun_df = pokemon_df.join(pokemon_stats_df.set_index('pokemon_id'))
	veekun_df = veekun_df.join(stats_df, rsuffix='_stat', on='stat_id')
	veekun_df['hp'] = veekun_df['base_stat'].loc[veekun_df['identifier_stat']=='hp']
	veekun_df['atk'] = veekun_df['base_stat'].loc[veekun_df['identifier_stat']=='attack']
	veekun_df['def'] = veekun_df['base_stat'].loc[veekun_df['identifier_stat']=='defense']
	veekun_df['s_atk'] = veekun_df['base_stat'].loc[veekun_df['identifier_stat']=='special-attack']
	veekun_df['s_def'] = veekun_df['base_stat'].loc[veekun_df['identifier_stat']=='special-defense']
	veekun_df['speed'] = veekun_df['base_stat'].loc[veekun_df['identifier_stat']=='speed']
	veekun_df = veekun_df[['identifier', 'species_id', 'hp', 'atk', 'def', 's_atk', 's_def', 'speed']]
	veekun_df.drop_duplicates(inplace=True)

	print("veekun_df.head():\n", veekun_df.head(), file=sys.stderr) #!#
	# exit(3)

	calc_df = veekun_df[['identifier', 'species_id']].copy()
	max_atk = np.max(veekun_df[['atk', 's_atk']], axis=1)
	min_atk = np.min(veekun_df[['atk', 's_atk']], axis=1)
	max_def = np.max(veekun_df[['def', 's_def']], axis=1)
	min_def = np.min(veekun_df[['def', 's_def']], axis=1)
	# scaled_attack = np.round(2 * (7/8*max_atk + 1/8*min_atk))
	# # scaled_defense = np.round(2 * (7/8*max_def + 1/8*min_def))
	# scaled_defense = np.round(2 * (5/8*max_def + 3/8*min_def)) # https://www.reddit.com/r/TheSilphRoad/comments/9ofymc/new_defense_stat_formula/
	# speed_mod = 1 + (veekun_df['speed'] - 75) / 500
	# base_attack = np.round(scaled_attack * speed_mod)
	# base_defense = np.round(scaled_defense * speed_mod)
	scaled_attack  = calc_scaled_attack(max_atk,  min_atk)
	scaled_defense = calc_scaled_defense(max_atk, min_atk)
	speed_mod = calc_speed_mod(veekun_df['speed'])
	calc_df['attack']  = calc_base_attack(scaled_attack,   speed_mod)
	calc_df['defense'] = calc_base_defense(scaled_defense, speed_mod)
	calc_df['stamina'] = calc_stamina(veekun_df['hp'])
	calc_df['max_cp'] = cp_formula(calc_df['attack']+15, calc_df['defense']+15, calc_df['stamina']+15, CP_MULTIPLIERS[40])
	print("calc_df.head():\n", calc_df.head(), file=sys.stderr) #!#

	with open(args.json, 'r') as f:
		gamepress_data = json.load(f)

	# pprint.pprint(gamepress_data[0]) #!#

	cols = ['number', 'name', 'attack', 'defense', 'stamina', 'max_cp']
	gamepress_cols = ['number', 'title_1', 'atk', 'def', 'sta', 'cp']
	types = [int, str, int, int, int, int]
	pokemon_d = { c: [] for c in cols }
	for pokemon in gamepress_data:
		for col_name, gp_col, col_type in zip(cols, gamepress_cols, types):
			pokemon_d[col_name].append(col_type(pokemon[gp_col]))

	del gamepress_data
	gp_df = pd.DataFrame(pokemon_d)
	del pokemon_d

	# gp_df['calc_max_cp'] = cp_formula(gp_df['attack']+15, gp_df['defense']+15, gp_df['stamina']+15, CP_MULTIPLIERS[40])
	# print("gp_df.head():\n", gp_df.head(), file=sys.stderr) #!#
	print("gp_df:\n", gp_df, file=sys.stderr) #!#

	# join = calc_df.join(gp_df.set_index('number'), on='species_id', lsuffix='_calc', rsuffix='_gp', how='right')
	# compare_df = calc_df.set_index('species_id').join(gp_df.set_index('number'), lsuffix='_calc', rsuffix='_gp', how='right')
	compare_df = calc_df.join(gp_df.set_index('number'), lsuffix='_calc', rsuffix='_gp', how='right')
	compare_df = compare_df[['identifier', 'attack_calc', 'attack_gp', 'defense_calc', 'defense_gp', 'stamina_calc', 'stamina_gp', 'max_cp_calc', 'max_cp_gp']]
	print('Total entries:', len(compare_df), file=sys.stderr)
	equal_df = compare_df.loc[compare_df['max_cp_calc']==compare_df['max_cp_gp']]
	different_df = compare_df.loc[compare_df['max_cp_calc']!=compare_df['max_cp_gp']]
	print('Different entries:', len(compare_df), file=sys.stderr)
	print("equal_df:\n", equal_df, file=sys.stderr) #!#
	print("different_df:\n", different_df, file=sys.stderr) #!#

def parse_args():
	parser = argparse.ArgumentParser(description='')
	# parser.add_argument('arg')
	parser.add_argument('--json', default=os.path.join(os.path.dirname(__file__), 'data', 'gamepress_data.json'))
	# parser.add_argument('--cp-multipliers', default=os.path.join(os.path.dirname(__file__), 'cp_multipliers.json'))
	args = parser.parse_args()
	return args

if __name__ == '__main__':
	args = parse_args()
	main(args)