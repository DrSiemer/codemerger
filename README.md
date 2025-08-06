# CodeMerger

A simple app for developers that prefer to stay in control and want to avoid working in AI powered IDE's. It allows you to define which files should be merged into a single string, so you can easily paste all relevant code into an LLM. Settings for a folder are stored in a .allcode file that can be committed with your project.

I recommend using this with [Gemini 2.5 Pro](https://aistudio.google.com/prompts/new_chat), because at this time it offers a large context length for free.

## Download

Download the latest release [here](https://github.com/DrSiemer/codemerger/releases).

- **Windows**: The download is a portable executable
- **macOS**: The build is a **universal binary**, which runs natively on both Apple Silicon (M1/M2/M3) and Intel-based Macs

Ignore the Windows Defender SmartScreen block if you get it (click "More info" > "Run anyway"); the app is safe, all it does is bundle text with a convenient UI.

## Usage

- Select a working directory
- Add the files you want to manage
    - You can open an added file by double clicking
- Click "Copy merged" to merge all the selected files into a single string in your clipboard
- Click "Compact Mode" to switch to a small, always-on-top copy button. This is useful for keeping the copy functionality handy while you work.
    - Double-click the move bar or use the close button to return to the full view

### Settings

- Select your preferred editor in the settings (none means default will be used)
- To manage indexed filetypes, click "Manage Filetypes" from the main window

## Development

- Make sure you have Python installed (and added to your PATH)
- Run `go` to start
- Run `go b` to build executable
- Run `go r` to push or update a release on Github using Actions
    - Update `/assets/version.txt` if you want a new release
    - You can add a comment to the release like this: `go r "Comment"`
    - The release will be a draft, you'll need to finalize it on github.com

### Planned features

- Installer
- Actual design