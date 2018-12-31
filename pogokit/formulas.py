#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, division

import numpy as np
import sys
import os

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

def calc_cp(attack, defense, stamina, lvl=None, cpm=None):
    """Please include IV on attributes."""
    if cpm is None:
        if lvl is None:
            raise ValueError('Missing argument lvl or cpm.')
        else:
            cpm = CP_MULTIPLIERS[lvl]
    return np.floor((attack * (defense**0.5) * (stamina**0.5) * cpm**2) / 10).astype(int)

ZEPDOOS_C = 1.4
def calc_zepdoos_score(ppt, ept, zepdoos_c=ZEPDOOS_C):
    return ppt + zepdoos_c * ept

def calc_hp(stamina, lvl):
    return np.floor(stamina * CP_MULTIPLIERS[lvl])

def calc_pokemon_moveset_tdo(atk_a, def_a, hp_a, fast_ppt_a, fast_ept_a, charge_ppe_a,
    atk_b, def_b, fast_ppt_b, fast_ept_b, charge_ppe_b,
    fast_mult_a=1, charge_mult_a=1, fast_mult_b=1, charge_mult_b=1):
    """Calculate a Pokémon's TDO."""
    return ((fast_ppt_a*fast_mult_a + fast_ept_a*charge_ppe_a*charge_mult_a) * atk_a * def_a * hp_a) / \
        ((fast_ppt_b*fast_mult_b + fast_ept_b*charge_ppe_b*fast_mult_b) * atk_b * def_b)

def calc_pokemon_moveset_tdo_ref(atk, def_, hp, fast_ppt, fast_ept, charge_ppe, fast_mult=1, charge_mult=1):
    """Calculate a Pokémon's TDO against a reference enemy."""
    atk_b, def_b = 200, 150
    fast_ppt_b, fast_ept_b, charge_ppe_b = 5, 5, 1.8
    return calc_pokemon_moveset_tdo(atk, def_, hp, fast_ppt, fast_ept, charge_ppe,
        atk_b, def_b, fast_ppt_b, fast_ept_b, charge_ppe_b,
        fast_mult_a=fast_mult, charge_mult_a=charge_mult)

def calc_pokemon_moveset_propto_tdo(atk, def_, hp, fast_ppt, fast_ept, charge_ppe, fast_mult=1, charge_mult=1):
    """Calculate something proportional to a Pokémon's TDO"""
    return (fast_ppt*fast_mult + fast_ept*charge_ppe*charge_mult) * atk * def_ * hp

def find_league_pokemon(atks, defs, stas):
    """Find maximum level pokémon (IV 0) that fit in the leagues."""
    if type(atks) is np.array:
        assert len(atks) == len(defs) and len(atks) == len(stas), 'Weird number of elements in arrays'
        n_pokemon = len(atks)
    else:
        n_pokemon = 1
    levels = np.arange(1, 40.5, 0.5)
    cpms = np.array([ CP_MULTIPLIERS[l] for l in levels ])
    cpms_sqr = cpms**2
    cps = atks * (defs**0.5) * (stas**0.5)
    cps = cps * cpms_sqr[:,np.newaxis]
    cps /= 10
    cps = np.floor(cps).astype(int)

    league_caps = [
        ('GL', 1500),
        ('UL', 2500),
        ('ML', 0),
    ]
    d = {}
    for league, cp_cap in league_caps:
        capped_cps = cps
        if cp_cap > 0:
            capped_cps = np.where(cps<=cp_cap, cps, 0)
        idxs = capped_cps.argmax(axis=0)
        max_league_levels = levels[idxs]
        max_league_cps = cps[[idxs], range(n_pokemon)].flatten()
        d[league] = {
            'levels': max_league_levels,
            'cps': max_league_cps,
        }
    return d

if __name__ == '__main__':
    attrs = np.array([[110,80,100], [190,147,127], [200,160,150], [250,200,210]])
    max0cps = calc_cp(attrs[:,0], attrs[:,1], attrs[:,2], 40)
    print("max0cps:\n", max0cps) #!#
    # x = find_league_pokemon(attrs[:,0], attrs[:,1], attrs[:,2])
    x = find_league_pokemon(attrs[-1,0], attrs[-1,1], attrs[-1,2])
    import pprint
    print("x:\n") #!#
    pprint.pprint(x)
