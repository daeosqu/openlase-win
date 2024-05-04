/*
        OpenLase - a realtime laser graphics toolkit

Copyright (C) 2009-2011 Hector Martin "marcan" <hector@marcansoft.com>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as published by
the Free Software Foundation, either version 2.1 or version 3.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
*/

#ifndef TRACE_H
#define TRACE_H

#include "libol_common.h"

typedef struct OLTraceCtx OLTraceCtx;

typedef uint32_t icoord;

typedef enum {
	OL_TRACE_THRESHOLD,
	OL_TRACE_CANNY
} OLTraceMode;

typedef struct {
	OLTraceMode mode;
	icoord width, height;
	float sigma;
	unsigned int threshold;
	unsigned int threshold2;
} OLTraceParams;

typedef struct {
	icoord x, y;
} OLTracePoint;

typedef struct {
	unsigned int count;
	OLTracePoint *points;
} OLTraceObject;

typedef struct {
	unsigned int count;
	OLTraceObject *objects;
} OLTraceResult;

OL_EXPORT int olTraceInit(OLTraceCtx **ctx, OLTraceParams *params);
OL_EXPORT int olTraceReInit(OLTraceCtx *ctx, OLTraceParams *params);

OL_EXPORT int olTrace(OLTraceCtx *ctx, uint8_t *src, icoord stride, OLTraceResult *result);
OL_EXPORT void olTraceFree(OLTraceResult *result);

OL_EXPORT void olTraceDeinit(OLTraceCtx *ctx);

#endif
