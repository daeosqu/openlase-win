# INSTALL

Build and Installation instructions for OpenLase windows.

# REQUIREMENTS

- Windows 11
- Powershell 7
- Visual Studio 2022 Community
- scoop
  - yasm 1.3.0
  - cmake 3.29.2 64bit
  - vcpkg 2024.04.26 64bit
    - ffmpeg4.4.3
    - freeglut3.4.0
    - getopt
    - libmodplug0.8.9.0
    - pdcurses3.9
    - pthreads3.0.0
- Git for Windows 2.44.0.1
- [JACK 1.9.22 win64](https://github.com/jackaudio/jack2-releases/releases/download/v1.9.22/jack2-win64-v1.9.22.exe) JACK Audio Connection Kit for Windows 64bit
- Qt5 5.14.2 (qt-opensource-windows-x86-5.14.2.exe)
- python 3.11.9 (64bit) (3.11 or older)
- [laserdock_jack](https://github.com/daeosqu/laserdock_jack.git)

# Install visual studio

[Visual Studio 2022 Community](https://c2rsetup.officeapps.live.com/c2r/downloadVS.aspx?sku=community&channel=Release&version=VS2022&source=VSLandingPage&cid=2030:9583320712cb4f7982ad59fe836f4b4e) をインストールします。

コンポーネントは以下のコンポーネントを選択します。

- C++ コア機能
- MSVC v143 - VS 2022 C++ x64/x86 ビルドツール (最新)
- Windows 11 SDK (10.0.22621.0)

コンポーネントの選択とインストールは以下の構成ファイルを Visual Studio Installer で読み込むことでも可能です。

```json:requirements.vsconfig
{
  "version": "1.0",
  "components": [
    "Microsoft.VisualStudio.Component.CoreEditor",
    "Microsoft.VisualStudio.Workload.CoreEditor",
    "Microsoft.VisualStudio.Component.VC.CoreIde",
    "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
    "Microsoft.VisualStudio.Component.Windows11SDK.22621",
    "Microsoft.VisualStudio.ComponentGroup.WebToolsExtensions.CMake"
  ],
  "extensions": []
}
```

# Install Qt, Git, Scoop

以下のアプリケーションをインストールします。

- [Qt5 x86-5.14.2 (qt-opensource-windows-x86-5.14.2.exe)](https://download.qt.io/archive/qt/5.14/5.14.2/qt-opensource-windows-x86-5.14.2.exe)
- [Git for Windows](https://gitforwindows.org/)
- [Scoop](https://scoop.sh/)

# Install cmake, vcpkg, yasm

```powershell
scoop install cmake vcpkg yasm
```

# Install python3

Python3 を C:\opt\python311 にインストールを行います。

```powershell
$TargetVer="3.11.9"
$Arch="-amd64"
$TargetDir="C:\opt\python311"
$py_url="https://www.python.org/ftp/python/${TargetVer}/python-${TargetVer}${Arch}.exe"

Invoke-WebRequest "$py_url" -OutFile "$env:USERPROFILE\Downloads\python-${TargetVer}${Arch}.exe"

. $env:USERPROFILE\Downloads\python-${TargetVer}${Arch}.exe InstallAllUsers=0 TargetDir=$TargetDir AssociateFiles=0 CompileAll=0 PrependPath=0 Shortcuts=0 Include_doc=0 Include_debug=1 Include_dev=1 Include_exe=1 Include_launcher=0 InstallLauncherAllUsers=0 Include_lib=1 Include_pip=1 Include_symbols=1 Include_tcltk=1 Include_test=0 Include_tools=1 LauncherOnly=0 SimpleInstall=1
```

cython をインストールします。

```powershell
C:\opt\python311\Scripts\pip.exe install cython
```

# ソースコードの準備

作業ディレクトリを作成します。

```powershell
mkdir C:/opt/el
cd C:/opt/el
```

openlace-win を clone します。

```powershell
git clone https://github.com/daeosqu/openlase-win.git
cd C:/opt/el/openlase-win
mkdir build
```

# Run cmake generator

```powershell
cd C:/opt/el/openlase-win\build
$env:PATH="C:\opt\python311\Scripts;$env:PATH"
cmake .. -G "Visual Studio 17 2022" -A x64 -DCMAKE_BUILD_TYPE=Release -DPython3_ROOT_DIR=C:/opt/python311 -DCMAKE_TOOLCHAIN_FILE="$env:USERPROFILE/scoop/apps/vcpkg/current/scripts/buildsystems/vcpkg.cmake" -DCMAKE_PREFIX_PATH="C:/Qt/Qt5.14.2/5.14.2/msvc2017_64"
```

# Build

```powershell
cmake --build . --config Release --target clean
cmake --build . --config Release
```

# Install

```powershell
gsudo cmake --build . --config Release --target install
```

注意: pylase は Python の site-packages にコピーされません。

# QuickStart

## Run QjackCtl

QjackCtl がスタートメニューにない場合は C:/Program Files/JACK2/qjackctl/qjackctl.exe を右クリックでスタートメニューに登録します。

1. QjackCtl を起動
1. Settings ボタンを押す
  1. Settings タブの Driver を portaudio にする
  1. Setup... ボタンを押して Settings タブの Driver を portaudio にする
    - Sample Rate: 48000
    - Frames/Period: 128
  1. Misc タブの Start JACK audio server on application startup にチェックを入れます
1. qjackctl を一旦終了します
1. qjackctl を起動
1. Start ボタンを押します

注意: Windows のオーディオ出力デバイスが 48kHz, 16bit 以外だと音が壊れたり再生速度が正しく再生されません。異なる場合は 48kHz, 16bit に設定してください。

## Run simulator

レーザーの投影をシミュレーションする為の Simulator を実行します。

```powershell
. "C:\Program Files\openlase\bin\simulator.exe"
```

NOTE: QjackCtl の起動と同時に simulator を起動したい場合は Setup の Options タブで Execute script on Startup にチェックを入れて以下のコマンドを指定します。

```
cmd /c start cmd /c ""timeout" /t 2 /nobreak & start cmd /c "C:\Program Files\openlase\bin\simulator.exe""
```

## simple の実行

openlase のレーザー出力アプリを実行します。

```
. "C:\Program Files\openlase\bin\simple.exe"
```

## QjackCtl で接続

simple の出力を simulator に繋げて動作確認をします。

1. QjackCtl の Graph ボタンを押す
1. libol と simulator の out_b と in_b を繋ぐ
1. 同じ様に g, r, x, y を繋ぎます

OpenLase Simulator に２つの立方体が表示されたら動作確認 OK です。
ただし毎回配線する必要があります。

# QjackCtl Patchbay の利用

永続的に自動配線をするには Patchbay を使います。定義は xml ファイルとして保存することができます。作成した config/openlase-laserdock.xml を用意しました。これを利用したセットアップ方法を解説します。

1. QjackCtl を起動します。
1. Patchbay ボタンを押します。
1. Load... ボタンを押して config/openlase-laserdock.xml をロードします。
1. Activate ボタンを押します。

.\examples\simple.exe を実行して先程と同じ様に２つの立方体のアニメーションが simulator に再生される事を確認します。

# Bad Apple

## 動画のダウンロード

yt-dlp で "[Touhou] Bad Apple!! PV [Shadow]  [sm8628149].mp4" をダウンロードします。

```
C:\opt\python311\Scripts\pip install yt-dlp
mkdir c:\opt\el\data
cd c:\opt\el\data
C:\opt\python311\Scripts\yt-dlp https://www.nicovideo.jp/watch/sm8628149
ren '[Touhou] Bad Apple!! PV [Shadow]  [sm8628149].mp4' 'bad_apple.mp4'
```

## 再生

simple の再生と同様に QjackCtl と simulator を起動しておき、以下のようにしてダウンロードした bad_apple.mp4 を再生します。

Min size を小さくすると詳細度が上がりますがフレームレートが落ちます。

```
. "C:\Program Files\openlase\bin\qplayvid.exe" C:/opt/el/data/bad_apple.mp4
```

# LaserCube で本番投影

実機 (LaserCube) で投影するには laserdock_jack.exe を使用します。
simulator を使用した場合と異なるのは laserdock_jack.exe を実行しておく必要があるのと output.exe を使用することです。 output.exe は映像の歪みなどを補正する事ができます。プロジェクターの台形補正と同じ様に LaserCube が投影する映像を補正するのに利用できます。

1. QjackCtl を起動します。
2. output.exe を実行します。
3. LaserCube に電源を入れて PC と USB 接続します。
4. laserdock_jack を実行します。
5. qplayvid で動画を再生して投影します。

```
. "C:\Program Files\JACK2\qjackctl\qjackctl.exe"
start "C:\Program Files\openlase\bin\output.exe"
start "C:\Program Files\lasershark_hostapp\bin\laserdock_jack.exe"
. "C:\Program Files\openlase\bin\qplayvid.exe" C:/opt/el/data/bad_apple.mp4
```

# Pylase

OpenLase の python バインディングを利用するには以下のように PYTHONPATH を設定してください。

```powershell
$env:PATH="C:\opt\python311;$env:PATH"
$env:PATH="C:\opt\python311\Scripts;$env:PATH"
$env:PYTHONPATH="C:\Program Files\openlase\bin"
```

```
python -c "import pylase; print('ok')"
```

以下を実行して２つの矩形と Hi! という文字が表示される事を確認します。

```
python "C:\Program Files\openlase\bin\simple.py"
```

# Programs

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
| ugoira_player.py  | Pixiv のうごイラを描画出力(動作せず)。                                                             |
| webcam_shadows.py | カメラの映像をリアルタイムで描画出力。                                                             |

# Development

開発中は以下のように PATH を設定します。

```
$env:PATH="C:\opt\el\openlase-win\build\libol;$env:PATH"
$env:PATH="C:\Qt\Qt5.14.2\5.14.2\msvc2017_64\bin;$env:PATH"
$env:PATH="C:\opt\python311;$env:PATH"
$env:PATH="C:\opt\python311\Scripts;$env:PATH"
$env:PYTHONPATH="C:\opt\el\openlase-win\build\python"
```

また python 3.8 以降は DLL の探索パスが環境変数 PATH に従いません。libjack64.dll と ol.dll を pylase.cp311-win_amd64.pyd と同じ場所にコピーする必要があります。

```
cp C:\Windows\libjack64.dll C:\opt\el\openlase-win\build\python
cp C:\opt\el\openlase-win\build\libol\ol.dll C:\opt\el\openlase-win\build\python
```

pylase をインポートできる事を確認します。

```
python -c 'import pylase'
```

# Update vcpkg

vcpkg で以下のエラーが発生した場合は次のコマンドを試してください。

```
fatal: path 'versions/baseline.json' exists on disk, but not in 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
```

```powershell
cd "$env:USERPROFILE\scoop\apps\vcpkg\current\versions"
git pull
vcpkg update
git rev-parse HEAD
```

出力されたハッシュを vcpkg.json の builtin-baseline に設定してください。


