#include <stdio.h>
#include <stdlib.h>

// La función toma dos enteros y devuelve el mayor de los dos (máximo)
int func1(int a, int b) {
    if (a > b) {
        return a;
    } else {
        return b;
    }
}

int main(int argc, char *argv[]) {
    // El ensamblador asume que se pasan al menos dos argumentos, sin comprobar argc
    // Carga argv[1] y argv[2] y los convierte a enteros
    int val1 = atoi(argv[1]);
    int val2 = atoi(argv[2]);

    // Llama a func1 con los dos enteros
    int result = func1(val1, val2);

    // Imprime el resultado (El ensamblador usa %ld aunque opera con registros de 32 bits 'w')
    printf("Result: %ld\n", (long)result);

    return 0;
}
