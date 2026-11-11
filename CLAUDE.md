# PyPanTool — Data File Swiss Army Knife

Personal-use Windows desktop tool for batch processing of large tabular text files.
Inspired by PANGAEA PanTool (https://wiki.pangaea.de/wiki/PanTool).

## Critical Constraint: Large File Handling

Files can be 700 MB+ with 2,500,000+ lines. Every design decision flows from this.

- NEVER load entire files into memory. No `.readlines()`, no `.read()`, no accumulating lists.
- Stream line-by-line using `open()` iteration or generators. Write output progressively.
- Every processing function signature: `process(input: Iterable[str], ...) -> Iterator[str]`
- For stateful operations (e.g. duplicate detection): use hashes, not stored line text.
- Always report progress (line count, percentage) back to the GUI via signals.
- Batch file operations must process files sequentially to limit memory to one file at a time.

## Tech Stack

- Python 3.12+
- PySide6 for GUI (native Windows menus, file dialogs, drag-and-drop, progress bar)
- No other runtime dependencies for core processing

## Architecture

```
pypantool/
  core/           # Pure Python. Zero GUI imports. One module per tool.
  gui/            # PySide6 windows, menus, dialogs, worker threads.
  tests/          # Tests for core/ only. No GUI tests.
  main.py         # Entry point
```

Rules:
- Core functions never import from gui/. GUI calls core/ via QThread workers.
- All file processing runs in background threads. GUI must never freeze.
- Each tool is one function. No deep class hierarchies. No premature abstraction.

## Output File Naming

Support PanTool's pattern system for output filenames:
- `%N` = input filename without extension
- `%a` = auto-incrementing counter (1, 2, 3...) when chaining tools
- `%E` = original file extension
- Example: `%N_processed.txt` turns `data.tab` into `data_processed.txt`

User configures this once in File > Options. Default: `%N_out%E`

## Feature Set — Basic Tools Menu

Each tool opens a small dialog for parameters, then processes all loaded files.

1. **Extract columns** — by number, range (`4-7`), or `end` keyword (`3,5-end`)
2. **Extract matched columns** — header matches a search string or regex
3. **Extract lines** — by line number or range
4. **Extract matched lines** — line contains string or matches regex
5. **Delete columns** — inverse of extract columns, same syntax
6. **Delete matched columns** — inverse of extract matched columns
7. **Delete lines** — by line number or range
8. **Delete matched lines** — line contains string or matches regex
9. **Delete comment blocks** — remove lines starting with a configurable prefix (default `//`)
10. **Delete double lines** — remove duplicate lines (keep first occurrence)
11. **Concatenate files by columns** — merge files side-by-side into `Concatenate_columns_out.<ext>` (auto-numbered; same row count required). Options: skip N header lines, include filename in first row.
12. **Concatenate files by lines** — append files top-to-bottom into `Concatenate_out.<ext>` (auto-numbered, never overwrites). Options: N header lines (kept once), filename stem as column 1 (`Filename` on the header line; comment/empty lines untouched), skip empty lines, skip comment lines, move inputs to recycle bin after success.
13. **Save file list** — export loaded file metadata (path, name, size, date) to `Filelist_out.txt` in the first file's folder (auto-numbered).
14. **Search and replace one string** - allows to search and replace a string in multiple files at once
15. **Search and replace many strings at once** - asks for a "search and replace database" file (1st column search text, second column replace text) and does a find replace of many strings in either one or many files
16. **Recalculate columns** — apply `new = old × factor + offset` to selected columns (same spec syntax as extract/delete). Non-numeric values and configurable number of header lines pass through unchanged.
17. **Rename files** — bulk in-place rename with search/replace in filename, prefix, and suffix (suffix inserts before extension). Dialog shows a live old→new preview before executing.
18. **Extract 10 min lines** — time-series thinning: keep one line per interval (default 600 s) based on the ISO-format `Date/Time` column. First and last data lines are always kept; malformed timestamps produce an error-marker line.
19. **Search one string** — report every match across all loaded files as `Filename / Line / String` rows into `Search_out.<ext>` (auto-numbered; works with a single file). Options: start line, number of lines.
20. **Insert characters at positions** — insert text before each 1-based character position (`5,10-12` spec syntax) in every line. `^t` = tab.
21. **Replace characters at positions** — replace the character at each position with text (empty text deletes).
22. **Split file by lines** — N data lines per numbered output chunk (`name_0001.ext`); header lines repeated per chunk.
23. **Split file by columns** — fixed columns repeated + N data columns per chunk; comment lines pass through to all chunks.
24. **Split large file** — new chunk when a size (default 100 MB) or line cap (default 1,000,000) is reached; header lines repeated.
25. **Add column** — prepend/append a constant column and/or metadata columns (`Event label` = file stem, `Filename` = full path, `No` = 1-based ordinal).
26. **Add text line / Add text block** — insert one or more lines at a 1-based line number (appended when the file is shorter). `^t` = tab.
27. **Compress files (zip/gz)** — archive each loaded file next to its source using stdlib zipfile/gzip (no external binaries); archives replace the file list for chaining.
28. **Compress folder (zip/tar.gz)** — folder picker, recursive.
29. **Decompress files** — dispatch on `.zip`/`.gz`/`.tgz`/`.tar`/`.tar.gz`, extract next to the archive.
30. **File statistics** — read-only scan of the *selected* file (toolbar, Tools menu, Ctrl+I or double-click) shown in a window: encoding validity, BOM, line endings, header line, row-width deviations; per column type, filled/empty/numeric counts, min/max, decimals, distinct count (capped at 1000), missing-value markers, non-numeric examples with line numbers, Date/Time order checks. "Save report…" writes `<name>_stats.txt` (auto-numbered). Core: `core/profile.py`; it is the one tool that returns a result object instead of a line iterator and reads lines with endings and `errors="surrogateescape"`.
31. **Convert Date/Time to ISO 8601** — rewrite one date column (optionally merged with a separate time column) as `yyyy-MM-ddTHH:mm[:ss[.fff]]`; header becomes `Date/Time`. Input format given with PanTool-style tokens (`dd.MM.yyyy HH:mm:ss`, `DDD` = day of year, `MMM`, `AP`) or `excel` / `unix`; optional UTC offset is subtracted. Non-matching cells stay unchanged and are reported; the run aborts if the first 100 values all fail. Dialog previews the first data row. Core: `core/datetime_convert.py`.

## File Handling — File Menu

- **Open files** via file dialog (multi-select)
- **Select folder** to load all text files in a directory
- **Drag & drop** files or folders onto the main window
- **Options dialog**: output naming pattern, input/output encoding (UTF-8, Latin-1, CP1252, ASCII)
- Chaining: output of one tool becomes input for the next tool automatically

## GUI Layout

Top to bottom, one window, no ribbon, no tabs, no sidebar:

- **Menu bar** grouped by what a tool works on: File, Columns, Lines, Text, Combine / Split, Files, Help. New tools go into the fitting group via `_add_tool_menu` in `gui/main_window.py`; mnemonics must be unique within a menu. Help › Find Tool (Ctrl+K) filters all tools by name.
- **Toolbar**: Open files, Select folder, Clear, File Statistics; on the right a chip showing delimiter, encodings, header line and name pattern (click opens Options). Menus and toolbar are disabled while a tool runs.
- **Context line**: file count, total size, common folder.
- **File list**: name, folder (only shown when files come from several folders), size (SI units), lines, columns, and a quick sniff of the first 64 kB (encoding validity, line endings, ragged rows; problems in amber). Sniff and line counts run in `LineCountWorker`.
- **Peek pane**: first 200 lines of the selected file (at most 256 kB are read) with column numbers and line numbers; header row highlighted.
- **Journal**: one line per tool run (time, tool, parameters, files in → out, lines in → out, duration). "Step back" (Ctrl+Z) reloads the previous file set; "Save journal…" writes a tab-delimited log with UTC timestamps. Parameters come from the `functools.partial` passed to `run_*` (`describe_params`).
- **Status bar**: current operation, progress, Cancel.
- **Dialogs**: one small dialog per tool; the action button carries the verb and is the default button. Dialogs that take a column spec show what it selects in the first file.

Style lives in `gui/style.py` (paper/ink palette; teal = selection, amber = needs attention; numbers and file content in a monospaced font via `mono_font()`). Spin boxes, combo boxes and check boxes are deliberately left native.

## Column Delimiter

Default delimiter: tab (`\t`). Allow user override in Options (tab, semicolon, comma, pipe, space).

## Header Line and Comments (shared rule)

All column-aware tools locate the header with `core/header.py::header_finder`; never re-implement header detection in a tool. The header is the first line that
- is not inside a leading `/* ... */` block (PANGAEA download metadata),
- is on or after the Options setting "Header is on or after line" (default 1),
- does not start with the Options comment prefix (default `//`),
- contains the delimiter.

Lines before the header, comment lines and lines without the delimiter pass through unchanged. GUI dialogs pass these settings with `table_options(settings)`.

## Data Safety Rules

- Decode input strictly (no `errors="replace"`); report file, byte and line on failure. UTF-8 input drops a BOM.
- Output keeps the input's line ending (CRLF or LF).
- Never overwrite silently: ask (per-file tools) or refuse (split chunks, decompress).
- Invalid column specs (column < 1 or beyond the header width, header pattern without match) are errors, never empty output.
- Recalculation uses `decimal.Decimal` so written precision is preserved.

## Code Style

- Type hints on all function signatures
- Docstrings only on public core/ functions
- Keep functions short and flat. Prefer early returns.
- Test core processing functions with the fixtures in `tests/fixtures/` (see README there).
- Never generate synthetic test data when fixtures already cover the case.
