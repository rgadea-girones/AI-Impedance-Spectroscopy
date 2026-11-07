import io
import numpy as np
from time import perf_counter as pc


class ConfiguracionMixin(object):
    """Configuración de la FPGA y del barrido antes de cada medida (modelo 0)."""

    def _configurar_shunt_2p(self):
        """Aplica la configuración de shunt para el modelo de 2 puntas (2P)."""
        # LED3 (autoshunt/shunt fijo) se fija en config_measurement; aquí solo se configuran los pines DIO
        modo = int(self.sd.def_cfg.get('modo_shunt', {}).get('value', 0))
        if modo == 1:
            self.tx_txt('DIG:PIN:DIR OUT,DIO0_N')
            self.tx_txt('DIG:PIN:DIR OUT,DIO1_N')
            self.tx_txt('DIG:PIN:DIR OUT,DIO2_N')
            self.tx_txt('DIG:PIN:DIR OUT,DIO3_N')
            tab_pines = {
                0: (1, 0, 0, 1),  # 90.9 Ω (100 || 1k)
                1: (1, 1, 0, 1),  # 100 Ω
                2: (0, 0, 1, 0),  # 285.7 Ω (500 || 1k || 2k)
                3: (0, 0, 0, 0),  # 333.3 Ω (500 || 1k)
                4: (0, 1, 0, 0),  # 500 Ω
                5: (1, 0, 1, 0),  # 666.7 Ω (1k || 2k)
                6: (1, 0, 0, 0),  # 1000 Ω
                7: (1, 1, 1, 0),  # 2000 Ω
            }
            idx = int(self.sd.def_cfg.get('shunt_fijo_idx', {}).get('value', 4))
            pines = tab_pines.get(idx, (0, 1, 0, 0))
            self.tx_txt('DIG:PIN DIO0_N,' + str(pines[0]))
            self.tx_txt('DIG:PIN DIO1_N,' + str(pines[1]))
            self.tx_txt('DIG:PIN DIO2_N,' + str(pines[2]))
            self.tx_txt('DIG:PIN DIO3_N,' + str(pines[3]))

    def config_measurement(self):
        # modo_barrido: 0 -> Single sweep (LED1=0), 1 -> Up-down sweep (LED1=1)
        if (self.sd.def_cfg['modo_barrido']['value']==1):
            # configuramos la FPGA con diseño verilog propio de DSD
            # adaptado para el autoshunt
            self.tx_txt('DIG:PIN? DIO'+str(7)+'_P')
            state = self.rx_txt()
            t0=pc()
            self.shunt=[90.9,100.0,285.71,500.0,1000.0,2000.0]

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
                self.tx_txt('DIG:PIN LED'+str(1)+','+str(1))  # 1->sweep on                          0->sweep off
                self.tx_txt('DIG:PIN LED'+str(2)+','+str(0))  # 1->debugueo memoria de incrementos   0->no debugueo
                shunt_fijo_val = 1 if int(self.sd.def_cfg.get('modo_shunt', {}).get('value', 0)) == 1 else 0
                self.tx_txt('DIG:PIN LED3,' + str(shunt_fijo_val))  # 0-> autoshunt (defecto), 1-> shunt fijo
                filtro_val = int(self.sd.def_cfg.get('filtro_senales', {}).get('value', 1))
                self.tx_txt('DIG:PIN LED4,' + str(filtro_val))  # 1-> filtros on, 0-> filtros bypaseados

                self.tx_txt('SOUR1:FUNC ARBITRARY')
            except BrokenPipeError:
                print("Broken pipe error occurred.")
                self.dv.append_plus("Algo pasa con la conexión")
                error=1
            #recortamos a 40 Hz
            else:
                # Ejecutar cálculo en ARM (RedPitaya) con C++ y escribir en FPGA
                remote_incr_loaded = False
                f1 = float(self.sd.def_cfg['f_inicial']['value'])
                f2 = float(self.sd.def_cfg['f_final']['value'])
                modo = int(self.sd.def_cfg['tipo_barrido']['value'])  # 0 lineal, 1 log
                num_puntos = int(self.sd.def_cfg['n_puntos']['value'])
                fm = 125000000.0
                try:
                    veamos = self._get_ssh()
                    veamos.cwd.chdir("/root/nuevas_aplicaciones_2026")
                    cmd = "./raf_incr_writer_sweep {:.6f} {:.6f} {} {} {:.6f} {}".format(f1, f2, modo, num_puntos, fm, "on")
                    salida = veamos[cmd]()
                    if salida.strip().rfind("OK") == 0:
                        remote_incr_loaded = True
                        self.dv.append_plus("Incrementos calculados en ARM y escritos en FPGA")
                    else:
                        self.dv.append_plus("ARM error: " + salida.strip())
                except Exception as e:
                    self.dv.append_plus("Fallo ejecutando en ARM: " + str(e))

                outStr = None
                frecuencias2=self.sd.freq[self.sd.freq>40]
                numero_valores=len(frecuencias2)*2
                self.frecuencias=np.concatenate((frecuencias2,np.flip(frecuencias2)))
                if not remote_incr_loaded:
                    # Fallback local: reproducir cálculo Python y enviar traza
                    frecuencias2=self.sd.freq[self.sd.freq>40]
                    numero_valores=len(frecuencias2)*2
                    incrementos2=np.ones(256-numero_valores)*34360000.0
                    incrementos1= (frecuencias2*(2**32))/125e6
                    incrementos=np.concatenate((incrementos1, incrementos2), axis=None)
                    s = io.BytesIO()
                    np.savetxt(s, [incrementos], fmt='%1.1f', delimiter=', ')
                    outStr = s.getvalue().decode('UTF-8')

                self.tx_txt('SOUR1:VOLT ' +str(self.sd.def_cfg['vosc']['value']))
            #    self.tx_txt('SOUR1:VOLT:OFFS 0.00') # esto lo utilizo para cambiar el offset de canal b
            #    self.tx_txt('SOUR2:VOLT:OFFS ' + str(self.sd.def_cfg['nivel_DC']['value'])) # esto lo utilizo para cambiar el offset de canal b
            #   self.tx_txt('SOUR1:BURS:NCYC 0')  # solo funciona si led3 esta activado, numero de ciclos por frecuencia
            #   self.tx_txt('SOUR1:BURS:NOR ' +str(muestras_ampliadas)) # solo funciona si led3 esta activado, numero de frecuencias
                # # rp_s.tx_txt('SOUR2:BURS:INT:PER 30') # solo funciona si led3 esta activado, ancho detector
            #    self.tx_txt('SOUR2:BURS:NOR ' +str(umbral_horizontal_detector_cero))
            #    self.tx_txt('SOUR2:BURS:NCYC ' +str(umbral_vertical_detector_cero)) #controlo el numero de ciclos de ancho del deteccor de cero

                #self.tx_txt('SOUR1:TRAC:DATA:DATA ' + outStr)

                if remote_incr_loaded:
                    # Ya está escrito por el ARM en la memoria de la FPGA
                    self.tx_txt('OUTPUT:STATE ON')
                else:
                    # Envío local de la traza si el cálculo remoto no ha sido posible
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
                self.muestras=muestras

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

                #self.tx_txt('DIG:PIN? DIO'+str(7)+'_P')
                #state = self.rx_txt()

                #elegimos el cable rojo , conector j1
                #activo a nivel bajo: desactivo
                self.tx_txt('DIG:PIN DIO4_N,1')
                #activo a nivel alto: activo
                self.tx_txt('DIG:PIN DIO5_N,1')
                #activo a nivel alto: desactivo
                self.tx_txt('DIG:PIN DIO6_N,0')
                #activo a nivel bajo: desactivo
                self.tx_txt('DIG:PIN DIO7_N,1')

                self._configurar_shunt_2p()

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
                self.frecuencias=self.frecuencias[0:muestras]
                muestras_ampliadas=muestras+1
                # configuraciones  varias
                self.tx_txt('SOUR1:VOLT ' +str(self.sd.def_cfg['vosc']['value']))
                self.tx_txt('SOUR1:VOLT:OFFS 0.00') # esto lo utilizo para cambiar el offset de canal b
                self.tx_txt('SOUR2:VOLT:OFFS ' + str(self.sd.def_cfg['nivel_DC']['value'])) # esto lo utilizo para cambiar el offset de canal b
                # Escribir n_ciclos en memoria vía monitor
                veamos = self._get_ssh()
                n_ciclos_hex = f"0x{int(self.sd.def_cfg['n_ciclos']['value']):08X}"
                veamos["monitor"]("0x40200018", n_ciclos_hex)
                # Escribir muestras_ampliadas en memoria vía monitor
                muestras_ampliadas_hex = f"0x{int(muestras_ampliadas):08X}"
                veamos["monitor"]("0x4020001C", muestras_ampliadas_hex)
                #introduccion valores de filtros
                ADC_canal1_filtroAA = "0x7D93"  # filtro paso bajo aprox. Butterworth fc=20kHz
                veamos["monitor"]("0x40100030 ", ADC_canal1_filtroAA)
                ADC_canal1_filtroBB = "0x437c7"  # filtro paso bajo aprox. Butterworth fc=20kHz
                veamos["monitor"]("0x40100034 ", ADC_canal1_filtroBB)
                ADC_canal1_filtroKK="0xD9999A"  # filtro paso bajo aprox. Butterworth fc=20kHz
                veamos["monitor"]("0x40100038 ", ADC_canal1_filtroKK)
                ADC_canal1_filtroPP="0x2666"      # filtro paso bajo aprox. Butterworth fc=20kHz
                veamos["monitor"]("0x4010003C ", ADC_canal1_filtroPP)

                ADC_canal2_filtroAA = "0x7D93"  # filtro paso bajo aprox. Butterworth fc=20kHz
                veamos["monitor"]("0x40100040 ", ADC_canal2_filtroAA)
                ADC_canal2_filtroBB = "0x437c7"  # filtro paso bajo aprox. Butterworth fc=20kHz
                veamos["monitor"]("0x40100044 ", ADC_canal2_filtroBB)
                ADC_canal2_filtroKK="0xD9999A"  # filtro paso bajo aprox. Butterworth fc=20kHz
                veamos["monitor"]("0x40100048 ", ADC_canal2_filtroKK)
                ADC_canal2_filtroPP="0x2666"      # filtro paso bajo aprox. Butterworth fc=20kHz
                veamos["monitor"]("0x4010004C ", ADC_canal2_filtroPP)
                # con umbral 0 la FPGA rechaza el comando (ERR 9506) y su respuesta desfasa el socket
                if umbral_horizontal_detector_cero>0:
                    self.tx_txt('SOUR2:BURS:NOR ' +str(umbral_horizontal_detector_cero))
                if umbral_vertical_detector_cero>0:
                    self.tx_txt('SOUR2:BURS:NCYC ' +str(umbral_vertical_detector_cero)) #controlo el numero de ciclos de ancho del deteccor de cero

                #self.tx_txt('DIG:PIN LED'+str(2)+','+str(procedimiento_fase))  # desbloqueo finalizacion state1, tambien genera inicio

        elif (self.sd.def_cfg['modo_barrido']['value']==0):
            # configuramos la FPGA con diseño verilog propio de DSD
            # adaptado para el autoshunt
            self.tx_txt('DIG:PIN? DIO'+str(7)+'_P')
            state = self.rx_txt()
            t0=pc()
            self.shunt=[90.9,100.0,285.71,500.0,1000.0,2000.0]


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
                self.tx_txt('DIG:PIN LED'+str(1)+','+str(0))  # 1->sweep on                          0->sweep off
                self.tx_txt('DIG:PIN LED'+str(2)+','+str(0))  # 1->debugueo memoria de incrementos   0->no debugueo
                shunt_fijo_val = 1 if int(self.sd.def_cfg.get('modo_shunt', {}).get('value', 0)) == 1 else 0
                self.tx_txt('DIG:PIN LED3,' + str(shunt_fijo_val))  # 0-> autoshunt (defecto), 1-> shunt fijo
                filtro_val = int(self.sd.def_cfg.get('filtro_senales', {}).get('value', 1))
                self.tx_txt('DIG:PIN LED4,' + str(filtro_val))  # 1-> filtros on, 0-> filtros bypaseados

                self.tx_txt('SOUR1:FUNC ARBITRARY')
            except BrokenPipeError:
                print("Broken pipe error occurred.")
                self.dv.append_plus("Algo pasa con la conexión")
                error=1
            #recortamos a 40 Hz
            else:
                # Ejecutar cálculo en ARM (RedPitaya) con C++ y escribir en FPGA
                remote_incr_loaded = False
                f1 = float(self.sd.def_cfg['f_inicial']['value'])
                f2 = float(self.sd.def_cfg['f_final']['value'])
                modo = int(self.sd.def_cfg['tipo_barrido']['value'])  # 0 lineal, 1 log
                num_puntos = int(self.sd.def_cfg['n_puntos']['value'])
                fm = 125000000.0
                try:
                    veamos = self._get_ssh()
                    veamos.cwd.chdir("/root/nuevas_aplicaciones_2026")
                    cmd = "./raf_incr_writer_sweep {:.6f} {:.6f} {} {} {:.6f} {}".format(f1, f2, modo, num_puntos, fm, "off")
                    salida = veamos[cmd]()
                    if salida.strip().rfind("OK") == 0:
                        remote_incr_loaded = True
                        self.dv.append_plus("Incrementos calculados en ARM y escritos en FPGA")
                    else:
                        self.dv.append_plus("ARM error: " + salida.strip())
                except Exception as e:
                    self.dv.append_plus("Fallo ejecutando en ARM: " + str(e))

                outStr = None
                self.frecuencias=self.sd.freq[self.sd.freq>40]
                numero_valores=len(self.frecuencias)*1
                if not remote_incr_loaded:
                    # Fallback local: reproducir cálculo Python y enviar traza
                    frecuencias2=self.sd.freq[self.sd.freq>40]
                    numero_valores=len(frecuencias2)*1
                    incrementos2=np.ones(256-numero_valores)*34360000.0
                    incrementos1= (frecuencias2*(2**32))/125e6
                    incrementos=np.concatenate((incrementos1, incrementos2), axis=None)
                    s = io.BytesIO()
                    np.savetxt(s, [incrementos], fmt='%1.1f', delimiter=', ')
                    outStr = s.getvalue().decode('UTF-8')

                self.tx_txt('SOUR1:VOLT ' +str(self.sd.def_cfg['vosc']['value']))
                if remote_incr_loaded:
                    # Ya está escrito por el ARM en la memoria de la FPGA
                    self.tx_txt('OUTPUT:STATE ON')
                else:
                    # Envío local de la traza si el cálculo remoto no ha sido posible
                    self.tx_txt('SOUR1:TRAC:DATA:DATA_rafa ' + outStr)
                    self.tx_txt('OUTPUT:STATE ON')

                muestras=numero_valores
                self.muestras=muestras

                decimation=1
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

                self.tx_txt('DIG:PIN? DIO'+str(7)+'_P')
                state = self.rx_txt()

                #elegimos el cable rojo , conector j1
                #activo a nivel bajo: desactivo
                self.tx_txt('DIG:PIN DIO4_N,1')
                #activo a nivel alto: activo
                self.tx_txt('DIG:PIN DIO5_N,1')
                #activo a nivel alto: desactivo
                self.tx_txt('DIG:PIN DIO6_N,0')
                #activo a nivel bajo: desactivo
                self.tx_txt('DIG:PIN DIO7_N,1')

                self._configurar_shunt_2p()

                self.frecuencias=self.frecuencias[0:muestras]
                muestras_ampliadas=muestras+1
                # configuraciones  varias
                self.tx_txt('SOUR1:VOLT ' +str(self.sd.def_cfg['vosc']['value']))
                self.tx_txt('SOUR1:VOLT:OFFS 0.00') # esto lo utilizo para cambiar el offset de canal b
                self.tx_txt('SOUR2:VOLT:OFFS ' + str(self.sd.def_cfg['nivel_DC']['value'])) # esto lo utilizo para cambiar el offset de canal b
                # Escribir n_ciclos en memoria vía monitor
                veamos = self._get_ssh()
                n_ciclos_hex = f"0x{int(self.sd.def_cfg['n_ciclos']['value']):08X}"
                veamos["monitor"]("0x40200018", n_ciclos_hex)
                # Escribir muestras_ampliadas en memoria vía monitor
                muestras_ampliadas_hex = f"0x{int(muestras_ampliadas):08X}"
                veamos["monitor"]("0x4020001C", muestras_ampliadas_hex)
                #introduccion valores de filtros
                ADC_canal1_filtroAA = "0x7D93"  # filtro paso bajo aprox. Butterworth fc=20kHz
                veamos["monitor"]("0x40100030 ", ADC_canal1_filtroAA)
                ADC_canal1_filtroBB = "0x437c7"  # filtro paso bajo aprox. Butterworth fc=20kHz
                veamos["monitor"]("0x40100034 ", ADC_canal1_filtroBB)
                ADC_canal1_filtroKK="0xD9999A"  # filtro paso bajo aprox. Butterworth fc=20kHz
                veamos["monitor"]("0x40100038 ", ADC_canal1_filtroKK)
                ADC_canal1_filtroPP="0x2666"      # filtro paso bajo aprox. Butterworth fc=20kHz
                veamos["monitor"]("0x4010003C ", ADC_canal1_filtroPP)

                ADC_canal2_filtroAA = "0x7D93"  # filtro paso bajo aprox. Butterworth fc=20kHz
                veamos["monitor"]("0x40100040 ", ADC_canal2_filtroAA)
                ADC_canal2_filtroBB = "0x437c7"  # filtro paso bajo aprox. Butterworth fc=20kHz
                veamos["monitor"]("0x40100044 ", ADC_canal2_filtroBB)
                ADC_canal2_filtroKK="0xD9999A"  # filtro paso bajo aprox. Butterworth fc=20kHz
                veamos["monitor"]("0x40100048 ", ADC_canal2_filtroKK)
                ADC_canal2_filtroPP="0x2666"      # filtro paso bajo aprox. Butterworth fc=20kHz
                veamos["monitor"]("0x4010004C ", ADC_canal2_filtroPP)
                # con umbral 0 la FPGA rechaza el comando (ERR 9506) y su respuesta desfasa el socket
                if umbral_horizontal_detector_cero>0:
                    self.tx_txt('SOUR2:BURS:NOR ' +str(umbral_horizontal_detector_cero))
                if umbral_vertical_detector_cero>0:
                    self.tx_txt('SOUR2:BURS:NCYC ' +str(umbral_vertical_detector_cero)) #controlo el numero de ciclos de ancho del deteccor de cero

                #self.tx_txt('DIG:PIN LED'+str(2)+','+str(procedimiento_fase))  # desbloqueo finalizacion state1, tambien genera inicio
                #self.tx_txt('DIG:PIN LED'+str(3)+','+str(0))  #activacion del led3 absolutamente necesario para que el numero de ciclos sea configurable y el numero de frecuencias y los umbrales
