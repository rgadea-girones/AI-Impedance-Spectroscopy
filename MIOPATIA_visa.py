import pyvisa as visa
import socket
import io
import numpy as np
from time import perf_counter as pc
from time import sleep
from scipy.fft import fft, fftfreq, fftshift
from scipy.interpolate import interp1d, make_interp_spline
from PyQt5.QtWidgets import QMessageBox
import fit_library as fit
import pandas as pd
from plumbum import SshMachine
from plumbum.machines.paramiko_machine import ParamikoMachine



class VISA(object):
    delimiter = '\r\n'
    def __init__(self, host, shared_data, dataview, timeout=None, port=5000):
        self.sd = shared_data
        #self.tb = txt_browser
        #self.fit_browser = fit_browser
        self.dv = dataview

        # Visa initializationg
        # self.rm = visa.ResourceManager()
        # self.lor = self.rm.list_resources()
        # ("Lista de dispositivos encontrados:") 
        # self.dv.append_plus(str(self.lor)) 

        """Initialize object and open IP connection.
        Host IP should be a string in parentheses, like '192.168.1.100'.
        """
        self.host    = host
        self.port    = port
        self.timeout = timeout

        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            if timeout is not None:
                self._socket.settimeout(timeout)

            self._socket.connect((host, port))
            print('conexion establecida con redpitaya')

        except socket.error as e:
            print('SCPI >> connect({:s}:{:d}) failed: {:s}'.format(host, port, e))

    def __del__(self):
        if self._socket is not None:
            self._socket.close()
        self._socket = None

    def close(self):
        """Close IP connection."""
        self.__del__()

    def rx_txt(self, chunksize = 4096):
        """Receive text string and return it after removing the delimiter."""
        msg = ''
        while 1:
            chunk = self._socket.recv(chunksize + len(self.delimiter)).decode('utf-8') # Receive chunk size of 2^n preferably
            msg += chunk
            if (len(chunk) and chunk[-2:] == self.delimiter):
                break
        return msg[:-2]

    def rx_arb(self):
        numOfBytes = 0
        """ Recieve binary data from scpi server"""
        str=''
        while (len(str) != 1):
            str = (self._socket.recv(1))
        if not (str == '#'):
            return False
        str=''
        while (len(str) != 1):
            str = (self._socket.recv(1))
        numOfNumBytes = int(str)
        if not (numOfNumBytes > 0):
            return False
        str=''
        while (len(str) != numOfNumBytes):
            str += (self._socket.recv(1))
        numOfBytes = int(str)
        str=''
        while (len(str) != numOfBytes):
            str += (self._socket.recv(1))
        return str

    def tx_txt(self, msg):
        """Send text string ending and append delimiter."""
        return self._socket.send((msg + self.delimiter).encode('utf-8'))

    def txrx_txt(self, msg):
        """Send/receive text string."""
        self.tx_txt(msg)
        return self.rx_txt()

# IEEE Mandated Commands

    def cls(self):
        """Clear Status Command"""
        return self.tx_txt('*CLS')

    def ese(self, value: int):
        """Standard Event Status Enable Command"""
        return self.tx_txt('*ESE {}'.format(value))

    def ese_q(self):
        """Standard Event Status Enable Query"""
        return self.txrx_txt('*ESE?')

    def esr_q(self):
        """Standard Event Status Register Query"""
        return self.txrx_txt('*ESR?')

    def idn_q(self):
        """Identification Query"""
        return self.txrx_txt('*IDN?')

    def opc(self):
        """Operation Complete Command"""
        return self.tx_txt('*OPC')

    def opc_q(self):
        """Operation Complete Query"""
        return self.txrx_txt('*OPC?')

    def rst(self):
        """Reset Command"""
        return self.tx_txt('*RST')

    def sre(self):
        """Service Request Enable Command"""
        return self.tx_txt('*SRE')

    def sre_q(self):
        """Service Request Enable Query"""
        return self.txrx_txt('*SRE?')

    def stb_q(self):
        """Read Status Byte Query"""
        return self.txrx_txt('*STB?')

# :SYSTem

    def err_c(self):
        """Error count."""
        return rp.txrx_txt('SYST:ERR:COUN?')

    def err_c(self):
        """Error next."""
        return rp.txrx_txt('SYST:ERR:NEXT?')


    def switch(self,switcher,input):
        #Switch case function
         arg = switcher.get(input, "Error in Switch Operation")
         return arg

    def float_v(self,number):
        # Limit float precision
        try:
            return float("{0:.2f}".format(float(number)))
        except ValueError:
            return 0.0


    def config_measurement(self):

        frecuencia_min = np.log10(self.sd.def_cfg['f_inicial']['value'])
        frecuencia_max= np.log10(self.sd.def_cfg['f_final']['value'])
        puntos_decada= self.sd.def_cfg['n_puntos']['value']
        ampl =self.sd.def_cfg['vosc']['value']
        decimation=1*puntos_decada*[8192]+2*puntos_decada*[1024]+1*puntos_decada*[64]+2*puntos_decada*[1]
        numero_valores=int((frecuencia_max-frecuencia_min)*puntos_decada)

        if (self.sd.def_cfg['tipo_barrido']['value']==0):
            self.sd.freq = np.linspace(self.sd.def_cfg['f_inicial']['value'],
                                    self.sd.def_cfg['f_final']['value'],
                                    self.sd.def_cfg['n_puntos']['value'])
        elif(self.sd.def_cfg['tipo_barrido']['value']==1):
            self.sd.freq = np.logspace(np.log10(self.sd.def_cfg['f_inicial']['value']),
                                    np.log10(self.sd.def_cfg['f_final']['value']),
                                    numero_valores,base=10)

        #recortamos a 40 Hz

        self.sd.freq=self.sd.freq[self.sd.freq>40]
        numero_valores=len(self.sd.freq)
        incrementos= (self.sd.freq*(2**32))/125e6;
        #print(str(incrementos))
        s = io.BytesIO()
        np.savetxt(s, [incrementos], fmt='%d', delimiter=',')
        outStr = s.getvalue().decode('UTF-8')
        print(outStr)
        self.tx_txt('SOUR2:TRAC:DATA:DATA ' + outStr)

        if (self.sd.def_cfg['post_procesado']['value']==0):
            self.tx_txt('RP:FPGABITREAM 0.94')
        else:
            self.tx_txt('RP:FPGABITREAM_DSD 0.94')

        # valores no configurables desde el front-end
        wave_form = 'sine'
        Rs=1000
        fm=125000000
        numero_pulsos=10
        ciclos=5

        R_shunt_k = self.sd.def_cfg['shunt']['value'] #elijo 1000 
        
        # Postprocesamiento=self.sd.def_cfg['postprocesamiento']['value']
        tipo_Postprocesamiento=self.sd.def_cfg['post_procesado']['value']
        # print(R_shunt_k)
        # # borra cuando quite la SOURCE 2
        # amplreference=np.linspace(10,1,numero_valores)
        # ampl2=1/amplreference
        # phases=np.linspace(180,0,numero_valores)
        shunt=[10.0,100.0,1000.0,10000.0,100000.0,1300000.0]


        #configuro via i2c la resistencia de shunt
        
        # veamos = SshMachine(self.host, user = "root")
        veamos = ParamikoMachine(self.host, user = "root", password="root")
        veamos.env["LD_LIBRARY_PATH"]="/opt/redpitaya/lib"
        veamos.cwd.chdir("/opt/redpitaya/bin")
        comando="./i2c_shunt " + str(R_shunt_k)
        # print (comando)
        r_back = veamos[comando]
        r_back()
        # sizeh1=str('-sizeh1={0}'.format(individual[0]))
        # sizeh2=str('-sizeh2={0}'.format(individual[1]))
        # epochs=str('-epochs={0}'.format(epochs))
        # decay=str('-decay={0}'.format(decay_value))
        # step=str('-step={0}'.format(learning_step))
        # minibatch=str('-batchsize={0}'.format(batchsize))
        # idea=str(r_back[epochs, sizeh1,sizeh2, minibatch,decay,step]())
        # for line in idea.split("\n"):
        #     if "error_val" in line:
        #     #print (line.strip())
        #        error_rate_float=[float(s) for s in re.findall('\d+\.\d+',line)]
        #        error_rate=error_rate_float[0]
        veamos.close()

        # vamos a guardar valores en la memoria de frecuencias



        ## borra cuando quite la SOURCE 2
        # amplreference=np.linspace(10,1,numero_valores)
        # ampl2=1/amplreference
        # phases=np.linspace(180,0,numero_valores)
        # prueba de conexion
        # self.tx_txt('SOUR2:BURS:STAT?')
        # veamosburst= self.rx_txt() 
        # print(veamosburst)
        # self.tx_txt('SOUR2:BURS:NCYC?')
        # veamosCICLOS= self.rx_txt() 
        # print(veamosCICLOS)

        #fprintf(handles.GPIBobj,'PAVER OFF'); % Desactivo el promediado. Añadido por mi.

        # # Average of measurement points
        # self.inst.write('PAVERFACT %s' % str(self.sd.def_cfg['n_medidas_punto']['value']))
        # # Activate average or not
        # self.inst.write('PAVER %s' % self.switch({0:'OFF', 1:'ON'},self.sd.def_cfg['avg']['value']))
        # # Frequency sweep starting at ...
        # self.inst.write('STAR %s' % str(self.sd.def_cfg['f_inicial']['value']))
        # # Frequency sweep stopping at ...
        # self.inst.write('STOP %s' % str(self.sd.def_cfg['f_final']['value']))
        # # Tipo de barrido
        # self.inst.write('SWPT %s' % self.switch({0:'LIN', 1:'LOG'},self.sd.def_cfg['tipo_barrido']['value']))
        # # Number of points
        # self.inst.write('POIN %s' % str(self.sd.def_cfg['n_puntos']['value']))
        # # Bandwidth - resolución de la medida.
        # self.inst.write('BWFACT %s' % str(self.sd.def_cfg['ancho_banda']['value']))
        # # Configura la tensión de salida del oscilador
        # self.inst.write('POWMOD VOLT;POWE %s' % str(self.sd.def_cfg['vosc']['value']))


        # # DC_bias active
        # if (self.sd.def_cfg['DC_bias']==0):
        #     # Tensión de polarización.
        #     self.inst.write('DCV %s' % str(self.sd.def_cfg['nivel_DC']['value']))
        #     # Modo de BIAS
        #     self.inst.write('DCMOD CVOLT')
        #     # Rango de tensión de bias.
        #     self.inst.write('DCRNG M1')
        #     # Borrar errores
        #     self.inst.write('*CLS')
        #     # Activo la tensión de bias.
        #     self.inst.write('DCO ON')
        #     # Solicito el último error que se ha producido
        #     error = self.inst.query('OUTPERRO?')
        #     error_code = int(error[0:error.find(',')])
        #     if (error_code==0):
        #         flag_dcrange = 1
        #     elif (error_code==137):
        #         self.inst.write('DCRNG M10')
        #         self.inst.write('*CLS')
        #         self.inst.write('DCO ON')
        #         error = self.inst.query('OUTPERRO?')
        #         error_code = int(error[0:error.find(',')])
        #         if (error_code==0):
        #             flag_dcrange = 10
        #         elif (error_code==137):
        #             self.inst.write('DCRNG M100')
        #             self.inst.write('*CLS')
        #             self.inst.write('DCO ON')
        #             error = self.inst.query('OUTPERRO?')
        #             error_code = int(error[0:error.find(',')])
        #             if (error_code==0):
        #                 flag_dcrange = 100
        #             elif (error_code==137):
        #                 # ERROR: BIAS Voltage too high
        #                 self.dv.append_plus("Módulo de BIAS demasiado elevado. Redúzcala o Desactívela")
        #                 self.dv.append_plus("ERROR %s" % str(error_code))
        #             else:
        #                 self.dv.append_plus("Reconsidere usar la tensión de BIAS")
        #                 self.dv.append_plus("ERROR %s" % str(error_code))
        #         else:
        #             self.dv.append_plus("Reconsidere usar la tensión de BIAS")
        #             self.dv.append_plus("ERROR %s" % str(error_code))
        #     else:
        #         self.dv.append_plus("Reconsidere usar la tensión de BIAS")
        #         self.dv.append_plus("ERROR %s" % str(error_code))

        # No BIAS voltage
        # else:
        #     self.inst.write('DCRNG M1') # Default range
        #     self.inst.write('DCO OFF')





    def measure(self):
        if (self.sd.def_cfg['post_procesado']['value']==0):
            self.tx_txt('RP:FPGABITREAM 0.94')
            t0=pc()
            frecuencia_min = np.log10(self.sd.def_cfg['f_inicial']['value'])
            frecuencia_max= np.log10(self.sd.def_cfg['f_final']['value'])
            puntos_decada= self.sd.def_cfg['n_puntos']['value']
            ampl =self.sd.def_cfg['vosc']['value']
            decimation=1*puntos_decada*[8192]+2*puntos_decada*[1024]+1*puntos_decada*[64]+2*puntos_decada*[1]
            numero_valores=int((frecuencia_max-frecuencia_min)*puntos_decada)

            if (self.sd.def_cfg['tipo_barrido']['value']==0):
                self.sd.freq = np.linspace(self.sd.def_cfg['f_inicial']['value'],
                                        self.sd.def_cfg['f_final']['value'],
                                        self.sd.def_cfg['n_puntos']['value'])
            elif(self.sd.def_cfg['tipo_barrido']['value']==1):
                self.sd.freq = np.logspace(np.log10(self.sd.def_cfg['f_inicial']['value']),
                                        np.log10(self.sd.def_cfg['f_final']['value']),
                                        numero_valores,base=10)

            #recortamos a 40 Hz

            self.sd.freq=self.sd.freq[self.sd.freq>40]
            numero_valores=len(self.sd.freq)
            incrementos= (self.sd.freq*(2**32))/125e6;
            print(str(incrementos))
            s = io.BytesIO()
            np.savetxt(s, [incrementos], fmt='%d', delimiter=',')
            print(str(s))
            outStr = s.getvalue().decode('UTF-8')
            print(outStr)
            # valores no configurables desde el front-end
            wave_form = 'sine'
            Rs=1000
            fm=125000000
            numero_pulsos=10
            ciclos=5
            R_shunt_k = self.sd.def_cfg['shunt']['value'] #elijo 1000 
            
            # Postprocesamiento=self.sd.def_cfg['postprocesamiento']['value']
            tipo_Postprocesamiento=self.sd.def_cfg['post_procesado']['value']
            # print(R_shunt_k)
            # # borra cuando quite la SOURCE 2
            # amplreference=np.linspace(10,1,numero_valores)
            # ampl2=1/amplreference
            # phases=np.linspace(180,0,numero_valores)
            shunt=[10.0,100.0,1000.0,10000.0,100000.0,1300000.0]


            #configuro via i2c la resistencia de shunt
            
            # veamos = SshMachine(self.host, user = "root")
            veamos = ParamikoMachine(self.host, user = "root", password="root")
            veamos.env["LD_LIBRARY_PATH"]="/opt/redpitaya/lib"
            veamos.cwd.chdir("/opt/redpitaya/bin")
            comando="./i2c_shunt " + str(R_shunt_k)
            # print (comando)
            r_back = veamos[comando]
            r_back()
            # sizeh1=str('-sizeh1={0}'.format(individual[0]))
            # sizeh2=str('-sizeh2={0}'.format(individual[1]))
            # epochs=str('-epochs={0}'.format(epochs))
            # decay=str('-decay={0}'.format(decay_value))
            # step=str('-step={0}'.format(learning_step))
            # minibatch=str('-batchsize={0}'.format(batchsize))
            # idea=str(r_back[epochs, sizeh1,sizeh2, minibatch,decay,step]())
            # for line in idea.split("\n"):
            #     if "error_val" in line:
            #     #print (line.strip())
            #        error_rate_float=[float(s) for s in re.findall('\d+\.\d+',line)]
            #        error_rate=error_rate_float[0]
            veamos.close()



            self.dv.append_plus("Midiendo Z=R+iX")
            iteracion=1
            configuracion=0
            adquisicion=0
            postprocesamiento=0
            espera_trigger=0
            Z=np.zeros(numero_valores)
            PHASE=np.zeros(numero_valores)
            for freq in (self.sd.freq):
                t1=pc()
                self.tx_txt('GEN:RST')
                self.tx_txt('ACQ:RST')
                self.tx_txt('ACQ:DATA:UNITS VOLTS')
                self.tx_txt('SOUR1:BURS:STAT BURST') # % Set burst mode to ON
                self.tx_txt('SOUR1:BURS:NCYC 10') # Set 10 pulses of sine wave
            
                self.tx_txt('SOUR1:FUNC ' + str(wave_form).upper())
                self.tx_txt('SOUR1:VOLT ' + str(ampl))
                self.tx_txt('SOUR1:FREQ:FIX ' + str(freq))
                ## esta siguiente linea hace que se cuelgue
                # self.tx_txt('SOUR1:VOLT:OFFS ' + str(self.sd.def_cfg['nivel_DC']['value'])) # esto lo utilizo para cambiar el offset de canal a
                #rp_s.tx_txt('SOUR1:TRIG:SOUR INT')
                #rp_s.tx_txt('SOUR1:TRIG:IMM')
    # esto habrá que borrarlo !!
                # self.tx_txt('SOUR2:FUNC ' + str(wave_form).upper())
                # self.tx_txt('SOUR2:VOLT ' + str(ampl2[iteracion-1]))
                # self.tx_txt('SOUR2:FREQ:FIX ' + str(freq))
                # self.tx_txt('SOUR2:BURS:STAT BURST') # % Set burst mode to ON
                # self.tx_txt('SOUR2:BURS:NCYC 10') # Set 10 pulses of sine wave     
                # self.tx_txt('SOUR2:PHAS ' + str(phases[iteracion-1]))    
    # hay que borrarlo

                self.tx_txt('ACQ:DEC ' + str(decimation[iteracion-1]))
                self.tx_txt('ACQ:START')
                self.tx_txt('ACQ:TRIG CH1_PE')

                self.tx_txt('OUTPUT:STATE ON')  #cuidado con cambiar esto
                t2=pc()
            # ESPERAMOS EL TRIGGER
                # sleep(1)
                while freq<100:
                    self.tx_txt('ACQ:TRIG:STAT?')
                    if self.rx_txt() == 'TD':
                        break
                t2t=pc()
                # self.dv.append_plus('iteracion:'+ str(iteracion))
                # self.dv.append_plus('frecuencia:'+ str(freq))
                print (iteracion)
                print(freq)
                sleep(0.2)
                self.tx_txt('ACQ:TPOS?')
                veamos= self.rx_txt()
                posicion_trigger=int(veamos)
                # self.dv.append_plus("posicion trigger:" + str(posicion_trigger))
                print('posicion trigger:',veamos)
                length=fm*(ciclos)/(freq*decimation[iteracion-1])
                # print('decimation:',decimation[iteracion-1])
                # LEEMOS Y REPRESENTAMOS 1
                

                self.tx_txt('ACQ:SOUR1:DATA:STA:N? ' + str(posicion_trigger)+','+ str(length))
                
                t3=pc()

                buff_string = self.rx_txt()
                buff_string = buff_string.strip('{}\n\r').replace("  ", "").split(',')
                buff = list(map(float, buff_string))
                t4=pc()
                my_array = np.asarray(buff)
                # super_buffer.append(buff)
                # super_buffer_flat=sum(super_buffer, [])

                t5=pc()



                # LEEMOS Y REPRESENTAMOS2
                self.tx_txt('ACQ:SOUR2:DATA:STA:N? ' + str(posicion_trigger)+','+ str(length))
                t6=pc()
                buff_string = self.rx_txt()
                buff_string = buff_string.strip('{}\n\r').replace("  ", "").split(',')
                buff = list(map(float, buff_string))
                t7=pc()

                my_array2 = np.asarray(buff)
                dif=my_array-my_array2
                #super_buffer2.append(buff)
                #super_buffer_flat2=sum(super_buffer2, [])
                ## lo hacia con FFT
       #         if tipo_Postprocesamiento==1:
       #             yf = fft(my_array)
       #             yf2 = fft(my_array2)
       #             yf3=fft(dif)
       #             indice1=np.argmax(np.abs(yf))
       #             indice2=np.argmax(np.abs(yf2))
       #             indice3=np.argmax(np.abs(yf3))
    #            # Zq=np.max(np.abs(yf))
    #               # Zr=np.max(np.abs(yf2))
    #               # Z[iteracion-1]=np.max(np.abs(yf))/np.max(np.abs(yf2)) #  primera opcion
    #               #yf_dif=(yf2-yf)
    #                # indice3=np.argmax(np.abs(yf_dif))            
    #               ## Z[iteracion-1]=np.max(np.abs(yf_dif))*1000/np.max(np.abs(yf2)) # segunda opcion
    #                Z[iteracion-1]=np.max(np.abs(yf3))*shunt[R_shunt_k]/np.max(np.abs(yf2))    #tercera opcion         
    #                PHASE[iteracion-1]=((np.angle(yf2[indice2]/yf[indice1])))*180/np.pi   
                           
                # metodo alternativo
                T=(1/125e6)*decimation[iteracion-1];           # Sampling time [seconds]                                 # time increment
                w_out=freq*2*np.pi

                U_dut=dif
                I_dut=my_array2/shunt[R_shunt_k]
                
                N=int(length)
                U_dut_sampled_X=np.zeros(N)
                U_dut_sampled_Y=np.zeros(N)
                I_dut_sampled_X=np.zeros(N)
                I_dut_sampled_Y=np.zeros(N)
                dT=np.zeros(N)
                # Accurie  signals  U_in_1 and U_in_2 from RedPitaya for N-sampels time and Calculate for Lock in and save in vectors for sampels
                for t in range(N):
                    U_dut_sampled_X[t]=U_dut[t]*np.sin(t*T*w_out)
                    U_dut_sampled_Y[t]=U_dut[t]*np.sin(t*T*w_out-np.pi/2)

                    I_dut_sampled_X[t]=I_dut[t]*np.sin(t*T*w_out)
                    I_dut_sampled_Y[t]=I_dut[t]*np.sin(t*T*w_out-np.pi/2)
                    dT[t]=t*T
                # Calculate two components of lock-in for both mesured voltage signals

                X_component_lock_in_1=np.trapz(U_dut_sampled_X,x=dT)
                Y_component_lock_in_1=np.trapz(U_dut_sampled_Y,dT)

                X_component_lock_in_2=np.trapz(I_dut_sampled_X,dT)
                Y_component_lock_in_2=np.trapz(I_dut_sampled_Y,dT)

                U_dut_amp=(np.sqrt((X_component_lock_in_1)**2+(Y_component_lock_in_1)**2))*2
                Phase_U_dut=np.arctan2(Y_component_lock_in_1,X_component_lock_in_1)

                # Calculate amplitude and angle of I_dut

                I_dut_amp=(np.sqrt((X_component_lock_in_2)**2+(Y_component_lock_in_2)**2))*2
                Phase_I_dut=np.arctan2(Y_component_lock_in_2,X_component_lock_in_2)
                # Calculate amplitude of current trough impedance and amplitude of impedance

                Z_amp=(U_dut_amp/I_dut_amp);            # Amplitude of impedance

                Z[iteracion-1]=Z_amp

                Phase_Z_rad=(Phase_U_dut-Phase_I_dut)
                Phase_check=(Phase_U_dut-Phase_I_dut)*(180/np.pi)
                if (Phase_check<=-180):
                    Phase_Z=(Phase_U_dut-Phase_I_dut)*(180/np.pi)+360
                else:
                    if (Phase_check>=180):
                        Phase_Z=(Phase_U_dut-Phase_I_dut)*(180/np.pi)-360
                    else:
                        Phase_Z=Phase_check
                PHASE[iteracion-1]=Phase_Z

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
                self.tx_txt('OUTPUT:STATE OFF')
                self.tx_txt('ACQ:STOP')
                t9=pc()
                postprocesamiento=postprocesamiento+(t5-t4)+(t8-t7)
                configuracion=configuracion+(t2-t1)+(t9-t8)+(t6-t5)+(t3-t2t)
                adquisicion=adquisicion+(t4-t3)+(t7-t6)  
                espera_trigger=espera_trigger+ (t2t-t2)  


            # # Service Request instead of using pulling
            # event_type = visa.constants.EventType.service_request
            # # Mechanism by which we want to be notified
            # event_mech = visa.constants.EventMechanism.queue

            # self.inst.write('TRGS INT')          # Internal Trigger Source
            # self.inst.write('ESNB 1')            # Event_Status_Register[0]=1 // Enables Sweep Completion bit
            # self.inst.write('*SRE 4')            # Service Request Enable = 1
            # self.inst.write('*CLS')              # Clears Error queue


            # self.inst.write('MEAS IRIM')         # Medida de R y X
            # self.inst.write('HIDI OFF')          # Muestras la traza inactiva
            # self.inst.write('SING')              # Iniciar un barrido único.

            # self.dv.append_plus("ACK Instrumento = %s" % self.inst.query('*OPC?'))

            # self.inst.enable_event(event_type, event_mech)
            #
            # #self.dv.append_plus(self.inst.query('*OPC?'))
            # # Wait for the event to occur
            # response = self.inst.wait_on_event(event_type, 10000)
            #
            # #if (response.event.event_type == event_type):
            #     # response.timed_out = False
            # self.inst.disable_event(event_type, event_mech)
            # response.timed_out = False

            # Recover Measured Data
            # self.inst.write('TRAC A')           # Selecciona traza A
            # self.inst.write('AUTO')             # Autoescala
            # aux_R = np.fromstring(self.inst.query('OUTPDTRC?'), dtype=float, sep=',')

            # self.inst.write('TRAC B')           # Selecciona traza A
            # self.inst.write('AUTO')             # Autoescala
            # aux_X = np.fromstring(self.inst.query('OUTPDTRC?'), dtype=float, sep=',')
            t10=pc()
            self.sd.R_data = Z*np.cos(PHASE*np.pi/180)
            self.sd.X_data = Z*np.sin(PHASE*np.pi/180)

            # Compute Err, Eri, Er_mod, Er_fase_data
            # First create frequency array based on actual gui conditions
            # The freq array will not be changed until next data acquisition even if GUI changes


            complex_aux         = self.sd.R_data + self.sd.X_data*1j
            self.sd.Z_mod_data  = Z
            self.sd.Z_fase_data = PHASE

            admitance_aux       = 1./complex_aux
            G_data              = np.real(admitance_aux)
            Cp_data             = np.imag(admitance_aux)/(2*np.pi*self.sd.freq)
            self.sd.Err_data    = Cp_data/self.sd.Co
            self.sd.Eri_data    = G_data/(self.sd.Co*(2*np.pi*self.sd.freq));
            E_data              = self.sd.Err_data + -1*self.sd.Eri_data*1j;

            self.sd.Er_mod_data  = np.abs(E_data);
            self.sd.Er_fase_data = np.angle(E_data);
            t11=pc()
            # # Deactivate BIAS for security reasons
            # self.inst.write('DCO OFF')
            # self.inst.write('DCRNG M1')
            postprocesamiento=postprocesamiento+(t11-t10)
            print('espera_trigger:',espera_trigger)
            print('configuracion:',configuracion)
            print('adquisicion:',adquisicion)
            print('postprocesamiento:',postprocesamiento)
            total=t11-t0
            print ('total:',total)
            absolute_val_array = np.abs(self.sd.freq - 1000)
            smallest_difference_index = absolute_val_array.argmin()
            print ('R_data =', self.sd.R_data[smallest_difference_index])        
            print ('X_data=', self.sd.X_data[smallest_difference_index])
            print ('resistencia shunt=', shunt[R_shunt_k])
            # self.inst.wait_for_srq(self.sd.def_cfg['GPIB_timeout'])
            self.dv.append_plus("He finalizado de medir")
            self.dv.append_plus("tiempo transcurrido:" + str(total))
        elif (self.sd.def_cfg['post_procesado']['value']==1):
            # configuramos la FPGA con diseño verilog propio de DSD
            self.tx_txt('RP:FPGABITREAM_DSD 0.94')
            t0=pc()

            frecuencia_min = np.log10(self.sd.def_cfg['f_inicial']['value'])
            frecuencia_max= np.log10(self.sd.def_cfg['f_final']['value'])
            puntos_decada= self.sd.def_cfg['n_puntos']['value']
            numero_valores=int((frecuencia_max-frecuencia_min)*puntos_decada)
            # numero_valores=256
            ##configuramos las frecuencias y enviamos un listado de incrementos a la memoria de incrementos de la FPGA
            if (self.sd.def_cfg['tipo_barrido']['value']==0):
                self.sd.freq = np.linspace(self.sd.def_cfg['f_inicial']['value'],
                                        self.sd.def_cfg['f_final']['value'],
                                        self.sd.def_cfg['n_puntos']['value'])
            elif(self.sd.def_cfg['tipo_barrido']['value']==1):
                self.sd.freq = np.logspace(np.log10(self.sd.def_cfg['f_inicial']['value']),
                                        np.log10(self.sd.def_cfg['f_final']['value']),
                                        numero_valores,base=10)
            self.tx_txt('DIG:PIN LED'+str(1)+','+str(0))  # 1->state2  0->state1
            #recortamos a 40 Hz

            frecuencias=self.sd.freq[self.sd.freq>40]
            numero_valores=len(frecuencias)
            
            print(numero_valores)
            incrementos2=np.ones(256-numero_valores)*1407.0
            incrementos1= (frecuencias*(2**32))/125e6
            incrementos=np.concatenate((incrementos1, incrementos2), axis=None)
            #print(str(incrementos))
            s = io.BytesIO()
            np.savetxt(s, [incrementos], fmt='%1.1f', delimiter=', ')
            outStr = s.getvalue().decode('UTF-8')
            # print(outStr)
            #self.tx_txt('SOUR1:TRAC:DATA:DATA ' + outStr)
            self.tx_txt('SOUR1:FUNC ARBITRARY')
            self.tx_txt('SOUR1:TRAC:DATA:DATA_rafa ' + outStr)
            #self.tx_txt('OUTPUT:STATE ON') 
            #  quitar estas 5 lineas al terminar de debugear 
           # self.tx_txt('ACQ:RESULT2:DATA?')
           # buff_string3 = self.rx_txt()
           # buff_string3 = buff_string3.strip('{}\n\r').replace("  ", "").split(',')
           # buff3 = list(map(float, buff_string3))
           # my_array3 = np.asarray(buff3)

            ## 
            # self.tx_txt('SOUR1:TRAC:DATA:DATA 2, 0.1, 0.1, 0.1, 0.2, 0.3, 0.3, 0.3,-0.2')
            muestras=numero_valores

            decimation=1
            umbral_horizontal_detector_cero=150*puntos_decada/50
            # umbral_vertical_detector_cero=750
            umbral_vertical_detector_cero=200*puntos_decada/50            
            procedimiento_fase=1

            #configuramos el shunt
            shunt=[10.0,100.0,1000.0,10000.0,100000.0,1300000.0]
            R_shunt_k = self.sd.def_cfg['shunt']['value'] #elijo 1000 
            veamos = ParamikoMachine(self.host, user = "root", password="root")
            veamos.env["LD_LIBRARY_PATH"]="/opt/redpitaya/lib"
            veamos.cwd.chdir("/opt/redpitaya/bin")
            comando="./i2c_shunt " + str(R_shunt_k)
            r_back = veamos[comando]
            r_back()
            veamos.close()

            # muestras=10
            frecuencias=frecuencias[0:muestras]
            # configuraciones  varias
            self.tx_txt('SOUR1:VOLT ' +str(self.sd.def_cfg['vosc']['value']))
            self.tx_txt('SOUR1:VOLT:OFFS 0.00') # esto lo utilizo para cambiar el offset de canal b
            self.tx_txt('SOUR2:VOLT:OFFS ' + str(self.sd.def_cfg['nivel_DC']['value'])) # esto lo utilizo para cambiar el offset de canal b
            self.tx_txt('SOUR1:BURS:NCYC 1')  # solo funciona si led3 esta activado, numero de ciclos por frecuencia
            self.tx_txt('SOUR1:BURS:NOR ' +str(muestras)) # solo funciona si led3 esta activado, numero de frecuencias
            # # rp_s.tx_txt('SOUR2:BURS:INT:PER 30') # solo funciona si led3 esta activado, ancho detector
            self.tx_txt('SOUR2:BURS:NOR ' +str(umbral_horizontal_detector_cero))
            self.tx_txt('SOUR2:BURS:NCYC ' +str(umbral_vertical_detector_cero)) #controlo el numero de ciclos de ancho del deteccor de cero


            self.tx_txt('DIG:PIN LED'+str(2)+','+str(procedimiento_fase))  # desbloqueo finalizacion state1, tambien genera inicio
            self.tx_txt('DIG:PIN LED'+str(3)+','+str(1))  #activacion del led3 absolutamente necesario para que el numero de ciclos sea configurable y el numero de frecuencias y los umbrales


            self.dv.append_plus("Midiendo Z=R+iX")
            t1=pc()
            self.tx_txt('CHIRP ON')
            while 1 :
            #    rp_s.tx_txt('FIN:RAF:STAT? 1')
                self.tx_txt('DIG:PIN? DIO'+str(7)+'_N')
                state = self.rx_txt()
                if state == '1':
                    break
            #    # print(rp_s.rx_txt())
            # rp_s.tx_txt('DIG:PIN? DIO'+str(7)+'_N')
            # state = rp_s.rx_txt()
            print(state)
            # EMPEZAMOS CON LA ADQUISION

            self.tx_txt('CHIRP OFF')
            self.tx_txt('ACQ:RESULT1:DATA?')
            t3=pc()

            buff_string = self.rx_txt()
            buff_string = buff_string.strip('{}\n\r').replace("  ", "").split(',')
            buff = list(map(float, buff_string))
            t4=pc()
            my_array = np.asarray(buff)
            my_array =my_array[:-decimation:decimation]
            # super_buffer.append(buff)
            # super_buffer_flat=sum(super_buffer, [])
            self.tx_txt('ACQ:RESULT2:DATA?')
            buff_string2 = self.rx_txt()
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
            Z_sin_comprimir=my_array[0:muestras]*shunt[R_shunt_k]/1000

            # en principio el calculo en verilog es suponiendo una resistencia de 1k. Con esto lo ajusto a la resistencia de shunt exacta


            # PhaseA=interp1d(frecuencias[0:muestras],my_array2[0:muestras])
            # Phase_check=PhaseA(frecuencias)*frecuencias*360/125e6
            # Phase_radianes=PhaseA(frecuencias)*frecuencias*2*np.pi/125e6
            # my_array2=interp1d(frecuencias[0:muestras],my_array2[0:muestras])
            #funcion_interpolacion = make_interp_spline(frecuencias[0:muestras],my_array2[0:muestras], k=7)
            # my_array2=funcion_interpolacion(frecuencias[0:muestras])
            
            smooth=1
            k=9


            Phase_check=-my_array2[0:muestras]*frecuencias[0:muestras]*360/125e6
            Phase_radianes=-my_array2[0:muestras]*frecuencias[0:muestras]*2*np.pi/125e6
            Phase_Z=np.zeros(muestras)
            PHASE_sin_comprimir_pre=np.zeros(muestras)
            PHASE_sin_comprimir=np.zeros(muestras)            
            for fases in range(len(Phase_check)):
                if (Phase_check[fases]<=-180):
                    PHASE_sin_comprimir_pre[fases]=Phase_radianes[fases]*(180/np.pi)+360
                else:
                    if (Phase_check[fases] >=180):
                        PHASE_sin_comprimir_pre[fases]=Phase_radianes[fases]*(180/np.pi)-360
                    else:
                        PHASE_sin_comprimir_pre[fases]=Phase_check[fases]
                if (PHASE_sin_comprimir_pre[fases]<=-90):
                    PHASE_sin_comprimir[fases]= PHASE_sin_comprimir_pre[fases]+180
                else:
                    if (PHASE_sin_comprimir_pre[fases]>=90):
                        PHASE_sin_comprimir[fases]= PHASE_sin_comprimir_pre[fases]-180
                    else:
                        PHASE_sin_comprimir[fases]=PHASE_sin_comprimir_pre[fases]
            PHASE=np.ma.masked_where((Z_sin_comprimir==0),PHASE_sin_comprimir) 
            self.sd.freq=np.ma.masked_where((Z_sin_comprimir==0),frecuencias) 
            Z = np.ma.masked_where((Z_sin_comprimir==0),Z_sin_comprimir) 

            prePHASE=PHASE.compressed()
            preZ = Z.compressed()
            self.sd.freq=self.sd.freq.compressed()
            # ahora aplico una forma de smooth
            if (smooth==1):
                PHASE = np.cumsum(prePHASE, dtype=float)
                Z=np.cumsum(preZ, dtype=float)
                PHASE[k:] = PHASE[k:] - PHASE[:-k]
                Z[k:] = Z[k:] - Z[:-k]
                PHASE=PHASE[k - 1:] / k
                Z=Z[k - 1:] / k
                self.sd.freq=self.sd.freq[k-1:]
            else:
                PHASE=prePHASE
            # self.sd.freq=frecuencias
                Z = preZ
            # Z = Z.compressed()[k-1:]

            #PHASE=PHASE.compressed()
            #self.sd.freq=self.sd.freq.compressed()
            #Z = Z.compressed()
            # self.sd.freq=frecuencias


            # PHASE=PHASE_sin_comprimir
            # self.sd.freq=frecuencias
            # Z = Z_sin_comprimir

            t10=pc()
            self.sd.R_data = Z*np.cos(PHASE*np.pi/180)
            self.sd.X_data = Z*np.sin(PHASE*np.pi/180)

            # Compute Err, Eri, Er_mod, Er_fase_data
            # First create frequency array based on actual gui conditions
            # The freq array will not be changed until next data acquisition even if GUI changes


            complex_aux         = self.sd.R_data + self.sd.X_data*1j
            self.sd.Z_mod_data  = Z
            self.sd.Z_fase_data = PHASE
            # las proximas lineas deben de descomentarse cuando haya eliminado los outliers
            admitance_aux       = 1./complex_aux
            G_data              = np.real(admitance_aux)
            Cp_data             = np.imag(admitance_aux)/(2*np.pi*self.sd.freq)
            self.sd.Err_data    = Cp_data/self.sd.Co
            self.sd.Eri_data    = G_data/(self.sd.Co*(2*np.pi*self.sd.freq));
            E_data              = self.sd.Err_data + -1*self.sd.Eri_data*1j;

            self.sd.Er_mod_data  = np.abs(E_data);
            self.sd.Er_fase_data = np.angle(E_data);
            t11=pc()

            total=t11-t1
            print ('total:',total)

            self.dv.append_plus("He finalizado de medir")
            self.dv.append_plus("tiempo transcurrido:" + str(total))
        elif (self.sd.def_cfg['post_procesado']['value']==2):
            # configuramos la FPGA con diseño verilog propio de DSD
            self.tx_txt('RP:FPGABITREAM_DSD 0.94')
            t0=pc()

            frecuencia_min = np.log10(self.sd.def_cfg['f_inicial']['value'])
            frecuencia_max= np.log10(self.sd.def_cfg['f_final']['value'])
            puntos_decada= self.sd.def_cfg['n_puntos']['value']
            numero_valores=int((frecuencia_max-frecuencia_min)*puntos_decada)
            # numero_valores=256
            ##configuramos las frecuencias y enviamos un listado de incrementos a la memoria de incrementos de la FPGA
            if (self.sd.def_cfg['tipo_barrido']['value']==0):
                self.sd.freq = np.linspace(self.sd.def_cfg['f_inicial']['value'],
                                        self.sd.def_cfg['f_final']['value'],
                                        self.sd.def_cfg['n_puntos']['value'])
            elif(self.sd.def_cfg['tipo_barrido']['value']==1):
                self.sd.freq = np.logspace(np.log10(self.sd.def_cfg['f_inicial']['value']),
                                        np.log10(self.sd.def_cfg['f_final']['value']),
                                        numero_valores,base=10)
            self.tx_txt('DIG:PIN LED'+str(1)+','+str(0))  # 1->state2  0->state1
            #recortamos a 40 Hz

            frecuencias=self.sd.freq[self.sd.freq>40]
            numero_valores=len(frecuencias)
            
            print(numero_valores)
            incrementos2=np.ones(256-numero_valores)*34360000.0
            incrementos1= (frecuencias*(2**32))/125e6
            incrementos=np.concatenate((incrementos1, incrementos2), axis=None)
            #print(str(incrementos))
            s = io.BytesIO()
            np.savetxt(s, [incrementos], fmt='%1.1f', delimiter=', ')
            outStr = s.getvalue().decode('UTF-8')
            # print(outStr)
            self.tx_txt('SOUR1:TRAC:DATA:DATA ' + outStr)
            self.tx_txt('SOUR1:FUNC ARBITRARY')
            self.tx_txt('SOUR1:TRAC:DATA:DATA_rafa ' + outStr)
            self.tx_txt('OUTPUT:STATE ON') 
            #  quitar estas 5 lineas al terminar de debugear 
           # self.tx_txt('ACQ:RESULT2:DATA?')
           # buff_string3 = self.rx_txt()
           # buff_string3 = buff_string3.strip('{}\n\r').replace("  ", "").split(',')
           # buff3 = list(map(float, buff_string3))
           # my_array3 = np.asarray(buff3)

            ## 
            # self.tx_txt('SOUR1:TRAC:DATA:DATA 2, 0.1, 0.1, 0.1, 0.2, 0.3, 0.3, 0.3,-0.2')
            muestras=numero_valores

            decimation=1
            umbral_horizontal_detector_cero=150*puntos_decada/50
            # umbral_vertical_detector_cero=750
            umbral_vertical_detector_cero=200*puntos_decada/50            
            procedimiento_fase=2

            #configuramos el shunt
            shunt=[10.0,100.0,1000.0,10000.0,100000.0,1300000.0]
            R_shunt_k = self.sd.def_cfg['shunt']['value'] #elijo 1000 
            veamos = ParamikoMachine(self.host, user = "root", password="root")
            veamos.env["LD_LIBRARY_PATH"]="/opt/redpitaya/lib"
            veamos.cwd.chdir("/opt/redpitaya/bin")
            comando="./i2c_shunt " + str(R_shunt_k)
            r_back = veamos[comando]
            r_back()
            veamos.close()

            # muestras=10
            frecuencias=frecuencias[0:muestras]
            muestras_incrementadas=muestras+4
            # configuraciones  varias
            self.tx_txt('SOUR1:VOLT ' +str(self.sd.def_cfg['vosc']['value']))
            self.tx_txt('SOUR1:VOLT:OFFS 0.00') # esto lo utilizo para cambiar el offset de canal b
            self.tx_txt('SOUR2:VOLT:OFFS ' + str(self.sd.def_cfg['nivel_DC']['value'])) # esto lo utilizo para cambiar el offset de canal b
            self.tx_txt('SOUR1:BURS:NCYC 1')  # solo funciona si led3 esta activado, numero de ciclos por frecuencia
            self.tx_txt('SOUR1:BURS:NOR ' +str(muestras_incrementadas)) # solo funciona si led3 esta activado, numero de frecuencias
            # # rp_s.tx_txt('SOUR2:BURS:INT:PER 30') # solo funciona si led3 esta activado, ancho detector
            self.tx_txt('SOUR2:BURS:NOR ' +str(umbral_horizontal_detector_cero))
            self.tx_txt('SOUR2:BURS:NCYC ' +str(umbral_vertical_detector_cero)) #controlo el numero de ciclos de ancho del deteccor de cero


            self.tx_txt('DIG:PIN LED'+str(2)+','+str(procedimiento_fase))  # desbloqueo finalizacion state1, tambien genera inicio
            self.tx_txt('DIG:PIN LED'+str(3)+','+str(1))  #activacion del led3 absolutamente necesario para que el numero de ciclos sea configurable y el numero de frecuencias y los umbrales


            self.dv.append_plus("Midiendo Z=R+iX")
            t1=pc()
            self.tx_txt('CHIRP ON')
            while 1 :
            #    rp_s.tx_txt('FIN:RAF:STAT? 1')
                self.tx_txt('DIG:PIN? DIO'+str(7)+'_N')
                state = self.rx_txt()
                if state == '1':
                    break
            #    # print(rp_s.rx_txt())
            # rp_s.tx_txt('DIG:PIN? DIO'+str(7)+'_N')
            # state = rp_s.rx_txt()
            print(state)
            # EMPEZAMOS CON LA ADQUISION

            self.tx_txt('CHIRP OFF')
            self.tx_txt('ACQ:RESULT1:DATA?')
            t3=pc()

            buff_string = self.rx_txt()
            buff_string = buff_string.strip('{}\n\r').replace("  ", "").split(',')
            buff = list(map(float, buff_string))
            t4=pc()
            my_array = np.asarray(buff)
            my_array =my_array[:-decimation:decimation]
            # super_buffer.append(buff)
            # super_buffer_flat=sum(super_buffer, [])
            self.tx_txt('ACQ:RESULT2:DATA?')
            buff_string2 = self.rx_txt()
            buff_string2 = buff_string2.strip('{}\n\r').replace("  ", "").split(',')
            buff2 = list(map(float, buff_string2))
            my_array2 = np.asarray(buff2)
            my_array2 =my_array2[:-decimation:decimation]
            muestras=round(muestras/decimation)
            t5=pc()
            print('t5-t1:',t5-t1)


            smooth=0
            k=9


            #Enable output
            iteracion=1
            # ZA=interp1d(frecuencias[0:muestras],my_array[0:muestras])
            # ZB=interp1d(frecuencias,my_array[256: 256+225])
            # Z=(ZA(frecuencias))*shunt[R_shunt_k]/1000
            Z_sin_comprimir=(my_array[0:muestras]*shunt[R_shunt_k])/1000
            # en principio el calculo en verilog es suponiendo una resistencia de 1k. Con esto lo ajusto a la resistencia de shunt exacta


            # PhaseA=interp1d(frecuencias[0:muestras],my_array2[0:muestras])
            # Phase_check=PhaseA(frecuencias)*frecuencias*360/125e6
            # Phase_radianes=PhaseA(frecuencias)*frecuencias*2*np.pi/125e6

                # tangentea=my_array2[0:muestras]/(1024*64)
                # tangenteb=my_array2[256:256+muestras]/(1024*64)
                # arcoa=np.arctan(tangentea) 
                # arcob=np.arctan(tangenteb) 
                # Phase_radianes=(arcoa-arcob)
            # Phase_escalada=-my_array2[0:muestras]/(2**29) 
            Phase_escalada=-my_array2[0:muestras]  # porque las fases las calculo multiplicads por 2
            #Phase_radianes=Phase_escalada*np.pi           
            #Phase_check=Phase_radianes*360/(2*np.pi)
            Phase_radianes=Phase_escalada*np.pi/180           
            Phase_check=Phase_escalada            
            PHASE_sin_comprimir=np.zeros(muestras)
            for fases in range(len(Phase_check)):
                if (Phase_check[fases]<=-180):
                    PHASE_sin_comprimir[fases]=Phase_radianes[fases]*(180/np.pi)+360
                else:
                    if (Phase_check[fases] >=180):
                        PHASE_sin_comprimir[fases]=Phase_radianes[fases]*(180/np.pi)-360
                    else:
                        PHASE_sin_comprimir[fases]=Phase_check[fases]                
            # PHASE=my_array[256: 256+225]*frecuencias*360/125e6
            # PHASE= Phase_check
            PHASE_sin_comprimir=PHASE_sin_comprimir/2
            PHASE=np.ma.masked_where((Z_sin_comprimir==0),PHASE_sin_comprimir) 
            self.sd.freq=np.ma.masked_where((Z_sin_comprimir==0),frecuencias) 
            Z = np.ma.masked_where((Z_sin_comprimir==0),Z_sin_comprimir) 

            prePHASE=PHASE.compressed()
            self.sd.freq=self.sd.freq.compressed()
            preZ = Z.compressed()

                        # ahora aplico una forma de smooth
            if (smooth==1):
                PHASE = np.cumsum(prePHASE, dtype=float)
                Z=np.cumsum(preZ, dtype=float)
                PHASE[k:] = PHASE[k:] - PHASE[:-k]
                Z[k:] = Z[k:] - Z[:-k]
                PHASE=PHASE[k - 1:] / k

                Z=Z[k - 1:] / k
                self.sd.freq=self.sd.freq[k-1:]
            else:
                PHASE=prePHASE
            # self.sd.freq=frecuencias
                Z = preZ

            t10=pc()
            self.sd.R_data = Z*np.cos(PHASE*np.pi/180)
            self.sd.X_data = Z*np.sin(PHASE*np.pi/180)

            # Compute Err, Eri, Er_mod, Er_fase_data
            # First create frequency array based on actual gui conditions
            # The freq array will not be changed until next data acquisition even if GUI changes


            complex_aux         = self.sd.R_data + self.sd.X_data*1j
            self.sd.Z_mod_data  = Z
            self.sd.Z_fase_data = PHASE
            # las proximas lineas deben de descomentarse cuando haya eliminado los outliers
            admitance_aux       = 1./complex_aux
            G_data              = np.real(admitance_aux)
            Cp_data             = np.imag(admitance_aux)/(2*np.pi*self.sd.freq)
            self.sd.Err_data    = Cp_data/self.sd.Co
            self.sd.Eri_data    = G_data/(self.sd.Co*(2*np.pi*self.sd.freq));
            E_data              = self.sd.Err_data + -1*self.sd.Eri_data*1j;

            self.sd.Er_mod_data  = np.abs(E_data);
            self.sd.Er_fase_data = np.angle(E_data);
            t11=pc()

            total=t11-t1
            print ('total:',total)

            self.dv.append_plus("He finalizado de medir")
            self.dv.append_plus("tiempo transcurrido:" + str(total))            

    def config_calibration(self):
        # Configuración de los valores para la calibración en abierto, corto y carga
        # Calibración MEDIDOR/USUARIO
        # COMMON PARAMETERS
        # Average of measurement points

        self.inst.write('PAVERFACT %s' % str(self.sd.def_cfg['n_medidas_punto']['value']))
        # Activate average or not
        self.inst.write('PAVER %s' % self.switch({0:'OFF', 1:'ON'},self.sd.def_cfg['avg']['value']))
        # Frequency sweep starting at ...
        self.inst.write('STAR %s' % str(self.sd.def_cfg['f_inicial']['value']))
        # Frequency sweep stopping at ...
        self.inst.write('STOP %s' % str(self.sd.def_cfg['f_final']['value']))
        # Tipo de barrido
        self.inst.write('SWPT %s' % self.switch({0:'LIN', 1:'LOG'},self.sd.def_cfg['tipo_barrido']['value']))
        # Number of points
        self.inst.write('POIN %s' % str(self.sd.def_cfg['n_puntos']['value']))
        # Bandwidth - resolución de la medida.
        self.inst.write('BWFACT %s' % str(self.sd.def_cfg['ancho_banda']['value']))
        # Configura la tensión de salida del oscilador
        self.inst.write('POWMOD VOLT;POWE %s' % str(self.sd.def_cfg['vosc']['value']))

        # Desativo bias
        self.inst.write('DCO OFF')
        # Fijo rango de tensión de bias
        self.inst.write('DCRNG M1')

        # Configure calibration/measurement process
        self.inst.write('CALP %s' % self.switch({0:'FIXED', 1:'USER'},self.sd.def_cfg['pto_cal']['value']))

        # % ************** IMPORTANTE ***********************************
        # % * Los valores de la calibración en abierto serán usados para la
        # % * calibración en carga y los valores de la caligración en carga serán
        # % * usados para la calibración en abierto.
        # % ***************************************************************

        # Conductancia esparada en la calibración en abierto
        self.inst.write('DCOMOPENG %s' % str(self.sd.def_cfg['g_load']['value']))
        # Capacidad esparada en la calibración en abierto (fF)
        self.inst.write('DCOMOPENC %s' % str(self.sd.def_cfg['c_load']['value']))

        # Resistencia esperada calibración corto
        self.inst.write('DCOMSHORR %s' % str(self.sd.Short_r))
        # Inductancia esperada calibración corto
        self.inst.write('DCOMSHORL %s' % str(self.sd.Short_l))
        # Resistencia esperada calibración en carga
        self.inst.write('DCOMLOADR %s' % str(self.sd.Open_r))
        # Inductancia esperada calibración en carga
        self.inst.write('DCOMLOADL %s' % str(self.sd.Open_l))


    def cal_load_open_short(self):
        # Proceos de la calibración en carga, para ello como se indica se
        # realiza una calibración en abierto con la configuración realizada con
        # los comandos anteriores.

        # % ************** IMPORTANTE ***********************************
        # % * Los valores de la calibración en abierto serán usados para la
        # % * calibración en carga y los valores de la caligración en carga serán
        # % * usados para la calibración en abierto.
        # % ***************************************************************

        ############## CARGA
        self.message_box("Calibración con CARGA",
                         "Introduzca la carga indicada y pulsa ACEPTAR")
        self.dv.append_plus("Realizando calibración por carga")

        error_code = self.AdapterCorrection('Compen_Open')
        if error_code==0:
            self.dv.append_plus("Calibración por CARGA realizada correctamente")
        else:
            self.dv.append_plus("Error %s en calibración por carga" % error_code)

        ############## ABIERTO
        self.message_box("Calibración en ABIERTO",
                         "Configure el sensor para calibración en ABIERTO y pulsa ACEPTAR")
        self.dv.append_plus("Realizando calibración en ABIERTO")

        error_code = self.AdapterCorrection('Compen_Load')
        if error_code==0:
            self.dv.append_plus("Calibración en ABIERTO realizada correctamente")
        else:
            self.dv.append_plus("Error %s en calibración en ABIERTO" % error_code)

        ############## CORTO
        self.message_box("Calibración en CORTO",
                         "Configure el sensor para calibración en CORTO y pulsa ACEPTAR")
        self.dv.append_plus("Realizando calibración en CORTO")

        error_code = self.AdapterCorrection('Compen_Short')
        if error_code==0:
            self.dv.append_plus("Calibración en CORTO realizada correctamente")
        else:
            self.dv.append_plus("Error %s en calibración en CORTO" % error_code)

    def cal_open_short(self):
        # Proceos de la calibración en carga, para ello como se indica se
        # realiza una calibración en abierto con la configuración realizada con
        # los comandos anteriores.

        ############## ABIERTO
        self.message_box("Calibración en ABIERTO",
                         "Configure el sensor para calibración en ABIERTO y pulsa ACEPTAR")
        self.dv.append_plus("Realizando calibración en ABIERTO")

        error_code = self.AdapterCorrection('Compen_Open')
        if error_code==0:
            self.dv.append_plus("Calibración en ABIERTO realizada correctamente")
        else:
            self.dv.append_plus("Error %s en calibración en ABIERTO" % error_code)

        ############## CORTO
        self.message_box("Calibración en CORTO",
                         "Configure el sensor para calibración en CORTO y pulsa ACEPTAR")
        self.dv.append_plus("Realizando calibración en CORTO")

        error_code = self.AdapterCorrection('Compen_Short')
        if error_code==0:
            self.dv.append_plus("Calibración en CORTO realizada correctamente")
        else:
            self.dv.append_plus("Error %s en calibración en CORTO" % error_code)


    def get_calibration(self):
        # Loads OPEN - SHORT - LOAD calibration results
        test=self.inst.query('OUTPCOMC1?')
        OPEN_cal  = np.fromstring(test, dtype=float, sep=',')
        SHORT_cal = np.fromstring(self.inst.query('OUTPCOMC2?'), dtype=float, sep=',')
        LOAD_cal  = np.fromstring(self.inst.query('OUTPCOMC3?'), dtype=float, sep=',')

        self.sd.COM_OPEN_data_R = OPEN_cal[0::2]
        self.sd.COM_OPEN_data_X = OPEN_cal[1::2]
        self.sd.COM_SHORT_data_R = SHORT_cal[0::2]
        self.sd.COM_SHORT_data_X = SHORT_cal[1::2]
        self.sd.COM_LOAD_data_R = LOAD_cal[0::2]
        self.sd.COM_LOAD_data_X = LOAD_cal[1::2]

        # Frequency array creation
        if (self.sd.def_cfg['tipo_barrido']['value']==0):
            self.sd.freq = np.linspace(self.sd.def_cfg['f_inicial']['value'],
                                       self.sd.def_cfg['f_final']['value'],
                                       self.sd.def_cfg['n_puntos']['value'])
        elif(self.sd.def_cfg['tipo_barrido']['value']==1):
            self.sd.freq = np.logspace(np.log10(self.sd.def_cfg['f_inicial']['value']),
                                       np.log10(self.sd.def_cfg['f_final']['value']),
                                       self.sd.def_cfg['n_puntos']['value'])

    def send_calibration(self):
        # Create arrays to send CALIBRATION information
        # Think about what to do with load calibration information when open-short calibration is used
        open_data = np.zeros(len(self.sd.COM_OPEN_data_R)*2)
        open_data[0::2] = self.sd.COM_OPEN_data_R
        open_data[1::2] = self.sd.COM_OPEN_data_X
        short_data = np.zeros(len(self.sd.COM_SHORT_data_R)*2)
        short_data[0::2] = self.sd.COM_SHORT_data_R
        short_data[1::2] = self.sd.COM_SHORT_data_X
        load_data = np.zeros(len(self.sd.COM_LOAD_data_R)*2)
        load_data[0::2] = self.sd.COM_LOAD_data_R
        load_data[1::2] = self.sd.COM_LOAD_data_X

        open_data_string = ''.join(str("{:-8.6e}".format(i))+","  for i in open_data)
        open_data_string = open_data_string[:-1]
        short_data_string = ''.join(str("{:-8.6e}".format(i))+","  for i in short_data)
        short_data_string = short_data_string[:-1]
        load_data_string = ''.join(str("{:-8.6e}".format(i))+","  for i in load_data)
        load_data_string = load_data_string[:-1]


        self.inst.write('INPUCOMC1 ' + open_data_string)
        self.inst.write('INPUCOMC2 ' + short_data_string)
        self.inst.write('INPUCOMC3 ' + load_data_string)


    def message_box(self,title,text):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setText(text)
        # msg.setInformativeText(text)
        msg.setWindowTitle(title)
        #msg.setDetailedText("")
        retval = msg.exec_()


    def AdapterCorrection(self, type):
        # Activo el bit 8 del instrument event status register
        # Que se activará cuando se finalice una calibración o compensación
        self.inst.write('ESNB 256')
        # Activo el bit 2 del Status Byte Register, el denomindo bit Instrument
        # Event Status Register Summary. Este indica que se active la linea SRQ
        # del bus GPIB cuando se produzca el evento programando en el Instrument
        # Event Status Register
        self.inst.write('*SRE 4')
        # Clear de los registros
        self.inst.write('*CLS')


        # Se aplica la compensación según el tipo de calibración
        self.inst.write(self.switch({'Adapter_Phase':'ECALP',
                                   'Compen_Open':'COMA',
                                   'Compen_Short':'COMB',
                                   'Compen_Load':'COMC'}
                                   ,type))
        # Espera hasta que se produce un SRQ en el instrumento indicado con GPIBobj
        # En este caso la linea SRQ se activa cuando se ha finalizado la
        # compensación (timeout 120seg)
        self.inst.wait_for_srq(self.sd.def_cfg['GPIB_timeout'])

        # Pregunto por el último error
        error = self.inst.query('OUTPERRO?')
        error_code = int(error[0:error.find(',')])


        if error_code == 0:
            self.dv.append_plus("Calibración %s correcta" % type)
        else:
            self.dv.append_plus("Error en Calibración %s" % type)

        return error_code