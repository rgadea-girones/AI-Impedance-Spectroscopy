import time
import numpy as np
import pandas as pd
from datetime import datetime

class DB_management(object):
    """ Functions to create, write and read chicken database
    """

    def __init__(self, filename, dataview):
        self.filename = filename
        self.dv = dataview
        try:
            with pd.HDFStore(self.filename,'r',complib="zlib",complevel=4) as self.hdf_db:
                self.dv.append_plus("Acceso a Base de Datos: " + self.filename)
        except EnvironmentError:
            self.dv.append_plus("Base de Datos no encontrada")



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
        try:
            with pd.HDFStore(self.filename,complib="zlib",complevel=4) as hdf_db:
                #rafa: si hay duplicados cogera el último
                # p_e  = hdf_db.get('data/pollos_estado')
                pre_p_e  = hdf_db.get('data/pollos_estado')
                p_e =pre_p_e.drop_duplicates(subset = ['Pollo', 'Medida'],  keep = 'last').reset_index(drop = True)
                t    = hdf_db.get('data/tabla')
                extracto = p_e[(p_e['Pollo']==str(pollo))&(p_e['Medida']==str(medida))]

                if (np.array(extracto).size==0):
                    self.dv.append_plus("Medida no encontrada")
                    ceros = pd.DataFrame(0, index=np.arange(200), columns=['Pollo','Medida','Freq','Z_mod',
                                                    'Z_Fase','Err','Eri','E_mod','E_fase','R','X'])
                    #return_value = pd.DataFrame([])
                    return_value = ceros
                else:
                    Primero = extracto['Primero'].to_numpy(dtype='int')[0]
                    Ultimo  = extracto['Ultimo'].to_numpy(dtype='int')[0]
                    return_value = t.iloc[Primero:Ultimo+1]
        except EnvironmentError:
            self.dv.append_plus("Base de Datos no encontrada")
            return_value = -1

        return return_value
    
    def lee_medida_rafa_BD(self, pollo, medida):
        # Devuelve los datos de la tabla correspondientes con el pollo y la medida en formato DataFrame
        # rafa: modificado para que incluya tambien el estado y poder graficar conociendo el estado
        #tiene fallos que modifique pero que perdi
        try:
            with pd.HDFStore(self.filename,complib="zlib",complevel=4) as hdf_db:
                #rafa: si hay duplicados cogera el último
                # p_e  = hdf_db.get('data/pollos_estado')
                pre_p_e  = hdf_db.get('data/pollos_estado')
                p_e =pre_p_e.drop_duplicates(subset = ['Pollo', 'Medida'],  keep = 'last').reset_index(drop = True)
                t    = hdf_db.get('data/tabla')
                extracto = p_e[(p_e['Pollo']==str(pollo))&(p_e['Medida']==str(medida))]

                if (np.array(extracto).size==0):
                    self.dv.append_plus("Medida %d no encontrada de sujeto %d"% (medida, pollo))
                    ceros = pd.DataFrame(0, index=np.arange(200), columns=['Pollo','Medida','Freq','Z_mod',
                                                    'Z_Fase','Err','Eri','E_mod','E_fase','R','X'])
                    #return_value = pd.DataFrame([])
                    return_value = ceros
                else:
                    Primero = extracto['Primero'].to_numpy(dtype='int')[0]
                    Ultimo  = extracto['Ultimo'].to_numpy(dtype='int')[0]
                    Estado = extracto['Estado'].to_numpy(dtype='int')[0]
                    return_value = t.iloc[Primero:Ultimo+1], Estado
        except EnvironmentError:
            self.dv.append_plus("Base de Datos no encontrada")
            return_value = -1

        return return_value
    def lee_medida_rafa_BD_ale(self, pollo, medida,estado):
        # la base de datos de alejandra puede tener un mismo sujeto y medida varias veces
        # Devuelve los datos de la tabla correspondientes con el pollo y la medida en formato DataFrame
        # rafa: modificado para que incluya tambien el estado y poder graficar conociendo el estado
        try:
            with pd.HDFStore(self.filename,complib="zlib",complevel=4) as hdf_db:
                #rafa: si hay duplicados cogera el último; pero ese filtro lo he quitado por lo explicado anteriormente
                p_e  = hdf_db.get('data/pollos_estado')
                #pre_p_e  = hdf_db.get('data/pollos_estado')
                #p_e =pre_p_e.drop_duplicates(subset = ['Pollo', 'Medida'],  keep = 'last').reset_index(drop = True)
                t    = hdf_db.get('data/tabla')
                #extracto = p_e[(p_e['Pollo']==str(pollo))&(p_e['Medida']==str(medida))]
                extracto = p_e[(p_e['Pollo'] == str(pollo)) & (p_e['Medida'] == str(medida)) & (p_e['Estado'] == str(estado))]
                if (np.array(extracto).size==0):
                    self.dv.append_plus("Medida %d no encontrada de sujeto %d"% (medida, pollo))
                    ceros = pd.DataFrame(0, index=np.arange(200), columns=['Pollo','Medida','Freq','Z_mod',
                                                    'Z_Fase','Err','Eri','E_mod','E_fase','R','X'])
                    #return_value = pd.DataFrame([])
                    return_value = ceros
                else:
                    Primero = extracto['Primero'].to_numpy(dtype='int')[0]
                    Ultimo  = extracto['Ultimo'].to_numpy(dtype='int')[0]
                    Estado = extracto['Estado'].to_numpy(dtype='int')[0]
                    return_value = t.iloc[Primero:Ultimo+1],Estado
        except EnvironmentError:
            self.dv.append_plus("Base de Datos no encontrada")
            return_value = -1

        return return_value   
    def lee_estado_BD(self, pollo, medida):
        # Devuelve los datos de la tabla correspondientes con el pollo y la medida en formato DataFrame
        try:
            with pd.HDFStore(self.filename,complib="zlib",complevel=4) as hdf_db:
                #rafa: si hay duplicados cogera el último
                # p_e  = hdf_db.get('data/pollos_estado')
                pre_p_e  = hdf_db.get('data/pollos_estado')
                p_e =pre_p_e.drop_duplicates(subset = ['Pollo', 'Medida'],  keep = 'last').reset_index(drop = True)
                t    = hdf_db.get('data/tabla')
                extracto = p_e[(p_e['Pollo']==str(pollo))&(p_e['Medida']==str(medida))]

                if (np.array(extracto).size==0):
                    self.dv.append_plus("Medida no encontrada")
                    ceros = pd.DataFrame(0, index=np.arange(200), columns=['Pollo','Medida','Freq','Z_mod',
                                                    'Z_Fase','Err','Eri','E_mod','E_fase','R','X'])
                    #return_value = pd.DataFrame([])
                    return_value = ceros
                else:
                    Estado = extracto['Estado'].to_numpy(dtype='int')[0]
                    return_value = Estado
        except EnvironmentError:
            self.dv.append_plus("Base de Datos no encontrada")
            return_value = -1

        return return_value
    
    def borra_medida_BD(self, pollo, medida): #no implementada aun porque no me convence manipular la base de datos de esta manera
        # Devuelve los datos de la tabla correspondientes con el pollo y la medida en formato DataFrame
        try:
            with pd.HDFStore(self.filename,complib="zlib",complevel=4) as hdf_db:
                pre_p_e  = hdf_db.get('data/pollos_estado')
                p_e =pre_p_e.drop_duplicates(subset = ['Pollo', 'Medida'],  keep = 'last').reset_index(drop = True)
                t    = hdf_db.get('data/tabla')
                extracto = p_e[(p_e['Pollo']==str(pollo))&(p_e['Medida']==str(medida))]

                if (np.array(extracto).size==0):
                    return_value = pd.DataFrame([])
                else:
                    Primero = extracto['Primero'].to_numpy(dtype='int')[0]
                    Ultimo  = extracto['Ultimo'].to_numpy(dtype='int')[0]
                    return_value = t.iloc[Primero:Ultimo+1]
        except EnvironmentError:
            self.dv.append_plus("Base de Datos no encontrada")
            return_value = -1

        return return_value

    def chequea_ultimos(self):
        try:
            with pd.HDFStore(self.filename,'r',complib="zlib",complevel=4) as hdf_db:
                try:
                    pollos = hdf_db.get('data/pollos_estado') #.to_numpy(dtype=float)
                except:
                    last_pollo = 0
                    last_medida = 0
                else:
                    last_pollo = np.max(pollos['Pollo'].to_numpy(dtype='int'))
                    extracto = pollos[(pollos['Pollo']==str(last_pollo))]
                    last_medida = np.max(extracto['Medida'].to_numpy(dtype='int'))
        except EnvironmentError:
            self.dv.append_plus("Base de Datos no encontrada")
            last_pollo = 0
            last_medida = 0

        return last_pollo, last_medida
    def chequea_ultima_medida(self, pollo):
        try:
            with pd.HDFStore(self.filename,'r',complib="zlib",complevel=4) as hdf_db:
                try:
                    pollos = hdf_db.get('data/pollos_estado') #.to_numpy(dtype=float)
                except:
                    last_medida = 0
                else:
 #                   last_pollo = np.max(pollos['Pollo'].to_numpy(dtype='int'))
                    sujeto=str(pollo)
                    extracto = pollos[(pollos['Pollo']==str(pollo))]
                    if (extracto.empty):
                        self.dv.append_plus("Sujeto " + sujeto + " no encontrado en la base de Datos\n")
                        last_medida=0
                    else:
                        last_medida = np.max(extracto['Medida'].to_numpy(dtype='int'))
        except EnvironmentError:
            self.dv.append_plus("Base de Datos no encontrada")
            last_medida = 0

        return last_medida        

    def chequea_ultimo_pollo(self):
        try:
            with pd.HDFStore(self.filename,'r',complib="zlib",complevel=4) as hdf_db:
                try:
                    pollos = hdf_db.get('data/pollos_estado') #.to_numpy(dtype=float)
                except:
                    last_pollo = 0
                else:
                    last_pollo = np.max(pollos['Pollo'].to_numpy(dtype='int'))
        except EnvironmentError:
            self.dv.append_plus("Base de Datos no encontrada")
            last_pollo = 0
        return last_pollo


    def escribe_medida_BD(self, pollo, medida, datos, estado):
        # Introduce una medida en la base de datos. Los datos se añaden a la tabla sin borrar nada
        # (la tabla crece indefinidamente) y se crea una nueva entrada en pollos_estado sin comprobar la
        # existencia de pollos o medidas coincidentes.
        # Si en caso de que la BD se corrompa por introducir entradas coincidentes en pollo y/o medida
        # se puede recuperar eliminando manualmente una de las entradas o reasignando la numeración del pollo
        # El número de medidas por pollo o pollos es totalmente arbitrario

        fecha_hora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        try:
            with pd.HDFStore(self.filename,'a',complib="zlib",complevel=4) as hdf_db:
                n_freq = np.shape(datos)[0]
                datos_aux = np.concatenate([np.ones((n_freq,1),dtype=int)*(pollo),
                                            np.ones((n_freq,1),dtype=int)*(medida),
                                            datos],axis=1)

                data_aux_df = pd.DataFrame(datos_aux,columns=['Pollo','Medida','Freq','Z_mod',
                                                    'Z_Fase','Err','Eri','E_mod','E_fase','R','X'])
                try:
                    t    = hdf_db.get('data/tabla')
                except:
                    Primeri = 0
                    #Empty DataBase
                else:
                    Primeri= len(t)
                Primero=str(Primeri)
                Ultimo  = str(Primeri + n_freq - 1)

                pollo_aux = np.array([pollo,medida,fecha_hora,estado,Primero,Ultimo]).reshape(1,-1)

                pollo_aux_df = pd.DataFrame(pollo_aux, columns=['Pollo','Medida','Fecha','Estado','Primero','Ultimo'])
            
                max_str_len = 50
                #para cambiar el limite de strings en la base de datos
                #pollo_aux_df['Primero'] = pollo_aux_df['Primero'].astype(str)
                hdf_db.append('data/tabla', data_aux_df)
                hdf_db.append('data/pollos_estado', pollo_aux_df,format='table', data_columns=True, min_itemsize={'Primero': max_str_len, 'Ultimo': max_str_len, 'Pollo': max_str_len, 'Medida': max_str_len, 'Fecha': max_str_len, 'Estado': max_str_len})

                pollos = hdf_db.get('data/pollos_estado')
                last_pollo = np.max(pollos['Pollo'].to_numpy(dtype='int'))
                extracto = pollos[(pollos['Pollo']==str(last_pollo))]
                last_medida = np.max(extracto['Medida'].to_numpy(dtype='int'))
        except EnvironmentError:
            self.dv.append_plus("Base de Datos no encontrada")
            last_pollo = 0
            last_medida = 0

        return last_pollo, last_medida
