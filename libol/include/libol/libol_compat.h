/*
 * Compatibility header for openlase
 *
 * Usage:
 *   gcc -DNOMINMAX -D_USE_MATH_DEFINE ...
 *
 * #include <stdint.h>
 * #include <time.h>
 * #include <math.h>
 * #include <process.h>
 * #include <windows.h>
 * #include <unistd.h>
 * #include <sys/param.h>
 *
 */
#ifndef LIBOL_LIBOL_COMPAT_H
#define LIBOL_LIBOL_COMPAT_H

#include <stdint.h>
#include <time.h>
#include <math.h>

#ifdef _MSC_VER
#include <process.h>
#include <windows.h>
#else
#include <unistd.h>
#include <sys/param.h>
#endif

#ifdef _MSC_VER
#ifndef M_PI
#define M_PI (3.14159265358979323846)
#endif
typedef int clockid_t;
#define getpid _getpid
#define sleep_millis(n) Sleep(n)
#define sleep(n) Sleep(n * 1000)
#else /* NOT _MSC_VER */
#define sleep_millis(n) usleep(n * 1000)
#endif

#if defined(_MSC_VER) || defined(__MINGW32__) || defined(__MINGW64__)
#define random rand
#define srandom srand
#endif

#ifndef MAX
#define MAX(a, b) (((a) > (b)) ? (a) : (b))
#define MIN(a, b) (((a) < (b)) ? (a) : (b))
#endif

#endif /* LIBOL_LIBOL_COMPAT_H */
