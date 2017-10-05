#!/usr/bin/python
#
# We are solving the scheduling problem for compute dense kernels by focusing
# on the microarchitecture of the target processor. Even though these are OOO
# processors, we treat this underlying system as a VLIW machine and schedule
# our code accordingly.
#
# This program implements the OASIC model for scheduling VLIW programs using
# Integer Linear Programming.
#
#
# - Richard Michael Veras
#   rveras@cmu.edu

from oasic_vliw_scheduler import *

## Dummy Program to test scheduler
exprog      = ExampleProgram()
exuarch     = ExampleMicroarchitecture()
exscheduler = OasicScheduler( exprog, exuarch )
exscheduler.schedule()


## Simple block to schedule
## Modify/extend SimpleMicroarchitecture() for different archs
block = [("LD","a",()),
         ("LD","b",()),
         ("MUL","r",("a","b")),
         ("ADD", "cn", ("r", "co"))]

interval  = 5 # can make this longer if the program takes longer than 10 cycles
prog      = SimpleProgram(block,interval)
uarch     = SimpleMicroarchitecture()
scheduler = OasicScheduler( prog, uarch )

scheduler.schedule()

