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

#ifndef LIBOL_LIBOL_H
#define LIBOL_LIBOL_H

#ifdef __cplusplus
extern "C" {
#endif

#include "libol/libol_export.h"
#include "libol/libol_compat.h"
#include "libol/libol_config.h"

enum {
	OL_LINESTRIP,
	OL_BEZIERSTRIP,
	OL_POINTS,
};

#define C_RED   0xff0000
#define C_GREEN 0x00ff00
#define C_BLUE  0x0000ff
#define C_WHITE 0xffffff
#define C_BLACK 0x000000

#define CLAMP(a,b,c) (((a)<(b))?(b):((a)>(c)?(c):(a)))

#define C_GREY(x)   (0x010101 * CLAMP((int)(x), 0, 255))
#define C_RED_I(x)   (0x010000 * CLAMP((int)(x), 0, 255))
#define C_GREEN_I(x)   (0x000100 * CLAMP((int)(x), 0, 255))
#define C_BLUE_I(x)   (0x000001 * CLAMP((int)(x), 0, 255))

enum {
	RENDER_GRAYSCALE = 1,
	RENDER_NOREORDER = 2,
	RENDER_NOREVERSE = 4,
	RENDER_CULLDARK = 8,
};

#define OL_MAX_OUTPUTS 16

typedef struct {
	int buffer_count;
	int max_points;
	int num_outputs;
} OLConfig;

typedef struct {
	int rate;
	float on_speed;
	float off_speed;
	int start_wait;
	int start_dwell;
	int curve_dwell;
	int corner_dwell;
	int end_dwell;
	int end_wait;
	float curve_angle;
	float flatness;
	float snap;
	int render_flags;
	int min_length;
	int max_framelen;
	float z_near;
} OLRenderParams;

typedef struct {
	int objects;
	int points;
	int resampled_points;
	int resampled_blacks;
	int padding_points;
} OLFrameInfo;

LIBOL_EXPORT int olInit(int buffer_count, int max_points);
LIBOL_EXPORT int olInit2(const OLConfig *config);

LIBOL_EXPORT void olSetRenderParams(OLRenderParams *params);
LIBOL_EXPORT void olGetRenderParams(OLRenderParams *params);

LIBOL_EXPORT void olSetOutput(int output);

typedef void (*AudioCallbackFunc)(float *leftbuf, float *rightbuf, int samples);

LIBOL_EXPORT void olSetAudioCallback(AudioCallbackFunc f);

LIBOL_EXPORT void olLoadIdentity(void);
LIBOL_EXPORT void olPushMatrix(void);
LIBOL_EXPORT void olPopMatrix(void);

LIBOL_EXPORT void olMultMatrix(float m[9]);
LIBOL_EXPORT void olRotate(float theta);
LIBOL_EXPORT void olTranslate(float x, float y);
LIBOL_EXPORT void olScale(float sx, float sy);

LIBOL_EXPORT void olLoadIdentity3(void);
LIBOL_EXPORT void olPushMatrix3(void);
LIBOL_EXPORT void olPopMatrix3(void);

LIBOL_EXPORT void olMultMatrix3(float m[16]);
LIBOL_EXPORT void olRotate3X(float theta);
LIBOL_EXPORT void olRotate3Y(float theta);
LIBOL_EXPORT void olRotate3Z(float theta);
LIBOL_EXPORT void olTranslate3(float x, float y, float z);
LIBOL_EXPORT void olScale3(float sx, float sy, float sz);

LIBOL_EXPORT void olFrustum (float left, float right, float bot, float ttop, float near, float far);
LIBOL_EXPORT void olPerspective(float fovy, float aspect, float zNear, float zFar);

LIBOL_EXPORT void olResetColor(void);
LIBOL_EXPORT void olMultColor(uint32_t color);
LIBOL_EXPORT void olPushColor(void);
LIBOL_EXPORT void olPopColor(void);

LIBOL_EXPORT void olBegin(int prim);
LIBOL_EXPORT void olVertex(float x, float y, uint32_t color);
LIBOL_EXPORT void olVertex3(float x, float y, float z, uint32_t color);
LIBOL_EXPORT void olVertex2Z(float x, float y, float z, uint32_t color);
LIBOL_EXPORT void olEnd(void);

LIBOL_EXPORT void olTransformVertex(float *x, float *y);
LIBOL_EXPORT void olTransformVertex3(float *x, float *y, float *z);
LIBOL_EXPORT void olTransformVertex4(float *x, float *y, float *z, float *w);

typedef void (*ShaderFunc)(float *x, float *y, uint32_t *color);
typedef void (*Shader3Func)(float *x, float *y, float *z, uint32_t *color);

LIBOL_EXPORT void olSetVertexPreShader(ShaderFunc f);
LIBOL_EXPORT void olSetVertexShader(ShaderFunc f);
LIBOL_EXPORT void olSetVertex3Shader(Shader3Func f);

LIBOL_EXPORT void olSetPixelShader(ShaderFunc f);
LIBOL_EXPORT void olSetPixel3Shader(Shader3Func f);

LIBOL_EXPORT void olRect(float x1, float y1, float x2, float y2, uint32_t color);
LIBOL_EXPORT void olLine(float x1, float y1, float x2, float y2, uint32_t color);
LIBOL_EXPORT void olDot(float x, float y, int points, uint32_t color);

LIBOL_EXPORT float olRenderFrame(int max_fps);

LIBOL_EXPORT void olGetFrameInfo(OLFrameInfo *info);

LIBOL_EXPORT void olShutdown(void);

LIBOL_EXPORT void olSetScissor (float x0, float y0, float x1, float y1);

LIBOL_EXPORT void olLog(const char *fmt, ...);

typedef void (*LogCallbackFunc)(const char *msg);

LIBOL_EXPORT void olSetLogCallback(LogCallbackFunc f);

#ifdef __cplusplus
}  // extern "C"
#endif

#endif
