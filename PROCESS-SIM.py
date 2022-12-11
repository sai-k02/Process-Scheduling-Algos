import re
from typing import List
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
        self.leftOverProcessingTime = 0
        self.activities = activities

        # statistics #
        self.arriveTime = arrive
        self.serviceTime = 0

        ##
        self.startTime = 0
        self.touchedCPU = False

        self.finishTime = 0
        self.normTurnTime = 0

        self.respTimeList = []
        self.lastTimeInReady = 0

        # DEFINE PRIORITY (FOR ALGORIMS THAT REQUIRE PRIORITY)
        self.priority = 0

    def getAvgRespTime(self):

        return sum(self.respTimeList) / len(self.respTimeList)

    def getNormTurnTime(self):
        return self.getTurnTime() / self.serviceTime

    def getTurnTime(self):
        return self.finishTime - self.arriveTime

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
            'FEEDBACK': ['quantum', 'num_priorities']
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

        if option == "num_priorities":
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

    def __getProcesses(self, procFile) -> List[Process]:
        procs = []
        with open(procFile) as f:
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

    def printStatistics(self):
        # DEFINE INIT VARIABLES FOR STATS
        turnAroundTimeSum = 0
        normalizedTurnTimeSum = 0
        meanAverageRespTimeSum = 0
        numProcesses = len(self.processes)

        # PRINT STATISTICS
        print()
        print("Statistics: ")
        for process in self.processes:
            print("Process %d:" % process.pid)
            print("\tArrival Time: %d" % process.arriveTime)
            print("\tService Time: %d" % process.serviceTime)
            print("\tStart Time: %d" % process.startTime)
            print("\tFinish Time: %s" % process.finishTime)
            print("\tTurnaround Time: %s" % process.getTurnTime())
            print("\tNormalized Turnaround Time: %s" %
                  process.getNormTurnTime())
            print("\tAverage Response Time: %s" % process.getAvgRespTime())

            turnAroundTimeSum += process.getTurnTime()
            normalizedTurnTimeSum += process.getNormTurnTime()
            meanAverageRespTimeSum += process.getAvgRespTime()

        print()

        meanTurnAroundTime = turnAroundTimeSum / numProcesses
        meanNormalizedTurnTime = normalizedTurnTimeSum / numProcesses
        meanAverageRespTime = meanAverageRespTimeSum / numProcesses

        print("System Wide Statistics: ")
        print("Mean Turnaround Time: %f" %
              meanTurnAroundTime)
        print("Mean Normalized Turnaround Time: %f" %
              meanNormalizedTurnTime)
        print("Mean Average Response Time: %f" %
              meanAverageRespTime)

    def FCFS(self):
        # SET UP THE SIMULATION RUN
        clock = 0

        # SET UP QUEUES
        ready = []
        blocked = []
        running = []

        # DEFINE A VARIABLE FOR KEEPING TRACK OF PREV DISPATCH TIME
        prevDispatchTime = 0

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

                        # CHECK IF FIRST TIME RUNNING THE PROCESS
                        if (currProcess.touchedCPU == False):
                            currProcess.touchedCPU = True
                            currProcess.startTime = clock

                        # UPDATE PREV DISPATCH TIME
                        prevDispatchTime = clock

                        # UPDATE RESPONSE TIME
                        currProcess.respTimeList.append(
                            clock - currProcess.lastTimeInReady)

                        # ADD TO RUNNING
                        running.append(currProcess.pid)

                        # CREATE NEW EVENT BY FINDING NEXT ACTIVITY TIME
                        nextActivityTime = currProcess.activities[0]
                        currProcess.activities.pop(0)
                        self.eventQueue.push(
                            Event("BLOCK", currProcess, nextActivityTime + clock))

                    else:
                        ready.append(currProcess.pid)

                        # SET LAST IN READY
                        currProcess.lastTimeInReady = clock

                if event.type == "BLOCK":
                    # MOVE THE PROCESS FROM RUNNING TO BLOCKED
                    running.remove(currProcess.pid)

                    # ADD TO BLOCKED
                    blocked.append(currProcess.pid)

                    # UPDATE SERVICE TIME
                    currProcess.serviceTime += clock-prevDispatchTime
                    prevDispatchTime = 0

                    # CREATE NEW EVENT FOR UNBLOCK
                    nextActivityTime = currProcess.activities[0]
                    currProcess.activities.pop(0)
                    self.eventQueue.push(
                        Event("UNBLOCK", currProcess, nextActivityTime + clock))
                if event.type == "UNBLOCK":
                    # MOVE TO READY
                    ready.append(currProcess.pid)

                    # SET LAST IN READY
                    currProcess.lastTimeInReady = clock

                    # REMOVE FROM BLOCKED
                    blocked.remove(currProcess.pid)

                if event.type == "EXIT":
                    # REMOVE FROM THE RUNNING QUEUE
                    running.remove(currProcess.pid)

                    # UPDATE SERVICE TIME
                    currProcess.serviceTime += clock-prevDispatchTime
                    prevDispatchTime = 0

                    # UPDATE FINISH TIME
                    currProcess.finishTime = clock

                # CHECK TO SEE IF SOMETHING IS RUNNING IF NOT RUN SOMETHING
                if (len(running) == 0) and len(ready) > 0:
                    toRun = ready.pop(0)
                    print("Dispatch", toRun)

                    prevDispatchTime = clock
                    running.append(toRun)

                    # GO THROUGH THE PROCESSES AND CREATE A NEW EVENT FOR THAT ONE
                    for process in self.processes:
                        if (process.pid == toRun):
                            nextActivityTime = process.activities[0]
                            process.activities.pop(0)

                            # CHECK TO SEE IF WE NEED UPDATE THE START TIME
                            if (process.touchedCPU == False):
                                process.touchedCPU = True
                                process.startTime = clock

                            # UPDATE RESPONSE TIME
                            process.respTimeList.append(
                                clock - process.lastTimeInReady)

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

                # UPDATE STATS FOR PROCESS

                # INCREASE TIME
                clock += 1

    def VRR(self):
        print("==================================")

        # SET UP THE SIMULATION RUN
        clock = 0

        # DEFINE THE QUANTUM
        quantum = int(self.scheduler.options["quantum"])

        # SET UP QUEUES
        auxilary = []
        ready = []
        blocked = []
        running = []

        # DEFINE A VARIABLE FOR KEEPING TRACK OF PREV DISPATCH TIME
        prevDispatchTime = 0

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

                        # CHECK IF FIRST TIME RUNNING THE PROCESS
                        if (currProcess.touchedCPU == False):
                            currProcess.touchedCPU = True
                            currProcess.startTime = clock

                        # UPDATE PREV DISPATCH TIME
                        prevDispatchTime = clock

                        # UPDATE RESPONSE TIME
                        currProcess.respTimeList.append(
                            clock - currProcess.lastTimeInReady)

                        # ADD TO RUNNING
                        running.append(currProcess.pid)

                        ''' CREATE A NEW EVENT (HANDLE THE THREE CASES FOR VIRTUAL ROUND ROBIN)'''
                        # DEFINE THE TIME FOR THAT NEW EVENT
                        nextActivityTime = currProcess.activities[0]

                        # BLOCK -> AUXILARY
                        # MUST HAVE A LOCATION FOR leftOverProcessingTime
                        if (nextActivityTime < quantum):
                            # MAKE SURE DURING OUR BLOCK EVENT HANDLING WE
                            currProcess.leftOverProcessingTime = quantum - nextActivityTime
                            currProcess.activities.pop(0)
                            self.eventQueue.push(
                                Event("BLOCK", currProcess, nextActivityTime + clock))

                        # BLOCK
                        if (nextActivityTime == quantum):
                            currProcess.leftOverProcessingTime = 0
                            currProcess.activities.pop(0)
                            self.eventQueue.push(
                                Event("BLOCK", currProcess, nextActivityTime + clock))

                        # TIMEOUT -> READY
                        if (nextActivityTime > quantum):
                            # TIMEOUT
                            currProcess.leftOverProcessingTime = 0
                            currProcess.activities[0] = nextActivityTime - quantum
                            self.eventQueue.push(
                                Event("TIMEOUT", currProcess, quantum + clock))

                    else:
                        ready.append(currProcess.pid)

                        # SET LAST IN READY
                        currProcess.lastTimeInReady = clock

                if event.type == "TIMEOUT":
                    running.remove(currProcess.pid)
                    ready.append(currProcess.pid)

                    # UPDATE SERVICE TIME
                    currProcess.serviceTime += clock-prevDispatchTime

                    # SET LAST IN READY
                    currProcess.lastTimeInReady = clock

                if event.type == "BLOCK":
                    # MOVE THE PROCESS FROM RUNNING TO BLOCKED
                    running.remove(currProcess.pid)

                    # ADD TO BLOCKED
                    blocked.append(currProcess.pid)

                    # UPDATE SERVICE TIME
                    currProcess.serviceTime += clock-prevDispatchTime
                    prevDispatchTime = 0

                    '''CREATE NEW EVENT FOR UNBLOCK'''
                    nextActivityTime = currProcess.activities[0]
                    currProcess.activities.pop(0)
                    self.eventQueue.push(
                        Event("UNBLOCK", currProcess, nextActivityTime + clock))
                if event.type == "UNBLOCK":
                    # HIGHLIGHT: WE MOVE TO AUXILARY ONCE WE HAVE LEFT OVER TIME
                    if (currProcess.leftOverProcessingTime != 0):
                        auxilary.append(currProcess.pid)
                    else:
                        # MOVE TO READY
                        ready.append(currProcess.pid)

                    # SET LAST IN READY
                    currProcess.lastTimeInReady = clock

                    # REMOVE FROM BLOCKED
                    blocked.remove(currProcess.pid)

                if event.type == "EXIT":
                    # REMOVE FROM THE RUNNING QUEUE
                    running.remove(currProcess.pid)

                    # UPDATE SERVICE TIME
                    currProcess.serviceTime += clock-prevDispatchTime
                    prevDispatchTime = 0

                    # UPDATE FINISH TIME
                    currProcess.finishTime = clock

                if (len(running) == 0) and (len(ready) > 0 or len(auxilary) > 0):
                    # GET FROM AUXILARY OR READY
                    if (len(auxilary) == 0):
                        toRun = ready.pop(0)
                    elif (len(auxilary) > 0):
                        toRun = auxilary.pop(0)

                    print("Dispatch", toRun)

                    # SET THE PREVIOUS TIME WE DISPATCH A PROCESS
                    prevDispatchTime = clock

                    # UPDATE RESPONSE TIME

                    # ADD TO RUNNING QUEUE
                    running.append(toRun)

                    # GO THROUGH PROCESSES AND CREATE A NEW EVENT FOR CORRECT ONE
                    for process in self.processes:
                        if (process.pid == toRun):
                            # ADD TO RESPONSE TIME
                            process.respTimeList.append(
                                clock - process.lastTimeInReady)

                            # DEFINE THE NEXT ACTIVITY
                            nextActivityTime = process.activities[0]

                            # CHECK TO SEE IF WE NEED UPDATE THE START TIME
                            # (THE FIRST TIME THE PROCESS HAS TOUCHED THE CPU)
                            if (process.touchedCPU == False):
                                process.touchedCPU = True
                                process.startTime = clock

                            # IF LEFT OVER PROCESSING TIME IS GREATER THAN ZERO, WE KNOW THAT WE ARE COMING FROM AUXILARY
                            if (process.leftOverProcessingTime > 0):
                                ''' THREE CASES FOR WHEN WE HAVE LEFTOVERPROCESSINGTIME'''
                                if (process.leftOverProcessingTime < nextActivityTime):

                                    # SET THE NEW ACTIVITY TIME
                                    process.activities[0] = nextActivityTime - \
                                        process.leftOverProcessingTime

                                    # CREATE NEW EVENT TIMEOUT
                                    self.eventQueue.push(
                                        Event("TIMEOUT", process, process.leftOverProcessingTime + clock))

                                    # RESET LEFT OVER PROCESSING TIME
                                    process.leftOverProcessingTime = 0

                                if (process.leftOverProcessingTime >= nextActivityTime):
                                    process.leftOverProcessingTime = process.leftOverProcessingTime - nextActivityTime

                                    # BLOCK OR EXIT
                                    process.activities.pop(0)

                                    if (len(process.activities) == 0):
                                        self.eventQueue.push(
                                            Event("EXIT", process, nextActivityTime + clock))
                                    else:
                                        self.eventQueue.push(
                                            Event("BLOCK", process, nextActivityTime + clock))

                            elif process.leftOverProcessingTime == 0:
                                # TIMEOUT -> READY
                                if (nextActivityTime > quantum):
                                    process.activities[0] = nextActivityTime - quantum
                                    self.eventQueue.push(
                                        Event("TIMEOUT", process, quantum + clock))

                                # IF NEXT ACTIVITY TIME IS
                                # CHECK IF WE NEED TO EXIT OR BLOCK AGAIN
                                if (nextActivityTime <= quantum):
                                    process.leftOverProcessingTime = quantum - nextActivityTime

                                    # REMOVE THE ACTIVITY
                                    process.activities.pop(0)

                                    if (len(process.activities) == 0):
                                        self.eventQueue.push(
                                            Event("EXIT", process, nextActivityTime + clock))
                                    else:
                                        self.eventQueue.push(
                                            Event("BLOCK", process, nextActivityTime + clock))

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

                # UPDATE STATS FOR PROCESS

                # INCREASE TIME
                clock += 1

    def FEEDBACK(self):

        def populateReadyQueues(num_priorities):
            '''CREATE AN OBJECT OF LISTS'''
            ready = {}

            for i in range(0, num_priorities):
                ready[i] = []

            return ready

        # SET UP THE SIMULATION RUN
        clock = 0

        # DEFINE THE QUANTUM
        quantum = int(self.scheduler.options["quantum"])
        num_priorities = int(self.scheduler.options["num_priorities"])

        # SET UP QUEUES
        ready = populateReadyQueues(num_priorities)
        blocked = []
        running = []

        # DEFINE A VARIABLE FOR KEEPING TRACK OF PREV DISPATCH TIME
        prevDispatchTime = 0

        # WHILE THERE ARE NO MORE TO PROCESS
        while not self.eventQueue.empty():
            print("==================================")

            # PEEK AT THE NEXT EVENT
            event: Event = self.eventQueue.peek()

            # SET CLOCK TO THE NEXT EVENT
            clock = event.time

            # WHILE THE NEXT HAS A "TIME STAMP EQUAL TO THE CLOCK"
            while event.time == clock:
                # print("==================================")
                print(event)

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

                        # CHECK IF FIRST TIME RUNNING THE PROCESS
                        if (currProcess.touchedCPU == False):
                            currProcess.touchedCPU = True
                            currProcess.startTime = clock

                        # UPDATE PREV DISPATCH TIME
                        prevDispatchTime = clock

                        # UPDATE RESPONSE TIME
                        currProcess.respTimeList.append(
                            clock - currProcess.lastTimeInReady)

                        # ADD TO RUNNING
                        running.append(currProcess.pid)

                        ''' CREATE A NEW EVENT (HANDLE THE THREE CASES FOR VIRTUAL ROUND ROBIN)'''
                        # DEFINE THE TIME FOR THAT NEW EVENT
                        nextActivityTime = currProcess.activities[0]

                        # BLOCK -> AUXILARY
                        # MUST HAVE A LOCATION FOR leftOverProcessingTime
                        if (nextActivityTime < quantum):
                            # MAKE SURE DURING OUR BLOCK EVENT HANDLING WE
                            currProcess.activities.pop(0)
                            self.eventQueue.push(
                                Event("BLOCK", currProcess, nextActivityTime + clock))

                        # BLOCK
                        if (nextActivityTime == quantum):
                            # SET PRIORITY BACK TO ZERO
                            currProcess.activities.pop(0)
                            self.eventQueue.push(
                                Event("BLOCK", currProcess, nextActivityTime + clock))

                        # TIMEOUT -> READY
                        if (nextActivityTime > quantum):
                            currProcess.activities[0] = nextActivityTime - quantum
                            self.eventQueue.push(
                                Event("TIMEOUT", currProcess, quantum + clock))

                    else:
                        ready[0].append(currProcess.pid)

                        # SET LAST IN READY
                        currProcess.lastTimeInReady = clock

                if event.type == "TIMEOUT":
                    running.remove(currProcess.pid)

                    # FEEDBACK DECREASE PRIORITY
                    if ((currProcess.priority+1) != num_priorities):
                        currProcess.priority += 1

                    ready[currProcess.priority].append(currProcess.pid)

                    # UPDATE SERVICE TIME
                    currProcess.serviceTime += clock-prevDispatchTime

                    # SET LAST IN READY
                    currProcess.lastTimeInReady = clock

                if event.type == "BLOCK":
                    # MOVE THE PROCESS FROM RUNNING TO BLOCKED
                    running.remove(currProcess.pid)

                    # RESET PRIORITY
                    currProcess.priority = 0

                    # ADD TO BLOCKED
                    blocked.append(currProcess.pid)

                    # UPDATE SERVICE TIME
                    currProcess.serviceTime += clock-prevDispatchTime
                    prevDispatchTime = 0

                    '''CREATE NEW EVENT FOR UNBLOCK'''
                    nextActivityTime = currProcess.activities[0]
                    currProcess.activities.pop(0)
                    self.eventQueue.push(
                        Event("UNBLOCK", currProcess, nextActivityTime + clock))
                if event.type == "UNBLOCK":

                    # REGARDLESS OF LEFTOVER TIME APPEND TO READY
                    currProcess.priority = 0
                    ready[0].append(currProcess.pid)

                    # SET LAST IN READY
                    currProcess.lastTimeInReady = clock

                    # REMOVE FROM BLOCKED
                    blocked.remove(currProcess.pid)

                if event.type == "EXIT":
                    # REMOVE FROM THE RUNNING QUEUE
                    running.remove(currProcess.pid)

                    # UPDATE SERVICE TIME
                    currProcess.serviceTime += clock-prevDispatchTime
                    prevDispatchTime = 0

                    # UPDATE FINISH TIME
                    currProcess.finishTime = clock

                # FIND A PROCESS IN READY QUEUES TO RUN
                readyToRun = False
                for index in range(0, num_priorities):
                    if (len(ready[index]) > 0) and readyToRun == False:
                        readyToRun = True
                        break

                # DISPATCHER
                if (len(running) == 0) and (readyToRun == True):

                    # GET THE NEXT PROCESS TO RUN
                    for index in range(0, num_priorities):
                        if (len(ready[index]) > 0):
                            toRun = (ready[index]).pop(0)
                            break

                    print("Dispatch", toRun)

                    # SET THE PREVIOUS TIME WE DISPATCH A PROCESS
                    prevDispatchTime = clock

                    # ADD TO RUNNING QUEUE
                    running.append(toRun)

                    # GO THROUGH PROCESSES AND CREATE A NEW EVENT FOR CORRECT ONE
                    for process in self.processes:
                        if (process.pid == toRun):
                            # ADD TO RESPONSE TIME
                            process.respTimeList.append(
                                clock - process.lastTimeInReady)

                            # DEFINE THE NEXT ACTIVITY
                            nextActivityTime = process.activities[0]

                            # CHECK TO SEE IF WE NEED UPDATE THE START TIME
                            # (THE FIRST TIME THE PROCESS HAS TOUCHED THE CPU)
                            if (process.touchedCPU == False):
                                process.touchedCPU = True
                                process.startTime = clock

                            # TIMEOUT -> READY
                            if (nextActivityTime > quantum):
                                process.activities[0] = nextActivityTime - quantum

                                self.eventQueue.push(
                                    Event("TIMEOUT", process, quantum + clock))

                            # IF NEXT ACTIVITY TIME IS
                            # CHECK IF WE NEED TO EXIT OR BLOCK AGAIN
                            if (nextActivityTime <= quantum):
                                # REMOVE THE ACTIVITY
                                process.activities.pop(0)

                                if (len(process.activities) == 0):
                                    self.eventQueue.push(
                                        Event("EXIT", process, nextActivityTime + clock))
                                else:
                                    self.eventQueue.push(
                                        Event("BLOCK", process, nextActivityTime + clock))

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
                print("EVENT QUEUE: ")
                for element in self.eventQueue.queue:
                    print(element)
                print(ready)
                # print("\n\n")

                print("==================================")

                # UPDATE STATS FOR PROCESS

                # INCREASE TIME
                clock += 1

    def run(self):
        """
        MAIN DRIVER OF THE PROCESS SIMULATION
        """
        if self.scheduler.algorithm == "FCFS":
            self.FCFS()
        if self.scheduler.algorithm == "VRR":
            self.VRR()
        if self.scheduler.algorithm == "FEEDBACK":
            self.FEEDBACK()
        self.printStatistics()


EVENT_TYPE_PRIORITY = {
    "ARRIVE": 0,
    "UNBLOCK": 1,
    "TIMEOUT": 2,
    "BLOCK": 3,
    "EXIT": 4
}

# sim = Simulation(sys.argv[1], sys.argv[2])
sim = Simulation("sample-runs/feedback.sf", "sample-runs/example.pf")
sim.run()
