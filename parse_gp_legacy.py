#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, division
from bs4 import BeautifulSoup

import pandas as pd
import argparse
import requests
import sys
import os
import re

# Moves that were never obtainable.
# https://www.reddit.com/r/TheSilphRoad/comments/92i8yc/list_of_legacy_pok%C3%A9mon_and_their_moves_in_dex/
BLACK_LIST = [
	('Kyogre', 'Dragon Tail'),
	('Zapdos', 'Discharge'),
	('Moltres', 'Ember'),
	('Moltres', 'Flamethrower'),
]

FAST_COLUMNS = ['pokemon_name', 'fast_move']
CHARGE_COLUMNS = ['pokemon_name', 'charge_move']

def parse_args():
	parser = argparse.ArgumentParser(description='')
	parser.add_argument('--gp-legacy-url', default='https://pokemongo.gamepress.gg/legacy-pokemon-move-list')
	parser.add_argument('--gp-legacy-page', default=os.path.join(os.path.dirname(__file__), 'data', 'gp_legacy_page.html'))
	parser.add_argument('--legacy-txt', default=os.path.join(os.path.dirname(__file__), 'data', 'gp_legacy_list.txt'))
	parser.add_argument('--save-fast-moves', default=os.path.join(os.path.dirname(__file__), 'data', 'legacy_fast_moves.csv'))
	parser.add_argument('--save-charge-moves', default=os.path.join(os.path.dirname(__file__), 'data', 'legacy_charge_moves.csv'))
	args = parser.parse_args()
	return args

def blacklisted(pok_name, move_name):
	for item in BLACK_LIST:
		if pok_name == item[0] and move_name == item[1]:
			return True
	return False

def main():
	args = parse_args()

	if not os.path.isfile(args.gp_legacy_page):
		r = requests.get(args.gp_legacy_url)
		with open(args.gp_legacy_page, 'w') as f:
			f.write(r.text)
		gp_legacy_page_content = r.text
	else:
		with open(args.gp_legacy_page, 'r') as f:
			gp_legacy_page_content = f.read()

	fast_moves = []
	charge_moves = []
	soup = BeautifulSoup(gp_legacy_page_content, 'html.parser')
	table = soup.find(id='sort-table')
	blacklist_count = 0
	for tr in table.find_all('tr'):
		if tr.th:
			continue
		tds = tr.find_all('td')
		pok_name = tds[0].find(lambda tag: tag.name=='a' and 'hreflang' in tag.attrs).string
		for a in tds[1].find_all('a'):
			print('{: >15}: {} (fast)'.format(pok_name, a.string))
			if blacklisted(pok_name, a.string):
				blacklist_count += 1
			else:
				fast_moves.append({'pokemon_name': pok_name, 'fast_move': a.string})
		for a in tds[2].find_all('a'):
			print('{: >15}: {} (charge)'.format(pok_name, a.string))
			if blacklisted(pok_name, a.string):
				blacklist_count += 1
			else:
				charge_moves.append({'pokemon_name': pok_name, 'charge_move': a.string})

	print('Number of blacklisted moves:', blacklist_count)

	fast_moves = pd.DataFrame(fast_moves).sort_values(by='pokemon_name')
	charge_moves = pd.DataFrame(charge_moves).sort_values(by='pokemon_name')

	fast_moves.to_csv(args.save_fast_moves, columns=FAST_COLUMNS, index=False)
	charge_moves.to_csv(args.save_charge_moves, columns=CHARGE_COLUMNS, index=False)

if __name__ == '__main__':
	main()