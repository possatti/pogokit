#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, division

import pandas as pd
import numpy as np
import argparse
import pprint
import json
import sys
import os
import re

from pogokit import data
from pogokit import formulas

try:
    import fuzzywuzzy as fw
    from fuzzywuzzy import fuzz
    from fuzzywuzzy import process as fwprocess
    FUZZY_ENABLED = True
except ImportError:
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

STAB_MULTIPLIER = 1.2
LEGACY_IDENTIFIER = ' (✝)'

FAST_MOVE_COLUMN_ORDER_PRE = ['uniqueId', 'name', 'type', 'power', 'energyDelta', 'durationTurns']
FAST_MOVE_COLUMN_ORDER = ['uniqueId', 'name', 'type', 'power', 'energyDelta', 'durationTurns', 'PPT', 'EPT', 'ZEPDOOS']
FAST_MOVE_VISIBLE_COLUMNS = ['name', 'type_name', 'power', 'energyDelta', 'durationTurns', 'PPT', 'EPT', 'ZEPDOOS']

CHARGED_MOVE_COLUMN_ORDER_PRE = ['uniqueId', 'name', 'type', 'power', 'energyDelta']
CHARGED_MOVE_COLUMN_ORDER = ['uniqueId', 'name', 'type', 'power', 'energyDelta', 'PP100E', 'PPE']
CHARGED_MOVE_VISIBLE_COLUMNS = ['name', 'type_name', 'power', 'energyDelta', 'PP100E', 'PPE']

POKEMON_COLUMN_ORDER = ['dex', 'pokemonId', 'complete_name', 'name', 'form', 'type', 'type2', 'quickMoves', 'cinematicMoves', 'stamina', 'attack', 'defense']

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
            # TODO: Double check if I can assume 0 for these.
            if 'power' not in cm:
                cm['power'] = 0
            if 'energyDelta' not in cm:
                cm['energyDelta'] = 0
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
            # template_match = re.match(r'V(\d+)_POKEMON_.+?(ALOLA)?$', item['templateId']))
            template_match = re.match(r'V(\d+)_POKEMON_(\w+)$', item['templateId'])
            p['dex'] = int(template_match.group(1))
            p['complete_name'] = re.sub(r'_', ' ', template_match.group(2)).title()
            p['name'] = re.sub(r'_', ' ', pok['pokemonId']).title()
            p['form'] = pok['form'] if 'form' in pok else None
            p['stamina'] = pok['stats']['baseStamina']
            p['attack'] = pok['stats']['baseAttack']
            p['defense'] = pok['stats']['baseDefense']
            pokemons.append(p)

    fast_df = pd.DataFrame(fast_moves)[FAST_MOVE_COLUMN_ORDER_PRE]
    charged_df = pd.DataFrame(charged_moves)[CHARGED_MOVE_COLUMN_ORDER_PRE]
    pokemon_df = pd.DataFrame(pokemons)[POKEMON_COLUMN_ORDER]

    # Filter entries for pokémon which have form.
    no_form_mask = pokemon_df['form'].isnull()
    dex_has_forms = pokemon_df.loc[~no_form_mask, 'dex'].unique()
    pokemon_df = pokemon_df.loc[~(pokemon_df['dex'].isin(dex_has_forms) & no_form_mask)]

    return fast_df, charged_df, pokemon_df

def calc_fast_attack_stats(fast_df, zepdoos_c=formulas.ZEPDOOS_C):
    # FIXME: I shouldn't be doing it inplace as well.
    fast_df['type_name'] = fast_df['type'].apply(type_from_gm_template_id)
    fast_df['PPT'] = fast_df['power'] / fast_df['durationTurns']
    fast_df['EPT'] = fast_df['energyDelta'] / fast_df['durationTurns']
    fast_df['ZEPDOOS'] = formulas.calc_zepdoos_score(fast_df['PPT'], fast_df['EPT'], zepdoos_c=zepdoos_c)
    return fast_df

def calc_charged_attack_stats(charged_df):
    # FIXME: I shouldn't be doing it inplace as well.
    charged_df['type_name'] = charged_df['type'].apply(type_from_gm_template_id)
    charged_df['PP100E'] = np.floor(charged_df['power'] / np.abs(charged_df['energyDelta']) * 100).astype(int)
    charged_df['PPE'] = charged_df['power'] / np.abs(charged_df['energyDelta'])
    return charged_df

def best_pvp_moves(args):
    fast_df, charged_df, _ = process_game_master(args.game_master)
    fast_df = calc_fast_attack_stats(fast_df)
    charged_df = calc_charged_attack_stats(charged_df)

    def print_or_save_df(df, path=None, print_n=0):
            with pd.option_context('display.max_rows', None, 'display.max_columns', None):
                table = df.rename(columns=SHORTER_COLUMN_NAMES).reset_index(drop=True)
                if print_n > 0:
                    print(table.head(print_n))
                elif print_n == -1:
                    print(table)
                if path:
                    with open(path, 'w') as f:
                        print(table, file=f)

    print('\nBest PPT moves:')
    best_fast_ppt = fast_df.sort_values(by=['PPT', 'ZEPDOOS'], ascending=False)
    fast_ppt_txt_path = os.path.join(args.save_tables, 'pvp_fast_moves_by_ppt.txt') if args.save_tables else None
    print_or_save_df(best_fast_ppt[FAST_MOVE_VISIBLE_COLUMNS], path=fast_ppt_txt_path, print_n=10)

    print('\nBest EPT moves:')
    best_fast_ept = fast_df.sort_values(by=['EPT', 'ZEPDOOS'], ascending=False)
    fast_ept_txt_path = os.path.join(args.save_tables, 'pvp_fast_moves_by_ept.txt') if args.save_tables else None
    print_or_save_df(best_fast_ept[FAST_MOVE_VISIBLE_COLUMNS], path=fast_ept_txt_path, print_n=10)

    print('\nBest zepdoos moves:')
    best_fast_zepdoos = fast_df.sort_values(by='ZEPDOOS', ascending=False)
    fast_zepdoos_txt_path = os.path.join(args.save_tables, 'pvp_fast_moves_by_zepdoos.txt') if args.save_tables else None
    print_or_save_df(best_fast_zepdoos[FAST_MOVE_VISIBLE_COLUMNS], path=fast_zepdoos_txt_path, print_n=-1)
    best_fast_type_zepdoos = fast_df.sort_values(by=['type', 'ZEPDOOS'], ascending=False)
    fast_type_zepdoos_txt_path = os.path.join(args.save_tables, 'pvp_fast_moves_by_type_and_zepdoos.txt') if args.save_tables else None
    print_or_save_df(best_fast_type_zepdoos[FAST_MOVE_VISIBLE_COLUMNS], path=fast_type_zepdoos_txt_path, print_n=0)

    print('\nBest charge moves for PvP (PPE):')
    best_charged_ppe = charged_df.sort_values(by='PPE', ascending=False)
    charged_ppe_txt_path = os.path.join(args.save_tables, 'pvp_charged_moves_by_ppe.txt') if args.save_tables else None
    print_or_save_df(best_charged_ppe[CHARGED_MOVE_VISIBLE_COLUMNS], path=charged_ppe_txt_path, print_n=30)
    best_charged_type_ppe = charged_df.sort_values(by=['type', 'PPE'], ascending=False)
    charged_type_ppe_txt_path = os.path.join(args.save_tables, 'pvp_charged_moves_by_type_and_ppe.txt') if args.save_tables else None
    print_or_save_df(best_charged_type_ppe[CHARGED_MOVE_VISIBLE_COLUMNS], path=charged_type_ppe_txt_path, print_n=0)

def show_pvp_pokemon_info(rows, fast_df, charge_df, maximum_movesets=25, legacy_fast_df=None, legacy_charge_df=None):
    for row in rows.itertuples():
        complete_type = type_from_gm_template_id(row.type)
        if row.type2:
            complete_type += '-' + type_from_gm_template_id(row.type2)
        max_cp = formulas.calc_cp(row.attack+15, row.defense+15, row.stamina+15, lvl=40)
        max_hp = formulas.calc_hp(row.stamina+15, 40)
        league_d = formulas.find_league_pokemon(row.attack+15, row.defense+15, row.stamina+15)
        print('\n# {:0>3} {} ({})'.format(row.dex, row.complete_name, complete_type))
        print('Base attributes:  ATK={}  DEF={}  STA={}'.format(row.attack, row.defense, row.stamina))
        print('Maximum CP:  {}'.format(max_cp))
        print('Maximum HP:  {}'.format(max_hp))
        print('Perfect IV league levels:  GL={}  UL={}  ML={}'.format(league_d['GL']['levels'][0], league_d['UL']['levels'][0], league_d['ML']['levels'][0]))
        print('Perfect IV league CPs:     GL={}  UL={}  ML={}'.format(league_d['GL']['cps'][0], league_d['UL']['cps'][0], league_d['ML']['cps'][0]))

        fast_moves = fast_df.loc[fast_df['uniqueId'].isin(row.quickMoves)].copy().assign(legacy=False)
        fast_leg_names = legacy_fast_df.loc[legacy_fast_df['pokemon_name']==row.name, 'fast_move']
        fast_moves_leg = fast_df.loc[fast_df['name'].isin(fast_leg_names)].copy().assign(legacy=True)
        fast_moves = pd.concat([fast_moves, fast_moves_leg], ignore_index=True)
        fast_moves['pretty'] = np.where(fast_moves['legacy'], fast_moves['name']+LEGACY_IDENTIFIER, fast_moves['name'])
        fast_moves['STAB'] = np.logical_or(fast_moves['type']==row.type, fast_moves['type']==row.type2)
        fast_moves['STAB_M'] = np.where(fast_moves['STAB'], STAB_MULTIPLIER, 1)
        fast_moves['R_PPT'] = fast_moves['PPT'] * fast_moves['STAB_M']
        fast_moves['R_ZEPDOOS'] = formulas.calc_zepdoos_score(fast_moves['R_PPT'], fast_moves['EPT'])
        fast_moves = fast_moves.sort_values(by='R_ZEPDOOS', ascending=False, inplace=False)
        print('\nFast moves:')
        for move in fast_moves.itertuples():
            stab_str = 'STAB' if move.STAB else ''
            pretty_name = move.name + ' ✝' if move.legacy else move.name
            print(' - [{: <4}] [{: <8}] {: <17} (TURNS={} POWER={:<2.0f} ΔE={:<2} PPT={:<4.1f} EPT={:<4.1f} ZEPDOOS={:<4.1f})'.format(
                stab_str, move.type_name, move.pretty, move.durationTurns, move.power,
                move.energyDelta, move.R_PPT, move.EPT, move.R_ZEPDOOS))

        charge_moves = charge_df.loc[charge_df['uniqueId'].isin(row.cinematicMoves)].copy().assign(legacy=False)
        charge_leg_names = legacy_charge_df.loc[legacy_charge_df['pokemon_name']==row.name, 'charge_move']
        charge_moves_leg = charge_df.loc[charge_df['name'].isin(charge_leg_names)].copy().assign(legacy=True)
        charge_moves = pd.concat([charge_moves, charge_moves_leg])
        charge_moves['pretty'] = np.where(charge_moves['legacy'], charge_moves['name']+LEGACY_IDENTIFIER, charge_moves['name'])
        charge_moves['STAB'] = np.logical_or(charge_moves['type']==row.type, charge_moves['type']==row.type2)
        charge_moves['STAB_M'] = np.where(charge_moves['STAB'], STAB_MULTIPLIER, 1)
        charge_moves['R_PPE'] = charge_moves['power'] * charge_moves['STAB_M'] / np.abs(charge_moves['energyDelta'])
        charge_moves['R_PP100E'] = np.floor(charge_moves['R_PPE'] * 100).astype(int)
        charge_moves = charge_moves.sort_values(by='R_PPE', ascending=False, inplace=False)
        print('\nCharged moves:')
        for move in charge_moves.itertuples():
            stab_str = 'STAB' if move.STAB else ''
            print(' - [{: <4}] [{: <8}] {: <17} (POWER={:<3.0f} ΔE={:<3} PP100E={:<3})'.format(
                stab_str, move.type_name, move.pretty, move.power, move.energyDelta, move.R_PP100E))

        movesets = []
        for f, fast in fast_moves.iterrows():
            for c, charged in charge_moves.iterrows():
                movesets.append({
                    'fast_name': fast['pretty'],
                    'charged_name': charged['pretty'],
                    'PPT': fast['R_PPT']+charged['R_PPE']*fast['EPT'],
                    # 'TDO': formulas.calc_pokemon_moveset_tdo_ref(
                    #     row.attack+15, row.defense+15, max_hp,
                    #     fast['PPT'], fast['EPT'], charged['PPE'],
                    #     fast_mult=fast['STAB_M'], charge_mult=charged['STAB_M']),
                })
                for league in league_d:
                    lvl = league_d[league]['levels'][0]
                    cpm = formulas.CP_MULTIPLIERS[lvl]
                    movesets[-1]['TDO_'+league] = formulas.calc_pokemon_moveset_tdo_ref(
                        (row.attack+15)*cpm, (row.defense+15)*cpm, formulas.calc_hp((row.stamina+15), lvl),
                        fast['PPT'], fast['EPT'], charged['PPE'],
                        fast_mult=fast['STAB_M'], charge_mult=charged['STAB_M']
                    )
        movesets = pd.DataFrame(movesets)
        movesets = movesets.sort_values(by='PPT', ascending=False)
        print('\nBest movesets:')
        for moveset in movesets.iloc[:maximum_movesets].itertuples():
            # print(' - {m.fast_name: >17} - {m.charged_name: <17} (PPT={m.PPT:6.3f}, TDO={m.TDO:7.3f})'.format(m=moveset))
            print((' - {m.fast_name: >17} - {m.charged_name: <17}'
                ' (PPT={m.PPT:6.3f}'
                ', TDO_GL={m.TDO_GL:6.2f}'
                ', TDO_UL={m.TDO_UL:6.2f}'
                ', TDO_ML={m.TDO_ML:6.2f})'
            ).format(m=moveset))
        if len(movesets) > maximum_movesets:
            print(' - {} others'.format(len(movesets) - maximum_movesets))
        print()


def interactive_pvp_mon_search(args):
    fast_df, charged_df, pok_df = process_game_master(args.game_master)
    fast_df = calc_fast_attack_stats(fast_df)
    charged_df = calc_charged_attack_stats(charged_df)
    legacy_fast_df = pd.read_csv(args.legacy_fast)
    legacy_charge_df = pd.read_csv(args.legacy_charge)

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
            show_pvp_pokemon_info(rows, fast_df, charged_df,
                legacy_fast_df=legacy_fast_df, legacy_charge_df=legacy_charge_df)
        else:
            complete_rows = pok_df.loc[pok_df['complete_name']==query.title()]
            rows = pok_df.loc[pok_df['name']==query.title()]
            if len(rows) > 0:
                show_pvp_pokemon_info(rows, fast_df, charged_df,
                    legacy_fast_df=legacy_fast_df, legacy_charge_df=legacy_charge_df)
            elif len(complete_rows) > 0:
                show_pvp_pokemon_info(complete_rows, fast_df, charged_df,
                    legacy_fast_df=legacy_fast_df, legacy_charge_df=legacy_charge_df)
            elif query == 'q' or query == 'quit' or raw_query == '':
                do_quit = True
            elif query == '':
                print('`q` or `quit` to quit', file=sys.stderr)
            elif re.match(r'^\s+$', raw_query):
                continue
            else:
                if FUZZY_ENABLED:
                    possibilities = fw.process.extract(query, pok_df['complete_name'])
                    possible_names = set(p[0] for p in possibilities)
                    print('Couldn\'t find `{}`. Maybe you meant: {}'.format(query, ', '.join(possible_names)))
                else:
                    print('Couldn\'t find any pokemon named `{}`.'.format(query.title()))

def prompt_download_data(args):
    data.download_data(args.data_dir, latest=False)

def download_data(args):
    data.download_data(args.data_dir, latest=args.latest)

def parse_args():
    parser = argparse.ArgumentParser(description='')
    subparsers = parser.add_subparsers(help='Available commands.', dest='command')
    subparsers.required = True

    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument('--data-dir', default=data.get_data_dir())
    common_parser.add_argument('--game-master')
    common_parser.set_defaults(legacy_fast=os.path.join(os.path.dirname(__file__), 'legacy_fast_moves.csv'))
    common_parser.set_defaults(legacy_charge=os.path.join(os.path.dirname(__file__), 'legacy_charge_moves.csv'))

    best_moves_parser = subparsers.add_parser('best_pvp_moves', parents=[common_parser], help='Print best moves.')
    best_moves_parser.add_argument('--save-tables')
    best_moves_parser.set_defaults(func=best_pvp_moves)

    pvp_mon_parser = subparsers.add_parser('pokemon', aliases=['pok', 'mon'], parents=[common_parser], help='Show pokemon info.')
    pvp_mon_parser.add_argument('--query')
    pvp_mon_parser.set_defaults(func=interactive_pvp_mon_search)

    download_data_parser = subparsers.add_parser('download', parents=[common_parser], help='Download essential data.')
    download_data_parser.add_argument('--latest', action='store_true', help='Download latest files (e.g. latest game master)')
    download_data_parser.set_defaults(func=download_data)

    args = parser.parse_args()
    if args.game_master is None:
        args.game_master = os.path.join(args.data_dir, 'GAME_MASTER.json')
    return args

def main():
    print('PoGo Kit (@possatti)')
    args = parse_args()
    args.func(args)

if __name__ == '__main__':
    main()
