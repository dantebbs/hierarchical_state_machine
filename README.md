<h1 align="center">
Crystal Clear Design's Hierarchical State Machine for Python
</h1><br>

# hierarchical_state_machine
This python library provides an easy-to-learn and easy-to-use API for using Hierarchical State Machines in your project. The state machine is defined using a basic JSON string, and includes convenience timers.

- **Source code:** https://github.com/dantebbs/hierarchical_state_machine

## Simplest Example
The Blinky Light

## Countdown Example
Fireworks

## A More Involved Example
A Hierarchical State Machine Implementing a Simple Crosswalk Controller

1. Get the location of the examples:
    `python -m pip show hierarchical_state_machine`
2. Go to the example folder:
    `cd <site-packages>/hierarchical_state_machine/example/pedestrian_crosswalk/`
3. Look at the state machine diagram:
    `hierarchical_example_pedestrian_crosswalk_signaler.pdf`
4. Execute and follow along:
    `python crosswalk_light_simulator.py`
5. Press the `b` button to request a crossing.
6. Press the `Esc` button to exit the simulation.

## A Tutorial
Here are details about creating a hierarchical state machine in python.

### Components of a State Machine
> Events - Are user inputs, timeouts, code-generated, or an output of another state machine.
> States - A state machine waits in a state until an event or condition causes a transition to another state.
> Transitions - Are paths gated by events and/or conditions, to go to another state.
> Actions - Are behaviors (i.e. callbacks) evoked as a side-effect of a transition.

### Creating a State
Each state contains the following optional elements:
> **entry** A list of callback functions that will be invoked each time the state is entered.
> **exit** A list of callback functions that will be invoked each time the state is exited.
> **tran** A list of transitions which will be followed when conditions are met.
> **sub_state** States which operate only within the scope of the current state.
