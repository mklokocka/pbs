# -*- coding: utf-8 -*-
"""Base for complementation algorithms.

This module provides an abstract class for specific complementation algorithms to
inherit. It provides basic input operations (storing the input automaton, getting its
SCCs, and creating a new automaton to manipulate having the same BDD dictionary,...) and
basic helper functions for generating complements with our algorithms.

"""

import abc

from itertools import combinations, chain
from typing import Any, List, Iterable, Set, FrozenSet, Tuple, Callable

import spot
import buddy

BDD = Any
States = FrozenSet[int]
MetaStates = FrozenSet[Tuple[FrozenSet[int], FrozenSet[int]]]


class ComplementationAlgorithm(abc.ABC):
    """Base class for complementation algorithms.

    Most notably, this class does some basic manipulations with the input
    automaton, like getting its SCCs and creating a new output automaton with
    the same BDD dicitonary. It also stores any arguments related to possible
    switches (for example for optimizations).

    Attributes:
        input_automaton (`spot.twa_graph`): Input automaton for the algorithm.
        args (`dict`): Optional arguments.
        sccs (`spot.scc_info`): SCC information of the input automaton.
        output_automaton (`spot.twa_graph`): Output automaton of the algorithm.
        all_aps (`BDD`): BDD representing all possible APs used in the input automaton.
        cache (`dict`): Dictionary for any caching required by the algorithm.

    """

    @abc.abstractmethod
    def __init__(self, input_automaton: spot.twa_graph, args: dict = {}):
        # Check whether the input is a Buchi automaton.
        if not input_automaton.acc().is_buchi():
            raise ValueError('Input automaton must be Buchi')

        self.input_automaton = input_automaton#spot.scc_filter_states(input_automaton, True)
        self.args = {}
        self.args.update(args)

        # Get SCCs of the input automaton.
        self.sccs = spot.scc_info(self.input_automaton)
        self.sccs.determine_unknown_acceptance()

        # Create a new automaton for output with the same BDD dictionary.
        bdict = spot.make_bdd_dict()
        self.output_automaton = spot.make_twa_graph(bdict)

        # Copy APs of the input automaton to the output one.
        self.output_automaton.copy_ap_of(self.input_automaton)

        # Set basic Buchi acceptance.
        self.output_automaton.set_acceptance(1, "Inf(0)")

        # Prepare helper for minterms (all APs).
        self.all_aps = buddy.bddtrue
        # All possible minterms.
        conds = set()
        for edge in self.input_automaton.edges():
            conds.add(edge.cond)
        for cond in conds:
            self.all_aps &= buddy.bdd_support(cond)

        self.cache = {}

    @abc.abstractmethod
    def complement(self):
        """Run the complementation algorithm.

        The main method which runs the complementation.

        """
        pass

    def get_minterms(self, label: BDD) -> List[BDD]:
        """Get minterms for a given label.

        Get all the minterms that are represented by a given BDD label.

        Args:
            label (`BDD`): Label (such as `a & !b`) represented as a BDD var.

        Returns:
            `List[BDD]`: List of all possible minterms (represented as BDD vars)
                for the given label.

        """
        cached = self.cache.setdefault('minterms', dict())

        if label in cached:
            return cached[label]

        minterms = []

        all_ = label

        while all_ != buddy.bddfalse:
            one = buddy.bdd_satoneset(all_, self.all_aps, buddy.bddfalse)
            all_ = all_ - one
            minterms.append(one)

        cached[label] = minterms

        return minterms

    @staticmethod
    def powerset(iterable: Iterable[Any]) -> Iterable[Iterable[Any]]:
        """Create a powerset of an iterable object.

        This is handy when trying any possible subset of a set of states
        when generating states in the output automaton.

        Args:
            iterable (`Iterable[Any]`): Any iterable.

        Returns:
            `Iterable[Iterable[Any]]`: An iterable on the different subsets of
                the input `iterable`.

        Examples:
            >>> ComplementationAlgorithm.powerset([1,2,3])
            () (1,) (2,) (3,) (1,2) (1,3) (2,3) (1,2,3)

        """
        s = list(iterable)
        return chain.from_iterable(combinations(s, r) for r in range(len(s) + 1))

    def is_hopeful_state(self, s: int) -> bool:
        """Check if state `s` is hopeful.

        Checks if the state `s` is hopeful - that is a rejecting cycle is reachable from
        `s` in the SCC of this state.

        The check constructs a new temporary automaton, starting from state `s`. It
        adds the successors one by one, ignoring any accepting edges. Once the whole
        SCC is filled this way (all other successors lie in a different SCC),
        it tries if the automaton contains anything. If it does not, there is
        no rejecting cycle reachable from `s`.

        Args:
            s (int): State of the input automaton given by a number.

        Returns:
            `bool`: State `s` is hopeful or not.
        """
        cached = self.cache.setdefault('hopeful_states', dict())

        if s in cached:
            return cached[s]

        if not spot.scc_has_rejecting_cycle(self.sccs, self.sccs.scc_of(s)):
            cached[s] = False
            return False

        # Create a temporary automaton.
        bdict = spot.make_bdd_dict()
        temp = spot.make_twa_graph(bdict)

        temp.copy_ap_of(self.input_automaton)
        temp.set_acceptance(0, "all")

        state_map = dict()

        state_map[s] = temp.new_state()
        to_check = [s]

        while to_check:
            state = to_check.pop(0)

            for edge in self.input_automaton.out(state):
                # Follow a single SCC.
                if self.sccs.scc_of(edge.src) != self.sccs.scc_of(edge.dst):
                    continue

                if not edge.acc:
                    if edge.dst not in state_map:
                        to_check.append(edge.dst)
                        state_map[edge.dst] = temp.new_state()

                    temp.new_edge(state_map[state], state_map[edge.dst], buddy.bddtrue)

        hopeful = spot.contains(temp, 'true')

        cached[s] = hopeful
        return hopeful

    def successors(
            self,
            states: States,
            minterm: BDD,
            state_filter: Callable[[Tuple[int, int]], bool] = lambda s: True
    ) -> Tuple[States, States, Set[States]]:
        """Get successors of the given list of states for given label.

        This calculates the powerset for a given set of states and a minterm, ie. all
        the successors of the states in `states` for `minterm`.

        Also checks which of those we got to by passing an accepting edge or by a
        nondeterministic transition.

        Args:
            states (`Frozenset[int]`): Set of states.
            minterm (`BDD`): A minterm to calculate successors for.
            state_filter (`Callable[[Tuple[int, int]], bool]`, optional): Filter for
                successor states (for possible optimizations).

        Returns:
            `Tuple[FrozenSet[int], Set[int], Set[FrozenSet[int]]]`: A triple containing
                the set of all successors, a set of all successors by passing an accepting
                transition and a set of sets of the different nondeterministic successors.

        """
        cached_sets = self.cache.setdefault('successor_set', dict())
        cached_states = self.cache.setdefault('successor_state', dict())

        if (minterm, states, state_filter) in cached_sets:
            return cached_sets[(minterm, states, state_filter)]

        successors = {}
        marked = {}
        for s in states:
            if (minterm, s, state_filter) in cached_states:
                successors.update(cached_states[(minterm, s, state_filter)][0])
                marked.update(cached_states[(minterm, s, state_filter)][1])
                continue

            for edge in self.input_automaton.out(s):
                # Skip this edge if it does not contain the minterm currently handled.
                if minterm not in self.get_minterms(edge.cond):
                    continue

                # Check if state passes the state filter for any possible optimizations.
                if not state_filter((edge.src, edge.dst)):
                    continue

                successors.setdefault(s, set()).add(edge.dst)

                if edge.acc:
                    marked.setdefault(s, set()).add(edge.dst)

            cached_states[(minterm, s, state_filter)] = (
                {s: successors.get(s, set())},
                {s: marked.get(s, set())}
            )

        # Flatten all the different successors and marked successors into a single set.
        all_successors = {s for succs in successors.values() for s in succs}
        all_marked = {s for succs in marked.values() for s in succs}

        # Get nondeterministic successors of different states.
        # This seems complicated but it basically creates a set of all the
        # sets of states we got to by a nondeterministic transition for each state.
        nondeterministic = {frozenset(v) for _, v in successors.items() if len(v) > 1}

        cached_sets[(minterm, states, state_filter)] = (
            frozenset(all_successors),
            frozenset(all_marked),
            nondeterministic
        )

        return frozenset(all_successors), frozenset(all_marked), nondeterministic

    def successors_metastates(
            self,
            states: MetaStates,
            minterm: BDD,
            state_filter: Callable[[Tuple[int, int]], bool] = lambda s: True,
            metastate_filter: Callable[[MetaStates], bool] = lambda s: True
    ) -> Tuple[MetaStates, bool]:
        """Get successors of metastates in S.

        Also check whether the resulting set of metastates is valid, ie.
        there is no metastate in the form (A, A).

        Args:
            states (`FrozenSet[Tuple[FrozenSet[int], FrozenSet[int]]]`): Set of metastates.
            minterm (`BDD`): A minterm to calculate successors for.
            state_filter (`Callable[[Tuple[int, int]], bool]`, optional): Filter for
                successor states (for possible optimizations).
            metastate_filter (`Callable[[MetaStates], bool]`, optional): Filter on all
                the metastate successors. Can be used for optimizations.

        Returns:
            `Tuple[FrozenSet[Tuple[FrozenSet[int], FrozenSet[int]]], bool]`: A pair
                with the first element being the resulting set of metastates and
                the second element being a boolean of validness of the given result.

        """
        cached = self.cache.setdefault('successor_S', dict())

        if (minterm, states, state_filter) in cached:
            return cached[(minterm, states, state_filter)]

        successors = set()
        valid = True
        for s in states:
            # Since S states are pair of set of states, we need to split those,
            # calculate their successors, then put this back together.
            powerset = s[0]
            breakpoint = s[1]

            successor_powerset, marked, _ = self.successors(powerset, minterm, state_filter)
            successor_breakpoint, ignored, _ = self.successors(breakpoint, minterm, state_filter)

            successor_breakpoint = successor_breakpoint.union(marked)

            # Cut off preemptively to avoid accepting in the input automaton.
            if successor_powerset == successor_breakpoint:
                valid = False

            new = (successor_powerset, successor_breakpoint)

            if new not in successors:
                successors.add(new)

        successors = frozenset(successors)

        if not metastate_filter(successors):
            valid = False

        cached[(minterm, states, state_filter)] = (successors, valid)

        return successors, valid

