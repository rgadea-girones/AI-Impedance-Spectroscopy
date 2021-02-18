import time
import numpy as np
import pandas as pd
from datetime import datetime

class DB_management(object):
    """ Functions to create, write and read chicken database
    """

    def __init__(self, filename):
        self.filename = filename
        self.hdf_db = pd.HDFStore(self.filename,'a',complib="zlib",complevel=4)
        print(self.hdf_db.info())
        self.hdf_db.close()


    def crea_BD(self):
        # Crea una base de datos con la estructura correcta
        hdf_db = pd.HDFStore(filename,'a',complib="zlib",complevel=4)
        hdf_db.put('data/tabla',pd.DataFrame(columns=['Pollo', 'Medida',
                                                           'Freq',  'Z_mod', 'Z_Fase','Err', 'Eri' ,'E_mod',
                                                           'E_fase','R'    ,'X']), format='table')
        hdf_db.put('data/pollos_estado',pd.DataFrame(columns=['Pollo','Medida',
                                                              'Fecha','Estado','Primero','Ultimo']),format='table')
        hdf_db.put('data/fit',pd.DataFrame( columns=['Pollo','Medida','A', 'B1', 'C1', 'D1',
                                                                           'B2', 'C2', 'D2',
                                                                           'B3', 'C3', 'D3',
                                                                      'Ae','B1e','C1e','D1e',
                                                                           'B2e','C2e','D2e',
                                                                           'B3e','C3e','D3e',
                                                     'EPS_INF','EPS_ALFA1','EPS_ALFA2','EPS_ALFA3',
                                                     'F_ALFA1','F_ALFA2','F_ALFA3',
                                                     'EPS_INFe','EPS_ALFA1e','EPS_ALFA2e','EPS_ALFA3e',
                                                     'F_ALFA1e','F_ALFA2e','F_ALFA3e','R2']), format='table')
        # A partir de los duplicados en 'Pollo' y 'Medida' de pollos_estado podemos reconstruir la BD si hay un
        # error de numeración, simplemente borrando la entrada o renombrando 'Pollo'o 'Medida'
        self.hdf_db.close()


    def llena_BD(self,n_pollos,bueno_malo,excel,filename,pollo_inicial):
        """
            NO USAR: Sólo para rescatar datos de Excel viejas
        """
        # Llena la base de datos con datos de una excel primigenia
        tabla = pd.DataFrame(columns=['Pollo','Medida','Freq','Z_mod','Z_Fase','Err','Eri','E_mod','E_fase','R','X'])
        pollos_estado = pd.DataFrame(columns=['Pollo','Medida','Fecha','Estado','Primero','Ultimo'])

        hdf_db = pd.HDFStore(self.filename,'a',complib="zlib",complevel=4)

        for pollo in range(0,n_pollos):
            for medida in range(0,n_medidas):
                indice_maestro = pollo*n_medidas+medida
                # Creacion del indice para recorrer la Excel
                if (pollo == 0) & (medida == 0):
                    indice = ''
                else:
                    indice = '.'+str(indice_maestro)

                data_aux = np.concatenate([
                        np.ones((n_freq,1),dtype=int)*(pollo + pollo_inicial),np.ones((n_freq,1),dtype=int)*(medida),
                        np.reshape(np.array(excel['Freq'][0:n_freq],dtype=float),(-1,1)),
                        np.reshape(np.array(excel['Z_mod' + indice][0:n_freq],dtype=float),(-1,1)),
                        np.reshape(np.array(excel['Z_Fase' + indice][0:n_freq],dtype=float),(-1,1)),
                        np.reshape(np.array(excel['Err' + indice][0:n_freq],dtype=float),(-1,1)),
                        np.reshape(np.array(excel['Eri' + indice][0:n_freq],dtype=float),(-1,1)),
                        np.reshape(np.array(excel['E_mod' + indice][0:n_freq],dtype=float),(-1,1)),
                        np.reshape(np.array(excel['E_f' + indice][0:n_freq],dtype=float),(-1,1)),
                        np.reshape(np.array(excel['R' + indice][0:n_freq],dtype=float),(-1,1)),
                        np.reshape(np.array(excel['             X' + indice][0:401],dtype=float),(-1,1))
                        ], axis=1)
                data_aux_df = pd.DataFrame(data_aux,columns=['Pollo','Medida','Freq','Z_mod',
                                                    'Z_Fase','Err','Eri','E_mod','E_fase','R','X'])
                #tabla = tabla.append(data_aux_df, ignore_index=True)

                Primero = (indice_maestro + pollo_inicial * n_medidas) * n_freq
                Ultimo  = (indice_maestro + pollo_inicial * n_medidas) * n_freq + n_freq - 1
                pollo_aux = np.array([pollo + pollo_inicial,medida,fecha_hora,bueno_malo,Primero,Ultimo]).reshape(1,-1)
                pollo_aux_df = pd.DataFrame(pollo_aux, columns=['Pollo','Medida','Fecha','Estado','Primero','Ultimo'])
                #pollos_estado = pollos_estado.append(pollo_aux_df,ignore_index=True)

                hdf_db.append('data/tabla', data_aux_df)
                hdf_db.append('data/pollos_estado', pollo_aux_df)
        hdf_db.close()

    def lee_medida_BD(self, pollo, medida):
        # Devuelve los datos de la tabla correspondientes con el pollo y la medida en formato DataFrame

        hdf_db = pd.HDFStore(self.filename,complib="zlib",complevel=4)
        p_e  = hdf_db.get('data/pollos_estado')
        t    = hdf_db.get('data/tabla')
        extracto = p_e[(p_e['Pollo']==str(pollo))&(p_e['Medida']==str(medida))]

        if (np.array(extracto).size==0):
            return_value = -1
        else:
            Primero = extracto['Primero'].to_numpy(dtype='int')[0]
            Ultimo  = extracto['Ultimo'].to_numpy(dtype='int')[0]
            return_value = t.iloc[Primero:Ultimo+1]

        hdf_db.close()

        return return_value


    def escribe_medida_BD(self, pollo, medida, datos, estado):
        # Introduce una medida en la base de datos. Los datos se añaden a la tabla sin borrar nada
        # (la tabla crece indefinidamente) y se crea una nueva entrada en pollos_estado sin comprobar la
        # existencia de pollos o medidas coincidentes.
        # Si en caso de que la BD se corrompa por introducir entradas coincidentes en pollo y/o medida
        # se puede recuperar eliminando manualmente una de las entradas o reasignando la numeración del pollo
        # El número de medidas por pollo o pollos es totalmente arbitrario

        fecha_hora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        hdf_db = pd.HDFStore(self.filename,'a',complib="zlib",complevel=4)
        n_freq = np.shape(datos)[0]

        datos_aux = np.concatenate([np.ones((n_freq,1),dtype=int)*(pollo),
                                    np.ones((n_freq,1),dtype=int)*(medida),
                                   datos],axis=1)

        data_aux_df = pd.DataFrame(datos_aux,columns=['Pollo','Medida','Freq','Z_mod',
                                                    'Z_Fase','Err','Eri','E_mod','E_fase','R','X'])
        t    = hdf_db.get('data/tabla')
        Primero = len(t)
        Ultimo  = Primero + n_freq - 1
        pollo_aux = np.array([pollo,medida,fecha_hora,estado,Primero,Ultimo]).reshape(1,-1)
        pollo_aux_df = pd.DataFrame(pollo_aux, columns=['Pollo','Medida','Fecha','Estado','Primero','Ultimo'])

        hdf_db.append('data/tabla', data_aux_df)
        hdf_db.append('data/pollos_estado', pollo_aux_df)