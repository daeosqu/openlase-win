#ifndef __LIBOL_COMMON_H__
#define __LIBOL_COMMON_H__

#include <stdint.h>
#define _STDINT_H

#ifdef _MSC_VER
#ifdef BUILD_LIBOL_DLL
#define OL_EXPORT __declspec(dllexport)
#else
#define OL_EXPORT __declspec(dllimport)
#endif
#else
#define OL_EXPORT
#endif

#endif
