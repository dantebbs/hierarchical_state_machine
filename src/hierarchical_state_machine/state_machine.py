"""
Copyright (c) 2023 by Crystal Clear Design

This intellectual property is shared to the public domain under the MIT License.
Crystal Clear Design offers no warranty and accepts no liability.
The only requirement for use is that this copyright notice remains intact.

This file contains an implementation of a hierarchical state machine processor.
It allows for a straightforward JSON-style definition of the state machine, and
includes a very convenient timer function.

The state machine is described by states, events, transitions, and actions.
Then the state machine processor automatically executes based on events.

Reserved Words:
start_state  A state required by each state machine or state with more
             than one state or sub-state, to indicate which one to enter.
end_state  A state that exists for all state machines. It cannot have
           exiting transitions, nor exit actions. Enter actions can be
           defined by the user. Enter actions will be executed after all
           other sub-state and state exit actions are executed.
exit_all_states  An event which causes the current state to run its exit
                 actions, and then all parent states to do the same.
                 No further state machine action can happen after this.
TimerManager  Is an instance that holds and processes all the active
              timers within the system.
cond  Is the dictionary entry for conditions, and the value is a string
      which will resolve to True or False when executed.
acts  Is the actions which will be taken upon: entry to a state, exit
      from a state, or during a transition. It is a list of functions
      with parameters, which will be called in the order presented.
tran  Is the dictionary entry for transitions available for exiting a
      particular state.
auto  Is a special "event", in that it always triggers / happens. There
      can only be one transition with an "auto" event unless different
      conditions are applied to each "auto" transition.
      *** IMPORTANT NOTE ***
      For situations where both an "auto" event is valid, and a specific
      event (and conditions) are valid (anywhere up the tree), the user-
      spelled-out event will be executed. This keeps "auto" as a
      convenience feature. So all user-defined transitions in the current
      state, and all parent states, are checked for event and conditions.
      If any match is found, then that transition will be taken. Only
      when no transitions are taken before getting back up to the "root"
      state, will the search re-start and look for an "auto" transition
      in the current and parent states.
root  Is a state-like entity that contains all top-most states defined
      by the user. It should NOT be referenced by the user, even though
      it will appear at the start of all state paths.
final  Is the name of any state from which there are no exiting tran-
       sitions. There can be multiple final states in a machine, but
       only one in any one state.
"""

import json
import re
import time
from datetime import datetime
import threading
from state_machine_state import state, debug_flags


# A handy function used in this module to help implement the Timer class.
get_curr_time_ms = lambda: int(round(time.time() * 1000))

# A generic timer which is instantiated at the start of a period, and which
# is destructed when finished. The resolution is 1 ms.
# param[in]  owner_machine  This is the state machine which the event will
#                           be posted to. The owner_machine.enqueue_event()
#                           method will be called.
# param[in]  event  This is a function which will be executed at the end of
#                   the (or each) period, before the object is destructed.
#                   It can be treated as a callback.
# param[in]  period_ms  The number of milliseconds until the (next) event
#                       is emitted.
# param[in]  repetitions  While repetitions is >= 1, the given period is
#                         waited and then the event is emitted. The internal
#                         counter is then decremented. If the counter is at
#                         zero, then the object instance is done (destructed).
#                         A special case is added, if repetitions is negative,
#                         then the timer runs forever, emitting an event after
#                         each period.
class timer_ms:
    def __init__(self, timer_id: int, owner_machine: object, event: str, period_ms: int, repetitions = 1) -> None:
        self.timer_id = timer_id
        self.owner_machine = owner_machine
        self.event = event
        self.period_ms = period_ms
        self.repetitions = repetitions
        self.next_event_time_ms = get_curr_time_ms() + self.period_ms

    def check_for_timeout(self) -> None:
        curr_time_ms = get_curr_time_ms()
        if curr_time_ms >= self.next_event_time_ms:
            self.repetitions -= 1
            if self.repetitions > 0:
                # Update the timer to react to the next period.
                self.next_event_time_ms += self.period_ms
            else:
                self.owner_machine.rem_timer(self)
                # Remove the current timer before queueing up the resulting
                # event to avoid complications of "overlapping" timers.
            self.owner_machine.enqueue_event(self.event)

    def get_id(self) -> int:
        return self.timer_id

    def get_evt(self) -> str:
        return self.event

# See note below about minimum sleep time.
timer_resolution_ms = 20
# Do a 1-sec watchdog, but divide by 20 because of tick resolution.
watchdog_period_ms = int(1000 / timer_resolution_ms)
class timer_manager:
    def __init__(self) -> None:
        self.timers = []
        self.next_avail_timer_id = 0
        self.quit_flag = False
        global watchdog_period_ms
        self.watchdog_ms = watchdog_period_ms
        self.timers_thread = threading.Thread(target = self.run_timers)
        self.timers_thread.start()

    def run_timers(self) -> None:
        while (not self.quit_flag):
            # Wait 20 milliseconds.
            # A 1-ms time was desired, but it turns out that on Windows 10 and
            # python 3.10.9, the minimum sleep time is somewhere between 10 ms
            # and 13 ms, so we have to use larger chunks and suffer the loss
            # in resolution.
            time.sleep(timer_resolution_ms / 1000)
            
            # Check for time-out on each active timer.
            for timer in self.timers:
                timer.check_for_timeout()

            # Make sure the thread hasn't been abandoned.
            self.watchdog_ms -= 1
            if self.watchdog_ms <= 0:
                print(f"Error: Timer thread exiting because process_events() wasn't called often enough.")
                self.quit_flag = True

    def add_timer(self, owner_machine: object, event: str, period_ms: int, repetitions = 1) -> int:
        new_timer_id = self.next_avail_timer_id
        new_timer = timer_ms(new_timer_id, owner_machine, event, period_ms, repetitions)
        self.next_avail_timer_id += 1
        self.timers.append(new_timer)
        #print(f"  timr: added timer {new_timer_id}, event {event}, period {period_ms}, reps {repetitions}")
        return new_timer_id

    def rem_timer(self, old_timer: object) -> None:
        #print(f"  timr: removing timer {old_timer.timer_id}, event {old_timer.event}, period {old_timer.period_ms}, remaining reps {old_timer.repetitions}")
        self.timers.remove(old_timer)
        return
        
    def rem_timer_by_id(self, timer_id: int) -> bool:
        for timer in self.timers:
            if timer.get_id() == timer_id:
                self.rem_timer(timer)
                return True
        return False

    def rem_timer_by_evt(self, event: str) -> bool:
        for timer in self.timers:
            if timer.get_evt() == event:
                self.rem_timer(timer)
                return True
        return False

    def feed_dog(self) -> None:
        global watchdog_period_ms
        self.watchdog_ms = watchdog_period_ms
        return

    def cleanup(self) -> None:
        self.quit_flag = True
        self.timers_thread.join()
        return

# In most ways, the state machine is just a glorified, special-case, of a regular
# state. The state heirarchy is stored in a state named "root", and this class
# implements the basic algorithm that processes events.
class state_machine:
    # Parse through the JSON-formatted definition of a state machine in preparation
    # for executing events and transitions.
    # param[in]  machine_definition  Must be a valid JSON format, and contain top-level
    #            keys of "events", "actions", "states", and "transitions". See example
    #            below.
    #            "events" and "actions" are global to the whole state machine, and are
    #            only allowed at the top level... so they must all be uniquely named.
    #            The usual C/C++ type naming conventions for variables and functions
    #            apply (start with letter or underscore, followed by letters, under-
    #            scores, and digits).
    #            The "states" must be uniquely named for the level they are at. If a
    #            state name is re-used, it is disambiguated using the full "path"
    #            (top state and sub-states).
    #            "transitions" are specific to each state, and are uniquely identified
    #            by the combination of (sub) state and event.
    # param[in]  period_ms  This determines how often the state machine will check for
    #            events and process them. 1 ms is often a good number, as it gives a
    #            fast response to events without overloading your CPU.
    def __init__(self, machine_definition: dict, callback_module: object, period_ms = 1) -> None:
        self.machine_defined = False
        self.machine = {}
        self.root_state = None
        self.curr_state = None
        self.curr_state_name = ""
        self.events_lock = threading.Lock()
        self.incoming_events = []
        self.processing_period = period_ms * 0.001
        self.last_processing_time = datetime.now().timestamp()
        self.timer_manager = timer_manager()
        self.callback_module = callback_module

        try:
            self.machine = json.loads(machine_definition)
            self.machine_defined = True
            
            # Validate Events
            num_events = 0
            if "events" in self.machine:
                num_events = len(self.machine["events"])
            else:
                print("Error: the state machine has no events defined!")
                self.machine_defined = False

            # Instantiate States
            self.root_state = state("root", None, self.machine, self.callback_module)
            
            # Validate States
            self.curr_state = self.root_state.get_start_state()
            if not self.curr_state:
                print(f"Error: the state machine has no start state!")
                self.machine_defined = False
                return
            self.curr_state_name = self.curr_state.get_path()
            num_states = 1
            # TODO: Count and report the number of states created.
            #num_states = self.root_state.count_all_states()
                
            # Validate Transitions
            num_transitions = 1
            # TODO: Count and report the number of transitions created.
            # TODO: Verify that each state and sub-state transition goes
            #       to a defined state somewhere in the tree.
            #num_transitions = self.root_state.count_all_transitions()
            if num_transitions < num_states - 1:
                print(f"Error: the state machine has insufficient transitions {num_transitions}, for {num_states} states!")
                self.machine_defined = False
                return

            if (num_events > 0) and (num_states > 0):
                debug_flags.print("machine_parse", f"Successfully parsed {num_events} events, {num_states} states, and {num_transitions} transitions.")
        except json.JSONDecodeError as err:
            print(f"JSON decoding error at char {err.pos}, line {err.lineno}, column {err.colno}.")
            print(err.msg)
            self.machine_defined = False

        if not self.machine_defined:
            print(f"State machine not defined. Unable to continue.")
            self.cleanup()
            
        return

    # Adds a timer and automatically starts it. The indicated event will be produced
    # when the specified time has elapsed after this call (unless it is removed).
    def add_timer(self, event: str, period_ms: int, repetitions = 1) -> None:
        timer_id = self.timer_manager.add_timer(self, event, period_ms, repetitions)
        return timer_id

    def rem_timer(self, dead_timer: timer_ms) -> None:
        self.timer_manager.rem_timer(dead_timer)
        return

    def rem_timer_by_id(self, timer_id: int) -> None:
        self.timer_manager.rem_timer_by_id(timer_id)
        return

    def rem_timer_by_evt(self, event: str) -> None:
        self.timer_manager.rem_timer_by_evt(event)
        return

    # This is used to signal to the state machine that a new event has
    # occurred and needs to be processed.
    #
    # param[in]:  new_event  This must be one of the events supplied in the
    #             state machine definition at this object's instantiation.
    #
    # returns: True if it is a recognized event and the machine is properly
    #          defined.
    def enqueue_event(self, new_event: str) -> bool:
        ret_val = False
        
        if not self.machine_defined:
            return ret_val

        self.events_lock.acquire(blocking=True, timeout = self.processing_period)
        
        events = self.machine["events"]
        if new_event in events:
            self.incoming_events.append(new_event)
            ret_val = True

        self.events_lock.release()
        return ret_val

    # Go through the queued events and process them.
    # This must be called on a regular basis. Somewhere between 20 and 200 ms
    # period is usually good.
    #
    # Side-effects:
    # * The state machine may be in a new state on return.
    # * Functions outside of the state machine (actions) may get called.
    # * The state machine may pass through multiple states and run many
    #   actions at different levels in the hierarchy during this call.
    #
    # returns: True if the machine is properly defined.
    def process_events(self) -> bool:
        if not self.machine_defined:
            return False

        self.timer_manager.feed_dog()

        # Now process all events in the queue.
        # The event only matters if there is a relevant transition for the current state.
        self.events_lock.acquire(blocking=True, timeout = self.processing_period)

        # Start with the current state, and work our way up the tree of parent states,
        # until we find a match with either the "auto" event, or the next event in the
        # queue.
        examine_state = self.curr_state
        event_to_process = ""
        process_result = ""
        #print(f"  [{examine_state.get_path()}] proc:")
        if examine_state.get_path().split('.')[-1] != "final":
            # Process any events in the queue.
            if len(self.incoming_events) > 0:
                while (len(self.incoming_events) > 0):
                    event_to_process = self.incoming_events[0]
                    # Consume the event at this point.
                    self.incoming_events.pop(0)
                    process_result = self.curr_state.process_event(event_to_process)
                    if process_result != "":
                        break;
                        
            # Check for an "auto" event if no transition fired.
            if process_result == "":
                process_result = self.curr_state.process_event("auto")

        if process_result != "":
            # TODO: Add the recursive descent into sub-states.
            # TODO: Decide if this should move to the transition execution section.
            # We are just completing a transition into a new state.
            self.curr_state = self.get_state_by_path(process_result)
            # Run the new state's entry functions.
            self.curr_state = self.curr_state.enter()

        self.last_processing_time = datetime.now().timestamp()
        
        self.events_lock.release()
        return True

    def get_state_by_path(self, state_path: str) -> object:
        requested_state = None
        curr_search_state = self.root_state
        path_states = state_path.split('.')
            
        level_searching = 1
        while level_searching < len(path_states):
            sub_state = curr_search_state.get_sub_state(path_states[level_searching])
            if sub_state:
                level_searching += 1
                curr_search_state = sub_state
            else:
                break;
        
        if level_searching == len(path_states):
            requested_state = curr_search_state

        return requested_state
    
    def get_curr_state_name(self) -> str:
        return self.curr_state.get_name()

    # This is required to stop the timer threads.
    # It also does a proper hierarchical exit of
    # the current state and all parent states.
    def cleanup(self):
        self.timer_manager.cleanup()
        self.enqueue_event("exit_all_states")
        self.process_events()
        return

    # Limit the processing rate so the caller can just call from a
    # simple loop without the CPU bogging down 100%.
    def process_events_rate_limited(self) -> bool:
        curr_time = datetime.now().timestamp()
        delt_time = curr_time - self.last_processing_time
        wait_time = self.processing_period - delt_time
        if (wait_time > 0):
            time.sleep(wait_time)
        return self.process_events()
        
