/*
        OpenLase - a realtime laser graphics toolkit

Copyright (C) 2009-2011 Hector Martin "marcan" <hector@marcansoft.com>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 2 or version 3.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
*/

#include "libol/libol_compat.h"

#include <stdio.h>
#include <errno.h>
#include <string.h>
#include <stdlib.h>
#include <stdarg.h>
#include <math.h>
#include <jack/jack.h>

#include <GL/glut.h>

#ifdef __APPLE__
#include <OpenGL/gl.h>
#include <OpenGL/glu.h>
#else
#include <GL/gl.h>
#include <GL/glu.h>
#endif
#ifdef _MSC_VER
#include <getopt.h>
#endif

#define DEFAULT_FRAMERATE 60

float framerate = DEFAULT_FRAMERATE;

int window;

jack_client_t *client;

typedef jack_default_audio_sample_t sample_t;
typedef jack_nframes_t nframes_t;

jack_port_t *in_x;
jack_port_t *in_y;
jack_port_t *in_r;
jack_port_t *in_g;
jack_port_t *in_b;

nframes_t rate;

#define MIN_HIST_SAMPLES (48 * 10)
#define DEFAULT_HIST_SAMPLES (48 * 50)
#define MAX_HIST_SAMPLES (48 * 200)

#define MAX_BUF_SAMPLES (MAX_HIST_SAMPLES+48000)

typedef struct {
	float x, y, r, g, b;
} bufsample_t;

bufsample_t buffer[MAX_BUF_SAMPLES];

int hist_samples = DEFAULT_HIST_SAMPLES;
int buf_samples = 0;
int buf_widx = 0;

float psize = 2;

int opt_quiet = 0;
int opt_verbose = 0;
int opt_fullscreen = 0;

int my_fprintf(FILE *stream, const char *format, ...) {
    va_list args;
    int result = 0;
    va_start(args, format);
    if (!opt_quiet)
        result = vfprintf(stream, format, args);
    va_end(args);
    return result;
}

int my_printf(const char *format, ...) {
    va_list args;
    int result = 0;
    va_start(args, format);
    if (!opt_quiet)
        result = vprintf(format, args);
    va_end(args);
    return result;
}

#define real_printf printf
#define real_fprintf fprintf
#define printf my_printf
#define fprintf my_fprintf

static int process (nframes_t nframes, void *arg)
{
	sample_t *i_x = (sample_t *) jack_port_get_buffer (in_x, nframes);
	sample_t *i_y = (sample_t *) jack_port_get_buffer (in_y, nframes);
	sample_t *i_r = (sample_t *) jack_port_get_buffer (in_r, nframes);
	sample_t *i_g = (sample_t *) jack_port_get_buffer (in_g, nframes);
	sample_t *i_b = (sample_t *) jack_port_get_buffer (in_b, nframes);

	nframes_t frm;
	for (frm = 0; frm < nframes; frm++) {
		buffer[buf_widx].x = *i_x++;
		buffer[buf_widx].y = *i_y++;
		buffer[buf_widx].r = *i_r++;
		buffer[buf_widx].g = *i_g++;
		buffer[buf_widx].b = *i_b++;

		buf_widx++;
		if (buf_widx >= buf_samples)
			buf_widx = 0;
	}

	return 0;
}

static int bufsize (nframes_t nframes, void *arg)
{
	printf ("the maximum buffer size is now %u\n", nframes);
	return 0;
}

static int srate (nframes_t nframes, void *arg)
{
	rate = nframes;
	if(rate % 1000) {
		real_fprintf(stderr, "error: the sample rate should be a multiple of 1000\n");
		exit(1);
	}
	printf ("Sample rate: %u/sec\n", nframes);
	return 0;
}

static void jack_shutdown (void *arg)
{
	exit (1);
}

static inline void laser_color(float r, float g, float b, float ascale)
{
	if (r < 0)
		r = 0;
	if (g < 0)
		g = 0;
	if (b < 0)
		b = 0;
	if (r > 2.0)
		r = 2.0;
	if (g > 2.0)
		g = 2.0;
	if (b > 2.0)
		b = 2.0;

	float l = (r + g + b) / 3.0f;
	float m = MAX(r,MAX(g,b));

	if (l > 1.0) {
		r = g = b = l - 1.0;
		l = 1.0;
	}
	if ( r > 1.0 )
		r = 1.0;
	if ( g > 1.0 )
		g = 1.0;
	if ( b > 1.0 )
		b = 1.0;
	glColor4f(r, g, b, m*ascale);

}

void draw_gl(void)
{
	int i, ridx;
	static int fno = 0;
	fno++;

#if 1 /* SHOW_FPS */

#define TV_TIMEVAL timespec
#define TV_GETTIMEOFDAY(a) timespec_get(a, TIME_UTC)
#define TV_DIFF(a, b) (a.tv_sec - b.tv_sec + (double)(a.tv_nsec - b.tv_nsec) / 1000000000)

    static struct TV_TIMEVAL last_time_short = { 0, 0 };
    static struct TV_TIMEVAL last_warned = { 0, 0 };
    struct TV_TIMEVAL tv;
    static double fps = 0;
    static int old_fno = 0;
    double diff_time;

    if (last_time_short.tv_sec == 0) {
        TV_GETTIMEOFDAY(&last_time_short);
    }
    TV_GETTIMEOFDAY(&tv);
    diff_time = TV_DIFF(tv, last_time_short);

    if (diff_time > 1.0) {
        fps = (fno - old_fno) / diff_time;
        last_time_short = tv;
        old_fno = fno;

        if (opt_verbose)
            fprintf(stderr, "FPS: %.1f\n", fps);

        double ratio = opt_verbose ? 0.1 : 0.5;
        double minimum_fps = framerate * (1.0 - ratio);
        double diff_time_warned = TV_DIFF(tv, last_warned);
        if (diff_time_warned > 1.0 && fps < minimum_fps) {
            fprintf(stderr, "warning: frame rate slowdown: %.1f < %d - %.1f%\n", fps, (int)framerate, ratio * 100);
            last_warned = tv;
        }
    }

#endif /* SHOW_FPS */

	glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
	glLoadIdentity();
	glLineWidth(psize);
	glPointSize(psize);

	// horrid workaround for recordmydesktop/libtheora brokenness
#if 0
	glBegin(GL_POINTS);
	glColor4f((fno&1) * (64/256.0), (fno&2) * (32/256.0), (fno&4)  * (16/256.0), 1);
	//glColor4f(1,1,1,1);
	glVertex3f(-0.99, -0.74, 0);
	glVertex3f(0.99, 0.74, 0);
	glVertex3f(-0.99, 0.74, 0);
	glVertex3f(0.99, -0.74, 0);
	glEnd();
#endif

	ridx = (buf_widx - hist_samples + buf_samples) % buf_samples;

	float lx, ly, lr, lg, lb;
	lx = ly = lr = lg = lb = 0;

	float rdelay[2] = {0,0};
	float gdelay[2] = {0,0};
	float bdelay[2] = {0,0};

	for (i = 0; i<hist_samples; i++)
	{
		float r, g, b;

		bufsample_t s = buffer[ridx];
		// lowpass
		s.x = lx * 0.65 + s.x * 0.35;
		s.y = ly * 0.65 + s.y * 0.35;
		// delay brightness
		rdelay[i%2] = s.r;
		gdelay[i%2] = s.g;
		bdelay[i%2] = s.b;
		s.r = rdelay[(i+1)%2];
		s.g = gdelay[(i+1)%2];
		s.b = bdelay[(i+1)%2];

		float d = sqrtf((s.x-lx)*(s.x-lx) + (s.y-ly)*(s.y-ly));
		if (d == 0)
			d = 0.0001;
#ifdef NO_CUSTOM_DFACTOR
		float dfactor = 0.01/d;
		if (dfactor > 0.5)
			dfactor = 0.5;
#else
        // I like more brightness
        float dfactor = 0.5/d;
        if (dfactor > 0.9)
            dfactor = 0.9;
#endif

		int age = hist_samples-i;
		float factor;

		factor = (hist_samples-age)/(float)hist_samples;

		//factor = factor*factor;

		if (fabsf(s.x-lx) < 0.001 && fabsf(s.y-ly) < 0.001) {
			r = (s.r-0.2) * factor * 1.4;
			g = (s.g-0.2) * factor * 1.4;
			b = (s.b-0.2) * factor * 1.4;
			glBegin(GL_POINTS);
			laser_color(r, g, b, 0.08);
			glVertex3f(s.x, s.y, 0);
			glEnd();
		} else {
			r = (s.r-0.2) * factor * dfactor * 1.8;
			g = (s.g-0.2) * factor * dfactor * 1.8;
			b = (s.b-0.2) * factor * dfactor * 1.8;
			glBegin(GL_LINES);
			laser_color(lr, lg, lb, 0.8);
			glVertex3f(lx, ly, 0);
			laser_color(r, g, b, 0.8);
			glVertex3f(s.x, s.y, 0);
			glEnd();
		}

		lx = s.x;
		ly = s.y;
		lr = r;
		lg = g;
		lb = b;

		ridx++;
		if (ridx >= buf_samples)
			ridx = 0;
	}
	glEnd();
	glutSwapBuffers();
}

void key_gl(unsigned char key, int x, int y)
{
	if (key == 27) {
		jack_client_close (client);
		glutDestroyWindow(window);
		exit(0);
	}
}

void resize_gl(int width, int height)
{
	int min = width < height ? height : width;
	glViewport((width-min)/2, (height-min)/2, min, min);
	glMatrixMode(GL_PROJECTION);
	glLoadIdentity();
	glOrtho (-1, 1, -1, 1, -1, 1);
	glMatrixMode(GL_MODELVIEW);
	psize = min/350.0;
}

void init_gl(int width, int height)
{
	glClearColor(0.0f, 0.0f, 0.0f, 0.0f);
	glClearDepth(1.0);
	glDepthFunc(GL_LESS);
	glDisable(GL_DEPTH_TEST);
	glEnable(GL_BLEND);
	glBlendFunc (GL_SRC_ALPHA, GL_ONE);
	glEnable(GL_POINT_SMOOTH);
	glEnable(GL_LINE_SMOOTH);
	resize_gl(width, height);
}

void gl_timer(int arg)
{
	glutPostRedisplay();
	glutTimerFunc(1000 / framerate, &gl_timer, 0);
}

void usage(const char *argv0)
{
	real_printf("Usage: %s [options]\n\n", argv0);
	real_printf("Options:\n");
	real_printf("-v          Verbose mode\n");
	real_printf("-q          Very quietly mode\n");
	real_printf("-r FLOAT    Maximum Framerate (default: %d)\n", DEFAULT_FRAMERATE);
	real_printf("-s INTEGER  Histgram Samples [%d-%d] (default: %d)\n", MIN_HIST_SAMPLES, MAX_HIST_SAMPLES, DEFAULT_FRAMERATE);
}

int main (int argc, char *argv[])
{
	static const char jack_client_name[] = "simulator";
	jack_status_t jack_status;
	int optchar;

	setvbuf(stdout, NULL, _IONBF, 0);
	setvbuf(stderr, NULL, _IONBF, 0);

	while ((optchar = getopt(argc, argv, "h?vqFr:s:")) != -1) {
		switch (optchar) {
			case 'h':
			case '?':
				usage(argv[0]);
				return 0;
			case 'q':
                opt_quiet = 1;
                break;
			case 'v':
                opt_verbose = 1;
				break;
			case 'F':
                opt_fullscreen = 1;
				break;
			case 'r':
				framerate = atof(optarg);
				break;
			case 's':
				hist_samples = atoi(optarg);
                if (hist_samples < MIN_HIST_SAMPLES)
                    hist_samples = MIN_HIST_SAMPLES;
                if (hist_samples > MAX_HIST_SAMPLES)
                    hist_samples = MAX_HIST_SAMPLES;
				break;
		}
	}

    buf_samples = hist_samples + 48000;

	if (optind != argc) {
		usage(argv[0]);
		return 1;
	}

    if (opt_verbose)
        fprintf (stderr, "GL frame rate: %.1f FPS\n", framerate);

	glutInit(&argc, argv);

	glutInitDisplayMode(GLUT_RGBA | GLUT_DOUBLE | GLUT_ALPHA | GLUT_DEPTH);
	glutInitWindowSize(640, 640);
	glutInitWindowPosition(0, 0);

	window = glutCreateWindow("OpenLase Simulator");

    if (opt_fullscreen)
        glutFullScreen();

	glutDisplayFunc(&draw_gl);
	glutTimerFunc(0, &gl_timer, 0);
	glutReshapeFunc(&resize_gl);
	glutKeyboardFunc(&key_gl);
	init_gl(640, 640);

	if ((client = jack_client_open(jack_client_name, JackNullOption, &jack_status)) == 0) {
		real_fprintf (stderr, "jack server not running?\n");
		return 1;
	}

	jack_set_process_callback (client, process, 0);
	jack_set_buffer_size_callback (client, bufsize, 0);
	jack_set_sample_rate_callback (client, srate, 0);
	jack_on_shutdown (client, jack_shutdown, 0);

	in_x = jack_port_register (client, "in_x", JACK_DEFAULT_AUDIO_TYPE, JackPortIsInput, 0);
	in_y = jack_port_register (client, "in_y", JACK_DEFAULT_AUDIO_TYPE, JackPortIsInput, 0);
	in_r = jack_port_register (client, "in_r", JACK_DEFAULT_AUDIO_TYPE, JackPortIsInput, 0);
	in_g = jack_port_register (client, "in_g", JACK_DEFAULT_AUDIO_TYPE, JackPortIsInput, 0);
	in_b = jack_port_register (client, "in_b", JACK_DEFAULT_AUDIO_TYPE, JackPortIsInput, 0);

	if (jack_activate (client)) {
		real_fprintf (stderr, "cannot activate client");
		return 1;
	}

	glutMainLoop();
	return 0;
}

