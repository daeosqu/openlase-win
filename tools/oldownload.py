#!python3

import os
import sys
import re
import subprocess
import unicodedata
from pathlib import Path

import click
import jaconv
import yt_dlp
import ffmpeg
from tinydb import TinyDB, Query, where

original_stdout = sys.stdout
sys.stdout = sys.stderr


class MediaManager:
    Row = Query()

    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
    }

    def __init__(self):
        data_dir = os.getenv('OL_DATA_DIR', None)
        if data_dir is None or data_dir.strip() == '':
            self.data_dir = str(Path.home() / '.cache/openlase')
        self.data_dir = Path(data_dir)
        self.db_path = self.data_dir / 'db.json'
        self.cache_dir = self.data_dir / 'cache'
        self.media_dir = self.data_dir / 'media'
        self.db = TinyDB(str(self.db_path))

    def all(self):
        return [MediaFile(self, x) for x in self.db.all()]

    def get_fetch_opts(self):
        return {
            **self.ydl_opts,
            'quiet': True,
            'simulate': True,
        }

    def get_download_opts(self, filepath):
        return {
            **self.ydl_opts,
            'quiet': True,
            'simulate': False,
            'outtmpl': str(filepath).replace('%', '%%'),
        }

    def get_by_id(self, row_id):
        if isinstance(row_id, str):
            row_id = int(row_id)
        elif not isinstance(row_id, int):
            raise ValueError('Not a integer')

        row = self.db.get(doc_id=row_id)
        if row is not None:
            return MediaFile(self, row)
        else:
            return None

    def get(self, url, force=False):
        row = None
        if not force:
            row = self.db.get(self.Row.url == url)
        if force or row is None:
            row = self._get_row_fetch(url)
            if row['url'] != url:
                r = self.db.get(self.Row.url == row['url'])
                if r is not None:
                    row = r
                else:
                    self.add_row(row)
            else:
                self.add_row(row)
        if row is not None:
            return MediaFile(self, row)
        else:
            return None

    def add_row(self, row):
        last_row = self.db.get(doc_id=len(self.db))
        last_doc_id = last_row.doc_id if last_row else 0
        row['id'] = last_doc_id + 1
        self.normalize_row(row)
        self.db.insert(row)

    def _get_row_fetch(self, url):
        with yt_dlp.YoutubeDL(self.get_fetch_opts()) as ydl:
            info = ydl.extract_info(url, download=False)
            print(info)
            row = {
                'id': None,
                'hash': info['id'],
                'url': info['webpage_url'],
                'title': info['title'],
                'ext': info['ext'],
                'filename': None,
            }
            return row

    def prepare_directories(self):
        self.db_path.parent.mkdir(exist_ok=True, parents=True)
        self.cache_dir.mkdir(exist_ok=True, parents=True)
        self.media_dir.mkdir(exist_ok=True, parents=True)

    def normalize_filename(self, filename):
        def h2z(m):
            return jaconv.h2z(m.group(0), kana=False, ascii=True, digit=False)        
        filename = unicodedata.normalize("NFKC", filename)
        filename = filename.strip()
        filename = filename.encode('cp932', errors='replace').decode('cp932')
        filename = re.sub(r'[][(){}<>|#$^&*`"\'?\:;/\\,~%-+]', h2z, filename)
        filename = re.sub(r'[][(){}<>|#$^&*`"\'?\:;/\\,~%-+!@ ]', '_', filename)
        return filename

    def normalize_row(self, row):
        idstr = '{:03d}'.format(row['id'])
        mediakey = row['hash']
        filename = idstr + '.' + mediakey + '.' + self.normalize_filename(row['title']) + '.' + row['ext']

        old = {
            'cache': row['cache'],
            'media': row['media'],
        }

        row['idstr'] = idstr
        row['cache'] = filename
        row['media'] = filename

        def rename_file(key):
            if row[key] != old[key]:
                p = getattr(self, key + '_dir') / old[key]
                if p.exists():
                    p.rename(getattr(self, key + '_dir') / row[key])

        rename_file('cache')
        rename_file('media')

    def normalize_database(self):
        self.db.update(self.normalize_row)


class MediaFile:

    MAX_WIDTH = 1280
    VIDEO_BIT_RATE = '640k'
    MAX_AUDIO_BIT_RATE = 256000

    def __init__(self, mm, row):
        self.mm = mm
        self.row = row

    @property
    def cache_path(self):
        return Path(self.mm.cache_dir / self.row['cache'])

    @property
    def media_path(self):
        return Path(self.mm.media_dir / self.row['media'])

    @property
    def idstr(self):
        return self.row['idstr']

    @property
    def url(self):
        return self.row['url']

    def prepare(self):
        self.mm.prepare_directories()

    def clean(self):
        self.cache_path.unlink(missing_ok=True)

    def delete(self):
        self.media_path.unlink(missing_ok=True)

    def purge(self):
        self.clean()
        self.delete()

    def ensure_cache(self):
        filepath = self.cache_path
        if not filepath.exists():
            print(f'{self.idstr}: download: path={str(filepath)}')
            self.prepare()
            with yt_dlp.YoutubeDL(self.mm.get_download_opts(filepath)) as ydl:
                ydl.download([self.url])

    def get_gpu(self):
        output = subprocess.run(['nvidia-smi', '-L'], stdout=subprocess.PIPE).stdout.decode('utf-8')
        lines = output.split('\n')
        if len(lines) > 0:
            first = lines[0]
            m = re.match(r'GPU 0: (.*)', first)
            if m:
                return m.group(1)
        return None

    def ensure_video(self):
        ifilepath = self.cache_path
        ofilepath = self.media_path

        gpu = self.get_gpu()
        if gpu:
            vcodec = 'h264_nvenc'
        else:
            vcodec = 'libx264'

        if not ofilepath.exists():
            self.ensure_cache()

            print(f'{self.idstr}: convert: path={str(ifilepath)}')
            self.prepare()

            probe = ffmpeg.probe(str(ifilepath))
            video_info = next(s for s in probe['streams'] if s['codec_type'] == 'video')
            audio_info = next(s for s in probe['streams'] if s['codec_type'] == 'audio')

            fps1, fps2 = video_info['r_frame_rate'].split('/')
            fps = float(fps1) / float(fps2)
            print(f'input video fps is {fps}')

            audio_bit_rate = round(float(audio_info['bit_rate']))
            print(f'audio bit rate is {audio_bit_rate}')

            media = ffmpeg.input(str(ifilepath))
            video = media.video
            audio = media.audio

            video = video.filter('scale', 1280, -1,
                                 force_original_aspect_ratio='decrease')

            if fps > 30.1:
                video = video.filter('fps',
                                     fps=min(fps, 30),
                                     round='down')

            media = ffmpeg.concat(video, audio, v=1, a=1)

            output_options = {
                'vcodec': vcodec,
                'acodec': 'aac',
                'b:v': self.VIDEO_BIT_RATE,
            }

            if audio_bit_rate > self.MAX_AUDIO_BIT_RATE:
                output_options['b:a'] = str(self.MAX_AUDIO_BIT_RATE)

            (
                media
                .output(str(ofilepath), **output_options)
                .global_args('-hide_banner')
                .global_args('-hwaccel_device', 'auto')
                .global_args('-hwaccel', 'auto')
                .run()
            )


@click.command(
    context_settings={
        "show_default": True,
        "help_option_names": ["-h", "--help"],
    }
)
@click.option(
    "-l",
    "--list",
    'list_files',
    is_flag=True,
    help="List media files",
)
@click.option(
    "-p",
    "--play",
    "--playvid2",
    'playvid2',
    is_flag=True,
    help="Play media files with playvid2",
)
@click.option(
    "-P",
    "--playvid",
    'playvid',
    is_flag=True,
    help="Play media files with playvid",
)
@click.option(
    "-Q",
    "--qplayvid",
    'qplayvid',
    is_flag=True,
    help="Play media files with qplayvid",
)
@click.option(
    "-c",
    "--command",
    'command',
    help="Play media files with specified command",
)
@click.option(
    "--migrate",
    is_flag=True,
    help="Migrate database",
)
@click.option(
    "--force-convert",
    is_flag=True,
    help="Force convert",
)
@click.option(
    "--id",
    "by_id",
    is_flag=True,
    help="Print filenames with id",
)
@click.argument("args", nargs=-1)
def main(list_files, migrate, playvid, playvid2, qplayvid, command, force_convert, by_id, args):
    mm = MediaManager()

    if migrate:
        mm.normalize_database()

    if list_files:
        if len(args) == 0:
            arr = mm.all()
        else:
            arr = []
        for mf in arr:
            print(str(mf.media_path), file=original_stdout)
    else:
        if playvid:
            command = 'playvid'
        elif playvid2:
            command = 'playvid2'
        elif qplayvid:
            command = 'qplayvid'

        if by_id is not None:
            op = mm.get_by_id
        else:
            op = mm.get

        for url in args:
            mf = op(url)
            if mf is not None:
                if force_convert:
                    mf.delete()
                mf.ensure_video()
                print(str(mf.media_path), file=original_stdout)
                if command:
                    subprocess.run([command, str(mf.media_path)], shell=False)

if __name__ == '__main__':
    main()
