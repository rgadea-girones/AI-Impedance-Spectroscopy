import pandas as pd
import numpy as np
import fit_library as fit
#from statsmodels.tsa.seasonal import seasonal_decompose
#from statsmodels.tsa.api import ExponentialSmoothing, SimpleExpSmoothing, Holt

import matplotlib.pyplot as plt
from MIOPATIA_db import DB_management as db 
from MIOPATIA_dataview import DATA_VIEW as dv


from scipy.interpolate import interp1d

# Supongamos que este es tu array original
original_array = np.random.rand(10, 401, 8)

# Crea un array para almacenar el resultado
interpolated_array = np.empty((201, 3))

# Crea los índices de entrada y salida
x_in = np.geomspace(1, 401, 401)
x_out = np.geomspace(1, 401, 201)

def no_es_primo(n):
    if n <= 1:
        return True
    elif n <= 3:
        return False
    elif n % 2 == 0 or n % 3 == 0:
        return True
    i = 5
    while i * i <= n:
        if n % i == 0 or n % (i + 2) == 0:
            return True
        i += 6
    return False

def show_data_fit_fija_rafa( x_data, funcion, comboBox_fit_alg='trf',pollo_pw=0, medida_pw=0):
    # Posición en el vector de parametros






    def_cfg={'param_fit':{'names' :['n_func_fit','f_low_fit','f_high_fit',
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
                            'float','float','float']}}
    pos_low = np.argwhere(np.array(def_cfg['param_fit']['names'])=='f_low_fit')[0][0]
    pos_high = np.argwhere(np.array(def_cfg['param_fit']['names'])=='f_high_fit')[0][0]
    pos_n_func = np.argwhere(np.array(def_cfg['param_fit']['names'])=='n_func_fit')[0][0]

    A = fit.gompertz()


    x_data = x_data.reshape(-1) 
    funcion = funcion.reshape(-1)       

    index_range = np.where((x_data > def_cfg['param_fit']['value'][pos_low])*
                               (x_data < def_cfg['param_fit']['value'][pos_high]))[0]


    param_n_func =  def_cfg['param_fit']['value'][pos_n_func]
    bounds = np.array(def_cfg['param_fit']['limits'][3:])
    bounds_low = bounds[0:param_n_func*3+1,0]
    bounds_high = bounds[0:param_n_func*3+1,1]
    # print([bounds_low.tolist(),bounds_high.tolist()])
    # print(self.sd.def_cfg['param_fit']['value'][3:4+3*(param_n_func)])

    A(np.log10(funcion[index_range]),
            np.log10(x_data[index_range]),
            param_n_func,
            def_cfg['param_fit']['value'][3:4+3*(param_n_func)],
            method = comboBox_fit_alg,
            bounds = [bounds_low.tolist(),bounds_high.tolist()]
            )
    return A.r_sqr
    # # Main PARAMETERS
    # epsilon_inf    = 10**A.coeff[0]
    # epsilon_alfa   = 10**(A.coeff[0]+np.cumsum(A.coeff[1::3])-A.coeff[1::3]/2)
    # # El término que resta se pone para compensar la última suma que lleva 1/2
    # # y se hace algo similar para el error
    # #10**(A.perr[0]+np.cumsum(A.perr[1::3])-A.perr[1::3]/2)
    # f_alfa         = 10**(A.coeff[2::3]) # Pedro usa /(2.pi)


    # if (np.isnan(A.perr).any()) or (np.isinf(A.perr).any()) :
    #     A.perr = np.zeros(np.shape(A.perr))
    # # Get rid of warnings and errors due to perr NaN and Inf values

    # epsilon_inf_e  = np.log(10)*(10**A.coeff[0])*np.sqrt(A.perr[0])
    # epsilon_alfa_e = np.log(10)*epsilon_alfa*np.sqrt(np.cumsum(A.perr[1::3])-A.perr[1::3]*0.75)
    # f_alfa_e       = np.log(10)*f_alfa*np.sqrt(A.perr[2::3])





    # # Save fit information in Shared Data
    # fit_data_HF = np.zeros((1,35))
    # p_count = 0
    # strt_p  = [0,10,20,21,24,27,28,31,34]
    # strt_count = 0
    # for j in [A.coeff, A.perr, [epsilon_inf], epsilon_alfa, f_alfa,
    #                             [epsilon_inf_e], epsilon_alfa_e, f_alfa_e,
    #                             [A.r_sqr]]:
    #     p_count = strt_p[strt_count]
    #     strt_count = strt_count = strt_count + 1

    #     for i in j:
    #         fit_data_HF[0,p_count] = i
    #         p_count = p_count + 1

    # keys = data.keys()

    # pollo_medida = np.array([pollo_pw,medida_pw]).reshape(1,2)

    # fit_data_HF = np.concatenate([pollo_medida,fit_data_HF],axis=1)

    # fit_data_frame = pd.DataFrame(fit_data_HF,
    #                     columns=['Pollo','Medida','A','B1','C1','D1','B2','C2','D2','B3','C3','D3',
    #                                 'Ae','B1e','C1e','D1e','B2e','C2e','D2e','B3e','C3e','D3e',
    #                                 'EPS_INF','EPS_ALFA1','EPS_ALFA2','EPS_ALFA3',
    #                                 'F_ALFA1','F_ALFA2','F_ALFA3',
    #                                 'EPS_INFe','EPS_ALFA1e','EPS_ALFA2e','EPS_ALFA3e',
    #                                 'F_ALFA1e','F_ALFA2e','F_ALFA3e','R2'])


filename= "COPIA_PANDAS\hdf_28_06_atunes_agilent_201_puntos_clasificados.hdf"
filename1="COPIA_PANDAS\hdf_28_06_atunes_agilent_201_puntos_clasificados.hdf"
filename2= "COPIA_PANDAS\hdf_28_06_atunes_agilent_201_clasificados_filtrado_automatico4_meditado_trainval.hdf"
filename3= "COPIA_PANDAS\hdf_28_06_atunes_agilent_201_clasificados_filtrado_automatico4_meditado_test.hdf"
df = pd.HDFStore(filename,'a',complib="zlib",complevel=4)
df1= pd.HDFStore(filename1,'a',complib="zlib",complevel=4)
df_trainval=pd.HDFStore(filename2,'a',complib="zlib",complevel=4)
df_test=pd.HDFStore(filename3,'a',complib="zlib",complevel=4)

# Crear un DataFrame de ejemplo
pre_p_e  = df.get('data/pollos_estado')
pre_p_e1 = df1.get('data/pollos_estado')    
pre_p_e2 = pd.DataFrame(columns=pre_p_e.columns)
pre_p_e3 = pd.DataFrame(columns=pre_p_e.columns)




datos = df.get('data/tabla')
datos1= df1.get('data/tabla')
datos2 = pd.DataFrame(columns=datos.columns)
datos3 = pd.DataFrame(columns=datos.columns)

# Modificar un valor específico
#pre_p_e.at[4, 'Estado'] = 2
#pre_p_e['Estado'] = pre_p_e['Estado'].astype('int32')

# Modificar una columna entera

max_str_len = 50
df_trainval.put('data/pollos_estado', pre_p_e2, format='table', data_columns=True, min_itemsize={'Primero': max_str_len, 'Ultimo': max_str_len, 'Pollo': max_str_len, 'Medida': max_str_len, 'Fecha': max_str_len, 'Estado': max_str_len})
df_trainval.put('data/tabla', datos2 , format='table', data_columns=True)

df_test.put('data/pollos_estado', pre_p_e3, format='table', data_columns=True, min_itemsize={'Primero': max_str_len, 'Ultimo': max_str_len, 'Pollo': max_str_len, 'Medida': max_str_len, 'Fecha': max_str_len, 'Estado': max_str_len})
df_test.put('data/tabla', datos3 , format='table', data_columns=True)

n_freq=201

#recorrer el dataframe y agregar datos

# for index, row in pre_p_e.iterrows():

#     Primero_ori = int(row['Primero'])
#     Ultimo_ori  = int(row['Ultimo'])
#     Pollo=row['Pollo']
#     pollo=int(Pollo)
#     Medida=row['Medida']
#     medida=int(Medida)
#     fecha_hora=row['Fecha'] 
#     estado  = row['Estado']
#     data_aux=np.array(datos.iloc[Primero_ori:Ultimo_ori+1])
#     Z=data_aux[:,3].reshape(-1,1)
#     freq=data_aux[:,2].reshape(-1,1)
#     fase=data_aux[:,4].reshape(-1,1)
#     #vuelvo a calcular el resto de 6 parametros con los datos fitados
#     Co              = 1E-12   # Valor capacidad en abierto sensor de puntas
#     R_data = Z*np.cos(fase*np.pi/180)
#     X_data = Z*np.sin(fase*np.pi/180)
#     complex_aux         = R_data + X_data*1j
#     admitance_aux       = 1./complex_aux
#     G_data              = np.real(admitance_aux)
#     Cp_data             = np.imag(admitance_aux)/(2*np.pi*freq)
#     Err_data    = (Cp_data/Co).reshape(-1,1)
#     Eri_data    = G_data/(Co*(2*np.pi*freq)).reshape(-1,1)
#     E_data   = Err_data + -1*Eri_data*1j
#     Er_mod_data  = np.abs(E_data).reshape(-1,1)
#     Er_fase_data = np.angle(E_data).reshape(-1,1)

#     if int(estado)<5:
#         if pollo<26:
#             Primero = len(datos2)
#             Ultimo  = Primero + Ultimo_ori - Primero_ori
#             datos_auxiliares= np.concatenate([freq,Z,fase,Err_data,Eri_data,Er_mod_data,Er_fase_data,R_data,X_data],axis=1 )
#             datos_aux = np.concatenate([np.ones((n_freq,1),dtype=int)*(pollo),
#                                                     np.ones((n_freq,1),dtype=int)*(medida),
#                                                     datos_auxiliares],axis=1)
#             data_aux_df = pd.DataFrame(datos_aux,columns=['Pollo','Medida','Freq','Z_mod',
#                                                         'Z_Fase','Err','Eri','E_mod','E_fase','R','X'])
#             pollito=pollo        
#             pollo_aux = np.array([pollito,medida,fecha_hora,estado,Primero,Ultimo]).reshape(1,-1)
#             pollo_aux_df = pd.DataFrame(pollo_aux, columns=['Pollo','Medida','Fecha','Estado','Primero','Ultimo'])        
#             df_trainval.append('data/tabla', data_aux_df)
#             df_trainval.append('data/pollos_estado',pollo_aux_df)
#             datos2 = df_trainval.get('data/tabla')
#         else:
#             Primero = len(datos3)
#             Ultimo  = Primero + Ultimo_ori - Primero_ori
#             datos_auxiliares= np.concatenate([freq,Z,fase,Err_data,Eri_data,Er_mod_data,Er_fase_data,R_data,X_data],axis=1 )
#             datos_aux = np.concatenate([np.ones((n_freq,1),dtype=int)*(pollo),
#                                                     np.ones((n_freq,1),dtype=int)*(medida),
#                                                     datos_auxiliares],axis=1)
#             data_aux_df = pd.DataFrame(datos_aux,columns=['Pollo','Medida','Freq','Z_mod',
#                                                         'Z_Fase','Err','Eri','E_mod','E_fase','R','X'])
#             pollito=pollo-25
#             pollo_aux = np.array([pollito,medida,fecha_hora,estado,Primero,Ultimo]).reshape(1,-1)
#             pollo_aux_df = pd.DataFrame(pollo_aux, columns=['Pollo','Medida','Fecha','Estado','Primero','Ultimo'])        
#             df_test.append('data/tabla', data_aux_df)
#             df_test.append('data/pollos_estado',pollo_aux_df)
#             datos3 = df_test.get('data/tabla')
pollito_trainval=1
pollito_test=1
medida=0
for index, row in pre_p_e1.iterrows():

    Primero_ori = int(row['Primero'])
    Ultimo_ori  = int(row['Ultimo'])
    Pollo=row['Pollo']
    pollo=int(Pollo)
    Medida=row['Medida']
    # medida=int(Medida)
    fecha_hora=row['Fecha'] 
    estado  = row['Estado']
    data_aux=np.array(datos1.iloc[Primero_ori:Ultimo_ori+1])
    Z=data_aux[:,3].reshape(-1,1)
    freq=data_aux[:,2].reshape(-1,1)
    fase=data_aux[:,4].reshape(-1,1)
    #vuelvo a calcular el resto de 6 parametros con los datos fitados
    Co              = 1E-12   # Valor capacidad en abierto sensor de puntas
    R_data = Z*np.cos(fase*np.pi/180)
    X_data = Z*np.sin(fase*np.pi/180)
    complex_aux         = R_data + X_data*1j
    admitance_aux       = 1./complex_aux
    G_data              = np.real(admitance_aux)
    Cp_data             = np.imag(admitance_aux)/(2*np.pi*freq)
    Err_data    = (Cp_data/Co).reshape(-1,1)
    Eri_data    = G_data/(Co*(2*np.pi*freq)).reshape(-1,1)
    E_data   = Err_data + -1*Eri_data*1j
    Er_mod_data  = np.abs(E_data).reshape(-1,1)
    Er_fase_data = np.angle(E_data).reshape(-1,1)

    error=show_data_fit_fija_rafa(freq,Err_data,'trf')


    if error>0.90 and error<1:
        if no_es_primo(pollo):
            Primero = len(datos2)
            Ultimo  = Primero + Ultimo_ori - Primero_ori
            datos_auxiliares= np.concatenate([freq,Z,fase,Err_data,Eri_data,Er_mod_data,Er_fase_data,R_data,X_data],axis=1 )
            datos_aux = np.concatenate([np.ones((n_freq,1),dtype=int)*(pollo),
                                                    np.ones((n_freq,1),dtype=int)*(medida),
                                                    datos_auxiliares],axis=1)
            data_aux_df = pd.DataFrame(datos_aux,columns=['Pollo','Medida','Freq','Z_mod',
                                                        'Z_Fase','Err','Eri','E_mod','E_fase','R','X'])
            pollo_aux = np.array([pollito_trainval,medida,fecha_hora,estado,Primero,Ultimo]).reshape(1,-1)
            pollo_aux_df = pd.DataFrame(pollo_aux, columns=['Pollo','Medida','Fecha','Estado','Primero','Ultimo'])        
            df_trainval.append('data/tabla', data_aux_df)
            df_trainval.append('data/pollos_estado',pollo_aux_df)
            datos2 = df_trainval.get('data/tabla')
            pollito_trainval=pollito_trainval+1
        else:
            Primero = len(datos3)
            Ultimo  = Primero + Ultimo_ori - Primero_ori
            datos_auxiliares= np.concatenate([freq,Z,fase,Err_data,Eri_data,Er_mod_data,Er_fase_data,R_data,X_data],axis=1 )
            datos_aux = np.concatenate([np.ones((n_freq,1),dtype=int)*(pollo),
                                                    np.ones((n_freq,1),dtype=int)*(medida),
                                                    datos_auxiliares],axis=1)
            data_aux_df = pd.DataFrame(datos_aux,columns=['Pollo','Medida','Freq','Z_mod',
                                                        'Z_Fase','Err','Eri','E_mod','E_fase','R','X'])

            pollo_aux = np.array([pollito_test,medida,fecha_hora,estado,Primero,Ultimo]).reshape(1,-1)
            pollo_aux_df = pd.DataFrame(pollo_aux, columns=['Pollo','Medida','Fecha','Estado','Primero','Ultimo'])        
            df_test.append('data/tabla', data_aux_df)
            df_test.append('data/pollos_estado',pollo_aux_df)
            datos3 = df_test.get('data/tabla')
            pollito_test=pollito_test+1
        # else:  borro el pollo 0 que no sirve en agilent_atunes
        #     Primero = len(datos3)
        #     Ultimo  = Primero + Ultimo_ori - Primero_ori
        #     datos_auxiliares= np.concatenate([freq,Z,fase,Err_data,Eri_data,Er_mod_data,Er_fase_data,R_data,X_data],axis=1 )
        #     datos_aux = np.concatenate([np.ones((n_freq,1),dtype=int)*(pollo),
        #                                             np.ones((n_freq,1),dtype=int)*(medida),
        #                                             datos_auxiliares],axis=1)
        #     data_aux_df = pd.DataFrame(datos_aux,columns=['Pollo','Medida','Freq','Z_mod',
        #                                                 'Z_Fase','Err','Eri','E_mod','E_fase','R','X'])
        #     pollito=25
        #     pollo_aux = np.array([pollito,medida,fecha_hora,estado,Primero,Ultimo]).reshape(1,-1)
        #     pollo_aux_df = pd.DataFrame(pollo_aux, columns=['Pollo','Medida','Fecha','Estado','Primero','Ultimo'])        
        #     df_test.append('data/tabla', data_aux_df)
        #     df_test.append('data/pollos_estado',pollo_aux_df)
        #     datos3 = df_test.get('data/tabla')

# Convertir la columna 'Pollo' a números
pre_p_e2  = df_trainval.get('data/pollos_estado')
pre_p_e3 = df_test.get('data/pollos_estado')  
pollo_numeros = pd.to_numeric(pre_p_e2['Pollo'], errors='coerce')

estados0_trainval=pre_p_e2[pre_p_e2['Estado']=='0'].shape[0]
estados1_trainval=pre_p_e2[pre_p_e2['Estado']=='1'].shape[0]
estados2_trainval=pre_p_e2[pre_p_e2['Estado']=='2'].shape[0]
estados3_trainval=pre_p_e2[pre_p_e2['Estado']=='3'].shape[0]
estados4_trainval=pre_p_e2[pre_p_e2['Estado']=='4'].shape[0]

# Obtener el valor máximo
max_pollo = pollo_numeros.max()

print("pollos en train",max_pollo)
print("estados0_trainval",estados0_trainval)
print("estados1_trainval",estados1_trainval)
print("estados2_trainval",estados2_trainval)
print("estados3_trainval",estados3_trainval)
print("estados4_trainval",estados4_trainval)

# Convertir la columna 'Pollo' a números
pollo_numeros2 = pd.to_numeric(pre_p_e3['Pollo'], errors='coerce')

estados0_test=pre_p_e3[pre_p_e3['Estado']=='0'].shape[0]
estados1_test=pre_p_e3[pre_p_e3['Estado']=='1'].shape[0]
estados2_test=pre_p_e3[pre_p_e3['Estado']=='2'].shape[0]
estados3_test=pre_p_e3[pre_p_e3['Estado']=='3'].shape[0]
estados4_test=pre_p_e3[pre_p_e3['Estado']=='4'].shape[0]

# Obtener el valor máximo
max_pollo2 = pollo_numeros2.max()

print("pollos en test",max_pollo2)
print("estados0_test",estados0_test)
print("estados1_test",estados1_test)
print("estados2_test",estados2_test)
print("estados3_test",estados3_test)
print("estados4_test",estados4_test)
# Cerrar el archivo original
df.close
df1.close
df_trainval.close
df_test.close
