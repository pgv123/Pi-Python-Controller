# data dictionary and json file storage approach
# style of the data dictionary is as follows:
#
# board --- type, digit size, ziku data (translates numbers to binary sequence for the segments), ziku segs (need to know so we get the right amount of data), 
#			bit map data for team names and vms (bmp)
# comms --- port, baud, timeout
# spi 	---	freq, ports used (this is built at runtime using the fn - get_spi_vals) because we need to know
#			the exact order of the digits matched to their port
# i2c	---	freq, ports used (built at runtime using the fn - get_i2c_vals)
# leds	---	indexing number --> type, colour, set, group, units, spi_port, i2c_port, spi (position in the data string),
#			i2c channel, state (ie whether it is in this board), value

# the intent is to use this dictionary for all data control on the board...hence the large number of functions
# below

import os
import json
import Ziku


def read_config(file):
	with open(file,'r') as conf:
		dict1 = json.load(conf)
	return dict1

def write_config(file, dict1):
	with open(file,'w') as conf:
		json.dump(dict1, conf, indent=4 )

def get_scoreboard_data(file):
    return read_config(file)


def set_scoreboard_data(file, s1):
    write_config(file, s1)


def get_board(s1):
    return s1['board']

def get_sport(s1):
    return s1['sport']

def get_this_sport(s1, version):
    return s1['sport'][version]

def get_names(s1):
    return s1['names']


def get_comms(s1):
    return s1['comms']


def get_spi(s1):
    return s1['spi']


def get_i2c(s1):
    return s1['i2c']


def get_leds(s1):
    return s1['leds']


def get_active_leds(s1):
    active_leds = {k: v for k, v in s1['leds'].items() if is_active(v)}
    return active_leds

def get_physical_leds(s1):
    physical_leds = {k: v for k, v in s1['leds'].items() if is_physical(v)}
    return physical_leds

def get_active_clock_leds(s1):
    clock_leds = {k: v for k, v in s1['leds'].items() if is_active(v) and is_clock(v)}
    return clock_leds

def get_ziku(s1, port):
    return getattr(Ziku, s1['spi']['port_settings'][port]['ziku'])


def get_ziku_segs(s1, port):
    return s1['spi']['port_settings'][port]['ziku_segs']

def get_dot_val(s1, port):
    return s1['spi']['port_settings'][port]["dot_val"]

def get_i2c_port(s1, port):
    leds = get_active_leds(s1)
    i2c_port = {k: v for k, v in leds.items() if is_port(v, port)}
    return i2c_port

def is_port(digit, pt):
    return digit['i2c_port'] == pt

def is_physical(digit):
    return digit['state'] != 'NC'

def is_active(digit):
    return digit['state'] == 'ON'


def is_home(digit):
    return digit['set'] == 'Home'


def is_away(digit):
    return digit['set'] == 'Away'


def is_clock(digit):
    return digit['set'] == 'Clock'

def is_quarter(digit):
    return digit['set'] == 'Quarter'

def is_digit(digit):
    return digit['type'] == 'digit'


def is_dot(digit):
    return digit['dot'] == 'YES'


def is_char(digit):
    return digit['type'] == 'char'


def is_colour(digit, colour):
    return digit['colour'] == colour


def is_group(digit, group):
    return digit['group'] == group


def is_set(digit, set):
    return digit['set'] == set


def is_team(digit, team):
    return digit['set'] == team

def set_sport(s1, vers):
    s1['board']['sport'] = vers

def set_leds_state(s1):
    version = get_board(s1).get('sport')
    leds = get_leds(s1)
    this_vers = get_this_sport(s1, version)
    digits = this_vers['Digits']
    for k, v in digits.items():
        leds[k]['state'] = v
        if v == 'OFF' :
            leds[k]['val'] = 32 #set to blank


def set_score_location(s1, team, score):
    leds = get_active_leds(s1)
    s_loc = {}  # s_loc entries match the Lou string locations for values
    score_leds = {k: v for k, v in leds.items() if (is_team(v, team) and is_group(v, score))}
    for k, v in score_leds.items():
        s_loc[v['units']] = k
    return s_loc


def set_team_score_location(s1, team):
    # returns a dict with the digit which corresponds to the particular 'unit' of that digit
    # eg if digits "1","2","3" are intended to be the Home teams "Score" with "1" as 100's, "2" as 10's
    # and "3" as 1's then the entry in the returned dict will be
    # {'Home': {'Score': {100: '1', 10: '2', 1: '3'}.......
    s_loc = {}
    s_loc[team] = {}
    s_loc[team]['Score'] = set_score_location(s1, team,
                                              'Score')  # s_loc entries match the Lou string locations for values
    s_loc[team]['Behinds'] = set_score_location(s1, team, 'Behind')
    s_loc[team]['Total'] = set_score_location(s1, team, 'Total')
    return s_loc

def set_quarter_location(s1):
    leds = get_active_leds(s1)
    q_loc = {}  # q_loc entries match the Lou string locations for values
    quarter_leds = {k: v for k, v in leds.items() if is_quarter(v) }
    for k, v in quarter_leds.items():
        q_loc[v['units']] = k
    return q_loc

def set_clock_group_location(s1, group):
    leds = get_active_leds(s1)
    c_loc = {}  # c_loc entries match the Lou string locations for values
    clock_leds = {k: v for k, v in leds.items() if (is_clock(v) and is_group(v, group))}
    for k, v in clock_leds.items():
        c_loc[v['units']] = k
    return c_loc


def set_clock_location(s1):
    # returns a dict with the digit which corresponds to the particular 'unit' of that digit
    # eg if digits "17","18" are intended to be the "Minute" with "17" as 10's, "18" as 1's
    # then the entry in the returned dict will be
    # {'Minute': {10: '17', 1: '18'}.......
    c_loc = {}
    c_loc['Hour'] = set_clock_group_location(s1, 'Hour')
    c_loc['Minute'] = set_clock_group_location(s1, 'Minute')  # c_loc entries match the Lou string locations for values
    c_loc['Second'] = set_clock_group_location(s1, 'Second')
    c_loc['Millisecond'] = set_clock_group_location(s1, 'Millisecond')
    return c_loc

# set up the score and clock locations in SPI
# these dicts show the order of the digit objects based on their "spi" key value

def set_all_locations(s1):
    s_loc = {}
    c_loc = {}
    q_loc = {}
    s_loc = set_team_score_location(s1, 'Home')
    sa_loc = set_team_score_location(s1, 'Away')
    s_loc.update(sa_loc)
    c_loc = set_clock_location(s1)
    q_loc = set_quarter_location(s1)
    return s_loc, c_loc, q_loc

def toggle_clock_dot(s1, c_loc):
    leds = get_active_leds(s1)
    #iterate over the groups in c_loc
    for k, v in c_loc.items():
        #iterate over the digits in each group
        for k1, v1 in v.items():
            if leds[v1]['dot'] != 'NO' :
                leds[v1]['dot_state'] ^= 1
    return

def set_clock_dot(s1, c_loc):
    leds = get_leds(s1)
    #iterate over the groups in c_loc

    for k, v in c_loc.items():
        #iterate over the digits in each group
        for k1, v1 in v.items():
            if leds[v1]['dot'] != 'NO' :
                leds[v1]['dot_state'] = 1
    return

def get_s_val(s1, s_loc, team, score):
    leds = get_leds(s1)
    s_val = 0
    s_sc = s_loc[team][score]
    for k, v in s_sc.items():
        s_val = s_val + leds[v]['val'] * k
    return s_val


def get_team_scores(s1, s_loc, team):
    Score = get_s_val(s1, s_loc, team, 'Score')
    Behinds = get_s_val(s1, s_loc, team, 'Behinds')
    Total = get_s_val(s1, s_loc, team, 'Total')
    return Score, Behinds, Total

def get_quarter(s1, q_loc):
    leds = get_active_leds(s1)
    if 1 in q_loc:	#test whether there is anything in q_loc
	    qtr_led = q_loc[1]
	    ret_val = leds[qtr_led]['val']
    else:
        ret_val = 0
    return ret_val

def get_c_val(s1, c_loc, group):
    leds = get_leds(s1)
    c_val = 0
    c_sc = c_loc[group]
    for k, v in c_sc.items():
        c_val = c_val + leds[v]['val'] * k
    return c_val


def get_clock(s1, c_loc):
    Hours = get_c_val(s1, c_loc, 'Hour')
    Minutes = get_c_val(s1, c_loc, 'Minute')
    Seconds = get_c_val(s1, c_loc, 'Second')
    Milliseconds = get_c_val(s1, c_loc, 'Millisecond')
    return Hours, Minutes, Seconds, Milliseconds


def set_team_score(s1, s_loc, team, score, x):
    # takes the string arg x and puts each of it's members into correct digit in the scoreboard data structure s1
    # this is for team and score thus x should never be more than 3 in len
    # s_loc provides the key:value pair of units:digit so that the placement is correct
    # keep in mind that the string must have the correct no. of arguments...an enhancement will be to
    # make it that only the first n of x will be used based on there being n "unit" keys
    x1 = to_space_val(x)
    leds = get_active_leds(s1)
    s_sc = s_loc[team][score]
    if len(x) > 2:
        if 100 in s_sc:
            leds[s_sc[100]]['val'] = int(x1[0])
        if 10 in s_sc:
            leds[s_sc[10]]['val'] = int(x1[1])
        if 1 in s_sc:
            leds[s_sc[1]]['val'] = int(x1[2])
    else:
        if 10 in s_sc:
            leds[s_sc[10]]['val'] = int(x1[0])
        if 1 in s_sc:
            leds[s_sc[1]]['val'] = int(x1[1])


def set_all_scores(s1, s_loc, x):
    # takes the string arg x and puts each of it's members into correct digit in the scoreboard data structure s1
    # s_loc provides the key:value pair of units:digit so that the placement is correct
    set_team_score(s1, s_loc, 'Home', 'Score', x[0:3])
    set_team_score(s1, s_loc, 'Home', 'Behinds', x[3:5])
    set_team_score(s1, s_loc, 'Home', 'Total', x[5:8])
    set_team_score(s1, s_loc, 'Away', 'Score', x[8:11])
    set_team_score(s1, s_loc, 'Away', 'Behinds', x[11:13])
    set_team_score(s1, s_loc, 'Away', 'Total', x[13:])


def to_spaces( x_str ):
    return (x_str.lstrip('0')).rjust(len(x_str),' ')

def to_space_val( x_num_list ):
    val_found = False
    x1 = []
    for i,val in enumerate(x_num_list):
        if int(val) == 0 and not val_found:
            x1.append(32)
        else:
            val_found = True
            x1.append(int(val))
    if not val_found :
        x1[len(x1)-1] = 0
    return ( x1 )

def set_clock_group(s1, c_loc, group, x):
    leds = get_active_leds(s1)
    c_sc = c_loc[group]
    if group == 'Hour':
        x1 = to_space_val(x)
        leds[c_sc[10]]['val'] = int(x1[0])
    else:
        leds[c_sc[10]]['val'] = int(x[0])
    leds[c_sc[1]]['val'] = int(x[1])

def set_clock_new(s1, x):
    clk_leds = get_active_clock_leds(s1)
    x1 = to_space_val(x[0:2])
    hrs_leds = {k: v for k, v in clk_leds.items() if is_group(v, 'Hour')}
    for k, v in hrs_leds.items():
        if v['units'] == 10 :
            v['val'] = int(x1[0])
        if v['units'] == 1 :
            v['val'] = int(x1[1])
   #     scoreboard.log_it(True,f"{k} : {v['units']} {v['val']} x is: {x} x1 is: {x1}")
    mins_leds = {k: v for k, v in clk_leds.items() if is_group(v, 'Minute')}
    for k, v in mins_leds.items():
        if v['units'] == 10 :
            v['val'] = int(x[2])
        if v['units'] == 1 :
            v['val'] = int(x[3])
   #     scoreboard.log_it(True,f"{k} : {v['units']} {v['val']}")
    secs_leds = {k: v for k, v in clk_leds.items() if is_group(v, 'Second')}
    for k, v in secs_leds.items():
        if v['units'] == 10 :
            v['val'] = int(x[4])
        if v['units'] == 1 :
            v['val'] = int(x[5])
   #     scoreboard.log_it(True,f"{k} : {v['units']} {v['val']}")
    milli_leds = {k: v for k, v in clk_leds.items() if is_group(v, 'Millisecond')}
    for k, v in milli_leds.items():
        if v['units'] == 10 and len(x) > 7 :
            v['val'] = int(x[6])
        if v['units'] == 1 and len(x) > 7 :
            v['val'] = int(x[7])
  #      scoreboard.log_it(True,f"{k} : {v['units']} {v['val']}")

def set_clock(s1, c_loc, x):
    # takes the string arg x and puts each of it's members into correct clock digit
    # in the scoreboard data structure s1
    # this is for all digits of clock
    # thus x should always be at least 6 in len
    # and x should never be more than 8 in len
    # c_loc provides the key:value pair of units:digit so that the placement is correct

    set_clock_group(s1, c_loc, 'Hour', x[0:2])
    set_clock_group(s1, c_loc, 'Minute', x[2:4])
    set_clock_group(s1, c_loc, 'Second', x[4:6])
    if ( len(x) > 7) : #only do milliseconds if the string includes them
        set_clock_group(s1, c_loc, 'Millisecond', x[6:])

def set_quarter(s1, q_loc, val):
    leds = get_leds(s1)
    if 1 in q_loc:
        qtr_led = q_loc[1]
        leds[qtr_led]['val'] = val

def sort_vals(ports):  # return a list which is the values from each digit for this port
    # the returned values are sorted in port order ie if the value of a digit
    # should be 9 and that digits position in the port is 1 then the first value
    # in the list will be 9
    vals = {}
    for k_port, v_port in ports.items():
        vals[k_port] = ()
        for i, v in sorted(v_port.items()):
            #			print(i,v)
            vals[k_port]=vals[k_port]+(v,)
    #	print(vals)
    return vals


# build the spi array based on the spi numbering in the scoreboard data dictionary
# the function returns a list that contains arrays of each of the ports
# the numeric value stored against each digit
# in the correct order as described in the 'spi' value for each of the ports
# it also returns a list which is either 1 or 0 for each digit based on whether the dot
# should be displayed for this digit

def get_spi_vals(s1):
    s_spi = get_spi(s1)
    s_spi['ports'] = {}
    s_spi['port_vals'] = {}
    s_spi['port_dots'] = {}
    leds = get_physical_leds(s1)


    for k, v in leds.items():
        if v['spi_port'] not in s_spi['ports']:
            s_spi['ports'][v['spi_port']] = {}
            s_spi['port_vals'][v['spi_port']] = {}
            s_spi['port_dots'][v['spi_port']] = {}
        s_spi['ports'][v['spi_port']][(v['spi'])] = k
        s_spi['port_vals'][v['spi_port']][(v['spi'])] = v['val']
        if v['dot'] == "YES":
            s_spi['port_dots'][v['spi_port']][(v['spi'])] = v['dot_state']
        else:
            s_spi['port_dots'][v['spi_port']][(v['spi'])] = 0

    spi_vals = sort_vals(s_spi['port_vals'])
    spi_dot_state = sort_vals(s_spi['port_dots'])
  #  scoreboard.log_it(True,s_spi['port_vals'])
  #  scoreboard.log_it(True,spi_vals)
  #  scoreboard.log_it(True,s_spi['port_dots'])
  #  scoreboard.log_it(True,spi_dot_state)
    return spi_vals, spi_dot_state


# build the i2c array based on the i2c channel in the scoreboard data dictionary
# the function returns the array with the numeric value stored against each digit
# order doesn't matter with i2c as each channel corresponds to a digit
def get_i2c_vals(s1):
    leds = get_active_leds(s1)
    s1['i2c']['ports'] = {}
    s1['i2c']['port_vals'] = {}

    for k, v in leds.items():
        if v['i2c_port'] not in s1['i2c']['ports']:
            s1['i2c']['ports'][v['i2c_port']] = {}
            s1['i2c']['port_vals'][v['i2c_port']] = {}
        s1['i2c']['ports'][v['i2c_port']][(v['i2c'])] = k
        s1['i2c']['port_vals'][v['i2c_port']][(v['i2c'])] = v['val']
    i2c_vals = sort_vals(s1['i2c']['port_vals'])
    return i2c_vals


def get_ziku_row(ziku, ziku_num, ziku_segs, dot):
    d1 = []
    for i in ziku[ziku_num: ziku_num + ziku_segs]:
        d1.append(i + dot)
    return d1

# create the hardware string that can be sent to each port
# currently both a ziku dict 'port_ziku' and a string dict 'port_hw_str' are built
# entries are built for every port
# at the moment there is no purpose for the ziku dict
# the string is built by iterating through the spi_vals and dot_state dictionaries
# the spi_vals values are a list
# which should be in the correct order for each port and represents the value to be displayed
# at each digit/char
# the dot_state values are a corresponding list and represents high or low for the dot
# attached to each digit/char

def convert_spi_vals(s1, spi_vals, dot_state):
    port = s1['spi']['port_vals']
    # set dictionaries to null
    s1['spi']['port_ziku'] = {}
    s1['spi']['port_hw_str'] = {}
    #iterate through each port
    for (k, v),(k_dots, v_dots) in zip(spi_vals.items(),dot_state.items()):
        ziku = get_ziku(s1, k)
        ziku_segs = get_ziku_segs(s1, k)
        dot_val = get_dot_val(s1, k)
        spistr = "" #set the hardware string to null
        ba = bytearray() #set the byte array to null
        if k not in s1['spi']['port_ziku']:
            s1['spi']['port_ziku'][k] = () #create the key for the port if not already there
            s1['spi']['port_hw_str'][k] = {}
 #       print(f'Port: {k} Value: {v}')
        #iterate through the values
        for i, i_dots in zip(v, v_dots):
            #find the line in the ziku array that matches the value
            if int(i) != 32 :       #32 indicates a blank
                ziku_num = int(i) * ziku_segs
                z1 = list(ziku[ziku_num: ziku_num + ziku_segs])  #store the line values in z1
            else :
                z1 = [0] * ziku_segs
            # the dot is triggered by ANY of the higher bits 5-8 of the 1st byte so
            # OR ing the first byte with 240 (the value set in dot_val) should do the trick

            this_dot = dot_val * i_dots
            z1[0] = z1[0] | this_dot
            s1['spi']['port_ziku'][k] = s1['spi']['port_ziku'][k] + tuple(z1)
            #add this set of values into the byte array
            ba = ba + bytearray(z1)

            by = bytes(ba) #convert to a sequence of single bytes
            spistr = "".join(str(by)) #convert to a string we can send

        s1['spi']['port_hw_str'][k] = spistr #save the complete string for the port in the dict
  #      scoreboard.log_it(True, spistr)
  #      scoreboard.log_it(True, s1['spi']['port_ziku'][k])
    return


def create_spi_hw(s1):
    spi_vals, dot_state = get_spi_vals(s1)
#    print(f'Spi Values:{ spi_vals}' )
    convert_spi_vals(s1, spi_vals, dot_state)

