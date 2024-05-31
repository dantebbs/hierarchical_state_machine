"""
Copyright (c) 2023 by Crystal Clear Design

This intellectual property is shared to the public domain under the MIT License.
Crystal Clear Design offers no warranty and accepts no liability.
The only requirement for use is that this copyright notice remains intact.

This file is an example to help illustrate the use of the state_machine.py
library module. It simulates the common crosswalk signaling system used to
help pedestrians cross a busy street by stopping the vehicle traffic.

DISCLAIMER: This example must not be used for an actual, safety-critical
implementation of a crosswalk! It was selected for its familiarity to anyone
learning about the library, and is only to be used for demonstrating the various
features of the state_machine library module, and its use. This example does not
meet necessary safety requirements such as handling power outages, burned out
lights, emergency vehicle approaches, additional sensors, audio indicators,
nor other possible events and usages.
"""

pedestrian_crosswalk_signals = """
{
  "events": [
    "button_push",
    "countdown_complete",
    "flash_complete",
    "one_second"
  ],
  "states": {
    "start": {
      "tran": {
        "auto": {
          "dest": "Traffic Flowing"
        }
      }
    },
    "Traffic Flowing": {
      "entry": [
        "set_ped_light(red)"
      ],
      "exit": [
        "cancel_flash()"
      ],
      "tran": {
        "button_push": {
          "dest": "Traffic Stopping"
        }
      },
      "states": {
        "start": {
          "tran": {
            "auto": {
              "dest": "Yel Lght On"
            }
          }
        },
        "Yel Lght On": {
          "entry": [
            "set_traf_light(yel)",
            "start_flash(800)"
          ],
          "tran": {
            "flash_complete": {
              "dest": "Yel Lght Off"
            }
          }
        },
        "Yel Lght Off": {
          "entry": [
            "set_traf_light(blk)",
            "start_flash(800)"
          ],
          "tran": {
            "flash_complete": {
              "dest": "Yel Lght On"
            }
          }
        }
      }
    },
    "Traffic Stopping": {
      "entry": [
        "set_traf_light(yel)",
        "start_countdown(5000)"
      ],
      "tran": {
        "countdown_complete": {
          "dest": "Pedestrian Crossing"
        }
      }
    },
    "Pedestrian Crossing": {
      "entry": [
        "set_traf_light(red)",
        "set_ped_light(grn)",
        "start_countdown(5000)"
      ],
      "tran": {
        "countdown_complete": {
          "acts": [
            "set_ped_light(yel)",
            "start_countdown(10000)",
            "start_ped_time(10)"
          ],
          "dest": "Crossing Countdown"
        }
      }
    },
    "Crossing Countdown": {
      "exit": [
        "cancel_flash()"
      ],
      "tran": {
        "countdown_complete": {
          "acts": [
            "update_ped_time()"
          ],
          "dest": "Traffic Flowing"
        }
      },
      "states": {
        "start": {
          "tran": {
            "auto": {
              "dest": "Yel Hand On"
            }
          }
        },
        "Yel Hand On": {
          "entry": [
            "set_ped_light(yel)",
            "start_flash(400)"
          ],
          "tran": {
            "flash_complete": {
              "dest": "Yel Hand Off"
            }
          }
        },
        "Yel Hand Off": {
          "entry": [
            "set_ped_light(blk)",
            "start_flash(600)"
          ],
          "exit": [
            "update_ped_time()"
          ],
          "tran": {
            "flash_complete": {
              "dest": "Yel Hand On"
            }
          }
        }
      }
    }
  }
}
"""

import sys

try:
    import curses
except ImportError:
    print( "This example script requires the 'curses' module. Before trying again, run: python -m pip install windows-curses" )
    exit( 1 )

try:
    import hierarchical_state_machine as hsm
except ImportError:
    print("This example script requires the 'hierarchical_state_machine' module. Before trying again, run: python -m pip install hierarchical_state_machine")
    exit(1)

import ascii_crosswalk


callbacks_module = sys.modules[__name__]

proc_period_ms = 50
crosswalk = None
ascii = None
quit = False

def set_traf_light(color: str) -> bool:
    global ascii
    ascii.print_status(f"Setting traffic light to {color}.")
    ascii.set_traf_light(color)
    ascii.print_display()
    return True

def set_ped_light(color: str) -> bool:
    global ascii
    ascii.print_status(f"Setting pedestrian light to {color}.")
    ascii.set_ped_light(color)
    ascii.print_display()
    return True

def start_countdown(time_s: str) -> bool:
    time_s_int = int(time_s, 10)
    #global ascii
    #ascii.print_status(f"Starting countdown of {time_s_int} milliseconds.")
    crosswalk.add_timer("countdown_complete", time_s_int)
    return True

def start_flash(time_s: str) -> bool:
    time_s_int = int(time_s, 10)
    crosswalk.add_timer("flash_complete", time_s_int)
    return True

def cancel_flash(unused: str) -> bool:
    crosswalk.rem_timer_by_evt("flash_complete")
    return True

ped_count_down_s = 0
def start_ped_time(time_s: str) -> bool:
    time_s_int = int(time_s, 10)
    global ped_count_down_s
    ped_count_down_s = time_s_int
    update_ped_time()
    return True

def update_ped_time(unused = "") -> bool:
    global ped_count_down_s
    ped_count_down_s -= 1
    global ascii
    ascii.print_status(f"Showing pedestrian countdown of {ped_count_down_s} seconds.")
    print(f"Showing pedestrian countdown of {ped_count_down_s} seconds.")
    ascii.set_ped_time(ped_count_down_s)
    ascii.draw_ped_sig()
    return True

def main(stdscr):
    # Allow for fancy display.
    global ascii
    ascii = ascii_crosswalk.ascii_crosswalk(stdscr)

    # Set desired flags before instantiation.
    #hsm.debug_flags.set("machine_parse")
    #hsm.debug_flags.set("execution_details")
    hsm.debug_flags.set("enter_exit")
    hsm.debug_flags.set("transitions")

    # Now that all the call-back functions are defined, create the machine.
    global crosswalk
    crosswalk = hsm.state_machine( pedestrian_crosswalk_signals, callbacks_module, proc_period_ms )

    global quit
    while (not quit):
        crosswalk.process_events_rate_limited()
        c = stdscr.getch()
        if c == ord('b'):
            crosswalk.enqueue_event("button_push")
            ascii.print_status("You pressed the crossing request button.")
        #elif c == curses.ascii.ESC or c == ord('q'):
        elif c == 27 or c == ord('q'):
            quit = True

    ascii.print_status("Exiting simulation.")
    crosswalk.cleanup()

# Execute with proper curses lib set-up and clean-up.
curses.wrapper(main)
