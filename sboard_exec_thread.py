# 0_1 1st attempt to use i2c - Done
# 0_2 Need to increase speed - make Lou selections optional - Done
# and modify the timing routines to only use delta time - Done
# also turned logging off - Done
# 0_3 fixed serial port byte reading issue - Done
# 0_4 streamline time conversions - Done
# 0_5 added in the json config data - Done
# 0_6 tidied up the clock and score update loop
# 0_7 still dealing with SPI issues
# 0_8 add some control codes in team strings and check whether running as a service
# 0_9 incorporate team names
# 0_10 incorporate vms

import os
import json
import datetime
import threading
from time import time, ctime, sleep
import pigpio as GPIO
import serial
import string
from sys import platform

# our functions
import s_data1 as s_data  # includes all the data structure info

from scoreboardv1 import log_it as log_it
from scoreboardv1 import check_int as check_int
from scoreboardv1 import check_allint as check_allint
from scoreboardv1 import set_data_spi as set_data_spi
from scoreboardv1 import set_chars_spi as set_chars_spi
from scoreboardv1 import send_digits_spi as send_digits_spi
from scoreboardv1 import send_i2c_bright_data as send_i2c_bright_data
from scoreboardv1 import send_i2c_colour_data as send_i2c_colour_data
from scoreboardv1 import send_i2c_digit_data as send_i2c_digit_data
from scoreboardv1 import sound_siren as sound_siren

# check whether the scoreboard service is already running
# it is actually this program running as a system service
# if it is then we don't want to output clr for the console screen
# it will end up being a TERM environment variable errors
# if 0 is returned from following it means the service is running
# anything else means it is not

if platform  == 'linux':
    os.system('systemctl is-active --quiet scoreboard')

# create local PI GPIO
    p1 = GPIO.pi()

else:
    p1 = GPIO.pi('Aussport')
if not p1.connected:
    print("NO Connection! Exiting!")
    exit

# grab all of the scoreboard data from the file
scoreboard = (s_data.get_scoreboard_data('config.json'))

board = s_data.get_board(scoreboard)  # all the general info about the board
sport = s_data.get_sport(scoreboard)  # which sport is this board set up for
comms = s_data.get_comms(scoreboard)  # all comms related parameters
names = s_data.get_names(scoreboard)  # all the personalised names for this board
s_spi = s_data.get_spi(scoreboard)  # critcial SPI port settings
s_i2c = s_data.get_i2c(scoreboard)  # critical I2C port settings


# set up the Serial Port
if platform == 'linux':
    com_port = comms['com_port_pi']
else:
    com_port = comms['com_port_win']
ser = serial.Serial(

    port=com_port,
    baudrate=comms['com_baud'],
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout=comms['timeout']
)

comms_start_char = bytes.fromhex(comms['start_char'])
comms_end_char = bytes.fromhex(comms['end_char'])
max_comm_string = comms['max_comm_string']

ser.reset_input_buffer()  # flush out any rubbish already there

serial_flag = 0

def thread_serial(ser):
    global serial_flag, x
    if ser.in_waiting > 0:
        Comms_Error = ''
    # print('*')
        if ser.read() != comms_start_char:
            Comms_Error = 'Message Discarded!'
            st1 = ser.read_until(comms_end_char, max_comm_string)
            log_it(logging, f'Comms: {st1}')
            log_it(logging, Comms_Error)
            serial_flag = 0
        else:
            st1 = ser.read_until(comms_end_char, max_comm_string).decode("utf-8", "replace")
            x = st1.replace(chr(65533), ' ')
            x = x[:len(x) - 1]  # remove the Ctrl t char at the end
            print(f'Current Comms: {x}')
            if x[0] != 'K' or 'L':
                serial_flag = check_allint(x)  # check what has been received is all integers
            else:
                serial_flag = True  # mix of char and numbers so can't check
            if serial_flag == True:
                Last_Comms = f'Message Received: {x}'
                Comms_Error = f'Valid Message! Length: {len(x)}'
            else:
                Comms_Error = f'Message Corrupt: {x} Length: {len(x)}'
                log_it(logging, f'Comms: {x}')
                log_it(logging, Comms_Error)


# set up the port arrays. These show the position of the digit no. in the scoreboard dictionary
# in it's correct location in the spi port or which channel it is in the i2c port


def send_screen():
    if platform == 'linux':
        os.system('clear')  # clear the screen
    else:
        os.system('cls')
    print(Message0)
    print(Message1)
    print(Message2)
    #	print(s_loc)
    #	print(s_spi)
    print(Spec_Message)
    print('\r')

    print(Last_Comms)
    print(Comms_Error)
    print('\r')

    print(f"Clock: {ClkStr}\r")
    print('\r')

    print(TimerMessage1)
    print(TimerMessage2)

    print(f"Timer: {TimeStr}")
    print('\r')

    Home, Home_Behinds, Home_Total = s_data.get_team_scores(scoreboard, s_loc, "Home")
    Away, Away_Behinds, Away_Total = s_data.get_team_scores(scoreboard, s_loc, "Away")
    Quarter = s_data.get_quarter(scoreboard, q_loc)    
    if Quarter > 0 :
      print(f'Quarter: {Quarter}')
    print(f'{tn1} Scores: G {Home} B {Home_Behinds} T {Home_Total}')
    print(f'{tn2} Scores: G {Away} B {Away_Behinds} T {Away_Total}')
    print(f'VMS: {vms1}')

    print('\r')
    print(f'Current brightness: {brightness}')


logging = False  # set True/False to turn on/off capture of logging data in 'scorelog.txt'

# get the config information defaults and then what is on file


# general strings to help display useful information.

appName = 'Scoreboard Controller V0.11 '
board_type = board.get('board_type')
board_digit_size = board.get('digit_size')
sport_version = board.get('sport')
current_sport = sport.get(sport_version)
sport_name = current_sport['name']


TimerState = ('ON', 'Paused')
TimerDir = ('NONE', 'UP', 'DOWN')

# Global data structure
Home = 0
Away = 0
Home_Behinds = 0
Away_Behinds = 0
Home_Total = 0
Away_Total = 0
Quarter = 0
tens = 0
unit = 0

CurrentTime = time()  # get the curent time
PrevTime = CurrentTime
LouTime = CurrentTime
DiffTime = CurrentTime - PrevTime
end_siren_time = time()  # this time variable gets loaded whenever a siren instruction occurs

DispStr = ctime(CurrentTime)

ClkStr = DispStr[11:19]
TimeStr = "00:00.00"

NumSeconds = -1
NumMinutes = -1
NumHours = -1
DisplaySec = -1
DisplayMin = -1
DisplayHour = -1
ElapsedSecs = float(0)
TimeLeft = float(0)


# NB the SPI channel is set in spi_flag in the spi key "port_settings" as follows:
# 0 means main spi, 1 means aux spi
# the chip select is then determined by the chan value in the same key for the port
# however because of flickering of the display the chip select function is not used
# config.json provides the latch pin location as a substitute for the chip select
# latch is held low until the data has been shifted across via SPI to the shift registers
# in the digits. Latch is then taken high to 'latch' the current data and immediately dropped low
# this avoids seeing any of the shift transitions 'on the scoreboard'
# Straight digital pins below on Pi are either Out for Output or In for Input




siren_pin = 6    # 31			BLAM		23


# SPI clock frequency
freq = 5000000

# general program defs

x = []  # serial data list
d1 = []  # first data port list
d2 = []  # second data port list
d3 = []  # third data port list
s1 = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]  # score data
clk = [0, 0, 0, 0, 0, 0]  # clock data
#clk2 = [0, 0, 0, 0, 0, 0]  # clock data for i2c display
t1 = [0, 0, 0, 0, 0, 0]  # timer data
t2 = [0, 0, 0, 0, 0, 0]  # timer data for i2c display

tn1 = names.get('Home')
tn2 = names.get('Away')
vms1 = names.get('Vms1')
maxteamname = board.get('max_team_name')
maxvms = board.get('max_vms')
vms_scroll = board.get('vms_scroll')
brightness = board.get('brightness')

timer_update = False
run_timer = False
siren_time = board.get('siren_time')  # no. of seconds to sound the siren
siren_on = 0
# PyCharm says it is declared above....TimeLeft = 0.0
CountDir = 0
TotMins = 0
TotSeconds = 0
# Declared above as a float ElapsedSecs = 0.0
normal_loop = 1
fast_loop = .05

i2c_settings = scoreboard['i2c']['port_settings']

#i2c has to be enabled in raspi-config interface settings

# the channels are set as follows:
# If channel is 0 then it will be a standard i2c port on the PI
# Clk Pin 28 (ID_SC GPIO 0) Data Pin 27 (ID_SD GPIO 1)
# i2c channel 0 has to be enabled in the Device Tree overlay
# Enable it by adding "dtpar  am=i2c_vc=on" in /boot/config.txt

# If channel is 1 then it will be the standard i2c port on the PI
# Clk Pin 05 (SCL GPIO 3) Data Pin 03 (SDA GPIO 2)


SPI = (s_spi['state'] == 'ON')
I2C = (s_i2c['state'] == 'ON')  # select which hardware output to use

oe_pin = s_spi['OE']            # set which pin controls the LED output (used by SPI only)

p1.set_mode(siren_pin, GPIO.OUTPUT)
p1.write(siren_pin, 0)  # Make sure the siren stays off

# make sure we set pull ups and the output pins
if SPI:
    p1.set_mode(oe_pin, GPIO.OUTPUT)


    p1.write(oe_pin, 1)  # Disable output for the SPI LED's


    p1.set_PWM_dutycycle(oe_pin, brightness)  # start off at 50% brightness

if I2C:
    send_i2c_bright_data(p1, scoreboard)

old_brightness = brightness
loopval = normal_loop
clk_update = True
score_update = True
timer_update = False
run_timer = False

#prepare the standard messages for on-screen and log file
Message0 = appName + board_type + board_digit_size + ' Playing: ' + sport_name
Message1 = 'AusSport Scoreboards - all rights reserved'
Message2 = 'Scoreboard Start Up Testing....'
Spec_Message = ''
TimerMessage1 = 'Timer is OFF'
TimerMessage2 = ''
Last_Comms = 'No Comms Received'
Comms_Error = ''

log_it(logging, appName)
log_it(logging, Message1)

s_data.set_leds_state(scoreboard)
s_loc, c_loc, q_loc, tn_loc, vms_loc = s_data.set_all_locations(scoreboard)

send_screen()

if I2C:
    send_i2c_colour_data(p1, scoreboard)    #need to get colours set before first chars

def test_seq(scoreboard, s_loc, c_loc, q_loc, tn_loc, s_spi, dig_val):
#this sequence runs through the digits with a short time delay between shifting to the next one

    clk = [32,32,32,32,32,32]
    s1 = [32, 32, 32, 32, 32, 32, 32, 32, 32, 32, 32, 32, 32, 32, 32, 32]  # score data
    s_data.set_all_scores(scoreboard, s_loc, s1)
    if bool(q_loc):
        s_data.set_quarter(scoreboard, q_loc, 32)
    if bool(tn_loc):
        s_data.set_team_names(scoreboard, tn_loc, "Home", "Away")
    for i in range(0,len(clk)):
        clk[i] = dig_val
 #   s_data.set_clock(scoreboard, c_loc, clk)
        s_data.set_clock_new(scoreboard, clk)
        if SPI:
            s_data.create_spi_hw(scoreboard)
        # send it out!
            for k_port, v in s_spi['port_ziku'].items():
                Freq = s_spi['freq']
                Channel = s_spi['port_settings'][k_port]['chan']
                Flags = s_spi['port_settings'][k_port]['spi_flag']
                Latch = s_spi['port_settings'][k_port]['latch_pin']
                send_digits_spi(p1, Freq, Channel, Flags, Latch, v, "", 0)
        if I2C:
            send_i2c_colour_data(p1, scoreboard)
            send_i2c_digit_data(p1, scoreboard )
        sleep(0.5)
 #   clk[i] = 32
#s_data.set_clock(scoreboard, c_loc, clk)
    s_data.set_clock_new(scoreboard, clk)
    if bool(q_loc):
        s_data.set_quarter(scoreboard, q_loc, 8)
    sleep(0.5)
    tn1 = "TEAM1"
    tn2 = "TEAM2"
    for i in range(0,len(s1)):
        s1[i] = dig_val
        s_data.set_all_scores(scoreboard, s_loc, s1)
        if bool(tn_loc):
            s_data.set_team_names(scoreboard, tn_loc, tn1, tn2)
        if SPI:
            s_data.create_spi_hw(scoreboard)
        # send it out!
            for k_port, v in s_spi['port_ziku'].items():
                Freq = s_spi['freq']
                Channel = s_spi['port_settings'][k_port]['chan']
                Flags = s_spi['port_settings'][k_port]['spi_flag']
                Latch = s_spi['port_settings'][k_port]['latch_pin']
                send_digits_spi(p1, Freq, Channel, Flags, Latch, v, "",0)
        if I2C:
            send_i2c_colour_data(p1, scoreboard)
            send_i2c_digit_data(p1, scoreboard)
        sleep(0.5)

#test_seq(scoreboard, s_loc, c_loc, q_loc, tn_loc, s_spi, 8)
s1 = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]  # score data
clk = [0, 0, 0, 0, 0, 0]  # clock data
s_data.set_all_scores(scoreboard, s_loc, s1)
#s_data.set_clock(scoreboard, c_loc, clk)
s_data.set_clock_new(scoreboard, clk)
if bool(q_loc):
    s_data.set_quarter(scoreboard, q_loc, 0)

Message2 = 'Scoreboard initialised - waiting for commands on serial port!'
send_screen()
ser_thread = threading.Thread(target=thread_serial, args=(ser,), daemon=True)
ser_thread.start()

while True:

    if serial_flag == 1:

        message_type = x[0]

        # Single Score update message
        # Sends the particular score and the total
        # no other digits affected
        if message_type == 'W':

            if len(x) > 2:
                if x[1] == '1':  # home team score
                    s1[0] = x[2] ; s1[1] = x[3] ; s1[2] = x[4]
                if x[1] == '2':  # home team behinds
                    s1[3] = x[2] ; s1[4] = x[3]                       
                if x[1] == '3':  # home team total
                    s1[5] = x[2] ; s1[6] = x[3] ; s1[7] = x[4]
                if x[1] == '4':  # away team score
                    s1[8] = x[2] ; s1[9] = x[3] ; s1[10] = x[4]
                if x[1] == '5':  # away team behinds
                    s1[11] = x[2] ; s1[12] = x[3]                     
                if x[1] == '6':  # away team total
                    s1[13] = x[2] ; s1[14] = x[3] ; s1[15] = x[4]                    
                elif ( (x[1] == '9') or (x[1] == '0') )  : # quarter info - depends on which Lou program
                    s_data.set_quarter(scoreboard, q_loc, int(x[2]))
                    Quarter = int(x[2])
                Home = int(s1[0]) * 100 + int(s1[1]) * 10 + int(s1[2])
                Home_Behinds = int(s1[3]) * 10 + int(s1[4])
                Home_Total = int(s1[5]) * 100 + int(s1[6]) * 10 + int(s1[7])
                Away = int(s1[8]) * 100 + int(s1[9]) * 10 + int(s1[10])
                Away_Behinds = int(s1[11]) * 10 + int(s1[12])
                Away_Total = int(s1[13]) * 100 + int(s1[14]) * 10 + int(s1[15])
                if ser.in_waiting > 1:
                    score_update = False
                else:
                    score_update = True

            else:
                Comms_Error = 'Message Too Short!'




        # All score update message
        elif message_type == 'A':

            if len(x) > 5:
                Message2 = 'All Score Update'
                s1[:] = []
                for i in range(1, len(x)):
                    s1.append(x[i])

                Home = int(s1[0]) * 100 + int(s1[1]) * 10 + int(s1[2])
                Home_Behinds = int(s1[3]) * 10 + int(s1[4])
                Home_Total = int(s1[5]) * 100 + int(s1[6]) * 10 + int(s1[7])

                Away = int(s1[8]) * 100 + int(s1[9]) * 10 + int(s1[10])
                Away_Behinds = int(s1[11]) * 10 + int(s1[12])
                Away_Total = int(s1[13]) * 100 + int(s1[14]) * 10 + int(s1[15])


            else:
                Comms_Error = 'Message Too Short!'

            score_update = True

        # Brightness control message
        elif message_type == 'B':
            Message2 = 'Brightness Update'
            if x[1] == '1':
                brightness = 254
            if x[1] == '2':
                brightness = 192
            if x[1] == '3':
                brightness = 128
            if x[1] == '4':
                brightness = 64
            if x[1] == '5':
                brightness = 32




        # Timer setup message either count up or count down
        # Also sent when timer pauses

        elif message_type == 'D':
            Message2 = 'Timer Setup'
            x = x.ljust(7,"0")
            t1[:] = []  # for spi
            t2[:] = []  # for i2c
            TimeStr = f"{x[1]}{x[2]}:{x[3]}{x[4]}:{x[5]}{x[6]}"
            t1 = [0, 0, TimeStr[3], TimeStr[4], TimeStr[0], TimeStr[1]]
            t2 = [TimeStr[0], TimeStr[1], TimeStr[3], TimeStr[4], 0, 0]
            NumMinutes = int(x[1]) * 10 + int(x[2])
            NumSeconds = int(x[3]) * 10 + int(x[4])
            MilliSeconds = float(int(x[5]) * 10 + int(x[6]))
            MilliSeconds = MilliSeconds / 100
            timer_update = True
            s_data.set_clock_dot(scoreboard, c_loc)
            run_timer = False
            if (NumMinutes == 0) and (CountDir != 1):   #only change display position for count down
                t1 = [0, 0, TimeStr[6], TimeStr[7], TimeStr[3], TimeStr[4]]
                t2 = [TimeStr[3], TimeStr[4], TimeStr[6], TimeStr[7], 0, 0]
                loopval = fast_loop
            else:
                t1 = [0, 0, TimeStr[3], TimeStr[4], TimeStr[0], TimeStr[1]]
                t2 = [TimeStr[0], TimeStr[1], TimeStr[3], TimeStr[4], 0, 0]
                loopval = normal_loop
            s_data.set_clock_new(scoreboard, t2)


        # Clock display message
        elif message_type == 'M':
            if len(x) > 5:  # enough bytes to process
                Message2 = 'Clock Update'
                CountDir = 0
                run_timer = False;  # turn off any running timers
                PauseTimer = 0
                TotSeconds = 0;
                TimeLeft = 0.0;
                ElapsedSecs = 0.0
                clk[:] = []  # for spi display use
           #     clk2[:] = []  # for i2c display use
                for i in range(1, len(x)):
                    clk.append(x[i])
           #         clk2.append(x[len(x) - 1 - i])  # reverse order for i2c
                ClkStr = f"{clk[0]}{clk[1]}:{clk[2]}{clk[3]}:{clk[4]}{clk[5]}"
                DisplayHour = int(clk[0] + clk[1])
                DisplayMin = int(clk[2] + clk[3])
                DisplaySec = int(clk[4] + clk[5])
                # always set the system time to controller time
                OsStr = f"sudo date +%T -s {ClkStr}"
                os.system(OsStr)
                CurrentTime = time()
                PrevTime = CurrentTime
                loopval = normal_loop
                clk_update = True
                timer_update = False

            else:
                Comms_Error = 'Message Too Short!'

        # Team Names Message
        elif message_type == 'K':  # team names message
            if x[1:4] == "+++":     #means this is a control command transmission
                ctrl_cmnd = x[4:6]
                ctrl_val = 0
                try:
                    ctrl_val = int(x[6:8])
                    Message2 = f'Control Command {ctrl_cmnd} {ctrl_val}'
                except:
                    Message2 = f'Control Command {ctrl_cmnd}'
                if ctrl_cmnd == "TS":
                    if ctrl_val == 0:
                        dig_val = 8
                    else:
                        dig_val = ctrl_val
                    test_seq(scoreboard, s_loc, c_loc, q_loc, s_spi, dig_val)
                if ctrl_cmnd == "BR":
                    scoreboard['brightness'] = brightness
                    s_data.set_scoreboard_data('config.json', scoreboard)
            else:
                Message2 = 'Team Names Update'
                tn1 = x[1:maxteamname + 1]
                tn2 = x[maxteamname +1:(maxteamname*2) + 1]
                if bool(tn_loc):
                    s_data.set_team_names(scoreboard,tn_loc,tn1,tn2)
            #			if  "exit" in tn1:
            #				exit()
                log_it(logging, "Team Name 1: {tn1}")
                log_it(logging, "Team Name 2: {tn2}")

        # VMS Message
        elif message_type == 'L':  # VMS message
            Message2 = 'VMS Update'
            vms1 = x[1:maxvms + 1]
            if bool(vms1_loc):
                s_data.set_vms(scoreboard,vms1_loc,vms1)

            log_it(logging, "Vms1: {vms1}")


        # siren Sound Message
        elif message_type == 'P':
            Message2 = 'Siren Sound'
            end_siren_time = sound_siren(p1, siren_time, siren_pin)
            siren_on = 1

        # sport selection message
        elif message_type == 'V':
            Message2 = 'Sport Selector'
            board['sport'] = x[0:2]
            sport_version = board.get('sport')
            current_sport = sport.get(sport_version)
            sport_name = current_sport['name']
            s_data.set_leds_state(scoreboard)
            s_loc, c_loc, q_loc, tn_loc, vms_loc = s_data.set_all_locations(scoreboard)
            Message0 = appName + board_type + board_digit_size + ' Playing: ' + sport_name
            screen_update = True

        # Timer start message
        elif message_type == 'T':
            Message2 = 'Timer Start'
            t1[:] = []
            t2[:] = []  # for i2c use
            for i in range(2, len(x)):
                t1.append(x[i])
                t2.append(x[i])
            TimeStr = f"{t1[0]}{t1[1]}:{t1[2]}{t1[3]}:{t1[4]}{t1[5]}"
            log_it(logging, f"Timer Set: {TimeStr}")
            CurrentTime = time()
            PrevTime = CurrentTime
            NumMinutes = int(x[2]) * 10 + int(x[3])
            NumSeconds = int(x[4]) * 10 + int(x[5])
            MilliSeconds = float(int(x[6]) * 10 + int(x[7]))
            MilliSeconds = MilliSeconds / 100

            if len(x) > 9:  # the starting T message always has the total mins in it
                # by only checking when there are 9 or more numbers should
                # avoid value errors in the next statement
                TotMins = (int(x[8]) * 10 + int(x[9]))
                TotSeconds = (TotMins * 60)

            #			TimerTime = CurrentTime + (NumMinutes * 60) + NumSeconds + int(MilliSeconds*1000)

            if x[1] == '1':  # count up
                # means the time received is how far along
                # the timer is progressed
                ElapsedSecs = float(NumMinutes * 60 + NumSeconds + MilliSeconds)
                TimeLeft = float(TotSeconds - ElapsedSecs)
                TimerTime = CurrentTime + TimeLeft
                CountDir = 1

            if x[1] == '2':  # count down
                # means the time received is how far along
                # the timer is progressed

                TimeLeft = float(NumMinutes * 60 + NumSeconds + MilliSeconds)
                ElapsedSecs = float(TotSeconds - TimeLeft)
                TimerTime = CurrentTime + TimeLeft
                CountDir = 2

            log_it(logging, f"Timer Set to Count: {TimerDir[CountDir]}")

            run_timer = True  # start the timer

            timer_update = True  # make sure the data structures and hardware know

    # this marks the end of the signal processing
    #
    # this is the start of time based processing

    CurrentTime = time()  # get the current time
    if (CurrentTime - PrevTime) >= loopval:  # loopval has elapsed!
        # first check on the siren - when this goes to audio out maybe change a lot of this one
        if siren_on == 1:
            Message2 = f"siren is On for secs {end_siren_time - CurrentTime}"
            if end_siren_time <= CurrentTime:
                siren_on = 0
                p1.write(siren_pin, 0)
                Message2 = "Waiting for comms"

        if run_timer:
            timer_update = True
            clk_update = False
        else:
            clk_update = True

        if clk_update:
            DispTime = CurrentTime + DiffTime
            DispStr = ctime(DispTime)

            ClkStr = DispStr[11:19]  # get the display time and drop it into the clock string

      #      clk = [ClkStr[6], ClkStr[7], ClkStr[3], ClkStr[4], ClkStr[0], ClkStr[1]]
            clk = [ClkStr[0], ClkStr[1], ClkStr[3], ClkStr[4], ClkStr[6], ClkStr[7]]

        PrevTime = CurrentTime  # set up for the next counting loop

    if clk_update and not timer_update:
        # need to rewrite the data into the scoreboard data structure
        # firstly toggle the dot(s) to show the clock is active
        s_data.toggle_clock_dot(scoreboard, c_loc)
        # then update the clock digits
#        s_data.set_clock(scoreboard, c_loc, clk)
        s_data.set_clock_new(scoreboard, clk)
        #       Spec_Message = f'Clk: {clk} c_loc: {c_loc}'
        screen_update = True

    if timer_update:


        if run_timer:
            # when the timer is running OR paused then it is displaying
            clk_update = False
            TimerMessage2 = f'Timing is set for {TotMins:#} minutes. Time left {TimeLeft:#.2f} Elapsed {ElapsedSecs:#.2f}'
            TimerMessage1 = f'Timer is Counting {TimerDir[CountDir]} and is ON'
            TimeLeft = TimerTime - CurrentTime
            ElapsedSecs = float(TotSeconds - TimeLeft)
            if TimeLeft <= 0:
                TimerMessage2 = 'Timer is Done!'
                loopval = normal_loop  # need to reset so display returns to normal
                end_siren_time = sound_siren(p1, siren_time, siren_pin)
                siren_on = 1        #tells the rest of the world that the siren is firing
                TimeLeft = 0
                ElapsedSecs = TotSeconds

                run_timer = False

            if CountDir == 1:  # counting up
                TimeShow = ElapsedSecs
            else:  # must be counting down
                TimeShow = TimeLeft

            NumMinutes = int(TimeShow // 60)
            NumSeconds = int(TimeShow % 60)
            MilliSeconds = float(int((TimeShow - int(TimeShow)) * 100))
            TimeStr = f'{NumMinutes:02d}:{NumSeconds:02d}.{int(MilliSeconds):02d}'
            if CountDir == 1:  # counting up
                t1 = [TimeStr[6], TimeStr[7], TimeStr[3], TimeStr[4], TimeStr[0], TimeStr[1]]
                t2 = [TimeStr[0], TimeStr[1], TimeStr[3], TimeStr[4], TimeStr[6], TimeStr[7]]
                loopval = normal_loop
            else:  # counting down
                if (NumMinutes == 0):
                    t1 = [0, 0, TimeStr[6], TimeStr[7], TimeStr[3], TimeStr[4]]
                    t2 = [TimeStr[3], TimeStr[4], TimeStr[6], TimeStr[7], 0, 0]
                    loopval = fast_loop
                    screen_update = False
                else:
                    t1 = [TimeStr[6], TimeStr[7], TimeStr[3], TimeStr[4], TimeStr[0], TimeStr[1]]
                    t2 = [TimeStr[0], TimeStr[1], TimeStr[3], TimeStr[4], TimeStr[6], TimeStr[7]]
                    if clk_update:
                        screen_update = True
            # need to rewrite the data into the scoreboard data structure
            #        s_data.set_clock(scoreboard, c_loc, t2)
            s_data.set_clock_new(scoreboard, t2)

        else:  # timer has gone into it's stopped mode
            TimerMessage1 = 'Timer is OFF'
            if clk_update:          #only update the screen based on a tic...not all the time!
                screen_update = True



    if score_update:
        s_data.set_all_scores(scoreboard, s_loc, s1)  # saves the scores into the data structure scoreboard
   #     log_it(True, scoreboard['leds']['10']['val'])
        screen_update = True

    if clk_update or timer_update or score_update:
        # now get the updated values in a form that can be sent to hardware

        if SPI:
            s_data.create_spi_hw(scoreboard)
            # send it out!
            for (k_port, v),(k1_port, v1),(kbmp_port,bmp_state) in zip(s_spi['port_ziku'].items(),s_spi['port_ziku_lower'].items(),s_spi['port_bmp_flag'].items()):
                Freq = s_spi['freq']
                Channel = s_spi['port_settings'][k_port]['chan']
                Flags = s_spi['port_settings'][k_port]['spi_flag']
                Latch = s_spi['port_settings'][k_port]['latch_pin']
                #log_it(True,f'Port: {k_port} {v}')
                send_digits_spi(p1, Freq, Channel, Flags, Latch, v, v1, bmp_state)
        if I2C:
            send_i2c_colour_data(p1, scoreboard)
            send_i2c_digit_data(p1, scoreboard)
        score_update = False
        clk_update = False
 #      timer_update = False


        d1[:] = []

    if screen_update:  # show the diagnostic screen
        send_screen()
        screen_update = False

    if old_brightness != brightness:  # must have to reset the brightness
        board['brightness'] = brightness
        if SPI:
            p1.set_PWM_dutycycle(oe_pin, brightness)  # set the brightness level
        if I2C:
            send_i2c_bright_data(p1, scoreboard)
        old_brightness = brightness
