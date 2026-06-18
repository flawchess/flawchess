# Remote Stockfish Worker

Want to help out? You can run a small program on your computer that helps the FlawChess server analyze games faster. It runs Stockfish (the chess engine) in the background and quietly does analysis work whenever the server needs it.

You don't need to be a programmer to set this up. You also don't need Docker, a database, or the full FlawChess developer setup. Just the files, Stockfish, and one helper tool called `uv`. The steps below walk you through it.

## What you'll need first

- Ask the server owner for your `EVAL_OPERATOR_TOKEN`. This is a secret code that lets your computer connect. You'll paste it in later.

## Setup (Linux and macOS)

1. **Download the files.** Go to the [FlawChess repository](https://github.com/flawchess/flawchess) on GitHub, click the green **Code** button, and choose **Download ZIP**. Unzip it somewhere easy to find, like your Desktop. (No GitHub account needed.)

   *If you're comfortable with git, you can clone the repo instead:*
   ```
   git clone https://github.com/flawchess/flawchess.git
   ```

2. **Open a terminal** and go into the folder you just unzipped. For example:
   ```
   cd ~/Desktop/flawchess
   ```

3. **Install Stockfish.** Run this once:
   ```
   bin/install_stockfish.sh
   ```

4. **Install `uv`** (a tool that runs the worker). Follow the one-line install instructions at [the uv website](https://docs.astral.sh/uv/).

5. **Add your token.** In the flawchess folder, make a copy of the file `.env.example` and name the copy `.env`. Open `.env` in any text editor, find the line that starts with `EVAL_OPERATOR_TOKEN=`, and paste your token right after the `=`, like this:
   ```
   EVAL_OPERATOR_TOKEN=your-token-here
   ```

6. **Start the worker.** Back in the terminal, run:
   ```
   uv run python scripts/remote_eval_worker.py --workers 4
   ```
   `--workers 4` means it uses 4 CPU cores. 4 is a good default. If your computer is powerful and you want it to do more, you can go up to twice your number of CPU cores.

7. **Leave it running** as long as you like. To stop it, press `Ctrl-C` in the terminal or just close the window.

## Setup (Windows)

The worker runs on Windows too. No extra tools like WSL or Docker needed. The steps are the same as above, with two differences:

- **Instead of step 3** (`bin/install_stockfish.sh`), download the [Windows version of Stockfish](https://stockfishchess.org/download/) and unzip it somewhere on your computer.

- **After step 5**, also open your `.env` file and find the line starting with `STOCKFISH_PATH`. Remove the `#` at the start of the line (if there is one) and set it to where you put Stockfish. Use forward slashes `/` and leave off the `.exe` at the end:
   ```
   STOCKFISH_PATH="C:/path/to/stockfish-windows-x86-64-avx2"
   ```

Then start the worker exactly like step 6 above:
```
uv run python scripts/remote_eval_worker.py --workers 4
```
