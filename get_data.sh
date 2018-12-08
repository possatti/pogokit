#!/usr/bin/env bash

declare -A DATA

DATA[gamepress_data.json]=https://gamepress.gg/sites/default/files/aggregatedjson/list-en-PoGO.json?2012215149129830236
DATA[pokemon.csv]=https://github.com/veekun/pokedex/raw/master/pokedex/data/csv/pokemon.csv
DATA[pokemon_stats.csv]=https://github.com/veekun/pokedex/raw/master/pokedex/data/csv/pokemon_stats.csv
DATA[stats.csv]=https://github.com/veekun/pokedex/raw/master/pokedex/data/csv/stats.csv

DATA_DIR=data

mkdir -p "$DATA_DIR"

for FILE_NAME in ${!DATA[@]}; do
	FILE_PATH="${DATA_DIR}/${FILE_NAME}"
	URL="${DATA[$FILE_NAME]}"
	echo "Downloading '${URL}' to '${FILE_PATH}'..."
	if [[ ! -s ${FILE_PATH} ]]; then
		wget -O "$FILE_PATH" "$URL"
	fi
done
