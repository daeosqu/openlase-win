#include <stdio.h>
#include <libol/libol.h>

int main() {
    printf("LIBOL_VERSION is %s\n", LIBOL_VERSION);
    olInit(1, 2);
    return 0;
}
