#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/mman.h>
#include <stdint.h>
#include <string.h>

/* Lee memoria y escribe a archivo binario */
int main(int argc, char *argv[]) {
    if (argc < 4) {
        fprintf(stderr, "Uso: %s <direccion_hex> <num_valores> <archivo_salida>\n", argv[0]);
        return 1;
    }
    
    uint32_t addr = strtoul(argv[1], NULL, 16);
    uint32_t count = strtoul(argv[2], NULL, 10);
    char *output_file = argv[3];
    uint32_t word_bytes = 4;
    
    int fd = open("/dev/mem", O_RDONLY);
    if (fd < 0) {
        perror("open /dev/mem");
        return 1;
    }
    
    uint32_t page_size = sysconf(_SC_PAGE_SIZE);
    uint32_t page_mask = page_size - 1;
    uint32_t aligned_addr = addr & ~page_mask;
    uint32_t offset = addr - aligned_addr;
    uint32_t map_len = offset + count * word_bytes;
    
    void *map = mmap(NULL, map_len, PROT_READ, MAP_SHARED, fd, aligned_addr);
    if (map == MAP_FAILED) {
        perror("mmap");
        close(fd);
        return 1;
    }
    
    uint32_t *data = (uint32_t *)((char *)map + offset);
    uint32_t total_bytes = count * word_bytes;
    
        fprintf(stderr, "[DEBUG] Leyendo %u valores desde 0x%x (offset=%u, mmap=%p)\n", 
            count, addr, offset, map);
    
        // Copiar a buffer intermedio palabra por palabra
        uint32_t *buffer = (uint32_t *)malloc(total_bytes);
    if (!buffer) {
        perror("malloc");
        munmap(map, map_len);
        close(fd);
        return 1;
    }
    
    // Leer palabra por palabra para evitar problemas de acceso
    for (uint32_t i = 0; i < count; i++) {
        buffer[i] = data[i];
        if (i % 64 == 0) {
            fprintf(stderr, "[DEBUG] Leídos %u/%u valores\n", i, count);
        }
    }
    
    fprintf(stderr, "[DEBUG] Lectura completada: %u valores\n", count);
    
    // Ya no necesitamos el mmap
    munmap(map, map_len);
    close(fd);
    
    // Escribir a archivo
    FILE *fp = fopen(output_file, "wb");
    if (!fp) {
        perror("fopen");
        free(buffer);
        return 1;
    }
    
    fprintf(stderr, "[DEBUG] Escribiendo a %s...\n", output_file);
    size_t written = fwrite(buffer, 1, total_bytes, fp);
    fclose(fp);
    free(buffer);
    
    if (written != total_bytes) {
        fprintf(stderr, "Error: escribió %zu de %u bytes\n", written, total_bytes);
        return 1;
    }
    
    fprintf(stderr, "[DEBUG] Archivo creado exitosamente\n");
    
    return 0;
}