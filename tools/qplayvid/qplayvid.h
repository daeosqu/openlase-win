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

#ifndef QPLAYVID_H
#define QPLAYVID_H

#ifdef __cplusplus
extern "C" {
#endif

#define IM_BIBUF 0
#define IM_BTBUF 1
#define IM_SIBUF 2
#define IM_STBUF 3
#define IM_SXBUF 4 /* available when mode is canny */
#define IM_SYBUF 5 /* available when mode is canny */
#define IM_SMBUF 6 /* available when mode is canny */
#define IM_GRAY 7
#define IM_COLOR 8

typedef struct PlayerCtx PlayerCtx;

typedef struct {
	int canny;
	int splitthreshold;

	int blur;
	int scale;
	int threshold;
	int threshold2;
	int darkval;
	int lightval;
	int offset;
	int decimation;

	int minsize;
	int startwait;
	int endwait;
	int dwell;
	int offspeed;
	int snap;
	int minrate;
	int overscan;

	int volume;

	int update_debug_images;
} PlayerSettings;

typedef struct {
	float time;
	float ftime;
	int frames;
	int objects;
	int points;
	int resampled_points;
	int resampled_blacks;
	int padding_points;
	double pts;
	int ended;
} PlayerEvent;

typedef void (*PlayerEventCb)(PlayerEvent *ev);

void playvid_init(void);
int playvid_open(PlayerCtx **octx, const char *filename);
void playvid_set_eventcb(PlayerCtx *ctx, PlayerEventCb cb);
void playvid_play(PlayerCtx *ctx);
void playvid_pause(PlayerCtx *ctx);
void playvid_stop(PlayerCtx *ctx);
void playvid_skip(PlayerCtx *ctx);
void playvid_update_settings(PlayerCtx *ctx, PlayerSettings *settings);
double playvid_get_duration(PlayerCtx *ctx);
void playvid_seek(PlayerCtx *ctx, double pos);
uint8_t* playvid_get_image(PlayerCtx *ctx, int index, int *width, int *height, int *stride, int *pix_fmt);

int ol_err(const char* format, ...);
int ol_warn(const char* format, ...);
int ol_info(const char* format, ...);
int ol_verbose(const char* format, ...);
int ol_debug(const char* format, ...);
int ol_debug2(const char* format, ...);

extern int playvid_opt_verbose;

#ifdef __cplusplus
};
#endif

#endif
