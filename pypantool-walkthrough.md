# PyPanTool — Plain-English Walkthrough

## What Changed
**2026-07-02** — Fifteen new tools were added, completing the full "Basic tools" menu of the original C++ PanTool. New abilities: thin a time series to one line per 10 minutes, insert/replace characters at fixed positions, add columns or text lines/blocks, search for a string across files and get a match report, split one file into many (by lines, by columns, or by size), and compress/decompress files and folders (zip, gz, tar.gz). Six new processing modules, six new dialogs, and two new background worker types were added; tests grew from 162 to 243.

---

## What This App Does

PyPanTool is a Windows desktop tool for batch processing large tabular text files — the kind of files that might have 2.5 million rows and be 700 megabytes in size. You load one or more files, choose an operation (extract certain columns, remove duplicate lines, merge files side-by-side, find-and-replace across all files at once, etc.), and the app processes every file and saves the results — without ever freezing the window or loading the whole file into memory. It's inspired by PANGAEA's PanTool, used in oceanographic data work.

---

## The Big Picture

Think of this app like a production line for data files. Files come in on a conveyor belt (the file list). You pick a tool from the menu. The tool runs on every file in the background while you watch a progress bar. The output files drop out the other end, named according to a pattern you configured. You can chain tools: the output of one operation automatically becomes the input for the next.

```
┌──────────────────────────────────────────────────────────┐
│  Menu Bar: File | Tools | Help                           │
├──────────────────────────────────────────────────────────┤
│  Toolbar: Open Files | Open Folder | Clear               │
├──────────────────────────────────────────────────────────┤
│  File List Table                                         │
│  Name          | Path          | Size    | Lines         │
│  data.tab      | C:\work\      | 700 MB  | 2,500,000     │
│  data2.tab     | C:\work\      | 350 MB  | 1,200,000     │
├──────────────────────────────────────────────────────────┤
│  Status Bar: "Processed 1,500,000 / 2,500,000 lines..."  │
│              [=================>    ]                    │
└──────────────────────────────────────────────────────────┘
```

The project is split into three clearly separated areas:

| Folder | Job |
|---|---|
| `core/` | The actual data processing — pure Python, no window code |
| `gui/` | The windows, menus, dialogs, and background threads |
| `tests/` | Automated checks that confirm the core logic is correct |

The processing and the interface never talk to each other directly. The GUI hands data to the core through a "worker" running in a background thread, receives progress updates, and displays them — without ever locking up.

---

## File & Folder Map

```
pypantool/
│
├── main.py                    ← Starts the application
│
├── core/
│   ├── addcol.py              ← Add a constant column and/or metadata columns
│   ├── addline.py             ← Insert text lines at a given line number
│   ├── charpos.py             ← Insert/replace characters at fixed positions
│   ├── columns.py             ← Extract or delete columns by number or header name
│   ├── comments.py            ← Delete lines that start with a comment marker (e.g. //)
│   ├── compress.py            ← Zip/gzip/tar.gz compression and decompression
│   ├── concat.py              ← Join files vertically (stacked) or horizontally (side-by-side)
│   ├── duplicates.py          ← Remove duplicate lines, keep first occurrence
│   ├── filelist.py            ← Export a list of loaded files (name, path, size, date)
│   ├── lines.py               ← Extract or delete lines by number or content match
│   ├── naming.py              ← Resolve output filenames from a pattern like "%N_out%E"
│   ├── recalc.py              ← Recalculate column values: new = old × factor + offset
│   ├── rename.py              ← Filename transformation: search/replace, prefix, suffix
│   ├── search_replace.py      ← Find/replace strings; search-report across files
│   ├── split.py               ← Split one file into many (by lines, columns, or size)
│   └── timeseries.py          ← Thin a time series to one line per interval
│
├── gui/
│   ├── main_window.py         ← The main application window
│   ├── options_dialog.py      ← Settings: output pattern, encoding, delimiter
│   ├── run_tool.py            ← Wires a dialog's settings to a background worker
│   ├── style.py               ← All visual styling (slate-blue theme)
│   ├── worker.py              ← Background threads that do the actual file I/O
│   └── dialogs/               ← One small dialog per tool (19 dialog files)
│
└── tests/
    ├── fixtures/
    │   ├── test_data.txt          ← 35-line realistic oceanographic dataset
    │   ├── test_data_supplement.txt  ← 8-line companion for concat tests
    │   └── test_timeseries.txt    ← 8-line Date/Time dataset for interval thinning
    ├── test_addcol.py
    ├── test_addline.py
    ├── test_charpos.py
    ├── test_columns.py
    ├── test_comments.py
    ├── test_compress.py
    ├── test_concat.py
    ├── test_duplicates.py
    ├── test_filelist.py
    ├── test_lines.py
    ├── test_recalc.py
    ├── test_rename.py
    ├── test_search_replace.py
    ├── test_split.py
    └── test_timeseries.py
```

---

## Section-by-Section Walkthrough

---

### `main.py` — Starting the App

**What it does:** The single entry point. When you run `python main.py`, this file sets the font to Segoe UI, applies the slate-blue stylesheet, creates the main window, and hands control to the Qt event loop (which then sits waiting for mouse clicks and keypresses forever until you close the window).
**Why it exists:** Every GUI application needs one "start here" file. This one does nothing except bootstrap — all real logic lives elsewhere.
**To change it:** Font size is set here. Application name and organization name are set here (they determine where settings are saved in the Windows registry).

---

### `core/naming.py` — Output Filename Patterns

**What it does:** Translates a pattern string into a real filename. The user types something like `%N_processed%E` in the Options dialog, and this module swaps in the real values when it's time to save. `%N` becomes the input filename without its extension. `%E` becomes the extension (including the dot). `%a` becomes an auto-incrementing counter (1, 2, 3…) that goes up every time you run a tool.
**Why it exists:** Without this, every output file would overwrite the input or need a fixed name. The pattern system lets users set it once and have it applied consistently across all files and all tool runs.
**To change it:** The default pattern (`%N_out%E`) is set in `options_dialog.py`. Users can override it through File → Options.

Example: `%N_out%E` applied to `temperature_data.tab` → `temperature_data_out.tab`

---

### `core/columns.py` — Column Operations

**What it does:** Handles extracting or deleting specific columns from tab-delimited files. There are two ways to specify which columns you want: by position (e.g., "1-3,5,7-end") or by matching the column header name (or a search pattern).

#### Column spec parser
**What it does:** Converts a human-readable specification like "1-3,5,7-end" into an internal list of column positions. The word `end` means "the last column, whatever it is."
**Why it exists:** Users shouldn't have to count columns to find the last one in a file with 80 columns — `end` handles it automatically.
**To change it:** Specs use 1-based column numbers (column 1 is the first column). Internally they're converted to 0-based for processing.

#### Extract columns / Delete columns
**What it does:** Streams through the file line by line. For each line that has tab-separated columns, it keeps (or removes) the columns specified. Lines without any tabs (comments, blank lines, section headers) always pass through untouched.
**Why lines without tabs always pass through:** A comment line like `// Station PS001` has no columns. Trying to split it would break the output structure.
**To change it:** The delimiter defaults to tab but uses whatever the user set in Options.

#### Extract/delete matched columns
**What it does:** Instead of column numbers, you give it a text pattern (or a regex). It finds the first non-comment line (the header line), identifies which column headers match your pattern, and then keeps or removes those columns.
**Why it exists:** In files with many columns (e.g., "Salinity [PSU]", "Temperature [°C]", "Depth [m]"), searching by name is far easier than counting column positions.

---

### `core/lines.py` — Line Operations

**What it does:** Extracts or deletes specific lines from a file. Like columns, there are two approaches: by line number (e.g., "1-3,10,50-end") or by content (keep/remove lines that contain a word or match a pattern).

#### Line spec parser
**What it does:** Same idea as the column spec parser but for line numbers. "1-3,10,50-end" means lines 1, 2, 3, 10, and everything from line 50 to the end of the file.
**Why it exists:** Lets you pull out specific sections of a file without opening it in an editor.

#### Extract/delete by spec
**What it does:** Streams the file, checking each line's number against the spec. Matching lines are kept (extract) or removed (delete).

#### Extract/delete matched lines
**What it does:** Streams the file and checks whether each line contains a given string (or matches a regex pattern). Matched lines are kept (extract) or removed (delete).
**Use case:** Remove all blank lines, pull out all rows mentioning "PS003", or delete all lines starting with "//".

---

### `core/comments.py` — Comment Line Deletion

**What it does:** Removes every line that starts with a configurable prefix. The default prefix is `//` (double forward-slash), but you can set it to anything (`#`, `%`, `*`, etc.).
**Why it exists:** Many scientific data formats embed comment or metadata lines at the top or interspersed throughout. This tool strips them out cleanly.
**To change it:** The prefix is entered in the tool's dialog each time you run it.

---

### `core/duplicates.py` — Duplicate Line Removal

**What it does:** Removes duplicate lines, keeping only the first occurrence of each. The clever part: instead of storing every line in memory to compare against future lines (which would crash the program on a 700 MB file), it stores only an 8-byte fingerprint (BLAKE2b hash) of each line. With 2.5 million unique lines this needs about 160 MB, regardless of line length.
**Why it exists:** Tabular data exports often contain accidental duplicates from data joins or repeated exports.
**Things to know:** Comparison is case-sensitive and whitespace-significant — "Station A" and "station a" are treated as different lines.

---

### `core/concat.py` — File Concatenation

**What it does:** Merges multiple files into one. Two completely different strategies:

#### Concatenate by lines (vertical stacking)
**What it does:** Appends files one after another, like stacking sheets of paper. The first N lines count as header: kept from the first file, skipped from files 2, 3, etc. so the output doesn't repeat the header. Optionally the file name (without extension) is added as column 1 of every data line; the last header line then gets `Filename` as its first column, while comment and empty lines stay untouched. You can also skip blank lines or comment lines. The output is always named `Concatenate_out.<ext>` (extension of the first file) in the first file's folder; if that name is taken, `_2`, `_3`, … is appended, so nothing is overwritten. Optionally the input files are moved to the recycle bin, but only after the output was written completely.
**Use case:** You have one data file per month. This merges them into a single year-long file without duplicating the header row.

#### Concatenate by columns (horizontal merging)
**What it does:** Zips files side-by-side, row by row. Row 1 of file A and row 1 of file B become a single wider row. All files must have the same number of rows. Optionally, a row of filenames is prepended at the top. The output is `Concatenate_columns_out.<ext>` in the first file's folder (auto-numbered, never overwrites); Search One String likewise writes `Search_out.<ext>`, and Save File List writes `Filelist_out.txt`.
**Use case:** You measured temperature in one file and salinity in another, same stations in the same order. This creates one combined file with all measurements.
**Things to know:** If the files have different numbers of rows, the operation stops with an error — misaligned data would silently produce wrong results.

---

### `core/search_replace.py` — Find and Replace

**What it does:** Three related functions.

#### Single find/replace
**What it does:** Replaces all occurrences of a search string with a replacement string, in every line, in every loaded file. Not regex — plain text matching.
**Use case:** Fix a misspelled station name across a hundred files at once.

#### Search one string (report, no replacing)
**What it does:** Looks for a piece of text in every loaded file and writes a report instead of changing anything. Each match becomes one row: filename, line number, and the full matching line. You can limit the search to a window of lines (start at line X, search Y lines).
**Why it exists:** Before changing data across many files, you often want to know *where* something appears. This is the "look before you leap" companion to find-and-replace.
**To change it:** The report's column headers ("Filename", "Line", "String") are set at the top of the function.

#### Many find/replace at once
**What it does:** Takes an ordered list of (search, replace) pairs and applies them all in sequence. The output of the first replacement feeds into the second, and so on.
**Why ordered matters:** If you're replacing "A" → "B" and then "B" → "C", the order determines whether the first replacement gets caught by the second.

#### Load replacements from a file
**What it does:** Reads a tab-delimited "database" file where the first column is the search text and the second column is the replacement. Returns the list of pairs for use with the many-at-once function above.
**Use case:** You have a lookup table of old station codes → new station codes. Load it once and apply it everywhere.

---

### `core/filelist.py` — File Metadata Export

**What it does:** Writes a tab-delimited summary of all loaded files: filename, directory path, size in bytes, and last-modified timestamp. The output is a regular text file that can be opened in Excel.
**Why it exists:** Useful for documenting what data files were processed in a batch job, or for auditing which version of a file was used.

---

### `assets/css/style.py` — Visual Styling

**What it does:** Defines the entire visual appearance of the app in one place — colors, fonts, button shapes, table row colors, menu styling, scrollbars, progress bar, and more. The theme is a professional slate-blue.
**Why it exists:** Centralizing all styling means changing the accent color once updates it everywhere. Also keeps all the visual decisions out of the window logic.
**To change it:** Edit the color constants at the top of the file. `HEADER_BG` is the dark blue menu/toolbar color. `ACCENT` is the button color. `SURFACE` is the white area behind the table.

---

### `gui/options_dialog.py` — Settings

**What it does:** The dialog opened by File → Options. Lets the user set four things that apply to all tool runs:
- **Output filename pattern** (e.g., `%N_out%E`)
- **Input file encoding** (UTF-8, Latin-1, CP1252, ASCII — handles files from different operating systems or regions)
- **Output file encoding** (same choices)
- **Column delimiter** (Tab, Semicolon, Comma, Pipe, or Space)

Settings are saved automatically in the Windows registry and remembered across sessions.
**To change it:** The default output pattern and default encoding are constants at the top of the file.

---

### `gui/worker.py` — Background Processing Threads

**What it does:** Three classes that run file processing in a background thread so the window never freezes. They communicate with the main window by emitting signals (like notifications) for events such as "started file 3 of 10", "processed 500,000 lines", and "all done".

#### ProcessWorker
**What it does:** Opens each file, feeds lines to a core processing function one at a time, and writes the output lines immediately to the output file. Reports progress every 5,000 input lines. Used by all single-file tools (extract columns, delete duplicates, recalculate columns, etc.). Before starting it refuses to run if an output name would overwrite an input or if two inputs would write the same output (e.g. a pattern without `%N`). On error or cancel, the half-written output file is deleted.

#### Progress and cancel
ProcessWorker, ConcatWorker and SplitWorker share a small base class. Every 5,000 input lines it reports lines read and a percentage (characters read vs. file size) to the status bar and progress bar, and checks whether you pressed **Cancel** in the status bar. Closing the window while a tool runs asks first, then cancels cleanly.

#### LineCountWorker
**What it does:** Fills the "Lines" column of the file list in the background, reading files in 1 MB binary blocks. It pauses while a tool runs, so no file is held open during a rename or move to the recycle bin.

#### ConcatWorker
**What it does:** Passes the input files' line streams to the concat function and writes the result. Each file is opened only when the function first reads from it, so concatenating by lines holds one file open at a time, while side-by-side merging still reads all files in parallel. Refuses to run if the output path is one of the inputs. On error, the partial output is deleted and no input is touched; on success it can move the inputs to the recycle bin (Qt `QFile.moveToTrash`).

#### FilelistWorker
**What it does:** The simplest worker — it doesn't read any file contents, just collects file metadata and writes the summary file.

#### RenameWorker
**What it does:** Renames files in place on disk (no new output file is created). Iterates through the (old path, new path) pairs computed by the dialog preview and calls the operating system rename for each pair. Files whose name would not change are skipped. After all renames succeed, emits the list of new paths so the file list table updates.

**Why all four exist separately:** Their patterns of file access are fundamentally different — one file at a time vs. all at once vs. no file reading at all vs. in-place rename with no content I/O.
#### SplitWorker
**What it does:** The reverse of ConcatWorker — one input file becomes many numbered output files. The processing function tags every line with a chunk number, and the worker opens `name_0001.ext`, `name_0002.ext`, … as those numbers first appear. For line-based splits it keeps only one output open at a time; for column splits (where every input line feeds all outputs) it keeps them all open until the file ends.

#### CompressWorker
**What it does:** Runs a file-level operation — compress or decompress — on each path in the list, one at a time, in the background. Unlike the other workers it never reads lines; the compression functions handle the bytes themselves.

**Things to know:** If an error occurs during processing, the worker catches it and sends an error notification to the window, which shows a message box. No partial output files are left behind. For `RenameWorker`, if a rename fails mid-way (e.g. a file is locked), processing stops and already-renamed files keep their new names. `ProcessWorker` has an opt-in `pass_path` switch that hands the current file's path to the processing function — only Add Column uses it, for its filename/path columns.

---

### `gui/run_tool.py` — The Wiring Layer

**What it does:** The bridge between dialogs and workers. When you click OK in a tool's dialog, this module:
1. Takes the core function pre-configured with your settings
2. Figures out the output file path for each input file using the naming pattern
3. Creates the appropriate worker
4. Hands the worker to the main window, which connects progress, error and cancel handling centrally
5. Starts the background thread
6. When it's done, replaces the file list with the output files (enabling tool chaining)

**Why it exists:** Without this, every dialog would have to duplicate the same wiring code. This puts it in one place.

**Things to know:** There is one `run_…` helper per worker type: `run_tool` (one output per input), `run_concat` (many inputs, one output — also used by Search One String, which is allowed to run on a single file), `run_split` (one input, many outputs), `run_rename`, `run_filelist`, and `run_compress`. All follow the same shape: build the worker, connect its signals to the status bar, start it, and update the file list when it finishes.

---

### `gui/main_window.py` — The Main Window

**What it does:** The central hub of the application. Manages the file list table, all menus and toolbar buttons, status bar, drag-and-drop, and coordinates all tool operations.

#### File list table
**What it does:** Shows each loaded file with its name, directory path, size, and line count. Line counts are filled in by a background counter after files are loaded or produced by a tool.

#### File loading
**What it does:** Three ways to load files — file picker dialog (multi-select), folder picker (loads every text file in the folder), or drag-and-drop files/folders directly onto the window. Duplicate files are automatically skipped.

#### Tool chaining
**What it does:** After a tool runs, the output files automatically replace the input files in the list. Running another tool immediately processes the output of the previous one. The `%a` counter in the filename pattern increments with each run, so outputs are named `data_out_1.txt`, `data_out_2.txt`, etc.

#### Menus
**What it does:** The Tools menu has 32 items, one per tool — the complete "Basic tools" set of the original PanTool. Most open a small dialog; the compression entries act immediately (the folder variants open a folder picker). File menu has Open, Open Folder, Clear, Options, and Quit. Help menu has About.

**Things to know:** Each menu item's dialog is only loaded from disk when you click it (not at startup). This keeps the app fast to launch.

---

### `core/recalc.py` — Column Recalculation

**What it does:** Applies the formula `new = old × factor + offset` to selected columns, streaming line by line. Column selection uses the same spec syntax as the other column tools ("4", "2,4", "3-5", "3-end"). A configurable number of header lines at the top are passed through unchanged. Non-numeric values in a targeted column (e.g. column header text that wasn't skipped) are also passed through unchanged rather than causing an error.
**Why it exists:** Common need in scientific data work — converting units (°C to K, dbar to metres, etc.) across many files at once.
**Things to know:** Results are formatted with up to 15 significant digits, which preserves the full precision of standard 64-bit floating-point numbers. Integer results (e.g. 5 × 2 = 10) are written without a decimal point.

---

### `core/rename.py` — Filename Transformation

**What it does:** Two pure functions. `apply_rename` takes a filename and returns the transformed name based on three optional operations applied in order: (1) search/replace a substring anywhere in the filename, (2) prepend text before the filename, (3) insert a suffix after the stem but before the extension (e.g. `_v2` turns `data.tab` into `data_v2.tab`). `preview_renames` applies this to a list of file paths without touching the filesystem.
**Why the preview function exists:** The rename dialog calls it live as the user types, so the table of old→new names updates instantly without any disk access. The actual renaming only happens when OK is clicked.

---

### `core/timeseries.py` — Time-Series Thinning ("Extract 10 min Lines")
**What it does:** Reduces a dense time series (e.g. a sensor logging every 10 seconds) to one line per interval — 10 minutes by default. It finds the `Date/Time` column in the header, then walks through the file keeping a line only when enough time has passed since the last kept line. The first and last data lines are always kept.
**Why it exists:** Instruments often record far more frequently than an archive needs. This shrinks a file dramatically while preserving the shape of the data.
**Things to know:** Timestamps must be ISO format like `2024-01-15T08:30:00` (seconds and milliseconds optional). A malformed timestamp doesn't stop the run — an error-marker line is written in its place, matching the original PanTool. The interval is adjustable in the dialog.

---

### `core/charpos.py` — Characters at Fixed Positions
**What it does:** Two operations for fixed-width data: *insert* pushes text in before given character positions (turning `abcdef` with positions "3,5" and text "-" into `ab-cd-ef`); *replace* overwrites the single character at each position (positions "2-4" with `_` turns `abcdef` into `a___ef`). Positions count from 1 and accept ranges.
**Why it exists:** Some instrument files have no delimiters at all — values sit at fixed character positions. This is how you add tabs to such files (insert `^t`) or blank out a fixed-width field.
**Things to know:** Replacing with empty text deletes characters. Positions beyond a line's end simply append the text. `^t` in the dialog becomes a tab.

---

### `core/addcol.py` — Add Column
**What it does:** Adds one or both of: a constant text column (header text on line 1, a repeated value on every data line), and metadata columns — the file's name (header `Event label`), its full path (header `Filename`), and/or a running line number (header `No`). Each block can go at the front or the end of every line.
**Why it exists:** Before concatenating many station files into one, you usually need a column saying which file each row came from.
**Things to know:** This is the one tool whose core function also receives the file's path (the worker passes it in), because the filename column differs per file.

---

### `core/addline.py` — Add Text Line / Block
**What it does:** Inserts one line (or a multi-line block) so it starts at a given line number. If the file is shorter than that, the text lands at the end.
**Why it exists:** Adding a missing header line, or a comment block with licence/citation text, across hundreds of files at once.

---

### `core/split.py` — Splitting One File into Many
**What it does:** Three ways to break a file apart. *By lines*: every N data lines start a new file. *By size*: a new file starts when the current one reaches a size cap (default 100 MB) or a line cap (default 1 million). *By columns*: each output file gets a slice of N data columns, optionally with "fixed" columns (like station and date) repeated in front of every slice.
**Why it exists:** Some programs (or email attachments, or upload forms) can't handle a 700 MB file. Splitting with repeated headers keeps every piece usable on its own.
**Things to know:** Output pieces are numbered `name_0001.ext`, `name_0002.ext`, … next to the input. Header lines are repeated at the top of every piece. For column splits, comment lines (no delimiter) are copied into every piece.

---

### `core/compress.py` — Compression and Decompression
**What it does:** Compresses each loaded file to a `.zip` or `.gz` archive next to it, packs a whole folder into `.zip` or `.tar.gz`, and decompresses archives (`.zip`, `.gz`, `.tar`, `.tar.gz`) back into their folder.
**Why it exists:** Data curation ends with archiving. The original PanTool searched your computer for an external zip program; this version uses Python's built-in libraries, so it always works.
**Things to know:** Data is copied in 1 MB chunks, so even a 700 MB file compresses without memory pressure. Existing archives with the same name are overwritten. Decompressing replaces the file list with the extracted files, so you can chain straight into processing them.

---

### `gui/dialogs/` — Tool Dialogs (19 files)

Each tool has its own small dialog. They all follow the same pattern: a short form collecting the tool's parameters, an OK button that validates input and launches the worker, and a Cancel button. None of them contain processing logic — they just collect settings and pass them to `run_tool.py`.

Here's a quick reference:

| Dialog | What you enter |
|---|---|
| `ColumnsDialog` | Column spec like "1-3,5,7-end"; extract or delete mode |
| `MatchedColumnsDialog` | Pattern text to match against column headers; regex option |
| `LinesDialog` | Line spec like "1-3,10,50-end"; extract or delete mode |
| `MatchedLinesDialog` | Pattern text to match within line content; regex option |
| `CommentsDialog` | The prefix that marks comment lines (default: `//`) |
| `DoublesDialog` | No settings — just confirm |
| `ConcatLinesDialog` | Header lines; optional filename column; skip blanks/comments; move inputs to recycle bin |
| `ConcatColumnsDialog` | Lines to skip; optional filename row at top |
| `SearchReplaceDialog` | Search text and replacement text |
| `SearchReplaceManyDialog` | Path to a tab-delimited database file of search/replace pairs |
| `FilelistDialog` | No settings — just confirm |
| `RecalcDialog` | Column spec, factor, offset, number of header lines to skip |
| `RenameDialog` | Search/replace in filename, prefix, suffix; shows live old→new preview table |
| `TimeseriesDialog` | Thinning interval in seconds (default 600); keep-header option |
| `CharPosDialog` | Character positions like "5,10-12"; text to insert or substitute; insert or replace mode |
| `AddColumnDialog` | Header/column text with prepend/append choice; filename, path, and line-number metadata columns |
| `AddLineDialog` | Single line or multi-line block; line number where the text goes |
| `SearchOneDialog` | Search text; start line; number of lines to search (0 = all) |
| `SplitDialog` | Lines per file, size/line caps, or columns per file + fixed columns — depending on mode |

The compression tools have no dialogs: compress/decompress act directly on the loaded files, and the folder variants open a standard folder picker.

---

### `tests/` — Automated Tests

**What it does:** 258 tests that verify the core processing functions work correctly. They run automatically (e.g., with `pytest`) and take under a second. No GUI is involved.

#### Test fixtures
**What it does:** Three realistic data files that all tests use as input:
- `test_data.txt` — 35 lines of oceanographic CTD data (station codes, depths, temperatures, salinity, etc.) including comment lines, a blank line, adjacent duplicates, and non-adjacent duplicates — all the edge cases the code needs to handle.
- `test_data_supplement.txt` — 8 extra lines used for testing file concatenation.
- `test_timeseries.txt` — 8 lines with a `Date/Time` column in mixed ISO formats, spacings around the 10-minute threshold, and one deliberately malformed timestamp.

**Why use realistic data instead of made-up data:** Real data has realistic quirks — special characters in column headers (`[°C]`), missing values, mixed-content lines — that made-up data might not cover.

**What the tests verify:**
- `test_columns.py` (54 tests): Column specs parse correctly, matched columns work with and without regex, comment lines always pass through, extracting + deleting the same columns reconstructs the original file.
- `test_comments.py` (8 tests): Default and custom prefixes, empty files, files with no comments.
- `test_concat.py` (25 tests): Header skipping, filename column, row-count mismatch detection, custom delimiters.
- `test_naming.py` (8 tests): Pattern tokens, collision-free output names, detection of outputs that would overwrite inputs or each other.
- `test_duplicates.py` (8 tests): Adjacent and non-adjacent duplicates, order preserved, case sensitivity.
- `test_filelist.py` (13 tests): Header format, all metadata fields present, graceful handling of missing files, line counting across chunk boundaries.
- `test_lines.py` (23 tests): All spec formats, matched line extraction, regex patterns, complement property.
- `test_recalc.py` (12 tests): Factor, offset, combined formula, multi-column ranges, non-numeric passthrough, header skipping, custom delimiter, integer vs. float formatting.
- `test_rename.py` (14 tests): Search/replace, prefix, suffix, combined operations, filesystem not modified by preview, empty file list.
- `test_search_replace.py` (29 tests): All occurrences replaced, replacement ordering, empty search values skipped, database loading, search-report rows with correct filenames and line numbers.
- `test_timeseries.py` (11 tests): Column detection, thinning at different intervals, malformed timestamps, first/last line guarantees.
- `test_charpos.py` (15 tests): Position spec parsing, insert/replace at single positions and ranges, past-end behavior, deletion via empty text.
- `test_addcol.py` (11 tests): Text columns front and back, metadata columns, ordinal numbering, combined blocks, custom delimiter.
- `test_addline.py` (8 tests): Insert at top/middle/past-end, multi-line blocks, empty input.
- `test_split.py` (22 tests): Even and remainder chunks, repeated headers, size and line caps, fixed columns, comment pass-through, chunk counts.
- `test_compress.py` (7 tests): Zip/gzip/tar.gz roundtrips for files and folders — compress, delete the original, decompress, and confirm the bytes are identical.

---

## Things to Know

- **The app never loads a full file into memory.** Every core function reads one line, processes it, and writes it immediately. This is why it can handle files larger than your available RAM. Never change this by adding `.readlines()` or collecting lines into a list.
- **Output files are saved in the same folder as the input files.** The naming pattern controls the filename but not the directory.
- **Tool chaining is automatic.** After a tool finishes, the file list updates to the output files. Just run the next tool.
- **Settings persist between sessions** via the Windows registry. Encoding, delimiter, and output pattern are all remembered.
- **The GUI never freezes** because all file processing runs in a background thread. If a tool is running, the status bar shows progress and menus are disabled until it finishes.
- **Regex mode is available** in matched-columns and matched-lines dialogs. Leave the checkbox unchecked for plain text matching.
- **Concatenate by columns requires equal row counts.** If your files have different numbers of rows, the operation will stop with an error rather than silently producing misaligned output.
- **64-bit hashes for deduplication** mean duplicate detection uses about 63 bytes of memory per unique line (hash plus set overhead), regardless of how long the line is: about 160 MB for 2.5 million unique lines. The chance that two different lines share a hash (and one is wrongly dropped) is about 2 in 10 million for such a file.
- **Progress is reported every 5,000 lines,** as line count and percentage. The Cancel button in the status bar stops a tool within the next 5,000 lines and deletes the unfinished output file; outputs of files already finished are kept.
- **Setup:** `pip install -r requirements.txt` (runtime) or `requirements-dev.txt` (adds pytest for the tests).
- **Tests only cover `core/`**, not the GUI. GUI behavior is tested manually. This is intentional: GUI testing is fragile and slow; core logic tests are fast and reliable.

---

## Glossary

- **TSV / Tab-delimited file:** A plain text file where each column in a row is separated by a tab character (the key between `Q` and `Caps Lock`). Opens in Excel but is stored as plain text. The default format for this app.
- **Streaming / line-by-line processing:** Reading one line at a time rather than loading the entire file. Keeps memory usage constant no matter how large the file.
- **Generator / Iterator:** A Python pattern that produces one item at a time on demand, rather than computing all items upfront. Every core function uses this pattern.
- **QThread:** A class in the PySide6 GUI library for running code in a background thread so the window stays responsive.
- **Signal:** In PySide6, a way for a background thread to send a notification to the main window (e.g., "I finished processing line 500,000"). The window then updates the progress bar.
- **Hash (BLAKE2b):** An algorithm that converts any text into a short fingerprint (here 8 bytes). Used to track which lines have been seen without storing the lines themselves.
- **Regex (regular expression):** A mini-language for describing text patterns. For example, `^//` means "starts with //". Available as an option in search tools — leave unchecked for plain text matching.
- **ExitStack:** A Python tool for safely managing multiple open files at once. Used in the split worker to ensure all chunk files are properly closed even if an error occurs.
- **QSettings:** A PySide6 class that saves and reads application settings from the Windows registry, so preferences persist between sessions.
- **Encoding:** A rule for converting characters to bytes. UTF-8 handles virtually all modern text; Latin-1 and CP1252 are older formats common in European scientific data.
- **Tool chaining:** Running one tool, then immediately running another on the output. PyPanTool supports this natively — after each run, the file list updates to the outputs automatically.
- **Complement property:** A correctness guarantee tested for columns and lines — if you extract a set of rows/columns and separately delete the same set, the two results together should reconstruct the original file exactly.
