# Lectura Directa de Memoria en RedPitaya

## Cambios Realizados

Se ha reemplazado la lectura SCPI tradicional (`ACQ:RESULT1:DATA?` y `ACQ:RESULT2:DATA?`) con una función nueva que lee directamente desde las direcciones de memoria FPGA.

### Líneas Reemplazadas
- **Línea original ~3738**: Se sustituyó `self.tx_txt('ACQ:RESULT1:DATA?')` y su lectura por `self.read_memory_direct(address=0x40210000, num_samples=256)`
- **Línea original ~3747**: Se sustituyó `self.tx_txt('ACQ:RESULT2:DATA?')` y su lectura por `self.read_memory_direct(address=0x40210400, num_samples=256)`

## Nueva Función: `read_memory_direct()`

```python
def read_memory_direct(self, address=0x40210000, num_samples=256):
    """
    Lee datos directamente desde una dirección de memoria en RedPitaya.
    Intenta múltiples métodos para compatibilidad con diferentes configuraciones.
    """
```

### Parámetros
- `address`: Dirección de memoria base (default: `0x40210000` para RESULT1)
- `num_samples`: Número de muestras a leer (default: 256)

### Direcciones de Memoria
- **RESULT1**: `0x40210000` - Primera canal de resultados (256 muestras = 1024 bytes = 0x400)
- **RESULT2**: `0x40210400` - Segunda canal de resultados

## Configuración de Direcciones

Las direcciones fueron calculadas como:
```
RESULT1_BASE = 0x40210000
RESULT2_BASE = RESULT1_BASE + (256 * 4 bytes) = 0x40210000 + 0x400 = 0x40210400
```

**IMPORTANTE**: Verifica que estas direcciones coincidan con tu configuración FPGA específica. Puedes:

1. Revisar el archivo de device tree de tu bitstream
2. Usar `devmem2` en RedPitaya para verificar:
   ```bash
   devmem2 0x40210000 32 256  # Leer 256 words de 32 bits
   ```
3. Consultar la documentación de tu bitstream FPGA

## Alternativas de Implementación

### Opción A: Usar SSH/Paramiko directamente (ya implementado en el código)
```python
# En RedPitaya:
from plumbum.machines.paramiko_machine import ParamikoMachine
veamos = ParamikoMachine(self.host, user="root", password="root")
# Ejecutar devmem2 remotamente
```

### Opción B: Si necesitas máxima velocidad
Puedes crear una función alternativa usando `devmem2` vía SSH:

```python
def read_memory_via_devmem(self, address=0x40210000, num_samples=256):
    """Lee memoria usando devmem2 en RedPitaya (SSH)"""
    try:
        veamos = ParamikoMachine(self.host, user="root", password="root")
        cmd = f"devmem2 {hex(address)} 32 {num_samples}"
        result = veamos[cmd]()
        # Parsear resultado
        return np.array([int(x, 16) for x in result.split() if x])
    except Exception as e:
        print(f"Error con devmem2: {e}")
        return np.array([])
```

### Opción C: Acceso directo a través de mmap
Si quieres implementar acceso mediante memory-mapped files:

```python
def read_memory_mmap(self, address=0x40210000, num_samples=256):
    """Lee memoria directa via mmap (requiere /dev/mem en RedPitaya)"""
    import mmap
    try:
        with open('/dev/mem', 'rb') as f:
            with mmap.mmap(f.fileno(), num_samples*4, offset=address) as m:
                data = m.read(num_samples * 4)
                return np.frombuffer(data, dtype=np.float32)
    except Exception as e:
        print(f"Error con mmap: {e}")
        return np.array([])
```

## Testing y Validación

Para verificar que la lectura funciona correctamente:

```python
# En tu código de prueba:
buff_test = self.read_memory_direct(address=0x40210000, num_samples=256)
print(f"Datos leídos: {len(buff_test)} muestras")
print(f"Primeros valores: {buff_test[:10]}")
print(f"Estadísticas: min={buff_test.min()}, max={buff_test.max()}, mean={buff_test.mean()}")
```

## Notas Importantes

1. **Timeout**: La función maneja timeouts de lectura de socket (0.5s por defecto). Ajusta si es necesario.

2. **Formato de datos**: Se asume que los datos están en formato `float32` (IEEE 754). Si son otro formato (int32, double, etc.), ajusta `dtype=` en la función.

3. **Endianness**: Se asume little-endian. Para big-endian usa `dtype='>f'` en lugar de `np.float32`.

4. **Persistencia**: Verifica que el socket se mantenga abierto durante toda la lectura. La función restaura automáticamente el timeout original.

5. **Errores**: Si obtienes arrays vacíos, revisa:
   - La dirección de memoria es correcta
   - El servidor SCPI está corriendo
   - La conexión socket está activa
   - Los datos están efectivamente en esa dirección de memoria

## Rollback (Si necesitas volver al método anterior)

Si quieres volver a usar los comandos SCPI originales, busca "# Lectura directa de memoria" y reemplaza por:

```python
self.tx_txt('ACQ:RESULT1:DATA?')
buff_string = self.rx_txt()
buff_string = buff_string.strip('{}\n\r').replace("  ", "").split(',')
buff = list(map(float, buff_string))
my_array = np.asarray(buff)
```

---

**Última actualización**: Diciembre 26, 2025
**Versión de función**: read_memory_direct v1.0
