import time
from pymata4 import pymata4

board = pymata4.Pymata4()

serPin = 2
rclkPin = 3
srclkPin = 4
buzzerPin = 5

for pin in [serPin,rclkPin,srclkPin]:
    board.set_pin_mode_digital_output(pin)

inputPins = [('pb1Button', 6)]

state = {
    'sub1': [False, 0],
    'sub1PA1Stage': [0, 0],
    'sub1Stage': [0, 0],
    'sub2': [False, 0],
    'sub2Stage': [0, 0],
    'sub3': [False, 0],
    'sub3PB1Stage': [0,0],
    'sub3Stage': [0, 0],
    'sub4': [False, 0],
    'sub4WL1': [0,0],
    'sub4Stage': [0, 0],
}

"""
sub3: 'fl1Fl2', 'tl5GreenBlink', 'tl5Green', 'tl5Yellow', 'tl5Red'
    
sub1: 'tl2Green', 'tl2Yellow', 'tl2Red','tl1Green', 'tl1Yellow', 'tl1Red', 'wlAstable'

sub2: 'pl1RedBlink', 'pl1RedGreen', 'tl4GreenYellow', 'tl4YellowRed'

sub4: 'tl3Red', 'tl3Green','wl2Red'

"""

componentStatusDictionary = {'fl1Fl2':0, 
                'tl5GreenBlink':0, 
                'tl5Green':0, 
                'tl5Yellow':0, 
                'tl5Red':0, 
                'tl2Green':0,
                'tl2Yellow':0,
                'tl2Red':0,

                'wl1Astable':0,
                'tl1Green':0,
                'tl1Yellow':0,
                'tl1Red':0,
                'pl1RedGreen':1,
                'pl1RedBlink':1,
                'tl4GreenYellow':0,
                'tl4YellowRed':0,
                
                'tl3Red':0,
                'tl3Green':0,
                'wl2Red':0}

def stopwatch(last_time: float) -> float:
    return time.time() - last_time

def timer(last_time: float, duration: int) -> bool:
    return stopwatch(last_time) >= duration

def activate_subsystem(name) -> None:
    state[name] = [True, time.time()]

def deactivate_subsystem(name) -> None:
    state[name] = [False, state[name][1]]

def get_state(name) -> bool | int:
    return state[name][0]

def update_stage(name, stage) -> None:
    state[name] = [stage, time.time()]

def get_timestamp(name) -> float:
    return state[name][1]

def pin_reader(pin: int):
    board.set_pin_mode_digital_input(pin)
    def read_pin() -> int:
        return board.digital_read(pin)[0]

    return read_pin 

def sonar_reader(triggerPin: int, echoPin: int):
    board.set_pin_mode_sonar(triggerPin, echoPin, timeout=50000)

    def update_distance() -> int | None:
        """
        Retrieves the distance detected by the sonar.
            Parameters:
                functions has no input
            Returns:
                dis[0] (int| None): The distance detected by the sonar. If there is an error, it will return None.
        """
        try:
            dist = board.sonar_read(triggerPin) # Gets data from the sonar
            if dist: # Check whether the list is not empty of not None
                return dist[0] # Returns the last value that the sonar has detected
            return update_distance()
        # As a safety measure to catch unwanted errors, and set variable e as Exception (any non-exit exceptions)
        # Unwanted errors may be due to connection issues
        except Exception as e:
            print(f"Error: {e}") # Print out the error
            return update_distance()
        
    avgArray = [update_distance() for _ in range(10)]

    def avg_updater() -> None:
        avgArray.pop(0)
        avgArray.append(update_distance())
    
    def get_distance() -> int:
        return round(sum(avgArray)/len(avgArray))
    
    return avg_updater, get_distance

def buzzer(buzzerPin: int):
    board.set_pin_mode_tone(buzzerPin)
    def play_unique_tone(long_warning: int):
        if long_warning == 1:
            board.play_tone_continuously(buzzerPin, 500)
        elif long_warning == 2:
            board.play_tone_continuously(buzzerPin, 2100)
        elif long_warning == 0:
            board.play_tone_off(buzzerPin)

    return play_unique_tone

def signal(componentUpdateDictionary) -> None:
    """
    This function updates the componentStatusDictionary, converts the dictionary into a list of "0" and "1", shifts out the bits to shift register, and triggers the shift register to store the values (update its output).
        Parameter:
            componentUpdateDictionary (dictionary): A dictionary that assigns new integer value (1 or 0) to an existing key in componentStatusDictionary
        
        Returns:
            None
    """

    # A - update the key in componentStatusDictionary using componentUpdateDictionary
    for component in componentUpdateDictionary:
        if component in componentStatusDictionary:
            componentStatusDictionary[component]=componentUpdateDictionary[component]
    
    signalList = [componentStatusDictionary[status] for status in componentStatusDictionary]
    """print(signalList)
    print(componentStatusDictionary)"""

    # B - store and shift, bit by bit
    for signal in signalList[::-1]:
        # shift register's behaviour
        # step 1 - signal (voltage high or low) is sent to serPin
        board.digital_write(serPin, signal)
        # step 2 - shift register clock turns from low to high, triggers shift register to read the serPin value 
        board.digital_write(srclkPin, 1)
        # step 3 - SRCLK turns low to prepare shift register for another rising edge (only shift the data when it's from low to high) 
        board.digital_write(srclkPin, 0)
    
    # step 4 - copy values in the shift register into the storage register
    board.digital_write(rclkPin, 1)
    # step 5 - turn off RCLK to prepare for storing a new wave of values
    board.digital_write(rclkPin, 0)

"""sr = shift_register_updater([0,0,0,0,0,0,0,0], 1,2,3)

d = {"x": sr(1),
     "y": sr(2),
     "z": sr(3)}

d["x"](1)
d["y"](1)
d["z"](1)
d["y"](0)
d["x"](0)"""

def subsystem_1():
    # compare stage (int) to integer
    if get_state('sub1Stage') == 0:
        signal({'tl1Green': 0, 'tl1Yellow': 1, 'tl2Green': 0, 'tl2Yellow': 1, 'wl1Astable':1})
        sub1Buzzer(1)
        update_stage('sub1Stage', 1)
    if get_state('sub1Stage') == 1 and timer(get_timestamp('sub1Stage'), 1):
        signal({'tl1Yellow': 0, 'tl1Red': 1, 'tl2Yellow': 0, 'tl2Red': 1, 'wl1Astable':1})
        update_stage('sub1PA1Stage', 1)
        update_stage('sub1Stage', 2)
    if get_state('sub1Stage') in [1,2,3] and get_state('sub1PA1Stage') == 1 and timer(get_timestamp('sub1PA1Stage'), 30):
        update_stage('sub1PA1Stage', 2)
        sub1Buzzer(2)
    if get_state('sub1Stage') == 2 and (0 < readComponents['us2']() < 10 or 0 < readComponents['us3']() < 10):
        update_stage('sub1Stage', 3)
    if get_state('sub1Stage') == 3 and not get_state('sub3') and not get_state('sub4'):
        sub1Buzzer(0)
        print("turning off buzzer")
        signal({'tl1Green': 1, 'tl1Yellow': 0, 'tl1Red': 0, 'tl2Green': 0, 'tl2Yellow': 0, 'tl2Red': 0, 'wl1Astable':0})
        update_stage('sub1Stage', 0)
        deactivate_subsystem('sub1')

def subsystem_2():
    if get_state('sub2Stage') == 0 and timer(get_timestamp('sub2'), 2):
        signal({'tl4GreenYellow': 1})
        update_stage('sub2Stage', 1)
    if get_state('sub2Stage') == 1 and timer(get_timestamp('sub2Stage'), 2):
        signal({'tl4YellowRed': 1, 'pl1RedGreen': 0})
        update_stage('sub2Stage', 2)
    if get_state('sub2Stage') == 2 and timer(get_timestamp('sub2Stage'), 3):
        signal({'pl1RedGreen': 1, 'pl1RedBlink': 0})
        update_stage('sub2Stage', 3)
    if get_state('sub2Stage') == 3 and timer(get_timestamp('sub2Stage'), 2):
        signal({'pl1RedBlink': 1, 'tl4YellowRed': 0, 'tl4GreenYellow': 0})
        update_stage('sub2Stage', 0)
        deactivate_subsystem('sub2')
    
def subsystem_3():
    if get_state('sub3Stage') == 0:
        signal({'tl5Red':0,'tl5Yellow':1,'tl5Green':0,'tl5GreenBlink':0,'fl1Fl2':1, 'tl4GreenYellow': 1, 'tl4YellowRed': 0})
        update_stage('sub3Stage', 1)
    if get_state('sub3PB1Stage') == 0 and get_state('sub3Stage') == 1 and readComponents['pb1Button'] == 0:
        signal({'pl1RedGreen':0, 'pl1RedBlink':1})
        update_stage('sub3PB1Stage', 1)
    if get_state('sub3Stage') == 1 and timer(get_timestamp('sub3Stage'), 2):
        signal({'tl5Red':0,'tl5Yellow':0,'tl5Green':1,'tl5GreenBlink':0,'fl1Fl2':1, 'tl4YellowRed': 1})
        update_stage('sub3Stage', 2)
    if get_state('sub3Stage') == 2 and timer(get_timestamp('sub3Stage'), 5):
        signal({'tl5Red':0,'tl5Yellow':0,'tl5Green':1,'tl5GreenBlink':1,'fl1Fl2':1, 'tl4GreenYellow': 0, 'tl4YellowRed': 0})
        update_stage('sub3Stage', 3)
    if get_state('sub3Stage') == 3 and readComponents['us3']() > 10:
        signal({'tl5Red':1,'tl5Yellow':0,'tl5Green':0,'tl5GreenBlink':0,'fl1Fl2':0, 'tl4GreenYellow': 0, 'tl4YellowRed': 0, 'pl1RedGreen': 1, 'pl1RedBlink': 1})
        deactivate_subsystem('sub3')
        update_stage('sub3Stage', 0)

def subsystem_4():
    if get_state('sub4Stage') == 0:
        signal({'tl3Red': 1, 'tl3Green': 0, 'wl2Red': 1})
        update_stage('sub4Stage', 1)
    if get_state('sub4Stage') == 1 and 0 < readComponents['us3']() < 10:
        signal({'tl5Red':0,'tl5Yellow':1,'tl5Green':0,'tl5GreenBlink':0,'fl1Fl2':1})
        update_stage('sub4Stage', 2)
    if get_state('sub4Stage') == 2 and timer(get_timestamp('sub4Stage'), 2):
        signal({'tl5Red':0,'tl5Yellow':0,'tl5Green':1,'tl5GreenBlink':0,'fl1Fl2':1})
        update_stage('sub4Stage', 3)
 
    if get_state('sub4Stage') == 3 and readComponents['us2']() > 10 and readComponents['us1']() > 10:
        signal({'tl3Red': 0, 'tl3Green': 1, 'wl2Red': 0, 'tl4GreenYellow': 0, 'tl4YellowRed': 0})
        update_stage('sub4Stage', 0)
        deactivate_subsystem('sub4')

sub1Buzzer = buzzer(buzzerPin)

readComponents = {component[0]:pin_reader(component[1]) for component in inputPins}

updateUS1, readComponents["us1"] = sonar_reader(9, 8)

updateUS2, readComponents["us2"] = sonar_reader(11, 10)

updateUS3, readComponents["us3"] = sonar_reader(13, 12)


updateUS = [updateUS1,updateUS2,updateUS3]

def main() -> None:
    for update in updateUS:
        update()

    if 0 < readComponents['us1']() < 10 and not get_state('sub1'):
        activate_subsystem('sub1')  
        print(f"Detected overheight vehicle at US1.\nTotal Height: {20 + (10 - readComponents['us1']())}\nExceeding by: {(10 - readComponents['us1']())}")
    
    if (not get_state('sub3') or not get_state('sub4')) and readComponents['pb1Button']() == 0 and timer(get_timestamp('sub2'), 30) and not get_state('sub2'):
        activate_subsystem('sub2')
        print("PB1 has been pressed")

    if 0 < readComponents['us3']() < 10 and not get_state('sub3'):
        activate_subsystem('sub3')
        deactivate_subsystem('sub2')
        print(f"Detected overheight vehicle at US3.\nTotal Height: {20 + (10 - readComponents['us3']())}\nExceeding by: {(10 - readComponents['us3']())}")
    
    if 0 < readComponents['us2']() < 10 and not get_state('sub4'):
        activate_subsystem('sub4')
        deactivate_subsystem('sub2')
        print(f"Detected overheight vehicle at US2.\nTotal Height: {20 + (10 - readComponents['us2']())}\nExceeding by: {(10 - readComponents['us2']())}")

    if get_state('sub1'):
        subsystem_1()
    if get_state('sub2'):
        subsystem_2()
    if get_state('sub3'):
        subsystem_3()
    if get_state('sub4'):
        subsystem_4()

if __name__ == "__main__":
    time.sleep(1)
    print("Starting System")
    try:
        while True:
            main()
    except KeyboardInterrupt:
        print("Shutting down...")
        board.shutdown()
        quit()
