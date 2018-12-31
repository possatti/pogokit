#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, division

import requests
import sys
import os

LATEST_GAME_MASTER_URL = 'https://raw.githubusercontent.com/pokemongo-dev-contrib/pokemongo-game-master/master/versions/latest/GAME_MASTER.json'
PINNED_GAME_MASTER_URL = 'https://raw.githubusercontent.com/pokemongo-dev-contrib/pokemongo-game-master/master/versions/1545819471259/GAME_MASTER.json'

def get_data_dir():
	if sys.platform.startswith('linux'):
		# Config directory according to freedesktop.org stuff.
		if 'XDG_CONFIG_HOME' in os.environ and os.environ['XDG_CONFIG_HOME']:
			return os.path.join(os.environ['XDG_CONFIG_HOME'], 'pogokit')
		else:
			return os.path.join(os.environ['HOME'], '.config', 'pogokit')
	elif sys.platform.startswith('win32'):
		return os.path.join(os.environ['APP_DATA'], 'pogokit')
	elif sys.platform.startswith('darwin'):
		# I have no experience with macs, so I have no idea if this is right.
		return os.path.join(os.environ['HOME'], 'pogokit')
	else:
		raise Exception('Don\'t know how to deal with platform `{}`'.format(sys.platform))

def download_data(data_dir=get_data_dir(), latest=False):
	game_master_url = PINNED_GAME_MASTER_URL
	if latest:
		game_master_url = LATEST_GAME_MASTER_URL

	if not os.path.isdir(data_dir):
		os.makedirs(data_dir)

	gm_path = os.path.join(data_dir, 'GAME_MASTER.json')
	print('Downloading game master to `{}`.'.format(gm_path), file=sys.stderr)
	r = requests.get(game_master_url)
	with open(gm_path, 'wb') as f:
		f.write(r.content)
