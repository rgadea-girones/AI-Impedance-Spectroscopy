import sys
import warnings
import matplotlib
matplotlib.use('Qt5Agg')
from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtUiTools import QUiLoader
from MainWindow import Ui_MainWindow

from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg as FigureCanvas,
    NavigationToolbar2QT as NavigationToolbar)
from PySide6.QtWidgets import QMessageBox
from collections import OrderedDict
import ctypes
from MIOPATIA_visa import VISA
from MIOPATIA_data import DATA
from MIOPATIA_BE import BACK_END
from MIOPATIA_BE import BROWSERS
from MIOPATIA_dataview import DATA_VIEW


# PYINSTALLER : pyinstaller -D --specpath .\EXE miopatia.py

#version septiembre 2025
#  pyinstaller --onefile --hidden-import xarray miopatia.py


qtCreatorFile = "impedance_spectroscopy_atunes.ui"


# Ui_MainWindow, QtBaseClass = uic.loadUiType(qtCreatorFile)

warnings.filterwarnings("ignore", message="Attempted to set non-positive left xlim on a log-scaled axis.\nInvalid limit will be ignored.")

# WERG Filter out RuntimeWarnings. 
warnings.filterwarnings('ignore',category=RuntimeWarning)

class MyApp(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self,data):
        QtWidgets.QMainWindow.__init__(self)
        Ui_MainWindow.__init__(self)
        self.setupUi(self)
        self.setWindowIcon(QtGui.QIcon('./atun1.jpg'))
        # self.showFullScreen()
        #self.resize(800,600)
        # self.showMaximized()
        self.show()
        # Shared data
        self.sd = data
        # Classes Instantiation

        # VISA start
        self.dv  = DATA_VIEW(self.sd,[self.textBrowser,self.textBrowser_2,self.textBrowser_4],self.textBrowser_3)
        self.vi  = VISA(self.sd,self.dv)
        self.be  = BACK_END(self,data,self.vi,self.dv)
        self.brw = BROWSERS(self,data,self.dv)


        ######### Combos Initialization and RadiButton Groups creation #########
        # Button groups creation
        def Rbutton_group(button_array):
            bg_config_cal = QtWidgets.QButtonGroup()
            radioButton = button_array
            j=0
            for i in radioButton:
                bg_config_cal.addButton(i)
                bg_config_cal.setId(i,j)
                j+=1
            return bg_config_cal

        self.comboBox_trazaA.addItems(self.sd.def_cfg['comboxA'])
        self.comboBox_trazaB.addItems(self.sd.def_cfg['comboxB'])
        self.comboBox_trazaA_4.addItems(self.sd.def_cfg['comboxA'])
        self.comboBox_mag_fit.addItems(self.sd.def_cfg['comboxA'])
        self.comboBox_fit_alg.addItems(self.sd.def_cfg['combox_fit'])
        self.bg_xaxis      = Rbutton_group([self.radioButton_lineal, self.radioButton_log])
        self.bg_xaxis_2    = Rbutton_group([self.radioButton_lineal_2, self.radioButton_log_2])
        self.bg_DC         = Rbutton_group([self.radioButton_DC_ON, self.radioButton_DC_OFF])
        self.bg_DC_2       = Rbutton_group([self.radioButton_DC_ON_2, self.radioButton_DC_OFF_2])
        self.post_pro      = Rbutton_group([self.radioButton_Corre, self.radioButton_F_Corre ])   
        self.post_pro_2    = Rbutton_group([self.radioButton_Corre_2, self.radioButton_F_Corre_2 ])  
        self.tipo_analisis = Rbutton_group([self.radioButton_tipoanalisis_3,self.radioButton_tipoanalisis_4 ])  
        self.sel_smooth    = Rbutton_group([self.SMOOTH_ON,self.SMOOTH_OFF ])  
        self.sel_smooth_2  = Rbutton_group([self.SMOOTH_ON_2,self.SMOOTH_OFF_2 ])     
        self.sel_modelo    = Rbutton_group([self.MODELO_1,self.MODELO_2,self.MODELO_3,self.MODELO_4])          
        self.sel_RANGO     = Rbutton_group([self.RANGO_OBJETO,self.RANGO_MEDIDA ])                
        
        self.bg_config_cal = Rbutton_group([self.radioButton_config_cal_1, self.radioButton_config_cal_2])
        self.bg_pto_cal    = Rbutton_group([self.radioButton_pto_cal_medidor, self.radioButton_pto_cal_usuario])

        #                     'avg':         {'array':['avg',      'avg_2'],  'qt':'QCheckBox'},
        ############## Widget to internal variables assignment #################
        # Data Mirroring through GUI
        self.mirror =  {'f_inicial':   {'array':['f_inicial', 'f_inicial_2'],'qt':'QLineEdit'},
                        'f_final':     {'array':['f_final',   'f_final_2'],  'qt':'QLineEdit'},
                        'n_puntos':    {'array':['n_puntos',  'n_puntos_2'],  'qt':'QLineEdit'},
                        'n_ciclos':    {'array':['n_ciclos',  'n_ciclos_2'],  'qt':'QLineEdit'},
                        'shunt':       {'array':['shunt', 'shunt_2'],  'qt':'QLineEdit'},
                        'smooth':      {'array':['sel_smooth','sel_smooth_2'], 'qt':'QButtonGroup'},
                        'k_factor':    {'array':['k_factor','k_factor_2'],  'qt':'QLineEdit'},                         
                        'vosc':        {'array':['vosc',        'vosc_2'],   'qt':'QLineEdit'},
                        'tipo_barrido':{'array':['bg_xaxis', 'bg_xaxis_2'],  'qt':'QButtonGroup'},
                        'DC_bias':     {'array':['bg_DC',    'bg_DC_2'],     'qt':'QButtonGroup'},
                        'nivel_DC':    {'array':['nivel_DC', 'nivel_DC_2'],  'qt':'QLineEdit'},
                        'post_procesado':{'array':['post_pro', 'post_pro_2'],  'qt':'QButtonGroup'}}
        # Paths
        self.paths = {'load_mfile_name':'load_path',
                      'save_mfile_name':'save_path',
                      'save_excelfile_name':'save_path_19',                      
                      'load_cal_file_name':'load_path_2',
                      'save_cal_file_name':'save_path_2',
                      'direccion_redpitaya':'load_path_18',
                      'sujetos':'load_path_19',
                      'io_h5file_name':'load_path_db'}
        # Other controls
        self.others = {'conf_cal':{'array':'bg_config_cal', 'qt':'QButtonGroup'},
                       'c_load':{'array':'c_load', 'qt':'QLineEdit'},
                       'g_load':{'array':'g_load', 'qt':'QLineEdit'},
                       'pto_cal':{'array':'bg_pto_cal', 'qt':'QButtonGroup'},
                       'modelo':{'array':'sel_modelo', 'qt':'QButtonGroup'},  
                       'RANGO':{'array':'sel_RANGO', 'qt':'QButtonGroup'},                    
                    #    'smooth':{'array':'sel_filtrado', 'qt':'QButtonGroup'},
                    #    'k_factor':{'array':'k_factor',  'qt':'QLineEdit'},                       
                       'pto_tip':{'array':'tipo_analisis', 'qt':'QButtonGroup'}
                       }
        #Fit Parameters
        self.fit_param = OrderedDict(
                         [
                         ('n_func_fit',{'array':'n_func', 'qt':'QLineEdit'}),
                         ('f_low_fit' ,{'array':'f_low', 'qt':'QLineEdit'}),
                         ('f_high_fit',{'array':'f_high', 'qt':'QLineEdit'}),
                         ('param_A1',{'array':'param_A1', 'qt':'QLineEdit'}),
                         ('param_B1',{'array':'param_B1', 'qt':'QLineEdit'}),
                         ('param_C1',{'array':'param_C1', 'qt':'QLineEdit'}),
                         ('param_D1',{'array':'param_D1', 'qt':'QLineEdit'}),
                         ('param_B2',{'array':'param_B2', 'qt':'QLineEdit'}),
                         ('param_C2',{'array':'param_C2', 'qt':'QLineEdit'}),
                         ('param_D2',{'array':'param_D2', 'qt':'QLineEdit'}),
                         ('param_B3',{'array':'param_B3', 'qt':'QLineEdit'}),
                         ('param_C3',{'array':'param_C3', 'qt':'QLineEdit'}),
                         ('param_D3',{'array':'param_D3', 'qt':'QLineEdit'}),
                         ('lparam_A1_H',{'array':'param_A1_H', 'qt':'QLineEdit'}),
                         ('lparam_B1_H',{'array':'param_B1_H', 'qt':'QLineEdit'}),
                         ('lparam_C1_H',{'array':'param_C1_H', 'qt':'QLineEdit'}),
                         ('lparam_D1_H',{'array':'param_D1_H', 'qt':'QLineEdit'}),
                         ('lparam_B2_H',{'array':'param_B2_H', 'qt':'QLineEdit'}),
                         ('lparam_C2_H',{'array':'param_C2_H', 'qt':'QLineEdit'}),
                         ('lparam_D2_H',{'array':'param_D2_H', 'qt':'QLineEdit'}),
                         ('lparam_B3_H',{'array':'param_B3_H', 'qt':'QLineEdit'}),
                         ('lparam_C3_H',{'array':'param_C3_H', 'qt':'QLineEdit'}),
                         ('lparam_D3_H',{'array':'param_D3_H', 'qt':'QLineEdit'}),
                          ('lparam_A1_L',{'array':'param_A1_L', 'qt':'QLineEdit'}),
                          ('lparam_B1_L',{'array':'param_B1_L', 'qt':'QLineEdit'}),
                          ('lparam_C1_L',{'array':'param_C1_L', 'qt':'QLineEdit'}),
                          ('lparam_D1_L',{'array':'param_D1_L', 'qt':'QLineEdit'}),
                          ('lparam_B2_L',{'array':'param_B2_L', 'qt':'QLineEdit'}),
                          ('lparam_C2_L',{'array':'param_C2_L', 'qt':'QLineEdit'}),
                          ('lparam_D2_L',{'array':'param_D2_L', 'qt':'QLineEdit'}),
                          ('lparam_B3_L',{'array':'param_B3_L', 'qt':'QLineEdit'}),
                          ('lparam_C3_L',{'array':'param_C3_L', 'qt':'QLineEdit'}),
                          ('lparam_D3_L',{'array':'param_D3_L', 'qt':'QLineEdit'})
                         ]
                         )

        ########### Controls Defaults ############
        self.be.default_data()


        ############# Function to Widget assignment

        # Clicked Calls
        clicked  = [{'wdg':self.toolButton_load,   'func':self.brw.load_mfile_browser},
                    {'wdg':self.toolButton_load_4,  'func':self.brw.load_h5file_browser},
                    {'wdg':self.toolButton_load_17,  'func':self.brw.load_h5file_browser2},
                    {'wdg':self.toolButton_load_18,  'func':self.brw.save_excelfile_browser},                    
                    {'wdg':self.toolButton_save,   'func':self.brw.save_mfile_browser},
                    {'wdg':self.toolButton_load_2, 'func':self.brw.load_calibration_file_browser},
                    {'wdg':self.toolButton_save_2, 'func':self.brw.save_calibration_file_browser},
                    {'wdg':self.toolButton_load_db,'func':self.brw.load_h5file_DB_browser},
                    {'wdg':self.REDRAW_MEASURE,    'func':self.be.redraw_measure},
                    {'wdg':self.MEDIR,             'func':self.be.medir},                 
                    {'wdg':self.LOAD_M,            'func':self.be.load_m},
                    {'wdg':self.SAVE_M,            'func':self.be.save_m},
                    {'wdg':self.GO_CAL,            'func':self.be.go_cal},
                    {'wdg':self.LOAD_CAL,          'func':self.be.load_cal},
                    {'wdg':self.SAVE_CAL,          'func':self.be.save_cal},
                    {'wdg':self.SAVE_cfg,          'func':self.be.save_config},
                    {'wdg':self.LOAD_fit_data,     'func':self.be.load_m_fit},
                    {'wdg':self.toolButton_load_3, 'func':self.brw.load_fit_data_browser},
                    {'wdg':self.AJUSTA,            'func':self.be.measure_fit},
                    {'wdg':self.LOAD_fit_data_2,   'func':self.be.load_h5_fit},
                    {'wdg':self.VER_ANALISIS,      'func':self.be.load_h5_analisis_selector},  
                    {'wdg':self.CONEXION_1,        'func':self.vi.conectar},    
                    {'wdg':self.GUARDAR_EXCEL,      'func':self.be.load_h5_to_excel},                                                            
                    {'wdg':self.SAVE_fit,          'func':self.be.save_fit},
                    {'wdg':self.SAVE_DB,           'func':self.be.save_measure_to_DB}]

        # Fit calls
        for i in self.fit_param.keys():
            eval("self." + self.fit_param[i]['array'] +".editingFinished").connect(self.be.store_fit)
        for i in clicked:
            i['wdg'].clicked.connect(i['func'])

        # WERG Initialise progressBar and counters.
        self.progressBar.setValue(0)
        self.progressBar_2.setValue(0)        
        self.last_pollo.display(0)
        self.last_medida.display(0)   
        self.last_medida_2.display(0)         

        # Mirrored calls
        for i in self.mirror.keys():
            if self.mirror[i]['qt'] == 'QLineEdit':
                event = 'editingFinished'
            elif self.mirror[i]['qt'] == 'QButtonGroup':
                event = 'buttonClicked'
            elif self.mirror[i]['qt'] == 'QCheckBox':
                event = 'stateChanged'

            for j in self.mirror[i]['array']:
                eval("self." + j + "." + event).connect(self.be.store_data)
        # Other widgets calls
        for i in self.others.keys():
            if self.others[i]['qt'] == 'QLineEdit':
                event = 'editingFinished'
            elif self.others[i]['qt'] == 'QButtonGroup':
                event = 'buttonClicked'
            elif self.others[i]['qt'] == 'QCheckBox':
                event = 'stateChanged'
            eval("self." + self.others[i]['array'] + "." + event).connect(self.be.store_data)
        # Path edit calls
        for i in self.paths.keys():
            eval("self." + self.paths[i] + "." + 'editingFinished').connect(self.be.store_data)


    # Close Window event treatment
    def closeEvent(self, event):
        quit_msg = "¿Seguro que quiere salir del programa?"
        reply = QMessageBox.question(self, 'Cuidado!',
                         quit_msg, QMessageBox.Yes, QMessageBox.No)

        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()

    # MatplotLib Widgets
    def addmpl_1(self, fig):
        # Matplotlib constructor
        self.canvas1 = FigureCanvas(fig)
        self.mpl_1.addWidget(self.canvas1)
        self.canvas1.show()
        self.toolbar = NavigationToolbar(self.canvas1, self.frame_2,
                                         coordinates=True)
        self.mpl_1.addWidget(self.toolbar)
        self.sd.axes['ax0'] = fig.add_subplot(111)
        self.sd.axes['ax1'] = self.sd.axes['ax0'].twinx()
        self.sd.axes['ax0'].tick_params(axis="x", labelsize=8)
        self.sd.axes['ax0'].tick_params(axis="y", labelsize=8)
        self.sd.axes['ax1'].tick_params(axis="x", labelsize=8)
        self.sd.axes['ax1'].tick_params(axis="y", labelsize=8)
        # self.sd.axes['ax2'] = self.sd.axes['ax1'].twinx()


    def addmpl_2(self, fig):
        # Matplotlib constructor
        self.canvas2 = FigureCanvas(fig)
        self.mpl_2.addWidget(self.canvas2)
        self.canvas2.draw()
        self.toolbar = NavigationToolbar(self.canvas2, self.frame_3,
                                         coordinates=True)
        self.mpl_2.addWidget(self.toolbar)
        self.sd.axes['ax2'] = fig.add_subplot(111)
        self.sd.axes['ax3'] = self.sd.axes['ax2'].twinx()
        self.sd.axes['ax2'].tick_params(axis="x", labelsize=8)
        self.sd.axes['ax2'].tick_params(axis="y", labelsize=8)
        self.sd.axes['ax3'].tick_params(axis="x", labelsize=8)
        self.sd.axes['ax3'].tick_params(axis="y", labelsize=8)


    def addmpl_3(self, fig):
        # Matplotlib constructor
        self.canvas3 = FigureCanvas(fig)
        self.mpl_3.addWidget(self.canvas3)
        self.canvas3.draw()
        self.toolbar = NavigationToolbar(self.canvas3, self.frame_5,
                                         coordinates=True)
        self.mpl_3.addWidget(self.toolbar)
        self.sd.axes['ax4'] = fig.add_subplot(111)
        self.sd.axes['ax4'].tick_params(axis="x", labelsize=8)
        self.sd.axes['ax4'].tick_params(axis="y", labelsize=8)

    def addmpl_4(self, fig):
        # Matplotlib constructor
        self.canvas4 = FigureCanvas(fig)
        self.mpl_4.addWidget(self.canvas4)
        self.canvas4.draw()
        self.toolbar = NavigationToolbar(self.canvas4, self.frame_14,
                                         coordinates=True)
        self.mpl_4.addWidget(self.toolbar)
        self.sd.axes['ax5'] = fig.add_subplot(111)
        self.sd.axes['ax5'].tick_params(axis="x", labelsize=8)
        self.sd.axes['ax5'].tick_params(axis="y", labelsize=8)


if __name__ == "__main__":

    app = QtWidgets.QApplication(sys.argv)
    myappid = 'UPV.visa.4294A.1' # arbitrary string
    # ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    app.setWindowIcon(QtGui.QIcon('atun1.jpg'))

    data = DATA(read=False)
    window = MyApp(data)
    window.setWindowIcon(QtGui.QIcon('atun1.jpg'))
    window.addmpl_1(data.fig1)
    window.addmpl_2(data.fig2)
    window.addmpl_3(data.fig3)
    window.addmpl_4(data.fig4)
    window.show()
    sys.exit(app.exec())
