#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, division
from subprocess import call

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import argparse
import math
import sys
import os

def parse_args():
	parser = argparse.ArgumentParser(description='')
	parser.add_argument('--type-chart-csv', default=os.path.join(os.path.dirname(__file__), 'data', 'type_chart.csv'))
	args = parser.parse_args()
	return args

def combination(n, r):
	if type(n) is not int or type(r) is not int:
		raise TypeError('n and r should be integer values. Got {} and {}. Types {} and {}'.format(n, r, type(n), type(r)))
	return int(math.factorial(n) / (math.factorial(r)*math.factorial(n-r)))

def main(args):
	df = pd.read_csv(args.type_chart_csv, index_col='Attacking')
	# print("Type effectiveness chart:\n{}".format(df), file=sys.stderr) #!#
	p_types = df.columns # 18 types

	# for t1 in range(len(p_types)):
	# 	for t2 in range(t1+1, len(p_types)):
	# 		type1 = p_types[t1]
	# 		type2 = p_types[t2]
	# 		dual_type_name = '{}-{}'.format(type1, type2)

	# 		print(dual_type_name)
	# exit(3)

	attacking_advantage = df.mean(axis=1)
	defending_advantage = df.mean(axis=0)
	advantage = pd.DataFrame({'attacking': attacking_advantage, 'defending': defending_advantage})
	advantage['overall'] = advantage.mean(axis=1)
	advantage.sort_values(by='overall', inplace=True)
	advantage.index.name = None
	print("Type advantage:\n{}".format(advantage))

	# trio_advantage
	trio_name_list = []
	trio_attacking_advantage = []
	trio_defending_advantage = []
	for t1 in range(len(p_types)):
		for t2 in range(t1+1, len(p_types)):
			for t3 in range(t2+1, len(p_types)):
				type1, type2, type3 = p_types[t1], p_types[t2], p_types[t3]
				type_names = [p_types[t1], p_types[t2], p_types[t3]]
				trio_name = '-'.join(type_names)
				trio_mean_row = df.loc[df.index.isin(type_names),:].mean(axis=0)
				# print("np.mean(df.loc[df.index.isin(type_names),:]):\n", np.mean(df.loc[df.index.isin(type_names),:].values), file=sys.stderr) #!#
				atk_advantage = np.mean(df.loc[df.index.isin(type_names),:].values)
				def_advantage = np.mean(df.loc[:,df.index.isin(type_names)].values)
				trio_name_list.append(trio_name)
				trio_attacking_advantage.append(atk_advantage)
				trio_defending_advantage.append(def_advantage)
	trio_advantage = pd.DataFrame({'attacking': trio_attacking_advantage, 'defending': trio_defending_advantage}, index=trio_name_list)
	trio_advantage['overall'] = trio_advantage.mean(axis=1)

	print('\nBest trios by attacking advantage:')
	print(trio_advantage.sort_values(by='attacking', ascending=False)[:10])

	print('\nBest trios by defending advantage:')
	print(trio_advantage.sort_values(by='defending', ascending=False)[:10])

	print('\nBest trios by overall advantage:')
	print(trio_advantage.sort_values(by='overall', ascending=False)[:10])



if __name__ == '__main__':
	args = parse_args()
	main(args)