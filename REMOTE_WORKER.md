# Remote Stockfish Worker

If you want to help out, here's how you can add a Stockfish worker to support the FlawChess server and speed up game analysis. This is a standalone setup: it does **not** require Docker, PostgreSQL, Node.js, or anything else from the [full development setup](README.md#getting-started). All you need is the repo, Stockfish, and the `uv` Python package manager.

## Prerequisites

- You need the `EVAL_OPERATOR_TOKEN` from the server owner.

## Setup

1. Get the [repo](https://github.com/flawchess/flawchess) from Github. It's public, so no GitHub account is required. Either clone over HTTPS:
   ```
   git clone https://github.com/flawchess/flawchess.git
   ```
   or [download the ZIP](https://github.com/flawchess/flawchess/archive/refs/heads/main.zip) from the GitHub web UI ("Code → Download ZIP") and extract it.

2. From inside the flawchess folder, install Stockfish 18 with `bin/install_stockfish.sh` (Linux/MacOS only. For Windows, see below).

3. Install the [uv](https://docs.astral.sh/uv/) python package manager.

4. Inside the flawchess directory, copy `.env.example` to `.env` and set your token on the `EVAL_OPERATOR_TOKEN=` line: `EVAL_OPERATOR_TOKEN=**********`

5. Run this from within the flawchess directory: 
   ```
   uv run python scripts/remote_eval_worker.py --workers 4
   ```
   You can increase the number of workers up to 2x your CPU core count, but the default is 4.

6. Keep it running as long as you want and end it with `Ctrl-C` or by closing the terminal.

## Running on Windows

Besides Linux and MacOS, the worker runs natively on Windows as well. No WSL or Docker needed.

- Instead of running `bin/install_stockfish.sh`, download and extract the [Windows Stockfish 18 release](https://stockfishchess.org/download/). 

- Uncomment and set the `STOCKFISH_PATH` line in `.env` (note the forward slashes and the absence of the .exe extension):
   ```
   STOCKFISH_PATH="C:/path/to/stockfish-windows-x86-64-avx2"
   ```

- Run the same command from within the flawchess directory as above: 
   ```
   uv run python scripts/remote_eval_worker.py --workers 4
   ```
