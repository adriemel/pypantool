# PyPanTool — Plain-English Walkthrough

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
│   ├── columns.py             ← Extract or delete columns by number or header name
│   ├── comments.py            ← Delete lines that start with a comment marker (e.g. //)
│   ├── concat.py              ← Join files vertically (stacked) or horizontally (side-by-side)
│   ├── duplicates.py          ← Remove duplicate lines, keep first occurrence
│   ├── filelist.py            ← Export a list of loaded files (name, path, size, date)
│   ├── lines.py               ← Extract or delete lines by number or content match
│   ├── naming.py              ← Resolve output filenames from a pattern like "%N_out%E"
│   ├── recalc.py              ← Recalculate column values: new = old × factor + offset
│   ├── rename.py              ← Filename transformation: search/replace, prefix, suffix
│   └── search_replace.py      ← Find/replace one string or many at once
│
├── gui/
│   ├── main_window.py         ← The main application window
│   ├── options_dialog.py      ← Settings: output pattern, encoding, delimiter
│   ├── run_tool.py            ← Wires a dialog's settings to a background worker
│   ├── style.py               ← All visual styling (slate-blue theme)
│   ├── worker.py              ← Background threads that do the actual file I/O
│   └── dialogs/               ← One small dialog per tool (13 dialog files)
│
└── tests/
    ├── fixtures/
    │   ├── test_data.txt          ← 35-line realistic oceanographic dataset
    │   └── test_data_supplement.txt  ← 8-line companion for concat tests
    ├── test_columns.py
    ├── test_comments.py
    ├── test_concat.py
    ├── test_duplicates.py
    ├── test_filelist.py
    ├── test_lines.py
    ├── test_recalc.py
    ├── test_rename.py
    └── test_search_replace.py
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

**What it does:** Removes duplicate lines, keeping only the first occurrence of each. The clever part: instead of storing every line in memory to compare against future lines (which would crash the program on a 700 MB file), it stores only a 32-byte fingerprint (SHA-256 hash) of each line. The fingerprints take up a tiny fraction of the memory.
**Why it exists:** Tabular data exports often contain accidental duplicates from data joins or repeated exports.
**Things to know:** Comparison is case-sensitive and whitespace-significant — "Station A" and "station a" are treated as different lines.

---

### `core/concat.py` — File Concatenation

**What it does:** Merges multiple files into one. Two completely different strategies:

#### Concatenate by lines (vertical stacking)
**What it does:** Appends files one after another, like stacking sheets of paper. Files 2, 3, etc. can optionally have their header lines skipped so the output doesn't repeat the header. You can optionally insert a `# filename` marker before each file's section, skip blank lines, or skip comment lines.
**Use case:** You have one data file per month. This merges them into a single year-long file without duplicating the header row.

#### Concatenate by columns (horizontal merging)
**What it does:** Zips files side-by-side, row by row. Row 1 of file A and row 1 of file B become a single wider row. All files must have the same number of rows. Optionally, a row of filenames is prepended at the top.
**Use case:** You measured temperature in one file and salinity in another, same stations in the same order. This creates one combined file with all measurements.
**Things to know:** If the files have different numbers of rows, the operation stops with an error — misaligned data would silently produce wrong results.

---

### `core/search_replace.py` — Find and Replace

**What it does:** Three related functions.

#### Single find/replace
**What it does:** Replaces all occurrences of a search string with a replacement string, in every line, in every loaded file. Not regex — plain text matching.
**Use case:** Fix a misspelled station name across a hundred files at once.

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
**What it does:** Opens each file, feeds lines to a core processing function one at a time, and writes the output lines immediately to the output file. Reports progress every 5,000 lines. Used by all single-file tools (extract columns, delete duplicates, recalculate columns, etc.).

#### ConcatWorker
**What it does:** Opens all input files at the same time, passes their line streams to the concat function, and writes the result. Keeps all files open simultaneously so rows can be interleaved (needed for side-by-side merging).

#### FilelistWorker
**What it does:** The simplest worker — it doesn't read any file contents, just collects file metadata and writes the summary file.

#### RenameWorker
**What it does:** Renames files in place on disk (no new output file is created). Iterates through the (old path, new path) pairs computed by the dialog preview and calls the operating system rename for each pair. Files whose name would not change are skipped. After all renames succeed, emits the list of new paths so the file list table updates.

**Why all four exist separately:** Their patterns of file access are fundamentally different — one file at a time vs. all at once vs. no file reading at all vs. in-place rename with no content I/O.
**Things to know:** If an error occurs during processing, the worker catches it and sends an error notification to the window, which shows a message box. No partial output files are left behind. For `RenameWorker`, if a rename fails mid-way (e.g. a file is locked), processing stops and already-renamed files keep their new names.

---

### `gui/run_tool.py` — The Wiring Layer

**What it does:** The bridge between dialogs and workers. When you click OK in a tool's dialog, this module:
1. Takes the core function pre-configured with your settings
2. Figures out the output file path for each input file using the naming pattern
3. Creates the appropriate worker
4. Connects the worker's progress signals to the window's status bar and progress indicator
5. Starts the background thread
6. When it's done, replaces the file list with the output files (enabling tool chaining)

**Why it exists:** Without this, every dialog would have to duplicate the same wiring code. This puts it in one place.

---

### `gui/main_window.py` — The Main Window

**What it does:** The central hub of the application. Manages the file list table, all menus and toolbar buttons, status bar, drag-and-drop, and coordinates all tool operations.

#### File list table
**What it does:** Shows each loaded file with its name, directory path, size, and line count. Line counts are filled in progressively as background workers report progress.

#### File loading
**What it does:** Three ways to load files — file picker dialog (multi-select), folder picker (loads every text file in the folder), or drag-and-drop files/folders directly onto the window. Duplicate files are automatically skipped.

#### Tool chaining
**What it does:** After a tool runs, the output files automatically replace the input files in the list. Running another tool immediately processes the output of the previous one. The `%a` counter in the filename pattern increments with each run, so outputs are named `data_out_1.txt`, `data_out_2.txt`, etc.

#### Menus
**What it does:** The Tools menu has 17 items, one per tool. Clicking any of them opens the corresponding small dialog. File menu has Open, Open Folder, Clear, Options, and Quit. Help menu has About.

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

### `gui/dialogs/` — Tool Dialogs (13 files)

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
| `ConcatLinesDialog` | Lines to skip from subsequent files; optional filename markers; skip blanks/comments |
| `ConcatColumnsDialog` | Lines to skip; optional filename row at top |
| `SearchReplaceDialog` | Search text and replacement text |
| `SearchReplaceManyDialog` | Path to a tab-delimited database file of search/replace pairs |
| `FilelistDialog` | No settings — just confirm |
| `RecalcDialog` | Column spec, factor, offset, number of header lines to skip |
| `RenameDialog` | Search/replace in filename, prefix, suffix; shows live old→new preview table |

---

### `tests/` — Automated Tests

**What it does:** 162 tests that verify the core processing functions work correctly. They run automatically (e.g., with `pytest`) and take under a second. No GUI is involved.

#### Test fixtures
**What it does:** Two realistic data files that all tests use as input:
- `test_data.txt` — 35 lines of oceanographic CTD data (station codes, depths, temperatures, salinity, etc.) including comment lines, a blank line, adjacent duplicates, and non-adjacent duplicates — all the edge cases the code needs to handle.
- `test_data_supplement.txt` — 8 extra lines used for testing file concatenation.

**Why use realistic data instead of made-up data:** Real data has realistic quirks — special characters in column headers (`[°C]`), missing values, mixed-content lines — that made-up data might not cover.

**What the tests verify:**
- `test_columns.py` (54 tests): Column specs parse correctly, matched columns work with and without regex, comment lines always pass through, extracting + deleting the same columns reconstructs the original file.
- `test_comments.py` (8 tests): Default and custom prefixes, empty files, files with no comments.
- `test_concat.py` (19 tests): Header skipping, filename markers, row-count mismatch detection, custom delimiters.
- `test_duplicates.py` (8 tests): Adjacent and non-adjacent duplicates, order preserved, case sensitivity.
- `test_filelist.py` (8 tests): Header format, all metadata fields present, graceful handling of missing files.
- `test_lines.py` (23 tests): All spec formats, matched line extraction, regex patterns, complement property.
- `test_recalc.py` (12 tests): Factor, offset, combined formula, multi-column ranges, non-numeric passthrough, header skipping, custom delimiter, integer vs. float formatting.
- `test_rename.py` (14 tests): Search/replace, prefix, suffix, combined operations, filesystem not modified by preview, empty file list.
- `test_search_replace.py` (20 tests): All occurrences replaced, replacement ordering, empty search values skipped, database loading.

---

## Things to Know

- **The app never loads a full file into memory.** Every core function reads one line, processes it, and writes it immediately. This is why it can handle files larger than your available RAM. Never change this by adding `.readlines()` or collecting lines into a list.
- **Output files are saved in the same folder as the input files.** The naming pattern controls the filename but not the directory.
- **Tool chaining is automatic.** After a tool finishes, the file list updates to the output files. Just run the next tool.
- **Settings persist between sessions** via the Windows registry. Encoding, delimiter, and output pattern are all remembered.
- **The GUI never freezes** because all file processing runs in a background thread. If a tool is running, the status bar shows progress and menus are disabled until it finishes.
- **Regex mode is available** in matched-columns and matched-lines dialogs. Leave the checkbox unchecked for plain text matching.
- **Concatenate by columns requires equal row counts.** If your files have different numbers of rows, the operation will stop with an error rather than silently producing misaligned output.
- **SHA-256 for deduplication** means duplicate detection uses 32 bytes of memory per unique line regardless of how long the line is. A file with 2.5 million unique lines needs about 80 MB of memory for the hash set — manageable.
- **Progress is reported every 5,000 lines.** For very large files you won't see every line tick by, but you'll see regular updates.
- **Tests only cover `core/`**, not the GUI. GUI behavior is tested manually. This is intentional: GUI testing is fragile and slow; core logic tests are fast and reliable.

---

## Glossary

- **TSV / Tab-delimited file:** A plain text file where each column in a row is separated by a tab character (the key between `Q` and `Caps Lock`). Opens in Excel but is stored as plain text. The default format for this app.
- **Streaming / line-by-line processing:** Reading one line at a time rather than loading the entire file. Keeps memory usage constant no matter how large the file.
- **Generator / Iterator:** A Python pattern that produces one item at a time on demand, rather than computing all items upfront. Every core function uses this pattern.
- **QThread:** A class in the PySide6 GUI library for running code in a background thread so the window stays responsive.
- **Signal:** In PySide6, a way for a background thread to send a notification to the main window (e.g., "I finished processing line 500,000"). The window then updates the progress bar.
- **SHA-256:** A hashing algorithm that converts any text into a unique 32-byte fingerprint. Used here to track which lines have been seen without storing the lines themselves.
- **Regex (regular expression):** A mini-language for describing text patterns. For example, `^//` means "starts with //". Available as an option in search tools — leave unchecked for plain text matching.
- **ExitStack:** A Python tool for safely managing multiple open files at once. Used in the concat worker to ensure all files are properly closed even if an error occurs.
- **QSettings:** A PySide6 class that saves and reads application settings from the Windows registry, so preferences persist between sessions.
- **Encoding:** A rule for converting characters to bytes. UTF-8 handles virtually all modern text; Latin-1 and CP1252 are older formats common in European scientific data.
- **Tool chaining:** Running one tool, then immediately running another on the output. PyPanTool supports this natively — after each run, the file list updates to the outputs automatically.
- **Complement property:** A correctness guarantee tested for columns and lines — if you extract a set of rows/columns and separately delete the same set, the two results together should reconstruct the original file exactly.
