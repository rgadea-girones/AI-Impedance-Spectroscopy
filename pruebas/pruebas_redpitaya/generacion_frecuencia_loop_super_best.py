import sys
import redpitaya_scpi_old as scpi
import numpy as np
from time import perf_counter as pc
from time import sleep
from scipy.fft import fft, fftfreq, fftshift
from scipy.interpolate import interp1d
import matplotlib.pyplot as plt
from plumbum import SshMachine
from plumbum.machines.paramiko_machine import ParamikoMachine


t0=pc()
rp_s = scpi.scpi(sys.argv[1])

# superparametros
wave_form = 'sine'
frecuencia_min = 1
frecuencia_max=6
puntos_decada=10


numero_valores=(frecuencia_max-frecuencia_min)*puntos_decada
#frecuencias =np.geomspace(frecuencia_min,frecuencia_max,numero_valores)
frecuencias_TOTAL =np.logspace(frecuencia_min,frecuencia_max,256,base=10)

frecuencias=frecuencias_TOTAL[frecuencias_TOTAL>40]

shunt=[10.0,100.0,1000.0,10000.0,100000.0,1300000.0]
fm=125000000
numero_pulsos=10
ciclos=5
ampl = 1

amplreference=np.linspace(10,1,numero_valores)
ampl2=1/amplreference
phases=np.linspace(180,0,numero_valores)
#decimation=np.logspace(numero_valores-1, 0, num=numero_valores, base=2.0)
#decimation=30*[1024]+30*[64]+40*[1]
decimation=1*puntos_decada*[8192]+2*puntos_decada*[1024]+1*puntos_decada*[64]+2*puntos_decada*[1]




# rp_s.tx_txt('SOUR1:BURS:NOR 2') # Set 2 repeticiones


# there is an option to select coupling when using SIGNALlab 250-12
# rp_s.tx_txt('ACQ:SOUR1:COUP AC') # enables AC coupling on channel 1

# by default LOW level gain is selected
# rp_s.tx_txt('ACQ:SOUR1:GAIN LV') # user can switch gain using this command

# configuramos la FPGA
rp_s.tx_txt('RP:FPGABITREAM_DSD 0.94')

#configuramos el shunt
R_shunt_k=2
veamos = ParamikoMachine('158.42.32.24', user = "root", password="root")
veamos.env["LD_LIBRARY_PATH"]="/opt/redpitaya/lib"
veamos.cwd.chdir("/opt/redpitaya/bin")
comando="./i2c_shunt " + str(R_shunt_k)
# print (comando)
r_back = veamos[comando]
r_back()
muestras=225
decimation=1

# frecuencias=frecuencias[:-decimation:decimation]

# si vemos que se bloquea descomentar
rp_s.tx_txt('SOUR1:VOLT 1')
rp_s.tx_txt('SOUR1:VOLT:OFFS 0.00') # esto lo utilizo para cambiar el offset de canal b
rp_s.tx_txt('SOUR2:VOLT:OFFS 0.016') # esto lo utilizo para cambiar el offset de canal b
rp_s.tx_txt('SOUR1:BURS:NCYC 1')  # solo funciona si led3 esta activado, numero de ciclos por frecuencia
rp_s.tx_txt('SOUR1:BURS:NOR ' +str(muestras)) # solo funciona si led3 esta activado, numero de frecuencias
# # rp_s.tx_txt('SOUR2:BURS:INT:PER 30') # solo funciona si led3 esta activado, ancho detector
rp_s.tx_txt('SOUR2:BURS:NOR ' +str(decimation))
rp_s.tx_txt('SOUR2:BURS:NCYC 255')  #controlo el numero de ciclos de ancho del deteccor de cero

rp_s.tx_txt('DIG:PIN LED'+str(1)+','+str(0))  # 1->state2  0->state1
rp_s.tx_txt('DIG:PIN LED'+str(2)+','+str(0))  # desbloqueo finalizacion state1, tambien genera inicio
rp_s.tx_txt('DIG:PIN LED'+str(3)+','+str(1))  #activacion del led3


t1=pc()
rp_s.tx_txt('CHIRP ON')

# rp_s.tx_txt('RP:FPGABITREAM_DSD 0.94')
while 1 :
#    rp_s.tx_txt('FIN:RAF:STAT? 1')
    rp_s.tx_txt('DIG:PIN? DIO'+str(7)+'_N')
    state = rp_s.rx_txt()
    if state == '1':
        break
#    # print(rp_s.rx_txt())
# rp_s.tx_txt('DIG:PIN? DIO'+str(7)+'_N')
# state = rp_s.rx_txt()
print(state)
# EMPEZAMOS CON LA ADQUISION

rp_s.tx_txt('CHIRP OFF')
rp_s.tx_txt('ACQ:RESULT1:DATA?')
t3=pc()

buff_string = rp_s.rx_txt()
buff_string = buff_string.strip('{}\n\r').replace("  ", "").split(',')
buff = list(map(float, buff_string))
t4=pc()
my_array = np.asarray(buff)
my_array =my_array[:-decimation:decimation]
# super_buffer.append(buff)
# super_buffer_flat=sum(super_buffer, [])
rp_s.tx_txt('ACQ:RESULT2:DATA?')
buff_string2 = rp_s.rx_txt()
buff_string2 = buff_string2.strip('{}\n\r').replace("  ", "").split(',')
buff2 = list(map(float, buff_string2))
my_array2 = np.asarray(buff2)
my_array2 =my_array2[:-decimation:decimation]
muestras=round(muestras/decimation)
t5=pc()
print('t5-t1:',t5-t1)
#Enable output
iteracion=1
# ZA=interp1d(frecuencias[0:muestras],my_array[0:muestras])
# ZB=interp1d(frecuencias,my_array[256: 256+225])
# Z=(ZA(frecuencias))*shunt[R_shunt_k]/1000
Z=my_array[0:muestras]*shunt[R_shunt_k]/1000
# en principio el calculo en verilog es suponiendo una resistencia de 1k. Con esto lo ajusto a la resistencia de shunt exacta


# PhaseA=interp1d(frecuencias[0:muestras],my_array2[0:muestras])
# Phase_check=PhaseA(frecuencias)*frecuencias*360/125e6
# Phase_radianes=PhaseA(frecuencias)*frecuencias*2*np.pi/125e6
Phase_check=-my_array2[0:muestras]*frecuencias[0:muestras]*360/125e6
Phase_radianes=-my_array2[0:muestras]*frecuencias[0:muestras]*2*np.pi/125e6
Phase_Z=np.zeros(muestras)
PHASE=np.zeros(muestras)
for fases in range(len(Phase_check)):
    if (Phase_check[fases]<=-180):
        Phase_Z[fases]=Phase_radianes[fases]*(180/np.pi)+360
    else:
        if (Phase_check[fases] >=180):
            Phase_Z[fases]=Phase_radianes[fases]*(180/np.pi)-360
        else:
            Phase_Z[fases]=Phase_check[fases]
    if (Phase_Z[fases]<=-90): 
        PHASE[fases]=Phase_Z[fases]+180
    else:    
        if (Phase_Z[fases]>=90):
            PHASE[fases]=Phase_Z[fases]-180
        else:
            PHASE[fases]=Phase_Z[fases]  
# PHASE=my_array[256: 256+225]*frecuencias*360/125e6
# PHASE= Phase_check

PHASE=Phase_Z     
# PHASE=my_array2[0:225]*shunt[R_shunt_k]/1000
plotZ=plt.figure(2*iteracion+1)
plt.semilogx(frecuencias[0:muestras], Z,'o')
#plt.semilogx(frecuencias,amplreference,'o')
plt.grid(True, color='0.7', linestyle='-', which='both', axis='both')
plt.ylabel('Z')

plotPHASE=plt.figure(2*iteracion+2)
plt.semilogx(frecuencias[0:muestras],PHASE, 'o')
#plt.semilogx(frecuencias,phases,'o')
plt.grid(True, color='0.7', linestyle='-', which='both', axis='both')
plt.ylabel('PHASE')



plt.show()
# view rawacquire_trigger_posedge.py

