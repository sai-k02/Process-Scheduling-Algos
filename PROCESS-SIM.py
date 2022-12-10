import re
import sys
import queue
import math


class Process:
    """
    A process is composed of an Identifier, Arrival time,
    and a list of activites, represented by a duration
    """

    def __init__(self, pid, arrive, activities):
        self.pid = pid
        self.arriveTime = arrive
        self.activities = activities

    def __str__(self):
        return "Process " + str(self.pid) + ", Arrive " + str(self.arriveTime) + ": " + str(self.activities)


class Event:
    """
    An event has a type, associated process, and the time it happens
    Here I will pass a reference to an object of type Process,
    But you could use Process ID instead if that is simpler for you.
    """

    def __init__(self, etype, process, time):
        self.type = etype
        self.process = process
        self.time = time

    def __lt__(self, other):
        if self.time == other.time:
            # Break Tie with event type
            if self.type == other.type:
                # Break type tie by pid
                return self.process.pid < other.process.pid
            else:
                return EVENT_TYPE_PRIORITY[self.type] < EVENT_TYPE_PRIORITY[other.type]
        else:
            return self.time < other.time

    def __str__(self):
        return "At time " + str(self.time) + ", " + self.type + " Event for Process " + str(self.process.pid)


class EventQueue:
    """
    A Priority Queue that sorts Events by '<'
    """

    def __init__(self):
        self.queue = []
        self.dirty = False

    def push(self, item):
        if type(item) is Event:
            self.queue.append(item)
            self.dirty = True
        else:
            raise TypeError("Only Events allowed in EventQueue")

    def __prepareLookup(self, operation):
        if self.queue == []:
            raise LookupError(operation + " on empty EventQueue")
        if self.dirty:
            self.queue.sort(reverse=True)
            self.dirty = False

    def pop(self):
        self.__prepareLookup("Pop")
        return self.queue.pop()

    def peek(self):
        self.__prepareLookup("Peek")
        return self.queue[-1]

    def empty(self):
        if (len(self.queue) == 0):
            return True
        return False

    def __str__(self):
        return "EventQueue(" + str(self.queue) + ")"


class Scheduler:
    """
    SCHEDULER CLASS WILL SETUP THE SIMULATION
    """

    def __init__(self, file: str):
        with open(file) as f:
            lines = [line.rstrip() for line in f]  # Read lines of the file
            self.algorithm = lines[0]
            self.options = {}
            lineNumber = 1

            for line in lines[1:]:
                split = re.split('\s*=\s*', line)
                if len(split) != 2:
                    raise ValueError(
                        "Invalid Scheduler option at line " + str(lineNumber))
                value = self.__checkAlgorithmOptions(split[0], split[1])
                if value == None:
                    raise ValueError(
                        "Invalid Scheduler option at line " + str(lineNumber))

                self.options[split[0]] = split[1]
                lineNumber = lineNumber + 1

        self.__confirmAlgorithm()

    def __checkAlgorithmOptions(self, option, value):
        """WILL CHECK FOR THE ACCORDING OPTIONS"""

        algorithmValues = {
            'VRR': ['quantum'],
            'SRT': ['service_given', 'alpha'],
            'HRRN': ['service_given', 'alpha'],
            'FEEDBACK': ['quantum', 'num_priories']
        }

        if (self.algorithm == 'FCFS') and (option in algorithmValues[self.algorithm]):
            return self.__checkOption(option, value)
        if self.algorithm == 'VRR' and (option in algorithmValues[self.algorithm]):
            return self.__checkOption(option, value)
        if self.algorithm == 'SRT' and (option in algorithmValues[self.algorithm]):
            return self.__checkOption(option, value)
        if self.algorithm == 'HRRN' and (option in algorithmValues[self.algorithm]):
            return self.__checkOption(option, value)
        if self.algorithm == 'FEEDBACK' and (option in algorithmValues[self.algorithm]):
            return self.__checkOption(option, value)

        return None

    def __checkOption(self, option, value):
        """ 
        FUNCTION WILL RETURN THE CORRECT CONVERTED VALUE OR NONE
        """

        if option == "quantum":
            try:
                return int(value)
            except:
                return None

        if option == "service_given":
            try:
                return bool(value)
            except:
                return None

        if option == "alpha":
            try:
                if not (0.0 <= float(value) <= 1.0):
                    raise Exception("Alpha Option must be between 0 and 1")
                return float(value)
            except:
                return None

        if option == "num_properties":
            try:
                return int(value)
            except:
                return None

        return None

    def __confirmAlgorithm(self):
        """ 
        CHECK FOR CORRECT ARGUMENTS FOR EACH SPECIFIC ALGORITHM
        """

        algorithmValues = {
            'FCSC': [],
            'VRR': ['quantum'],
            'SRT': ['service_given', 'alpha'],
            'HRRN': ['service_given', 'alpha'],
            'FEEDBACK': ['quantum', 'num_priorities']
        }

        if (self.algorithm == 'FCFS') and len(self.options) == 0:
            return
        if self.algorithm == 'VRR' and len(self.options) == 1 and "quantum" in self.options:
            return
        if self.algorithm == 'SRT' and len(self.options) == 2 and "service_given" in self.options and "alpha" in self.options:
            return
        if self.algorithm == 'HRRN' and len(self.options) == 2 and "service_given" in self.options and "alpha" in self.options:
            return
        if self.algorithm == 'FEEDBACK' and len(self.options) == 2 and "quantum" in self.options and "num_priorities" in self.options:
            return

        raise ValueError("Inappropriate algorithm \n",
                         self.algorithm, "\n", self.options)

    def __str__(self):
        return "Scheduler(" + self.algorithm + ", " + str(self.options) + ")"


class Simulation:
    """ 
    INITIALIZE THE SIMULATION WITH THE SCHEDULER FILE AND THE PROCESS FILE 
    """

    def __init__(self, schedFile, procFile):
        self.eventQueue = EventQueue()
        self.scheduler = Scheduler(schedFile)
        self.processes = self.__getProcesses(procFile)

        # POPULATE WITH INITIAL EVENTS
        for p in self.processes:
            self.eventQueue.push(Event("ARRIVE", p, p.arriveTime))

    def __getProcesses(self, procFile):
        procs = []
        print("Opening", procFile)
        with open(procFile) as f:
            print("Opened", procFile)
            lines = [line.rstrip() for line in f]  # Read lines of the file
            lineNumber = 1
            for p in lines:
                tmp = re.split('\s+', p)
                # Make sure there enough values on the line
                if len(tmp) < 2:
                    raise ValueError(
                        "Process missing activities and possible the arrival time at line " + str(lineNumber))
                # Check to make sure there is a final CPU activity
                # We assume the first activity is CPU, and it alternates from there.
                # This means there must be an odd number of activities or an even number
                # of ints on the line (the first being arrival time)
                if len(tmp) % 2 == 1:
                    raise ValueError(
                        "Process with no final CPU activity at line " + str(lineNumber))
                # Check to make sure each activity, represented by a duration,
                # is an integer, and then convert it.
                for i in range(0, len(tmp)):
                    #
                    if re.fullmatch('\d+', tmp[i]) == None:
                        raise ValueError(
                            "Invalid process on line " + str(lineNumber))
                    else:
                        # CONVERT TO INTEGER
                        tmp[i] = int(tmp[i])
                procs.append(Process(lineNumber-1, tmp[0], tmp[1:]))
                lineNumber = lineNumber + 1
        return procs

    def __str__(self):
        return "Simulation(" + str(self.scheduler) + ", " + str(self.processes) + ") : " + str(self.eventQueue)

    def getFutureEvent(self, event: Event, clock: int, dis_hap: bool):
        """ 
        Return the future event to add to event QUEUE 
        """

        process: Process = event.process

        nextActivityTime = process.activities[0]

        process.activities.pop(0)

        if (event.type == "BLOCK"):
            # WE KNOW THAT WE NEED TO DO A FUTURE EVENT FOR UNBLOCK
            return Event("UNBLOCK", process, nextActivityTime + clock)

        if dis_hap:
            if (event.type == "ARRIVE"):
                # WE KNOW THAT WE WILL CREATE A FUTURE EVENT FOR BLOCK
                return Event("BLOCK", process, nextActivityTime + clock)
            # if (event.type == "UNBLOCK"):
            #     # WE KNOW THAT WE NEED TO DO A FUTURE EVENT FOR BLOCK
            #     return Event("BLOCK", process, nextActivityTime + clock)            # if (event.type == "UNBLOCK"):
            #     # WE KNOW THAT WE NEED TO DO A FUTURE EVENT FOR BLOCK
            #     return Event("BLOCK", process, nextActivityTime + clock)

    def run(self):
        """
        RUN WILL BE THE MAIN DRIVER OF THE PROCESS SIMULATION
        """
        # SET UP THE SIMULATION RUN
        clock = 0
        algorithm = self.scheduler.algorithm

        # SET UP QUEUES
        ready = []
        blocked = []
        running = []

        # WHILE THERE ARE NO MORE TO PROCESS
        while not self.eventQueue.empty():

            # PEEK AT THE NEXT EVENT
            event: Event = self.eventQueue.peek()

            # SET CLOCK TO THE NEXT EVENT
            clock = event.time

            # WHILE THE NEXT HAS A "TIME STAMP EQUAL TO THE CLOCK"
            while event.time == clock:
                # print("==================================")
                print(event)

                # SET BOOL OF DISPATCH TO FALSE
                dis_hap = False

                # GET THE NEXT EVENT
                event: Event = self.eventQueue.pop()

                # DEFINE THE PROCESS
                currProcess: Process = event.process

                # DETERMINE WHAT TO DO ON ARRIVE
                if event.type == "ARRIVE":
                    # CHECK TO SEE IF ANOTHER PROCESS IS CURRENTLY RUNNING
                    if (len(running) == 0):
                        # DISPATCH
                        print("Dispatch", currProcess.pid)

                        dis_hap = True

                        # ADD TO RUNNING
                        running.append(currProcess.pid)

                        # CREATE NEW EVENT BY FINDING NEXT ACTIVITY TIME
                        nextActivityTime = currProcess.activities[0]
                        currProcess.activities.pop(0)
                        self.eventQueue.push(
                            Event("BLOCK", currProcess, nextActivityTime + clock))

                    else:
                        ready.append(currProcess.pid)

                if event.type == "BLOCK":
                    # MOVE THE PROCESS FROM RUNNING TO BLOCKED
                    running.remove(currProcess.pid)

                    # ADD TO BLOCKED
                    blocked.append(currProcess.pid)

                    # CREATE NEW EVENT FOR UNBLOCK
                    nextActivityTime = currProcess.activities[0]
                    currProcess.activities.pop(0)
                    self.eventQueue.push(
                        Event("UNBLOCK", currProcess, nextActivityTime + clock))
                if event.type == "UNBLOCK":
                    # MOVE TO READY
                    ready.append(currProcess.pid)

                    # REMOVE FROM BLOCKED
                    blocked.remove(currProcess.pid)

                if event.type == "TIMEOUT":
                    pass

                if event.type == "EXIT":
                    # REMOVE FROM THE RUNNING QUEUE
                    running.remove(currProcess.pid)

                # CHECK TO SEE IF SOMETHING IS RUNNING IF NOT RUN SOMETHING
                if (len(running) == 0) and len(ready) > 0:
                    toRun = ready.pop(0)
                    print("Dispatch", toRun)
                    dis_hap = True
                    running.append(toRun)

                    # GO THROUGH THE PROCESSES AND CREATE A NEW EVENT FOR THAT ONE
                    for process in self.processes:
                        if (process.pid == toRun):
                            nextActivityTime = process.activities[0]
                            process.activities.pop(0)

                            # WHEN DISPATCHING A PROCESS
                            # CHECK IF WE NEED TO EXIT OR BLOCK AGAIN
                            if (len(process.activities) != 0):
                                self.eventQueue.push(
                                    Event("BLOCK", process, nextActivityTime + clock))
                            else:
                                self.eventQueue.push(
                                    Event("EXIT", process, nextActivityTime + clock))

                # print("TIME: ", str(clock))
                # print()
                # print("RUNNING: ")
                # for element in running:
                #     print(element)
                # print()
                # print("BLOCKED: ")
                # for element in blocked:
                #     print(element)
                # print()
                # print("READY:  ")
                # for element in ready:
                #     print(element)
                # print()
                # print("EVENT QUEUE: ")
                # for element in self.eventQueue.queue:
                #     print(element)
                # print("\n\n")

                # print("==================================")

                # INCREASE TIME
                clock += 1


EVENT_TYPE_PRIORITY = {
    "ARRIVE": 0,
    "UNBLOCK": 1,
    "TIMEOUT": 2,
    "BLOCK": 3,
    "EXIT": 4
}

# sim = Simulation(sys.argv[1], sys.argv[2])
sim = Simulation("sample-runs/fcfs.sf", "sample-runs/example.pf")
sim.run()
