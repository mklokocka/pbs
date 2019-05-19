"""Helper module for setting up tool chains.

Provides methods to setup tool chains to use in our comparison and checks.
"""

def get_automata_generators():
    automata_script = 'python formula2aut.py -d automata/data -g -p aut -n 250 -f automata/random_ba.ltl -c'

    tools = {
        'random_ba': automata_script
    }

    return tools

def get_tools(full=True, automata=False, use_buechic=False, use_fribourg=False):
    """Prepare the tool chains

    Args:
        full     (bool, optional): All toolchains or only check ones.
        automata (bool, optional): Get tools that process automata, not ltl

    Returns:
        dict: Dictionary of tool configurations for ltlcross.
    """

    # Paths to tools.
    sem_bin     = './tools/seminator/seminator'
    ncsb_script = 'python tools/ncsb.py'
    pbs_script  = 'python ../complement/complement.py'
    buechic_jar = 'java -jar tools/buechic/buechic.jar'
    goal_bin    = './tools/goal/gc batch'

    if not automata:
        # Formula to automaton translation.
        make_tgba   = 'ltl2tgba --deterministic -B -f %f'
    else:
        # Command that translates fake ltl into random automata
        make_tgba   = 'python formula2aut.py -d automata/data %f'

    # We need an input SBA in a file for Buechic and Goal.
    input_sba = ' | autfilt -B > input.hoa && '

    # Tools
    spot        = make_tgba + ' | autfilt --complement'
    s_ncsb      = make_tgba + ' | ' + sem_bin + ' | ' + ncsb_script
    pbs         = make_tgba + ' | ' + pbs_script
    buechic     = make_tgba + input_sba + buechic_jar
    fribourg    = make_tgba + input_sba + goal_bin

    # Options
    buchi       = ' -B'
    tgba        = ' --tgba'
    fix_props   = ' | grep -v properties:'
    simp        = ' | autfilt --small --tgba'
    nos         = ' -s0' # disables Spot's simplifications used in Seminator
    end         = ' > %O' # saves result to file
    trim        = ' --trim'
    buechic_args = ' input.hoa -out output.hoa &>/dev/null'
    fribourg_args = " '$temp = complement -m fribourg input.hoa; save -c HOAF $temp output.hoa;'"
    file_output = ' && cat output.hoa'
    file_cleanup = ' && rm input.hoa output.hoa'

    ### Buechic configurations ###
    tool_chains_buechic = {
        'buechic.no': buechic + buechic_args + file_output + end + file_cleanup,
        'buechic.yes': buechic + buechic_args + file_output + simp + end + file_cleanup,
    }

    ### Fribourg configurations ###
    tool_chains_fribourg = {
        'fribourg.no': fribourg + fribourg_args + file_output + end + file_cleanup,
        'fribourg.yes': fribourg + fribourg_args + file_output + simp + end + file_cleanup,
    }

    ### Ltlcross runner configuration ###
    tools = {
        'spot_ncsb.no'       : s_ncsb + end,
        'spot_ncsb.yes'      : s_ncsb + simp + end,
        'ba_via_det.no'      : spot + buchi + end,
        'ba_via_det.yes'     : spot + buchi + simp + end,
        'tgba_via_det.no'    : spot + tgba + end,
        'tgba_via_det.yes'   : spot + tgba + simp + end,
        'pbs.no'             : pbs + end,
        'pbs.yes'            : pbs + simp + end,
    }

    if use_buechic:
        tools.update(tool_chains_buechic)

    if use_fribourg:
        tools.update(tool_chains_fribourg)

    if full:
        return tools
    else:
        return {
            'spot': tools['ba_via_det.no'],
            'pbs': pbs + trim + end
        }

def get_tool_order(use_buechic=False, use_fribourg=False):
    tool_order = ['spot_ncsb', 'ba_via_det', 'tgba_via_det']

    if use_buechic:
        tool_order.append('buechic')

    if use_fribourg:
        tool_order.append('fribourg')

    tool_order.append('pbs')

    return tool_order
