# INSTALL

Build and Installation instructions for OpenLase windows.

# REQUIREMENTS

- Windows 11
- Powershell 7
- Windows Terminal
- Visual Studio 2022 Community
- scoop
  - yasm 1.3.0
  - cmake 3.29.2 64bit
  - ffmpeg 7.0-full-build
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
  - cython 0.29.x
- [laserdock_jack](https://github.com/daeosqu/laserdock_jack.git)
- AutoHotkey

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

以下のアプリケーションをインストールしておきます。

- [Qt5 x86-5.14.2 (qt-opensource-windows-x86-5.14.2.exe)](https://download.qt.io/archive/qt/5.14/5.14.2/qt-opensource-windows-x86-5.14.2.exe)
- [Git for Windows](https://gitforwindows.org/)
- [Scoop](https://scoop.sh/)

git は自動改行変換をオフにしておきます。

```
git config --global core.autocrlf false
```

# Install cmake, vcpkg, yasm

```powershell
scoop install cmake vcpkg yasm gsudo ffmpeg
```

# Install python3

Python3 をインストールします。
または環境変数 OL_PYTHON_DIR に Python がインストールされているパスを指定します。

```powershell
$TargetDir=$env:OL_PYTHON_DIR

$TargetVer="3.11.9"
$Arch="-amd64"
$py_url="https://www.python.org/ftp/python/${TargetVer}/python-${TargetVer}${Arch}.exe"

Invoke-WebRequest "$py_url" -OutFile "$env:USERPROFILE\Downloads\python-${TargetVer}${Arch}.exe"

. $env:USERPROFILE\Downloads\python-${TargetVer}${Arch}.exe InstallAllUsers=0 TargetDir=$TargetDir AssociateFiles=0 CompileAll=0 PrependPath=0 Shortcuts=0 Include_doc=0 Include_debug=1 Include_dev=1 Include_exe=1 Include_launcher=0 InstallLauncherAllUsers=0 Include_lib=1 Include_pip=1 Include_symbols=1 Include_tcltk=1 Include_test=0 Include_tools=1 LauncherOnly=0 SimpleInstall=1
```

cython をインストールします。

```powershell
$env:OL_PYTHON_DIR\python -m ensurepip
$env:OL_PYTHON_DIR\python -m pip install -r requirements.txt
```

# ソースコードの準備

作業ディレクトリを作成してクローンします。

# Clone

```powershell
mkdir C:/opt/el
cd C:/opt/el
cd C:/opt/el
git clone https://github.com/daeosqu/openlase-win.git
```

# Install

```
cd C:/opt/el/openlase-win
. openlase.cmd
```

OpenLase ターミナルが起動したら以下のコマンドを実行します。

```
olbuild
olinstall
```

または以下の様にコマンドを実行します。

```powershell
cd C:/opt/el/openlase-win
mkdir build
cd build
$env:PATH="$env:OL_PYTHON_DIR\Scripts;$env:PATH"
cmake .. -G "Visual Studio 17 2022" -A x64 -DCMAKE_BUILD_TYPE=Release -DPython3_ROOT_DIR=$env:OL_PYTHON_DIR -DCMAKE_TOOLCHAIN_FILE="$env:USERPROFILE/scoop/apps/vcpkg/current/scripts/buildsystems/vcpkg.cmake" -DCMAKE_PREFIX_PATH="C:/Qt/Qt5.14.2/5.14.2/msvc2017_64"
cmake --build . --target clean
cmake --build .
gsudo cmake --build . --config Release --target install
```

# QuickStart

## Run QjackCtl

QjackCtl がスタートメニューにない場合は C:/Program Files/JACK2/qjackctl/qjackctl.exe を右クリックでスタートメニューに登録します。

1. QjackCtl を起動
1. Settings ボタンを押す
  1. Settings タブの Driver を portaudio にします。
  1. Setup... ボタンを押して Settings タブの Driver を portaudio にします。
    - Sample Rate: 48000
    - Frames/Period: 1024
  1. Misc タブの Start JACK audio server on application startup にチェックを入れます
1. qjackctl を一旦終了します
1. qjackctl を起動
1. Start ボタンを押します

注意: Windows のオーディオ出力デバイスが 48kHz, 16bit 以外だと音が壊れたり再生速度が正しく再生されません。異なる場合は 48kHz, 16bit に設定してください。

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
