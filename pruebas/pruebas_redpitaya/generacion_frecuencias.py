import sys
import redpitaya_scpi_old as scpi
import numpy as np
from time import perf_counter as pc
from time import sleep
from scipy.fft import fft, fftfreq
import matplotlib.pyplot as plt

rp_s = scpi.scpi(sys.argv[1])

wave_form = 'sine'
freq = 10
fm=125000000
numero_pulsos=10
ampl = 1

rp_s.tx_txt('GEN:RST')
rp_s.tx_txt('ACQ:RST')

rp_s.tx_txt('SOUR1:FUNC ' + str(wave_form).upper())
rp_s.tx_txt('SOUR1:VOLT ' + str(ampl))

rp_s.tx_txt('SOUR1:FREQ:FIX ' + str(freq))


rp_s.tx_txt('SOUR1:BURS:STAT BURST') # % Set burst mode to ON
rp_s.tx_txt('SOUR1:BURS:NCYC 10') # Set 10 pulses of sine wave
# rp_s.tx_txt('SOUR1:BURS:NOR 2') # Set 2 repeticiones


# there is an option to select coupling when using SIGNALlab 250-12
# rp_s.tx_txt('ACQ:SOUR1:COUP AC') # enables AC coupling on channel 1

# by default LOW level gain is selected
# rp_s.tx_txt('ACQ:SOUR1:GAIN LV') # user can switch gain using this command

# parametros de la adquisicion

rp_s.tx_txt('ACQ:DEC 8192')
rp_s.tx_txt('ACQ:TRIG:LEV 500')
rp_s.tx_txt('ACQ:TRIG:DLY 0')
rp_s.tx_txt('ACQ:GAIN LV')

# EMPEZAMOS CON LA ADQUISION

rp_s.tx_txt('ACQ:START')
rp_s.tx_txt('ACQ:TRIG CH1_PE')
#Enable output
rp_s.tx_txt('OUTPUT1:STATE ON')

# ESPERAMOS EL TRIGGER
while 1:
    rp_s.tx_txt('ACQ:TRIG:STAT?')
    if rp_s.rx_txt() == 'TD':
        break
#sleep(5)
rp_s.tx_txt('ACQ:TPOS?')
veamos= rp_s.rx_txt()

rp_s.tx_txt('ACQ:BUF:SIZE?')
veamos2= rp_s.rx_txt()
ciclos=5
offset=fm*ciclos/freq # un pulso
posicion_trigger=int(veamos)
#length=int(veamos2) -posicion_trigger
length=fm*(ciclos)/(freq*8192)
# length=10000 #fm*(numero_pulsos-ciclos)/freq
# LEEMOS Y REPRESENTAMOS
# rp_s.tx_txt('ACQ:SOUR1:DATA?')
rp_s.tx_txt('ACQ:SOUR1:DATA:STA:N? ' + str(posicion_trigger)+','+ str(length))
buff_string = rp_s.rx_txt()
buff_string = buff_string.strip('{}\n\r').replace("  ", "").split(',')
buff = list(map(float, buff_string))

my_array = np.asarray(buff)
yf = fft(my_array)
N=my_array.shape[0]
T=1/fm
idea=N//2
xf = fftfreq(N, T)[:N//2]
plot1=plt.figure(1)
plt.plot(xf, 2.0/N * np.abs(yf[0:N//2]))
plt.xlabel('Frecuencia')

plt.grid()
plot1=plt.figure(2)
plt.plot(buff)
plt.ylabel('Voltage')

plt.show()
# view rawacquire_trigger_posedge.py

