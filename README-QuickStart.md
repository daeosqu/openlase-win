# QuickStart

Quick start manual for OpenLase-win

## Requirements

Install OpenLase-win and download and install required software.

- [JACK 1.9.22 win64](https://github.com/jackaudio/jack2-releases/releases/download/v1.9.22/jack2-win64-v1.9.22.exe) JACK Audio Connection Kit for Windows 64bit
- AutoHotkey (v1)
- Python3.11 (C:\opt\python311)
- FFmpeg (`scoop install ffmpeg`)
- [laserdock_jack](https://github.com/daeosqu/laserdock_jack.git) if you have LaserCube

## Setup QjackCtl

1. Run `qjackctl` (`C:/Program Files/JACK2/qjackctl/qjackctl.exe`)
1. Push `Patchbay...` button and load `config/openlase-no-ab-matrix.xml`.
  1. Push `Activate` button.
1. Push `Setup...` button.
  1. Set `Driver` to `portaudio` in Settings tab.
  1. Set parameters.
    - Sample Rate: 48000
    - Frames/Period: 128
  1. Check `Start JACK audio server on application startup` in Misc tab.
  1. `Option` tab.
    1. Check `Activate Patchbay persistence` in Misc tab.
    1. And select file `share/openlase/openlase-laserjack.xml` in openlase directory.
1. Restart qjackctl

Important: Samplerate and bitrate must be same as windows audio device.

Parameters:

| Parameter                   | Value     |          |
|-----------------------------|-----------|----------|
| Driver                      | portaudio |          |
| Realtime                    | YES       |          |
| Interface                   | (default) |          |
| Sample Rate                 | 48000     |          |
| Frames/Period               | 32        | 32 - 256 |
| Periods/Buffer              | (default) |          |
| Use server synchronous mode | YES       |          |
| Verbose message             | YES       |          |

Advanced tab:

| Parameter         | Value                                          |
|-------------------|------------------------------------------------|
| Server Prefix     | jackd -S                                       |
| No Memory Lock    | NO                                             |
| Unlock Memory     | NO                                             |
| Audio             | Duplex                                         |
| Dither            | None                                           |
| Output Device     | (default)                                      |
| Input Device      | (default)                                      |
| Self connect mode | Don't restrict self connect requests (default) |
| Other Parameters  | (default)                                      |


## Setup windows from OpenLase installer

1. Run `openlase-X.Y.Z-win64.exe` or `openlase-X.Y.Z-win64.msi`
1. Run `Openlase-X.Y.Z` from start menu.
1. Install wheel package with pip (optional, if you want python extension)
  ```
  pip install c:\program files\openlase-X.Y.Z\share\openlase\wheel\pylase-X.Y.Z.2-cp39-abi3-win_amd64.whl
  ```

## Start OpenLase environment

Type `olstart` in Openlase terminal to start OpenLase environment. This will start Jack Audio server and simulator.

```powershel
olstart
```

## Run simple exaple

```
simple
```

## Play bad Apple

動画をダウンロードするには `oldownload` コマンドを使用します。

```
oldownload "https://www.nicovideo.jp/watch/sm8628149"
playvid (Get-Item $env:OL_DATA_DIR\media\*sm8628149*.mp4)
```

ダウンロードに失敗する場合は [Upgrade yt_dlp](#upgrade-yt_dlp) を参照してください。

## Bad Apple (Color)

Youtube の場合は ID を指定してダウンロードできます。

```
oldownload "uOyaCOViAPA"
qplayvid (Get-Item $env:OL_DATA_DIR\media\*Bad_Apple*Color*.mp4)
```

## oldownload

```
(venv) PS D:\oldev4\openlase-win-dev> oldownload -h
Usage: oldownload.py [OPTIONS] [ARGS]...

Options:
  -l, --list              List media files
  -t, --title             List media titles
  -p, --play, --playvid2  Play media files with playvid2
  -P, --playvid           Play media files with playvid
  -Q, --qplayvid          Play media files with qplayvid
  -c, --command TEXT      Play media files with specified command
  --migrate               Migrate database
  --force-convert         Force convert
  --force-convert-all     Force convert all
  -v, --verbose           Show detailed metadata before the filename
  --json                  Output entries as JSON
  --id                    Print filenames with id
  -h, --help              Show this message and exit.
```

Forward extra options to the playback tool by placing them after `--`. The
arguments after the separator are passed directly to the selected player.

```
oldownload -Q "https://www.youtube.com/watch?v=a6-MraffDlE" -- -p
```

Play multiple videos by ID with extra options (`--` indicates the pass-through of options to the player).

```
016,028,039,057,061,076,094,099,102 | % { oldownload -Q --id $_ -v -- -p }
```

## Upgrade yt_dlp

If you get error like below, upgrade yt_dlp.

```
WARNING: [youtube] XXXXXXXXXXXX: Signature extraction failed: Some formats may be missing
```

```
pip install -U yt_dlp
```

# ugoira

1. PixivUtil2 の readme を読んでログイン可能である事を確認して下さい。
1. 設定は以下のように変更します。

```~/.local/pixivutil/config.ini
[Network]
useragent = Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0

[Settings]
writeImageJSON = True
writeImageInfo = True

[Authentication]
username = user_xxxx9999
password = XXXXXXXXXXXXXXX
cookie = 99999999_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

ugoira 形式のアニメーションのみ再生できます。
再生可能なうごイラは以下のものがあります。

- 49319675 まんぞくさんのフードファイト
- 46671388 miku 深海少女

https://www.pixiv.net/artworks/<ID> でブラウザで確認してください。

# LaserCube

実機 (LaserCube) で投影するには laserdock_jack.exe を使用します。
simulator を使用した場合と異なるのは laserdock_jack.exe を実行しておく必要があるのと output.exe を使用することです。 output.exe は映像の歪みなどを補正する事ができます。プロジェクターの台形補正と同じ様に LaserCube が投影する映像を補正するのに利用できます。

1. LaserCube に電源を入れて PC と USB 接続します。
1. laserdock_jack を実行します。
1. qplayvid で動画を再生して投影します。

```
start "C:\Program Files\lasershark_hostapp\bin\laserdock_jack.exe"
qplayvid $HOME/.cache/openlase/bad_apple.mp4
```

## Sample rate overrides

OpenLase components now derive their audio playback rate directly from the active JACK server via `olGetJackRate()`.
Set `OL_SAMPLE_RATE` to control the renderer rate supplied to OpenLase. The decoded audio output rate automatically follows the JACK server configuration and no longer needs an `OL_AUDIO_RATE` override.

- ✅ `tools/qplayvid` (C): reads `OL_SAMPLE_RATE` and queries JACK for the audio rate, warning if `OL_AUDIO_RATE` is set.
- ✅ `python -m pylase.qplayvid`: mirrors the C player by warning about `OL_AUDIO_RATE` and probing JACK through `pylase.olGetJackRate()`.
- ❌ `tools/playvid`: still fixed at 48 kHz (pending update).

環境変数 OL_SAMPLE_RATE はレーザー出力デバイスの DAC のサンプリングレートを指定します。通常 20000 ～ 48000 程度です。デフォルトは 48000 です。Jack Audio のサンプリングレートよりも高くすると転送が間に合わなくなり、レーザーの描画が乱れます。DAC のサンプリングレートを超えないように注意してください。DAC に負荷がかかりすぎると破損する可能性があります。一般的には多少超えても問題ありませんが、描画精度が落ちる可能性があります（特に鋭角な動き）。

環境変数 OL_AUDIO_RATE は非推奨になりました。指定しても警告が表示され、JACK サーバーの現在のサンプリングレート (`olGetJackRate()` / `pylase.olGetJackRate()`) が自動的に使用されます。JACK が停止している場合は `OL_SAMPLE_RATE` の値へフォールバックします。

## Extras

| name              | description                                                                                        |
|-------------------|----------------------------------------------------------------------------------------------------|
| cal               | フルカラーの円を映像出力。                                                                         |
| circlescope       | 音に反応して赤い円が変化する映像を出力。                                                           |
| demo              | BGM 付きの OpenLase のデモ。音声と同期した映像を出力する。                                         |
| harp              | レーザーで楽器（ハープ）を投影出力する。                                                           |
| harp.py           | カメラでレーザーをキャプチャして音階を奏でる (動作未確認)。                                        |
| harp2.py          | カメラでレーザーをキャプチャして音階を奏でる (動作未確認)。                                        |
| invert            | 入力を反転反転するツール。                                                                         |
| output            | GUIで入力された座標を変換して出力する為のツール。                                                  |
| playilda          | .ild ファイルを描画出力。                                                                          |
| playvid           | 動画をリアルタイムでトレースして音声と共に描画出力する。                                           |
| qplayvid          | playvid の GUI バージョン。                                                                        |
| scope             | リアルタイムに音に反応して赤い横線が変化する映像を描画出力。                                       |
| simple            | ２つの立方体が回転するアニメーションを描画出力。                                                   |
| simulator         | 描画出力を入力して画面上にレンダリングして表示するシミュレーター。                                 |
| kinect_shadows.py | kinect から得た画像をトレースしてリアルタイムで描画出力する (以前改造して動かしたがソースがない)。 |
| rect.py           | 単純な四角形のトレースを描画出力。                                                                 |
| showsvg.py        | SVG の描画出力。                                                                                   |
| simple.py         | simple.exe の python バージョン。                                                                  |
| svg.py            | showsvg で利用する python ライブラリ。                                                             |
| showtext.py       | 文字列の描画出力。                                                                                 |
| svg2ild.py        | .svg を .ild に変換する。                                                                          |
| tweet.py          | Twitter (旧X) のツイートを描画出力(たぶん)。                                                       |
| ugoira_player.py  | 旧 Pixiv 用のうごイラを描画出力。                                                                  |
| ugoira_player2.py | Pixiv のうごイラを描画出力。                                                                       |
| webcam_shadows.py | カメラの映像をリアルタイムで描画出力。                                                             |
