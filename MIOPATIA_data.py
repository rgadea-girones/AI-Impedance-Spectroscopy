import sys
import json
import time
from matplotlib.figure import Figure
import numpy as np


class DATA(object):
    """ DATA shared among different parts of the application.
        Reads information from JSON file.
        Writes JSON file with information if required
    """

    def __init__(self,read=False):

        self.filename = "miopatia.json"
        self.def_cfg=[]

        # Figure handlers
        self.fig1 = Figure()
        self.fig2 = Figure()
        self.fig3 = Figure()
        self.fig4 = Figure()
        # Axes for plotting
        self.axes={'ax0':0,'ax1':0,'ax2':0,'ax3':0,'ax4':0, 'ax5':0}
        timestr = time.strftime("%Y%m%d")
        if (read==True):
            self.config_read()
        else:
            # These are the default values.
            self.def_cfg= {'f_inicial':{'value':10, 'limits':[10.0,100.0E6],'type':'float'},
                            'f_final' :{'value':1000000, 'limits':[10.0,100.0E6],'type':'float'},
                            'n_puntos':{'value':50, 'limits':[1,801],'type':'int'},
                            'n_ciclos':{'value':0, 'limits':[0,10],'type':'int'},
                            'shunt':{'value':4, 'limits':[0,5],'type':'int'},
                            'vosc':{'value':0.5, 'limits':[0.0,2.0],'type':'float'},
                            'tipo_barrido':{'value':1, 'limits':[0,1],'type':'int'},
                            'DC_bias':{'value':0, 'limits':[0,1],'type':'int'},
                            'smooth':{'value':1, 'limits':[0,1],'type':'int'},
                            'modelo':{'value':1, 'limits':[0,3],'type':'int'},       
                            'RANGO':{'value':0, 'limits':[0,1],'type':'int'},                                                                                    
                            'k_factor':{'value':9, 'limits':[1,9],'type':'int'},                            
                            'nivel_DC':{'value':0.016, 'limits':[-40.0,40.0],'type':'float'},
                            #'avg':{'value':0, 'limits':[0,1],'type':'int'},
                            'post_procesado':{'value':0, 'limits':[0,1],'type':'int'},
                            'pto_tip':{'value':0, 'limits':[0,3],'type':'int'},
                            'ultimo_pollo':{'value':0, 'limits':[0,99],'type':'int'},
                            'ultima_medida':{'value':0, 'limits':[0,9],'type':'int'},
                            #'direccion_redpitaya':"10.42.0.228",
                            #'direccion_redpitaya':"10.42.0.194",
                            'direccion_redpitaya':"169.254.240.106",                            
                            'sujetos': "0-0",
                            'load_mfile_name':"./COPIA_EXCELS/medida.csv",
                            'save_mfile_name':"./COPIA_EXCELS/medida.csv",
                            'save_excelfile_name':"./COPIA_EXCELS/medida.xlsx",                            
                            'load_cal_file_name':"./calibracion.cal",
                            'save_cal_file_name':"./calibracion_new.cal",
                            'load_h5file_name':"./COPIA_PANDAS/espectros.hdf",
                           # 'io_h5file_name':"./COPIA_PANDAS/hdf_"+timestr+".hdf",
                            'io_h5file_name':"./COPIA_PANDAS/reflujo_rafa_20240517_authoshunt_definitivo.hdf",
                            'def_path':"./",
                            'conf_cal':{'value':0, 'limits':[0,1],'type':'int'},
                            'c_load':{'value':500, 'limits':[0,1E6],'type':'float'},
                            'g_load':{'value':0.1, 'limits':[0,1E6],'type':'float'},
                            'pto_cal':{'value':1, 'limits':[0,1],'type':'int'},
                            'comboxA':['|Z|','F.Z','E\'r','E\'\'r','|Er|','F.Er'],
                            'comboxB':['F.Z','|Z|','E\'r','E\'\'r','|Er|','F.Er'],                            
                            'combox_fit':['lm','trf','dogbox'],
                            'load_mfile_fit':"./COPIA_EXCELS/medida.csv",
                            'origen_fit':{'value':0, 'limits':[0,1],'type':'int'},
                            # FIT PARAMETERS
                            'param_fit':{'names' :['n_func_fit','f_low_fit','f_high_fit',
                                                   'param_A1','param_B1','param_C1','param_D1',
                                                   'param_B2','param_C2','param_D2',
                                                   'param_B3','param_C3','param_D3'],
                                         'value' :[ 1,0,100E6,
                                                    0,0,0,0,
                                                    0,0,0,
                                                    0,0,0],
                                         'limits':[[1,3],[0,100E6],[0,100E6],
                                                   [-1E12,1E12],[-1E12,1E12],[-1E12,1E12],[-1E12,1E12],
                                                   [-1E12,1E12],[-1E12,1E12],[-1E12,1E12],
                                                   [-1E12,1E12],[-1E12,1E12],[-1E12,1E12]],
                                         'type'  :['int','float','float',
                                                   'float','float','float','float',
                                                   'float','float','float',
                                                   'float','float','float']},

                            #'n_func_fit': {'value':1, 'limits':[1,3],'type':'int'},
                            #'f_low_fit': {'value':0, 'limits':[0,100E6],'type':'float'},
                            #'f_high_fit': {'value':100E6, 'limits':[0,100E6],'type':'float'},
                            'VI_ADDRESS': 'GPIB0::17::INSTR',
                            'GPIB_timeout':12001
                            }
            self.config_write()


        # CONSTANTS
        self.E0              = 8.854e-12 # Vacuum permitivity
        self.Adj_center      = 100000    # Central Freq. for certain calibrations
        self.Adj_up_limit_a  = 1E-9      # Limite superior C (Faradios) del ajuste
                                         # de electrodos paralelos para electrodo TIPO A
        self.Adj_low_limit_a = 7E-10     # Limite inferior C (Faradios) del ajuste
                                         # de electrodos paralelos para electrodo TIPO A
        self.Adj_up_limit_b  = 2E-11     # Limite superior C (Faradios) del ajuste
                                         # de electrodos paralelos para electrodo TIPO B
        self.Adj_low_limit_b = 1.2E-11   # Limite inferior C (Faradios) del ajuste
                                         # de electrodos paralelos para electrodo TIPO B

        # Constantes para la calibración por carga
        self.Load_center     = 100000    # Frecuencia central 100KHz donde se realiza
                                         # la primera medida por carga.
        self.Load_ave        = 4         # Media de 4 medidas para el ajuste por carga
        self.Load_bw         = 5         # Bandwidth 5 (Mejor reolución - más lento) para el ajuste por carga.
        self.Load_up_limit_a = 5.05E-11  # 50.5 pF Limite superior del valor de la capacidad para la carga en el electrodo A
        self.Load_lo_limit_a = 4.95E-11  # 49.5 pF Limite inferior del valor de la capacidad para la carga en el electrodo A
        self.Load_up_limit_b = 5.05E-12  # 5.05 pF Limite superior del valor de la capacidad para la carga en el electrodo B
        self.Load_lo_limit_b = 4.95E-12  # 4.95 pF Limite inferior del valor de la capacidad para la carga en el electrodo B
        self.Load_up_limit_c = 1.55E-12  # 1.55 pF Limite superior del valor de la capacidad para la carga en el electrodo C
        self.Load_lo_limit_c = 1.45E-12  # 1.45 pF Limite inferior del valor de la capacidad para la carga en el electrodo C
        self.Load_up_limit_d = 1.55E-12  # 1.55 pF Limite superior del valor de la capacidad para la carga en el electrodo D
        self.Load_lo_limit_d = 1.45E-12  # 1.45 pF Limite inferior del valor de la capacidad para la carga en el electrodo D
        self.Load_g          = 0         # Valor de la admitancia de la carga

        # Constantes de calibración de abiertos - Caso calibración Carga-Open-Short
        self.Open_r          = 1E11      # Resistencia de 100GOhm. Valor esperado de resistencia en el abierto.
        self.Open_l          = 0         # Valor de la inductancia esperada en el abierto
        # Constantes de calibración de cortos - Caso calibración Carga-Open-Short
        self.Short_r         = 0         # Valor de la resitencia espreada del corto
        self.Short_l         = 0         # Valor de la inductancia esperada del corto.

        # Constantes de calibración de abiertos - Caso calibración Open-Short
        self.Open_c2         = 0         # Capacidad esperada para en el abierto.
        self.Open_g2         = 0         # Valor de la admitancia esperada en el abierto.
        # Constantes de calibración de cortos  - Caso calibración Open-Short
        self.Short_r2        = 0         # Valor de la resitencia espreada del corto
        self.Short_l2        = 0         # Valor de la inductancia esperada del corto.
        # Constantes de calibración de carga - Caso calibración Open-Short
        self.Load_r2         = 0         # Valor de la resitencia espreada del corto
        self.Load_l2         = 0         # Valor de la inductancia esperada del corto.

        self.Bw              = 3         # Valor del Bandwidth

        # Constantes para calibracion con platos
        self.D_elec_a        = 0.038     # Diametro del electrodo A - 38mm
        self.D_elec_b        = 0.005     # Diametro del electrodo B - 5 mm

        self.Nop             = 1         # ???
        self.Swe_type        = 'LIN'

        # Inicializacion de vectores de datos
        self.freq            = np.array([])
        self.Z_mod_data      = np.array([])
        self.Z_fase_data     = np.array([])
        self.Err_data        = np.array([])
        self.Eri_data        = np.array([])
        self.Er_mod_data     = np.array([])
        self.Er_fase_data    = np.array([])
        self.R_data          = np.array([])
        self.X_data          = np.array([])
        self.COM_OPEN_data_R = np.array([])
        self.COM_OPEN_data_X = np.array([])
        self.COM_SHORT_data_R = np.array([])
        self.COM_SHORT_data_X = np.array([])
        self.COM_LOAD_data_R = np.array([])
        self.COM_LOAD_data_X = np.array([])

        self.Co              = 1E-12   # Valor capacidad en abierto sensor de puntas
        self.stop_continue   = 0

        self.cal_points      = 100

        self.fit_params_glb = []

        self.fit_data_frame = []

        self.pollo_fitado  = 0
        self.medida_fitada = 0



    def config_write(self):
        writeName = self.filename
        try:
            with open(writeName,'w') as outfile:
                json.dump(self.def_cfg, outfile, indent=4, sort_keys=False)
        except IOError as e:
            print(e)

    def config_read(self):
        try:
            with open(self.filename,'r') as infile:
                self.def_cfg = json.load(infile)
        except IOError as e:
            print(e)
