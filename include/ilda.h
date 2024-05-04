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

#ifndef ILD_H
#define ILD_H

#include "libol_common.h"

#if __GNUC__
#define _ATTRIBUTE_PACKED __attribute__((packed))
#else
#define _ATTRIBUTE_PACKED
#endif

#pragma pack(push,1)
struct ilda_hdr {
	uint32_t magic;
	uint8_t pad1[3];
	uint8_t format;
	char name[8];
	char company[8];
	uint16_t count;
	uint16_t frameno;
	uint16_t framecount;
	uint8_t scanner;
	uint8_t pad2;
} _ATTRIBUTE_PACKED;
#pragma pack(pop)

struct color {
	uint8_t r, g, b;
};

#define BLANK 0x40
#define LAST 0x80

#pragma pack(push,1)
struct icoord3d {
	int16_t x;
	int16_t y;
	int16_t z;
	uint8_t state;
	uint8_t color;
} _ATTRIBUTE_PACKED;
#pragma pack(pop)

#pragma pack(push,1)
struct icoord2d {
	int16_t x;
	int16_t y;
	uint8_t state;
	uint8_t color;
} _ATTRIBUTE_PACKED;
#pragma pack(pop)

struct coord3d {
	int16_t x;
	int16_t y;
	int16_t z;
	uint8_t state;
	struct color color;
};

struct frame {
	struct coord3d *points;
	int position;
	int count;
};

typedef struct {
	float x;
	float y;
	float z;
	int is_blank;
	uint8_t color;
} IldaPoint;

typedef struct {
	int count;
	float min_x;
	float max_x;
	float min_y;
	float max_y;
	float min_z;
	float max_z;
	IldaPoint *points;
} IldaFile;

OL_EXPORT IldaFile *olLoadIlda(const char *filename);
OL_EXPORT void olDrawIlda(IldaFile *ild);
OL_EXPORT void olDrawIlda3D(IldaFile *ild);
OL_EXPORT void olFreeIlda(IldaFile *ild);

#endif
