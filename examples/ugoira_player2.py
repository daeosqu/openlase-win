#!python3

import io
import json
import time
import os
import sqlite3
import subprocess
import sys
import tkinter as tk
import zipfile
from contextlib import closing
import functools

from PIL import Image, ImageTk

import pylase as ol
from pixiv_config import *

# for MinGW
if True:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    print = functools.partial(print, flush=True)


def sqlite_dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def pixivutil2_list():
    if not os.path.exists(PIXIVUTIL2_DB):
        return None

    with closing(sqlite3.connect(PIXIVUTIL2_DB)) as conn:
        conn.row_factory = sqlite_dict_factory
        c = conn.cursor()
        c.execute("select * from pixiv_master_image")
        rows = c.fetchall()
        for row in rows:
            print(row)


def pixivutil2_find(id):
    if not os.path.exists(PIXIVUTIL2_DB):
        return None
    with closing(sqlite3.connect(PIXIVUTIL2_DB)) as conn:
        conn.row_factory = sqlite_dict_factory
        c = conn.cursor()
        c.execute("select * from pixiv_master_image where image_id=?", (id,))
        row = c.fetchone()
        if row is None:
            return None
        # print(row.keys())
        return row


def pixivutil2_download(id):
    print(PIXIVUTIL2_EXE)
    commandline = (str(PIXIVUTIL2_EXE), '-s', '2', '-x', str(id))
    print('Runing PixivUtil2...: {}'.format(commandline), file=sys.stderr)
    process = subprocess.run(commandline)
    if process.returncode == 0:
        print('PixivUtil2: success', file=sys.stderr)
        return True
    else:
        print('PixivUtil2: failed, exit code is {}'.format(process.returncode), file=sys.stderr)
        return False


def pixivutil2_fetch_ugo(id):
    row = pixivutil2_find(id)
    if row is None:
        if pixivutil2_download(id):
            row = pixivutil2_find(id)
    if row is None:
        raise Exception('Can not found ugoira data')
    if row['is_manga'] != 'ugoira_view':
        print('warning: {} - "{}" is not a ugoira_view format.'.format(row['image_id'], row['title']), file=sys.stderr)
        raise Exception('Not a ugoira_view format')
    filename = row['save_name']
    print('Pixiv content filename: {}'.format(filename), file=sys.stderr)
    json_filename = os.path.splitext(filename)[0] + '.json'
    with open(json_filename, 'r', encoding='utf-8') as fh:
        meta = json.loads(fh.read())
        if 'Ugoira Data' in meta:
            meta = json.loads(meta['Ugoira Data'])
    with open(filename, 'rb') as fh:
        zip_data = fh.read()
    return meta, zip_data


def trace_ugo(meta, zip_data):
    zipfd = io.BytesIO(zip_data)
    zf = zipfile.ZipFile(zipfd, 'r')

    tracer = None
    frames = []
    images = []

    for frame_meta in meta['frames']:
        im_debug = []
        file_data = zf.open(frame_meta['file']).read()
        fd = io.BytesIO(file_data)
        im = Image.open(fd)
        im_debug.append(to_imagetk(im))
        im = im.convert('I')
        im_debug.append(to_imagetk(im))
        if tracer is None:
            width, height = im.size
            tracer = ol.Tracer(width, height)
            tracer.mode = ol.TRACE_CANNY
            tracer.threshold = 30
            tracer.threshold2 = 10
            tracer.sigma = 1.2
        s = im.tobytes('raw', 'I')
        if len(s) == (width * height * 4):
             s = s[::4] #XXX workaround PIL bug
        objects = tracer.trace(s)
        frames.append(objects)
        images.append(im_debug)

    return (width, height), frames, images


def tk_init():
    global image_window, image_panel

    def close_window(event):
        image_window.withdraw()
        exit()

    image_window = tk.Tk()
    image_panel = tk.Label(image_window)
    image_panel.pack(side="bottom", fill="both", expand="no")
    image_window.bind('<space>', close_window)
    image_window.bind('<Escape>', close_window)


def resize_image(image, maxsize):
    rw = image.size[0]/maxsize[0]
    rh = image.size[1]/maxsize[1]
    ratio = max(rw, rh)
    newsize = (int(image.size[0]/ratio), int(image.size[1]/ratio))
    return image.resize(newsize)


def to_imagetk(im):
    if not isinstance(im, ImageTk.PhotoImage):
        im = resize_image(im, (400, 300))
        im = ImageTk.PhotoImage(im)
    return im


def tk_set_image(im):
    global image_panel
    im = to_imagetk(im)
    image_panel.configure(image=im)
    image_panel.image = im


def tk_run(callback):
    global image_window
    def tk_poll():
        callback()
        image_window.after(1, tk_poll)
    image_window.after(0, tk_poll)
    image_window.mainloop()


def play_ugo(size, frames, meta, images, use_tk=True):
    frame_pts = []
    total_time = 0

    for frame_meta in meta['frames']:
        #print("delay: {}".format(frame_meta['delay'] / 1000.0))
        total_time += frame_meta['delay'] / 1000.0
        frame_pts.append(total_time)

    if ol.init(3) < 0:
        return

    width, height = size

    params = ol.RenderParams()
    params.render_flags = ol.RENDER_GRAYSCALE
    params.on_speed = 1/60.0
    params.off_speed = 1/30.0
    params.end_wait = 2;
    params.start_wait = 12;
    params.flatness = 0.000001
    params.max_framelen = 48000 / 25
    params.min_length = 30
    params.snap = 0.04

    ol.setRenderParams(params)
    ol.loadIdentity()
    ol.scale((2, -2))
    ol.translate((-0.5, -0.5))
    mw = float(max(width, height))
    print(width, height, mw)
    ol.scale((1/mw, 1/mw))
    ol.translate(((mw-width)/2, (mw-height)/2))

    frame = -1
    start_time = None

    DECIMATE = 2

    def animate():
        nonlocal frame, start_time

        if start_time is None:
            if frame == -1:
                frame = 0
                if use_tk:
                    tk_set_image(images[0][1])
                    # first time, show first image and return
                    return 0
            start_time = time.time()

        now = time.time()

        delta_time = now - start_time

        frame_delta = 0
        while delta_time > total_time:
            delta_time -= total_time
            frame_delta += len(frame_pts) - frame
            frame = 0
            start_time = time.time()

        while delta_time > frame_pts[frame]:
            frame_delta += 1
            frame = (frame + 1) % len(frame_pts)

        if frame_delta > 1:
            print("*** skip=%d" % (frame_delta))
        print("t=%.02f frame=%d" % (delta_time, frame))

        if frame_delta > 0 and use_tk:
            tk_set_image(images[frame][1])

        if True or frame_delta > 0:
            objects = frames[frame]
            points = 0
            for o in objects:
                ol.begin(ol.POINTS)
                for point in o[::DECIMATE]:
                    ol.vertex(point, ol.C_WHITE)
                    points += 1
                ol.end()
            #print("%d objects, %d points" % (len(objects), points))
            ol.renderFrame(60)

        delta_time = time.time() - start_time
        next_delay = frame_pts[frame] - delta_time
        return next_delay

    if use_tk:
        global image_window, image_panel

        def tk_poll():
            animate()
            image_window.after(1, tk_poll)

        image_panel.after(0, tk_poll)
        image_window.mainloop()
    else:
        while True:
            animate()

    ol.shutdown()


if __name__ == '__main__':
    #pixivutil2_list()
    use_tk = True
    meta, zip_data = pixivutil2_fetch_ugo(sys.argv[1])
    if use_tk:
        tk_init()
        size, frames, images = trace_ugo(meta, zip_data)
        play_ugo(size, frames, meta, images, use_tk)
