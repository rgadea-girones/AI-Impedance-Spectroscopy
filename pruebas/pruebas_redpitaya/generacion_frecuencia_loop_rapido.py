import sys
import redpitaya_scpi_old as scpi
import numpy as np
from time import perf_counter as pc
from struct import *
from scipy.fft import fft, fftfreq, fftshift
import matplotlib.pyplot as plt
t0=pc()
rp_s = scpi.scpi(sys.argv[1])

wave_form = 'sine'
frecuencia_min = 100
frecuencia_max=4000000
numero_valores=100
frecuencias =np.geomspace(frecuencia_min,frecuencia_max,numero_valores)


fm=125000000
numero_pulsos=10
ampl = 1

amplreference=np.linspace(10,1,numero_valores)
ampl2=1/amplreference
phases=np.linspace(180,0,numero_valores)
#decimation=np.logspace(numero_valores-1, 0, num=numero_valores, base=2.0)
# decimation=[1024,1024,1024,64,8,8,1,1,1,1]
decimation=30*[1024]+30*[64]+40*[1]




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
configuracion=0
adquisicion=0
postprocesamiento=0
espera_trigger=0
rp_s.tx_txt('ACQ:DATA:UNITS VOLTS')

rp_s.tx_txt('ACQ:TRIG:LEV 125mV')
rp_s.tx_txt('ACQ:TRIG:DLY 8000')
for freq in (frecuencias):
    t1=pc()
    rp_s.tx_txt('GEN:RST')
    rp_s.tx_txt('ACQ:RST')
    rp_s.tx_txt('ACQ:DATA:FORMAT BIN')    
    rp_s.tx_txt('SOUR1:BURS:STAT BURST') # % Set burst mode to ON
    rp_s.tx_txt('SOUR1:BURS:NCYC 10') # Set 10 pulses of sine wave
 
    rp_s.tx_txt('SOUR1:FUNC ' + str(wave_form).upper())
    rp_s.tx_txt('SOUR1:VOLT ' + str(ampl))
    rp_s.tx_txt('SOUR1:FREQ:FIX ' + str(freq))

#esto habrá que borrarlo
    rp_s.tx_txt('SOUR2:FUNC ' + str(wave_form).upper())
    rp_s.tx_txt('SOUR2:VOLT ' + str(ampl2[iteracion-1]))
    rp_s.tx_txt('SOUR2:FREQ:FIX ' + str(freq))
    rp_s.tx_txt('SOUR2:BURS:STAT BURST') # % Set burst mode to ON
    rp_s.tx_txt('SOUR2:BURS:NCYC 10') # Set 10 pulses of sine wave     
    rp_s.tx_txt('SOUR2:PHAS ' + str(phases[iteracion-1]))    

    # rp_s.tx_txt('ACQ:DEC 8')
    rp_s.tx_txt('ACQ:DEC ' + str(decimation[iteracion-1]))


    rp_s.tx_txt('ACQ:START')
    rp_s.tx_txt('ACQ:TRIG CH1_PE')
    rp_s.tx_txt('OUTPUT:STATE ON')  #cuidado con cambiar esto




    t2=pc()

# ESPERAMOS EL TRIGGER
    #while 1:
    #    rp_s.tx_txt('ACQ:TRIG:STAT?')
    #    if rp_s.rx_txt() == 'TD':
    #        break
    t2t=pc()
    print (iteracion)
    rp_s.tx_txt('ACQ:TPOS?')
    veamos= rp_s.rx_txt()
    posicion_trigger=int(veamos)
    print('posicion trigger:',veamos)
    rp_s.tx_txt('ACQ:BUF:SIZE?')
    veamos2= rp_s.rx_txt()
    rp_s.tx_txt('ACQ:DEC?')
    veamos3= rp_s.rx_txt()    

 

    ciclos=5
    offset=fm*ciclos/freq # un pulso
    posicion_trigger=int(veamos)
    length=fm*(ciclos)/(freq*decimation[iteracion-1])
    # length=int(veamos2) -posicion_trigger
    # LEEMOS Y REPRESENTAMOS 1
    # rp_s.tx_txt('ACQ:SOUR1:DATA?')
    rp_s.tx_txt('ACQ:SOUR1:DATA:STA:N? ' + str(posicion_trigger)+','+ str(length))
    t3=pc()

# The first thing it sends is always a #
#
# One thing I don't understand here is that even if I do a recv(10), 
# I always get only one answer back. Like somehow we are getting a
# terimination signal in the socket? I don't know enough about sockets. 
# This doesn't work though for the the number of digits. 
# Maybe I need to look in the SCPI server code. 
#
    buf = rp_s._socket.recv(1)
    print(buf.decode('utf-8'))

# The second thing it sends is the number of digits in the byte count. 
    buf = rp_s._socket.recv(1)
    digits_in_byte_count = int(buf)
    

# The third thing it sends is the byte count
    buf = rp_s._socket.recv(digits_in_byte_count)
    #print(buf.decode('utf-8'))
    byte_count = int(buf)

# Now we're ready read! You might thing we would just to a recv(byte_count), but somehow this often 
# results in an incomplete transfer? Maybe related to first point above? 
# The RP code just reads one byte at a time until it's gets all
# it wants? I tried that and it seems to work. But it is not mega-fast? 317 ms, whereas we should be 
# able to get data off much faster than that! It is 65536 bytes = 5 ms at 100 MBit / second. 
# But 317 ms is still at least a lot better than the ASCII read which takes 1.3 seconds!

    buf = []
    while len(buf) != byte_count:
        buf.append(rp_s._socket.recv(1))
    #print(len(buf))

    idea=b''.join(buf)
    indice=0
    # dt = np.dtype('short')
    dt = np.dtype('float')    
    my_array=np.zeros(len(buf),dtype=dt)
    for st in iter_unpack('>f', idea):
        #print(st)
        my_array[indice]=st[0]
        indice=indice+1
    #bufb = []
    #bufb = rp_s.rx_arb()
    #buff_string = rp_s.rx_txt()
    #buff_string = buff_string.strip('{}\n\r').replace("  ", "").split(',')
    #buff = list(map(float, buff_string))
    t4=pc()

    my_list = my_array.tolist()
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
#
# One thing I don't understand here is that even if I do a recv(10), 
# I always get only one answer back. Like somehow we are getting a
# terimination signal in the socket? I don't know enough about sockets. 
# This doesn't work though for the the number of digits. 
# Maybe I need to look in the SCPI server code. 
#
    buf = rp_s._socket.recv(1)
    #print(buf.decode('utf-8'))

# The second thing it sends is the number of digits in the byte count. 
    buf = rp_s._socket.recv(1)
    digits_in_byte_count = int(buf)
    

# The third thing it sends is the byte count
    buf = rp_s._socket.recv(digits_in_byte_count)
    #print(buf.decode('utf-8'))
    byte_count = int(buf)

# Now we're ready read! You might thing we would just to a recv(byte_count), but somehow this often 
# results in an incomplete transfer? Maybe related to first point above? 
# The RP code just reads one byte at a time until it's gets all
# it wants? I tried that and it seems to work. But it is not mega-fast? 317 ms, whereas we should be 
# able to get data off much faster than that! It is 65536 bytes = 5 ms at 100 MBit / second. 
# But 317 ms is still at least a lot better than the ASCII read which takes 1.3 seconds!

    buf = []
    while len(buf) != byte_count:
        buf.append(rp_s._socket.recv(1))
    # print(len(buf))

    idea=b''.join(buf)
    indice=0
    my_array2=np.zeros(len(buf),dtype=dt)
    for st in iter_unpack('>f', idea):
        #print(st)
        my_array2[indice]=st[0]
        indice=indice+1
    #bufb = []
    #bufb = rp_s.rx_arb()
    #buff_string = rp_s.rx_txt()
    #buff_string = buff_string.strip('{}\n\r').replace("  ", "").split(',')
    #buff = list(map(float, buff_string))
    t7=pc()

    my_list = my_array2.tolist()
    # my_array = np.asarray(buff)
    super_buffer2.append(my_list)
    super_buffer_flat2=sum(super_buffer2, [])
    yf2 = fft(my_array2)
    #dif=my_array-my_array2
    #yf3=fft(dif)
    indice1=np.argmax(np.abs(yf))
    indice2=np.argmax(np.abs(yf2))
    #indice3=np.argmax(np.abs(yf3))

    Z[iteracion-1]=np.max(np.abs(yf))/np.max(np.abs(yf2))

    # Y = fftshift(yf2)
    # p=np.angle(Y)
    # p[np.abs(Y) < 1] = 0
    # PHASE[iteracion-1] =np.max(p)*180/np.pi
    # PHASE[iteracion-1]=((np.angle(yf[indice1])-np.angle(yf2[indice2])))*180/np.pi
    # PHASE[iteracion-1]=(np.angle(yf2[indice2])+np.pi/2)*180/np.pi
    PHASE[iteracion-1]=np.abs((np.angle(yf2[indice2]/yf[indice1])))*180/np.pi    

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


t10=pc()
plotfinal1=plt.figure(2*(iteracion-1)+1)
plt.plot(super_buffer_flat)
plt.plot(super_buffer_flat2)
plt.ylabel('Voltage')

plotfinal2=plt.figure(2*(iteracion-1)+2)
plt.plot(super_buffer_flat2)
plt.ylabel('Current')

plotZ=plt.figure(2*iteracion+1)
plt.plot(Z)
plt.plot(amplreference)
plt.ylabel('Z')

plotPHASE=plt.figure(2*iteracion+2)
plt.plot(PHASE)
plt.plot(phases)
plt.ylabel('PHASE')

t11=pc()
representacion=t11-t10
total=t11-t0
# view rawacquire_trigger_posedge.py
print('configuracion:',configuracion)
print('adquisicion:',adquisicion)
print('postprocesamiento:',postprocesamiento)
print ('representación:',representacion)
print ('total:',total)

plt.show()

