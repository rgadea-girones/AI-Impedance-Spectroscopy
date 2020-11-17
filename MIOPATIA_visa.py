import json
import pyvisa as visa
import time
#import socket as sk
#from threading import Thread, Event
import os
import numpy as np
from PyQt5.QtWidgets import QMessageBox
import fit_library as fit


class VISA():
    def __init__(self,shared_data,txt_browser,fit_browser):
        self.sd = shared_data
        self.tb = txt_browser
        self.fit_browser = fit_browser

        # Visa initializationg
        self.rm = visa.ResourceManager()
        self.lor = self.rm.list_resources()
        self.append_plus("Lista de dispositivos encontrados:")
        self.append_plus(str(self.lor))
        try:
            self.inst = self.rm.open_resource(self.sd.def_cfg['VI_ADDRESS'])
            self.append_plus("Conectados al equipo:")
            self.append_plus(str(self.inst.query("*IDN?")))

        except:
            self.append_plus("No encuentro el medidor 4294A")

        else:
            # Basic parameters
            self.inst.timeout = self.sd.def_cfg['GPIB_timeout']
            # Self-test operation takes a long time [self.inst.query("*TST?")]
            self.inst.read_termination  = '\n'
            self.inst.write_termination = '\n'
            # Avoids reading/sending carriage return inside messages

            self.inst.write('HOLD')


    def append_plus(self,message):
        for text_browser in self.tb:
            text_browser.append(message)

    def append_fit(self,message):
        self.fit_browser.append(message)


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

        #fprintf(handles.GPIBobj,'PAVER OFF'); % Desactivo el promediado. Añadido por mi.

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


        # DC_bias active
        if (self.sd.def_cfg['DC_bias']==0):
            # Tensión de polarización.
            self.inst.write('DCV %s' % str(self.sd.def_cfg['nivel_DC']['value']))
            # Modo de BIAS
            self.inst.write('DCMOD CVOLT')
            # Rango de tensión de bias.
            self.inst.write('DCRNG M1')
            # Borrar errores
            self.inst.write('*CLS')
            # Activo la tensión de bias.
            self.inst.write('DCO ON')
            # Solicito el último error que se ha producido
            error = self.inst.query('OUTPERRO?')
            error_code = int(error[0:error.find(',')])
            if (error_code==0):
                flag_dcrange = 1
            elif (error_code==137):
                self.inst.write('DCRNG M10')
                self.inst.write('*CLS')
                self.inst.write('DCO ON')
                error = self.inst.query('OUTPERRO?')
                error_code = int(error[0:error.find(',')])
                if (error_code==0):
                    flag_dcrange = 10
                elif (error_code==137):
                    self.inst.write('DCRNG M100')
                    self.inst.write('*CLS')
                    self.inst.write('DCO ON')
                    error = self.inst.query('OUTPERRO?')
                    error_code = int(error[0:error.find(',')])
                    if (error_code==0):
                        flag_dcrange = 100
                    elif (error_code==137):
                        # ERROR: BIAS Voltage too high
                        self.append_plus("Módulo de BIAS demasiado elevado. Redúzcala o Desactívela")
                        self.append_plus("ERROR %s" % str(error_code))
                    else:
                        self.append_plus("Reconsidere usar la tensión de BIAS")
                        self.append_plus("ERROR %s" % str(error_code))
                else:
                    self.append_plus("Reconsidere usar la tensión de BIAS")
                    self.append_plus("ERROR %s" % str(error_code))
            else:
                self.append_plus("Reconsidere usar la tensión de BIAS")
                self.append_plus("ERROR %s" % str(error_code))

        # No BIAS voltage
        else:
            self.inst.write('DCRNG M1') # Default range
            self.inst.write('DCO OFF')


    def measure(self):
        self.append_plus("Midiendo Z=R+iX")

        # Service Request instead of using pulling
        event_type = visa.constants.EventType.service_request
        # Mechanism by which we want to be notified
        event_mech = visa.constants.EventMechanism.queue

        self.inst.write('TRGS INT')          # Internal Trigger Source
        self.inst.write('ESNB 1')            # Event_Status_Register[0]=1 // Enables Sweep Completion bit
        self.inst.write('*SRE 4')            # Service Request Enable = 1
        self.inst.write('*CLS')              # Clears Error queue


        self.inst.write('MEAS IRIM')         # Medida de R y X
        self.inst.write('HIDI OFF')          # Muestras la traza inactiva
        self.inst.write('SING')              # Iniciar un barrido único.

        self.append_plus("ACK Instrumento = %s" % self.inst.query('*OPC?'))

        # self.inst.enable_event(event_type, event_mech)
        #
        # #self.append_plus(self.inst.query('*OPC?'))
        # # Wait for the event to occur
        # response = self.inst.wait_on_event(event_type, 10000)
        #
        # #if (response.event.event_type == event_type):
        #     # response.timed_out = False
        # self.inst.disable_event(event_type, event_mech)
        # response.timed_out = False

        # Recover Measured Data
        self.inst.write('TRAC A')           # Selecciona traza A
        self.inst.write('AUTO')             # Autoescala
        aux_R = np.fromstring(self.inst.query('OUTPDTRC?'), dtype=float, sep=',')

        self.inst.write('TRAC B')           # Selecciona traza A
        self.inst.write('AUTO')             # Autoescala
        aux_X = np.fromstring(self.inst.query('OUTPDTRC?'), dtype=float, sep=',')

        self.sd.R_data = aux_R[0::2]
        self.sd.X_data = aux_X[0::2]

        # Compute Err, Eri, Er_mod, Er_fase_data
        # First create frequency array based on actual gui conditions
        # The freq array will not be changed until next data acquisition even if GUI changes
        if (self.sd.def_cfg['tipo_barrido']['value']==0):
            self.sd.freq = np.linspace(self.sd.def_cfg['f_inicial']['value'],
                                       self.sd.def_cfg['f_final']['value'],
                                       self.sd.def_cfg['n_puntos']['value'])
        elif(self.sd.def_cfg['tipo_barrido']['value']==1):
            self.sd.freq = np.logspace(np.log10(self.sd.def_cfg['f_inicial']['value']),
                                       np.log10(self.sd.def_cfg['f_final']['value']),
                                       self.sd.def_cfg['n_puntos']['value'])

        complex_aux         = self.sd.R_data + self.sd.X_data*1j
        self.sd.Z_mod_data  = np.abs(complex_aux)
        self.sd.Z_fase_data = np.angle(complex_aux)

        admitance_aux       = 1./complex_aux
        G_data              = np.real(admitance_aux)
        Cp_data             = np.imag(admitance_aux)/(2*np.pi*self.sd.freq)
        self.sd.Err_data    = Cp_data/self.sd.Co
        self.sd.Eri_data    = G_data/(self.sd.Co*(2*np.pi*self.sd.freq));
        E_data              = self.sd.Err_data + -1*self.sd.Eri_data*1j;

        self.sd.Er_mod_data  = np.abs(E_data);
        self.sd.Er_fase_data = np.angle(E_data);

        # Deactivate BIAS for security reasons
        self.inst.write('DCO OFF')
        self.inst.write('DCRNG M1')

        self.inst.wait_for_srq(self.sd.def_cfg['GPIB_timeout'])



    def show_measurement(self,comboBox_trazaA,comboBox_trazaB):
        self.sd.axes['ax0'].cla()
        self.sd.axes['ax1'].cla()

        traza_A = self.switch({ 0:self.sd.Z_mod_data,
                                1:self.sd.Z_fase_data,
                                2:self.sd.Err_data,
                                3:self.sd.Eri_data,
                                4:self.sd.Er_mod_data,
                                5:self.sd.Er_fase_data}, comboBox_trazaA)

        traza_B = self.switch({ 0:self.sd.Z_mod_data,
                                1:self.sd.Z_fase_data,
                                2:self.sd.Err_data,
                                3:self.sd.Eri_data,
                                4:self.sd.Er_mod_data,
                                5:self.sd.Er_fase_data}, comboBox_trazaB)


        if (self.sd.def_cfg['tipo_barrido']['value']==0):
            string_A = self.switch({0:'plot', 1:'plot', 2:'plot',
                                    3:'plot', 4:'semilogy', 5:'plot'},
                                    comboBox_trazaA)
            string_B = self.switch({0:'plot', 1:'plot', 2:'plot',
                                    3:'plot', 4:'semilogy', 5:'plot'},
                                    comboBox_trazaB)
            eval("self.sd.axes['ax0']." + string_A + "(self.sd.freq, traza_A, color='red')")
            self.sd.axes['ax0'].tick_params(axis='y', colors='red')
            eval("self.sd.axes['ax1']." + string_B + "(self.sd.freq, traza_B, color='blue')")
            self.sd.axes['ax1'].grid(True)
            self.sd.axes['ax1'].tick_params(axis='y',colors='blue')

        elif(self.sd.def_cfg['tipo_barrido']['value']==1):
            string_A = self.switch({0:'semilogx', 1:'semilogx', 2:'semilogx',
                                    3:'semilogx', 4:'loglog', 5:'semilogx'},
                                    comboBox_trazaA)
            string_B = self.switch({0:'semilogx', 1:'semilogx', 2:'semilogx',
                                    3:'semilogx', 4:'loglog', 5:'semilogx'},
                                    comboBox_trazaB)
            eval("self.sd.axes['ax0']." + string_A + "(self.sd.freq, traza_A, color='red')")
            self.sd.axes['ax0'].tick_params(axis='y',colors='red')
            eval("self.sd.axes['ax1']." + string_B + "(self.sd.freq, traza_B, color='blue')")
            self.sd.axes['ax1'].grid(True)
            self.sd.axes['ax1'].tick_params(axis='y', colors='blue')

        self.sd.fig1.tight_layout()



    def show_data(self, comboBox_trazaA, comboBox_trazaB, data):

        self.sd.axes['ax2'].cla()
        self.sd.axes['ax3'].cla()

        traza_A = self.switch({ 0:data['Z_mod'],
                                1:data['Z_Fase'],
                                2:data['Err'],
                                3:data['Eri'],
                                4:data['E_mod'],
                                5:data['E_fase']},
                                comboBox_trazaA)

        traza_B = self.switch({ 0:data['Z_mod'],
                                1:data['Z_Fase'],
                                2:data['Err'],
                                3:data['Eri'],
                                4:data['E_mod'],
                                5:data['E_fase']},
                                comboBox_trazaB)

        if (self.sd.def_cfg['tipo_barrido']['value']==0):
            string_A = self.switch({0:'plot', 1:'plot', 2:'plot',
                                    3:'plot', 4:'semilogy', 5:'plot'},
                                    comboBox_trazaA)
            string_B = self.switch({0:'plot', 1:'plot', 2:'plot',
                                    3:'plot', 4:'semilogy', 5:'plot'},
                                    comboBox_trazaB)
            print(string_A)
            eval("self.sd.axes['ax2']." + string_A + "(data['Freq'], traza_A, color='red')")
            self.sd.axes['ax2'].tick_params(axis='y', colors='red')
            eval("self.sd.axes['ax3']." + string_B + "(data['Freq'], traza_B, color='blue')")
            self.sd.axes['ax3'].grid(True)
            self.sd.axes['ax3'].tick_params(axis='y',colors='blue')

        elif(self.sd.def_cfg['tipo_barrido']['value']==1):
            string_A = self.switch({0:'semilogx', 1:'semilogx', 2:'semilogx',
                                    3:'semilogx', 4:'loglog', 5:'semilogx'},
                                    comboBox_trazaA)
            string_B = self.switch({0:'semilogx', 1:'semilogx', 2:'semilogx',
                                    3:'semilogx', 4:'loglog', 5:'semilogx'},
                                    comboBox_trazaB)
            eval("self.sd.axes['ax2']." + string_A + "(data['Freq'], traza_A, color='red')")
            self.sd.axes['ax2'].tick_params(axis='y',colors='red')
            eval("self.sd.axes['ax3']." + string_B + "(data['Freq'], traza_B, color='blue')")
            self.sd.axes['ax3'].grid(True)
            self.sd.axes['ax3'].tick_params(axis='y', colors='blue')

        self.sd.fig2.tight_layout()




    def show_data_fit(self, comboBox_trazaA, comboBox_fit_alg, data):
        # Posición en el vector de parametros
        pos_low = np.argwhere(np.array(self.sd.def_cfg['param_fit']['names'])=='f_low_fit')[0][0]
        pos_high = np.argwhere(np.array(self.sd.def_cfg['param_fit']['names'])=='f_high_fit')[0][0]
        pos_n_func = np.argwhere(np.array(self.sd.def_cfg['param_fit']['names'])=='n_func_fit')[0][0]

        A = fit.gompertz()
        traza_A = self.switch({ 0:data['Z_mod'],
                                1:data['Z_Fase'],
                                2:data['Err'],
                                3:data['Eri'],
                                4:np.log10(data['E_mod']),
                                5:data['E_fase']},
                                comboBox_trazaA)

        x_data = np.array(data['Freq'])

        index_range = np.where((x_data > self.sd.def_cfg['param_fit']['value'][pos_low])*
                               (x_data < self.sd.def_cfg['param_fit']['value'][pos_high]))[0]



        param_n_func = self.sd.def_cfg['param_fit']['value'][pos_n_func]
        bounds = np.array(self.sd.def_cfg['param_fit']['limits'][3:])
        bounds_low = bounds[0:param_n_func*3+1,0]
        bounds_high = bounds[0:param_n_func*3+1,1]
        print([bounds_low.tolist(),bounds_high.tolist()])
        print(self.sd.def_cfg['param_fit']['value'][3:4+3*(param_n_func)])

        A(np.log10(traza_A[index_range]),
               np.log10(x_data[index_range]),
               param_n_func,
               self.sd.def_cfg['param_fit']['value'][3:4+3*(param_n_func)],
               method = comboBox_fit_alg,
               bounds = [bounds_low.tolist(),bounds_high.tolist()]
               )

        epsilon_inf  = 10**A.coeff[0]
        dispersion_1 = 10**A.coeff[1]
        errord1=10**A.perr[1]
        tiempo_relajacion_1 = (10**A.coeff[2])
        errort1=10**A.perr[2]
        pendiente_dispersion_1 = 10**A.coeff[3]

        string1 = (("Epsilon_inf = %3.3e \n" +\
                   "Dispersion 1 = %3.3e (+/- %3.3e)  \n" +\
                   "Tiempo Relajación 1 = %3.3e (+/- %3.3e)  \n" +\
                   "Pendiente Dispersión 1 = %3.3e") % \
                   (epsilon_inf,
                    dispersion_1, errord1,
                    tiempo_relajacion_1, errort1,
                    pendiente_dispersion_1))

        string2 = ""
        string3 = ""

        if param_n_func > 1:
            dispersion_2 = 10**A.coeff[4]
            errord2=10**A.perr[4]
            tiempo_relajacion_2 = (10**A.coeff[5])
            errort2=10**A.perr[5]
            pendiente_dispersion_2 = 10**A.coeff[6]

            string2 = (("Dispersion 2 = %3.3e (+/- %3.3e)  \n" +\
                       "Tiempo Relajación 2 = %3.3e (+/- %3.3e)  \n" +\
                       "Pendiente Dispersión 2 = %3.3e") % \
                       (dispersion_2, errord2,
                        tiempo_relajacion_2, errort2,
                        pendiente_dispersion_2))

        if param_n_func > 2:
            dispersion_3 = 10**A.coeff[7]
            errord3=10**A.perr[7]
            tiempo_relajacion_3 = (10**A.coeff[8])
            errort3=10**A.perr[8]
            pendiente_dispersion_3 = 10**A.coeff[9]

            string3 = (("Dispersion 3 = %3.3e (+/- %3.3e)  \n" +\
                       "Tiempo Relajación 3 = %3.3e (+/- %3.3e)  \n" +\
                       "Pendiente Dispersión 3 = %3.3e") % \
                       (dispersion_3, errord3,
                        tiempo_relajacion_3, errort3,
                        pendiente_dispersion_3))


        self.append_fit("PARAMETROS \n" + str(A.coeff))
        self.append_fit("ERROR \n" + str(A.perr))
        self.append_fit("Goodnes of Fit - R2 = %f" % A.r_sqr)
        self.append_fit(string1)
        self.append_fit(string2)
        self.append_fit(string3)

        self.sd.axes['ax4'].cla()

        # if (self.sd.def_cfg['tipo_barrido']['value']==0):
        #     self.sd.axes['ax4'].plot(x_data, traza_A, color='red')
        #     self.sd.axes['ax4'].tick_params(axis='y', colors='red')
        #     #self.sd.axes['ax4'].plot(data['Freq'], traza_B, color='blue')
        #     self.sd.axes['ax4'].plot(x_data, A.evaluate(x_data), color='green')
        #     self.sd.axes['ax4'].grid(True)
        #
        #
        # elif(self.sd.def_cfg['tipo_barrido']['value']==1):
        #     self.sd.axes['ax4'].loglog(x_data, traza_A, color='red')
        #     self.sd.axes['ax4'].tick_params(axis='y',colors='red')
        #     #self.sd.axes['ax4'].semilogx(data['Freq'], traza_B, color='blue')
        #     self.sd.axes['ax4'].loglog(x_data, 10**(A.evaluate(np.log10(x_data))), color='green')
        #     self.sd.axes['ax4'].grid(True)

        self.sd.axes['ax4'].loglog(x_data, traza_A, color='red')
        self.sd.axes['ax4'].tick_params(axis='y',colors='red')
        #self.sd.axes['ax4'].semilogx(data['Freq'], traza_B, color='blue')
        self.sd.axes['ax4'].loglog(x_data, 10**(A.evaluate(np.log10(x_data))), color='green')
        self.sd.axes['ax4'].grid(True)

        self.sd.fig3.tight_layout()

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
        self.append_plus("Realizando calibración por carga")

        error_code = self.AdapterCorrection('Compen_Open')
        if error_code==0:
            self.append_plus("Calibración por CARGA realizada correctamente")
        else:
            self.append_plus("Error %s en calibración por carga" % error_code)

        ############## ABIERTO
        self.message_box("Calibración en ABIERTO",
                         "Configure el sensor para calibración en ABIERTO y pulsa ACEPTAR")
        self.append_plus("Realizando calibración en ABIERTO")

        error_code = self.AdapterCorrection('Compen_Load')
        if error_code==0:
            self.append_plus("Calibración en ABIERTO realizada correctamente")
        else:
            self.append_plus("Error %s en calibración en ABIERTO" % error_code)

        ############## CORTO
        self.message_box("Calibración en CORTO",
                         "Configure el sensor para calibración en CORTO y pulsa ACEPTAR")
        self.append_plus("Realizando calibración en CORTO")

        error_code = self.AdapterCorrection('Compen_Short')
        if error_code==0:
            self.append_plus("Calibración en CORTO realizada correctamente")
        else:
            self.append_plus("Error %s en calibración en CORTO" % error_code)

    def cal_open_short(self):
        # Proceos de la calibración en carga, para ello como se indica se
        # realiza una calibración en abierto con la configuración realizada con
        # los comandos anteriores.

        ############## ABIERTO
        self.message_box("Calibración en ABIERTO",
                         "Configure el sensor para calibración en ABIERTO y pulsa ACEPTAR")
        self.append_plus("Realizando calibración en ABIERTO")

        error_code = self.AdapterCorrection('Compen_Open')
        if error_code==0:
            self.append_plus("Calibración en ABIERTO realizada correctamente")
        else:
            self.append_plus("Error %s en calibración en ABIERTO" % error_code)

        ############## CORTO
        self.message_box("Calibración en CORTO",
                         "Configure el sensor para calibración en CORTO y pulsa ACEPTAR")
        self.append_plus("Realizando calibración en CORTO")

        error_code = self.AdapterCorrection('Compen_Short')
        if error_code==0:
            self.append_plus("Calibración en CORTO realizada correctamente")
        else:
            self.append_plus("Error %s en calibración en CORTO" % error_code)


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

        print(test)

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

        print(open_data_string)

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
            self.append_plus("Calibración %s correcta" % type)
        else:
            self.append_plus("Error en Calibración %s" % type)

        return error_code
