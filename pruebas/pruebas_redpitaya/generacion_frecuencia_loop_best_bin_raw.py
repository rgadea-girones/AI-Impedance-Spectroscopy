import sys
import redpitaya_scpi_old as scpi
import numpy as np
from time import perf_counter as pc
from time import sleep
from struct import *
from scipy.fft import fft, fftfreq, fftshift
import matplotlib.pyplot as plt
t0=pc()
rp_s = scpi.scpi(sys.argv[1])

# superparametros
wave_form = 'sine'
frecuencia_min = 1
frecuencia_max=6
puntos_decada=30


numero_valores=(frecuencia_max-frecuencia_min)*puntos_decada
#frecuencias =np.geomspace(frecuencia_min,frecuencia_max,numero_valores)
frecuencias =np.logspace(frecuencia_min,frecuencia_max,puntos_decada*(frecuencia_max-frecuencia_min),base=10)

fm=125000000
numero_pulsos=5
ciclos=3
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

# parametros de la adquisicion
rp_s.tx_txt('SOUR2:BURS:STAT?')
veamosburst= rp_s.rx_txt() 
rp_s.tx_txt('SOUR2:BURS:NCYC?')
veamosCICLOS= rp_s.rx_txt() 

# EMPEZAMOS CON LA ADQUISION


#Enable output
iteracion=1
super_buffer=[]
super_buffer2=[]
Z=np.zeros(numero_valores)
PHASE=np.zeros(numero_valores)
rp_s.tx_txt('ACQ:DATA:FORMAT ASCII') #NO HACE NADA PORQUE SE RESETEA

rp_s.tx_txt('ACQ:TRIG:LEV 125mV') #NO HACE NADA PORQUE SE RESETEA
rp_s.tx_txt('ACQ:TRIG:DLY 8000') #NO HACE NADA PORQUE SE RESETEA
configuracion=0
adquisicion=0
postprocesamiento=0
espera_trigger=0
lupa=0
for freq in (frecuencias):
    t1=pc()
    rp_s.tx_txt('GEN:RST')
    rp_s.tx_txt('ACQ:RST')
    rp_s.tx_txt('ACQ:DATA:FORMAT BIN')
    rp_s.tx_txt('ACQ:DATA:UNITS RAW')
    rp_s.tx_txt('SOUR1:BURS:STAT BURST') # % Set burst mode to ON
    rp_s.tx_txt('SOUR1:BURS:NCYC '+ str(numero_pulsos)) # Set 10 pulses of sine wave
 
    rp_s.tx_txt('SOUR1:FUNC ' + str(wave_form).upper())
    rp_s.tx_txt('SOUR1:VOLT ' + str(ampl))
    rp_s.tx_txt('SOUR1:FREQ:FIX ' + str(freq))
    #rp_s.tx_txt('SOUR1:TRIG:SOUR INT')
    #rp_s.tx_txt('SOUR1:TRIG:IMM')

# #esto habrá que borrarlo
#     rp_s.tx_txt('SOUR2:FUNC ' + str(wave_form).upper())
#     rp_s.tx_txt('SOUR2:VOLT ' + str(ampl2[iteracion-1]))
#     rp_s.tx_txt('SOUR2:FREQ:FIX ' + str(freq))
#     rp_s.tx_txt('SOUR2:BURS:STAT BURST') # % Set burst mode to ON
#     rp_s.tx_txt('SOUR2:BURS:NCYC 10') # Set 10 pulses of sine wave     
#     rp_s.tx_txt('SOUR2:PHAS ' + str(phases[iteracion-1]))    

    # rp_s.tx_txt('ACQ:DEC 8')
    rp_s.tx_txt('ACQ:DEC ' + str(decimation[iteracion-1]))
    # rp_s.tx_txt('ACQ:DEC?')
    # veamosdecimation=rp_s.rx_txt()

    rp_s.tx_txt('ACQ:START')
    rp_s.tx_txt('ACQ:TRIG CH1_PE')

    rp_s.tx_txt('OUTPUT:STATE ON')  #cuidado con cambiar esto
    t2=pc()
# ESPERAMOS EL TRIGGER
    # sleep(1)
    while freq<100:
        rp_s.tx_txt('ACQ:TRIG:STAT?')
        if rp_s.rx_txt() == 'TD':
            break
    t2t=pc()

    #print (iteracion)
    #print(freq)
    sleep(0.1)
    rp_s.tx_txt('ACQ:TPOS?')
    veamos= rp_s.rx_txt()
    posicion_trigger=int(veamos)
    # print('%d: posicion trigger=%d'%(iteracion,posicion_trigger))
    #rp_s.tx_txt('ACQ:BUF:SIZE?')
    #veamos2= rp_s.rx_txt()
    #rp_s.tx_txt('ACQ:DEC?')
    #veamos3= rp_s.rx_txt()    

 
    #if iteracion==6:
    #    break


    # offset=fm*ciclos/freq # un pulso
    posicion_trigger=int(veamos)
    # length=fm*(numero_pulsos-ciclos)/freq
    length=fm*(ciclos)/(freq*decimation[iteracion-1])
    #print('length:',length)    
    # length=int(veamos2) -posicion_trigger
    # LEEMOS Y REPRESENTAMOS 1
    # rp_s.tx_txt('ACQ:SOUR1:DATA?')

    rp_s.tx_txt('ACQ:SOUR1:DATA:STA:N? ' + str(posicion_trigger)+','+ str(length))
    # sleep(2)
    t3=pc()

# The first thing it sends is always a #
    buf = rp_s._socket.recv(1)
    #print(buf.decode('utf-8'))

# The second thing it sends is the number of digits in the byte count. 
    buf = rp_s._socket.recv(1)
    digits_in_byte_count = int(buf)
    

# The third thing it sends is the byte count
    buf = rp_s._socket.recv(digits_in_byte_count)
    #print(buf.decode('utf-8'))
    byte_count = int(buf)
    number_shorts=int(byte_count/2)

# Now we're ready read! 

    buf = []
    while len(buf) != byte_count:
        buf.append(rp_s._socket.recv(1))
    #print(len(buf))

    idea=b''.join(buf)
    indice=0
    dt = np.dtype('short')
    # dt = np.dtype('float')    
    my_array=np.zeros(number_shorts,dtype=dt)
    for st in iter_unpack('>h', idea):
        #print(st)
        my_array[indice]=st[0]
        #float(st[0])/(2^15-1)
        indice=indice+1
    my_list = my_array.tolist()
    t4=pc()


    # my_array = np.asarray(buff)
    super_buffer.append(my_list)
    super_buffer_flat=sum(super_buffer, [])

    yf = fft(my_array)
    t5=pc()

    # N=my_array.shape[0]
    # T=1/fm
    # idea=N//2
    # xf = fftfreq(N, T)[:N//2]
    # plot1=plt.figure(2*(iteracion-1)+1)
    # plt.plot(xf, 2.0/N * np.abs(yf[0:N//2]))
    # plt.xlabel('Frecuencia')

    # LEEMOS Y REPRESENTAMOS2
    rp_s.tx_txt('ACQ:SOUR2:DATA:STA:N? ' + str(posicion_trigger)+','+ str(length))
    t6=pc()

# The first thing it sends is always a #


    buf = rp_s._socket.recv(1)
    #print(buf.decode('utf-8'))

# The second thing it sends is the number of digits in the byte count. 
    buf = rp_s._socket.recv(1)
    digits_in_byte_count = int(buf)
    

# The third thing it sends is the byte count
    buf = rp_s._socket.recv(digits_in_byte_count)
    #print(buf.decode('utf-8'))
    byte_count = int(buf)
    number_shorts=int(byte_count/2)
# Now we're ready read! 
    buf = []
    while len(buf) != byte_count:
        buf.append(rp_s._socket.recv(1))
    # print(len(buf))

    idea=b''.join(buf)
    indice=0
    my_array2=np.zeros(number_shorts,dtype=dt)
    for st in iter_unpack('>h', idea):
        #print(st)
        my_array2[indice]=st[0]
        # float(st[0])/(2^15-1)
        indice=indice+1
    my_list = my_array2.tolist()
    t7=pc()


    # my_array = np.asarray(buff)
    super_buffer2.append(my_list)
    super_buffer_flat2=sum(super_buffer2, [])
    yf2 = fft(my_array2)
    dif=my_array-my_array2
    yf3=fft(dif)

    indice1=np.argmax(np.abs(yf))
    indice2=np.argmax(np.abs(yf2))
    #indice3=np.argmax(np.abs(yf3))

    #Z[iteracion-1]=np.max(np.abs(yf))/np.max(np.abs(yf2))

    Z[iteracion-1]=np.max(np.abs(yf3))*1000/np.max(np.abs(yf2))    #tercera opcion  con Rref=1K
    PHASE[iteracion-1]=((np.angle(yf2[indice2]/yf[indice1])))*180/np.pi   
   

    t8=pc()
    # N2=my_array2.shape[0]
    # T=1/fm
    # idea=N//2
    # xf2 = fftfreq(N2, T)[:N2//2]
    # plot2=plt.figure(2*(iteracion-1)+2)
    # plt.plot(xf2, 2.0/N * np.abs(yf2[0:N2//2]))
    # plt.plot(xf2, p[0:N2//2])    
    # plt.xlabel('Frecuencia')
    # plt.grid()




    iteracion=iteracion+1
    rp_s.tx_txt('OUTPUT:STATE OFF')
    rp_s.tx_txt('ACQ:STOP')
    t9=pc()
    postprocesamiento=postprocesamiento+(t5-t4)+(t8-t7)
    configuracion=configuracion+(t2-t1)+(t9-t8)+(t6-t5)+(t3-t2t)
    adquisicion=adquisicion+(t4-t3)+(t7-t6)  
    espera_trigger=espera_trigger+ (t2t-t2)  
    lupa=lupa+(t3-t2t)


t10=pc()
plotfinal1=plt.figure(2*(iteracion-1)+1)
plt.plot(super_buffer_flat)
plt.plot(super_buffer_flat2)
plt.ylabel('Voltage')

plotfinal2=plt.figure(2*(iteracion-1)+2)
plt.plot(super_buffer_flat2)
plt.ylabel('Current')

plotZ=plt.figure(2*iteracion+1)
plt.semilogx(frecuencias, Z,'o')
#plt.semilogx(frecuencias,amplreference,'o')
plt.grid(True, color='0.7', linestyle='-', which='both', axis='both')
plt.ylabel('Z')

plotPHASE=plt.figure(2*iteracion+2)
plt.semilogx(frecuencias,PHASE, 'o')
#plt.semilogx(frecuencias,phases,'o')
plt.grid(True, color='0.7', linestyle='-', which='both', axis='both')
plt.ylabel('PHASE')

t11=pc()
representacion=t11-t10
total=t11-t0
# view rawacquire_trigger_posedge.py
print('t3-t2t:',lupa)
print('espera_trigger:',espera_trigger)
print('configuracion:',configuracion)
print('adquisicion:',adquisicion)
print('postprocesamiento:',postprocesamiento)
print ('representación:',representacion)
print ('total:',total)
print ('tiempo por punto:', total/((frecuencia_max-frecuencia_min)*puntos_decada))
plt.show()
# view rawacquire_trigger_posedge.py

