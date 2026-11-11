# Test Fixtures

## test_data.txt (main fixture)
Tab-delimited, 11 columns, 33 lines. Contains:
- 3 comment lines (`//`) at top, 1 mid-file (line 22)
- 1 empty line (after PS002 block)
- 1 exact adjacent duplicate (PS003 at 500m, lines 19-20)
- 2 non-adjacent duplicates (PS002/PS001 repeated at end, lines 30-31)
- 1 row with missing values — empty Temperature and Conductivity (PS004 at 1000m)
- Header with special characters: `[°C]`, `[ml/l]`, `[PSU]`, `[dbar]`, `[mS/cm]`
- Mixed comment content in last column (some filled, some empty)

## test_timeseries.txt (for Extract 10 min Lines tests)
Tab-delimited, 4 columns, 8 lines (1 header + 7 data). `Date/Time` column with:
- Mixed ISO formats: `yyyy-MM-ddTHH:MM`, `THH:MM:SS`, `THH:MM:SS.fff`
- 1 malformed timestamp (`15.01.2024 08:20`, line 6) → error-marker line
- Row spacing chosen to exercise the 600 s threshold (5, 5, 2, 8.5, 0.5 min)

## test_data_supplement.txt (for concatenation tests)
Same 11-column structure, 8 lines (1 comment + 1 header + 6 data).
Different stations (PS005, PS006). Use with test_data.txt to verify:
- Concatenate by lines (with skip-header option)
- Concatenate by columns (row counts differ — should error or warn)

## test_pangaea_header.txt (for header-detection tests)
Tab-delimited PANGAEA-style download, 11 lines. Contains:
- A `/* ... */` metadata block (lines 1-5) whose lines contain tabs
- Header on line 6 (5 columns), 4 data lines
- 1 comment line containing a tab (line 9)
- 1 short row with 4 cells (line 10) and 1 non-numeric value `n.d.` (line 11)
- Trailing zeros (`-1.820`, `-1.80`) for precision-preserving recalculation

## test_datetime_formats.txt (for Convert Date/Time tests)
Tab-delimited, 5 columns, 8 lines (1 header + 6 data + 1 comment on line 4).
- `Date` as `dd.MM.yyyy` (one row without leading zeros: `1.3.2024`), `Time` as `HH:mm:ss`
- `Excel day`: the same instants as Excel serial day numbers (1900 date system)
- 1 row with empty date, time and serial (line 6)
- 1 row with a date in the wrong format (`2024-03-02`) and `n.d.` as serial (line 7)
