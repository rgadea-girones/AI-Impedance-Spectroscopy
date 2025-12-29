#include <vector>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <algorithm>
#include <fstream>
#include <sys/mman.h>
#include <fcntl.h>
#include <unistd.h>
#include <cstring>

// Ajustar esto a la base de la memoria mapeada de la FPGA y tamaño
constexpr off_t FPGA_BASE = 0x40210000;     // ejemplo: sustituir por la tuya
constexpr size_t FPGA_MAP_SIZE = 0x1000; // 4096, suficientes para 512*4 bytes




int main(int argc, char** argv) {
    if (argc != 7) {
        std::cerr << "uso: " << argv[0] << " f1 f2 modo num_puntos fm sweep\n";
        std::cerr << "  modo: 0=lineal, 1=log\n";
        std::cerr << "  sweep: on/off (on=512 con inc1+flip, off=256)\n";
        return 1;
    }

    double f1 = std::atof(argv[1]);
    double f2 = std::atof(argv[2]);
    int modo = std::atoi(argv[3]);          // 0 lineal, 1 log
    int num_puntos = std::atoi(argv[4]);    // n_puntos (puntos_decada en log)
    double fm = std::atof(argv[5]);         // frecuencia de muestreo
    std::string sweep_str = argv[6];        // "on" o "off"

    bool sweep_on = (sweep_str == "on");

    if (num_puntos < 2 || f1 <= 0 || f2 <= 0 || fm <= 0) {
        std::cerr << "argumentos invalidos\n";
        return 2;
    }

    // 1) numero_valores según Python:
    //    - lineal: num_puntos
    //    - log: int((log10(f2) - log10(f1)) * num_puntos)
    int count = (modo == 0)
        ? num_puntos
        : static_cast<int>((std::log10(f2) - std::log10(f1)) * num_puntos);

    if (count < 2) count = 2;

    // 2) Generar frecuencias
    std::vector<double> freq;
    freq.reserve(count);
    if (modo == 0) {
        for (int i = 0; i < count; ++i) {
            double v = f1 + (f2 - f1) * (double(i) / double(count - 1));
            freq.push_back(v);
        }
    } else {
        double log0 = std::log10(f1), log1 = std::log10(f2);
        for (int i = 0; i < count; ++i) {
            double v = std::pow(10.0, log0 + (log1 - log0) * (double(i) / double(count - 1)));
            freq.push_back(v);
        }
    }

    // 3) Filtrar > 40 Hz
    std::vector<double> freq2;
    freq2.reserve(freq.size());
    for (double v : freq) {
        if (v > 40.0) freq2.push_back(v);
    }

    int numero_valores = static_cast<int>(freq2.size());

    // Debug
    std::cerr << "Total frecuencias después de filtrar > 40 Hz: " << freq2.size() << "\n";
    std::cerr << "Sweep mode: " << (sweep_on ? "ON" : "OFF") << "\n";
    if (!freq2.empty()) {
        std::cerr << "Primera freq: " << freq2.front() << " Hz\n";
        std::cerr << "Última freq: " << freq2.back() << " Hz\n";
    }

    // 4) incrementos1 = (freq2 * 2^32) / fm
    const double K = double(1ULL << 32); // cuidado con overflow en 32 bits
    std::vector<double> inc1;
    inc1.reserve(freq2.size());
    for (double v : freq2) {
        inc1.push_back((v * K) / fm);
    }
    
    // Debug incrementos
    if (!inc1.empty()) {
        std::cerr << "Primer incremento: " << inc1.front() << "\n";
        std::cerr << "Último incremento: " << inc1.back() << "\n";
    }

    // 5) Construir vector final según sweep mode
    const double pad_val = 34360000.0;
    std::vector<double> inc;

    if (!sweep_on) {
        // Modo normal: target_len = 256
        const int target_len = 256;
        inc.resize(target_len, pad_val);
        int m = std::min<int>(target_len, static_cast<int>(inc1.size()));
        for (int i = 0; i < m; ++i) inc[i] = inc1[i];
        std::cerr << "Modo 256: relleno con primeros " << m << " incrementos\n";
    } else {
        // Modo sweep: target_len = 512
        // inc1 + flip(inc1) + padding
        const int target_len = 512;
        inc.resize(target_len, pad_val);
        
        int inc1_size = static_cast<int>(inc1.size());
        
        // Copiar inc1 en la primera mitad
        for (int i = 0; i < inc1_size; ++i) {
            inc[i] = inc1[i];
        }
        std::cerr << "Copiados " << inc1_size << " valores de inc1\n";
        
        // Copiar flip(inc1) en la segunda mitad (en orden inverso)
        for (int i = 0; i < inc1_size; ++i) {
            inc[inc1_size + i] = inc1[inc1_size - 1 - i];
        }
        std::cerr << "Copiados " << inc1_size << " valores de flip(inc1)\n";
        
        // El resto se rellena con pad_val (ya inicializado)
        std::cerr << "Modo 512: inc1 + flip(inc1) + padding\n";
    }

    // 6) Escribir en /dev/mem base 0x40210000

    int fd = open("/dev/mem", O_RDWR | O_SYNC);
    if (fd < 0) { perror("open /dev/mem"); return 3; }
    void* map = mmap(nullptr, FPGA_MAP_SIZE, PROT_READ | PROT_WRITE, MAP_SHARED, fd, FPGA_BASE);
    if (map == MAP_FAILED) { perror("mmap"); close(fd); return 4; }
    volatile uint32_t* ptr = reinterpret_cast<volatile uint32_t*>(map);
    
    std::cerr << "Escribiendo a FPGA (" << inc.size() << " valores)...\n";
    std::cerr << "inc[0] (double): " << inc[0] << " -> uint32: " << static_cast<uint32_t>(inc[0]) << "\n";
    
    for (size_t i = 0; i < inc.size(); ++i) {
        ptr[i] = static_cast<uint32_t>(inc[i]);
    }
    
    // Sincronizar la memoria
    msync((void*)map, FPGA_MAP_SIZE, MS_SYNC);
    __sync_synchronize();  // Barrera de memoria
    usleep(100000);        // Esperar 100ms
    
    // Verificar que se escribió correctamente
    std::cerr << "Verificando escritura...\n";
    std::cerr << "ptr[0] leído: 0x" << std::hex << ptr[0] << std::dec << " (" << ptr[0] << ")\n";
    if (inc.size() > 1) {
        std::cerr << "ptr[" << (inc.size()-1) << "] leído: 0x" << std::hex << ptr[inc.size()-1] << std::dec << " (" << ptr[inc.size()-1] << ")\n";
    }
    
    munmap(map, FPGA_MAP_SIZE);
    close(fd);

    std::cout<<"OK\n";
    return 0;
}
