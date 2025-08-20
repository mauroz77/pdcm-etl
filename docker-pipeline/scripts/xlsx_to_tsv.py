import argparse
import re
import subprocess
import sys
import pandas as pd
import os
import pkg_resources
import zipfile

# Original file: https://gitlab.ebi.ac.uk/mouse-informatics/pdxfinder-data/-/blob/master/xlsx_to_tsv.py


def main(argv=None):
    arguments_options = argparse.ArgumentParser()
    mutually_exclusive_group = arguments_options.add_mutually_exclusive_group(
        required=True
    )
    arguments_options.add_argument(
        "-d",
        "--dir",
        help="Directory root containing xlsx (recurisvely) files",
        required=True,
    )
    arguments_options.add_argument(
        "-n", "--dry-run", help="Run dry command on directory", action="store_true"
    )
    arguments_options.add_argument(
        "-t",
        "--template-mode",
        help="Run in template mode (does not remove comments and field columns)",
        action="store_true",
    )
    mutually_exclusive_group.add_argument(
        "-a", "--all", help="Convert all xlsx files in directory", action="store_true"
    )
    mutually_exclusive_group.add_argument(
        "-g", "--git", help="Convert files in git index", action="store_true"
    )
    args = arguments_options.parse_args(argv)
    if args.dir:
        if os.path.exists(args.dir):
            run(args.dir, args)
        else:
            print(f"Path {args.dir} does not exist", file=sys.stderr)
    else:
        print("Directory was not passed", file=sys.stderr)


def run(target_dir_path, args):
    target_file_paths = []
    if args.dry_run:
        print("**** Dry run. No files will be changed ****")
    if args.all:
        print(f"Digesting all xlsx in target directory: {target_dir_path}")
        target_file_paths = get_all_xlsx_file_paths(target_dir_path)
    elif args.git:
        print(
            f"Digesting all xlsx with changes found in git index for dir: {target_dir_path}"
        )
        target_file_paths = get_git_index_file_paths(target_dir_path)
    if target_file_paths:
        digest_files(target_file_paths, args.dry_run, args.template_mode)


def get_all_xlsx_file_paths(target_dir_path):
    xlsx_paths = []
    for root, dirs, files in os.walk(target_dir_path):
        for file in files:
            if file.endswith(".xlsx"):
                file_path = os.path.join(root, file)
                xlsx_paths.append(file_path)
    return xlsx_paths


def filter_git_status(list_of_git_status):
    deleted_or_unknown = re.compile("(^D\s|^.D|^\!|^.\!|^\?|^.\?)")
    filter_func = lambda x: not deleted_or_unknown.match(x)
    return filter(filter_func, list_of_git_status)


def get_all_xlsx_files(list_of_git_filtered_files):
    file_path = []
    for file in list_of_git_filtered_files:
        if file.endswith(".xlsx"):
            file_path.append(file)
    return file_path


def clean_git_paths(xlsx_matches, target_dir_path):
    full_clean_paths = []
    for match in xlsx_matches:
        filename = match.split(" ")[-1]
        full_path = os.path.join(target_dir_path, os.path.basename(filename))
        full_clean_paths.append(full_path)
    return full_clean_paths


def get_git_index_file_paths(target_dir_path):
    os.chdir(target_dir_path)
    output_bytes = ""
    try:
        output_bytes = subprocess.check_output(["git", "status", "--porcelain", "."])
    except subprocess.CalledProcessError as e:
        print("Calling git failed. Check you are in a git repo", file=sys.stderr)
        print(e.output, file=sys.stderr)
    list_of_git_status = output_bytes.decode().split("\n")
    changed_git_status_files = filter_git_status(list_of_git_status)
    cleaned_git_paths = clean_git_paths(changed_git_status_files, target_dir_path)
    return get_all_xlsx_files(cleaned_git_paths)


def formatXlsxColumnDates(formatted_table, columnName):
    date_index = (
        formatted_table[columnName]
        .astype(str)
        .str.contains("[0-9]{4}-[0-9]{2}-[0-9]{2} 00:00:00", regex=True, na=False)
    )
    if any(date_index):
        print(f"    │   │   └──Formatting dates in column: {columnName}")
    formatted_table.loc[date_index, columnName] = formatted_table.loc[
        date_index, columnName
    ].apply(lambda x: x.strftime("%b %Y"))
    return formatted_table


def read_excel_sheets(file_path, template_mode):
    sheets = {}
    if template_mode:
        sheets = pd.read_excel(file_path, sheet_name=None, engine="openpyxl")
    else:
        if not file_path.endswith(".xlsx"):
            print(f"Skipping non-xlsx file: {file_path}")
            return sheets
        try:
            raw_sheets = pd.read_excel(
                file_path, sheet_name=None, engine="openpyxl", comment="#"
            )

            sheets = drop_field_column(raw_sheets)
        except zipfile.BadZipFile:
            print(f"Warning: {file_path} is not a valid Excel file. Skipping.")

    return sheets


def drop_field_column(dict_of_df):
    sheets_with_dropped_column = {}
    for df_name, df in dict_of_df.items():
        if "Field" in df.columns:
            sheets_with_dropped_column[df_name] = df.drop(columns=["Field"])
    return sheets_with_dropped_column


def digest_xlsx_to_tsv(file_path, dry_run, has_next, template_mode):
    file_path_without_ex = os.path.splitext(file_path)[0]
    file_base_name = os.path.basename(file_path_without_ex)
    sheets = read_excel_sheets(file_path, template_mode)
    size = len(sheets)
    counter = 0
    for key in sheets.keys():
        has_next_sheet = counter < size - 1
        treeSymbol = "├──" if has_next_sheet else "└──"
        treeSymbol = f"│   {treeSymbol}" if has_next else f"   {treeSymbol}"
        print(f"    {treeSymbol}Writing: {file_base_name}-{key}.tsv")
        counter += 1
        if not dry_run:
            tsv_file_path = f"{file_path_without_ex}-{key}.tsv"
            df = sheets[key]
            formatted_table = df.loc[:, ~df.columns.str.startswith("Unnamed")].dropna(
                axis=0, how="all"
            )
            if "collection_date" in formatted_table.columns:
                formatted_table = formatXlsxColumnDates(
                    formatted_table.copy(), "collection_date"
                )
            formatted_table.to_csv(tsv_file_path, sep="\t", index=False)


def digest_files(target_file_paths, dry_run, template_mode):
    size = len(target_file_paths)
    counter = 0
    for file_path in target_file_paths:
        has_next = counter < size - 1
        treeSymbol = "├──" if has_next else "└──"
        print(f"    {treeSymbol}Digesting: {file_path}")
        digest_xlsx_to_tsv(file_path, dry_run, has_next, template_mode)


required = {"openpyxl"}
installed = {pkg.key for pkg in pkg_resources.working_set}
missing = required - installed
if missing:
    print("Missing openpyxl. Please install and re-run")
else:
    if __name__ == "__main__":
    # Only run if executed directly, NOT imported
        main()
