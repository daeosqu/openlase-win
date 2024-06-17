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

#ifndef LIBOL_TEXT_H
#define LIBOL_TEXT_H

#ifdef __cplusplus
extern "C" {
#endif

#include <stdint.h>
#include <stddef.h>

#include "libol/libol_export.h"

typedef struct {
	int flag;
	float x;
	float y;
} FontPoint;

typedef struct {
	float width;
	const FontPoint *points;
} FontChar;

typedef struct {
	float height;
	float overlap;
	const FontChar *chars;
} Font;

LIBOL_EXPORT Font *olGetDefaultFont(void);
LIBOL_EXPORT float olGetCharWidth(Font *fnt, int c);
LIBOL_EXPORT float olGetStringWidth(Font *fnt, float height, const char *s);
LIBOL_EXPORT float olGetCharOverlap(Font *font, float height);
LIBOL_EXPORT float olDrawChar(Font *fnt, float x, float y, float height, uint32_t color, int c);
LIBOL_EXPORT float olDrawString(Font *fnt, float x, float y, float height, uint32_t color, const char *s);

#ifdef __cplusplus
}
#endif

#endif
