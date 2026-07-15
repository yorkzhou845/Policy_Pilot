"""
manage.py

Helper script for maintaining your local CSV vector database.

Before running this on the GB-10, fill these values in config.py:
- POLICY_SOURCE_FOLDER
- VECTOR_DB_CSV

The user types:
1. append -> then enters the full local file path to insert
2. delete -> then enters the file name, or a full path, to remove from the vector database
"""

from pathlib import Path

from chunking import insert_file_into_vector_db, delete_file_from_vector_db


def append_file():
    file_path = input("Enter the full file path to append: ").strip().strip('"')

    rows_added = insert_file_into_vector_db(
        file_path=file_path,
        replace_existing=False
    )

    print(f"Appended {rows_added} chunks from: {file_path}")


def delete_file():
    file_input = input("Enter the file name or full file path to delete: ").strip().strip('"')

    # If the user enters a full path, this extracts only the file name.
    file_name = Path(file_input).name

    rows_deleted = delete_file_from_vector_db(file_name)

    print(f"Deleted {rows_deleted} chunks from: {file_name}")


if __name__ == "__main__":
    while True:
        action = input("Type 'append' to insert a file, or 'delete' to remove a file. Type 'end' to stop ").strip().lower()

        if action == "append":
            append_file()

        elif action == "delete":
            delete_file()

        elif action == "end":
            print("Bye! From here, it's possible.")
            break

        else:
            print("Invalid choice. Type either 'append' or 'delete' or 'end'.")
