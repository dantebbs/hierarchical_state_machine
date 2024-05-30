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
       sitions. There can be multiple final states in a machine.
"""

import re
import inspect


# Some global flags which the user can set to help with debugging.
# Flags used by the state_machine module:
#
# "machine_parse" shows what the parser finds during the initialization of the
#                 state machine.
#
class debug_flags_cl:
    def __init__(self) -> None:
        self.flags = []
        return

    def set(self, flag_name: str) -> None:
        self.flags.append(flag_name)
        return

    def get(self, flag_name: str) -> bool:
        return flag_name in self.flags

    def clear(self, flag_name: str) -> None:
        self.flags.remove(flag_name)
        return
        
    def print(self, flag_name: str, text: str) -> bool:
        did_print = False
        if self.get(flag_name):
            print(text, end='')
            did_print = True
        return did_print


# Notes:
# For the library client, these calls look like state_machine.debug_flags.set("use_level_indenting")
# For the "machine_parse" flag, it must be set before you instantiate state_machine(...).
debug_flags = debug_flags_cl()
debug_flags.set("use_level_indenting")
#debug_flags.set("show_short_state_names")
#debug_flags.set("machine_parse")
#debug_flags.set("execution_details") # This one is verbose!
#debug_flags.get("activation_checks")
debug_flags.set("entry_exit")
debug_flags.set("actions_taken")


# A convenience routine to search for functions of the given names.
# The current code space is searched for functions and parameters
# matching the given names, and if valid, the functions are called in
# the order provided.
# param[in]  user_funcs  Defines functions to be called, and their
#                        parameters.
#                        Example, a state containing this definition:
#                        "entry": [
#                          "set_traf_light(blink_yel)",
#                          "set_ped_light(red, 0)"
#                        ]
#                        would cause first the set_traf_light function
#                        to be called with 1 parameter of blink_yel,
#                        followed by the set_ped_light function to be
#                        called with 2 parameters of red, and zero.
def run_user_functions(user_funcs: list, callback_module: object) -> bool:
    all_funcs_returned_true = True

    for potential_function in user_funcs:
        # The function and any parameters must be in valid python syntax.
        # Check that while simultaneously breaking out the function name
        # and the parameters.
        match = re.search("^([a-zA-Z_]\w*)\((.*(,.*)*)\)$", potential_function)
        if match:
            function_name = match.group(1)
            # Validate the parameters? This might be handy, but it might be overkill, too.
            # param_match = re.search("^([a-zA-Z_]\w*)|(\".*\")|(\'.*\')|(0x[0-9a-fA-F]+)|([+\-]?\d+)$")
            params = match.group(2)
            debug_flags.print("actions_taken", f"  Calling {function_name}({params})\n")

            func = getattr(callback_module, function_name)
            if func:
                func(params)
            else:
                raise NotImplementedError(f"Function {function_name}() not implemented!")

    return all_funcs_returned_true

# Example Transition Definition
#        "one_second": {
#          "acts": [
#            "set_ped_light(yel)"
#          ],
#          "dest": "Crossing Countdown"
#        },
class transition:
    def __init__(self, source_state: object, event_name: str, transition_definition: dict, callback_module: object, level: int) -> None:
        assert isinstance(source_state, state)
        self.source_state = source_state
        self.event_name = ""
        self.conditions = []
        self.actions = []
        self.destination_state = None
        self.callback_module = callback_module
        self.level = level

        num_transitions = len(list(transition_definition))
        assert num_transitions > 0

        if "dest" not in transition_definition:
            assert not f"Error! Invalid transition \"{self.event_name} from state {self.source_state.get_path()}\""
            return

        self.event_name = event_name
        self.destination_state = transition_definition["dest"]

        if "cond" in transition_definition:
            self.conditions = transition_definition["cond"]
            
        if "acts" in transition_definition:
            self.actions = transition_definition["acts"]

        return

    def get_event(self) -> str:
        return self.event_name

    def get_destination_state(self) -> str:
        return self.destination_state

    def would_activate(self, event_name: str) -> bool:
        assert(event_name != "")
        would_activate_flag = False
        
        if event_name == self.event_name:
            would_activate_flag = run_user_functions(self.conditions, self.callback_module)

        if debug_flags.get("activation_tests"):
            debug_flags.print("execution_details", f"    Would activate={would_activate_flag}, event={event_name}, cond={self.conditions}")

        return would_activate_flag

    # Warning! This executes the transition even if the conditions currently fail!
    #          The caller must check would_activate(...) first!
    def execute(self, event_name) -> str:
        new_sub_state_name = ""

        debug_flags.print("execution_details", f"__sm tran: \"{self.source_state.get_path()}\" -> \"{event_name}\" + cond {self.conditions} => acts {self.actions} + {{{self.get_destination_state()}}}].\n")
        run_user_functions(self.actions, self.callback_module)
        self.source_state.exit()
        new_sub_state_name = self.get_destination_state()

        return new_sub_state_name

    def __str__(self) -> str:
        transition_as_string = f"tran: {self.event_name}"

        if len(self.conditions) > 0:
            transition_as_string += f", cond={self.conditions}"
            
        if len(self.actions) > 0:
            transition_as_string += f", acts={self.actions}"

        transition_as_string += f" -> {{{self.destination_state}}}"

        return transition_as_string

# Example State Definition
#    "Crossing Countdown": {
#      "tran": {
#        "one_second": {
#          "acts": [
#            "update_ped_time()"
#          ],
#          "dest": "Crossing Countdown"
#        },
#        "countdown_complete": {
#          "dest": "Traffic Flowing"
#        }
#      }
#    }
class state:
    def __init__(self, state_name: str, parent_state: object, state_definition: dict, callback_module: object, level=0) -> None:
        self.path = state_name
        if parent_state:
            self.path = parent_state.get_path() + '.' + state_name
        self.parent_state = parent_state
        self.start_state = None
        self.sub_states = []
        self.transitions = []
        self.vars = {}
        self.entry_funcs = []
        self.exit_funcs = []
        self.callback_module = callback_module
        self.level = level

        # Check for sub-states.
        # Identify the starting state while we're at it.
        start_state = None
        if "states" in state_definition:
            # Decode each sub-state.
            for sub_state_name in state_definition["states"]:
                sub_state_definition = state_definition["states"][sub_state_name]
                new_state = state(sub_state_name, self, sub_state_definition, self.callback_module, level + 1)
                self.sub_states.append(new_state)
                
            # Validate start for various numbers of sub-states.
            if len(self.sub_states) > 1:
                # Make sure a start state is defined.
                for sub_state in self.sub_states:
                    sub_state_path = sub_state.get_path().split('.')
                    if sub_state_path[-1] == "start":
                        self.start_state = sub_state
                if not self.start_state:
                    print(f"Error: the {self.path} state has multiple sub states, but no start state!")
            if len(self.sub_states) == 1:
                self.start_state = self.sub_states[0]

        if "entry" in state_definition:
            self.entry_funcs = state_definition["entry"]

        if "tran" in state_definition:
            transitions = state_definition["tran"]
            for event_name in transitions:
                self.transitions.append(transition(self, event_name, transitions[event_name], self.callback_module, level))

        if "exit" in state_definition:
            self.exit_funcs = state_definition["exit"]

        if self.level > 0:
            debug_flags.print("machine_parse", str(self))

        # Make sure the start state has a transition into a user-defined state.
        if len(self.sub_states) == 1:
            # If there is only one sub-state, make sure there is a transition into it.
            single_sub_state_name = self.sub_states[0].get_full_path()
            has_transition = False
            for check_transition in self.transitions:
                if check_transition.get_destination_state() == single_sub_state_name:
                    has_transition = True
                    break
                    
            if not has_transition:
                print(f"Error: the {self.path} state has no starting transition.")

        return

    # Returns a reference to itself (if no further state change), or to the new
    # state, if it auto-enters into a sub-state.
    def enter(self) -> object:
        debug_flags.print("enter_exit", f"[{self.get_path()}] Entering\n")

        run_user_functions(self.entry_funcs, self.callback_module)
        return_state = self

        # In this newly entered state, check to see if there is a sub-state to auto-
        # transition in to.
        first_state = self.get_sub_state("start")
        if first_state:
            potential_new_state_name = first_state.process_event("auto")
            print(f"potential_new_state_name={potential_new_state_name}")
            if potential_new_state_name != "":
                return_state = self.get_sub_state(potential_new_state_name)
                return_state.enter()

        return return_state

    def exit(self) -> None:
        debug_flags.print("enter_exit", f"[{self.get_name()}] Exiting\n")
        run_user_functions(self.exit_funcs, self.callback_module)
        return

    def get_path(self) -> str:
        return self.path

    def get_name(self) -> str:
        if debug_flags.get("show_short_state_names"):
            return self.path.split('.')[-1]
        else:
            return self.path

    def get_start_state(self) -> object:
        return self.start_state

    def get_transitions(self) -> dict:
        return self.transitions

    def process_event(self, event_to_process: str) -> object:
        new_state_path = ""

        for transition in self.transitions:
            if transition.would_activate(event_to_process):
                debug_flags.print("transitions", f"[{self.get_name()}] transitioning via {transition.event_name}, {transition.conditions}, {transition.actions}, {transition.destination_state}\n")
                new_state_path = transition.execute(event_to_process)
                if new_state_path.find('.') == -1:
                    # Allow for sub_state_path to be just the name of the most-nested state
                    # being referenced, so that the machine definition remains much more
                    # readable.
                    new_state_path = self.parent_state.path + '.' + new_state_path
                break;

        if new_state_path == "" and event_to_process != "auto" and self.parent_state:
            # After checking for regular event activities, check for any automatic
            # transitions using a (single-level) recursive call.
            new_state_path = self.parent_state.process_event("auto")

        if new_state_path == "" and self.parent_state:
            # If neither the event nor "auto" triggered, then try again at a higher
            # level with the parent state (unless already at root).
            # Uses a (multi-level) recursive call to potentially visit all parents.
            new_state_path = self.parent_state.process_event(event_to_process)

        return new_state_path

    def get_sub_state(self, sub_state_path: str) -> object:
        sub_state = None
        if sub_state_path != "root" and sub_state_path.find('.') == -1:
            # Allow for sub_state_path to be just the name of the most-nested state
            # being referenced, so that the machine definition remains much more
            # readable.
            sub_state_path = self.get_path() + '.' + sub_state_path
        for sub_state_check in self.sub_states:
            if sub_state_check.get_path() == sub_state_path:
                sub_state = sub_state_check
                break;

        return sub_state

    def count_sub_states(self) -> int:
        count = len(self.sub_states)
        return count

    def __str__(self) -> str:
        indent_str = ''
        if debug_flags.get("use_level_indenting"):
            # Don't indent for root or 1st level states.
            if self.level > 0:
                indent_str = '  ' * ( self.level - 1 )

        name = self.get_name()

        state_as_string  = f"{indent_str}{{{name}}}\n"
        if len(self.entry_funcs):
            state_as_string += f"{indent_str}  entr: {self.entry_funcs}\n"

        for transition in self.transitions:
            state_as_string += f"{indent_str}  {transition}\n"

        if len(self.exit_funcs):
            state_as_string += f"{indent_str}  exit: {self.exit_funcs}\n"

        return state_as_string

