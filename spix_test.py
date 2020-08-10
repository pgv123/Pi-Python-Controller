#test of spix2_write

import pigpio as GPIO
import scoreboardv1
import time
import Ziku



bmp = getattr(Ziku, "Bmp001")
disply = "AusSport Scoreboards   "
l1 = 0
clear_it = 0
latch = 23
bmp_segs = 8
bmp_upper = ()
bmp_lower = ()


# create local PI GPIO
p1 = GPIO.pi()
pointer = 0
for j in range(100):
   # print(j)

    range_val = 1
    for i in range(range_val):
        bmp_num = ((ord(disply[pointer]) - 32) * 16)     #* bmp_segs  # the value starts at 0x20 or 32
        bmp1 = list(bmp[bmp_num : bmp_num + bmp_segs])  # store all the upper line values in bmp1

        bmp1.reverse()
        bmp2 = list(bmp[bmp_num + bmp_segs : bmp_num + bmp_segs + bmp_segs ])  # store all the lower line values in bmp2
        bmp2.reverse()
        bmp_upper = bmp_upper + tuple(bmp1)
        bmp_lower = bmp_lower + tuple(bmp2)
        scoreboardv1.spix2_write(p1,latch,bmp_upper, bmp_lower)
    time.sleep(0.3)
#    disply = disply[-1:]+disply[:-1]
    bmp_upper = ()
    bmp_lower = ()
    pointer += 1
    if pointer >= len(disply):
       pointer = 0
    