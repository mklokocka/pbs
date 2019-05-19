import argparse

import spot

from algo.pbs import PBS

spot.setup()


def main():
    parser = argparse.ArgumentParser \
      (description='Apply PBS complementation construction to an input automaton',
           allow_abbrev=True)
    parser.add_argument('file', type=str, nargs='*',
                        help='automata to process', default='-')
    parser.add_argument('--trim', action='store_true',
                        help='trim dead states in result')

    # Optimization tuning.
    parser.add_argument('-nscc', '--no_use_scc', action='store_true',
                        help='do not use SCCs to optimize transitions')
    parser.add_argument('-nhope', '--no_use_hopeful', action='store_true',
                        help='do not use hopeful states')
    parser.add_argument('-nrbts', '--no_restrict_B_to_S', action='store_true',
                        help='do not restrict states that can move from B to S '
                        'to those that are successors after an accepting or '
                        'nondeterministic transition')

    args = parser.parse_args()

    complement_args = {
        'optimizations': {
            'use_scc': not args.no_use_scc,
            'use_hopeful': not args.no_use_hopeful,
            'restrict_B_to_S': not args.no_restrict_B_to_S
        }
    }

    for aut in spot.automata(*args.file):
        try:
            pbs_algorithm = PBS(aut, complement_args)
            res = pbs_algorithm.complement()

            if args.trim:
                res = spot.scc_filter_states(res, True)

            print(res.to_str())
        except ValueError as e:
            print(f'There is a problem with the input automaton: {e}')


if __name__ == "__main__":
    main()
