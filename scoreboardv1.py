#scoreboard
#AusSport user defined functions

import os
import json
import datetime
from time import time, ctime, sleep
import pigpio as GPIO
import s_data1 as s_data
from array import array
#import pygame
#from pygame.mixer import Sound, get_init, pre_init

# class Note(Sound):
#
#     def __init__(self, frequency, volume=.9):
#         self.frequency = frequency
#         Sound.__init__(self, self.build_samples())
#         self.set_volume(volume)
#
#     def build_samples(self):
#         period = int(round(get_init()[0] / self.frequency))
#         samples = array("h", [0] * period)
#         amplitude = 2 ** (abs(get_init()[1]) - 1) - 1
#         for time in range(period):
#              if time < period / 2:
#                 samples[time] = amplitude
#
#         print( samples)
#         return samples




def log_it(logging, str1):
    if logging:
        with open('scorelog.txt','a') as s_log:
            s_log.write("T: {0}: {1}".format(datetime.datetime.now(),str1))
            s_log.write('\r\n')

def check_int(s):
    s = str(s)
    if s[0] in ('-', '+'):
        return s[1:].isdigit()
    return s.isdigit()  

def check_allint(str_to_check):
    all_int = 1
    if len(str_to_check) > 1:		#must have some integers to check or just return true
        #first char is always non-int so skipping it
        for i in range(1,len(str_to_check)-1):
            if check_int(str_to_check[i]) == False:
            #	print('Failed int check: {0}'.format(str_to_check[i]))
                all_int = 0
                break
            else:
                all_int = 1

    return all_int



def get_ziku_row(Ziku, ziku_num, ziku_segs, dot):
    d1 = []
    for i in Ziku[ziku_num: ziku_num + ziku_segs]:
        d1.append(i + dot)
    return d1


def set_data_spi(p1, d_vals,vals_strt,vals_end,d_port,port_start, dot):
    spistr = ""
    ba = bytearray()
    p_cnt = port_start
    for i in d_vals[vals_strt:vals_end]:

        ziku_num = int(i) * ziku_segs
        if len(d_port) > p_cnt:
            d_port[p_cnt] = get_ziku_row(Ziku, ziku_num, ziku_segs, dot)
            #[Ziku[ziku_num], Ziku[ziku_num+1], Ziku[ziku_num+2], Ziku[ziku_num+3]]
        else:
            d_port.append(get_ziku_row(Ziku, ziku_num, ziku_segs, dot))
            #[Ziku[ziku_num], Ziku[ziku_num+1], Ziku[ziku_num+2], Ziku[ziku_num+3]])
        ba = ba + bytearray(d_port[p_cnt])
        p_cnt = p_cnt + 1
    by = bytes(ba)
    spistr = "".join(str(by))
    return spistr

def set_chars_spi(p1, d_vals,vals_strt,vals_end,d_port,port_start):
    spistr = ""
    ba = bytearray()
    p_cnt = port_start
    for i in d_vals[vals_strt:vals_end]:

        bmp_num = int(i) * 16
        if len(d_port) > p_cnt:
            d_port[p_cnt] = [Bmp[bmp_num], Bmp[bmp_num+1], Bmp[bmp_num+2], Bmp[bmp_num+3]]
        else:
            d_port.append([Bmp[bmp_num], Bmp[bmp_num+1], Bmp[bmp_num+2], Bmp[bmp_num+3]])
        ba = ba + bytearray(d_port[p_cnt])
        p_cnt = p_cnt + 1
    by = bytes(ba)
    spistr = "".join(str(by))
    return spistr

#routine provided by Joan from pigpio to overcome dual data SPI
def spix2_write(p1, latch, d1, d2):
   SPI_CLK = 11
   SPI_CS =  latch
   SPI_D1 = 10      #need to fix up the magic numbers in here
                    #put them into the json config file
   SPI_D2 = 24 
   p1.set_mode(SPI_CLK, GPIO.OUTPUT)
   p1.set_mode(SPI_CS, GPIO.OUTPUT)
   p1.set_mode(SPI_D1, GPIO.OUTPUT)
   p1.set_mode(SPI_D2, GPIO.OUTPUT)
   wf=[]
   if len(d1) > len(d2):
      bytes = len(d1)
      d2 += (0,)*(bytes-len(d2))
   elif len(d1) < len(d2):
      bytes = len(d2)
      d1 += (0,)*(bytes-len(d1))
   else:
      bytes = len(d1)


   for i in range(bytes):
      for b in reversed(range(8)):
         d_on = 0
         d_off = 0

         if d1[i] & (1<<b):
            d_on |= (1<<SPI_D1)
         else:
            d_off |= (1<<SPI_D1)

         if d2[i] & (1<<b):
            d_on |= (1<<SPI_D2)
         else:
            d_off |= (1<<SPI_D2)
 #        print(f"d_on: {d_on}")
  #       print(f"d_off: {d_off}")
         wf.append(GPIO.pulse(d_on, d_off, 5))
         d_on |= (1 << SPI_CLK)
         wf.append(GPIO.pulse(d_on, d_off, 5))
         wf.append(GPIO.pulse(0, 1<<SPI_CLK, 0))
   wf.append(GPIO.pulse(0, 0, 5)) # delay before deassert CS
   wf.append(GPIO.pulse(1<<SPI_CS, 0, 5)) # assert CS

   wf.append(GPIO.pulse(0, 1<<SPI_CS, 0)) # deassert CS

   p1.wave_add_generic(wf)
   wid = p1.wave_create()

   if wid >= 0:
      p1.wave_send_once(wid)
      p1.wave_delete(wid)

def send_digits_spi(p1, freq, chan, spi_flag, latch, b_str, bmp_str, bmp_flag):
#NB Chip Enable lines on SPI are NOT used
#the latching is done via whatever GPIO is in latch
#this way flickering is eliminated from the display
#if the bitmap flag is on then there is secondary data to be sent
#have to use the function spix2_write

    if bmp_flag:
        #print( "bmp:")
        spix2_write(p1, latch, b_str, bmp_str)
    else:
        h1 = p1.spi_open(chan, freq, spi_flag)
        #if latch == 27:
            #log_it(True, b_str)
        p1.spi_write(h1, b_str)
        p1.spi_close(h1)
        p1.write(latch,1)
        p1.write(latch,0)

def send_i2c_digit_data(p1, s1):
    i2c_settings = s1['i2c']['port_settings']
    offset = s1['i2c']['offset']
    for k,v in i2c_settings.items():
        this_port = s_data.get_i2c_port(s1,k)
        #send all the values for this port
        for k, v in this_port.items():
            val = int(v['val'])
            p_val = v['i2c_port']
            chan = i2c_settings[p_val]['chan']
            addr = v['i2c'] + offset
            if val == 32: #this means a blank digit
                valreg = s1['i2c']['col_reg']
                val = 0 #by setting colour to BLACK it should go off
            else: #this means it is a valid value
                valreg = s1['i2c']['val_reg']

    #		print(chan,addr,valreg,val)
    #		sleep(.1)
            send_data_i2c(p1, chan, addr, valreg, val)


def send_i2c_colour_data(p1, s1):
    i2c_settings = s1['i2c']['port_settings']
    offset = s1['i2c']['offset']
    colreg = s1['i2c']['col_reg']
    for k,v in i2c_settings.items():
        this_port = s_data.get_i2c_port(s1,k)
        #send all the values for this port
        for k, v in this_port.items():
            p_val = v['i2c_port']
            chan = i2c_settings[p_val]['chan']
            addr = v['i2c'] + offset
            colour = v['colour']
            val = s1['i2c']['colours'][colour]

            send_data_i2c(p1,chan, addr, colreg, val)


def send_i2c_bright_data(p1, s1):
    i2c_settings = s1['i2c']['port_settings']
    offset = int(s1['i2c']['offset'])
    brightreg = int(s1['i2c']['bright_reg'])
    bright = s1['board']['brightness']
    for k,v in i2c_settings.items():
        this_port = s_data.get_i2c_port(s1,k)
        #send all the values for this port
        for k, v in this_port.items():
            p_val = v['i2c_port']
            chan = i2c_settings[p_val]['chan']
            addr = v['i2c'] + offset

            send_data_i2c(p1, chan, addr, brightreg, bright)


def send_data_i2c(p1, chan1, addr1, reg1, val1):

    h1 = p1.i2c_open(chan1, addr1)

    GPIO.exceptions = False
    try:
        p1.i2c_write_byte_data(h1, reg1, val1)

    except GPIO.error as error:
        print(error)
    GPIO.exceptions = False
    p1.i2c_close(h1)


def sound_siren(p1, siren_time, siren_pin):

    end_siren_time = time() + siren_time
    p1.write(siren_pin, 1)
#	pre_init(44100, -16, 1, 1024)
#	pygame.init()

#	Note(450).play(-1)
#	Note(320).play(-1)
    return end_siren_time
