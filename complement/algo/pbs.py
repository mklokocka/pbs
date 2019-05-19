# -*- coding: utf-8 -*-
"""PBS complementation algorithm.

This module implements the PBS complementation algorithm as defined in my thesis.

"""

from typing import List, Set, Dict, FrozenSet, Tuple

from .base import ComplementationAlgorithm, States, MetaStates

import spot
import buddy


class PBS(ComplementationAlgorithm):
    """PBS.

    This class provides access to the PBS complementation algorithm.

    """

    def __init__(self, input_automaton: spot.twa_graph, args: dict = {}):
        super().__init__(input_automaton, args)

        # Add new optimization options.
        self.args.update({
            'optimizations': {
                'use_scc': True,
                'use_hopeful': True,
                'restrict_B_to_S': True
            }
        })
        # Update with actual arguments.
        self.args.update(args)

    def complement(self):
        initial_state = frozenset([self.input_automaton.get_init_state_number()]), frozenset(), frozenset()

        state_map = dict()
        state_map[initial_state] = self.output_automaton.new_state()

        self.output_automaton.set_init_state(state_map[initial_state])

        # Setup filter for successor methods depending on used optimizations.
        state_filter = lambda s: True

        if self.args['optimizations']['use_scc']:
            state_filter = lambda t: self._scc_filter(t[0], t[1])

        # Setup metastate filter for S
        metastate_filter = lambda s: True

        if self.args['optimizations']['use_hopeful']:
            metastate_filter = self._hopeful_filter

        todo = [initial_state]
        while todo:
            state_now = todo.pop(0)

            P = state_now[0]
            B = state_now[1]
            S = state_now[2]

            # We try every possible minterm. If we do not have any successors
            # we go to the "dump state" naturally.
            for minterm in self.get_minterms(buddy.bddtrue):
                new_P, _, _ = self.successors(P, minterm)
                new_B, B_marked, B_nondeterministic = self.successors(B, minterm, state_filter)
                new_S, valid = self.successors_metastates(S, minterm, state_filter, metastate_filter)

                # In this case we would have an invalid state in S, thus we do not
                # continue.
                if not valid:
                    continue

                if not self.args['optimizations']['restrict_B_to_S']:
                    leaving_B = self.B_to_S(new_B)
                else:
                    leaving_B = self.B_to_S(new_B, accepting=B_marked, nondeterministic=B_nondeterministic)

                for left_B in leaving_B:
                    accepting = False

                    possible_S = set(new_S)
                    for state in left_B:
                        if (frozenset([state]), frozenset()) not in possible_S:
                            possible_S.add((frozenset([state]), frozenset()))
                    possible_B = new_B.difference(left_B)

                    possible_B = self.trim_B(possible_B, frozenset(possible_S))

                    if not possible_B:
                        if self.args['optimizations']['use_scc']:
                            possible_B = set(filter(lambda x: self.sccs.is_accepting_scc(self.sccs.scc_of(x)), new_P))
                        else:
                            possible_B = new_P
                        accepting = True

                        possible_B = self.trim_B(possible_B, frozenset(possible_S))

                        if self.args['optimizations']['restrict_B_to_S']:
                            # Now we want any state to be able to leave B' for S'.
                            leaving_possible_B = self.B_to_S(possible_B)

                            for left_possible_B in leaving_possible_B:
                                possible_S_after_emptiness = set(possible_S)
                                for state in left_possible_B:
                                    possible_S_after_emptiness.add((frozenset([state]), frozenset()))
                                possible_B_after_emptiness = possible_B.difference(left_possible_B)

                                new_state = (
                                new_P, frozenset(possible_B_after_emptiness), frozenset(possible_S_after_emptiness))
                                if new_state not in state_map:
                                    # We got a new state to process.
                                    state_map[new_state] = self.output_automaton.new_state()
                                    todo.append(new_state)

                                if not accepting:
                                    self.output_automaton.new_edge(state_map[state_now], state_map[new_state], minterm)
                                else:
                                    self.output_automaton.new_edge(state_map[state_now], state_map[new_state], minterm, [0])
                            # We already created new states.
                            continue

                    new_state = (new_P, frozenset(possible_B), frozenset(possible_S))
                    if new_state not in state_map:
                        # We got a new state to process.
                        state_map[new_state] = self.output_automaton.new_state()
                        todo.append(new_state)

                    if not accepting:
                        self.output_automaton.new_edge(state_map[state_now], state_map[new_state], minterm)
                    else:
                        self.output_automaton.new_edge(state_map[state_now], state_map[new_state], minterm, [0])

        self.output_automaton.set_state_names(self.get_state_names(state_map))
        self.output_automaton.merge_edges()

        return self.output_automaton

    def _scc_filter(self, edge_src: int, edge_dst: int) -> bool:
        """Filter states not in the same SCC as source state and not in an accepting SCC.

        Used for the `use_scc` optimization.

        Args:
            edge_src (int): Source state as Spot integer representation.
            edge_dst (int): Destination state as Spot integer representation.

        Returns:
            bool: `True` if both states in the same SCC and `edge_dst` is in an accepting SCC, `False` otherwise.

        """
        same_scc = self.sccs.scc_of(edge_src) == self.sccs.scc_of(edge_dst)
        acc_scc = self.sccs.is_accepting_scc(self.sccs.scc_of(edge_dst))
        return same_scc and acc_scc

    def _hopeful_filter(self, metastates: MetaStates) -> bool:
        """Filter for checking for no hopeful states in metastates.

        Used for `use_hopeful` optimization.

        Args:
            metastates (`MetaStates`): Metastates we are checking.

        Returns:
            bool: `True` if all metastates contain some state from which a rejecting cycle can be reached in their
                first component, `False` otherwise.

        """
        for metastate in metastates:
            ps = metastate[0]

            # We also cut off preemptively when there are no hopeful states in the
            # powerset, if we are optimizing by hopeful states.
            if not list(filter(lambda s: self.is_hopeful_state(s), ps)):
                return False

        return True

    def B_to_S(
            self,
            B: States,
            accepting: States = None,
            nondeterministic: Set[States] = None
    ) -> FrozenSet[States]:
        """Compute possible combinations of states leaving from B to S.

        The computation either takes all subsets of B, or only subsets of the union
        of the states of B to which we got by an accepting or nondeterministic transition.

        Args:
            B (States): States in B.
            accepting (States): States in B that we got to through by an accepting transition.
            nondeterministic (States): States in B that we got to through a nondeterministic transition.

        Return:
            FrozenSet[States]: Possible combinations of states in B that will leave B for S.

        """
        powerset_of_B = self.powerset(B)

        final = powerset_of_B

        # If we are given accepting and nondeterministic successors of B, we want
        # to restrict the states moving to S only to those successors.
        if accepting and nondeterministic:
            # Flatten the targets of nondeterministic transitions to a single set.
            nondeterministic_flat = {s for states in nondeterministic for s in states}
            final = self.powerset(accepting.union(nondeterministic_flat))

        combinations = set()

        for combination in final:
            if self.args['optimizations']['use_hopeful']:
                filtered = frozenset(filter(lambda s: self.is_hopeful_state(s), combination))
            else:
                filtered = combination

            combinations.add(filtered)

        return frozenset(combinations)

    @staticmethod
    def trim_B(B: States, S: MetaStates) -> States:
        """Trim B of singletons in S.

        Trims B by going over the metastates in S of which the first component
        is a singleton and the second one is an empty set.

        Args:
            B (`FrozenSet[int]`): Set B.
            S (`FrozenSet[int]`): Set S.

        Returns:
            `FrozenSet[int]`: Set B trimmed of the singleton states from S.
        """
        return B.difference({list(s)[0] for (s, _) in filter(lambda x: len(list(x)[0]) == 1 and not list(x)[1], S)})

    @staticmethod
    def get_state_names(
            state_map: Dict[Tuple[States, States, MetaStates], int]
    ) -> List[str]:
        """Get state labels.

        Get nice names for states for better, human understandable output.

        Args:
            state_map (`Dict[Tuple[FrozenSet[int],
                FrozenSet[int], FrozenSet[FrozenSet[int], FrozenSet[int]]], int]`):
                Map from states described by the P, B, S sets to their integer representation in Spot.

        Returns:
            `List[str]`: List of names in the order given in `state_map`.

        """
        labels = []
        for (P, B, S), state in state_map.items():
            P_label = list(P)
            B_label = list(B)
            S_label = [(list(x), list(y)) for (x, y) in S]
            labels.append(str((P_label, B_label, S_label)))

        return labels
