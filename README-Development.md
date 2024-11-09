# OpenLase development

# Requirements

- [JACK 1.9.22 win64](https://github.com/jackaudio/jack2-releases/releases/download/v1.9.22/jack2-win64-v1.9.22.exe) JACK Audio Connection Kit for Windows 64bit
- [laserdock_jack](https://github.com/daeosqu/laserdock_jack.git) if you have LaserCube
- AutoHotkey

# Build requirements

- Visual Studio 2022 Community
- Powershell (v7 or later recomended)
- [Git for Windows 2.44.0.1](https://gitforwindows.org/)
- [Qt5 x86-5.14.2 (qt-opensource-windows-x86-5.14.2.exe)](https://download.qt.io/archive/qt/5.14/5.14.2/qt-opensource-windows-x86-5.14.2.exe)
- python 3.11.9 (64bit) (3.11 or older)
  - cython 0.29.x
- [wix3](https://github.com/wixtoolset/wix3/releases/)
- [Scoop](https://scoop.sh/)
  - cmake 3.29.2 64bit
  - yasm 1.3.0
  - ffmpeg 7.0
  - gsudo 2.4.4
- Libraries (vcpkg)
  - ffmpeg4.4.3 (< 5.x)
  - freeglut3.4.0
  - getopt
  - libmodplug0.8.9.0
  - pdcurses3.9
  - pthreads3.0.0

# Install PowerShell 7.x

PowerShell 7 以降インストールをします。以後 PowerShell 7 を利用します。

```powershell
PS> winget install --id Microsoft.Powershell --source winget
```

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

# Install applications

以下のアプリケーションをインストールしておきます。


git は自動改行変換をオフにしておきます。

```
git config --global core.autocrlf false
```

# Install with scoop

scoop で必要なツール類をインストールします。

```powershell
scoop install cmake yasm ffmpeg gsudo vcpkg 
```

# Install python3

Python3 (>= 3.11) をインストールします。

```powershell
if (!$env:OL_PYTHON_DIR) { $env:OL_PYTHON_DIR="C:\opt\python311" }

$TargetVer="3.11.9"
$Arch="-amd64"
$py_url="https://www.python.org/ftp/python/${TargetVer}/python-${TargetVer}${Arch}.exe"

Invoke-WebRequest "$py_url" -OutFile "$env:USERPROFILE\Downloads\python-${TargetVer}${Arch}.exe"

. $env:USERPROFILE\Downloads\python-${TargetVer}${Arch}.exe InstallAllUsers=0 TargetDir=$env:OL_PYTHON_DIR AssociateFiles=0 CompileAll=0 PrependPath=0 Shortcuts=0 Include_doc=0 Include_debug=1 Include_dev=1 Include_exe=1 Include_launcher=0 InstallLauncherAllUsers=0 Include_lib=1 Include_pip=1 Include_symbols=1 Include_tcltk=1 Include_test=0 Include_tools=1 LauncherOnly=0 SimpleInstall=1
```

Python パッケージをインストールします。ビルドには cython 以外は不要です。ただし cython のバージョンは 0.29.x 以下にしてください。

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
git clone --config core.autocrlf=false https://github.com/daeosqu/openlase-win.git
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

$env:OL_PYTHON_DIR="c:/opt/python311"
$env:Qt5_DIR="C:/Qt/Qt5.14.2/5.14.2/msvc2017_64"

$env:PATH="$env:OL_PYTHON_DIR;$env:OL_PYTHON_DIR\Scripts;$env:PATH"

cmake -S . -B "build" -G "Ninja" -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=On -DPython3_ROOT_DIR="$env:OL_PYTHON_DIR" -DCMAKE_TOOLCHAIN_FILE="$env:VCPKG_ROOT\scripts\buildsystems\vcpkg.cmake"

ninja -C build

gsudo cmake --install build
# or
cd build
cpack
.\Openlase-*.msi
```

# Install PixivUtil2 (OPTIONAL)

ugoira_player2 を使うには PixivUtil2 をインストールしておく必要があります。

```
Invoke-WebRequest -Uri "https://github.com/Nandaka/PixivUtil2/releases/download/v20230105/pixivutil202305.zip" -OutFile pixivutil202305.zip
Expand-Archive pixivutil202305.zip -DestinationPath "$HOME/.local/pixivutil" -Force
del pixivutil202305.zip
```
