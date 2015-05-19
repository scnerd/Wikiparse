from wikisplitter import DB_NAME
import sqlite3 as sql
import bz2, argparse, os, atexit

global args

SQL_FETCH = r"SELECT title, xml_bz2 FROM pages"

def parse_xml(xml):
    print(xml)

def handle_entry(entry):
    title, zipped = entry[0:2]
    if args.verbose:
        print(title)
    return parse_xml(bz2.decompress(zipped))

def process_database():
    connection = sql.connect(os.path.join(args.directory, DB_NAME))
    atexit.register(connection.close)
    c = connection.cursor()
    for entry in c.execute(SQL_FETCH):
        handle_entry(entry)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Expand wikipedia file into page files')
    parser.add_argument('-d', '--directory', help="Changes the output directory", default="./wikipedia")
    parser.add_argument('-v', '--verbose', help="Prints page titles as they get output", action="store_true")
    args = parser.parse_args()

    process_database()