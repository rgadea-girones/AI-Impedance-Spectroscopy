
// ATENCION: LO HE PROBADO Y PARECE QUE NO VA BIEN. HAY QUE REVISARLO.
/* read_mem_prueba_sin_file.c
    Lee memoria desde /dev/mem y escribe a archivo binario o stdout (use '-' para stdout)
    Similar a read_mem.c pero sin usar buffer intermedio en RAM, escribe directamente desde el mmap.
    Esto es una prueba para ver si funciona bien con grandes cantidades de datos.
    */


#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/mman.h>
#include <stdint.h>
#include <string.h>

/* Lee memoria y escribe a archivo binario o stdout (use '-' para stdout) */
int main(int argc, char *argv[]) {
    if (argc < 4) {
        fprintf(stderr, "Uso: %s <direccion_hex> <num_valores> <archivo_salida|- >\n", argv[0]);
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
    if (count > (UINT32_MAX - offset) / word_bytes) {
        fprintf(stderr, "count overflow: offset=%u, count=%u, word_bytes=%u\n", offset, count, word_bytes);
        return 1;
    }
    uint32_t map_len = offset + count * word_bytes;
    
    void *map = mmap(NULL, map_len, PROT_READ, MAP_SHARED, fd, aligned_addr);
    if (map == MAP_FAILED) {
        perror("mmap");
        close(fd);
        return 1;
    }
    
    uint8_t *data_ptr = (uint8_t *)((char *)map + offset);
    uint32_t total_bytes = count * word_bytes;

    fprintf(stderr, "[DEBUG] Leyendo %u valores desde 0x%x (offset=%u, mmap=%p)\n", 
            count, addr, offset, map);

    const uint32_t chunk = 4096;
    uint32_t remaining = total_bytes;
    uint8_t *p = data_ptr;

    if (strcmp(output_file, "-") == 0) {
        // Stream a stdout
        while (remaining > 0) {
            uint32_t n = (remaining < chunk) ? remaining : chunk;
            ssize_t w = write(STDOUT_FILENO, p, n);
            if (w < 0) {
                perror("write(stdout)");
                munmap(map, map_len);
                close(fd);
                return 1;
            }
            p += w;
            remaining -= (uint32_t)w;
        }
    } else {
        // Escribir a archivo
        FILE *fp = fopen(output_file, "wb");
        if (!fp) {
            perror("fopen");
            munmap(map, map_len);
            close(fd);
            return 1;
        }
        while (remaining > 0) {
            uint32_t n = (remaining < chunk) ? remaining : chunk;
            size_t w = fwrite(p, 1, n, fp);
            if (w == 0) {
                perror("fwrite");
                fclose(fp);
                munmap(map, map_len);
                close(fd);
                return 1;
            }
            p += w;
            remaining -= (uint32_t)w;
        }
        fclose(fp);
    }

    // Cerrar mmap/FD
    munmap(map, map_len);
    close(fd);
    
    return 0;
}
