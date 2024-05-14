/*
 * Compatibility header for openlase
 */
#ifndef __OL_COMPAT_H__
#define __OL_COMPAT_H__

//#define NOMINMAX
//#define _USE_MATH_DEFINE

/* Common definitions */
#include <stdint.h>
#define _STDINT_H

#include <time.h>

#ifdef _MSC_VER
/* for Visual C */

#include <process.h>
#include <windows.h>

/*#define pid_t int*/
# if defined __MINGW64__
    typedef __int64 pid_t;
# else
    typedef int pid_t;
#endif

#define getpid _getpid
/*#define random rand*/
#define sleep_millis(n) Sleep(n)
#define sleep(n) Sleep(n * 1000)

#define NULL_DEVICE "nul"

#else
/* for POSIX-ly system */

#if defined(__MINGW32__) || defined(__MINGW64__)
#define random rand
#endif

#include <unistd.h>
#include <sys/param.h>

#define sleep_millis(n) usleep(n * 1000)

#endif /* _MSC_VER */

#ifndef MAX
#define MAX(a, b) (((a) > (b)) ? (a) : (b))
#define MIN(a, b) (((a) < (b)) ? (a) : (b))
#endif

#endif
