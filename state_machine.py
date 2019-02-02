#!/usr/bin/env python3

import random
import sys
import time
import unittest

# TODO:
# https://stackoverflow.com/questions/865115/how-do-i-correctly-clean-up-a-python-object
# Convert to only allow using with so can't construct and forget
# slots if can - really could be good
# Builder pattern for transition and/or state machine
# Think about error handling - currently we don't

_="""

We observe there are probably several big things in a state machine
The set of states (nodes)
The set of events/triggers (possible edge values)
A transition table or some way of saying in a particular state
when we receive a trigger/event whether we have that edge on
this node and can move to a new state and what that new state is.

How to attach actions to edges etc?

"""

# Example for receiver in esp8266 project

states = ["recv_ask_wait", "waiting"]
events = ["request_data", "recv_data", "set_output", "send_ack", "wait"]

states = {"recv_ask_wait", "waiting"}

# "from": {
#   "event_type": ("to", callback(event_type, event)),
# where event is a an optionally None object that may be passed too
#   ...

transitions = {
        "recv_ask_wait": {
            "request_data": ("recv_ask_wait", None),
            "recv_data": ("waiting", None),
            },
        "waiting": {
            "recv_data": ("waiting", None),
            "wait": ("waiting", None),
            },
        }

def random_item(l):
    assert len(l) > 0
    return l[random.randint(0, len(l) - 1)], None

def transition(state, event_type, event = None):
    assert state in transitions
    if event_type not in transitions[state]:
        raise RuntimeError("State " + str(state) +
                " has no transition for this event " + str(event_type))
    new_state, callback = transitions[state][event_type]
    if callback is not None:
        callback(event_type, event)
    return new_state

class TestTransitions(unittest.TestCase):
    def test(self):
        # Yes this is bad practice as one case here test multiple things
        s1 = "s1"
        s2 = "s2"
        e1 = "e1"
        e2 = "e2"
        e3 = "e3"

        trans = Transitions(s1)
        trans.add_transition(e1, s1)
        # Overwriting not implemented/allowed
        self.assertRaises(RuntimeError, trans.add_transition, e1, s1)
        # For order testing of callbacks
        i = 0
        def inc():
            nonlocal i
            i += 1
        def mul():
            nonlocal i
            i *= -1
        trans.add_transition(e2, s2, [inc, mul])

        self.assertTrue(e1 in trans)
        self.assertTrue(e2 in trans)
        self.assertTrue(e3 not in trans)
        self.assertEqual(trans.transition(e1), s1)
        self.assertEqual(trans.transition(e2), s2)
        self.assertEqual(i, -1)

class Transitions:
    def __init__(self, start_state):
        self._start_state = start_state
        self._transitions = {} # event -> (dst, callbacks)
    def add_transition(self, event, dst, callbacks = None):
        if event in self._transitions:
            raise RuntimeError("May not overwrite transition for " + str(event))
        self._transitions[event] = (dst, [] if callbacks is None else callbacks)
    def __contains__(self, event):
        """
        >>> "event_type_1" in transitions
        """
        return event in self._transitions
    def transition(self, event):
        # NOTE: do not allow yourself to change this and intro a test what you
        # would change to version of this function, will cause race condition
        # weirdness with timers.
        # Eg. print("Going to", transitions.would_transition_to(event))
        # new_state = transitions.transition(event) # new_state != printed as
        # timer expired
        # Possible other races in this class but I think by moving stuff like
        # network timeout to higher up then we avoid dealing with it (confused)
        if event not in self._transitions:
            raise RuntimeError("No transition for event:" + str(event))
        dst, callbacks = self._transitions[event]
        for f in callbacks:
            f()
        return dst
    def __str__(self):
        return ",".join("".join(("{", str(event), "->", str(dst), "}"))
                for event, dst in self._transitions.items())

# Based on
# http://code.activestate.com/recipes/52308-the-simple-but-handy-collector-of-a-bunch-of-named/?in=user-97991

# TODO: improve name of this (store, scratch_space, struct, data, empty_class?)
class Bunch:
    """Struct like class for passing data around by member attributes
    >>> store = Bunch()
    >>> store.data = "FOSS"
    # Pass store to something, use store.data, etc...
    >>> store.reset()
    # Data member is no more
    """

    def __init__(self):
        self.__dict__["_added_attrs"] = set()

    def reset(self):
        """Erases any attributes the user created on this instance"""
        for attr in self._added_attrs:
            self.__delattr__(attr)

    def __getattribute__(self, name):
        return super().__getattribute__(name)

    def __setattr__(self, name, value):
        assert name != "_added_attrs"
        if not name.startswith("_"):
            self._added_attrs.add(name)
        super().__setattr__(name, value)

class StateMachine:

    def __init__(self, *, initial_state):
        self._state_to_transitions = {}
        self._state = initial_state
        # Need way to send additional state to callbacks. Cannot think of a way
        # to neatly do it via arguments. So instead the StateMachine has a
        # store() method that can be called to get an object that can be used as
        # storage/scratch space and will be reset between calls. The disad
        self._store = Bunch()

    def add_transition(self, src, transitions):
        self._state_to_transitions[src] = transitions

    def next(self, event):
        self._store.reset()
        transitions = self._state_to_transitions[self._state]
        self._state = transitions.transition(event)
        return self.state()

    def state(self):
        return self._state

class Thing:

    def __init__(self, sock):
        self.sm = StateMachine(
                initial_state = "recv_ask_wait"
                )
        self.sm.add_transition("recv_ask_wait", None, "recv_ask_wait", callbacks = [request_data])
        self.sm.add_transition("recv_ask_wait", "recv_bad_data", "waiting")
        self.sm.add_transition("recv_ask_wait", "recv_data", "waiting", callbacks = [process_data])
        self.sm.event_generator(get_input_from_network)

        self.sm.add_transition("waiting", None, "waiting")
        self.sm.add_transition("waiting", "recv_data", "waiting",
                callbacks = [process_data, reset_timeout])
        self.sm.add_transition("waiting", "recv_bad_data", "waiting")
        self.sm.add_transition("waiting", "timed_out", "recv_ask_wait")
        self.sm.event_generator(get_input_from_network_else_timeout)

        # Remember special case last event "done"
        # Clear .data afterward

        self.sock = sock

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):


    def process_data(self):
        data = self.sm.data.msg
        self.set_output(data)
        self.send_ack(data)
    def request_data(self):
        # Send request of data to sender
        pass

    def reset_timeout(self):
        pass
    def timed_out(self):
        pass

    def get_input_from_network(self):
        #MSG_LEN = 9
        # Strongly dislike passing state through member vars rather than as (freer) functions
        msg = sock.read(MSG_LEN)
        self.sm.data.msg = msg
        # Timed out on read
        if msg is None:
            return None
        elif len(msg) == 0:
            return "done"
        elif len(msg) != MSG_LEN:
            return "recv_bad_data"
        else:
            return "recv_data"

    def get_input_from_network_else_timeout(self):
        event = self.get_input_from_network()
        if event != "recv_data" and self.timed_out():
            return "timed_out"
        return event

def main(argv):
    pass

    # sock = socket()
    # t = Thing(sock, timeout)
    # while True:
    #     event = t.generate_event()
    #     new_state = t.transition(event)
    #     input()

    # while True:
    #     event_type, event = random_item(list(transitions[state].keys()))
    #     print("State", state, "received event of type", event_type)
    #     state = transition(state, event_type, event)
    #     print("New state:", state)
    #     input()

if __name__ == "__main__":
    sys.exit(main(sys.argv))
