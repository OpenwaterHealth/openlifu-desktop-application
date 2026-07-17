Build and Package OpenLIFU
==============================

This document summarizes how to build and package OpenLIFU on Windows.

OpenLIFU is a custom Slicer application. Reading the [3D Slicer Developer Documentation](https://slicer.readthedocs.io/en/latest/developer_guide/index.html) may help answer additional questions.

The initial source files were created using [KitwareMedical/SlicerCustomAppTemplate](https://github.com/KitwareMedical/SlicerCustomAppTemplate).

Prerequisites
-------------

* Setting up your git account:

    * Create a [Github](https://github.com) account.

    * Setup your SSH keys following [these](https://help.github.com/articles/generating-ssh-keys) instructions.

    * Setup [your git username](https://help.github.com/articles/setting-your-username-in-git) and [your git email](https://help.github.com/articles/setting-your-email-in-git).

Checkout
--------

1. Start `Git Bash`
2. Checkout the source code into a directory `C:\W\` by typing the following commands:

```bat
cd /c
mkdir W
cd /c/W
git clone https://github.com/OpenwaterHealth/OpenLIFU-app.git O
```

Note: use short source and build directory names to avoid the [maximum path length limitation](https://learn.microsoft.com/en-us/windows/win32/fileio/naming-a-file#maximum-path-length-limitation).

Build
-----
Note: The build process can take hours.

<b>Option 1: CMake GUI and Visual Studio (Recommended)</b>

1. Start [CMake GUI](https://cmake.org/runningcmake/), select source directory `C:\W\O` and set build directory to `C:\W\OR`.
2. Add an entry `Qt5_DIR` pointing to `C:/Qt/${QT_VERSION}/${COMPILER}/lib/cmake/Qt5`.
2. Generate the project.
3. Open `C:\W\OR\OpenLIFU.sln`, select `Release` and build the project.

<b>Option 2: Command Line</b>

1. Start the [Command Line Prompt](http://windows.microsoft.com/en-us/windows/command-prompt-faq)
2. Configure and build the project in `C:\W\OR` by typing the following commands:

```bat
cd C:\W\
mkdir OR
cd OR
cmake -G "Visual Studio 17 2022" -A x64 -DQt5_DIR:PATH=`C:/Qt/${QT_VERSION}/${COMPILER}/lib/cmake/Qt5 ..\O
cmake --build . --config Release -- /maxcpucount:4
```

Package
-------

Install [NSIS 2](http://sourceforge.net/projects/nsis/files/)

<b>Option 1: CMake and Visual Studio</b>

1. In the `C:\W\OR\Slicer-build` directory, open `Slicer.sln` and build the `PACKAGE` target

<b>Option 2: Command Line</b>

1. Start the [Command Line Prompt](http://windows.microsoft.com/en-us/windows/command-prompt-faq)
2. Build the `PACKAGE` target by typing the following commands:

```bat
cd C:\W\OR\Slicer-build
cmake --build . --config Release --target PACKAGE
```

