@echo off
setlocal

REM --- Configuration ---
set VENV_DIR=cm-venv
set START_SCRIPT=src.codemerger
set SPEC_FILE=codemerger.spec
set FLAG=%1

REM --- Environment Setup ---
if "%VIRTUAL_ENV%"=="" (
    if not exist "%VENV_DIR%\Scripts\activate" (
        echo Virtual environment not found. Creating a new one...
        python -m venv %VENV_DIR%
        call %VENV_DIR%\Scripts\activate
        if exist requirements.txt (
            echo Installing required packages...
            pip install -r requirements.txt
        )
    ) else (
        echo Activating virtual environment...
        call %VENV_DIR%\Scripts\activate
    )
)

REM --- Main Command Router ---
if /I "%FLAG%"=="" goto :DefaultAction
if /I "%FLAG%"=="cmd" goto :OpenCmd
if /I "%FLAG%"=="f" goto :FreezeReqs
if /I "%FLAG%"=="b" goto :BuildApp
if /I "%FLAG%"=="r" goto :HandleRelease

echo Unrecognized command: %FLAG%
goto :eof

:OpenCmd
echo Virtual environment activated. You are now in a new command prompt.
cmd /k
goto :eof

:FreezeReqs
echo.
echo --- Writing requirements.txt ---
pip freeze > requirements.txt
echo Done.
goto :eof

:BuildApp
echo.
echo --- Starting PyInstaller Build ---
rmdir /s /q dist 2>nul
rmdir /s /q build 2>nul
echo Running PyInstaller with %SPEC_FILE%...
pyinstaller %SPEC_FILE%
echo.
echo --- Build Complete! ---
echo Executable is located in the 'dist' folder.
goto :eof

:DefaultAction
echo Starting CodeMerger application...
python -m %START_SCRIPT%
goto :eof


REM --- Release Subroutine ---
:HandleRelease
    setlocal enabledelayedexpansion
    echo.
    echo --- Rebuilding and Re-tagging ---

    REM --- Step 1: Parse the comment correctly ---
    shift /1
    set "COMMENT="
    :ArgLoop
    if "%~1"=="" goto EndArgLoop
    if not defined COMMENT (
        set "COMMENT=%~1"
    ) else (
        set "COMMENT=!COMMENT! %~1"
    )
    shift /1
    goto ArgLoop
    :EndArgLoop

    if not defined COMMENT set "COMMENT=No comment"
    echo Comment: !COMMENT!

    REM --- Step 2: Read version from file ---
    if not exist "assets\version.txt" (
        echo Error: assets\version.txt not found.
        exit /b 1
    )
    set "MAJOR_VER="
    set "MINOR_VER="
    set "REVISION_VER="
    for /f "tokens=1,2 delims==" %%a in (assets\version.txt) do (
        if /i "%%a"=="Major" set "MAJOR_VER=%%b"
        if /i "%%a"=="Minor" set "MINOR_VER=%%b"
        if /i "%%a"=="Revision" set "REVISION_VER=%%b"
    )
    if not defined MAJOR_VER ( echo Error: "Major" version not found. & exit /b 1 )
    if not defined MINOR_VER ( echo Error: "Minor" version not found. & exit /b 1 )
    if not defined REVISION_VER ( echo Error: "Revision" version not found. & exit /b 1 )
    set "VERSION=!MAJOR_VER!.!MINOR_VER!.!REVISION_VER!"
    echo Version: !VERSION!

    REM --- Step 3: Perform Git operations ---
    echo Checking out master branch...
    git checkout master
    set "TAG=v!VERSION!"

    REM Delete local tag if it exists - Using the reliable rev-parse method
    git rev-parse "!TAG!" >nul 2>nul
    if %errorlevel% equ 0 (
        echo Deleting local tag !TAG!...
        git tag -d !TAG!
    ) else (
        echo Local tag !TAG! does not exist.
    )

    REM Delete remote tag if it exists
    git ls-remote --tags origin refs/tags/!TAG! | findstr "refs/tags/!TAG!" > nul
    if %errorlevel% equ 0 (
        echo Deleting remote tag !TAG!...
        git push origin --delete !TAG!
    ) else (
        echo Remote tag !TAG! does not exist on origin.
    )

    REM Recreate and annotate the tag
    echo Recreating annotated tag !TAG!...
    git tag -a "!TAG!" -m "!COMMENT!"
    if %errorlevel% neq 0 (
        echo.
        echo --- FATAL: Failed to create tag. It might already exist if a previous step failed. Aborting. ---
        endlocal
        exit /b 1
    )

    REM Push the new tag to remote
    echo Pushing new tag !TAG! to origin...
    git push origin !TAG!
    echo.
    echo --- Re-tag Complete! ---
    endlocal
goto :eof