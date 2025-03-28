# import pyvisa as visa
import socket
import io
import numpy as np
import signal
from time import perf_counter as pc
from time import sleep
from scipy.fft import fft, fftfreq, fftshift
from scipy.interpolate import interp1d, make_interp_spline
from PySide6.QtWidgets import QMessageBox
import fit_library as fit
import pandas as pd
from plumbum import SshMachine
from plumbum.machines.paramiko_machine import ParamikoMachine



class VISA(object):
    delimiter = '\r\n'
    def __init__(self, shared_data, dataview, timeout=None, port=5000):
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
        host=self.sd.def_cfg['direccion_redpitaya']
        self.host    = host
        self.port    = port
        self.timeout = timeout

        try:
             self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

             if timeout is not None:
                 self._socket.settimeout(timeout)

             self._socket.connect((self.host, port))
             print('conexion establecida con redpitaya')

        except socket.error as e:
            self.dv.append_plus("no se puede conectar a la redpitaya ="+ str(host))     
            # print('SCPI >> connect({:s}:{:d}) failed: {:s}'.format(host, port, e))
    def conectar(self):
        # self.sd = shared_data
        # #self.tb = txt_browser
        # #self.fit_browser = fit_browser
        # self.dv = dataview

        # Visa initializationg
        # self.rm = visa.ResourceManager()
        # self.lor = self.rm.list_resources()
        # ("Lista de dispositivos encontrados:") 
        # self.dv.append_plus(str(self.lor)) 

        """Initialize object and open IP connection.
        Host IP should be a string in parentheses, like '192.168.1.100'.
        """
        host=self.sd.def_cfg['direccion_redpitaya']
        self.host    = host
        port    = self.port
        timeout= self.timeout

        try:
            self._socket = None
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)            
            if timeout is not None:
                 self._socket.settimeout(timeout)

            self._socket.connect((host, port))
            if self.sd.def_cfg['modelo']['value']==0:
                shunt=[90.9,100.0,900.9,1000.0,10000.0,100000.0]
                self.tx_txt('RP:FPGABITREAM_DSD 0.94')
            else:
                if self.sd.def_cfg['modelo']['value']==1:
                    shunt=[90.9,100.0,285.71,500.0,1000.0,2000.0]
                    bitstream="/opt/redpitaya/fpga/red_pitaya_top_rafa.bit.bin"
              
                    veamos = ParamikoMachine(self.host, user = "root", password="root")
                    veamos.env["LD_LIBRARY_PATH"]="/opt/redpitaya/lib"
                    veamos.cwd.chdir("/opt/redpitaya/bin")
                    comando="./fpgautil -b " + bitstream
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
                else:
                    shunt=[90.9,100.0,285.71,500.0,1000.0,2000.0]
                    # opcion que me ha funcionado correctamente
                    # bitstream="/opt/redpitaya/fpga/red_pitaya_top_rafa_autoshunt3.bit.bin"              
                    bitstream="/opt/redpitaya/fpga/fpga_2025.bit.bin"    #opcion con mejoras de analisis temporal estático y cuantización de senoide    
                    veamos = ParamikoMachine(self.host, user = "root", password="root")
                    veamos.env["LD_LIBRARY_PATH"]="/opt/redpitaya/lib"
                    veamos.cwd.chdir("/opt/redpitaya/bin")
                    comando="./fpgautil -b " + bitstream
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
            print('conexion establecida con redpitaya')
            self.dv.append_plus("CONECTADO a redpitaya ="+ str(host))  

        except socket.error as e:
            self.dv.append_plus("no se puede conectar a la redpitaya ="+ str(host))     
            # print('SCPI >> connect({:s}:{:d}) failed: {:s}'.format(host, port, e))
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
        error=0
    #     if (self.sd.def_cfg['post_procesado']['value']==0):
    #         if self.sd.def_cfg['modelo']['value']==0:
    #             shunt=[90.9,100.0,900.9,1000.0,10000.0,100000.0]
    #             self.tx_txt('RP:FPGABITREAM 0.94')
    #         else:
    #             shunt=[90.9,100.0,285.71,500.0,1000.0,2000.0]        
    #             self.tx_txt('RP:FPGABITREAM 0.94')
    #             bitstream="/opt/redpitaya//fpga/z20_125/v0.94/fpga.bit.bin"
    #             veamos = ParamikoMachine(self.host, user = "root", password="root")
    #             veamos.env["LD_LIBRARY_PATH"]="/opt/redpitaya/lib"
    #             veamos.cwd.chdir("/opt/redpitaya/bin")
    #             comando="./fpgautil -b " + bitstream
    #             # print (comando)
    #             r_back = veamos[comando]
    #             r_back()
    #             # sizeh1=str('-sizeh1={0}'.format(individual[0]))
    #             # sizeh2=str('-sizeh2={0}'.format(individual[1]))
    #             # epochs=str('-epochs={0}'.format(epochs))
    #             # decay=str('-decay={0}'.format(decay_value))
    #             # step=str('-step={0}'.format(learning_step))
    #             # minibatch=str('-batchsize={0}'.format(batchsize))
    #             # idea=str(r_back[epochs, sizeh1,sizeh2, minibatch,decay,step]())
    #             # for line in idea.split("\n"):
    #             #     if "error_val" in line:
    #             #     #print (line.strip())
    #             #        error_rate_float=[float(s) for s in re.findall('\d+\.\d+',line)]
    #             #        error_rate=error_rate_float[0]
    #             veamos.close()
    #         t0=pc()
    #         frecuencia_min = np.log10(self.sd.def_cfg['f_inicial']['value'])
    #         frecuencia_max= np.log10(self.sd.def_cfg['f_final']['value'])
    #         puntos_decada= self.sd.def_cfg['n_puntos']['value']
    #         ampl =self.sd.def_cfg['vosc']['value']
    #         decimation=1*puntos_decada*[8192]+2*puntos_decada*[1024]+1*puntos_decada*[64]+2*puntos_decada*[1]
    #         numero_valores=int((frecuencia_max-frecuencia_min)*puntos_decada)

    #         if (self.sd.def_cfg['tipo_barrido']['value']==0):
    #             self.sd.freq = np.linspace(self.sd.def_cfg['f_inicial']['value'],
    #                                     self.sd.def_cfg['f_final']['value'],
    #                                     self.sd.def_cfg['n_puntos']['value'])
    #         elif(self.sd.def_cfg['tipo_barrido']['value']==1):
    #             self.sd.freq = np.logspace(np.log10(self.sd.def_cfg['f_inicial']['value']),
    #                                     np.log10(self.sd.def_cfg['f_final']['value']),
    #                                     numero_valores,base=10)

    #         #recortamos a 40 Hz

    #         self.sd.freq=self.sd.freq[self.sd.freq>40]
    #         numero_valores=len(self.sd.freq)
    #         incrementos= (self.sd.freq*(2**32))/125e6;
    #         #print(str(incrementos))
    #         s = io.BytesIO()
    #         np.savetxt(s, [incrementos], fmt='%d', delimiter=',')
    #         #print(str(s))
    #         outStr = s.getvalue().decode('UTF-8')
    #         #print(outStr)
    #         # valores no configurables desde el front-end
    #         wave_form = 'sine'
    #         Rs=1000
    #         fm=125000000
    #         numero_pulsos=10
    #         ciclos=5
    #         R_shunt_k = self.sd.def_cfg['shunt']['value'] #elijo 1000 
            
    #         # Postprocesamiento=self.sd.def_cfg['postprocesamiento']['value']
    #         tipo_Postprocesamiento=self.sd.def_cfg['post_procesado']['value']
    #         # print(R_shunt_k)
    #         # # borra cuando quite la SOURCE 2
    #         # amplreference=np.linspace(10,1,numero_valores)
    #         # ampl2=1/amplreference
    #         # phases=np.linspace(180,0,numero_valores)


    #         ## shunt=[10.0,100.0,1000.0,10000.0,100000.0,1300000.0]

    #         shunt =[100.0,1000.0,10000.0,100000.0]
    #         #configuro via i2c la resistencia de shunt
            
    #         # veamos = SshMachine(self.host, user = "root")
    #         ##veamos = ParamikoMachine(self.host, user = "root", password="root")
    #         ##veamos.env["LD_LIBRARY_PATH"]="/opt/redpitaya/lib"
    #         ##veamos.cwd.chdir("/opt/redpitaya/bin")
    #         ##comando="./i2c_shunt " + str(R_shunt_k)
    #         # print (comando)
    #         ##r_back = veamos[comando]
    #         ##r_back()
    #         ##veamos.close()
            
    #         self.tx_txt('DIG:PIN:DIR OUT,DIO0_N')
    #         self.tx_txt('DIG:PIN:DIR OUT,DIO1_N')
    #         self.tx_txt('DIG:PIN:DIR OUT,DIO2_N')
    #         self.tx_txt('DIG:PIN:DIR OUT,DIO3_N')
    #         self.tx_txt('DIG:PIN:DIR OUT,DIO4_N')
    #         self.tx_txt('DIG:PIN:DIR OUT,DIO5_N')
    #         self.tx_txt('DIG:PIN:DIR OUT,DIO6_N')
    #         self.tx_txt('DIG:PIN:DIR OUT,DIO7_N')

    #         if (R_shunt_k==0):
    #             # elegimos 90.9 
    #             # activo a nivel bajo: activo
    #             self.tx_txt('DIG:PIN DIO0_N,0') 
    #             # activo a nivel bajo: desactivo
    #             self.tx_txt('DIG:PIN DIO1_N,1')
    #             # activo a nivel alto: desactivo            
    #             self.tx_txt('DIG:PIN DIO2_N,0')
    #             # activo a nivel alto: activo                
    #             self.tx_txt('DIG:PIN DIO3_N,1')
    #         else:
    #             if (R_shunt_k==1):
    #                 # elegimos 100 
    #                 # activo a nivel bajo: desactivo
    #                 self.tx_txt('DIG:PIN DIO0_N,1') 
    #                 # activo a nivel bajo: desactivo
    #                 self.tx_txt('DIG:PIN DIO1_N,1')
    #                 # activo a nivel alto: desactivo            
    #                 self.tx_txt('DIG:PIN DIO2_N,0')
    #                 # activo a nivel alto: activo                
    #                 self.tx_txt('DIG:PIN DIO3_N,1')
    #             else:
    #                 if (R_shunt_k==2):
    #                     # elegimos 900.9 
    #                     # activo a nivel bajo: activo
    #                     self.tx_txt('DIG:PIN DIO0_N,0') 
    #                     # activo a nivel bajo: activo
    #                     self.tx_txt('DIG:PIN DIO1_N,0')
    #                     # activo a nivel alto: activo            
    #                     self.tx_txt('DIG:PIN DIO2_N,1')
    #                     # activo a nivel alto: desactivo                
    #                     self.tx_txt('DIG:PIN DIO3_N,0')
    #                 else:
    #                     if (R_shunt_k==3):
    #                         # #elegimos 1K
    #                         # #activo a nivel bajo: activo
    #                         self.tx_txt('DIG:PIN DIO0_N,0') 
    #                         # #activo a nivel bajo: desactivo
    #                         self.tx_txt('DIG:PIN DIO1_N,1')
    #                         # #activo a nivel alto: desactivo            
    #                         self.tx_txt('DIG:PIN DIO2_N,0')
    #                         # #activo a nivel alto: desactivo                
    #                         self.tx_txt('DIG:PIN DIO3_N,0')  
    #                     else:
    #                         if (R_shunt_k==4):
    #                             # elegimos 10K
    #                             # activo a nivel bajo: desactivo
    #                             self.tx_txt('DIG:PIN DIO0_N,1') 
    #                             # activo a nivel bajo: activo
    #                             self.tx_txt('DIG:PIN DIO1_N,0')
    #                             # activo a nivel alto: desactivo            
    #                             self.tx_txt('DIG:PIN DIO2_N,0')
    #                             # activo a nivel alto: desactivo                
    #                             self.tx_txt('DIG:PIN DIO3_N,0')
    #                         else:
    #                             # k==4 y K==0 y K==5
    #                             # elegimos 100K
    #                             # activo a nivel bajo: desactivo
    #                             self.tx_txt('DIG:PIN DIO0_N,1') 
    #                             # activo a nivel bajo: desactivo
    #                             self.tx_txt('DIG:PIN DIO1_N,1')
    #                             # activo a nivel alto: activo            
    #                             self.tx_txt('DIG:PIN DIO2_N,1')
    #                             # activo a nivel alto: desactivo                
    #                             self.tx_txt('DIG:PIN DIO3_N,0')
             

    #         #elegimos el cable rojo , conector j1
    #         #activo a nivel bajo: desactivo    
    #         self.tx_txt('DIG:PIN DIO4_N,1')
    #         #activo a nivel alto: activo    
    #         self.tx_txt('DIG:PIN DIO5_N,1')
    #         #activo a nivel alto: desactivo                
    #         self.tx_txt('DIG:PIN DIO6_N,0')
    #         #activo a nivel bajo: desactivo                
    #         self.tx_txt('DIG:PIN DIO7_N,1')

    #         # #elegimos el cable amarillo , conector j3
    #         # #activo a nivel bajo: desactivo    
    #         # self.tx_txt('DIG:PIN DIO4_N,1')
    #         # #activo a nivel alto: desactivo    
    #         # self.tx_txt('DIG:PIN DIO5_N,0')
    #         # #activo a nivel alto: desactivo                
    #         # self.tx_txt('DIG:PIN DIO6_N,0')
    #         # #activo a nivel bajo: activo                
    #         # self.tx_txt('DIG:PIN DIO7_N,0')


    #         # #elegimos el cable verde , conector j2
    #         # #activo a nivel bajo: activo    
    #         # self.tx_txt('DIG:PIN DIO4_N,0')
    #         # #activo a nivel alto: desactivo    
    #         # self.tx_txt('DIG:PIN DIO5_N,0')
    #         # #activo a nivel alto: desactivo                
    #         # self.tx_txt('DIG:PIN DIO6_N,0')
    #         # #activo a nivel bajo: desactivo                
    #         # self.tx_txt('DIG:PIN DIO7_N,1')

    #         # #elegimos el cable azul , conector j4
    #         # #activo a nivel bajo: desactivo    
    #         # self.tx_txt('DIG:PIN DIO4_N,1')
    #         # #activo a nivel alto: desactivo    
    #         # self.tx_txt('DIG:PIN DIO5_N,0')
    #         # #activo a nivel alto: activo                
    #         # self.tx_txt('DIG:PIN DIO6_N,1')
    #         # #activo a nivel bajo: desactivo                
    #         # self.tx_txt('DIG:PIN DIO7_N,1')




    #         #ponemos la resistencia a 1k

    #         # sizeh1=str('-sizeh1={0}'.format(individual[0]))
    #         # sizeh2=str('-sizeh2={0}'.format(individual[1]))
    #         # epochs=str('-epochs={0}'.format(epochs))
    #         # decay=str('-decay={0}'.format(decay_value))
    #         # step=str('-step={0}'.format(learning_step))
    #         # minibatch=str('-batchsize={0}'.format(batchsize))
    #         # idea=str(r_back[epochs, sizeh1,sizeh2, minibatch,decay,step]())
    #         # for line in idea.split("\n"):
    #         #     if "error_val" in line:
    #         #     #print (line.strip())
    #         #        error_rate_float=[float(s) for s in re.findall('\d+\.\d+',line)]
    #         #        error_rate=error_rate_float[0]




    #         self.dv.append_plus("Midiendo Z=R+iX")
    #         iteracion=1
    #         configuracion=0
    #         adquisicion=0
    #         postprocesamiento=0
    #         espera_trigger=0
    #         Z=np.zeros(numero_valores)
    #         PHASE=np.zeros(numero_valores)
    #         Phase_Z_rad=np.zeros(numero_valores)
    #         Phase_U_rad=np.zeros(numero_valores)
    #         Phase_I_rad=np.zeros(numero_valores)
    #         for freq in (self.sd.freq):
    #             t1=pc()
    #             self.tx_txt('GEN:RST')
    #             self.tx_txt('ACQ:RST')
    #             self.tx_txt('ACQ:DATA:UNITS VOLTS')
    #            # self.tx_txt('SOUR1:BURS:STAT BURST') # % Set burst mode to ON
    #            # self.tx_txt('SOUR1:BURS:NCYC 10') # Set 10 pulses of sine wave
            
    #             self.tx_txt('SOUR1:FUNC ' + str(wave_form).upper())
    #             self.tx_txt('SOUR1:VOLT ' + str(ampl))
    #             self.tx_txt('SOUR1:FREQ:FIX ' + str(freq))
    #             ## esta siguiente linea hace que se cuelgue
    #             # self.tx_txt('SOUR1:VOLT:OFFS ' + str(self.sd.def_cfg['nivel_DC']['value'])) # esto lo utilizo para cambiar el offset de canal a
    #             #rp_s.tx_txt('SOUR1:TRIG:SOUR INT')
    #             #rp_s.tx_txt('SOUR1:TRIG:IMM')
    # # esto habrá que borrarlo !!
    #             # self.tx_txt('SOUR2:FUNC ' + str(wave_form).upper())
    #             # self.tx_txt('SOUR2:VOLT ' + str(ampl2[iteracion-1]))
    #             # self.tx_txt('SOUR2:FREQ:FIX ' + str(freq))
    #             # self.tx_txt('SOUR2:BURS:STAT BURST') # % Set burst mode to ON
    #             # self.tx_txt('SOUR2:BURS:NCYC 10') # Set 10 pulses of sine wave     
    #             # self.tx_txt('SOUR2:PHAS ' + str(phases[iteracion-1]))    
    # # hay que borrarlo

    #             self.tx_txt('ACQ:DEC ' + str(decimation[iteracion-1]))
    #             self.tx_txt('ACQ:START')
    #             self.tx_txt('ACQ:TRIG CH1_PE')

    #             self.tx_txt('OUTPUT:STATE ON')  #cuidado con cambiar esto
    #             t2=pc()
    #         # ESPERAMOS EL TRIGGER
    #             # sleep(1)
    #             if self.sd.def_cfg['modelo']['value']==0:
    #                 while freq<100:
    #                     self.tx_txt('ACQ:TRIG:STAT?')
    #                     if self.rx_txt() == 'TD':
    #                         break
    #             else:
    #                 while freq<100:
    #                     self.tx_txt('ACQ:TRIG:FILL?')
    #                     if self.rx_txt() == 'TD':
    #                         break                
    #             t2t=pc()
    #             # self.dv.append_plus('iteracion:'+ str(iteracion))
    #             # self.dv.append_plus('frecuencia:'+ str(freq))
    #             print (iteracion)
    #             print(freq)
    #             sleep(0.2)
    #             self.tx_txt('ACQ:TPOS?')
    #             veamos= self.rx_txt()
    #             posicion_trigger=int(veamos)
    #             # self.dv.append_plus("posicion trigger:" + str(posicion_trigger))
    #             print('posicion trigger:',veamos)
    #             length=fm*(ciclos)/(freq*decimation[iteracion-1])
    #             # print('decimation:',decimation[iteracion-1])
    #             # LEEMOS Y REPRESENTAMOS 1
                

    #             self.tx_txt('ACQ:SOUR1:DATA:STA:N? ' + str(posicion_trigger)+','+ str(length))
                
    #             t3=pc()

    #             buff_string = self.rx_txt()
    #             buff_string = buff_string.strip('{}\n\r').replace("  ", "").split(',')
    #             buff = list(map(float, buff_string))
    #             t4=pc()
    #             my_array = np.asarray(buff)
    #             # super_buffer.append(buff)
    #             # super_buffer_flat=sum(super_buffer, [])

    #             t5=pc()



    #             # LEEMOS Y REPRESENTAMOS2
    #             self.tx_txt('ACQ:SOUR2:DATA:STA:N? ' + str(posicion_trigger)+','+ str(length))
    #             t6=pc()
    #             buff_string = self.rx_txt()
    #             buff_string = buff_string.strip('{}\n\r').replace("  ", "").split(',')
    #             buff = list(map(float, buff_string))
    #             t7=pc()

    #             my_array2 = np.asarray(buff)
    #             dif=my_array-my_array2
    #             #super_buffer2.append(buff)
    #             #super_buffer_flat2=sum(super_buffer2, [])
    #             ## lo hacia con FFT
    #    #         if tipo_Postprocesamiento==1:
    #    #             yf = fft(my_array)
    #    #             yf2 = fft(my_array2)
    #    #             yf3=fft(dif)
    #    #             indice1=np.argmax(np.abs(yf))
    #    #             indice2=np.argmax(np.abs(yf2))
    #    #             indice3=np.argmax(np.abs(yf3))
    # #            # Zq=np.max(np.abs(yf))
    # #               # Zr=np.max(np.abs(yf2))
    # #               # Z[iteracion-1]=np.max(np.abs(yf))/np.max(np.abs(yf2)) #  primera opcion
    # #               #yf_dif=(yf2-yf)
    # #                # indice3=np.argmax(np.abs(yf_dif))            
    # #               ## Z[iteracion-1]=np.max(np.abs(yf_dif))*1000/np.max(np.abs(yf2)) # segunda opcion
    # #                Z[iteracion-1]=np.max(np.abs(yf3))*shunt[R_shunt_k]/np.max(np.abs(yf2))    #tercera opcion         
    # #                PHASE[iteracion-1]=((np.angle(yf2[indice2]/yf[indice1])))*180/np.pi   
                           
    #             # metodo alternativo
    #             T=(1/125e6)*decimation[iteracion-1];           # Sampling time [seconds]                                 # time increment
    #             w_out=freq*2*np.pi

    #             U_dut=dif
    #             I_dut=my_array2/shunt[R_shunt_k]
                
    #             N=int(length)
    #             U_dut_sampled_X=np.zeros(N)
    #             U_dut_sampled_Y=np.zeros(N)
    #             I_dut_sampled_X=np.zeros(N)
    #             I_dut_sampled_Y=np.zeros(N)
    #             dT=np.zeros(N)
    #             # Accurie  signals  U_in_1 and U_in_2 from RedPitaya for N-sampels time and Calculate for Lock in and save in vectors for sampels
    #             for t in range(N):
    #                 U_dut_sampled_X[t]=U_dut[t]*np.sin(t*T*w_out)
    #                 U_dut_sampled_Y[t]=U_dut[t]*np.sin(t*T*w_out-np.pi/2)

    #                 I_dut_sampled_X[t]=I_dut[t]*np.sin(t*T*w_out)
    #                 I_dut_sampled_Y[t]=I_dut[t]*np.sin(t*T*w_out-np.pi/2)
    #                 dT[t]=t*T
    #             # Calculate two components of lock-in for both mesured voltage signals

    #             X_component_lock_in_1=np.trapz(U_dut_sampled_X,x=dT)
    #             Y_component_lock_in_1=np.trapz(U_dut_sampled_Y,dT)

    #             X_component_lock_in_2=np.trapz(I_dut_sampled_X,dT)
    #             Y_component_lock_in_2=np.trapz(I_dut_sampled_Y,dT)

    #             U_dut_amp=(np.sqrt((X_component_lock_in_1)**2+(Y_component_lock_in_1)**2))*2
    #             Phase_U_dut=np.arctan2(Y_component_lock_in_1,X_component_lock_in_1)
    #             Phase_U_rad[iteracion-1]=Phase_U_dut
    #             # Calculate amplitude and angle of I_dut

    #             I_dut_amp=(np.sqrt((X_component_lock_in_2)**2+(Y_component_lock_in_2)**2))*2
    #             Phase_I_dut=np.arctan2(Y_component_lock_in_2,X_component_lock_in_2)
    #             Phase_I_rad[iteracion-1]=Phase_I_dut                
    #             # Calculate amplitude of current trough impedance and amplitude of impedance

    #             Z_amp=(U_dut_amp/I_dut_amp);            # Amplitude of impedance

    #             Z[iteracion-1]=Z_amp

    #             Phase_Z_rad[iteracion-1]=-(Phase_U_dut-Phase_I_dut)
    #             Phase_check=-(Phase_U_dut-Phase_I_dut)*(180/np.pi)
    #             if (Phase_check<=-180):
    #                 Phase_Z=-(Phase_U_dut-Phase_I_dut)*(180/np.pi)+360
    #             else:
    #                 if (Phase_check>=180):
    #                     Phase_Z=-(Phase_U_dut-Phase_I_dut)*(180/np.pi)-360
    #                 else:
    #                     Phase_Z=Phase_check
    #             prefase=Phase_Z*(np.pi)/180

    #             #while prefase>=2*np.pi:
    #             #    prefase=prefase-2*np.pi
    #             PHASE[iteracion-1]=prefase
    #             #PHASE[iteracion-1]=Phase_Z_rad[iteracion-1]
    #             t8=pc()
    #             # N2=my_array2.shape[0]
    #             # T=1/fm
    #             # idea=N//2
    #             # xf2 = fftfreq(N2, T)[:N2//2]
    #             # plot2=plt.figure(2*(iteracion-1)+2)
    #             # plt.plot(xf2, 2.0/N * np.abs(yf2[0:N2//2]))
    #             # plt.plot(xf2, p[0:N2//2])    
    #             # plt.xlabel('Frecuencia')
    #             # plt.grid()
                




    #             iteracion=iteracion+1
    #             self.tx_txt('OUTPUT:STATE OFF')
    #             self.tx_txt('ACQ:STOP')
    #             t9=pc()
    #             postprocesamiento=postprocesamiento+(t5-t4)+(t8-t7)
    #             configuracion=configuracion+(t2-t1)+(t9-t8)+(t6-t5)+(t3-t2t)
    #             adquisicion=adquisicion+(t4-t3)+(t7-t6)  
    #             espera_trigger=espera_trigger+ (t2t-t2)  


    #         # # Service Request instead of using pulling
    #         # event_type = visa.constants.EventType.service_request
    #         # # Mechanism by which we want to be notified
    #         # event_mech = visa.constants.EventMechanism.queue

    #         # self.inst.write('TRGS INT')          # Internal Trigger Source
    #         # self.inst.write('ESNB 1')            # Event_Status_Register[0]=1 // Enables Sweep Completion bit
    #         # self.inst.write('*SRE 4')            # Service Request Enable = 1
    #         # self.inst.write('*CLS')              # Clears Error queue


    #         # self.inst.write('MEAS IRIM')         # Medida de R y X
    #         # self.inst.write('HIDI OFF')          # Muestras la traza inactiva
    #         # self.inst.write('SING')              # Iniciar un barrido único.

    #         # self.dv.append_plus("ACK Instrumento = %s" % self.inst.query('*OPC?'))

    #         # self.inst.enable_event(event_type, event_mech)
    #         #
    #         # #self.dv.append_plus(self.inst.query('*OPC?'))
    #         # # Wait for the event to occur
    #         # response = self.inst.wait_on_event(event_type, 10000)
    #         #
    #         # #if (response.event.event_type == event_type):
    #         #     # response.timed_out = False
    #         # self.inst.disable_event(event_type, event_mech)
    #         # response.timed_out = False

    #         # Recover Measured Data
    #         # self.inst.write('TRAC A')           # Selecciona traza A
    #         # self.inst.write('AUTO')             # Autoescala
    #         # aux_R = np.fromstring(self.inst.query('OUTPDTRC?'), dtype=float, sep=',')

    #         # self.inst.write('TRAC B')           # Selecciona traza A
    #         # self.inst.write('AUTO')             # Autoescala
    #         # aux_X = np.fromstring(self.inst.query('OUTPDTRC?'), dtype=float, sep=',')
    #         t10=pc()
    #         self.sd.R_data = Z*np.cos(PHASE*np.pi/180)
    #         self.sd.X_data = Z*np.sin(PHASE*np.pi/180)

    #         # Compute Err, Eri, Er_mod, Er_fase_data
    #         # First create frequency array based on actual gui conditions
    #         # The freq array will not be changed until next data acquisition even if GUI changes


    #         complex_aux         = self.sd.R_data + self.sd.X_data*1j
    #         self.sd.Z_mod_data  = Z
    #         self.sd.Z_fase_data = PHASE

    #         admitance_aux       = 1./complex_aux
    #         G_data              = np.real(admitance_aux)
    #         Cp_data             = np.imag(admitance_aux)/(2*np.pi*self.sd.freq)
    #         self.sd.Err_data    = Cp_data/self.sd.Co
    #         self.sd.Eri_data    = G_data/(self.sd.Co*(2*np.pi*self.sd.freq));
    #         E_data              = self.sd.Err_data + -1*self.sd.Eri_data*1j;

    #         self.sd.Er_mod_data  = np.abs(E_data);
    #         self.sd.Er_fase_data = np.angle(E_data);
    #         t11=pc()
    #         # # Deactivate BIAS for security reasons
    #         # self.inst.write('DCO OFF')
    #         # self.inst.write('DCRNG M1')
    #         postprocesamiento=postprocesamiento+(t11-t10)
    #         print('espera_trigger:',espera_trigger)
    #         print('configuracion:',configuracion)
    #         print('adquisicion:',adquisicion)
    #         print('postprocesamiento:',postprocesamiento)
    #         total=t11-t0
    #         print ('total:',total)
    #         absolute_val_array = np.abs(self.sd.freq - 1000)
    #         smallest_difference_index = absolute_val_array.argmin()
    #         print ('R_data =', self.sd.R_data[smallest_difference_index])        
    #         print ('X_data=', self.sd.X_data[smallest_difference_index])
    #         print ('resistencia shunt=', shunt[R_shunt_k])
    #         # self.inst.wait_for_srq(self.sd.def_cfg['GPIB_timeout'])
    #         self.dv.append_plus("He finalizado de medir")
    #         self.dv.append_plus("tiempo transcurrido:" + str(total))
    #         #metodo aproximado por contadores, poco estable y un poco mas lento

#nueva version con autoshunt, entrara en modo software

        # Definir la función que se llamará cuando se agote el tiempo
        def handler(signum, frame):
            raise Exception("Timeout")

        # Establecer la función de manejo de la señal
        signal.signal(signal.SIGALRM, handler)

        # Establecer un temporizador de 5 segundos
        signal.alarm(5)
        if (self.sd.def_cfg)['modelo']['value']==1:
            shunt=[90.9,100.0,285.71,500.0,1000.0,2000.0]
            # configuramos la FPGA con diseño verilog propio de DSD
            #este modo debería funcionar para version sin autoshunt

            t0=pc()
            if self.sd.def_cfg['modelo']['value']==0:
                shunt=[90.9,100.0,900.9,1000.0,10000.0,100000.0]
            else:
                shunt=[90.9,100.0,285.71,500.0,1000.0,2000.0]
            


            R_shunt_k = self.sd.def_cfg['shunt']['value'] #elijo 1000 

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
            self.tx_txt('SOUR1:VOLT ' +str(self.sd.def_cfg['vosc']['value']))
        #    self.tx_txt('SOUR1:VOLT:OFFS 0.00') # esto lo utilizo para cambiar el offset de canal b
        #    self.tx_txt('SOUR2:VOLT:OFFS ' + str(self.sd.def_cfg['nivel_DC']['value'])) # esto lo utilizo para cambiar el offset de canal b
         #   self.tx_txt('SOUR1:BURS:NCYC 0')  # solo funciona si led3 esta activado, numero de ciclos por frecuencia
         #   self.tx_txt('SOUR1:BURS:NOR ' +str(muestras_ampliadas)) # solo funciona si led3 esta activado, numero de frecuencias
            # # rp_s.tx_txt('SOUR2:BURS:INT:PER 30') # solo funciona si led3 esta activado, ancho detector
        #    self.tx_txt('SOUR2:BURS:NOR ' +str(umbral_horizontal_detector_cero))
        #    self.tx_txt('SOUR2:BURS:NCYC ' +str(umbral_vertical_detector_cero)) #controlo el numero de ciclos de ancho del deteccor de cero






            self.tx_txt('SOUR1:TRAC:DATA:DATA ' + outStr)
            self.tx_txt('SOUR1:FUNC ARBITRARY')
            #print("he llegado aqui1")
            self.tx_txt('SOUR1:TRAC:DATA:DATA_rafa ' + outStr)
            #print("he llegado aqui2")            
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
            #umbral_horizontal_detector_cero=150*puntos_decada/50

            #umbral_vertical_detector_cero=200*puntos_decada/50     
            umbral_horizontal_detector_cero=0

            umbral_vertical_detector_cero=0        
            procedimiento_fase=2

            #configuramos el shunt
            self.tx_txt('DIG:PIN:DIR OUT,DIO0_N')
            self.tx_txt('DIG:PIN:DIR OUT,DIO1_N')
            self.tx_txt('DIG:PIN:DIR OUT,DIO2_N')
            self.tx_txt('DIG:PIN:DIR OUT,DIO3_N')
            self.tx_txt('DIG:PIN:DIR OUT,DIO4_N')
            self.tx_txt('DIG:PIN:DIR OUT,DIO5_N')
            self.tx_txt('DIG:PIN:DIR OUT,DIO6_N')
            self.tx_txt('DIG:PIN:DIR OUT,DIO7_N')



            if (R_shunt_k==0):
                # elegimos 90.9 
                # activo a nivel bajo: activo
                self.tx_txt('DIG:PIN DIO0_N,0') 
                # activo a nivel bajo: desactivo
                self.tx_txt('DIG:PIN DIO1_N,1')
                # activo a nivel alto: desactivo            
                self.tx_txt('DIG:PIN DIO2_N,0')
                # activo a nivel alto: activo                
                self.tx_txt('DIG:PIN DIO3_N,1')
            else:
                if (R_shunt_k==1):
                    # elegimos 100 
                    # activo a nivel bajo: desactivo
                    self.tx_txt('DIG:PIN DIO0_N,1') 
                    # activo a nivel bajo: desactivo
                    self.tx_txt('DIG:PIN DIO1_N,1')
                    # activo a nivel alto: desactivo            
                    self.tx_txt('DIG:PIN DIO2_N,0')
                    # activo a nivel alto: activo                
                    self.tx_txt('DIG:PIN DIO3_N,1')
                else:
                    if (R_shunt_k==2):
                        # elegimos 900.9 
                        # activo a nivel bajo: activo
                        self.tx_txt('DIG:PIN DIO0_N,0') 
                        # activo a nivel bajo: activo
                        self.tx_txt('DIG:PIN DIO1_N,0')
                        # activo a nivel alto: activo            
                        self.tx_txt('DIG:PIN DIO2_N,1')
                        # activo a nivel alto: desactivo                
                        self.tx_txt('DIG:PIN DIO3_N,0')
                    else:
                        if (R_shunt_k==3):
                            # #elegimos 1K
                            # #activo a nivel bajo: activo
                            self.tx_txt('DIG:PIN DIO0_N,0') 
                            # #activo a nivel bajo: desactivo
                            self.tx_txt('DIG:PIN DIO1_N,1')
                            # #activo a nivel alto: desactivo            
                            self.tx_txt('DIG:PIN DIO2_N,0')
                            # #activo a nivel alto: desactivo                
                            self.tx_txt('DIG:PIN DIO3_N,0')  
                        else:
                            if (R_shunt_k==4):
                                # elegimos 10K
                                # activo a nivel bajo: desactivo
                                self.tx_txt('DIG:PIN DIO0_N,1') 
                                # activo a nivel bajo: activo
                                self.tx_txt('DIG:PIN DIO1_N,0')
                                # activo a nivel alto: desactivo            
                                self.tx_txt('DIG:PIN DIO2_N,0')
                                # activo a nivel alto: desactivo                
                                self.tx_txt('DIG:PIN DIO3_N,0')
                            else:
                                # k==4 y K==0 y K==5
                                # elegimos 100K
                                # activo a nivel bajo: desactivo
                                self.tx_txt('DIG:PIN DIO0_N,1') 
                                # activo a nivel bajo: desactivo
                                self.tx_txt('DIG:PIN DIO1_N,1')
                                # activo a nivel alto: activo            
                                self.tx_txt('DIG:PIN DIO2_N,1')
                                # activo a nivel alto: desactivo                
                                self.tx_txt('DIG:PIN DIO3_N,0')
             

            #elegimos el cable rojo , conector j1
            #activo a nivel bajo: desactivo    
            self.tx_txt('DIG:PIN DIO4_N,1')
            #activo a nivel alto: activo    
            self.tx_txt('DIG:PIN DIO5_N,1')
            #activo a nivel alto: desactivo                
            self.tx_txt('DIG:PIN DIO6_N,0')
            #activo a nivel bajo: desactivo                
            self.tx_txt('DIG:PIN DIO7_N,1')

            # #elegimos el cable amarillo , conector j3
            # #activo a nivel bajo: desactivo    
            # self.tx_txt('DIG:PIN DIO4_N,1')
            # #activo a nivel alto: desactivo    
            # self.tx_txt('DIG:PIN DIO5_N,0')
            # #activo a nivel alto: desactivo                
            # self.tx_txt('DIG:PIN DIO6_N,0')
            # #activo a nivel bajo: activo                
            # self.tx_txt('DIG:PIN DIO7_N,0')


            # #elegimos el cable verde , conector j2
            # #activo a nivel bajo: activo    
            # self.tx_txt('DIG:PIN DIO4_N,0')
            # #activo a nivel alto: desactivo    
            # self.tx_txt('DIG:PIN DIO5_N,0')
            # #activo a nivel alto: desactivo                
            # self.tx_txt('DIG:PIN DIO6_N,0')
            # #activo a nivel bajo: desactivo                
            # self.tx_txt('DIG:PIN DIO7_N,1')

            # #elegimos el cable azul , conector j4
            # #activo a nivel bajo: desactivo    
            # self.tx_txt('DIG:PIN DIO4_N,1')
            # #activo a nivel alto: desactivo    
            # self.tx_txt('DIG:PIN DIO5_N,0')
            # #activo a nivel alto: activo                
            # self.tx_txt('DIG:PIN DIO6_N,1')
            # #activo a nivel bajo: desactivo                
            # self.tx_txt('DIG:PIN DIO7_N,1')

            # muestras=10
            frecuencias=frecuencias[0:muestras]
            muestras_ampliadas=muestras+1
            # configuraciones  varias
            self.tx_txt('SOUR1:VOLT ' +str(self.sd.def_cfg['vosc']['value']))
            self.tx_txt('SOUR1:VOLT:OFFS 0.00') # esto lo utilizo para cambiar el offset de canal b
            self.tx_txt('SOUR2:VOLT:OFFS ' + str(self.sd.def_cfg['nivel_DC']['value'])) # esto lo utilizo para cambiar el offset de canal b
            self.tx_txt('SOUR1:BURS:NCYC ' + str(self.sd.def_cfg['n_ciclos']['value']))  # solo funciona si led3 esta activado, numero de ciclos por frecuencia
            self.tx_txt('SOUR1:BURS:NOR ' +str(muestras_ampliadas)) # solo funciona si led3 esta activado, numero de frecuencias
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
                self.tx_txt('DIG:PIN? DIO'+str(7)+'_P')
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


            smooth=self.sd.def_cfg['smooth']['value']
            k=self.sd.def_cfg['k_factor']['value']


            #Enable output
            iteracion=1
            # ZA=interp1d(frecuencias[0:muestras],my_array[0:muestras])
            # ZB=interp1d(frecuencias,my_array[256: 256+225])
            # Z=(ZA(frecuencias))*shunt[R_shunt_k]/32
            Z_sin_comprimir=(my_array[0:muestras]*shunt[R_shunt_k])/16
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
            Phase_escalada=-my_array2[0:muestras]/2 # porque las fases las calculo multiplicads por 2
            #Phase_radianes=Phase_escalada*np.pi           
            #Phase_check=Phase_radianes*360/(2*np.pi)

            Phase_radianes=Phase_escalada*np.pi/180           
            Phase_check=Phase_escalada            
            PHASE_sin_comprimir_grados=np.zeros(muestras)
            for fases in range(len(Phase_check)):
                if (Phase_check[fases]<=-90):
                    PHASE_sin_comprimir_grados[fases]=Phase_check[fases]+180
                else:
                    if (Phase_check[fases] >=90):
                        PHASE_sin_comprimir_grados[fases]=Phase_check[fases]-180
                    else:
                        PHASE_sin_comprimir_grados[fases]=Phase_check[fases]                
            # PHASE=my_array[256: 256+225]*frecuencias*360/125e6
            # PHASE= Phase_check
            PHASE_sin_comprimir=PHASE_sin_comprimir_grados*np.pi/180
            PHASE=np.ma.masked_where((Z_sin_comprimir==0),PHASE_sin_comprimir) 
            self.sd.freq=np.ma.masked_where((Z_sin_comprimir==0),frecuencias) 
            Z = np.ma.masked_where((Z_sin_comprimir==0),Z_sin_comprimir) 

            prePHASE=PHASE.compressed()
            self.sd.freq=self.sd.freq.compressed()
            preZ = Z.compressed()

                        # ahora aplico una forma de smooth; pero mejor hacerlo en la imagen , no sobre los datos
            # if (smooth==0):
            #     PHASE = np.cumsum(prePHASE, dtype=float)
            #     Z=np.cumsum(preZ, dtype=float)
            #     PHASE[k:] = PHASE[k:] - PHASE[:-k]
            #     Z[k:] = Z[k:] - Z[:-k]
            #     PHASE=PHASE[k - 1:] / k

            #     Z=Z[k - 1:] / k
            #     self.sd.freq=self.sd.freq[k-1:]
            # else:
            #     PHASE=prePHASE
            # # self.sd.freq=frecuencias
            #     Z = preZ

            PHASE=prePHASE
            Z=preZ

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
            absolute_val_array = np.abs(self.sd.freq - 1000)
            smallest_difference_index = absolute_val_array.argmin()
            print ('R_data =', self.sd.R_data[smallest_difference_index])        
            print ('X_data=', self.sd.X_data[smallest_difference_index])
            print ('resistencia shunt=', shunt[R_shunt_k])
            self.dv.append_plus("He finalizado de medir")
            self.dv.append_plus("tiempo transcurrido:" + str(total))  
            self.dv.append_plus("R_data ="+ str(self.sd.R_data[smallest_difference_index]))
            self.dv.append_plus("X_data ="+ str(self.sd.X_data[smallest_difference_index]))
            self.dv.append_plus("resistencia shunt ="+ str(shunt[R_shunt_k]))         

        else: #con esto cubrimos el modelo 2 (7020 con autoshunt) y el modelo 0 (7010)

            if (self.sd.def_cfg['post_procesado']['value']==0):
                # configuramos la FPGA con diseño verilog propio de DSD
                # adaptado para el autoshunt

                t0=pc()
                if self.sd.def_cfg['modelo']['value']==0:
                    shunt=[90.9,100.0,900.9,1000.0,10000.0,100000.0]
                else:
                    shunt=[90.9,100.0,285.71,500.0,1000.0,2000.0]
                


                R_shunt_k = self.sd.def_cfg['shunt']['value'] #elijo 1000 

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
                    
                try:
                    self.tx_txt('DIG:PIN LED'+str(1)+','+str(0))  # 1->state2  0->state1
                except BrokenPipeError:
                    print("Broken pipe error occurred.")
                    self.dv.append_plus("Algo pasa con la conexión")
                    error=1
                #recortamos a 40 Hz
                else:
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
                    self.tx_txt('SOUR1:VOLT ' +str(self.sd.def_cfg['vosc']['value']))
                #    self.tx_txt('SOUR1:VOLT:OFFS 0.00') # esto lo utilizo para cambiar el offset de canal b
                #    self.tx_txt('SOUR2:VOLT:OFFS ' + str(self.sd.def_cfg['nivel_DC']['value'])) # esto lo utilizo para cambiar el offset de canal b
                #   self.tx_txt('SOUR1:BURS:NCYC 0')  # solo funciona si led3 esta activado, numero de ciclos por frecuencia
                #   self.tx_txt('SOUR1:BURS:NOR ' +str(muestras_ampliadas)) # solo funciona si led3 esta activado, numero de frecuencias
                    # # rp_s.tx_txt('SOUR2:BURS:INT:PER 30') # solo funciona si led3 esta activado, ancho detector
                #    self.tx_txt('SOUR2:BURS:NOR ' +str(umbral_horizontal_detector_cero))
                #    self.tx_txt('SOUR2:BURS:NCYC ' +str(umbral_vertical_detector_cero)) #controlo el numero de ciclos de ancho del deteccor de cero






                    #self.tx_txt('SOUR1:TRAC:DATA:DATA ' + outStr)
                    self.tx_txt('SOUR1:FUNC ARBITRARY')
                    #print("he llegado aqui1")
                    self.tx_txt('SOUR1:TRAC:DATA:DATA_rafa ' + outStr)
                    #print("he llegado aqui2")            
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
                    #umbral_horizontal_detector_cero=150*puntos_decada/50

                    #umbral_vertical_detector_cero=200*puntos_decada/50     
                    umbral_horizontal_detector_cero=0

                    umbral_vertical_detector_cero=0        
                    procedimiento_fase=2

                    #configuramos el shunt
                    self.tx_txt('DIG:PIN:DIR OUT,DIO0_N')
                    self.tx_txt('DIG:PIN:DIR OUT,DIO1_N')
                    self.tx_txt('DIG:PIN:DIR OUT,DIO2_N')
                    self.tx_txt('DIG:PIN:DIR OUT,DIO3_N')
                    self.tx_txt('DIG:PIN:DIR OUT,DIO4_N')
                    self.tx_txt('DIG:PIN:DIR OUT,DIO5_N')
                    self.tx_txt('DIG:PIN:DIR OUT,DIO6_N')
                    self.tx_txt('DIG:PIN:DIR OUT,DIO7_N')



                    # if (R_shunt_k==0):
                    #     # elegimos 90.9 
                    #     # activo a nivel bajo: activo
                    #     self.tx_txt('DIG:PIN DIO0_N,0') 
                    #     # activo a nivel bajo: desactivo
                    #     self.tx_txt('DIG:PIN DIO1_N,1')
                    #     # activo a nivel alto: desactivo            
                    #     self.tx_txt('DIG:PIN DIO2_N,0')
                    #     # activo a nivel alto: activo                
                    #     self.tx_txt('DIG:PIN DIO3_N,1')
                    # else:
                    #     if (R_shunt_k==1):
                    #         # elegimos 100 
                    #         # activo a nivel bajo: desactivo
                    #         self.tx_txt('DIG:PIN DIO0_N,1') 
                    #         # activo a nivel bajo: desactivo
                    #         self.tx_txt('DIG:PIN DIO1_N,1')
                    #         # activo a nivel alto: desactivo            
                    #         self.tx_txt('DIG:PIN DIO2_N,0')
                    #         # activo a nivel alto: activo                
                    #         self.tx_txt('DIG:PIN DIO3_N,1')
                    #     else:
                    #         if (R_shunt_k==2):
                    #             # elegimos 900.9 
                    #             # activo a nivel bajo: activo
                    #             self.tx_txt('DIG:PIN DIO0_N,0') 
                    #             # activo a nivel bajo: activo
                    #             self.tx_txt('DIG:PIN DIO1_N,0')
                    #             # activo a nivel alto: activo            
                    #             self.tx_txt('DIG:PIN DIO2_N,1')
                    #             # activo a nivel alto: desactivo                
                    #             self.tx_txt('DIG:PIN DIO3_N,0')
                    #         else:
                    #             if (R_shunt_k==3):
                    #                 # #elegimos 1K
                    #                 # #activo a nivel bajo: activo
                    #                 self.tx_txt('DIG:PIN DIO0_N,0') 
                    #                 # #activo a nivel bajo: desactivo
                    #                 self.tx_txt('DIG:PIN DIO1_N,1')
                    #                 # #activo a nivel alto: desactivo            
                    #                 self.tx_txt('DIG:PIN DIO2_N,0')
                    #                 # #activo a nivel alto: desactivo                
                    #                 self.tx_txt('DIG:PIN DIO3_N,0')  
                    #             else:
                    #                 if (R_shunt_k==4):
                    #                     # elegimos 10K
                    #                     # activo a nivel bajo: desactivo
                    #                     self.tx_txt('DIG:PIN DIO0_N,1') 
                    #                     # activo a nivel bajo: activo
                    #                     self.tx_txt('DIG:PIN DIO1_N,0')
                    #                     # activo a nivel alto: desactivo            
                    #                     self.tx_txt('DIG:PIN DIO2_N,0')
                    #                     # activo a nivel alto: desactivo                
                    #                     self.tx_txt('DIG:PIN DIO3_N,0')
                    #                 else:
                    #                     # k==4 y K==0 y K==5
                    #                     # elegimos 100K
                    #                     # activo a nivel bajo: desactivo
                    #                     self.tx_txt('DIG:PIN DIO0_N,1') 
                    #                     # activo a nivel bajo: desactivo
                    #                     self.tx_txt('DIG:PIN DIO1_N,1')
                    #                     # activo a nivel alto: activo            
                    #                     self.tx_txt('DIG:PIN DIO2_N,1')
                    #                     # activo a nivel alto: desactivo                
                    #                     self.tx_txt('DIG:PIN DIO3_N,0')
                    

                    #elegimos el cable rojo , conector j1
                    #activo a nivel bajo: desactivo    
                    self.tx_txt('DIG:PIN DIO4_N,1')
                    #activo a nivel alto: activo    
                    self.tx_txt('DIG:PIN DIO5_N,1')
                    #activo a nivel alto: desactivo                
                    self.tx_txt('DIG:PIN DIO6_N,0')
                    #activo a nivel bajo: desactivo                
                    self.tx_txt('DIG:PIN DIO7_N,1')

                    # #elegimos el cable amarillo , conector j3
                    # #activo a nivel bajo: desactivo    
                    # self.tx_txt('DIG:PIN DIO4_N,1')
                    # #activo a nivel alto: desactivo    
                    # self.tx_txt('DIG:PIN DIO5_N,0')
                    # #activo a nivel alto: desactivo                
                    # self.tx_txt('DIG:PIN DIO6_N,0')
                    # #activo a nivel bajo: activo                
                    # self.tx_txt('DIG:PIN DIO7_N,0')


                    # #elegimos el cable verde , conector j2
                    # #activo a nivel bajo: activo    
                    # self.tx_txt('DIG:PIN DIO4_N,0')
                    # #activo a nivel alto: desactivo    
                    # self.tx_txt('DIG:PIN DIO5_N,0')
                    # #activo a nivel alto: desactivo                
                    # self.tx_txt('DIG:PIN DIO6_N,0')
                    # #activo a nivel bajo: desactivo                
                    # self.tx_txt('DIG:PIN DIO7_N,1')

                    # #elegimos el cable azul , conector j4
                    # #activo a nivel bajo: desactivo    
                    # self.tx_txt('DIG:PIN DIO4_N,1')
                    # #activo a nivel alto: desactivo    
                    # self.tx_txt('DIG:PIN DIO5_N,0')
                    # #activo a nivel alto: activo                
                    # self.tx_txt('DIG:PIN DIO6_N,1')
                    # #activo a nivel bajo: desactivo                
                    # self.tx_txt('DIG:PIN DIO7_N,1')

                    # muestras=10
                    frecuencias=frecuencias[0:muestras]
                    muestras_ampliadas=muestras+1
                    # configuraciones  varias
                    self.tx_txt('SOUR1:VOLT ' +str(self.sd.def_cfg['vosc']['value']))
                    self.tx_txt('SOUR1:VOLT:OFFS 0.00') # esto lo utilizo para cambiar el offset de canal b
                    self.tx_txt('SOUR2:VOLT:OFFS ' + str(self.sd.def_cfg['nivel_DC']['value'])) # esto lo utilizo para cambiar el offset de canal b
                    self.tx_txt('SOUR1:BURS:NCYC ' + str(self.sd.def_cfg['n_ciclos']['value']))  # solo funciona si led3 esta activado, numero de ciclos por frecuencia
                    self.tx_txt('SOUR1:BURS:NOR ' +str(muestras_ampliadas)) # solo funciona si led3 esta activado, numero de frecuencias
                    # # rp_s.tx_txt('SOUR2:BURS:INT:PER 30') # solo funciona si led3 esta activado, ancho detector
                    self.tx_txt('SOUR2:BURS:NOR ' +str(umbral_horizontal_detector_cero))
                    self.tx_txt('SOUR2:BURS:NCYC ' +str(umbral_vertical_detector_cero)) #controlo el numero de ciclos de ancho del deteccor de cero


                    self.tx_txt('DIG:PIN LED'+str(2)+','+str(procedimiento_fase))  # desbloqueo finalizacion state1, tambien genera inicio
                    self.tx_txt('DIG:PIN LED'+str(3)+','+str(1))  #activacion del led3 absolutamente necesario para que el numero de ciclos sea configurable y el numero de frecuencias y los umbrales


                    self.dv.append_plus("Midiendo Z=R+iX")
                    t1=pc()
                    self.tx_txt('CHIRP ON')
                    try:
                        while 1 :
                            #    rp_s.tx_txt('FIN:RAF:STAT? 1')
                            self.tx_txt('DIG:PIN? DIO'+str(7)+'_P')
                            state = self.rx_txt()
                            if state == '1':
                                break
                    except Exception as e:
                        print(e)
                        error=1
                    # Cancelar el temporizador
                    signal.alarm(0)                
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


                    smooth=self.sd.def_cfg['smooth']['value']
                    k=self.sd.def_cfg['k_factor']['value']


                    #Enable output
                    iteracion=1
                    # ZA=interp1d(frecuencias[0:muestras],my_array[0:muestras])
                    # ZB=interp1d(frecuencias,my_array[256: 256+225])
                    # Z=(ZA(frecuencias))*shunt[R_shunt_k]/32
                    ## solucion con shunt fija
                    #Z_sin_comprimir=(my_array[0:muestras]*shunt[R_shunt_k])/16

                    idea1=(my_array[20]*shunt[4])/16  -(my_array[19]*shunt[5])/16
                    idea2=(my_array[70]*shunt[3])/16  -(my_array[69]*shunt[4])/16
                    idea3=(my_array[120]*shunt[2])/16  -(my_array[119]*shunt[3])/16
                    idea4=(my_array[170]*shunt[1])/16  -(my_array[169]*shunt[2])/16

                    # idea1=0
                    # idea2=0
                    # idea3=0
                    # idea4=0
                    # Z_sin_comprimir = np.array([(val*shunt[5])/16+idea1 if i < 20 
                    #                 else (val*shunt[4])/16  if 20 <= i < 70 
                    #                 else (val*shunt[3])/16 -idea2 if 70 <= i < 120 
                    #                 else (val*shunt[2])/16  if 120 <= i < 170 
                    #                 else (val*shunt[1])/16 -idea4 
                    #                 for i, val in enumerate(my_array[0:muestras])])
                    Z_sin_comprimir = np.array([(val*shunt[5])/16 if i < 20 
                                    else (val*shunt[4])/16 -idea1 if 20 <= i < 70 
                                    else (val*shunt[3])/16 -idea2-idea1 if 70 <= i < 120 
                                    else (val*shunt[2])/16  -idea1-idea2-idea3 if 120 <= i < 170 
                                    else (val*shunt[1])/16 -idea1-idea2-idea3-idea4
                                    for i, val in enumerate(my_array[0:muestras])])            
                    
                    from scipy.interpolate import CubicSpline,PchipInterpolator,UnivariateSpline

                    # Identificar los índices de los escalones
                    step_indices = [20, 70, 120, 170]

                    # Identificar los valores en los índices de los escalones
                    step_values = [Z_sin_comprimir[i] for i in step_indices]

                    # Crear una función de interpolación
                    # interp_func = np.interp(np.arange(muestras), step_indices, step_values)
                    # Crear una función de interpolación spline cúbica
                    spline_func = PchipInterpolator(step_indices, step_values)            

                    # Aplicar la función de interpolación a todo el array
                    # Z_sin_comprimir2 = interp_func
                    Z_sin_comprimir2 = spline_func(np.arange(muestras))
                    from scipy.signal import savgol_filter

                    # Definir el tamaño de la ventana y el grado del polinomio
                    window_size = 11
                    poly_degree = 3

                    # Aplicar el filtro Savitzky-Golay
                    Z_sin_comprimir_3 = savgol_filter(Z_sin_comprimir2, window_size, poly_degree)

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
                    Phase_escalada=-my_array2[0:muestras]/2 # porque las fases las calculo multiplicads por 2
                    #Phase_radianes=Phase_escalada*np.pi           
                    #Phase_check=Phase_radianes*360/(2*np.pi)

                    Phase_radianes=Phase_escalada*np.pi/180           
                    Phase_check=Phase_escalada            
                    PHASE_sin_comprimir_grados=np.zeros(muestras)
                    for fases in range(len(Phase_check)):
                        if (Phase_check[fases]<=-90):
                            PHASE_sin_comprimir_grados[fases]=Phase_check[fases]+180
                        else:
                            if (Phase_check[fases] >=90):
                                PHASE_sin_comprimir_grados[fases]=Phase_check[fases]-180
                            else:
                                PHASE_sin_comprimir_grados[fases]=Phase_check[fases]                
                    # PHASE=my_array[256: 256+225]*frecuencias*360/125e6
                    # PHASE= Phase_check
                    PHASE_sin_comprimir=PHASE_sin_comprimir_grados*np.pi/180
                    PHASE=np.ma.masked_where((Z_sin_comprimir==0.0),PHASE_sin_comprimir) 
                    self.sd.freq=np.ma.masked_where((Z_sin_comprimir==0.0),frecuencias) 
                    Z = np.ma.masked_where((Z_sin_comprimir==0.0),Z_sin_comprimir) 

                    ##ATENCION NO HAGO NINGUNA INTERPOLACION DE LOS DATOS, SOLO LOS COMPRIMO

                    prePHASE=PHASE.compressed()
                    self.sd.freq=self.sd.freq.compressed()
                    preZ = Z.compressed()

                                # ahora aplico una forma de smooth; pero mejor hacerlo en la imagen , no sobre los datos
                    # if (smooth==0):
                    #     PHASE = np.cumsum(prePHASE, dtype=float)
                    #     Z=np.cumsum(preZ, dtype=float)
                    #     PHASE[k:] = PHASE[k:] - PHASE[:-k]
                    #     Z[k:] = Z[k:] - Z[:-k]
                    #     PHASE=PHASE[k - 1:] / k

                    #     Z=Z[k - 1:] / k
                    #     self.sd.freq=self.sd.freq[k-1:]
                    # else:
                    #     PHASE=prePHASE
                    # # self.sd.freq=frecuencias
                    #     Z = preZ

                    PHASE=prePHASE
                    Z=preZ

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
                    absolute_val_array = np.abs(self.sd.freq - 1000)
                    smallest_difference_index = absolute_val_array.argmin()
                    print ('R_data =', self.sd.R_data[smallest_difference_index])        
                    print ('X_data=', self.sd.X_data[smallest_difference_index])
                    print ('resistencia shunt=', shunt[R_shunt_k])
                    self.dv.append_plus("He finalizado de medir")
                    self.dv.append_plus("tiempo transcurrido:" + str(total))  
                    self.dv.append_plus("R_data ="+ str(self.sd.R_data[smallest_difference_index]))
                    self.dv.append_plus("X_data ="+ str(self.sd.X_data[smallest_difference_index]))
                    self.dv.append_plus("resistencia shunt ="+ str(shunt[R_shunt_k]))         
            

            elif (self.sd.def_cfg['post_procesado']['value']==1):
               # configuramos la FPGA con diseño verilog propio de DSD
                # adaptado para el autoshunt

                t0=pc()
                if self.sd.def_cfg['modelo']['value']==0:
                    shunt=[90.9,100.0,900.9,1000.0,10000.0,100000.0]
                else:
                    shunt=[90.9,100.0,285.71,500.0,1000.0,2000.0]
                


                R_shunt_k = self.sd.def_cfg['shunt']['value'] #elijo 1000 

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
                    
                try:
                    self.tx_txt('DIG:PIN LED'+str(1)+','+str(0))  # 1->state2  0->state1
                except BrokenPipeError:
                    print("Broken pipe error occurred.")
                    self.dv.append_plus("Algo pasa con la conexión")
                    error=1
                #recortamos a 40 Hz
                else:
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
                    self.tx_txt('SOUR1:VOLT ' +str(self.sd.def_cfg['vosc']['value']))
                #    self.tx_txt('SOUR1:VOLT:OFFS 0.00') # esto lo utilizo para cambiar el offset de canal b
                #    self.tx_txt('SOUR2:VOLT:OFFS ' + str(self.sd.def_cfg['nivel_DC']['value'])) # esto lo utilizo para cambiar el offset de canal b
                #   self.tx_txt('SOUR1:BURS:NCYC 0')  # solo funciona si led3 esta activado, numero de ciclos por frecuencia
                #   self.tx_txt('SOUR1:BURS:NOR ' +str(muestras_ampliadas)) # solo funciona si led3 esta activado, numero de frecuencias
                    # # rp_s.tx_txt('SOUR2:BURS:INT:PER 30') # solo funciona si led3 esta activado, ancho detector
                #    self.tx_txt('SOUR2:BURS:NOR ' +str(umbral_horizontal_detector_cero))
                #    self.tx_txt('SOUR2:BURS:NCYC ' +str(umbral_vertical_detector_cero)) #controlo el numero de ciclos de ancho del deteccor de cero






                    #self.tx_txt('SOUR1:TRAC:DATA:DATA ' + outStr)
                    self.tx_txt('SOUR1:FUNC ARBITRARY')
                    #print("he llegado aqui1")
                    self.tx_txt('SOUR1:TRAC:DATA:DATA_rafa ' + outStr)
                    #print("he llegado aqui2")            
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
                    #umbral_horizontal_detector_cero=150*puntos_decada/50

                    #umbral_vertical_detector_cero=200*puntos_decada/50     
                    umbral_horizontal_detector_cero=0

                    umbral_vertical_detector_cero=0        
                    procedimiento_fase=2

                    #configuramos el shunt
                    self.tx_txt('DIG:PIN:DIR OUT,DIO0_N')
                    self.tx_txt('DIG:PIN:DIR OUT,DIO1_N')
                    self.tx_txt('DIG:PIN:DIR OUT,DIO2_N')
                    self.tx_txt('DIG:PIN:DIR OUT,DIO3_N')
                    self.tx_txt('DIG:PIN:DIR OUT,DIO4_N')
                    self.tx_txt('DIG:PIN:DIR OUT,DIO5_N')
                    self.tx_txt('DIG:PIN:DIR OUT,DIO6_N')
                    self.tx_txt('DIG:PIN:DIR OUT,DIO7_N')



                    # if (R_shunt_k==0):
                    #     # elegimos 90.9 
                    #     # activo a nivel bajo: activo
                    #     self.tx_txt('DIG:PIN DIO0_N,0') 
                    #     # activo a nivel bajo: desactivo
                    #     self.tx_txt('DIG:PIN DIO1_N,1')
                    #     # activo a nivel alto: desactivo            
                    #     self.tx_txt('DIG:PIN DIO2_N,0')
                    #     # activo a nivel alto: activo                
                    #     self.tx_txt('DIG:PIN DIO3_N,1')
                    # else:
                    #     if (R_shunt_k==1):
                    #         # elegimos 100 
                    #         # activo a nivel bajo: desactivo
                    #         self.tx_txt('DIG:PIN DIO0_N,1') 
                    #         # activo a nivel bajo: desactivo
                    #         self.tx_txt('DIG:PIN DIO1_N,1')
                    #         # activo a nivel alto: desactivo            
                    #         self.tx_txt('DIG:PIN DIO2_N,0')
                    #         # activo a nivel alto: activo                
                    #         self.tx_txt('DIG:PIN DIO3_N,1')
                    #     else:
                    #         if (R_shunt_k==2):
                    #             # elegimos 900.9 
                    #             # activo a nivel bajo: activo
                    #             self.tx_txt('DIG:PIN DIO0_N,0') 
                    #             # activo a nivel bajo: activo
                    #             self.tx_txt('DIG:PIN DIO1_N,0')
                    #             # activo a nivel alto: activo            
                    #             self.tx_txt('DIG:PIN DIO2_N,1')
                    #             # activo a nivel alto: desactivo                
                    #             self.tx_txt('DIG:PIN DIO3_N,0')
                    #         else:
                    #             if (R_shunt_k==3):
                    #                 # #elegimos 1K
                    #                 # #activo a nivel bajo: activo
                    #                 self.tx_txt('DIG:PIN DIO0_N,0') 
                    #                 # #activo a nivel bajo: desactivo
                    #                 self.tx_txt('DIG:PIN DIO1_N,1')
                    #                 # #activo a nivel alto: desactivo            
                    #                 self.tx_txt('DIG:PIN DIO2_N,0')
                    #                 # #activo a nivel alto: desactivo                
                    #                 self.tx_txt('DIG:PIN DIO3_N,0')  
                    #             else:
                    #                 if (R_shunt_k==4):
                    #                     # elegimos 10K
                    #                     # activo a nivel bajo: desactivo
                    #                     self.tx_txt('DIG:PIN DIO0_N,1') 
                    #                     # activo a nivel bajo: activo
                    #                     self.tx_txt('DIG:PIN DIO1_N,0')
                    #                     # activo a nivel alto: desactivo            
                    #                     self.tx_txt('DIG:PIN DIO2_N,0')
                    #                     # activo a nivel alto: desactivo                
                    #                     self.tx_txt('DIG:PIN DIO3_N,0')
                    #                 else:
                    #                     # k==4 y K==0 y K==5
                    #                     # elegimos 100K
                    #                     # activo a nivel bajo: desactivo
                    #                     self.tx_txt('DIG:PIN DIO0_N,1') 
                    #                     # activo a nivel bajo: desactivo
                    #                     self.tx_txt('DIG:PIN DIO1_N,1')
                    #                     # activo a nivel alto: activo            
                    #                     self.tx_txt('DIG:PIN DIO2_N,1')
                    #                     # activo a nivel alto: desactivo                
                    #                     self.tx_txt('DIG:PIN DIO3_N,0')
                    

                    #elegimos el cable rojo , conector j1
                    #activo a nivel bajo: desactivo    
                    self.tx_txt('DIG:PIN DIO4_N,1')
                    #activo a nivel alto: activo    
                    self.tx_txt('DIG:PIN DIO5_N,1')
                    #activo a nivel alto: desactivo                
                    self.tx_txt('DIG:PIN DIO6_N,0')
                    #activo a nivel bajo: desactivo                
                    self.tx_txt('DIG:PIN DIO7_N,1')

                    # #elegimos el cable amarillo , conector j3
                    # #activo a nivel bajo: desactivo    
                    # self.tx_txt('DIG:PIN DIO4_N,1')
                    # #activo a nivel alto: desactivo    
                    # self.tx_txt('DIG:PIN DIO5_N,0')
                    # #activo a nivel alto: desactivo                
                    # self.tx_txt('DIG:PIN DIO6_N,0')
                    # #activo a nivel bajo: activo                
                    # self.tx_txt('DIG:PIN DIO7_N,0')


                    # #elegimos el cable verde , conector j2
                    # #activo a nivel bajo: activo    
                    # self.tx_txt('DIG:PIN DIO4_N,0')
                    # #activo a nivel alto: desactivo    
                    # self.tx_txt('DIG:PIN DIO5_N,0')
                    # #activo a nivel alto: desactivo                
                    # self.tx_txt('DIG:PIN DIO6_N,0')
                    # #activo a nivel bajo: desactivo                
                    # self.tx_txt('DIG:PIN DIO7_N,1')

                    # #elegimos el cable azul , conector j4
                    # #activo a nivel bajo: desactivo    
                    # self.tx_txt('DIG:PIN DIO4_N,1')
                    # #activo a nivel alto: desactivo    
                    # self.tx_txt('DIG:PIN DIO5_N,0')
                    # #activo a nivel alto: activo                
                    # self.tx_txt('DIG:PIN DIO6_N,1')
                    # #activo a nivel bajo: desactivo                
                    # self.tx_txt('DIG:PIN DIO7_N,1')

                    # muestras=10
                    frecuencias=frecuencias[0:muestras]
                    muestras_ampliadas=muestras+1
                    # configuraciones  varias
                    self.tx_txt('SOUR1:VOLT ' +str(self.sd.def_cfg['vosc']['value']))
                    self.tx_txt('SOUR1:VOLT:OFFS 0.00') # esto lo utilizo para cambiar el offset de canal b
                    self.tx_txt('SOUR2:VOLT:OFFS ' + str(self.sd.def_cfg['nivel_DC']['value'])) # esto lo utilizo para cambiar el offset de canal b
                    self.tx_txt('SOUR1:BURS:NCYC ' + str(self.sd.def_cfg['n_ciclos']['value']))  # solo funciona si led3 esta activado, numero de ciclos por frecuencia
                    self.tx_txt('SOUR1:BURS:NOR ' +str(muestras_ampliadas)) # solo funciona si led3 esta activado, numero de frecuencias
                    # # rp_s.tx_txt('SOUR2:BURS:INT:PER 30') # solo funciona si led3 esta activado, ancho detector
                    self.tx_txt('SOUR2:BURS:NOR ' +str(umbral_horizontal_detector_cero))
                    self.tx_txt('SOUR2:BURS:NCYC ' +str(umbral_vertical_detector_cero)) #controlo el numero de ciclos de ancho del deteccor de cero


                    self.tx_txt('DIG:PIN LED'+str(2)+','+str(procedimiento_fase))  # desbloqueo finalizacion state1, tambien genera inicio
                    self.tx_txt('DIG:PIN LED'+str(3)+','+str(1))  #activacion del led3 absolutamente necesario para que el numero de ciclos sea configurable y el numero de frecuencias y los umbrales


                    self.dv.append_plus("Midiendo Z=R+iX")
                    t1=pc()
                    self.tx_txt('CHIRP ON')
                    try:
                        while 1 :
                            #    rp_s.tx_txt('FIN:RAF:STAT? 1')
                            self.tx_txt('DIG:PIN? DIO'+str(7)+'_P')
                            state = self.rx_txt()
                            if state == '1':
                                break
                    except Exception as e:
                        print(e)
                        error=1
                    # Cancelar el temporizador
                    signal.alarm(0)                
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


                    smooth=self.sd.def_cfg['smooth']['value']
                    k=self.sd.def_cfg['k_factor']['value']


                    #Enable output
                    iteracion=1
                    # ZA=interp1d(frecuencias[0:muestras],my_array[0:muestras])
                    # ZB=interp1d(frecuencias,my_array[256: 256+225])
                    # Z=(ZA(frecuencias))*shunt[R_shunt_k]/32
                    ## solucion con shunt fija
                    #Z_sin_comprimir=(my_array[0:muestras]*shunt[R_shunt_k])/16

                    idea1=(my_array[20]*shunt[4])/16  -(my_array[19]*shunt[5])/16
                    idea2=(my_array[70]*shunt[3])/16  -(my_array[69]*shunt[4])/16
                    idea3=(my_array[120]*shunt[2])/16  -(my_array[119]*shunt[3])/16
                    idea4=(my_array[170]*shunt[1])/16  -(my_array[169]*shunt[2])/16

                    # idea1=0
                    # idea2=0
                    # idea3=0
                    # idea4=0
                    Z_sin_comprimir = np.array([(val*shunt[5])/16+idea1 if i < 20 
                                    else (val*shunt[4])/16  if 20 <= i < 70 
                                    else (val*shunt[3])/16 -idea2 if 70 <= i < 120 
                                    else (val*shunt[2])/16  if 120 <= i < 170 
                                    else (val*shunt[1])/16 -idea4 
                                    for i, val in enumerate(my_array[0:muestras])])
                    # Z_sin_comprimir = np.array([(val*shunt[5])/16 if i < 20 
                    #                 else (val*shunt[4])/16 -idea1 if 20 <= i < 70 
                    #                 else (val*shunt[3])/16 -idea2-idea1 if 70 <= i < 120 
                    #                 else (val*shunt[2])/16  -idea1-idea2-idea3 if 120 <= i < 170 
                    #                 else (val*shunt[1])/16 -idea1-idea2-idea3-idea4
                    #                 for i, val in enumerate(my_array[0:muestras])])            
                    
                    from scipy.interpolate import CubicSpline,PchipInterpolator,UnivariateSpline

                    # Identificar los índices de los escalones
                    step_indices = [20, 70, 120, 170]

                    # Identificar los valores en los índices de los escalones
                    step_values = [Z_sin_comprimir[i] for i in step_indices]

                    # Crear una función de interpolación
                    # interp_func = np.interp(np.arange(muestras), step_indices, step_values)
                    # Crear una función de interpolación spline cúbica
                    spline_func = PchipInterpolator(step_indices, step_values)            

                    # Aplicar la función de interpolación a todo el array
                    # Z_sin_comprimir2 = interp_func
                    Z_sin_comprimir2 = spline_func(np.arange(muestras))
                    from scipy.signal import savgol_filter

                    # Definir el tamaño de la ventana y el grado del polinomio
                    window_size = 11
                    poly_degree = 3

                    # Aplicar el filtro Savitzky-Golay
                    Z_sin_comprimir_3 = savgol_filter(Z_sin_comprimir2, window_size, poly_degree)

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
                    Phase_escalada=-my_array2[0:muestras]/2 # porque las fases las calculo multiplicads por 2
                    #Phase_radianes=Phase_escalada*np.pi           
                    #Phase_check=Phase_radianes*360/(2*np.pi)

                    Phase_radianes=Phase_escalada*np.pi/180           
                    Phase_check=Phase_escalada            
                    PHASE_sin_comprimir_grados=np.zeros(muestras)
                    for fases in range(len(Phase_check)):
                        if (Phase_check[fases]<=-90):
                            PHASE_sin_comprimir_grados[fases]=Phase_check[fases]+180
                        else:
                            if (Phase_check[fases] >=90):
                                PHASE_sin_comprimir_grados[fases]=Phase_check[fases]-180
                            else:
                                PHASE_sin_comprimir_grados[fases]=Phase_check[fases]                
                    # PHASE=my_array[256: 256+225]*frecuencias*360/125e6
                    # PHASE= Phase_check
                    PHASE_sin_comprimir=PHASE_sin_comprimir_grados*np.pi/180
                    PHASE=np.ma.masked_where((Z_sin_comprimir==0.0),PHASE_sin_comprimir) 
                    self.sd.freq=np.ma.masked_where((Z_sin_comprimir==0.0),frecuencias) 
                    Z = np.ma.masked_where((Z_sin_comprimir==0.0),Z_sin_comprimir) 

                    ##ATENCION NO HAGO NINGUNA INTERPOLACION DE LOS DATOS, SOLO LOS COMPRIMO

                    prePHASE=PHASE.compressed()
                    self.sd.freq=self.sd.freq.compressed()
                    preZ = Z.compressed()

                                # ahora aplico una forma de smooth; pero mejor hacerlo en la imagen , no sobre los datos
                    # if (smooth==0):
                    #     PHASE = np.cumsum(prePHASE, dtype=float)
                    #     Z=np.cumsum(preZ, dtype=float)
                    #     PHASE[k:] = PHASE[k:] - PHASE[:-k]
                    #     Z[k:] = Z[k:] - Z[:-k]
                    #     PHASE=PHASE[k - 1:] / k

                    #     Z=Z[k - 1:] / k
                    #     self.sd.freq=self.sd.freq[k-1:]
                    # else:
                    #     PHASE=prePHASE
                    # # self.sd.freq=frecuencias
                    #     Z = preZ

                    PHASE=prePHASE
                    Z=preZ

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
                    absolute_val_array = np.abs(self.sd.freq - 1000)
                    smallest_difference_index = absolute_val_array.argmin()
                    print ('R_data =', self.sd.R_data[smallest_difference_index])        
                    print ('X_data=', self.sd.X_data[smallest_difference_index])
                    print ('resistencia shunt=', shunt[R_shunt_k])
                    self.dv.append_plus("He finalizado de medir")
                    self.dv.append_plus("tiempo transcurrido:" + str(total))  
                    self.dv.append_plus("R_data ="+ str(self.sd.R_data[smallest_difference_index]))
                    self.dv.append_plus("X_data ="+ str(self.sd.X_data[smallest_difference_index]))
                    self.dv.append_plus("resistencia shunt ="+ str(shunt[R_shunt_k]))       
          
        return error

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
