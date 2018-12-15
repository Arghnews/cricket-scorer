#!/usr/bin/env python3

import random
import sys
import time

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

    sock = socket()
    t = Thing(sock, timeout)
    while True:
        event = t.generate_event()
        new_state = t.transition(event)
        input()

    # while True:
    #     event_type, event = random_item(list(transitions[state].keys()))
    #     print("State", state, "received event of type", event_type)
    #     state = transition(state, event_type, event)
    #     print("New state:", state)
    #     input()

if __name__ == "__main__":
    sys.exit(main(sys.argv))
