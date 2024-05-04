#include <stdio.h>
 
__attribute__((constructor))
void init_stdio()
{
    setvbuf(stdout, NULL, _IONBF, 0);
    setvbuf(stderr, NULL, _IONBF, 0);
}
